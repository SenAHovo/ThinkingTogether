"""
数据库操作工具模块
用于管理thinking_together数据库的连接和操作
"""

import pymysql
import json
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from contextlib import contextmanager


class DatabaseManager:
    """数据库管理器，负责处理与thinking_together数据库的所有交互"""

    def __init__(self, host='localhost', user='root', password='root', database='thinking_together', port=3306, charset='utf8mb4'):
        self.host = host
        self.user = user
        self.password = password
        self.database = database
        self.port = port
        self.charset = charset
        self.connection = None

    @classmethod
    def from_config(cls):
        """从配置文件创建数据库管理器"""
        from .db_config import get_db_config
        config = get_db_config()
        return cls(**config)

    def connect(self):
        """建立数据库连接"""
        try:
            self.connection = pymysql.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database,
                port=self.port,
                charset=self.charset,
                cursorclass=pymysql.cursors.DictCursor
            )
            print(f"成功连接到数据库: {self.database}")
            return True
        except Exception as e:
            print(f"数据库连接失败: {e}")
            return False

    def disconnect(self):
        """关闭数据库连接"""
        if self.connection:
            self.connection.close()
            self.connection = None
            print("数据库连接已关闭")

    @contextmanager
    def get_cursor(self):
        """获取数据库游标的上下文管理器"""
        if not self.connection:
            self.connect()

        cursor = self.connection.cursor()
        try:
            yield cursor
            self.connection.commit()
        except Exception as e:
            self.connection.rollback()
            raise e
        finally:
            cursor.close()

    def generate_event_id(self) -> str:
        """生成事件ID"""
        return str(uuid.uuid4()).replace('-', '')[:32]

    def generate_thread_id(self) -> str:
        """生成线程ID"""
        return str(uuid.uuid4()).replace('-', '')[:32]

    def save_agent_output(self,
                         speaker: str,
                         content: str,
                         thread_id: Optional[str] = None,
                         turn_id: Optional[int] = None,
                         tags: Optional[Dict[str, Any]] = None) -> str:
        """
        保存智能体输出到数据库

        Args:
            speaker: 说话者名称
            content: 输出内容
            thread_id: 线程ID，如果为None则生成新的
            turn_id: 回合ID
            tags: 标签字典，会转换为JSON

        Returns:
            str: 事件ID
        """
        if not self.connection:
            self.connect()

        event_id = self.generate_event_id()

        # 如果没有提供thread_id，生成新的
        if thread_id is None:
            thread_id = self.generate_thread_id()

        # 确保线程在threads表中存在
        self._ensure_thread_exists(thread_id)

        # 如果没有提供turn_id，查询当前thread的最大turn_id并加1
        if turn_id is None:
            with self.get_cursor() as cursor:
                cursor.execute(
                    "SELECT MAX(turn_id) as max_turn FROM events WHERE thread_id = %s",
                    (thread_id,)
                )
                result = cursor.fetchone()
                turn_id = (result['max_turn'] or 0) + 1

        # 将tags转换为JSON字符串
        tags_json = json.dumps(tags, ensure_ascii=False) if tags else None

        with self.get_cursor() as cursor:
            cursor.execute("""
                INSERT INTO events (event_id, thread_id, speaker, content, turn_id, tags, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                event_id, thread_id, speaker, content, turn_id, tags_json, datetime.now()
            ))

        print(f"智能体输出已保存 - Event ID: {event_id}, Speaker: {speaker}, Thread ID: {thread_id}")
        return event_id

    def _ensure_thread_exists(self, thread_id: str, topic: str = "讨论话题"):
        """确保线程在threads表中存在"""
        with self.get_cursor() as cursor:
            cursor.execute("SELECT thread_id FROM threads WHERE thread_id = %s", (thread_id,))
            if not cursor.fetchone():
                cursor.execute("""
                    INSERT INTO threads (thread_id, topic, phase, turn_id, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (thread_id, topic, 'discussion', 1, datetime.now(), datetime.now()))
                print(f"新线程已创建: {thread_id}")

    def get_thread_events(self, thread_id: str, limit: int = None) -> List[Dict[str, Any]]:
        """
        获取指定线程的所有事件

        Args:
            thread_id: 线程ID
            limit: 限制返回的事件数量

        Returns:
            List[Dict]: 事件列表
        """
        if not self.connection:
            self.connect()

        with self.get_cursor() as cursor:
            query = """
                SELECT event_id, thread_id, speaker, content, turn_id, tags, created_at
                FROM events
                WHERE thread_id = %s
                ORDER BY turn_id ASC, created_at ASC
            """
            if limit:
                query += f" LIMIT {limit}"

            cursor.execute(query, (thread_id,))
            events = cursor.fetchall()

            # 解析tags JSON
            for event in events:
                if event['tags']:
                    event['tags'] = json.loads(event['tags'])

            return events

    def get_latest_threads(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        获取最新的线程列表

        Args:
            limit: 限制返回的线程数量

        Returns:
            List[Dict]: 线程列表
        """
        if not self.connection:
            self.connect()

        with self.get_cursor() as cursor:
            cursor.execute("""
                SELECT
                    thread_id,
                    MAX(created_at) as latest_event_time,
                    COUNT(*) as event_count,
                    GROUP_CONCAT(DISTINCT speaker) as speakers
                FROM events
                GROUP BY thread_id
                ORDER BY latest_event_time DESC
                LIMIT %s
            """, (limit,))

            threads = cursor.fetchall()
            return threads

    def search_events(self, keyword: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        搜索包含关键词的事件

        Args:
            keyword: 搜索关键词
            limit: 限制返回的事件数量

        Returns:
            List[Dict]: 匹配的事件列表
        """
        if not self.connection:
            self.connect()

        with self.get_cursor() as cursor:
            cursor.execute("""
                SELECT event_id, thread_id, speaker, content, turn_id, tags, created_at
                FROM events
                WHERE content LIKE %s
                ORDER BY created_at DESC
                LIMIT %s
            """, (f'%{keyword}%', limit))

            events = cursor.fetchall()

            # 解析tags JSON
            for event in events:
                if event['tags']:
                    event['tags'] = json.loads(event['tags'])

            return events

    def save_consensus(self, thread_id: str, content: str) -> bool:
        """保存共识内容"""
        if not self.connection:
            self.connect()

        try:
            with self.get_cursor() as cursor:
                cursor.execute("""
                    INSERT INTO consensus (thread_id, content)
                    VALUES (%s, %s)
                """, (thread_id, content))
            print(f"共识已保存 - Thread ID: {thread_id}")
            return True
        except Exception as e:
            print(f"保存共识失败: {e}")
            return False

    def save_disagreement(self, thread_id: str, content: str) -> bool:
        """保存分歧内容"""
        if not self.connection:
            self.connect()

        try:
            with self.get_cursor() as cursor:
                cursor.execute("""
                    INSERT INTO disagreements (thread_id, content)
                    VALUES (%s, %s)
                """, (thread_id, content))
            print(f"分歧已保存 - Thread ID: {thread_id}")
            return True
        except Exception as e:
            print(f"保存分歧失败: {e}")
            return False

    def save_open_question(self, thread_id: str, content: str) -> bool:
        """保存开放问题"""
        if not self.connection:
            self.connect()

        try:
            with self.get_cursor() as cursor:
                cursor.execute("""
                    INSERT INTO open_questions (thread_id, content)
                    VALUES (%s, %s)
                """, (thread_id, content))
            print(f"开放问题已保存 - Thread ID: {thread_id}")
            return True
        except Exception as e:
            print(f"保存开放问题失败: {e}")
            return False


# 创建全局数据库管理器实例并自动连接
db_manager = DatabaseManager.from_config()
db_manager.connect()


def get_db_manager() -> DatabaseManager:
    """获取数据库管理器实例"""
    return db_manager


# 装饰器函数，用于自动保存智能体输出
def save_agent_response(speaker: str, thread_id: str = None, tags: Dict[str, Any] = None):
    """
    装饰器，自动保存智能体的响应到数据库

    Args:
        speaker: 说话者名称
        thread_id: 线程ID
        tags: 标签字典
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # 执行原函数
            result = func(*args, **kwargs)

            # 如果结果是字符串，保存到数据库
            if isinstance(result, str):
                db_manager.save_agent_output(
                    speaker=speaker,
                    content=result,
                    thread_id=thread_id,
                    tags=tags
                )

            return result
        return wrapper
    return decorator


if __name__ == "__main__":
    # 测试代码
    db = DatabaseManager()

    if db.connect():
        # 测试保存智能体输出
        event_id = db.save_agent_output(
            speaker="TestAgent",
            content="这是一条测试消息",
            tags={"test": True, "version": "1.0"}
        )
        print(f"测试事件ID: {event_id}")

        # 测试查询线程事件
        events = db.get_thread_events(event_id[:32])  # 使用event_id的前32位作为thread_id
        print(f"线程事件: {events}")

        db.disconnect()