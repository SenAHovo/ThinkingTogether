# dev/api/server.py
"""
智炬五维协同学习系统 - FastAPI 后端服务器
提供RESTful API接口供前端调用
"""
from __future__ import annotations

import os
import sys
from dotenv import load_dotenv

# 加载.env文件
load_dotenv()
import uuid
import asyncio
import zipfile
import io
import pymysql
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Header, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from fastapi.responses import JSONResponse, Response, StreamingResponse

# 添加项目根目录到Python路径
# server.py 位于 dev/api/ 目录下，需要向上两级到达项目根目录
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

# 导入认证模块
from dev.auth.auth_utils import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_user_id,
    generate_session_id,
)

# 导入邮件验证模块
from dev.email.verification import VerificationCodeManager
from dev.email.email_service import email_service

from dev.agents.organizer_agent import OrganizerAgent
from dev.agents.theorist_tool import theorist_speak
from dev.agents.practitioner_tool import practitioner_speak
from dev.agents.skeptic_tool import skeptic_speak
from dev.agents.rewriter_tools import rewrite_if_needed
from dev.memory.history_store import history_store, events_to_messages
from dev.memory.state_store import (
    init_state,
    set_agenda,
    apply_patch,
    advance_turn,
    DiscussionState,
    load_state_from_db,
)
from types import SimpleNamespace

# 尝试导入数据库管理器
_db_manager = None
_db_available = False  # 单独跟踪数据库可用性
_db_config = None  # 保存数据库配置
try:
    from dev.mysql.db_utils import DatabaseManager, ensure_db_connected
    from dev.mysql.db_config import get_db_config
    _db_config = get_db_config()
    _db_manager = DatabaseManager.from_config()

    # 尝试连接数据库
    if ensure_db_connected():
        print("[API] 数据库连接成功，将支持历史对话加载和用户认证")
        _db_available = True
    else:
        print("[API] 数据库连接失败，仅支持游客模式（无法登录/注册）")
        _db_manager = None
except Exception as e:
    print(f"[API] 数据库初始化失败: {e}，仅支持游客模式（无法登录/注册）")
    _db_manager = None


# 初始化验证码管理器
_verification_manager = None
if _db_config:
    try:
        _verification_manager = VerificationCodeManager(_db_config)
        print("[API] 验证码管理器初始化成功")
    except Exception as e:
        print(f"[API] 验证码管理器初始化失败: {e}")


def create_thread_local_connection():
    """为线程创建独立的数据库连接，避免多线程共享连接导致的问题"""
    if not _db_config:
        return None
    try:
        conn = pymysql.connect(
            host=_db_config['host'],
            user=_db_config['user'],
            password=_db_config['password'],
            database=_db_config['database'],
            port=_db_config['port'],
            charset=_db_config['charset'],
            cursorclass=pymysql.cursors.DictCursor
        )
        return conn
    except Exception as e:
        print(f"[API] 创建线程独立数据库连接失败: {e}")
        return None

# ========== 违禁词检测（Trie树） ==========

class BannedWordsTrie:
    """违禁词Trie树"""

    def __init__(self):
        self.root = {'children': {}}
        self._loaded = False

    def insert(self, word: str, category: str = "其他", severity: int = 1):
        """插入一个违禁词"""
        node = self.root
        for char in word:
            if char not in node['children']:
                node['children'][char] = {
                    'char': char,
                    'children': {},
                    'is_end': False
                }
            node = node['children'][char]

        node['is_end'] = True
        node['category'] = category
        node['severity'] = severity

    def search(self, text: str):
        """
        搜索文本中的违禁词
        返回第一个匹配的违禁词信息，或None
        """
        for i in range(len(text)):
            node = self.root

            for j in range(i, len(text)):
                char = text[j]

                if char not in node['children']:
                    break

                node = node['children'][char]

                if node['is_end']:
                    # 找到违禁词，立即返回
                    return {
                        'word': text[i:j+1],
                        'start': i,
                        'end': j+1,
                        'category': node['category'],
                        'severity': node['severity']
                    }

        return None

    def search_all(self, text: str):
        """
        搜索文本中的所有违禁词
        返回所有匹配的违禁词列表
        """
        violations = []

        for i in range(len(text)):
            node = self.root

            for j in range(i, len(text)):
                char = text[j]

                if char not in node['children']:
                    break

                node = node['children'][char]

                if node['is_end']:
                    violations.append({
                        'word': text[i:j+1],
                        'start': i,
                        'end': j+1,
                        'category': node['category'],
                        'severity': node['severity']
                    })
                    break  # 找到一个后继续从下一个位置开始

        return violations

# 全局违禁词Trie树
_banned_words_trie = BannedWordsTrie()

