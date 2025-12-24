# dev/api/server.py
"""
智炬五维协同学习系统 - FastAPI 后端服务器
提供RESTful API接口供前端调用
"""
from __future__ import annotations

import os
import sys
import uuid
import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from fastapi.responses import JSONResponse

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
try:
    from dev.mysql.db_utils import DatabaseManager
    _db_manager = DatabaseManager.from_config()
    if _db_manager.connect():
        print("[API] 数据库连接成功，将支持历史对话加载")
    else:
        print("[API] 数据库连接失败，仅使用内存存储")
        _db_manager = None
except Exception as e:
    print(f"[API] 数据库初始化失败: {e}，仅使用内存存储")
    _db_manager = None

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
    email: Optional[str] = None
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
    """从请求头中获取当前用户"""
    if not authorization:
        return None

    try:
        # Bearer token 格式
        token = authorization.replace("Bearer ", "")
        payload = decode_token(token)

        if not payload or payload.get("type") != "access":
            return None

        # 从数据库获取用户信息
        if _db_manager:
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
            cursor.execute("SELECT topic FROM threads WHERE thread_id = %s", (chat_id,))
            thread_info = cursor.fetchone()
            topic = thread_info.get('topic') if thread_info else "历史对话"

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
            "title": f"主题：{topic}",
            "topic": topic,
            "state": state,
            "organizer": organizer,
            "created_at": get_timestamp(),
            "updated_at": get_timestamp(),
            "messages": messages,
        }

        print(f"[API] 从数据库加载会话: {chat_id}, {len(messages)} 条消息")
        return True

    except Exception as e:
        print(f"[API] 加载会话失败: {e}")
        return False


def load_all_sessions_from_db():
    """从数据库加载所有历史对话"""
    if not _db_manager:
        return 0

    try:
        threads = _db_manager.get_latest_threads(limit=100)
        loaded = 0
        for thread in threads:
            thread_id = thread.get('thread_id')
            if thread_id and thread_id not in sessions:
                if load_session_from_db(thread_id):
                    loaded += 1
        print(f"[API] 从数据库加载了 {loaded} 个历史对话")
        return loaded
    except Exception as e:
        print(f"[API] 批量加载会话失败: {e}")
        return 0


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


async def process_agent_turn(chat_id: str, session: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """处理一轮智能体发言"""
    state = session["state"]
    organizer = session["organizer"]

    # 组织者动态路由
    decision = organizer.route(state, history_store.tail(state.thread_id, 12))
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
        raise HTTPException(status_code=500, detail="数据库未连接")

    # 验证输入
    if len(request.username) < 3:
        raise HTTPException(status_code=400, detail="用户名至少3个字符")
    if len(request.password) < 6:
        raise HTTPException(status_code=400, detail="密码至少6个字符")

    try:
        with _db_manager.get_cursor() as cursor:
            # 检查用户名是否已存在
            cursor.execute("SELECT user_id FROM users WHERE username = %s", (request.username,))
            if cursor.fetchone():
                raise HTTPException(status_code=400, detail="用户名已存在")

            # 检查邮箱是否已存在
            if request.email:
                cursor.execute("SELECT user_id FROM users WHERE email = %s", (request.email,))
                if cursor.fetchone():
                    raise HTTPException(status_code=400, detail="邮箱已被注册")

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
                False
            ))

            # 生成访问令牌
            access_token = create_access_token(user_id, request.username, "user")

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
        print(f"[API] 注册失败: {e}")
        raise HTTPException(status_code=500, detail="注册失败")


@app.post("/api/auth/login")
async def login(request: LoginRequest):
    """用户登录"""
    if not _db_manager:
        raise HTTPException(status_code=500, detail="数据库未连接")

    try:
        with _db_manager.get_cursor() as cursor:
            # 查询用户
            cursor.execute(
                "SELECT user_id, username, email, password_hash, avatar_url, role, is_active FROM users WHERE username = %s",
                (request.username,)
            )
            user = cursor.fetchone()

            if not user:
                raise HTTPException(status_code=401, detail="用户名或密码错误")

            # 验证密码
            if not verify_password(request.password, user["password_hash"]):
                raise HTTPException(status_code=401, detail="用户名或密码错误")

            # 检查账户是否激活
            if not user["is_active"]:
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
            session_id = generate_session_id()
            expires_at = datetime.now() + timedelta(days=30)
            cursor.execute(
                "INSERT INTO user_sessions (session_id, user_id, refresh_token, expires_at) VALUES (%s, %s, %s, %s)",
                (session_id, user["user_id"], refresh_token, expires_at)
            )

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
        print(f"[API] 登录失败: {e}")
        raise HTTPException(status_code=500, detail="登录失败")


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
            # 删除用户的所有会话
            if _db_manager:
                with _db_manager.get_cursor() as cursor:
                    cursor.execute(
                        "DELETE FROM user_sessions WHERE user_id = %s",
                        (payload.get("user_id"),)
                    )

        return {"message": "登出成功"}
    except Exception as e:
        print(f"[API] 登出失败: {e}")
        raise HTTPException(status_code=500, detail="登出失败")


# ========== 对话管理 API ==========

