# agents/organizer_agent.py
from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List, Optional, Tuple

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import BaseMessage
from langchain_core.runnables import RunnableLambda

from dev.agents._shared import clean_text, excerpt
from dev.memory.history_store import events_to_messages
from dev.model_client import llm_organizer


SPEAKERS = ["理论家", "实践者", "质疑者"]


def _safe_json_loads(s: str) -> Optional[dict]:
    """
    尽量从模型输出中提取 JSON 对象。
    支持：输出前后夹杂解释文字的情况（会尝试截取首尾大括号）。
    """
    if not s:
        return None
    s = s.strip()

    # 直接尝试
    try:
        obj = json.loads(s)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass

    # 尝试截取 {...}
    l = s.find("{")
    r = s.rfind("}")
    if l != -1 and r != -1 and r > l:
        try:
            obj = json.loads(s[l:r + 1])
            if isinstance(obj, dict):
                return obj
        except Exception:
            return None
    return None


def _get(state: Any, key: str, default: Any = None) -> Any:
    """兼容 dict 或有属性对象。"""
    if isinstance(state, dict):
        return state.get(key, default)
    return getattr(state, key, default)


def _set(state: Any, key: str, val: Any):
    """兼容 dict 或有属性对象。"""
    if isinstance(state, dict):
        state[key] = val
    else:
        setattr(state, key, val)


def _append_list(state: Any, key: str, values: List[str]):
    cur = _get(state, key, []) or []
    if not isinstance(cur, list):
        cur = list(cur)
    for v in values:
        v = (v or "").strip()
        if v and v not in cur:
            cur.append(v)
    _set(state, key, cur)


