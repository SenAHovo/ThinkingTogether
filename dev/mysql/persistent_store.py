"""
持久化存储层
替代现有的内存存储，提供数据库持久化功能
"""

import json
import uuid
from typing import Any, Dict, List, Optional, Sequence
from datetime import datetime

from .db_utils import DatabaseManager, get_db_manager
from .content_analyzer import get_content_analyzer, ExtractedContent


class PersistentHistoryStore:
    """
    持久化历史存储
    替代InMemoryHistoryStore，提供数据库持久化功能
    """

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db_manager = db_manager or get_db_manager()
        self.content_analyzer = get_content_analyzer()
        self.db_available = False  # 跟踪数据库是否可用

        # 尝试连接数据库
        try:
            if self.db_manager.connect():
                self.db_available = True
                print("[持久化存储] 数据库连接成功")
            else:
                print("[持久化存储] 数据库连接失败，将使用降级模式（仅内存）")
        except Exception as e:
            print(f"[持久化存储] 数据库初始化失败: {e}，将使用降级模式（仅内存）")
            self.db_available = False

    def _ensure_thread_exists(self, thread_id: str, topic: str = "未命名话题"):
        """确保线程在数据库中存在"""
        if not self.db_available:
            return

        if not self.db_manager.connection:
            if not self.db_manager.connect():
                self.db_available = False
                return

        try:
            with self.db_manager.get_cursor() as cursor:
                cursor.execute("SELECT thread_id FROM threads WHERE thread_id = %s", (thread_id,))
                if not cursor.fetchone():
                    cursor.execute("""
                        INSERT INTO threads (thread_id, topic, turn_id, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (thread_id, topic, 0, datetime.now(), datetime.now()))
                    print(f"[持久化存储] 新线程已创建: {thread_id}")
        except Exception as e:
            print(f"[持久化存储] 创建线程失败: {e}")
            self.db_available = False

    def _update_thread_stats(self, thread_id: str, speaker: str, content: str):
        """更新线程统计信息"""
        if not self.db_available:
            return

        if not self.db_manager.connection:
            if not self.db_manager.connect():
                self.db_available = False
                return

        try:
            with self.db_manager.get_cursor() as cursor:
                # 更新线程的最后发言者和时间
                cursor.execute("""
                    UPDATE threads
                    SET turn_id = turn_id + 1,
                        last_speaker = %s,
                        updated_at = %s
                    WHERE thread_id = %s
                """, (speaker, datetime.now(), thread_id))

        except Exception as e:
            print(f"[持久化存储] 更新统计失败: {e}")
            self.db_available = False

    def _save_analysis_results(self, thread_id: str, event_id: str, extracted: ExtractedContent):
        """保存分析结果"""
        if not self.db_available:
            return

        try:
            with self.db_manager.get_cursor() as cursor:
                # 保存共识到consensus表
                for content in extracted.consensus:
                    cursor.execute("""
                        INSERT INTO consensus (thread_id, content)
                        VALUES (%s, %s)
                    """, (thread_id, content))

                # 保存分歧到disagreements表
                for content in extracted.disagreements:
                    cursor.execute("""
                        INSERT INTO disagreements (thread_id, content)
                        VALUES (%s, %s)
                    """, (thread_id, content))

                # 保存问题到open_questions表
                for content in extracted.open_questions:
                    cursor.execute("""
                        INSERT INTO open_questions (thread_id, content)
                        VALUES (%s, %s)
                    """, (thread_id, content))

        except Exception as e:
            print(f"[持久化存储] 保存分析结果失败: {e}")
            self.db_available = False

    def append(
        self,
        thread_id: str,
        speaker: str,
        content: str,
        tags: Optional[Sequence[str]] = None,
        topic: Optional[str] = None
    ) -> Dict[str, Any]:
        """添加事件到数据库"""
        if not self.db_available:
            # 数据库不可用，返回虚拟事件（降级模式）
            event_id = uuid.uuid4().hex
            return {
                "event_id": event_id,
                "speaker": speaker,
                "content": content.strip(),
                "turn_id": 0,
                "tags": list(tags) if tags else [],
                "created_at": datetime.now().isoformat(),
                "warning": "数据库不可用，数据未持久化"
            }

        if not self.db_manager.connection:
            if not self.db_manager.connect():
                self.db_available = False
                # 连接失败，返回虚拟事件
                event_id = uuid.uuid4().hex
                return {
                    "event_id": event_id,
                    "speaker": speaker,
                    "content": content.strip(),
                    "turn_id": 0,
                    "tags": list(tags) if tags else [],
                    "created_at": datetime.now().isoformat(),
                    "warning": "数据库连接失败，数据未持久化"
                }

        # 确保线程存在
        self._ensure_thread_exists(thread_id, topic or "未命名话题")

        # 获取下一个turn_id
        try:
            with self.db_manager.get_cursor() as cursor:
                cursor.execute("SELECT MAX(turn_id) as max_turn FROM events WHERE thread_id = %s", (thread_id,))
                result = cursor.fetchone()
                turn_id = (result['max_turn'] or 0) + 1
        except Exception as e:
            print(f"[持久化存储] 获取turn_id失败: {e}")
            turn_id = 1
            self.db_available = False

        # 创建事件
        event_id = uuid.uuid4().hex
        tags_json = json.dumps(list(tags) if tags else [], ensure_ascii=False)

        # 添加内容分析元数据
        content_metadata = self.content_analyzer.get_content_metadata(content, speaker)
        tags_dict = json.loads(tags_json) if tags_json else []
        if isinstance(tags_dict, list):
            # 如果tags是列表，转换为字典格式
            tags_dict = {'tags': tags_dict, 'metadata': content_metadata}
        else:
            tags_dict.update({'metadata': content_metadata})

        try:
            with self.db_manager.get_cursor() as cursor:
                cursor.execute("""
                    INSERT INTO events (event_id, thread_id, speaker, content, turn_id, tags, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (event_id, thread_id, speaker, content, turn_id, json.dumps(tags_dict, ensure_ascii=False), datetime.now()))

            # 更新线程统计
            self._update_thread_stats(thread_id, speaker, content)

            # 分析内容并保存结果
            extracted = self.content_analyzer.extract_content(content)
            self._save_analysis_results(thread_id, event_id, extracted)

            ev = {
                "event_id": event_id,
                "speaker": speaker,
                "content": content.strip(),
                "turn_id": turn_id,
                "tags": list(tags) if tags else [],
                "created_at": datetime.now().isoformat(),
                "analysis": extracted
            }

            print(f"[持久化存储] 事件已保存: {event_id}, Speaker: {speaker}, Turn: {turn_id}")
            return ev

        except Exception as e:
            print(f"[持久化存储] 保存事件失败: {e}")
            self.db_available = False
            # 返回一个虚拟事件以保持兼容性
            return {
                "event_id": event_id,
                "speaker": speaker,
                "content": content.strip(),
                "turn_id": turn_id,
                "tags": list(tags) if tags else [],
                "created_at": datetime.now().isoformat(),
                "error": str(e)
            }

    def record_user(self, thread_id: str, content: str, tags: Optional[Sequence[str]] = None, topic: Optional[str] = None):
        """记录用户发言"""
        return self.append(thread_id, "用户", content, tags, topic)

    def record_speaker(self, thread_id: str, speaker: str, content: str, tags: Optional[Sequence[str]] = None, topic: Optional[str] = None):
        """记录智能体发言"""
        return self.append(thread_id, speaker, content, tags, topic)

    def tail(self, thread_id: str, n: int = 10) -> List[Dict[str, Any]]:
        """获取最后n个事件"""
        if not self.db_available:
            return []

        if not self.db_manager.connection:
            if not self.db_manager.connect():
                self.db_available = False
                return []

        try:
            with self.db_manager.get_cursor() as cursor:
                cursor.execute("""
                    SELECT event_id, speaker, content, turn_id, tags, created_at
                    FROM events
                    WHERE thread_id = %s
                    ORDER BY turn_id DESC
                    LIMIT %s
                """, (thread_id, n))

                events = cursor.fetchall()
                # 解析tags并按turn_id排序
                for ev in events:
                    if ev['tags']:
                        try:
                            ev['tags'] = json.loads(ev['tags'])
                        except:
                            ev['tags'] = []

                # 按turn_id重新排序（升序）
                events = sorted(events, key=lambda x: x['turn_id'])
                return events

        except Exception as e:
            print(f"[持久化存储] 获取历史记录失败: {e}")
            self.db_available = False
            return []

    def all(self, thread_id: str) -> List[Dict[str, Any]]:
        """获取所有事件"""
        if not self.db_available:
            return []

        if not self.db_manager.connection:
            if not self.db_manager.connect():
                self.db_available = False
                return []

        try:
            with self.db_manager.get_cursor() as cursor:
                cursor.execute("""
                    SELECT event_id, speaker, content, turn_id, tags, created_at
                    FROM events
                    WHERE thread_id = %s
                    ORDER BY turn_id ASC
                """, (thread_id,))

                events = cursor.fetchall()
                for ev in events:
                    if ev['tags']:
                        try:
                            ev['tags'] = json.loads(ev['tags'])
                        except:
                            ev['tags'] = []

                return events

        except Exception as e:
            print(f"[持久化存储] 获取所有事件失败: {e}")
            self.db_available = False
            return []

    def size(self, thread_id: str) -> int:
        """获取事件数量"""
        if not self.db_available:
            return 0

        if not self.db_manager.connection:
            if not self.db_manager.connect():
                self.db_available = False
                return 0

        try:
            with self.db_manager.get_cursor() as cursor:
                cursor.execute("SELECT COUNT(*) as count FROM events WHERE thread_id = %s", (thread_id,))
                result = cursor.fetchone()
                return result['count'] if result else 0
        except Exception as e:
            print(f"[持久化存储] 获取事件数量失败: {e}")
            self.db_available = False
            return 0

    def clear(self, thread_id: str):
        """清除线程数据"""
        if not self.db_available:
            return

        if not self.db_manager.connection:
            if not self.db_manager.connect():
                self.db_available = False
                return

        try:
            with self.db_manager.get_cursor() as cursor:
                # 删除相关的数据
                cursor.execute("DELETE FROM agenda_items WHERE thread_id = %s", (thread_id,))
                cursor.execute("DELETE FROM consensus WHERE thread_id = %s", (thread_id,))
                cursor.execute("DELETE FROM disagreements WHERE thread_id = %s", (thread_id,))
                cursor.execute("DELETE FROM open_questions WHERE thread_id = %s", (thread_id,))
                cursor.execute("DELETE FROM style_health WHERE thread_id = %s", (thread_id,))
                cursor.execute("DELETE FROM events WHERE thread_id = %s", (thread_id,))
                cursor.execute("DELETE FROM threads WHERE thread_id = %s", (thread_id,))
            print(f"[持久化存储] 线程数据已清除: {thread_id}")
        except Exception as e:
            print(f"[持久化存储] 清除线程数据失败: {e}")
            self.db_available = False

    def get_thread_analysis(self, thread_id: str) -> Dict[str, Any]:
        """获取线程分析摘要"""
        if not self.db_available:
            return {'thread_id': thread_id, 'error': '数据库不可用'}

        if not self.db_manager.connection:
            if not self.db_manager.connect():
                self.db_available = False
                return {'thread_id': thread_id, 'error': '数据库连接失败'}

        try:
            with self.db_manager.get_cursor() as cursor:
                # 获取基本统计
                cursor.execute("""
                    SELECT COUNT(*) as event_count,
                           COUNT(DISTINCT speaker) as speaker_count,
                           MIN(created_at) as start_time,
                           MAX(created_at) as end_time
                    FROM events WHERE thread_id = %s
                """, (thread_id,))
                basic_stats = cursor.fetchone()

                # 获取结构化数据统计
                cursor.execute("SELECT COUNT(*) as count FROM consensus WHERE thread_id = %s", (thread_id,))
                consensus_count = cursor.fetchone()['count']

                cursor.execute("SELECT COUNT(*) as count FROM disagreements WHERE thread_id = %s", (thread_id,))
                disagreement_count = cursor.fetchone()['count']

                cursor.execute("SELECT COUNT(*) as count FROM open_questions WHERE thread_id = %s", (thread_id,))
                question_count = cursor.fetchone()['count']

                # 获取发言统计
                cursor.execute("""
                    SELECT speaker, COUNT(*) as message_count, AVG(LENGTH(content)) as avg_length
                    FROM events
                    WHERE thread_id = %s
                    GROUP BY speaker
                """, (thread_id,))
                speaker_stats = cursor.fetchall()

                return {
                    'thread_id': thread_id,
                    'event_count': basic_stats['event_count'] if basic_stats else 0,
                    'speaker_count': basic_stats['speaker_count'] if basic_stats else 0,
                    'consensus_count': consensus_count,
                    'disagreement_count': disagreement_count,
                    'question_count': question_count,
                    'start_time': basic_stats['start_time'] if basic_stats else None,
                    'end_time': basic_stats['end_time'] if basic_stats else None,
                    'speaker_stats': {stat['speaker']: {
                        'message_count': stat['message_count'],
                        'avg_length': float(stat['avg_length']) if stat['avg_length'] else 0
                    } for stat in speaker_stats}
                }

        except Exception as e:
            print(f"[持久化存储] 获取线程分析失败: {e}")
            self.db_available = False
            return {'thread_id': thread_id, 'error': str(e)}


class PersistentStateStore:
    """持久化状态存储"""

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db_manager = db_manager or get_db_manager()
        self.db_available = False  # 跟踪数据库是否可用

        # 尝试连接数据库
        try:
            if self.db_manager.connect():
                self.db_available = True
                print("[持久化存储] 状态存储：数据库连接成功")
            else:
                print("[持久化存储] 状态存储：数据库连接失败，将使用降级模式")
        except Exception as e:
            print(f"[持久化存储] 状态存储：数据库初始化失败: {e}，将使用降级模式")
            self.db_available = False

    def save_state(self, state: 'DiscussionState'):
        """保存讨论状态到数据库"""
        if not self.db_available:
            return

        if not self.db_manager.connection:
            if not self.db_manager.connect():
                self.db_available = False
                return

        try:
            with self.db_manager.get_cursor() as cursor:
                # 更新线程基本信息
                cursor.execute("""
                    UPDATE threads SET
                        phase = %s,
                        turn_id = %s,
                        last_speaker = %s,
                        last_user_interjection = %s,
                        updated_at = %s
                    WHERE thread_id = %s
                """, (
                    getattr(state, 'phase', 'opening'),
                    getattr(state, 'turn_id', 0),
                    getattr(state, 'last_speaker', None),
                    getattr(state, 'last_user_interjection', None),
                    datetime.now(),
                    state.thread_id
                ))

                # 保存议程
                cursor.execute("DELETE FROM agenda_items WHERE thread_id = %s", (state.thread_id,))
                for item in getattr(state, 'agenda', []):
                    cursor.execute("""
                        INSERT INTO agenda_items (item_id, thread_id, question, priority, status, created_by)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (
                        item.get('item_id', uuid.uuid4().hex[:10]),
                        state.thread_id,
                        item.get('question', ''),
                        item.get('priority', 50),
                        item.get('status', 'open'),
                        item.get('created_by', 'unknown')
                    ))

                # 保存共识、分歧、问题到单独的表
                self._save_list_field(cursor, state.thread_id, 'consensus', getattr(state, 'consensus', []))
                self._save_list_field(cursor, state.thread_id, 'disagreements', getattr(state, 'disagreements', []))
                self._save_list_field(cursor, state.thread_id, 'open_questions', getattr(state, 'open_questions', []))

                # 保存风格健康度
                style_health = getattr(state, 'style_health', {})
                for metric_name, count in style_health.items():
                    if metric_name in ['list_like', 'generic', 'repetitive']:
                        cursor.execute("""
                            INSERT INTO style_health (thread_id, metric_name, count)
                            VALUES (%s, %s, %s)
                            ON DUPLICATE KEY UPDATE count = %s
                        """, (state.thread_id, metric_name, count, count))

            print(f"[持久化存储] 状态已保存: {state.thread_id}")

        except Exception as e:
            print(f"[持久化存储] 保存状态失败: {e}")
            self.db_available = False

    def _save_list_field(self, cursor, thread_id: str, field_type: str, items: List[str]):
        """保存列表字段到相应的表"""
        if field_type == 'consensus':
            for item in items:
                cursor.execute("""
                    INSERT INTO consensus (thread_id, content)
                    VALUES (%s, %s)
                """, (thread_id, item))
        elif field_type == 'disagreements':
            for item in items:
                cursor.execute("""
                    INSERT INTO disagreements (thread_id, content)
                    VALUES (%s, %s)
                """, (thread_id, item))
        elif field_type == 'open_questions':
            for item in items:
                cursor.execute("""
                    INSERT INTO open_questions (thread_id, content)
                    VALUES (%s, %s)
                """, (thread_id, item))

    def load_state(self, thread_id: str) -> Optional[Dict[str, Any]]:
        """从数据库加载状态"""
        if not self.db_available:
            return None

        if not self.db_manager.connection:
            if not self.db_manager.connect():
                self.db_available = False
                return None

        try:
            with self.db_manager.get_cursor() as cursor:
                # 获取线程基本信息
                cursor.execute("""
                    SELECT * FROM threads WHERE thread_id = %s
                """, (thread_id,))
                thread = cursor.fetchone()

                if not thread:
                    return None

                # 获取议程
                cursor.execute("""
                    SELECT * FROM agenda_items WHERE thread_id = %s
                """, (thread_id,))
                agenda = cursor.fetchall()

                # 获取共识、分歧、问题
                cursor.execute("SELECT content FROM consensus WHERE thread_id = %s", (thread_id,))
                consensus = [row['content'] for row in cursor.fetchall()]

                cursor.execute("SELECT content FROM disagreements WHERE thread_id = %s", (thread_id,))
                disagreements = [row['content'] for row in cursor.fetchall()]

                cursor.execute("SELECT content FROM open_questions WHERE thread_id = %s", (thread_id,))
                open_questions = [row['content'] for row in cursor.fetchall()]

                # 获取风格健康度
                cursor.execute("SELECT metric_name, count FROM style_health WHERE thread_id = %s", (thread_id,))
                style_health = {row['metric_name']: row['count'] for row in cursor.fetchall()}

                return {
                    'thread_id': thread_id,
                    'topic': thread['topic'],
                    'phase': thread['phase'],
                    'turn_id': thread['turn_id'],
                    'last_speaker': thread['last_speaker'],
                    'last_user_interjection': thread['last_user_interjection'],
                    'agenda': agenda,
                    'consensus': consensus,
                    'disagreements': disagreements,
                    'open_questions': open_questions,
                    'style_health': style_health
                }

        except Exception as e:
            print(f"[持久化存储] 加载状态失败: {e}")
            self.db_available = False
            return None


# 全局持久化存储实例
persistent_history_store = PersistentHistoryStore()
persistent_state_store = PersistentStateStore()