@app.post("/api/chats")
async def create_chat(
    request: CreateChatRequest,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user)
):
    """创建新对话"""
    thread_id = uuid.uuid4().hex[:12]
    chat_id = thread_id
    topic = request.topic
    title = request.title or f"主题：{topic}"
    user_id = current_user["user_id"] if current_user else None

    # 初始化状态
    state = init_state(thread_id=thread_id, topic=topic)

    # 创建组织者
    organizer = OrganizerAgent()

    # 记录用户话题
    history_store.record_user(thread_id, topic, tags=["topic"], topic=topic)
    advance_turn(state, "用户")

    # 组织者开场
    opening, agenda_items, active_item_id = organizer.open(topic, history_store.tail(thread_id, 8))
    opening = rewrite_if_needed(opening)
    history_store.record_speaker(thread_id, "组织者", opening, tags=["opening"])
    advance_turn(state, "组织者")

    set_agenda(state, agenda_items, active_item_id)
    state.phase = "discussion"

    # 保存用户关联到数据库
    if user_id and _db_manager:
        try:
            with _db_manager.get_cursor() as cursor:
                # 更新 threads 表的 user_id
                cursor.execute(
                    "UPDATE threads SET user_id = %s WHERE thread_id = %s",
                    (user_id, thread_id)
                )
                # 在 thread_owners 表中添加记录
                cursor.execute(
                    "INSERT INTO thread_owners (thread_id, user_id, is_public) VALUES (%s, %s, %s)",
                    (thread_id, user_id, False)
                )
        except Exception as e:
            print(f"[API] 保存用户关联失败: {e}")

    # 存储会话
    sessions[chat_id] = {
        "chat_id": chat_id,
        "thread_id": thread_id,
        "title": title,
        "topic": topic,
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
    }

    return {
        "chat_id": chat_id,
        "title": title,
        "created_at": sessions[chat_id]["created_at"],
        "updated_at": sessions[chat_id]["updated_at"],
        "messages": sessions[chat_id]["messages"],
    }


@app.get("/api/chats", response_model=ChatListResponse)
async def get_chats(keyword: Optional[str] = None, limit: int = 50):
    """获取对话列表 - 从数据库和内存合并获取"""
    chats = []

    # 首先从数据库获取历史对话
    if _db_manager:
        try:
            db_threads = _db_manager.get_latest_threads(limit=limit)
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
    for chat_id, session in sessions.items():
        if not any(c["id"] == chat_id for c in chats):
            chat_info = {
                "id": session["chat_id"],
                "title": session["title"],
                "topic": session["topic"],
                "pinned": False,
                "updatedAt": session["updated_at"],
                "messages": session["messages"],
                "messageCount": len(session["messages"]),
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

    return ChatListResponse(chats=chats[:limit], total=len(chats))


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

    # 简单的分页（before未实现，可以后续扩展）
    return {"messages": messages[-limit:], "total": len(messages)}


@app.post("/api/messages")
async def send_message(request: SendMessageRequest):
    """发送消息并返回AI响应"""
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

        # 如果用户输入了内容，分析并选择合适的智能体回应
        # 增强提示词，强调必须回应用户的具体问题或观点
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
            # 从组织者获取下一个发言者，但增强用户关注
            decision = organizer.route(state, history_store.tail(state.thread_id, 12))
            responder = decision["next_speaker"]
            # 在任务提示中强调用户输入
            task_hint = f"【用户发言】用户刚才说：\"{content}\"\n{decision['task_hint']}\n重要：你的回应必须与用户的这个发言产生直接对话关系，不要忽略用户的需求！"

        # 调用智能体回应用户，传递用户发言上下文
        response = call_companion(
            speaker=responder,
            state=state,
            task_hint=task_hint,
            stance_hint=None,
            tail_n=8,
        )

        # 记录回应
        history_store.record_speaker(state.thread_id, responder, response)
        advance_turn(state, responder)

        # 更新状态
        patch = organizer.update_from_new_public_event(state, history_store.tail(state.thread_id, 12))
        apply_patch(state, patch)

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
        session["messages"].append(ai_msg)
        session["updated_at"] = get_timestamp()

        # 返回消息列表（包含新增的用户消息和AI消息）
        return {
            "messages": session["messages"],
            "updated_at": session["updated_at"]
        }

    # 处理"继续"操作 - 让下一个智能体发言
    agent_msg = await process_agent_turn(chat_id, session)
    if agent_msg:
        session["messages"].append(agent_msg)
        session["updated_at"] = get_timestamp()

        # 返回消息列表
        return {
            "messages": session["messages"],
            "updated_at": session["updated_at"]
        }

    raise HTTPException(status_code=500, detail="无法生成响应")


@app.post("/api/chats/{chat_id}/continue")
async def continue_chat(chat_id: str):
    """让AI继续发言"""
    session = get_session(chat_id)
    agent_msg = await process_agent_turn(chat_id, session)

    if agent_msg:
        session["messages"].append(agent_msg)
        session["updated_at"] = get_timestamp()

        # 返回消息列表（包含新增的消息）
        return {
            "messages": session["messages"],
            "updated_at": session["updated_at"]
        }

    raise HTTPException(status_code=500, detail="无法生成响应")


@app.post("/api/chats/{chat_id}/summary")
async def summarize_chat(chat_id: str):
    """生成对话总结，对话继续进行"""
    session = get_session(chat_id)
    state = session["state"]
    organizer = session["organizer"]

    # 组织者生成总结（不改变对话状态，保持继续进行）
    summary = organizer.summarize(state, history_store.tail(state.thread_id, 20))
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


@app.delete("/api/chats/{chat_id}")
async def delete_chat(chat_id: str):
    """删除对话"""
    if chat_id not in sessions:
        raise HTTPException(status_code=404, detail="会话不存在")

    # 清理历史记录
    thread_id = sessions[chat_id]["thread_id"]
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
    print("启动服务器...")
    print("API地址: http://localhost:8000")
    print("API文档: http://localhost:8000/docs")
    print("WebSocket: ws://localhost:8000/ws/chat/{chat_id}")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
    )