class OrganizerAgent:
    """
    组织者：
    - 不直接替学伴输出内容观点（主要负责调度与总结）
    - 通过 JSON 路由决定谁发言、给什么任务提示（避免写死顺序）
    """

    def __init__(self):
        self._opening_chain = self._build_opening_chain()
        self._route_chain = self._build_route_chain()
        self._update_chain = self._build_update_chain()
        self._final_chain = self._build_final_chain()

    @staticmethod
    def _build_opening_chain():
        sys = (
            "你是【组织者/主持人】。你负责把讨论变得像真实小组讨论。\n"
            "你要做：开场白 + 切出2~4个可推进的子问题(议程)。\n"
            "\n"
            "适应不同类型话题：\n"
            "- 热点事件：快速切入争议点，关注影响和应对\n"
            "- 现状分析：聚焦核心矛盾，探讨成因和出路\n"
            "- 未来趋势：平衡机遇与挑战，讨论可能性和可行性\n"
            "- 学习概念：从问题出发，激发探索欲望\n"
            "\n"
            "不要写论文式综述，不要清单式盘点，不要小标题。\n"
            "你的输出必须严格为 JSON（不带任何多余文字）。"
        )
        prompt = ChatPromptTemplate.from_messages([
            ("system", sys),
            MessagesPlaceholder("history"),
            ("human", "{instruction}"),
        ])
        chain = prompt | llm_organizer | RunnableLambda(lambda m: m.content)
        return chain

    @staticmethod
    def _build_route_chain():
        sys = (
            "你是【组织者/主持人】。你不讨论内容，只做调度。\n"
            "你要根据最近讨论内容，动态选择下一位发言者（理论家/实践者/质疑者）并给一个短任务提示。\n"
            "\n"
            "角色选择策略：\n"
            "- 理论家：需要概念澄清、框架构建、机制分析时\n"
            "- 实践者：需要具体场景、可行性判断、操作建议时\n"
            "- 质疑者：需要逻辑检验、风险评估、观点平衡时\n"
            "\n"
            "任务提示要具体，但不要规定固定输出格式。\n"
            "输出必须严格为 JSON（不带任何多余文字）。"
        )
        prompt = ChatPromptTemplate.from_messages([
            ("system", sys),
            MessagesPlaceholder("history"),
            ("human", "{instruction}"),
        ])
        chain = prompt | llm_organizer | RunnableLambda(lambda m: m.content)
        return chain

    @staticmethod
    def _build_update_chain():
        sys = (
            "你是【主持人记录员】。你要从最新一条公开发言中提炼结构化信息，用于更新讨论状态。\n"
            "输出必须严格为 JSON（不带任何多余文字）。"
        )
        prompt = ChatPromptTemplate.from_messages([
            ("system", sys),
            MessagesPlaceholder("history"),
            ("human", "{instruction}"),
        ])
        chain = prompt | llm_organizer | RunnableLambda(lambda m: m.content)
        return chain

    @staticmethod
    def _build_final_chain():
        sys = (
            "你是【组织者/主持人】。现在要收尾。\n"
            "请用口语方式做2~3段总结：共识、分歧、下一步建议。\n"
            "不要清单/小标题/套话。"
        )
        prompt = ChatPromptTemplate.from_messages([
            ("system", sys),
            MessagesPlaceholder("history"),
            ("human", "{instruction}"),
        ])
        chain = prompt | llm_organizer | RunnableLambda(lambda m: m.content)
        return chain

    # ---------- Opening ----------
    def open(self, topic: str, transcript_tail: List[dict]) -> Tuple[str, List[dict], Optional[str]]:
        """
        返回：
          - opening_text: str（公开发言）
          - agenda_items: list[dict]（内部结构化议程）
          - active_item_id: Optional[str]（当前聚焦）
        """
        history: List[BaseMessage] = events_to_messages(transcript_tail)

        instruction = (
            "请为下面话题做主持开场：\n"
            "1) 先抛一个有张力的切口/争议点（80~160字，口语一点）\n"
            "2) 给出2~4个'可推进的子问题'（议程 agenda），注意：\n"
            "   - 热点事件：关注影响、原因、应对\n"
            "   - 现状分析：关注矛盾、成因、出路\n"
            "   - 未来趋势：关注机遇、挑战、路径\n"
            "   - 学习概念：关注意义、理解、应用\n"
            "3) 选择第一个讨论的焦点\n"
            "输出 JSON 格式必须严格如下：\n"
            "{"
            '"opening":"...",'
            '"agenda":["子问题1","子问题2"],'
            '"active_index":0'
            "}\n"
            f"话题：{topic}"
        )

        raw = self._opening_chain.invoke({"history": history, "instruction": instruction})
        data = _safe_json_loads(raw) or {}

        opening = clean_text(str(data.get("opening", ""))) or f"我们来聊「{topic}」。你更在意它带来的机会还是代价？"
        agenda_list = data.get("agenda", [])
        if not isinstance(agenda_list, list) or not agenda_list:
            agenda_list = [
                "我们讨论它带来的最大收益是什么？",
                "它最可能带来的代价/风险是什么？",
                "对个人而言该如何应对？",
            ]
        active_index = data.get("active_index", 0)
        try:
            active_index = int(active_index)
        except Exception:
            active_index = 0
        if active_index < 0 or active_index >= len(agenda_list):
            active_index = 0

        agenda_items: List[dict] = []
        active_item_id: Optional[str] = None
        for i, q in enumerate(agenda_list):
            item_id = uuid.uuid4().hex[:10]
            item = {
                "item_id": item_id,
                "question": clean_text(str(q)),
                "priority": 70 if i == active_index else 50,
                "status": "active" if i == active_index else "open",
                "created_by": "组织者",
            }
            agenda_items.append(item)
            if i == active_index:
                active_item_id = item_id

        return opening, agenda_items, active_item_id

    # ---------- Routing ----------
    def route(self, state: Any, transcript_tail: List[dict]) -> Dict[str, Any]:
        """
        返回 dict（给 main 用）：
          - next_speaker: str
          - task_hint: str
          - stance_hint: Optional[str]
          - ask_user: bool
          - should_end: bool
        """
        history: List[BaseMessage] = events_to_messages(transcript_tail)

        topic = _get(state, "topic", "")
        last_speaker = _get(state, "last_speaker", None)
        active_item_id = _get(state, "active_item_id", None)
        agenda = _get(state, "agenda", []) or []

        active_q = None
        if active_item_id:
            for it in agenda:
                if isinstance(it, dict) and it.get("item_id") == active_item_id:
                    active_q = it.get("question")
                    break

        # 兜底策略：避免连续同一人
        avoid = last_speaker if last_speaker in SPEAKERS else None

        instruction = (
            "请你决定下一位该叫谁发言，并给一个短任务提示。\n"
            f"- 可选发言者：{SPEAKERS}\n"
            f"- 尽量避免连续叫同一人：{avoid or '（无）'}\n"
            "\n"
            "路由策略优先级：\n"
            "1. 如果有人提出新观点或具体案例，优先叫质疑者回应\n"
            "2. 如果讨论过于抽象，优先叫实践者落地\n"
            "3. 如果概念不清或需要框架，优先叫理论家澄清\n"
            "4. 避免让同一角色重复相同内容\n"
            "\n"
            "你只输出 JSON，格式必须严格如下：\n"
            "{"
            '"next_speaker":"理论家|实践者|质疑者",'
            '"task_hint":"具体任务提示，要回应最新的观点",'
            '"stance_hint":"谨慎|乐观|悲观|中立(可省略)",'
            '"should_end":false'
            "}\n\n"
            f"话题：{topic}\n"
            f"当前聚焦问题：{active_q or '（未明确）'}\n"
            f"上一发言者：{avoid or '（无）'}\n"
            "请仔细分析最近2-3轮对话，找出需要回应的具体观点。\n"
            "注意：用户会在每次发言后参与，请设计好承接性的任务提示。"
        )

        raw = self._route_chain.invoke({"history": history, "instruction": instruction})
        data = _safe_json_loads(raw) or {}

        nxt = data.get("next_speaker", None)
        if nxt not in SPEAKERS:
            # fallback：简单轮转
            fallback = ["理论家", "实践者", "质疑者"]
            if avoid in fallback:
                fallback.remove(avoid)
            nxt = fallback[0] if fallback else "理论家"

        task_hint = clean_text(str(data.get("task_hint", "")))
        if not task_hint:
            # fallback：给一个"非模板"的柔性任务
            task_hint = "接着刚才那点往下推，不要回到开题总述。抓一个细节讲清楚。"

        stance = data.get("stance_hint", None)
        if stance not in {"谨慎", "乐观", "悲观", "中立", None}:
            stance = None

        should_end = bool(data.get("should_end", False))

        return {
            "next_speaker": nxt,
            "task_hint": task_hint,
            "stance_hint": stance,
            "should_end": should_end,
        }

    # ---------- Update state from new public event ----------
    def update_from_new_public_event(self, state: Any, transcript_tail: List[dict]) -> Dict[str, Any]:
        """
        从最近公开发言里提炼“状态更新 patch”。
        返回 patch dict，建议由 state_store.apply_patch(state, patch) 来应用。
        """
        history: List[BaseMessage] = events_to_messages(transcript_tail)

        instruction = (
            "请从最近的讨论发言中提炼状态更新。\n"
            "输出 JSON，格式必须严格如下（字段可为空数组）：\n"
            "{"
            '"add_consensus":["..."],'
            '"add_disagreements":["..."],'
            '"add_open_questions":["..."],'
            '"add_agenda":["子问题(可选)"],'
            '"style_flags":["list_like|generic|repetitive"]'
            "}\n"
            "要求：\n"
            "- add_consensus: 可复述的共识句\n"
            "- add_disagreements: 主要分歧/不同意见\n"
            "- add_open_questions: 仍需回答的追问\n"
            "- add_agenda: 新出现、值得加入议程的子问题（可选）\n"
            "- style_flags: 如果发言像清单/套话/重复，就标记\n"
        )

        raw = self._update_chain.invoke({"history": history, "instruction": instruction})
        data = _safe_json_loads(raw) or {}

        patch = {
            "add_consensus": data.get("add_consensus", []) if isinstance(data.get("add_consensus", []), list) else [],
            "add_disagreements": data.get("add_disagreements", []) if isinstance(data.get("add_disagreements", []), list) else [],
            "add_open_questions": data.get("add_open_questions", []) if isinstance(data.get("add_open_questions", []), list) else [],
            "add_agenda": data.get("add_agenda", []) if isinstance(data.get("add_agenda", []), list) else [],
            "style_flags": data.get("style_flags", []) if isinstance(data.get("style_flags", []), list) else [],
        }
        return patch

    def apply_patch(self, state: Any, patch: Dict[str, Any]):
        """一个简易 patch 应用器（你后面可以搬到 memory/state_store.py）。"""
        _append_list(state, "consensus", [str(x) for x in patch.get("add_consensus", [])])
        _append_list(state, "disagreements", [str(x) for x in patch.get("add_disagreements", [])])
        _append_list(state, "open_questions", [str(x) for x in patch.get("add_open_questions", [])])

        # 新 agenda 只做追加（你后面可以更精细：去重、优先级、激活等）
        add_agenda = patch.get("add_agenda", [])
        if isinstance(add_agenda, list) and add_agenda:
            agenda = _get(state, "agenda", []) or []
            for q in add_agenda:
                q = clean_text(str(q))
                if not q:
                    continue
                agenda.append({
                    "item_id": uuid.uuid4().hex[:10],
                    "question": q,
                    "priority": 45,
                    "status": "open",
                    "created_by": "组织者",
                })
            _set(state, "agenda", agenda)

        # style flags 累加
        flags = patch.get("style_flags", [])
        if isinstance(flags, list):
            style_health = _get(state, "style_health", {}) or {}
            for f in flags:
                style_health[str(f)] = int(style_health.get(str(f), 0)) + 1
            _set(state, "style_health", style_health)

    # ---------- Final summary ----------
    def finalize(self, state: Any, transcript_tail: List[dict]) -> str:
        history: List[BaseMessage] = events_to_messages(transcript_tail)
        topic = _get(state, "topic", "")

        instruction = (
            f"话题：{topic}\n"
            "请收尾总结，要求：\n"
            "- 2~3段口语自然段\n"
            "- 提到：目前的共识、主要分歧、给用户一个下一步建议\n"
            "- 不要清单/小标题/套话\n"
        )
        out = self._final_chain.invoke({"history": history, "instruction": instruction})
        return clean_text(out)
