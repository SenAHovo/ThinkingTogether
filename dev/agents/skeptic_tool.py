# agents/skeptic_tool.py
from __future__ import annotations

from typing import List, Optional, Any, Callable

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
from .model_client import llm_skeptic


_SKEPTIC_SYS = """
        你是一个真实小组讨论里的【质疑者】（不是抬杠机器，也不是写作文）。

        【核心能力】
        - 逻辑检验：识别推理过程中的跳跃、矛盾、漏洞
        - 证据评估：判断论据是否充分、可靠、相关
        - 假设揭示：挖掘隐藏的前提和未言明的假设
        - 风险识别：指出可能的负面影响、意外后果

        【适应不同话题】
        - **热点事件**：质疑信息来源、因果推断、情绪化判断
        - **现状分析**：挑战归因逻辑、数据可信度、样本偏差
        - **未来趋势**：质疑预测依据、线性外推、技术决定论
        - **学习概念**：质疑定义准确性、适用边界、过度简化

        你的自然倾向：
        - 抓"说空/说满/跳步"的地方：偷换概念、证据不足、忽略代价、结论过早
        - 提出一个关键追问，或者给出更稳的表述（加上必要条件/范围）
        - 善于从反例和边界情况中发现问题
        - 区分"不可能"和"有条件限制"

        你的语气：犀利但友善，不刻薄，不人身攻击。

        强禁忌：
        - 不要编号清单/项目符号/小标题
        - 不要用"以下是/主要包括/综上/总之/首先其次最后"这类套话
        - 不要做全面盘点，不要把话题从头讲一遍

        你要做的事：基于"最近讨论发言"继续往下推进，插入一个关键质疑点，让讨论更严谨。
        输出：1~2段中文口语自然段即可。
"""


def _active_question_from_state(state: Any) -> Optional[str]:
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
    import re
    qs = re.findall(r"[^。！？!\n]*[？?]", t)
    return qs[-1].strip() if qs else None


_prompt = ChatPromptTemplate.from_messages([
    ("system", _SKEPTIC_SYS),
    MessagesPlaceholder("history"),
    ("human", "{context_card}"),
])

_chain = _prompt | llm_skeptic | RunnableLambda(lambda m: m.content)
_rewrite_chain = _prompt | llm_skeptic | RunnableLambda(lambda m: m.content)


def skeptic_speak(req: CompanionSpeakInput) -> CompanionSpeakOutput:
    history: List[BaseMessage] = events_to_messages(req.transcript_tail)

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

【最重要的优先级】
1. 如果最近一轮是【用户】发言，你必须优先回应用户的具体问题或观点！
2. 用户参与这个讨论是为了得到有价值的回应，不要忽略用户的需求
3. 你的回应应该让用户感觉"被听到了"和"被理解了"

【重要提醒】
- 必须针对最近1-2轮发言中的具体观点进行质疑
- 及时回应新提出的观点或案例，不要延迟质疑
- 质疑要有针对性，不要泛泛而谈
- 提出建设性的替代观点或改进建议
- CRITICAL: 你的质疑必须针对前面某人刚刚提出的具体观点！

【发言要求】
请基于"最近讨论发言"继续往下说：挑一个可能说空/说满/跳步的点质疑。
但不要只否定：要补一个"更稳的说法/必要条件/边界"，并抛出一个关键追问推动讨论。
如果用户最近提出了问题或观点，你的第一句就应该直接回应用户，然后再展开分析。
不要回到题目开头做总述，不要写清单/小标题/套话。
输出1~2段口语自然段即可。
"""

    utterance = clean_text(_chain.invoke({"history": history, "context_card": context_card}))

    if is_templated(utterance):
        utterance = clean_text(_rewrite_chain.invoke({
            "history": history,
            "context_card": build_rewrite_context(utterance),
        }))

    hooks: List[Hook] = []

    # 质疑信号（非常粗略但实用）
    if any(k in utterance for k in ["但", "未必", "前提", "证据", "反例", "成本", "风险", "漏洞", "假设"]):
        hooks.append(Hook(kind="challenge", content="提出关键质疑/风险/前提条件"))

    q = _extract_last_question(utterance)
    if q:
        hooks.append(Hook(kind="new_question", content=q))

    return CompanionSpeakOutput(
        speaker="质疑者",
        utterance=utterance,
        hooks=hooks,
    )


async def skeptic_speak_stream(req: CompanionSpeakInput, stream_callback: Callable) -> CompanionSpeakOutput:
    """
    质疑者工具流式版本：实时推送内容片段到前端
    """
    history: List[BaseMessage] = events_to_messages(req.transcript_tail)

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

【最重要的优先级】
1. 如果最近一轮是【用户】发言，你必须优先回应用户的具体问题或观点！
2. 用户参与这个讨论是为了得到有价值的回应，不要忽略用户的需求
3. 你的回应应该让用户感觉"被听到了"和"被理解了"

【重要提醒】
- 必须针对最近1-2轮发言中的具体观点进行质疑
- 及时回应新提出的观点或案例，不要延迟质疑
- 质疑要有针对性，不要泛泛而谈
- 提出建设性的替代观点或改进建议
- CRITICAL: 你的质疑必须针对前面某人刚刚提出的具体观点！

【发言要求】
请基于"最近讨论发言"继续往下说：挑一个可能说空/说满/跳步的点质疑。
但不要只否定：要补一个"更稳的说法/必要条件/边界"，并抛出一个关键追问推动讨论。
如果用户最近提出了问题或观点，你的第一句就应该直接回应用户，然后再展开分析。
不要回到题目开头做总述，不要写清单/小标题/套话。
输出1~2段口语自然段即可。
"""

    # 流式生成
    prompt_messages = _prompt.invoke({"history": history, "context_card": context_card})
    full_content = ""

    async for chunk in llm_skeptic.astream(prompt_messages):
        content = chunk.content if hasattr(chunk, 'content') else str(chunk)
        if content:
            full_content += content
            try:
                await stream_callback({
                    "type": "stream_chunk",
                    "role": "skeptic",
                    "speaker": "质疑者",
                    "content": content
                })
            except Exception as e:
                print(f"[ERROR] 流式推送失败: {e}")

    utterance = clean_text(full_content)

    # 反模板检查
    if is_templated(utterance):
        rewrite_card = build_rewrite_context(utterance)
        rewrite_messages = _prompt.invoke({"history": history, "context_card": rewrite_card})
        full_content = ""

        async for chunk in llm_skeptic.astream(rewrite_messages):
            content = chunk.content if hasattr(chunk, 'content') else str(chunk)
            if content:
                full_content += content
                try:
                    await stream_callback({
                        "type": "stream_chunk",
                        "role": "skeptic",
                        "speaker": "质疑者",
                        "content": content
                    })
                except Exception as e:
                    print(f"[ERROR] 重写流式推送失败: {e}")

        utterance = clean_text(full_content)

    # 推送流结束信号
    try:
        await stream_callback({
            "type": "stream_end",
            "role": "skeptic",
            "speaker": "质疑者",
            "full_content": utterance
        })
    except Exception as e:
        print(f"[ERROR] 流结束信号推送失败: {e}")

    hooks: List[Hook] = []

    if any(k in utterance for k in ["但", "未必", "前提", "证据", "反例", "成本", "风险", "漏洞", "假设"]):
        hooks.append(Hook(kind="challenge", content="提出关键质疑/风险/前提条件"))

    q = _extract_last_question(utterance)
    if q:
        hooks.append(Hook(kind="new_question", content=q))

    return CompanionSpeakOutput(
        speaker="质疑者",
        utterance=utterance,
        hooks=hooks,
    )
