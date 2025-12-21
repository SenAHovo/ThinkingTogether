# agents/theorist_tool.py
from __future__ import annotations

from typing import List, Optional, Any

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import BaseMessage
from langchain_core.runnables import RunnableLambda

from ._shared import (
    clean_text,
    is_templated,
    build_rewrite_context,
    pick_tic,
    taboos_text,
)
from dev.memory.history_store import events_to_messages
from utils.companion_tool_io import CompanionSpeakInput, CompanionSpeakOutput, Hook
from .model_client import llm_theorist


# -------------------------
# Persona (Theorist)
# -------------------------
_THEORIST_SYS = """
你是一个真实小组讨论里的【理论家】（不是写作文、不是答题机器人）。

【核心能力】
- 建立认知框架：识别核心概念、边界条件、判断标准、关键变量
- 多维思考：从技术、社会、时间、价值等多个角度分析问题
- 结构化分析：梳理要素关系、形成机制、影响路径
- 概念辨析：澄清模糊认知、区分不同层面、建立理解阶梯

【适应不同话题】
- **热点事件**：分析深层原因、系统性影响、结构性矛盾
- **现状分析**：梳理形成机制、关键要素、发展阶段
- **未来趋势**：识别驱动因素、演变逻辑、可能路径
- **学习概念**：构建知识框架、理解核心原理、建立认知体系

你的自然倾向：
- 先把"概念、边界条件、判断标准、关键变量"讲清楚
- 不喜欢空泛结论，宁可说"要区分两种情况/要看前提是什么"
- 善于从具体案例提炼一般性思考框架

你的语气：克制、谨慎、像研究生讨论；不装腔，不引用教材式大纲。

强禁忌：
- 不要编号清单/项目符号/小标题
- 不要用"以下是/主要包括/综上/总之/首先其次最后"这类套话
- 不要做全面盘点，不要把话题从头讲一遍

你要做的事：基于"最近讨论发言"继续往下推进，抓住其中一个具体细节展开。
输出：1~2段中文口语自然段即可。
"""


def _active_question_from_state(state: Any) -> Optional[str]:
    """从 state 里取当前 active agenda 的 question（如果有）。"""
    try:
        active_id = getattr(state, "active_item_id", None)
        if not active_id:
            return None
        agenda = getattr(state, "agenda", None) or []
        for item in agenda:
            if isinstance(item, dict):
                if item.get("item_id") == active_id:
                    return item.get("question")
            else:
                if getattr(item, "item_id", None) == active_id:
                    return getattr(item, "question", None)
    except Exception:
        return None
    return None


def _extract_last_question(text: str) -> Optional[str]:
    t = (text or "").strip()
    if "？" not in t and "?" not in t:
        return None
    # 尽量取最后一个问句
    import re
    qs = re.findall(r"[^。！？!\n]*[？?]", t)
    return qs[-1].strip() if qs else None


# prompt: history 是“公开发言消息序列”，context_card 是“本轮内部任务卡片”（不写入共享历史）
_prompt = ChatPromptTemplate.from_messages([
    ("system", _THEORIST_SYS),
    MessagesPlaceholder("history"),
    ("human", "{context_card}"),
])

# 角色生成温度（更稳一点）
_chain = _prompt | llm_theorist | RunnableLambda(lambda m: m.content)
# 重写温度（更稳，减少跑题）
_rewrite_chain = _prompt | llm_theorist | RunnableLambda(lambda m: m.content)


def theorist_speak(req: CompanionSpeakInput) -> CompanionSpeakOutput:
    """
    理论家工具：读讨论上下文 + 主持任务提示 -> 输出一段讨论发言 + hooks
    注意：不负责写共享历史（由主循环/组织者统一写 public utterance）
    """
    # 1) 把最近公开发言转成 messages（让模型把它当对话而不是题干）
    history: List[BaseMessage] = events_to_messages(req.transcript_tail)

    # 2) 组织内部“本轮任务卡片”（不会进入共享历史）
    active_q = _active_question_from_state(req.state)
    tic = pick_tic(req.style)
    taboos = taboos_text(req.style)

    context_card = f"""
【讨论状态】
- 当前话题：{req.state.topic}
- 当前焦点：{active_q or "（主持人尚未明确焦点/或暂不需要聚焦）"}
- 主持人给你的任务提示：{req.task_hint or "（无）"}
- 你的立场提示：{req.stance_hint or "（无）"}
- 你的表达气质：{req.style.vibe}
- 可选口头禅：{tic or "（无）"}
- 禁忌：{taboos}

【重要提醒】
- 必须回应最近1-2轮发言中的具体观点或问题
- 避免重复之前已经讨论过的内容
- 如果前面有案例或具体说法，请从中提炼理论要点
- 不要重新解释基础概念，而是在原有讨论基础上深化
- CRITICAL: 你的发言必须与前面某人的观点产生直接对话关系！

【发言要求】
请基于"最近讨论发言"继续往下说：抓住一个具体点推进（概念/边界/变量/判断标准）。
不要回到题目开头做总述，不要写清单/小标题/套话。
输出1~2段口语自然段即可。
"""

    # 3) 生成
    utterance = clean_text(_chain.invoke({"history": history, "context_card": context_card}))

    # 4) 反模板：触发则用同角色更稳温度重写（保留意思，改成口语自然段）
    if is_templated(utterance):
        rewrite_card = build_rewrite_context(utterance)
        utterance = clean_text(_rewrite_chain.invoke({"history": history, "context_card": rewrite_card}))

    # 5) hooks：给组织者做路由参考（先简单，不强求）
    hooks: List[Hook] = []

    # 线索：理论家常见“澄清/边界”信号
    if any(k in utterance for k in ["需要区分", "边界", "前提", "关键变量", "判断标准", "换句话说", "从概念上讲"]):
        hooks.append(Hook(kind="clarify", content="提出概念澄清/边界条件/判断标准"))

    q = _extract_last_question(utterance)
    if q:
        hooks.append(Hook(kind="new_question", content=q))

    return CompanionSpeakOutput(
        speaker="理论家",
        utterance=utterance,
        hooks=hooks,
    )
