# companion_tool_io.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional, Sequence


@dataclass
class Hook:
    """
    给组织者的“推进线索”：
    - kind: 类型（clarify/action/challenge/new_question/evidence/...）
    - content: 具体内容（短句）
    """
    kind: str
    content: str


@dataclass
class CompanionStyle:
    """
    角色风格：用于差异化，不要把它当模板结构要求。
    """
    vibe: str = ""
    tics: Sequence[str] = field(default_factory=list)
    taboos: Sequence[str] = field(default_factory=list)


@dataclass
class CompanionSpeakInput:
    """
    学伴工具输入（由 main 组装传入）：
    - state: DiscussionState
    - transcript_tail: 公开历史末尾（list[dict]）
    - task_hint: 主持人的柔性任务提示
    - stance_hint: 可选立场提示
    - style: 角色风格
    """
    thread_id: str
    speaker: str
    state: Any
    transcript_tail: List[dict]
    task_hint: str = ""
    stance_hint: Optional[str] = None
    style: CompanionStyle = field(default_factory=CompanionStyle)


@dataclass
class CompanionSpeakOutput:
    """
    学伴工具输出：
    - speaker: 角色名
    - utterance: 公开发言（要写入 history_store）
    - hooks: 推进线索（组织者可用）
    """
    speaker: str
    utterance: str
    hooks: List[Hook] = field(default_factory=list)
