# memory/state_store.py
from __future__ import annotations

import uuid
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


def new_thread_id() -> str:
    """生成一个新的会话/房间 thread_id。"""
    return uuid.uuid4().hex


@dataclass
class DiscussionState:
    """
    结构化共享状态（主持人调度用，不是给用户看的）。
    注意：这里用 dataclass，避免你额外安装 pydantic。
    """
    thread_id: str
    topic: str

    phase: str = "opening"   # opening | discussion | closing
    turn_id: int = 0         # 每发生一次“公开发言”可以递增（这里由 main 控制）

    # 议程（agenda）里每项是 dict，字段：item_id/question/priority/status/created_by
    agenda: List[Dict[str, Any]] = field(default_factory=list)
    active_item_id: Optional[str] = None

    consensus: List[str] = field(default_factory=list)
    disagreements: List[str] = field(default_factory=list)
    open_questions: List[str] = field(default_factory=list)

    last_speaker: Optional[str] = None
    last_user_interjection: Optional[str] = None

    # 用于质量控制（可选）
    style_health: Dict[str, int] = field(default_factory=lambda: {
        "list_like": 0,
        "generic": 0,
        "repetitive": 0,
    })


def init_state(thread_id: str, topic: str) -> DiscussionState:
    return DiscussionState(thread_id=thread_id, topic=topic)


def set_agenda(state: DiscussionState, agenda_items: List[Dict[str, Any]], active_item_id: Optional[str]):
    """
    把 organizer.open() 生成的 agenda_items 写入 state。
    并标记 active_item_id 为 active，其余为 open（如未指定 active，则默认第一个）。
    """
    state.agenda = agenda_items or []
    if not state.agenda:
        state.active_item_id = None
        return

    # 兜底：如果没传 active_item_id，就用第一个
    if not active_item_id:
        active_item_id = state.agenda[0].get("item_id")

    state.active_item_id = active_item_id

    # 更新 status
    for it in state.agenda:
        if it.get("item_id") == state.active_item_id:
            it["status"] = "active"
            it["priority"] = max(int(it.get("priority", 50)), 70)
        else:
            if it.get("status") == "active":
                it["status"] = "open"


def get_active_question(state: DiscussionState) -> Optional[str]:
    if not state.active_item_id:
        return None
    for it in state.agenda:
        if it.get("item_id") == state.active_item_id:
            return it.get("question")
    return None


def activate_item(state: DiscussionState, item_id: str) -> bool:
    """把某个 agenda item 设为 active。"""
    found = False
    for it in state.agenda:
        if it.get("item_id") == item_id:
            it["status"] = "active"
            it["priority"] = max(int(it.get("priority", 50)), 70)
            found = True
        else:
            if it.get("status") == "active":
                it["status"] = "open"
    if found:
        state.active_item_id = item_id
    return found


def _append_unique(target: List[str], items: List[str]):
    for x in items:
        x = (x or "").strip()
        if x and x not in target:
            target.append(x)


def apply_patch(state: DiscussionState, patch: Dict[str, Any]):
    """
    应用 organizer.update_from_new_public_event() 产生的 patch。
    patch 格式（可能字段缺失）：
      add_consensus: list[str]
      add_disagreements: list[str]
      add_open_questions: list[str]
      add_agenda: list[str]  # 新子问题
      style_flags: list[str] # list_like/generic/repetitive
    """
    _append_unique(state.consensus, [str(x) for x in patch.get("add_consensus", []) if x is not None])
    _append_unique(state.disagreements, [str(x) for x in patch.get("add_disagreements", []) if x is not None])
    _append_unique(state.open_questions, [str(x) for x in patch.get("add_open_questions", []) if x is not None])

    # 新增 agenda
    add_agenda = patch.get("add_agenda", [])
    if isinstance(add_agenda, list):
        for q in add_agenda:
            q = str(q).strip()
            if not q:
                continue
            # 去重：同 question 不重复加
            if any((it.get("question") or "").strip() == q for it in state.agenda):
                continue
            state.agenda.append({
                "item_id": uuid.uuid4().hex[:10],
                "question": q,
                "priority": 45,
                "status": "open",
                "created_by": "组织者",
            })

    # style flags 累加
    flags = patch.get("style_flags", [])
    if isinstance(flags, list):
        for f in flags:
            k = str(f).strip()
            if not k:
                continue
            state.style_health[k] = int(state.style_health.get(k, 0)) + 1

    # 如果启用了持久化存储，同时保存到数据库
    if os.getenv('USE_PERSISTENT_STORAGE', 'true').lower() == 'true':
        try:
            from dev.mysql.persistent_store import persistent_state_store
            persistent_state_store.save_state(state)
        except Exception as e:
            print(f"保存状态到数据库失败: {e}")


def load_state_from_db(thread_id: str) -> Optional[DiscussionState]:
    """从数据库加载状态"""
    if os.getenv('USE_PERSISTENT_STORAGE', 'true').lower() != 'true':
        return None

    try:
        from dev.mysql.persistent_store import persistent_state_store
        state_data = persistent_state_store.load_state(thread_id)
        if state_data:
            state = DiscussionState(thread_id=thread_id, topic=state_data['topic'])
            state.phase = state_data.get('phase', 'opening')
            state.turn_id = state_data.get('turn_id', 0)
            state.last_speaker = state_data.get('last_speaker')
            state.last_user_interjection = state_data.get('last_user_interjection')
            state.agenda = state_data.get('agenda', [])
            state.consensus = state_data.get('consensus', [])
            state.disagreements = state_data.get('disagreements', [])
            state.open_questions = state_data.get('open_questions', [])
            state.style_health = state_data.get('style_health', {
                "list_like": 0,
                "generic": 0,
                "repetitive": 0,
            })
            return state
    except Exception as e:
        print(f"从数据库加载状态失败: {e}")

    return None


def advance_turn(state: DiscussionState, speaker: Optional[str] = None):
    """用于 main 里每发生一次公开发言后推进计数。"""
    state.turn_id += 1
    if speaker:
        state.last_speaker = speaker
