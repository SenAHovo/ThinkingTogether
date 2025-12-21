# memory/history_store.py
from __future__ import annotations

import uuid
import os
from typing import Any, Dict, List, Optional, Sequence

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

# 检查是否使用持久化存储
USE_PERSISTENT_STORAGE = os.getenv('USE_PERSISTENT_STORAGE', 'auto').lower() == 'true'

# 尝试使用持久化存储，如果失败则使用内存存储
_history_store_instance = None
_use_persistent = False

if USE_PERSISTENT_STORAGE:
    try:
        from mysql.persistent_store import PersistentHistoryStore
        # 尝试创建持久化存储实例（会测试数据库连接）
        _history_store_instance = PersistentHistoryStore()
        # 测试连接是否正常
        if _history_store_instance.db_manager.connection:
            _use_persistent = True
            print("[持久化存储] 数据库连接成功，使用数据库存储")
        else:
            _use_persistent = False
            print("[持久化存储] 数据库连接失败，切换到内存存储")
    except Exception as e:
        print(f"[持久化存储] 初始化失败: {e}，切换到内存存储")
        _use_persistent = False
        _history_store_instance = None

if not _use_persistent:
    class InMemoryHistoryStore:
        """
        只保存"公开发言"（用户能看到的内容），不保存内部控制 prompt。
        每个 thread_id（房间/会话）对应一串 event。

        event 字段：
          - event_id: str
          - speaker: str（例如：用户/组织者/理论家/实践者/质疑者）
          - content: str（公开发言文本）
          - turn_id: int（递增序号，便于回放）
          - tags: list[str]（可选标签）
        """

        def __init__(self):
            self._events: Dict[str, List[Dict[str, Any]]] = {}
            self._turn: Dict[str, int] = {}

        def _next_turn(self, thread_id: str) -> int:
            self._turn[thread_id] = self._turn.get(thread_id, 0) + 1
            return self._turn[thread_id]

        def append(
            self,
            thread_id: str,
            speaker: str,
            content: str,
            tags: Optional[Sequence[str]] = None,
        ) -> Dict[str, Any]:
            ev = {
                "event_id": uuid.uuid4().hex,
                "speaker": speaker,
                "content": (content or "").strip(),
                "turn_id": self._next_turn(thread_id),
                "tags": list(tags) if tags else [],
            }
            self._events.setdefault(thread_id, []).append(ev)
            return ev

        # 便捷方法：更语义化
        def record_user(self, thread_id: str, content: str, tags: Optional[Sequence[str]] = None, topic: Optional[str] = None):
            return self.append(thread_id, "用户", content, tags)

        def record_speaker(self, thread_id: str, speaker: str, content: str, tags: Optional[Sequence[str]] = None, topic: Optional[str] = None):
            return self.append(thread_id, speaker, content, tags)

        def tail(self, thread_id: str, n: int = 10) -> List[Dict[str, Any]]:
            evs = self._events.get(thread_id, [])
            return evs[-n:] if n > 0 else []

        def all(self, thread_id: str) -> List[Dict[str, Any]]:
            return list(self._events.get(thread_id, []))

        def clear(self, thread_id: str):
            self._events.pop(thread_id, None)
            self._turn.pop(thread_id, None)

        def size(self, thread_id: str) -> int:
            return len(self._events.get(thread_id, []))

    # 创建内存存储实例（如果未使用持久化存储）
    _history_store_instance = InMemoryHistoryStore()

# 设置全局history_store为选定的存储实例
history_store = _history_store_instance


def _get_field(ev: Any, key: str, default: Any = None) -> Any:
    """兼容 dict 或对象（有属性）。"""
    if isinstance(ev, dict):
        return ev.get(key, default)
    return getattr(ev, key, default)


def events_to_messages(
    events: Sequence[Any],
    max_content_chars: Optional[int] = 600,
    include_tags: bool = False,
) -> List[BaseMessage]:
    """
    把公开发言 events 转换成 LangChain messages 列表。
    规则：
      - speaker == '用户' → HumanMessage（内容加【用户】前缀）
      - 其他 speaker → AIMessage（内容加【角色】前缀）

    这样模型看到的是“讨论对话”，而不是“题目”。
    """
    messages: List[BaseMessage] = []

    for ev in events:
        speaker = str(_get_field(ev, "speaker", "未知"))
        content = str(_get_field(ev, "content", "")).strip()
        tags = _get_field(ev, "tags", []) or []

        if max_content_chars and len(content) > max_content_chars:
            content = content[:max_content_chars] + "…"

        if include_tags and tags:
            content = f"{content}\n（tags: {', '.join(map(str, tags))}）"

        if speaker == "用户":
            messages.append(HumanMessage(content=f"【用户】{content}"))
        else:
            messages.append(AIMessage(content=f"{content}"))

    return messages