def load_banned_words_to_trie():
    """从数据库加载违禁词到Trie树"""
    global _banned_words_trie

    if not _db_manager:
        print("[违禁词] 数据库未连接，无法加载违禁词")
        return False

    try:
        with _db_manager.get_cursor() as cursor:
            cursor.execute("""
                SELECT word, category, severity
                FROM forbidden_words
                WHERE is_active = 1
            """)
            words = cursor.fetchall()

            # 重建Trie树
            _banned_words_trie = BannedWordsTrie()
            count = 0
            for word_info in words:
                _banned_words_trie.insert(
                    word_info['word'],
                    word_info['category'],
                    word_info['severity']
                )
                count += 1

            _banned_words_trie._loaded = True
            print(f"[违禁词] 成功加载 {count} 个违禁词到Trie树")
            return True

    except Exception as e:
        print(f"[违禁词] 加载失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def reload_banned_words():
    """重新加载违禁词（管理员修改后调用）"""
    return load_banned_words_to_trie()

# 应用启动时加载违禁词
if _db_available:
    load_banned_words_to_trie()


# ========== FastAPI 应用初始化 ==========
app = FastAPI(
    title="智炬五维协同学习系统 API",
    description="多智能体协同学习对话系统后端接口",
    version="1.0.0"
)

# 添加 CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========== 角色工具映射 ==========
TOOLS = {
    "理论家": theorist_speak,
    "实践者": practitioner_speak,
    "质疑者": skeptic_speak,
}

# ========== 线程池执行器（用于非阻塞LLM调用） ==========
# 创建线程池，用于在独立线程中执行同步的LLM调用，避免阻塞事件循环
# max_workers=10 表示最多同时处理10个LLM请求
executor = ThreadPoolExecutor(max_workers=10)

# ========== 风格参数 ==========
THEORIST_STYLE = SimpleNamespace(
    vibe="学院派但不装腔，谨慎克制，爱讲边界条件和判断标准",
    tics=["从概念上讲", "换句话说", "关键变量在于", "我更倾向于先把边界说清楚"],
    taboos=["编号清单", "小标题", "加粗(**)", "以下是", "综上", "主要包括", "首先其次最后"],
)
PRACTITIONER_STYLE = SimpleNamespace(
    vibe="接地气、务实，像朋友聊天，喜欢用场景和可执行动作推进讨论",
    tics=["我举个身边的例子", "落到具体就是", "最实际的问题是", "可以先从小动作开始"],
    taboos=["编号清单", "小标题", "加粗(**)", "以下是", "综上", "主要包括", "首先其次最后"],
)
SKEPTIC_STYLE = SimpleNamespace(
    vibe="犀利但友善，专抓偷换概念和证据不足，逼大家把前提说清楚",
    tics=["等等", "你这句话其实默认了", "有没有反例", "这个结论的前提是什么"],
    taboos=["编号清单", "小标题", "加粗(**)", "以下是", "综上", "主要包括", "首先其次最后"],
)

STYLE_BY_SPEAKER = {
    "理论家": THEORIST_STYLE,
    "实践者": PRACTITIONER_STYLE,
    "质疑者": SKEPTIC_STYLE,
}

# ========== 全局状态管理 ==========
# 存储所有会话的状态和连接
sessions: Dict[str, Dict[str, Any]] = {}
active_websockets: Dict[str, WebSocket] = {}


# ========== Pydantic 数据模型 ==========
class CreateChatRequest(BaseModel):
    topic: str
    title: Optional[str] = None


class SendMessageRequest(BaseModel):
    chat_id: str
    content: str
    action: Optional[str] = "send"  # send, continue, end


# ========== 用户认证数据模型 ==========
class RegisterRequest(BaseModel):
    username: str
    password: str
    email: str  # 改为必填
    verification_code: str  # 添加验证码字段
    avatar_url: Optional[str] = None


class LoginRequest(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    user_id: str
    username: str
    email: Optional[str] = None
    avatar_url: Optional[str] = None
    role: str
    is_active: bool
    is_verified: bool


class SendVerificationCodeRequest(BaseModel):
    """发送验证码请求"""
    email: str
    purpose: str  # register, reset_password, change_password, bind_email


class VerifyCodeRequest(BaseModel):
    """验证验证码请求"""
    email: str
    code: str
    purpose: str


class ResetPasswordRequest(BaseModel):
    """重置密码请求"""
    email: str
    code: str
    new_password: str


class ChangePasswordWithEmailRequest(BaseModel):
    """通过邮箱验证码修改密码请求"""
    email: str
    code: str
    new_password: str


class ChatResponse(BaseModel):
    chat_id: str
    title: str
    created_at: str
    updated_at: str


class MessageResponse(BaseModel):
    message_id: str
    chat_id: str
    author_id: str
    author_name: str
    content: str
    timestamp: str
    role: Optional[str] = None


class ChatListResponse(BaseModel):
    chats: List[Dict[str, Any]]
    total: int


# ========== 辅助函数 ==========
def get_current_time() -> str:
    """获取当前时间字符串 HH:mm"""
    return datetime.now().strftime("%H:%M")


def get_timestamp() -> str:
    """获取完整时间戳 MM/DD HH:mm"""
    return datetime.now().strftime("%m/%d %H:%M")


async def get_current_user(authorization: Optional[str] = Header(None)) -> Optional[Dict[str, Any]]:
    """从请求头中获取当前用户（同步数据库查询）"""
    if not authorization:
        return None

    try:
        # Bearer token 格式
        token = authorization.replace("Bearer ", "")
        payload = decode_token(token)

        if not payload or payload.get("type") != "access":
            return None

        # 从数据库获取用户信息（如果数据库可用）- 使用同步查询
        if _db_manager and _db_manager.connection:
            try:
                with _db_manager.get_cursor() as cursor:
                    cursor.execute(
                        "SELECT user_id, username, email, avatar_url, role, is_active, is_verified FROM users WHERE user_id = %s",
                        (payload.get("user_id"),)
                    )
                    user = cursor.fetchone()
                    if user:
                        return {
                            "user_id": user["user_id"],
                            "username": user["username"],
                            "email": user["email"],
                            "avatar_url": user["avatar_url"],
                            "role": user["role"],
                            "is_active": user["is_active"],
                            "is_verified": user["is_verified"],
                        }
            except Exception as db_err:
                # 数据库查询失败，返回None
                print(f"[API] 警告: 无法从数据库获取用户信息: {db_err}")

        return None
    except Exception as e:
        print(f"[API] 获取当前用户失败: {e}")
        return None


def get_timestamp() -> str:
    """获取完整时间戳 MM/DD HH:mm"""
    return datetime.now().strftime("%m/%d %H:%M")


def get_session(chat_id: str) -> Dict[str, Any]:
    """获取或创建会话"""
    if chat_id not in sessions:
        # 尝试从数据库加载
        if _db_manager:
            load_session_from_db(chat_id)
        if chat_id not in sessions:
            raise HTTPException(status_code=404, detail="会话不存在")
    return sessions[chat_id]


def load_session_from_db(chat_id: str):
    """从数据库加载会话到内存"""
    if not _db_manager:
        return False

    try:
        # 获取线程的所有事件
        events = _db_manager.get_thread_events(chat_id)
        if not events:
            return False

        # 获取线程信息
        with _db_manager.get_cursor() as cursor:
            cursor.execute("""
                SELECT t.topic, t.user_id,
                       COALESCE(`to`.publication_status, 'draft') as publication_status,
                       COALESCE(`to`.rejection_reason, '') as rejection_reason
                FROM threads t
                LEFT JOIN thread_owners `to` ON t.thread_id = `to`.thread_id
                WHERE t.thread_id = %s
            """, (chat_id,))
            thread_info = cursor.fetchone()
            topic = thread_info.get('topic') if thread_info else "历史对话"
            thread_user_id = thread_info.get('user_id')  # 获取用户ID
            publication_status = thread_info.get('publication_status', 'draft')
            rejection_reason = thread_info.get('rejection_reason', '')

        # 初始化状态
        state = init_state(thread_id=chat_id, topic=topic)

        # 创建组织者
        organizer = OrganizerAgent()

        # 转换事件为消息格式
        role_id_map = {
            "用户": "user",
            "理论家": "theorist",
            "实践者": "practitioner",
            "质疑者": "skeptic",
            "组织者": "facilitator",
        }

        messages = []
        for event in events:
            speaker = event.get('speaker', '未知')
            content = event.get('content', '')
            created_at = event.get('created_at', '')

            # 格式化时间 - 兼容多种时间格式
            time_str = get_current_time()
            if created_at:
                try:
                    # 尝试解析不同格式的时间
                    created_at_str = str(created_at)
                    if '.' in created_at_str:
                        # 带微秒的格式
                        dt = datetime.strptime(created_at_str, "%Y-%m-%d %H:%M:%S.%f")
                    else:
                        # 不带微秒的格式
                        dt = datetime.strptime(created_at_str, "%Y-%m-%d %H:%M:%S")
                    time_str = dt.strftime("%H:%M")
                except:
                    time_str = get_current_time()

            messages.append({
                "message_id": event.get('event_id', uuid.uuid4().hex),
                "chat_id": chat_id,
                "author_id": role_id_map.get(speaker, "user"),
                "author_name": speaker,
                "content": content,
                "timestamp": time_str,
                "role": speaker,
            })

            # 更新状态（如果是用户或组织者）
            if speaker in ["用户", "组织者", "理论家", "实践者", "质疑者"]:
                advance_turn(state, speaker)

        # 存储会话
        sessions[chat_id] = {
            "chat_id": chat_id,
            "thread_id": chat_id,
            "title": topic,  # 直接使用 topic 作为 title，不添加"主题："前缀
            "topic": topic,
            "user_id": thread_user_id,  # 添加用户ID
            "is_guest": (thread_user_id is None),  # 添加游客标识
            "state": state,
            "organizer": organizer,
            "created_at": get_timestamp(),
            "updated_at": get_timestamp(),
            "messages": messages,
            "publication_status": publication_status,  # 发布状态
            "rejection_reason": rejection_reason,  # 驳回原因
        }

        print(f"[API] 从数据库加载会话: {chat_id}, {len(messages)} 条消息")
        return True

    except Exception as e:
        print(f"[API] 加载会话失败: {e}")
        return False


def load_all_sessions_from_db():
    """从数据库加载所有历史对话（只加载登录用户的对话，不加载游客的）"""
    if not _db_manager:
        return 0

    try:
        # 只加载有 user_id 的对话，不加载游客的对话（user_id 为 NULL）
        with _db_manager.get_cursor() as cursor:
            cursor.execute("""
                SELECT thread_id
                FROM threads
                WHERE user_id IS NOT NULL
                ORDER BY updated_at DESC
                LIMIT 100
            """)
            thread_ids = [row['thread_id'] for row in cursor.fetchall()]

        loaded = 0
        for thread_id in thread_ids:
            if thread_id not in sessions:
                if load_session_from_db(thread_id):
                    loaded += 1
        print(f"[API] 从数据库加载了 {loaded} 个历史对话")
        return loaded
    except Exception as e:
        print(f"[API] 批量加载会话失败: {e}")
        return 0


def generate_ai_response_in_background(
    chat_id: str,
    thread_id: str,
    topic: str,
    user_id: Optional[str],
    is_guest: bool,
    state: DiscussionState,
    organizer
):
    """后台任务：生成AI响应（不阻塞API响应）"""
    try:
        print(f"[后台任务] 开始生成AI响应: {chat_id}")

        # 获取历史记录
        history = history_store.tail(thread_id, 12) if not is_guest else []

        # 组织者路由决定下一个发言者
        decision = organizer.route(state, history)
        next_speaker = decision["next_speaker"]
        task_hint = decision["task_hint"]
        stance_hint = decision.get("stance_hint")

        # 调用智能体生成发言
        utterance = call_companion(
            speaker=next_speaker,
            state=state,
            task_hint=task_hint,
            stance_hint=stance_hint,
            tail_n=6,
        )

        # 记录发言（非游客才保存到历史）
        if not is_guest:
            history_store.record_speaker(thread_id, next_speaker, utterance)
        advance_turn(state, next_speaker)

        # 更新状态
        patch = organizer.update_from_new_public_event(state, history_store.tail(thread_id, 12) if not is_guest else [])
        apply_patch(state, patch)

        # 映射角色ID
        role_id_map = {
            "理论家": "theorist",
            "实践者": "practitioner",
            "质疑者": "skeptic",
            "组织者": "facilitator",
        }
        first_agent_id = role_id_map.get(next_speaker, "theorist")

        # 更新会话消息
        if chat_id in sessions:
            sessions[chat_id]["messages"].append({
                "message_id": uuid.uuid4().hex,
                "chat_id": chat_id,
                "author_id": first_agent_id,
                "author_name": next_speaker,
                "content": utterance,
                "timestamp": get_current_time(),
                "role": next_speaker,
            })
            sessions[chat_id]["updated_at"] = get_timestamp()

            # 通过 WebSocket 推送新消息（如果有连接）
            # 这里需要实现 WebSocket 推送逻辑

        print(f"[后台任务] AI响应生成完成: {chat_id}")
    except Exception as e:
        print(f"[后台任务] 生成AI响应失败: {chat_id}, 错误: {e}")
        import traceback
        traceback.print_exc()


def call_companion(
    speaker: str,
    state: DiscussionState,
    task_hint: str,
    stance_hint: Optional[str] = None,
    tail_n: int = 12,
) -> str:
    """调用智能体生成发言"""
    transcript_tail = history_store.tail(state.thread_id, n=tail_n)

    req = SimpleNamespace(
        thread_id=state.thread_id,
        speaker=speaker,
        state=state,
        transcript_tail=transcript_tail,
        task_hint=task_hint,
        stance_hint=stance_hint,
        style=STYLE_BY_SPEAKER[speaker],
        focus_on_latest=True,
    )

    out = TOOLS[speaker](req)
    utterance = getattr(out, "utterance", str(out))
    utterance = rewrite_if_needed(utterance)
    return utterance


def call_organizer_open(organizer: OrganizerAgent, topic: str, history_tail: list):
    """调用组织者开场（同步函数，用于在线程池中执行）"""
    return organizer.open(topic, history_tail)


async def process_user_message_in_background(chat_id: str, session: Dict[str, Any], content: str):
    """
    在后台处理用户消息并生成AI响应（非阻塞）
    处理流程：用户发言 -> 组织者路由 -> 智能体回应 -> 更新状态 -> 推送到前端
    """
    try:
        state = session["state"]
        organizer = session["organizer"]

        # 分析并选择合适的智能体回应（使用线程池执行LLM调用）
        loop = asyncio.get_event_loop()

        # 1. 调用组织者路由（如果需要）
        responder = None
        task_hint = None

        # 简单的关键词匹配不需要LLM调用
        if any(kw in content.lower() for kw in ["什么是", "如何", "怎么", "为什么", "哪些"]):
            responder = "理论家"
            task_hint = f"【用户提问】用户刚才问：\"{content}\"\n你的任务：直接回答这个具体问题，不要偏离主题。用简单的例子说明，让用户能理解。"
        elif any(kw in content.lower() for kw in ["技能", "框架", "工具", "方法", "步骤", "怎么做"]):
            responder = "实践者"
            task_hint = f"【用户需求】用户想了解：\"{content}\"\n你的任务：给出可操作的建议和具体步骤，避免空泛的理论。"
        elif any(kw in content.lower() for kw in ["对吗", "真的", "但是", "不对", "有问题"]):
            responder = "质疑者"
            task_hint = f"【用户质疑/反馈】用户说：\"{content}\"\n你的任务：认真回应用户的观点，指出可能的问题或盲点，但保持友善。"
        else:
            # 需要调用组织者路由（LLM调用）
            decision = await loop.run_in_executor(
                executor,
                lambda: organizer.route(state, history_store.tail(state.thread_id, 12))
            )
            responder = decision["next_speaker"]
            task_hint = f"【用户发言】用户刚才说：\"{content}\"\n{decision['task_hint']}\n重要：你的回应必须与用户的这个发言产生直接对话关系，不要忽略用户的需求！"

        # 2. 调用智能体回应用户（LLM调用）
        response = await loop.run_in_executor(
            executor,
            call_companion,
            responder,
            state,
            task_hint,
            None,
            8,
        )

        # 3. 记录回应
        history_store.record_speaker(state.thread_id, responder, response)
        advance_turn(state, responder)

        # 4. 更新状态（LLM调用）
        patch = await loop.run_in_executor(
            executor,
            lambda: organizer.update_from_new_public_event(state, history_store.tail(state.thread_id, 12))
        )
        apply_patch(state, patch)

        # 5. 创建AI消息
        role_id_map = {
            "理论家": "theorist",
            "实践者": "practitioner",
            "质疑者": "skeptic",
            "组织者": "facilitator",
        }

        ai_msg = {
            "message_id": uuid.uuid4().hex,
            "chat_id": chat_id,
            "author_id": role_id_map.get(responder, "theorist"),
            "author_name": responder,
            "content": response,
            "timestamp": get_current_time(),
            "role": responder,
        }

        # 6. 添加到会话
        session["messages"].append(ai_msg)
        session["updated_at"] = get_timestamp()

        # 7. 通过WebSocket推送到前端
        await send_to_websocket(chat_id, {
            "type": "new_message",
            "message": ai_msg,
            "updated_at": session["updated_at"]
        })

        print(f"[API] 用户消息的AI响应已推送到前端: chat_id={chat_id}")
    except Exception as e:
        print(f"[API] 后台处理用户消息失败: {e}")
        import traceback
        traceback.print_exc()
        # 推送错误消息到前端
        await send_to_websocket(chat_id, {
            "type": "error",
            "message": f"智能体响应失败: {str(e)}"
        })


async def process_agent_turn(chat_id: str, session: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """处理一轮智能体发言（使用线程池执行器，非阻塞）"""
    state = session["state"]
    organizer = session["organizer"]

    # 组织者动态路由
    decision = organizer.route(state, history_store.tail(state.thread_id, 12))
    next_speaker = decision["next_speaker"]
    task_hint = decision["task_hint"]
    stance_hint = decision.get("stance_hint")

    # ========== 关键修改：在线程池中运行同步的 call_companion ==========
    # 使用 run_in_executor 在独立线程中执行同步的LLM调用
    # 这样不会阻塞事件循环，其他请求可以正常处理
    loop = asyncio.get_event_loop()
    utterance = await loop.run_in_executor(
        executor,           # 线程池执行器
        call_companion,      # 要执行的同步函数
        next_speaker,        # 参数1: speaker
        state,               # 参数2: state
        task_hint,           # 参数3: task_hint
        stance_hint,         # 参数4: stance_hint
        6,                   # 参数5: tail_n
    )
    # =====================================================================

    # 记录发言
    history_store.record_speaker(state.thread_id, next_speaker, utterance)
    advance_turn(state, next_speaker)

    # 更新状态
    patch = organizer.update_from_new_public_event(state, history_store.tail(state.thread_id, 12))
    apply_patch(state, patch)

    # 映射角色ID
    role_id_map = {
        "理论家": "theorist",
        "实践者": "practitioner",
        "质疑者": "skeptic",
        "组织者": "facilitator",
    }

    return {
        "message_id": uuid.uuid4().hex,
        "chat_id": chat_id,
        "author_id": role_id_map.get(next_speaker, "theorist"),
        "author_name": next_speaker,
        "content": utterance,
        "timestamp": get_current_time(),
        "role": next_speaker,
    }


async def send_to_websocket(chat_id: str, message: dict):
    """通过WebSocket发送消息到前端"""
    if chat_id in active_websockets:
        try:
            await active_websockets[chat_id].send_json(message)
        except Exception:
            pass


# ========== API 路由 ==========

@app.on_event("startup")
async def startup_event():
    """应用启动时加载历史对话"""
    print("[API] 应用启动中...")
    load_all_sessions_from_db()
    # 启动完成后打印访问信息
    print("\n" + "="*50)
    print("[OK] 服务器启动成功！")
    print("="*50)
    print("API地址:  http://localhost:8000")
    print("API文档:  http://localhost:8000/docs")
    print("WebSocket: ws://localhost:8000/ws/chat/{chat_id}")
    print("="*50)
    print()


@app.get("/")
async def root():
    """根路径"""
    return {
        "name": "智炬五维协同学习系统 API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/api/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy"}


# ========== 用户认证 API ==========

@app.post("/api/auth/register")
async def register(request: RegisterRequest):
    """用户注册"""
    if not _db_manager:
        raise HTTPException(status_code=503, detail="数据库服务不可用，请检查MySQL服务是否已启动")

    # 验证输入
    if len(request.username) < 3:
        raise HTTPException(status_code=400, detail="用户名至少3个字符")
    if len(request.password) < 6:
        raise HTTPException(status_code=400, detail="密码至少6个字符")

    try:
        print(f"[API] 尝试注册用户: {request.username}")

        # 确保数据库连接存在
        if not _db_manager.connection:
            print("[API] 数据库未连接，尝试连接...")
            if not _db_manager.connect():
                print("[API] 数据库连接失败")
                raise HTTPException(
                    status_code=503,
                    detail="数据库连接失败，请检查MySQL服务是否已启动"
                )
            print("[API] 数据库连接成功")

        with _db_manager.get_cursor() as cursor:
            # 检查用户名是否已存在
            cursor.execute("SELECT user_id FROM users WHERE username = %s", (request.username,))
            if cursor.fetchone():
                raise HTTPException(status_code=400, detail="用户名已存在")

            # 检查邮箱是否已存在
            cursor.execute("SELECT user_id FROM users WHERE email = %s", (request.email,))
            if cursor.fetchone():
                raise HTTPException(status_code=400, detail="邮箱已被注册")

            # 验证邮箱验证码
            if not _verification_manager:
                raise HTTPException(status_code=503, detail="验证码服务不可用")

            if not _verification_manager.verify_code(request.email, request.verification_code, "register"):
                raise HTTPException(status_code=400, detail="验证码无效或已过期")

            # 创建用户
            user_id = generate_user_id()
            password_hash = hash_password(request.password)

            cursor.execute("""
                INSERT INTO users (user_id, username, email, password_hash, avatar_url, role, is_active, is_verified)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                user_id,
                request.username,
                request.email,
                password_hash,
                request.avatar_url,
                "user",  # 注册用户默认角色为 user
                True,
                True  # 邮箱已验证,设置为True
            ))

            # 生成访问令牌
            access_token = create_access_token(user_id, request.username, "user")

            print(f"[API] 注册成功: {request.username} (user_id: {user_id})")

            return {
                "message": "注册成功",
                "user": {
                    "user_id": user_id,
                    "username": request.username,
                    "email": request.email,
                    "avatar_url": request.avatar_url,
                    "role": "user",
                },
                "access_token": access_token,
            }
    except HTTPException:
        raise
    except Exception as e:
        print(f"[API] 注册异常: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"注册失败: {str(e)}"
        )


@app.post("/api/auth/login")
async def login(request: LoginRequest):
    """用户登录"""
    if not _db_manager:
        print("[API] 登录失败: 数据库管理器未初始化")
        raise HTTPException(
            status_code=503,
            detail="数据库服务不可用，请检查MySQL服务是否已启动"
        )

    try:
        print(f"[API] 尝试登录用户: {request.username}")

        # 尝试连接数据库
        if not _db_manager.connection:
            print("[API] 数据库未连接，尝试连接...")
            if not _db_manager.connect():
                print("[API] 数据库连接失败")
                raise HTTPException(
                    status_code=503,
                    detail="数据库连接失败，请检查MySQL服务是否已启动"
                )
            print("[API] 数据库连接成功")

        with _db_manager.get_cursor() as cursor:
            # 查询用户
            cursor.execute(
                "SELECT user_id, username, email, password_hash, avatar_url, role, is_active FROM users WHERE username = %s",
                (request.username,)
            )
            user = cursor.fetchone()

            if not user:
                print(f"[API] 登录失败: 用户不存在 - {request.username}")
                raise HTTPException(status_code=401, detail="用户名或密码错误")

            # 验证密码
            if not verify_password(request.password, user["password_hash"]):
                print(f"[API] 登录失败: 密码错误 - {request.username}")
                raise HTTPException(status_code=401, detail="用户名或密码错误")

            # 检查账户是否激活
            if not user["is_active"]:
                print(f"[API] 登录失败: 账户已禁用 - {request.username}")
                raise HTTPException(status_code=403, detail="账户已被禁用")

            # 更新最后登录时间
            cursor.execute(
                "UPDATE users SET last_login_at = %s WHERE user_id = %s",
                (datetime.now(), user["user_id"])
            )

            # 生成令牌
            access_token = create_access_token(user["user_id"], user["username"], user["role"])
            refresh_token = create_refresh_token(user["user_id"])

            # 保存刷新令牌到数据库
            try:
                session_id = generate_session_id()
                expires_at = datetime.now() + timedelta(days=30)
                cursor.execute(
                    "INSERT INTO user_sessions (session_id, user_id, refresh_token, expires_at) VALUES (%s, %s, %s, %s)",
                    (session_id, user["user_id"], refresh_token, expires_at)
                )
            except Exception as session_err:
                # 会话保存失败，但仍允许登录
                print(f"[API] 警告: 无法保存用户会话: {session_err}")

            print(f"[API] 登录成功: {request.username} (role: {user['role']})")

            return {
                "message": "登录成功",
                "user": {
                    "user_id": user["user_id"],
                    "username": user["username"],
                    "email": user["email"],
                    "avatar_url": user["avatar_url"],
                    "role": user["role"],
                },
                "access_token": access_token,
                "refresh_token": refresh_token,
            }
    except HTTPException:
        raise
    except Exception as e:
        print(f"[API] 登录异常: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"登录失败: {str(e)}"
        )


@app.get("/api/auth/me")
async def get_current_user_info(current_user: Optional[Dict[str, Any]] = Depends(get_current_user)):
    """获取当前用户信息"""
    if not current_user:
        return {
            "user": None,
            "role": "guest"
        }

    return {
        "user": {
            "user_id": current_user["user_id"],
            "username": current_user["username"],
            "email": current_user["email"],
            "avatar_url": current_user["avatar_url"],
            "role": current_user["role"],
        },
        "role": current_user["role"],
    }


@app.post("/api/auth/logout")
async def logout(
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user),
    authorization: Optional[str] = Header(None)
):
    """用户登出"""
    if not authorization:
        raise HTTPException(status_code=401, detail="未登录")

    try:
        token = authorization.replace("Bearer ", "")
        payload = decode_token(token)

        if payload and payload.get("user_id"):
            # 尝试删除用户的所有会话（如果数据库可用）
            if _db_manager and _db_manager.connection:
                try:
                    with _db_manager.get_cursor() as cursor:
                        cursor.execute(
                            "DELETE FROM user_sessions WHERE user_id = %s",
                            (payload.get("user_id"),)
                        )
                except Exception as session_err:
                    # 会话删除失败，但不影响登出
                    print(f"[API] 警告: 无法删除用户会话: {session_err}")

        return {"message": "登出成功"}
    except Exception as e:
        print(f"[API] 登出失败: {e}")
        raise HTTPException(status_code=500, detail="登出失败")


# ========== 用户个人信息管理 API ==========

class UpdateProfileRequest(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    avatar_url: Optional[str] = None


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


@app.put("/api/user/profile")
async def update_profile(
    request: UpdateProfileRequest,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user)
):
    """更新用户个人信息"""
    if not current_user:
        raise HTTPException(status_code=401, detail="未登录")

    if not _db_manager:
        raise HTTPException(status_code=503, detail="数据库服务不可用")

    try:
        with _db_manager.get_cursor() as cursor:
            # 构建更新字段
            update_fields = []
            params = []

            if request.username is not None:
                # 检查用户名是否已被其他用户使用
                cursor.execute(
                    "SELECT user_id FROM users WHERE username = %s AND user_id != %s",
                    (request.username, current_user["user_id"])
                )
                if cursor.fetchone():
                    raise HTTPException(status_code=400, detail="用户名已被使用")
                update_fields.append("username = %s")
                params.append(request.username)

            if request.email is not None:
                update_fields.append("email = %s")
                params.append(request.email)

            if request.avatar_url is not None:
                update_fields.append("avatar_url = %s")
                params.append(request.avatar_url)

            if not update_fields:
                raise HTTPException(status_code=400, detail="没有要更新的字段")

            # 添加更新时间和用户ID
            params.append(datetime.now())
            params.append(current_user["user_id"])

            # 执行更新
            query = f"UPDATE users SET {', '.join(update_fields)}, updated_at = %s WHERE user_id = %s"
            cursor.execute(query, params)

            # 查询更新后的用户信息
            cursor.execute(
                "SELECT user_id, username, email, avatar_url, role, is_active, is_verified FROM users WHERE user_id = %s",
                (current_user["user_id"],)
            )
            updated_user = cursor.fetchone()

            print(f"[API] 更新用户信息成功: {updated_user['username']}")

            return {
                "message": "个人信息已更新",
                "user": updated_user
            }
    except HTTPException:
        raise
    except Exception as e:
        print(f"[API] 更新个人信息失败: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="更新个人信息失败")


@app.put("/api/user/password")
async def change_password(
    request: ChangePasswordRequest,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user)
):
    """修改密码"""
    if not current_user:
        raise HTTPException(status_code=401, detail="未登录")

    if not _db_manager:
        raise HTTPException(status_code=503, detail="数据库服务不可用")

    try:
        with _db_manager.get_cursor() as cursor:
            # 查询用户当前密码
            cursor.execute(
                "SELECT password_hash FROM users WHERE user_id = %s",
                (current_user["user_id"],)
            )
            user = cursor.fetchone()

            if not user:
                raise HTTPException(status_code=404, detail="用户不存在")

            # 验证旧密码
            if not verify_password(request.old_password, user["password_hash"]):
                raise HTTPException(status_code=400, detail="当前密码错误")

            # 检查新密码长度
            if len(request.new_password) < 6:
                raise HTTPException(status_code=400, detail="新密码至少6个字符")

            # 更新密码
            new_password_hash = hash_password(request.new_password)
            cursor.execute(
                "UPDATE users SET password_hash = %s, updated_at = %s WHERE user_id = %s",
                (new_password_hash, datetime.now(), current_user["user_id"])
            )

            # 删除用户的所有会话，强制重新登录
            cursor.execute(
                "DELETE FROM user_sessions WHERE user_id = %s",
                (current_user["user_id"],)
            )

            print(f"[API] 修改密码成功: {current_user['username']}")

            return {"message": "密码已修改，请重新登录"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"[API] 修改密码失败: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="修改密码失败")


# ========== 对话管理 API ==========

@app.post("/api/chats")
async def create_chat(
    request: CreateChatRequest,
    background_tasks: BackgroundTasks,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user)
):
    """创建新对话（使用线程池生成组织者开场，避免阻塞API）"""
    thread_id = uuid.uuid4().hex[:12]
    chat_id = thread_id
    topic = request.topic
    # 生成标题时截断过长的主题，最多显示30个字符
    display_topic = topic[:30] + ("..." if len(topic) > 30 else "")
    title = request.title or f"主题：{display_topic}"
    user_id = current_user["user_id"] if current_user else None
    is_guest = (user_id is None)  # 游客标识

    # 初始化状态
    state = init_state(thread_id=thread_id, topic=topic)

    # 创建组织者
    organizer = OrganizerAgent()

    # 游客不保存到数据库，只在内存中
    if not is_guest:
        # 登录用户：记录到历史存储（会保存到数据库）
        history_store.record_user(thread_id, topic, tags=["topic"], topic=topic)
        advance_turn(state, "用户")

        # ========== 使用线程池执行组织者开场（非阻塞） ==========
        loop = asyncio.get_event_loop()
        opening, agenda_items, active_item_id = await loop.run_in_executor(
            executor,
            call_organizer_open,
            organizer,
            topic,
            history_store.tail(thread_id, 8)
        )
        # ============================================================
        opening = rewrite_if_needed(opening)
        history_store.record_speaker(thread_id, "组织者", opening, tags=["opening"])
        advance_turn(state, "组织者")

        set_agenda(state, agenda_items, active_item_id)
        state.phase = "discussion"

        # 保存用户关联到数据库
        if _db_manager:
            try:
                with _db_manager.get_cursor() as cursor:
                    # 确保 threads 表中有记录
                    cursor.execute("""
                        INSERT INTO threads (thread_id, topic, user_id, phase, turn_id, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE user_id = %s
                    """, (thread_id, topic, user_id, 'discussion', 1, datetime.now(), datetime.now(), user_id))

                    # 在 thread_owners 表中添加记录
                    cursor.execute(
                        "INSERT INTO thread_owners (thread_id, user_id, is_public) VALUES (%s, %s, %s)",
                        (thread_id, user_id, False)
                    )
            except Exception as e:
                print(f"[API] 保存用户关联失败: {e}")
    else:
        # 游客：只初始化状态，不保存到数据库
        advance_turn(state, "用户")

        # ========== 使用线程池执行组织者开场（非阻塞） ==========
        loop = asyncio.get_event_loop()
        opening, agenda_items, active_item_id = await loop.run_in_executor(
            executor,
            call_organizer_open,
            organizer,
            topic,
            []
        )
        # ============================================================
        opening = rewrite_if_needed(opening)
        advance_turn(state, "组织者")
        set_agenda(state, agenda_items, active_item_id)
        state.phase = "discussion"

    # 存储会话（立即返回，不等待AI生成）
    sessions[chat_id] = {
        "chat_id": chat_id,
        "thread_id": thread_id,
        "title": topic,  # 直接使用 topic 作为 title
        "topic": topic,
        "user_id": user_id,
        "is_guest": is_guest,
        "state": state,
        "organizer": organizer,
        "created_at": get_timestamp(),
        "updated_at": get_timestamp(),
        "messages": [
            {
                "message_id": uuid.uuid4().hex,
                "chat_id": chat_id,
                "author_id": "user",
                "author_name": "用户",
                "content": topic,
                "timestamp": get_current_time(),
                "role": "用户",
            },
            {
                "message_id": uuid.uuid4().hex,
                "chat_id": chat_id,
                "author_id": "facilitator",
                "author_name": "组织者",
                "content": opening,
                "timestamp": get_current_time(),
                "role": "组织者",
            },
        ],
        "publication_status": "draft",
        "rejection_reason": "",
    }

    # 添加后台任务：异步生成AI响应
    background_tasks.add_task(
        generate_ai_response_in_background,
        chat_id,
        thread_id,
        topic,
        user_id,
        is_guest,
        state,
        organizer
    )

    # 立即返回，不等待AI生成完成
    return {
        "chat_id": chat_id,
        "title": title,
        "topic": topic,
        "created_at": get_timestamp(),
        "messages": sessions[chat_id]["messages"],
    }


@app.get("/api/chats", response_model=ChatListResponse)
async def get_chats(
    keyword: Optional[str] = None,
    limit: int = 50,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user)
):
    """获取对话列表 - 根据用户过滤"""
    chats = []

    # 获取当前用户ID
    user_id = current_user["user_id"] if current_user else None

    # 首先从数据库获取历史对话（只获取当前用户的）
    if _db_manager and user_id:  # 只有登录用户才从数据库加载历史对话
        try:
            db_threads = _db_manager.get_threads_by_user(user_id, limit=limit)
            for thread in db_threads:
                thread_id = thread.get('thread_id')
                # 如果不在内存中，需要加载
                if thread_id not in sessions:
                    load_session_from_db(thread_id)

                # 现在从内存获取信息
                if thread_id in sessions:
                    session = sessions[thread_id]
                    chat_info = {
                        "id": session["chat_id"],
                        "title": session["title"],
                        "topic": session["topic"],
                        "pinned": False,
                        "updatedAt": session["updated_at"],
                        "messages": session["messages"],
                        "messageCount": len(session["messages"]),
                        "publicationStatus": session.get("publication_status", "draft"),
                        "rejectionReason": session.get("rejection_reason", ""),
                    }
                    # 关键词过滤
                    if keyword:
                        kw = keyword.lower()
                        if kw not in chat_info["title"].lower():
                            if session["messages"]:
                                last_msg = session["messages"][-1]["content"].lower()
                                if kw not in last_msg:
                                    continue
                    chats.append(chat_info)
        except Exception as e:
            print(f"[API] 从数据库获取对话失败: {e}")

    # 添加内存中只有的对话（未保存到数据库的）
    # 只返回当前用户的会话，游客只看到当前会话
    for chat_id, session in sessions.items():
        # 过滤：只返回当前用户的会话或游客的会话
        session_user_id = session.get("user_id")
        if session_user_id != user_id:
            continue  # 跳过不属于当前用户的会话

        if not any(c["id"] == chat_id for c in chats):
            chat_info = {
                "id": session["chat_id"],
                "title": session["title"],
                "topic": session["topic"],
                "pinned": False,
                "updatedAt": session["updated_at"],
                "messages": session["messages"],
                "messageCount": len(session["messages"]),
                "publicationStatus": session.get("publication_status", "draft"),
                "rejectionReason": session.get("rejection_reason", ""),
            }
            # 关键词过滤
            if keyword:
                kw = keyword.lower()
                if kw not in chat_info["title"].lower():
                    if session["messages"]:
                        last_msg = session["messages"][-1]["content"].lower()
                        if kw not in last_msg:
                            continue
            chats.append(chat_info)

    # 按更新时间排序
    chats.sort(key=lambda x: x["updatedAt"], reverse=True)

    return ChatListResponse(chats=chats, total=len(chats))


@app.get("/api/chats/export")
async def export_all_chats(
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user)
):
    """导出用户的所有对话为 ZIP 文件"""
    if not current_user:
        raise HTTPException(status_code=401, detail="未登录")

    if not _db_manager:
        raise HTTPException(status_code=503, detail="数据库服务不可用")

    try:
        # 查询用户的所有对话
        with _db_manager.get_cursor() as cursor:
            cursor.execute(
                """SELECT thread_id, topic, created_at, updated_at
                   FROM threads
                   WHERE user_id = %s
                   ORDER BY updated_at DESC""",
                (current_user["user_id"],)
            )
            threads = cursor.fetchall()

            if not threads:
                raise HTTPException(status_code=404, detail="没有可导出的对话")

            # 创建 ZIP 文件在内存中
            zip_buffer = io.BytesIO()

            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for thread in threads:
                    thread_id = thread["thread_id"]

                    # 获取该对话的所有消息
                    events = _db_manager.get_thread_events(thread_id)

                    # 格式化对话内容
                    content_lines = [
                        f"对话主题: {thread['topic']}",
                        f"创建时间: {thread['created_at'].strftime('%Y-%m-%d %H:%M:%S')}",
                        f"更新时间: {thread['updated_at'].strftime('%Y-%m-%d %H:%M:%S')}",
                        f"对话ID: {thread_id}",
                        "",
                        "=== 对话记录 ===",
                        ""
                    ]

                    for event in events:
                        timestamp = event.get('created_at', '').strftime('%Y-%m-%d %H:%M:%S') if event.get('created_at') else ''
                        content_lines.append(f"[{timestamp}] {event['speaker']}:")
                        content_lines.append(event['content'])
                        content_lines.append("")

                    # 添加到 ZIP
                    filename = f"{thread['topic'][:50]}_{thread_id[:8]}.txt"
                    # 确保文件名安全
                    filename = filename.replace('/', '_').replace('\\', '_').replace(':', '_')
                    zip_file.writestr(filename, '\n'.join(content_lines))

            # 准备响应
            zip_buffer.seek(0)
            zip_bytes = zip_buffer.getvalue()

            # 生成文件名: 用户名_对话记录_日期.zip
            from urllib.parse import quote
            date_str = datetime.now().strftime('%Y%m%d')
            safe_username = current_user["username"].replace('/', '_').replace('\\', '_')
            filename_ascii = f"{safe_username}_chats_{date_str}.zip"
            filename_utf8 = f"{safe_username}_对话记录_{date_str}.zip"

            # 使用 RFC 5987 编码格式支持中文文件名
            encoded_filename = quote(filename_utf8.encode('utf-8'))
            content_disposition = f"attachment; filename=\"{filename_ascii}\"; filename*=UTF-8''{encoded_filename}"

            return StreamingResponse(
                io.BytesIO(zip_bytes),
                media_type="application/zip",
                headers={
                    "Content-Disposition": content_disposition
                }
            )
    except HTTPException:
        raise
    except Exception as e:
        print(f"[API] 导出对话失败: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="导出对话失败")


@app.get("/api/chats/{chat_id}")
async def get_chat(chat_id: str):
    """获取单个对话详情"""
    session = get_session(chat_id)
    return {
        "id": session["chat_id"],
        "title": session["title"],
        "topic": session["topic"],
        "created_at": session["created_at"],
        "updated_at": session["updated_at"],
        "messages": session["messages"],
    }


@app.get("/api/chats/{chat_id}/messages")
async def get_messages(chat_id: str, limit: int = 100, before: Optional[str] = None):
    """获取对话消息列表"""
    session = get_session(chat_id)
    messages = session["messages"]

    # 返回消息、更新时间和发布状态
    return {
        "messages": messages[-limit:],
        "total": len(messages),
        "updated_at": session.get("updated_at"),
        "publication_status": session.get("publication_status", "draft"),
        "rejection_reason": session.get("rejection_reason", "")
    }


@app.post("/api/messages")
async def send_message(request: SendMessageRequest):
    """发送消息并返回AI响应（使用后台任务，非阻塞）"""
    chat_id = request.chat_id
    content = request.content.strip()
    action = request.action or "send"

    session = get_session(chat_id)
    state = session["state"]
    organizer = session["organizer"]

    # 不再处理 /end 命令 - 用户可以通过总结按钮来获取总结
    # 移除 action == "end" 的处理逻辑

    # 用户输入内容
    if content:
        # 记录用户发言
        history_store.record_user(state.thread_id, content, tags=["interject"], topic=session["topic"])
        state.last_user_interjection = content
        advance_turn(state, "用户")

        user_msg = {
            "message_id": uuid.uuid4().hex,
            "chat_id": chat_id,
            "author_id": "user",
            "author_name": "用户",
            "content": content,
            "timestamp": get_current_time(),
            "role": "用户",
        }
        session["messages"].append(user_msg)
        session["updated_at"] = get_timestamp()

        # ========== 创建后台任务处理AI响应（非阻塞） ==========
        asyncio.create_task(process_user_message_in_background(chat_id, session, content))
        # ===================================================

        # 立即返回，告诉前端AI正在处理
        return {
            "message": "智能体正在思考中，请稍候...",
            "chat_id": chat_id,
            "status": "processing",
            "messages": session["messages"],
            "updated_at": session["updated_at"]
        }

    # 处理"继续"操作 - 让下一个智能体发言
    # 创建后台任务处理智能体调用，不阻塞其他请求
    asyncio.create_task(process_agent_in_background(chat_id, session))

    # 立即返回响应，告诉前端智能体正在思考
    return {
        "message": "智能体正在思考中，请稍候...",
        "chat_id": chat_id,
        "status": "processing"
    }


@app.post("/api/chats/{chat_id}/continue")
async def continue_chat(chat_id: str):
    """让AI继续发言（非阻塞）"""
    session = get_session(chat_id)
    if not session:
        raise HTTPException(status_code=404, detail="对话不存在")

    # 创建后台任务处理智能体调用，不阻塞其他请求
    asyncio.create_task(process_agent_in_background(chat_id, session))

    # 立即返回响应，告诉前端智能体正在思考
    return {
        "message": "智能体正在思考中，请稍候...",
        "chat_id": chat_id,
        "status": "processing"
    }


async def process_agent_in_background(chat_id: str, session: Dict[str, Any]):
    """
    在后台处理智能体发言（非阻塞）
    智能体生成完成后，通过WebSocket推送结果到前端
    """
    try:
        # 处理智能体发言
        agent_msg = await process_agent_turn(chat_id, session)

        if agent_msg:
            # 将消息添加到会话
            session["messages"].append(agent_msg)
            session["updated_at"] = get_timestamp()

            # 通过WebSocket推送新消息到前端
            await send_to_websocket(chat_id, {
                "type": "new_message",
                "message": agent_msg,
                "updated_at": session["updated_at"]
            })

            print(f"[API] 智能体发言已推送到前端: chat_id={chat_id}")
        else:
            # 智能体生成失败，推送错误消息
            await send_to_websocket(chat_id, {
                "type": "error",
                "message": "智能体生成响应失败"
            })
            print(f"[API] 智能体发言生成失败: chat_id={chat_id}")
    except Exception as e:
        print(f"[API] 后台处理智能体发言失败: {e}")
        # 推送错误消息到前端
        await send_to_websocket(chat_id, {
            "type": "error",
            "message": f"智能体发言失败: {str(e)}"
        })


# ========== Pydantic 数据模型 ==========
class RenameChatRequest(BaseModel):
    title: str


@app.put("/api/chats/{chat_id}/rename")
async def rename_chat(
    chat_id: str,
    request: RenameChatRequest,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user)
):
    """重命名对话"""
    if not request.title or not request.title.strip():
        raise HTTPException(status_code=400, detail="标题不能为空")

    new_title = request.title.strip()

    # 更新内存中的会话
    if chat_id in sessions:
        sessions[chat_id]["title"] = new_title

    # 更新数据库
    if _db_manager:
        try:
            with _db_manager.get_cursor() as cursor:
                cursor.execute(
                    "UPDATE threads SET topic = %s, updated_at = %s WHERE thread_id = %s",
                    (new_title, datetime.now(), chat_id)
                )
                print(f"[API] 重命名对话: {chat_id} -> {new_title}")
        except Exception as e:
            print(f"[API] 重命名对话失败: {e}")
            raise HTTPException(status_code=500, detail="重命名失败")

    return {"message": "重命名成功", "title": new_title}


@app.get("/api/chats/{chat_id}/export")
async def export_chat(chat_id: str):
    """导出单个对话为TXT文件"""
    messages = []
    title = "对话"

    # 首先尝试从内存中获取会话
    if chat_id in sessions:
        session = sessions[chat_id]
        messages = session.get("messages", [])
        title = session.get("title", "对话")
    # 如果内存中没有，尝试从数据库加载
    elif _db_manager:
        try:
            # 获取线程信息
            with _db_manager.get_cursor() as cursor:
                cursor.execute("SELECT topic FROM threads WHERE thread_id = %s", (chat_id,))
                thread_info = cursor.fetchone()
                if thread_info:
                    title = thread_info.get("topic", "对话")

                # 获取消息
                events = _db_manager.get_thread_events(chat_id)
                if events:
                    for event in events:
                        messages.append({
                            "author_name": event.get("speaker", "未知"),
                            "authorId": event.get("speaker", "未知"),
                            "content": event.get("content", ""),
                            "text": event.get("content", ""),
                            "time": event.get("created_at", ""),
                            "timestamp": event.get("created_at", ""),
                        })
        except Exception as e:
            print(f"[API] 从数据库加载对话失败: {e}")

    if not messages:
        raise HTTPException(status_code=404, detail="对话不存在或没有消息")

    # 构建TXT内容
    lines = []
    lines.append(f"# {title}\n\n")

    for msg in messages:
        author = msg.get("author_name", msg.get("authorId", "未知"))
        content = msg.get("content", msg.get("text", ""))
        timestamp = msg.get("time", msg.get("timestamp", ""))

        # 格式化时间戳
        time_str = ""
        if timestamp:
            try:
                if isinstance(timestamp, str):
                    if '.' in timestamp:
                        dt = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S.%f")
                    else:
                        dt = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
                    time_str = dt.strftime("%H:%M")
            except Exception as e:
                print(f"[API] 时间戳格式化失败: {timestamp}, {e}")

        # 只在有时间的显示时间，否则只显示角色名
        if time_str:
            lines.append(f"[{time_str}] {author}：\n{content}\n\n")
        else:
            lines.append(f"{author}：\n{content}\n\n")

    txt_content = "".join(lines)

    # 返回文件
    from fastapi.responses import Response
    from urllib.parse import quote

    # 清理文件名中的特殊字符
    safe_title = "".join(c if c.isalnum() or c in (' ', '-', '_', '（', '）', '(', ')') else '_' for c in title)

    # 使用RFC 5987编码格式支持中文文件名
    filename_ascii = f"{safe_title}.txt"
    filename_utf8 = f"{safe_title}.txt"
    encoded_filename = quote(filename_utf8.encode('utf-8'))
    content_disposition = f"attachment; filename=\"{filename_ascii}\"; filename*=UTF-8''{encoded_filename}"

    return Response(
        content=txt_content,
        media_type="text/plain; charset=utf-8",
        headers={
            "Content-Disposition": content_disposition
        }
    )


@app.post("/api/chats/{chat_id}/summary")
async def summarize_chat(chat_id: str):
    """生成对话总结，对话继续进行（使用线程池，非阻塞）"""
    session = get_session(chat_id)
    state = session["state"]
    organizer = session["organizer"]

    # ========== 使用线程池执行组织者总结（非阻塞） ==========
    loop = asyncio.get_event_loop()
    summary = await loop.run_in_executor(
        executor,
        lambda: organizer.summarize(state, history_store.tail(state.thread_id, 20))
    )
    # ============================================================
    summary = rewrite_if_needed(summary)

    # 记录总结到历史
    history_store.record_speaker(state.thread_id, "组织者", summary, tags=["summary"])
    advance_turn(state, "组织者")

    # 添加总结消息
    summary_msg = {
        "message_id": uuid.uuid4().hex,
        "chat_id": chat_id,
        "author_id": "facilitator",
        "author_name": "组织者",
        "content": summary,
        "timestamp": get_current_time(),
        "role": "组织者",
    }
    session["messages"].append(summary_msg)
    session["updated_at"] = get_timestamp()

    # 对话继续进行，状态保持为 discussion
    # 返回消息列表（包含新增的总结消息）
    return {
        "messages": session["messages"],
        "updated_at": session["updated_at"]
    }


@app.delete("/api/chats/all")
async def delete_all_chats(
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user)
):
    """删除用户的所有对话"""
    if not current_user:
        raise HTTPException(status_code=401, detail="未登录")

    if not _db_manager:
        raise HTTPException(status_code=503, detail="数据库服务不可用")

    try:
        with _db_manager.get_cursor() as cursor:
            # 查询用户的所有对话 thread_id
            cursor.execute(
                "SELECT thread_id FROM threads WHERE user_id = %s",
                (current_user["user_id"],)
            )
            threads = cursor.fetchall()

            if not threads:
                raise HTTPException(status_code=404, detail="没有可删除的对话")

            deleted_count = 0
            threads_to_delete = []

            for thread in threads:
                thread_id = thread["thread_id"]
                threads_to_delete.append(thread_id)

                # 删除相关的所有数据（外键会自动级联删除）
                # threads 表会被删除，events 等会自动级联
                cursor.execute("DELETE FROM threads WHERE thread_id = %s", (thread_id,))
                deleted_count += 1

            print(f"[API] 从数据库删除用户所有对话: {current_user['username']}, 删除了 {deleted_count} 个对话")

            # 清除内存中的会话（只清除属于当前用户的对话）
            for chat_id in list(sessions.keys()):
                if chat_id in threads_to_delete:
                    # 清理历史记录
                    history_store.clear(chat_id)
                    # 删除会话
                    del sessions[chat_id]
                    # 关闭WebSocket连接
                    if chat_id in active_websockets:
                        try:
                            await active_websockets[chat_id].close()
                        except Exception:
                            pass
                        del active_websockets[chat_id]

            print(f"[API] 从内存清除会话: {len(threads_to_delete)} 个")

            return {
                "message": f"已删除 {deleted_count} 个对话",
                "deleted_count": deleted_count
            }
    except HTTPException:
        raise
    except Exception as e:
        print(f"[API] 删除所有对话失败: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="删除对话失败")


@app.delete("/api/chats/{chat_id}")
async def delete_chat(
    chat_id: str,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user)
):
    """删除对话"""
    # 首先检查会话是否在内存中
    if chat_id not in sessions:
        raise HTTPException(status_code=404, detail="会话不存在")

    # 获取thread_id
    thread_id = sessions[chat_id]["thread_id"]

    # 清理历史记录
    history_store.clear(thread_id)

    # 删除会话
    del sessions[chat_id]

    # 关闭WebSocket连接
    if chat_id in active_websockets:
        try:
            await active_websockets[chat_id].close()
        except Exception:
            pass
        del active_websockets[chat_id]

    # 如果数据库可用，从数据库中删除
    if _db_manager:
        try:
            with _db_manager.get_cursor() as cursor:
                # 删除相关的所有数据（外键会自动级联删除）
                cursor.execute("DELETE FROM threads WHERE thread_id = %s", (chat_id,))
                print(f"[API] 从数据库删除对话: {chat_id}")
        except Exception as e:
            print(f"[API] 删除数据库记录失败: {e}")

    return {"message": "对话已删除"}


# ========== WebSocket 路由 ==========

@app.websocket("/ws/chat/{chat_id}")
async def websocket_endpoint(websocket: WebSocket, chat_id: str):
    """WebSocket连接端点"""
    await websocket.accept()
    active_websockets[chat_id] = websocket

    try:
        while True:
            # 保持连接，接收客户端消息
            data = await websocket.receive_text()
            # 可以处理客户端发送的各种消息
            # 例如：心跳检测
    except WebSocketDisconnect:
        if chat_id in active_websockets:
            del active_websockets[chat_id]
    except Exception as e:
        if chat_id in active_websockets:
            del active_websockets[chat_id]


# ========== 管理员 API ==========

# Pydantic 模型
class BanUserRequest(BaseModel):
    reason: Optional[str] = None
    duration_days: Optional[int] = None


class UpdateRoleRequest(BaseModel):
    role: str  # 'user', 'admin', 'super_admin'


def require_admin(current_user: Optional[Dict[str, Any]] = Depends(get_current_user)):
    """验证管理员权限"""
    if not current_user:
        raise HTTPException(status_code=401, detail="未登录")
    if current_user.get("role") not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return current_user


def require_super_admin(current_user: Optional[Dict[str, Any]] = Depends(get_current_user)):
    """验证超级管理员权限"""
    if not current_user:
        raise HTTPException(status_code=401, detail="未登录")
    if current_user.get("role") != "super_admin":
        raise HTTPException(status_code=403, detail="需要超级管理员权限")
    return current_user


@app.get("/api/admin/users")
async def get_users(
    keyword: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(require_super_admin)
):
    """获取所有用户列表（仅超级管理员）"""
    if not _db_manager:
        raise HTTPException(status_code=503, detail="数据库服务不可用")

    try:
        with _db_manager.get_cursor() as cursor:
            if keyword:
                # 搜索用户
                cursor.execute("""
                    SELECT user_id, username, email, role, is_active, is_verified, created_at, updated_at
                    FROM users
                    WHERE username LIKE %s OR email LIKE %s
                    ORDER BY created_at DESC
                """, (f"%{keyword}%", f"%{keyword}%"))
            else:
                # 获取所有用户
                cursor.execute("""
                    SELECT user_id, username, email, role, is_active, is_verified, created_at, updated_at
                    FROM users
                    ORDER BY created_at DESC
                """)
            users = cursor.fetchall()

            return {"users": users, "total": len(users)}
    except Exception as e:
        print(f"[API] 获取用户列表失败: {e}")
        raise HTTPException(status_code=500, detail="获取用户列表失败")


@app.post("/api/admin/users")
async def create_user(
    user_data: dict,
    current_user: Dict[str, Any] = Depends(require_super_admin)
):
    """创建新用户（仅超级管理员）"""
    if not _db_manager:
        raise HTTPException(status_code=503, detail="数据库服务不可用")

    try:
        username = user_data.get("username")
        password = user_data.get("password")
        email = user_data.get("email")
        role = user_data.get("role", "user")
        is_active = user_data.get("is_active", True)

        # 验证输入
        if not username or not password:
            raise HTTPException(status_code=400, detail="用户名和密码不能为空")
        if len(username) < 3:
            raise HTTPException(status_code=400, detail="用户名至少3个字符")
        if len(password) < 6:
            raise HTTPException(status_code=400, detail="密码至少6个字符")
        if role not in ["user", "admin", "super_admin"]:
            raise HTTPException(status_code=400, detail="无效的角色")

        with _db_manager.get_cursor() as cursor:
            # 检查用户名是否已存在
            cursor.execute("SELECT user_id FROM users WHERE username = %s", (username,))
            if cursor.fetchone():
                raise HTTPException(status_code=400, detail="用户名已存在")

            # 检查邮箱是否已存在
            if email:
                cursor.execute("SELECT user_id FROM users WHERE email = %s", (email,))
                if cursor.fetchone():
                    raise HTTPException(status_code=400, detail="邮箱已被注册")

            # 创建用户
            user_id = generate_user_id()
            password_hash = hash_password(password)

            cursor.execute("""
                INSERT INTO users (user_id, username, email, password_hash, role, is_active, is_verified)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (user_id, username, email, password_hash, role, is_active, False))

            print(f"[API] 创建用户成功: {username} (role: {role})")

            return {
                "message": "用户创建成功",
                "user": {
                    "user_id": user_id,
                    "username": username,
                    "email": email,
                    "role": role,
                    "is_active": is_active
                }
            }
    except HTTPException:
        raise
    except Exception as e:
        print(f"[API] 创建用户失败: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"创建用户失败: {str(e)}")


@app.put("/api/admin/users/{user_id}")
async def update_user(
    user_id: str,
    user_data: dict,
    current_user: Dict[str, Any] = Depends(require_super_admin)
):
    """更新用户信息（仅超级管理员）"""
    if not _db_manager:
        raise HTTPException(status_code=503, detail="数据库服务不可用")

    try:
        with _db_manager.get_cursor() as cursor:
            # 检查用户是否存在
            cursor.execute("SELECT user_id FROM users WHERE user_id = %s", (user_id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail="用户不存在")

            # 构建更新字段
            update_fields = []
            params = []

            if "username" in user_data:
                new_username = user_data["username"]
                # 检查用户名是否已被其他用户使用
                cursor.execute(
                    "SELECT user_id FROM users WHERE username = %s AND user_id != %s",
                    (new_username, user_id)
                )
                if cursor.fetchone():
                    raise HTTPException(status_code=400, detail="用户名已被使用")
                update_fields.append("username = %s")
                params.append(new_username)

            if "email" in user_data:
                update_fields.append("email = %s")
                params.append(user_data["email"])

            if "role" in user_data:
                role = user_data["role"]
                if role not in ["user", "admin", "super_admin"]:
                    raise HTTPException(status_code=400, detail="无效的角色")
                update_fields.append("role = %s")
                params.append(role)

            if "is_active" in user_data:
                update_fields.append("is_active = %s")
                params.append(user_data["is_active"])

            if not update_fields:
                raise HTTPException(status_code=400, detail="没有要更新的字段")

            # 添加更新时间和用户ID
            params.append(datetime.now())
            params.append(user_id)

            # 执行更新
            query = f"UPDATE users SET {', '.join(update_fields)}, updated_at = %s WHERE user_id = %s"
            cursor.execute(query, params)

            print(f"[API] 更新用户成功: {user_id}")

            return {"message": "用户信息已更新"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"[API] 更新用户失败: {e}")
        raise HTTPException(status_code=500, detail="更新用户失败")


@app.delete("/api/admin/users/{user_id}")
async def delete_user(
    user_id: str,
    current_user: Dict[str, Any] = Depends(require_super_admin)
):
    """删除用户（仅超级管理员）"""
    if not _db_manager:
        raise HTTPException(status_code=503, detail="数据库服务不可用")

    try:
        # 不能删除自己
        if user_id == current_user["user_id"]:
            raise HTTPException(status_code=400, detail="不能删除自己")

        with _db_manager.get_cursor() as cursor:
            # 检查用户是否存在
            cursor.execute("SELECT username FROM users WHERE user_id = %s", (user_id,))
            user = cursor.fetchone()
            if not user:
                raise HTTPException(status_code=404, detail="用户不存在")

            # 删除用户（外键会自动级联删除相关数据）
            cursor.execute("DELETE FROM users WHERE user_id = %s", (user_id,))

            print(f"[API] 删除用户成功: {user['username']}")

            return {"message": "用户已删除"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"[API] 删除用户失败: {e}")
        raise HTTPException(status_code=500, detail="删除用户失败")


@app.put("/api/admin/users/{user_id}/ban")
async def ban_user(
    user_id: str,
    ban_data: BanUserRequest,
    current_user: Dict[str, Any] = Depends(require_super_admin)
):
    """封禁用户（仅超级管理员）"""
    if not _db_manager:
        raise HTTPException(status_code=503, detail="数据库服务不可用")

    try:
        # 不能封禁自己
        if user_id == current_user["user_id"]:
            raise HTTPException(status_code=400, detail="不能封禁自己")

        with _db_manager.get_cursor() as cursor:
            # 检查用户是否存在
            cursor.execute("SELECT username, is_active FROM users WHERE user_id = %s", (user_id,))
            user = cursor.fetchone()
            if not user:
                raise HTTPException(status_code=404, detail="用户不存在")

            if not user["is_active"]:
                raise HTTPException(status_code=400, detail="用户已被封禁")

            # 封禁用户
            cursor.execute(
                "UPDATE users SET is_active = FALSE, updated_at = %s WHERE user_id = %s",
                (datetime.now(), user_id)
            )

            print(f"[API] 封禁用户成功: {user['username']}")

            return {"message": "用户已被封禁"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"[API] 封禁用户失败: {e}")
        raise HTTPException(status_code=500, detail="封禁用户失败")


@app.put("/api/admin/users/{user_id}/unban")
async def unban_user(
    user_id: str,
    current_user: Dict[str, Any] = Depends(require_super_admin)
):
    """解禁用户（仅超级管理员）"""
    if not _db_manager:
        raise HTTPException(status_code=503, detail="数据库服务不可用")

    try:
        with _db_manager.get_cursor() as cursor:
            # 检查用户是否存在
            cursor.execute("SELECT username, is_active FROM users WHERE user_id = %s", (user_id,))
            user = cursor.fetchone()
            if not user:
                raise HTTPException(status_code=404, detail="用户不存在")

            if user["is_active"]:
                raise HTTPException(status_code=400, detail="用户状态正常")

            # 解禁用户
            cursor.execute(
                "UPDATE users SET is_active = TRUE, updated_at = %s WHERE user_id = %s",
                (datetime.now(), user_id)
            )

            print(f"[API] 解禁用户成功: {user['username']}")

            return {"message": "用户已解禁"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"[API] 解禁用户失败: {e}")
        raise HTTPException(status_code=500, detail="解禁用户失败")


@app.post("/api/chats/{chat_id}/publish")
async def publish_chat(
    chat_id: str,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user)
):
    """提交对话公开申请"""
    if not current_user:
        raise HTTPException(status_code=401, detail="未登录")

    if not _db_manager:
        raise HTTPException(status_code=503, detail="数据库服务不可用")

    try:
        with _db_manager.get_cursor() as cursor:
            # 检查对话是否存在且属于当前用户
            cursor.execute("""
                SELECT thread_id FROM threads
                WHERE thread_id = %s AND user_id = %s
            """, (chat_id, current_user["user_id"]))
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail="对话不存在或无权操作")

            # 检查thread_owners表中是否已有记录
            cursor.execute("""
                SELECT publication_status FROM thread_owners
                WHERE thread_id = %s
            """, (chat_id,))
            owner = cursor.fetchone()

            if owner:
                if owner["publication_status"] != "draft":
                    raise HTTPException(status_code=400, detail="对话已提交审核或已公开")
                # 更新为待审核状态
                cursor.execute("""
                    UPDATE thread_owners
                    SET publication_status = 'pending',
                        submitted_for_review_at = %s,
                        is_locked = TRUE
                    WHERE thread_id = %s
                """, (datetime.now(), chat_id))
            else:
                # 创建新的thread_owners记录
                cursor.execute("""
                    INSERT INTO thread_owners (thread_id, user_id, is_public, publication_status, submitted_for_review_at, is_locked)
                    VALUES (%s, %s, FALSE, 'pending', %s, TRUE)
                """, (chat_id, current_user["user_id"], datetime.now()))

            # 更新内存中的会话状态
            if chat_id in sessions:
                sessions[chat_id]["publication_status"] = "pending"
                sessions[chat_id]["rejection_reason"] = ""

            print(f"[API] 提交对话公开申请成功: {chat_id}")

            return {"message": "已提交公开申请", "status": "pending"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"[API] 提交公开申请失败: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="提交公开申请失败")


@app.get("/api/admin/publication-requests")
async def get_publication_requests(
    status: str = "pending",
    user_role: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(require_admin)
):
    """获取公开对话请求列表"""
    if not _db_manager:
        raise HTTPException(status_code=503, detail="数据库服务不可用")

    try:
        with _db_manager.get_cursor() as cursor:
            # 构建查询条件
            where_conditions = []
            params = []

            # 状态筛选 - 只查询非draft状态的记录
            if status == "all":
                # 查询所有非draft状态的记录
                where_conditions.append("(to.publication_status IN ('pending', 'published', 'rejected'))")
            else:
                # 查询特定状态的记录
                where_conditions.append("to.publication_status = %s")
                params.append(status)

            # 角色筛选（仅超级管理员）
            if current_user.get("role") == "super_admin" and user_role and user_role != "all":
                where_conditions.append("u.role = %s")
                params.append(user_role)
            # 管理员只能看到普通用户的申请
            elif current_user.get("role") == "admin":
                where_conditions.append("u.role = 'user'")

            # 执行查询
            query = f"""
                SELECT `to`.thread_id, t.topic, u.username, u.role, `to`.publication_status,
                       `to`.submitted_for_review_at, `to`.reviewed_at, `to`.reviewed_by,
                       `to`.rejection_reason
                FROM thread_owners `to`
                JOIN threads t ON `to`.thread_id = t.thread_id
                JOIN users u ON `to`.user_id = u.user_id
                WHERE {' AND '.join(where_conditions)}
                ORDER BY `to`.submitted_for_review_at DESC
            """
            cursor.execute(query, tuple(params))
            requests = cursor.fetchall()

            # 为每个请求添加消息预览
            result = []
            for req in requests:
                events = _db_manager.get_thread_events(req["thread_id"])
                messages_preview = [
                    {"author_name": e["speaker"], "content": e["content"]}
                    for e in events
                ]

                result.append({
                    "id": req["thread_id"],
                    "chat_id": req["thread_id"],
                    "chat_title": req["topic"],
                    "username": req["username"],
                    "user_role": req["role"],  # 添加用户角色
                    "status": req["publication_status"],
                    "created_at": req["submitted_for_review_at"],
                    "messages_preview": messages_preview,
                    "reject_reason": req["rejection_reason"]
                })

            return {"requests": result, "total": len(result)}
    except Exception as e:
        print(f"[API] 获取公开请求列表失败: {e}")
        raise HTTPException(status_code=500, detail="获取公开请求列表失败")


@app.post("/api/admin/publication-requests/{request_id}/review")
async def review_publication_request(
    request_id: str,
    review_data: dict,
    current_user: Dict[str, Any] = Depends(require_admin)
):
    """审核公开对话请求"""
    if not _db_manager:
        raise HTTPException(status_code=503, detail="数据库服务不可用")

    try:
        approved = review_data.get("approved", False)
        reason = review_data.get("reason", "")

        with _db_manager.get_cursor() as cursor:
            # 检查请求是否存在
            cursor.execute("""
                SELECT publication_status FROM thread_owners
                WHERE thread_id = %s
            """, (request_id,))
            owner = cursor.fetchone()
            if not owner:
                raise HTTPException(status_code=404, detail="请求不存在")

            # 允许对状态为 pending 或 published 的对话进行审核
            # 这样管理员既可以审核待发布的对话，也可以驳回已发布的对话
            if owner["publication_status"] not in ["pending", "published"]:
                raise HTTPException(status_code=400, detail="该对话当前状态不允许此操作")

            if approved:
                # 通过审核 - 保持锁定状态
                cursor.execute("""
                    UPDATE thread_owners
                    SET publication_status = 'published',
                        reviewed_at = %s,
                        reviewed_by = %s,
                        is_public = TRUE,
                        is_locked = TRUE,
                        rejection_reason = NULL
                    WHERE thread_id = %s
                """, (datetime.now(), current_user["user_id"], request_id))
                print(f"[API] 公开请求审核通过: {request_id}")
            else:
                # 驳回 - 解除锁定并设置为非公开
                cursor.execute("""
                    UPDATE thread_owners
                    SET publication_status = 'rejected',
                        reviewed_at = %s,
                        reviewed_by = %s,
                        rejection_reason = %s,
                        is_public = FALSE,
                        is_locked = FALSE
                    WHERE thread_id = %s
                """, (datetime.now(), current_user["user_id"], reason, request_id))
                print(f"[API] 公开请求审核驳回: {request_id}")

            # 更新内存中的会话状态
            if request_id in sessions:
                sessions[request_id]["publication_status"] = "published" if approved else "rejected"
                sessions[request_id]["rejection_reason"] = "" if approved else reason

            return {"message": "审核完成"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"[API] 审核公开请求失败: {e}")
        raise HTTPException(status_code=500, detail="审核公开请求失败")


# ========== 点赞相关 API ==========

# Pydantic模型
class CommentRequest(BaseModel):
    content: str

@app.post("/api/chats/{chat_id}/like")
async def like_chat(
    chat_id: str,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user)
):
    """
    点赞对话
    """
    if not _db_manager:
        raise HTTPException(status_code=503, detail="数据库未连接")

    if not current_user:
        raise HTTPException(status_code=401, detail="请先登录")

    try:
        with _db_manager.get_cursor() as cursor:
            # 检查对话是否存在
            cursor.execute("SELECT thread_id FROM threads WHERE thread_id = %s", (chat_id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail="对话不存在")

            # 检查是否已点赞
            cursor.execute(
                "SELECT id FROM thread_likes WHERE thread_id = %s AND user_id = %s",
                (chat_id, current_user['user_id'])
            )
            if cursor.fetchone():
                raise HTTPException(status_code=400, detail="已经点赞过了")

            # 添加点赞记录
            cursor.execute(
                "INSERT INTO thread_likes (thread_id, user_id) VALUES (%s, %s)",
                (chat_id, current_user['user_id'])
            )

            return {"message": "点赞成功"}

    except HTTPException:
        raise
    except Exception as e:
        print(f"[API] 点赞失败: {e}")
        raise HTTPException(status_code=500, detail="点赞失败")


@app.delete("/api/chats/{chat_id}/like")
async def unlike_chat(
    chat_id: str,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user)
):
    """
    取消点赞对话
    """
    if not _db_manager:
        raise HTTPException(status_code=503, detail="数据库未连接")

    if not current_user:
        raise HTTPException(status_code=401, detail="请先登录")

    try:
        with _db_manager.get_cursor() as cursor:
            # 检查是否已点赞
            cursor.execute(
                "SELECT id FROM thread_likes WHERE thread_id = %s AND user_id = %s",
                (chat_id, current_user['user_id'])
            )
            if not cursor.fetchone():
                raise HTTPException(status_code=400, detail="还未点赞")

            # 删除点赞记录
            cursor.execute(
                "DELETE FROM thread_likes WHERE thread_id = %s AND user_id = %s",
                (chat_id, current_user['user_id'])
            )

            return {"message": "取消点赞成功"}

    except HTTPException:
        raise
    except Exception as e:
        print(f"[API] 取消点赞失败: {e}")
        raise HTTPException(status_code=500, detail="取消点赞失败")


@app.get("/api/chats/{chat_id}/like-status")
async def get_like_status(
    chat_id: str,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user)
):
    """
    获取对话点赞状态和点赞数
    """
    if not _db_manager:
        raise HTTPException(status_code=503, detail="数据库未连接")

    try:
        with _db_manager.get_cursor() as cursor:
            # 获取点赞总数
            cursor.execute(
                "SELECT COUNT(*) as count FROM thread_likes WHERE thread_id = %s",
                (chat_id,)
            )
            result = cursor.fetchone()
            like_count = result['count'] if result else 0

            # 检查当前用户是否已点赞
            is_liked = False
            if current_user:
                cursor.execute(
                    "SELECT id FROM thread_likes WHERE thread_id = %s AND user_id = %s",
                    (chat_id, current_user['user_id'])
                )
                is_liked = cursor.fetchone() is not None

            return {
                "like_count": like_count,
                "is_liked": is_liked
            }

    except Exception as e:
        print(f"[API] 获取点赞状态失败: {e}")
        raise HTTPException(status_code=500, detail="获取点赞状态失败")


# ========== 公开对话大厅 API ==========

@app.get("/api/public/chats")
async def get_public_chat_hall(
    limit: int = 20,
    offset: int = 0,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user)
):
    """
    获取公开对话大厅列表（按点赞数和创建时间排序）
    """
    if not _db_manager:
        raise HTTPException(status_code=503, detail="数据库未连接")

    try:
        with _db_manager.get_cursor() as cursor:
            # 查询已公开的对话
            query = """
                SELECT
                    t.thread_id as id,
                    t.topic as title,
                    t.created_at,
                    u.username,
                    to_owners.publication_status,
                    COUNT(DISTINCT tl.user_id) as like_count,
                    COUNT(DISTINCT c.comment_id) as comment_count
                FROM threads t
                INNER JOIN thread_owners to_owners ON t.thread_id = to_owners.thread_id
                LEFT JOIN users u ON to_owners.user_id = u.user_id
                LEFT JOIN thread_likes tl ON t.thread_id = tl.thread_id
                LEFT JOIN comments c ON t.thread_id = c.thread_id AND c.is_deleted = 0
                WHERE to_owners.publication_status = 'published'
                GROUP BY t.thread_id, t.topic, t.created_at, u.username, to_owners.publication_status
                ORDER BY like_count DESC, t.created_at DESC
                LIMIT %s OFFSET %s
            """

            cursor.execute(query, (limit, offset))
            chats = cursor.fetchall()

            # 获取当前用户点赞的所有对话ID
            liked_thread_ids = set()
            if current_user:
                cursor.execute(
                    "SELECT DISTINCT thread_id FROM thread_likes WHERE user_id = %s",
                    (current_user['user_id'],)
                )
                liked_thread_ids = {row['thread_id'] for row in cursor.fetchall()}

            # 为每个对话添加消息预览和点赞状态
            result = []
            for chat in chats:
                events = _db_manager.get_thread_events(chat['id'])
                messages_preview = [
                    {"author_id": e.get("agent_id", "user"),
                     "author_name": e["speaker"],
                     "content": e["content"]}
                    for e in events[:3]
                ]

                result.append({
                    "id": chat['id'],
                    "title": chat['title'],
                    "username": chat['username'],
                    "created_at": chat['created_at'].isoformat() if chat['created_at'] else None,
                    "publication_status": chat['publication_status'],
                    "like_count": chat['like_count'],
                    "comment_count": chat['comment_count'],
                    "is_liked": chat['id'] in liked_thread_ids,
                    "messages_preview": messages_preview
                })

            return {"chats": result, "total": len(result)}

    except Exception as e:
        print(f"[API] 获取公开对话大厅失败: {e}")
        raise HTTPException(status_code=500, detail="获取公开对话大厅失败")


@app.get("/api/public/chats/{thread_id}/comments")
async def get_thread_comments_api(thread_id: str):
    """
    获取对话的评论列表
    """
    if not _db_manager:
        raise HTTPException(status_code=503, detail="数据库未连接")

    try:
        with _db_manager.get_cursor() as cursor:
            query = """
                SELECT
                    c.comment_id,
                    c.content,
                    c.created_at,
                    u.username
                FROM comments c
                LEFT JOIN users u ON c.user_id = u.user_id
                WHERE c.thread_id = %s AND c.is_deleted = 0
                ORDER BY c.created_at DESC
            """

            cursor.execute(query, (thread_id,))
            comments = cursor.fetchall()

            # 格式化评论数据
            result = []
            for comment in comments:
                result.append({
                    "comment_id": comment['comment_id'],
                    "content": comment['content'],
                    "created_at": comment['created_at'].isoformat() if comment['created_at'] else None,
                    "username": comment['username'] or '匿名'
                })

            return {"comments": result}

    except Exception as e:
        print(f"[API] 获取评论列表失败: {e}")
        raise HTTPException(status_code=500, detail="获取评论列表失败")


# ========== 违禁词检测 API ==========

class CheckViolationRequest(BaseModel):
    content: str

class ViolationInfo(BaseModel):
    word: str
    start: int
    end: int
    category: str
    severity: int

@app.post("/api/comments/check-violation")
async def check_violation(request_data: CheckViolationRequest):
    """
    检测评论内容是否包含违禁词
    返回所有违规词及其位置
    """
    content = request_data.content

    if not content or not content.strip():
        return {
            "has_violation": False,
            "violations": []
        }

    try:
        # 确保Trie树已加载
        if not _banned_words_trie._loaded:
            load_banned_words_to_trie()

        # 执行检测（返回所有违规词）
        violations = _banned_words_trie.search_all(content)

        return {
            "has_violation": len(violations) > 0,
            "violations": violations
        }

    except Exception as e:
        print(f"[API] 违禁词检测失败: {e}")
        import traceback
        traceback.print_exc()
        # 检测失败时不阻止评论发表
        return {
            "has_violation": False,
            "violations": []
        }


@app.post("/api/public/chats/{thread_id}/comments")
async def add_comment_api(
    thread_id: str,
    request_data: CommentRequest,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user)
):
    """
    添加评论
    """
    if not _db_manager:
        raise HTTPException(status_code=503, detail="数据库未连接")

    if not current_user:
        raise HTTPException(status_code=401, detail="请先登录")

    content = request_data.content.strip()
    if not content:
        raise HTTPException(status_code=400, detail="评论内容不能为空")

    try:
        with _db_manager.get_cursor() as cursor:
            # 检查对话是否存在且已公开
            cursor.execute("""
                SELECT publication_status FROM thread_owners
                WHERE thread_id = %s
            """, (thread_id,))

            thread_owner = cursor.fetchone()
            if not thread_owner:
                raise HTTPException(status_code=404, detail="对话不存在")

            if thread_owner['publication_status'] != 'published':
                raise HTTPException(status_code=400, detail="只能评论已公开的对话")

            # 创建评论
            comment_id = uuid.uuid4().hex[:32]
            created_at = datetime.now()

            cursor.execute("""
                INSERT INTO comments (comment_id, thread_id, user_id, content, is_deleted, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (comment_id, thread_id, current_user['user_id'], content, 0, created_at))

            return {
                "message": "评论成功",
                "comment_id": comment_id,
                "created_at": created_at.isoformat()
            }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[API] 添加评论失败: {e}")
        raise HTTPException(status_code=500, detail="添加评论失败")


# ========== 评论管理 API ==========

class DeleteCommentRequest(BaseModel):
    reason: Optional[str] = None  # 删除原因


class BatchCommentRequest(BaseModel):
    comment_ids: List[str]
    action: str  # 'restore' 或 'delete'


@app.get("/api/admin/comments")
async def get_admin_comments(
    status: Optional[str] = None,  # 'all', 'normal', 'deleted', 'violation'
    thread_id: Optional[str] = None,
    user_id: Optional[str] = None,
    keyword: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    current_user: Dict[str, Any] = Depends(require_admin)
):
    """
    获取评论列表（管理员）
    """
    if not _db_manager:
        raise HTTPException(status_code=503, detail="数据库未连接")

    try:
        with _db_manager.get_cursor() as cursor:
            # 构建查询条件
            conditions = []
            params = []

            if status == 'deleted':
                conditions.append("c.is_deleted = 1")
            elif status == 'normal':
                conditions.append("c.is_deleted = 0")
            elif status == 'violation':
                conditions.append("c.is_violation = 1")

            if thread_id:
                conditions.append("c.thread_id = %s")
                params.append(thread_id)

            if user_id:
                conditions.append("c.user_id = %s")
                params.append(user_id)

            if keyword:
                conditions.append("c.content LIKE %s")
                params.append(f"%{keyword}%")

            where_clause = " AND ".join(conditions) if conditions else "1=1"

            # 获取总数
            count_query = f"""
                SELECT COUNT(*) as total
                FROM comments c
                WHERE {where_clause}
            """
            cursor.execute(count_query, params)
            total = cursor.fetchone()['total']

            # 获取评论列表
            offset = (page - 1) * page_size
            query = f"""
                SELECT
                    c.comment_id,
                    c.thread_id,
                    c.user_id,
                    c.content,
                    c.is_deleted,
                    c.is_violation,
                    c.deleted_at,
                    c.deleted_by,
                    c.delete_reason,
                    c.created_at,
                    u.username,
                    u2.username as deleted_by_username,
                    t.topic as thread_topic
                FROM comments c
                LEFT JOIN users u ON c.user_id = u.user_id
                LEFT JOIN users u2 ON c.deleted_by = u2.user_id
                LEFT JOIN threads t ON c.thread_id = t.thread_id
                WHERE {where_clause}
                ORDER BY c.created_at DESC
                LIMIT %s OFFSET %s
            """

            cursor.execute(query, params + [page_size, offset])
            comments = cursor.fetchall()

            # 格式化结果
            result = []
            for comment in comments:
                result.append({
                    "comment_id": comment['comment_id'],
                    "thread_id": comment['thread_id'],
                    "thread_topic": comment['thread_topic'],
                    "user_id": comment['user_id'],
                    "username": comment['username'],
                    "content": comment['content'],
                    "is_deleted": bool(comment['is_deleted']),
                    "is_violation": bool(comment['is_violation']),
                    "deleted_at": comment['deleted_at'].isoformat() if comment['deleted_at'] else None,
                    "deleted_by": comment['deleted_by'],
                    "deleted_by_username": comment['deleted_by_username'],
                    "delete_reason": comment['delete_reason'],
                    "created_at": comment['created_at'].isoformat() if comment['created_at'] else None
                })

            return {
                "comments": result,
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": (total + page_size - 1) // page_size
            }

    except Exception as e:
        print(f"[API] 获取评论列表失败: {e}")
        raise HTTPException(status_code=500, detail="获取评论列表失败")


@app.delete("/api/admin/comments/{comment_id}")
async def delete_comment_admin(
    comment_id: str,
    request_data: DeleteCommentRequest,
    current_user: Dict[str, Any] = Depends(require_admin)
):
    """
    软删除评论（管理员）
    """
    if not _db_manager:
        raise HTTPException(status_code=503, detail="数据库未连接")

    try:
        with _db_manager.get_cursor() as cursor:
            # 检查评论是否存在
            cursor.execute("SELECT comment_id FROM comments WHERE comment_id = %s", (comment_id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail="评论不存在")

            # 软删除
            cursor.execute("""
                UPDATE comments
                SET is_deleted = 1,
                    deleted_at = NOW(),
                    deleted_by = %s,
                    delete_reason = %s
                WHERE comment_id = %s
            """, (current_user['user_id'], request_data.reason, comment_id))

            return {"message": "评论已删除"}

    except HTTPException:
        raise
    except Exception as e:
        print(f"[API] 删除评论失败: {e}")
        raise HTTPException(status_code=500, detail="删除评论失败")


@app.delete("/api/comments/{comment_id}")
async def delete_comment_user(
    comment_id: str,
    request_data: DeleteCommentRequest,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user)
):
    """
    用户删除自己的评论
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="请先登录")

    if not _db_manager:
        raise HTTPException(status_code=503, detail="数据库未连接")

    try:
        with _db_manager.get_cursor() as cursor:
            # 检查评论是否存在且属于当前用户
            cursor.execute(
                "SELECT comment_id, user_id, is_deleted FROM comments WHERE comment_id = %s",
                (comment_id,)
            )
            comment = cursor.fetchone()

            if not comment:
                raise HTTPException(status_code=404, detail="评论不存在")

            if comment['user_id'] != current_user['user_id']:
                raise HTTPException(status_code=403, detail="无权删除此评论")

            if comment['is_deleted']:
                raise HTTPException(status_code=400, detail="评论已被删除")

            # 软删除
            cursor.execute("""
                UPDATE comments
                SET is_deleted = 1,
                    deleted_at = NOW(),
                    deleted_by = %s,
                    delete_reason = %s
                WHERE comment_id = %s
            """, (current_user['user_id'], request_data.reason, comment_id))

            return {"message": "评论已删除"}

    except HTTPException:
        raise
    except Exception as e:
        print(f"[API] 删除评论失败: {e}")
        raise HTTPException(status_code=500, detail="删除评论失败")


@app.put("/api/admin/comments/{comment_id}/restore")
async def restore_comment(
    comment_id: str,
    current_user: Dict[str, Any] = Depends(require_admin)
):
    """
    恢复已删除评论
    """
    if not _db_manager:
        raise HTTPException(status_code=503, detail="数据库未连接")

    try:
        with _db_manager.get_cursor() as cursor:
            # 检查评论是否存在且已删除
            cursor.execute(
                "SELECT comment_id, is_deleted FROM comments WHERE comment_id = %s",
                (comment_id,)
            )
            comment = cursor.fetchone()
            if not comment:
                raise HTTPException(status_code=404, detail="评论不存在")
            if not comment['is_deleted']:
                raise HTTPException(status_code=400, detail="评论未被删除")

            # 恢复评论
            cursor.execute("""
                UPDATE comments
                SET is_deleted = 0,
                    deleted_at = NULL,
                    deleted_by = NULL,
                    delete_reason = NULL
                WHERE comment_id = %s
            """, (comment_id,))

            return {"message": "评论已恢复"}

    except HTTPException:
        raise
    except Exception as e:
        print(f"[API] 恢复评论失败: {e}")
        raise HTTPException(status_code=500, detail="恢复评论失败")


@app.post("/api/admin/comments/batch")
async def batch_comments_action(
    request_data: BatchCommentRequest,
    current_user: Dict[str, Any] = Depends(require_admin)
):
    """
    批量操作评论
    """
    if not _db_manager:
        raise HTTPException(status_code=503, detail="数据库未连接")

    if request_data.action not in ['restore', 'delete']:
        raise HTTPException(status_code=400, detail="无效的操作")

    try:
        with _db_manager.get_cursor() as cursor:
            if request_data.action == 'restore':
                # 批量恢复
                placeholders = ','.join(['%s'] * len(request_data.comment_ids))
                cursor.execute(f"""
                    UPDATE comments
                    SET is_deleted = 0,
                        deleted_at = NULL,
                        deleted_by = NULL,
                        delete_reason = NULL
                    WHERE comment_id IN ({placeholders})
                """, request_data.comment_ids)
                return {"message": f"已恢复 {cursor.rowcount} 条评论"}

            elif request_data.action == 'delete':
                # 批量删除
                placeholders = ','.join(['%s'] * len(request_data.comment_ids))
                cursor.execute(f"""
                    UPDATE comments
                    SET is_deleted = 1,
                        deleted_at = NOW(),
                        deleted_by = %s
                    WHERE comment_id IN ({placeholders})
                """, [current_user['user_id']] + request_data.comment_ids)
                return {"message": f"已删除 {cursor.rowcount} 条评论"}

    except Exception as e:
        print(f"[API] 批量操作失败: {e}")
        raise HTTPException(status_code=500, detail="批量操作失败")


@app.get("/api/admin/comments/stats")
async def get_comments_stats(
    current_user: Dict[str, Any] = Depends(require_admin)
):
    """
    获取评论统计数据
    """
    if not _db_manager:
        raise HTTPException(status_code=503, detail="数据库未连接")

    try:
        with _db_manager.get_cursor() as cursor:
            # 总评论数
            cursor.execute("SELECT COUNT(*) as count FROM comments")
            total = cursor.fetchone()['count']

            # 正常评论数
            cursor.execute("SELECT COUNT(*) as count FROM comments WHERE is_deleted = 0")
            normal = cursor.fetchone()['count']

            # 已删除评论数
            cursor.execute("SELECT COUNT(*) as count FROM comments WHERE is_deleted = 1")
            deleted = cursor.fetchone()['count']

            # 违规评论数
            cursor.execute("SELECT COUNT(*) as count FROM comments WHERE is_violation = 1")
            violation = cursor.fetchone()['count']

            # 今日评论数
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM comments
                WHERE DATE(created_at) = CURDATE()
            """)
            today = cursor.fetchone()['count']

            return {
                "total": total,
                "normal": normal,
                "deleted": deleted,
                "violation": violation,
                "today": today
            }

    except Exception as e:
        print(f"[API] 获取评论统计失败: {e}")
        raise HTTPException(status_code=500, detail="获取评论统计失败")


@app.get("/api/admin/dashboard-stats")
async def get_dashboard_stats(
    current_user: Dict[str, Any] = Depends(require_admin)
):
    """
    获取数据看板统计数据
    """
    if not _db_manager:
        raise HTTPException(status_code=503, detail="数据库未连接")

    try:
        with _db_manager.get_cursor() as cursor:
            # 用户总数
            cursor.execute("SELECT COUNT(*) as count FROM users WHERE role = 'user'")
            user_count = cursor.fetchone()['count']

            # 管理员总数（admin + super_admin）
            cursor.execute("SELECT COUNT(*) as count FROM users WHERE role IN ('admin', 'super_admin')")
            admin_count = cursor.fetchone()['count']

            # 总对话数量
            cursor.execute("SELECT COUNT(*) as count FROM threads")
            thread_count = cursor.fetchone()['count']

            # 已发布对话数量
            cursor.execute("SELECT COUNT(*) as count FROM thread_owners WHERE publication_status = 'published'")
            published_count = cursor.fetchone()['count']

            # 违规对话数量
            cursor.execute("SELECT COUNT(*) as count FROM thread_owners WHERE publication_status = 'rejected'")
            violation_count = cursor.fetchone()['count']

            # 评论总数
            cursor.execute("SELECT COUNT(*) as count FROM comments")
            comment_count = cursor.fetchone()['count']

            # 今日活跃用户数（今日有评论、对话或登录的用户）
            cursor.execute("""
                SELECT COUNT(DISTINCT user_id) as count
                FROM (
                    SELECT user_id FROM threads WHERE DATE(created_at) = CURDATE()
                    UNION
                    SELECT user_id FROM comments WHERE DATE(created_at) = CURDATE()
                    UNION
                    SELECT user_id FROM user_sessions WHERE DATE(created_at) = CURDATE()
                ) AS active_users
                WHERE user_id IS NOT NULL AND user_id != ''
            """)
            active_users_today = cursor.fetchone()['count']

            # 公开对话总数
            public_chat_count = published_count

            return {
                "user_count": user_count,
                "admin_count": admin_count,
                "thread_count": thread_count,
                "published_count": published_count,
                "violation_count": violation_count,
                "comment_count": comment_count,
                "active_users_today": active_users_today,
                "public_chat_count": public_chat_count,
            }

    except Exception as e:
        print(f"[API] 获取数据看板统计失败: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="获取数据看板统计失败")


@app.get("/api/admin/top-public-chats")
async def get_top_public_chats(
    limit: int = 3,
    current_user: Dict[str, Any] = Depends(require_admin)
):
    """
    获取点赞最高的公开对话
    """
    if not _db_manager:
        raise HTTPException(status_code=503, detail="数据库未连接")

    try:
        with _db_manager.get_cursor() as cursor:
            query = """
                SELECT
                    t.thread_id as id,
                    t.topic as title,
                    u.username,
                    towner.publication_status,
                    COUNT(tl.id) as like_count,
                    towner.reviewed_at
                FROM threads t
                INNER JOIN thread_owners towner ON t.thread_id = towner.thread_id
                LEFT JOIN users u ON towner.user_id = u.user_id
                LEFT JOIN thread_likes tl ON t.thread_id = tl.thread_id
                WHERE towner.publication_status = 'published'
                GROUP BY t.thread_id, t.topic, u.username, towner.publication_status, towner.reviewed_at
                ORDER BY like_count DESC, towner.reviewed_at DESC
                LIMIT %s
            """

            cursor.execute(query, (limit,))
            chats = cursor.fetchall()

            result = []
            for chat in chats:
                result.append({
                    "id": chat['id'],
                    "title": chat['title'],
                    "username": chat['username'],
                    "like_count": chat['like_count'],
                    "publication_status": chat['publication_status'],
                })

            return {
                "chats": result
            }

    except Exception as e:
        print(f"[API] 获取热门对话失败: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="获取热门对话失败")


# ========== 违禁词管理 API ==========

class BannedWordRequest(BaseModel):
    word: str
    category: Optional[str] = "其他"
    severity: Optional[int] = 1


class UpdateBannedWordRequest(BaseModel):
    word: Optional[str] = None
    category: Optional[str] = None
    severity: Optional[int] = None
    is_active: Optional[bool] = None


@app.get("/api/admin/banned-words")
async def get_banned_words(
    keyword: Optional[str] = None,
    category: Optional[str] = None,
    severity: Optional[int] = None,
    is_active: Optional[bool] = None,
    current_user: Dict[str, Any] = Depends(require_admin)
):
    """
    获取违禁词列表（无分页，返回所有数据）
    """
    if not _db_manager:
        raise HTTPException(status_code=503, detail="数据库未连接")

    try:
        with _db_manager.get_cursor() as cursor:
            # 构建查询条件
            conditions = []
            params = []

            if keyword:
                conditions.append("word LIKE %s")
                params.append(f"%{keyword}%")

            if category:
                conditions.append("category = %s")
                params.append(category)

            if severity is not None:
                conditions.append("severity = %s")
                params.append(severity)

            if is_active is not None:
                conditions.append("is_active = %s")
                params.append(int(is_active))

            where_clause = " AND ".join(conditions) if conditions else "1=1"

            # 获取所有违禁词列表（无分页）
            query = f"""
                SELECT
                    f.word_id, f.word, f.category, f.severity, f.is_active,
                    f.created_at, f.created_by, f.updated_at,
                    u.username as created_by_username
                FROM forbidden_words f
                LEFT JOIN users u ON f.created_by = u.user_id
                WHERE {where_clause}
                ORDER BY f.created_at DESC
            """

            cursor.execute(query, params)
            words = cursor.fetchall()

            # 格式化结果
            result = []
            for word in words:
                result.append({
                    "word_id": word['word_id'],
                    "word": word['word'],
                    "category": word['category'],
                    "severity": word['severity'],
                    "is_active": bool(word['is_active']),
                    "created_at": word['created_at'].isoformat() if word['created_at'] else None,
                    "created_by": word['created_by'],
                    "created_by_username": word['created_by_username'],
                    "updated_at": word['updated_at'].isoformat() if word['updated_at'] else None
                })

            print(f"[API] 获取违禁词列表成功，共 {len(result)} 条")

            return {
                "words": result,
                "total": len(result)
            }

    except Exception as e:
        print(f"[API] 获取违禁词列表失败: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="获取违禁词列表失败")


@app.post("/api/admin/banned-words")
async def create_banned_word(
    request_data: BannedWordRequest,
    current_user: Dict[str, Any] = Depends(require_admin)
):
    """
    添加违禁词
    """
    if not _db_manager:
        raise HTTPException(status_code=503, detail="数据库未连接")

    word = request_data.word.strip()
    if not word:
        raise HTTPException(status_code=400, detail="违禁词不能为空")

    try:
        with _db_manager.get_cursor() as cursor:
            # 检查是否已存在
            cursor.execute("SELECT word_id FROM forbidden_words WHERE word = %s", (word,))
            if cursor.fetchone():
                raise HTTPException(status_code=400, detail="该违禁词已存在")

            # 创建违禁词 - 使用自增ID，不需要手动指定word_id
            cursor.execute("""
                INSERT INTO forbidden_words (word, category, severity, is_active, created_by)
                VALUES (%s, %s, %s, %s, %s)
            """, (word, request_data.category, request_data.severity, 1, current_user['user_id']))

            # 重新加载违禁词到Trie树，确保新添加的违禁词立即生效
            reload_banned_words()

            return {
                "message": "违禁词添加成功"
            }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[API] 添加违禁词失败: {e}")
        raise HTTPException(status_code=500, detail="添加违禁词失败")


@app.put("/api/admin/banned-words/{word_id}")
async def update_banned_word(
    word_id: str,
    request_data: UpdateBannedWordRequest,
    current_user: Dict[str, Any] = Depends(require_admin)
):
    """
    更新违禁词
    """
    if not _db_manager:
        raise HTTPException(status_code=503, detail="数据库未连接")

    try:
        with _db_manager.get_cursor() as cursor:
            # 检查是否存在
            cursor.execute("SELECT word FROM forbidden_words WHERE word_id = %s", (word_id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail="违禁词不存在")

            # 构建更新语句
            updates = []
            params = []

            if request_data.word is not None:
                word = request_data.word.strip()
                if not word:
                    raise HTTPException(status_code=400, detail="违禁词不能为空")
                # 检查新词是否已被其他记录使用
                cursor.execute("SELECT word_id FROM forbidden_words WHERE word = %s AND word_id != %s",
                             (word, word_id))
                if cursor.fetchone():
                    raise HTTPException(status_code=400, detail="该违禁词已存在")
                updates.append("word = %s")
                params.append(word)

            if request_data.category is not None:
                updates.append("category = %s")
                params.append(request_data.category)

            if request_data.severity is not None:
                updates.append("severity = %s")
                params.append(request_data.severity)

            if request_data.is_active is not None:
                updates.append("is_active = %s")
                params.append(int(request_data.is_active))

            if not updates:
                raise HTTPException(status_code=400, detail="没有需要更新的字段")

            params.append(word_id)
            query = f"UPDATE forbidden_words SET {', '.join(updates)} WHERE word_id = %s"
            cursor.execute(query, params)

            # 重新加载违禁词到Trie树，确保更新的违禁词立即生效
            reload_banned_words()

            return {"message": "违禁词更新成功"}

    except HTTPException:
        raise
    except Exception as e:
        print(f"[API] 更新违禁词失败: {e}")
        raise HTTPException(status_code=500, detail="更新违禁词失败")


@app.delete("/api/admin/banned-words/{word_id}")
async def delete_banned_word(
    word_id: str,
    current_user: Dict[str, Any] = Depends(require_admin)
):
    """
    删除违禁词
    """
    if not _db_manager:
        raise HTTPException(status_code=503, detail="数据库未连接")

    try:
        with _db_manager.get_cursor() as cursor:
            # 检查是否存在
            cursor.execute("SELECT word FROM forbidden_words WHERE word_id = %s", (word_id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail="违禁词不存在")

            # 删除
            cursor.execute("DELETE FROM forbidden_words WHERE word_id = %s", (word_id,))

            # 重新加载违禁词到Trie树，确保删除的违禁词立即生效
            reload_banned_words()

            return {"message": "违禁词已删除"}

    except HTTPException:
        raise
    except Exception as e:
        print(f"[API] 删除违禁词失败: {e}")
        raise HTTPException(status_code=500, detail="删除违禁词失败")


# ========== 邮箱验证相关 API ==========

@app.post("/api/auth/send-verification-code")
async def send_verification_code(request: SendVerificationCodeRequest):
    """
    发送验证码到邮箱

    用途:
    - register: 注册验证
    - reset_password: 重置密码
    - change_password: 修改密码
    - bind_email: 绑定邮箱
    """
    print(f"[API] 收到发送验证码请求: {request.email}, 用途: {request.purpose}")

    if not _verification_manager:
        raise HTTPException(status_code=503, detail="验证码服务不可用")

    # 验证邮箱格式
    if "@" not in request.email or "." not in request.email:
        raise HTTPException(status_code=400, detail="邮箱格式不正确")

    # 验证purpose参数
    valid_purposes = ["register", "reset_password", "change_password", "bind_email"]
    if request.purpose not in valid_purposes:
        raise HTTPException(status_code=400, detail="无效的验证码用途")

    try:
        # 检查发送频率限制
        if not _verification_manager.check_rate_limit(request.email, request.purpose, 60):
            print(f"[API] 发送频率限制触发: {request.email}")
            raise HTTPException(status_code=429, detail="发送过于频繁，请60秒后再试")

        # 生成验证码
        print(f"[API] 开始生成验证码: {request.email}")
        code = _verification_manager.create_verification_code(
            email=request.email,
            purpose=request.purpose,
            expiry_minutes=10
        )

        if not code:
            print(f"[API] 验证码生成失败")
            raise HTTPException(status_code=500, detail="生成验证码失败")

        print(f"[API] 验证码生成成功: {code}")

        # 发送邮件
        print(f"[API] 开始发送邮件: {request.email}")
        success = email_service.send_verification_code(
            recipient_email=request.email,
            code=code,
            purpose=request.purpose
        )

        print(f"[API] 邮件发送结果: {success}")

        if not success:
            print(f"[API] 邮件发送失败")
            raise HTTPException(status_code=500, detail="发送邮件失败")

        print(f"[API] 验证码发送成功: {request.email}")
        return {
            "message": "验证码已发送",
            "email": request.email,
            "expires_in": 600  # 10分钟 = 600秒
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[API] 发送验证码失败: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"发送验证码失败: {str(e)}")


@app.post("/api/auth/verify-code")
async def verify_code(request: VerifyCodeRequest):
    """
    验证验证码是否有效
    """
    if not _verification_manager:
        raise HTTPException(status_code=503, detail="验证码服务不可用")

    try:
        is_valid = _verification_manager.verify_code(
            email=request.email,
            code=request.code,
            purpose=request.purpose
        )

        if not is_valid:
            raise HTTPException(status_code=400, detail="验证码无效或已过期")

        return {
            "message": "验证码有效",
            "valid": True
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[API] 验证验证码失败: {e}")
        raise HTTPException(status_code=500, detail=f"验证失败: {str(e)}")


@app.post("/api/auth/reset-password")
async def reset_password(request: ResetPasswordRequest):
    """
    通过邮箱验证码重置密码
    """
    if not _verification_manager or not _db_manager:
        raise HTTPException(status_code=503, detail="服务不可用")

    # 验证密码长度
    if len(request.new_password) < 6:
        raise HTTPException(status_code=400, detail="密码至少6个字符")

    try:
        # 验证验证码
        if not _verification_manager.verify_code(
            email=request.email,
            code=request.code,
            purpose="reset_password"
        ):
            raise HTTPException(status_code=400, detail="验证码无效或已过期")

        # 查找用户
        with _db_manager.get_cursor() as cursor:
            cursor.execute("SELECT user_id FROM users WHERE email = %s", (request.email,))
            user = cursor.fetchone()

            if not user:
                raise HTTPException(status_code=404, detail="该邮箱未注册")

            user_id = user["user_id"]

            # 更新密码
            password_hash = hash_password(request.new_password)
            cursor.execute(
                "UPDATE users SET password_hash = %s WHERE user_id = %s",
                (password_hash, user_id)
            )

            print(f"[API] 用户 {user_id} 通过邮箱重置密码成功")

            return {"message": "密码重置成功"}

    except HTTPException:
        raise
    except Exception as e:
        print(f"[API] 重置密码失败: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"重置密码失败: {str(e)}")


@app.put("/api/user/change-password-with-email")
async def change_password_with_email(
    request: ChangePasswordWithEmailRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    已登录用户通过邮箱验证码修改密码
    """
    if not _verification_manager or not _db_manager:
        raise HTTPException(status_code=503, detail="服务不可用")

    if not current_user:
        raise HTTPException(status_code=401, detail="请先登录")

    # 验证密码长度
    if len(request.new_password) < 6:
        raise HTTPException(status_code=400, detail="密码至少6个字符")

    try:
        # 验证邮箱是否属于当前用户
        if current_user.get("email") != request.email:
            raise HTTPException(status_code=400, detail="邮箱与当前用户不匹配")

        # 验证验证码
        if not _verification_manager.verify_code(
            email=request.email,
            code=request.code,
            purpose="change_password"
        ):
            raise HTTPException(status_code=400, detail="验证码无效或已过期")

        # 更新密码
        user_id = current_user["user_id"]
        password_hash = hash_password(request.new_password)

        with _db_manager.get_cursor() as cursor:
            cursor.execute(
                "UPDATE users SET password_hash = %s WHERE user_id = %s",
                (password_hash, user_id)
            )

            print(f"[API] 用户 {user_id} 通过邮箱验证码修改密码成功")

            return {"message": "密码修改成功"}

    except HTTPException:
        raise
    except Exception as e:
        print(f"[API] 修改密码失败: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"修改密码失败: {str(e)}")


# ========== 异常处理 ==========

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """全局异常处理"""
    return JSONResponse(
        status_code=500,
        content={"message": f"服务器错误: {str(exc)}"},
    )


# ========== 启动说明 ==========
if __name__ == "__main__":
    import uvicorn

    print("=== 智炬五维协同学习系统 API 服务器 ===")
    print("正在启动服务器...")
    print()

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
