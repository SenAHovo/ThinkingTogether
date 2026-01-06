# agents/practitioner_tool.py
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
from .model_client import llm_practitioner


_PRACTITIONER_SYS = """
        你是一个真实小组讨论里的【实践者】（不是写作文、不是答题机器人）。

        【核心能力】
        - 场景落地：将抽象讨论转化为具体的生活、工作、学习场景
        - 约束分析：识别现实中的成本、时间、资源、风险等约束条件
        - 可行性判断：评估什么能做到、什么不能做到、如何权衡
        - 执行建议：提出具体可操作的小步骤，避免空泛建议

        【适应不同话题】
        - **热点事件**：分析对普通人生活的影响、可能的应对措施
        - **现状分析**：从具体案例出发，讨论实际的困难和解决办法
        - **未来趋势**：考虑技术可行性、市场接受度、实施路径
        - **学习概念**：用具体例子说明概念，提供实践入门方法
        - **课程学习**：提供具体学习方法、练习项目、资源推荐、记忆技巧
        - **编程问题**：给出代码实现方案、库选择建议、调试技巧、工程实践
        - **科学探索**：设计实验步骤、推荐数据分析工具、指导验证方法、仪器使用

        你的自然倾向：
        - 把讨论落到一个具体场景（生活/学习/工作）
        - 讲清现实约束：成本、时间、风险、资源
        - 给一个可执行的小动作（不是一长串清单）
        - 善于用身边例子说明复杂问题

        你的语气：像靠谱朋友聊天，直接、接地气，但不油腻。

        强禁忌：
        - 不要编号清单/项目符号/小标题
        - 不要用"以下是/主要包括/综上/总之/首先其次最后"这类套话
        - 不要做全面盘点，不要把话题从头讲一遍

        你要做的事：基于"最近讨论发言"继续往下推进，用一个场景把点讲清楚。
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
    ("system", _PRACTITIONER_SYS),
    MessagesPlaceholder("history"),
    ("human", "{context_card}"),
])

# 角色生成温度（更自然一点）
_chain = _prompt | llm_practitioner | RunnableLambda(lambda m: m.content)
# 重写温度（稳一点）
_rewrite_chain = _prompt | llm_practitioner | RunnableLambda(lambda m: m.content)


def practitioner_speak(req: CompanionSpeakInput) -> CompanionSpeakOutput:
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
- 必须回应最近1-2轮发言中的具体观点或问题
- 如果前面有抽象概念，请用新例子说明（不要重复之前的例子）
- 如果前面有质疑，请给出具体的解决方案或应对方法
- 避免重复相同的场景或建议
- CRITICAL: 你的发言必须与前面某人的观点产生直接对话关系！

【发言要求】
请基于"最近讨论发言"继续往下说：优先选择一个具体场景，把"现实约束 + 具体建议"讲清楚，充分展开你的方案。
如果用户最近提出了问题或观点，你的第一句就应该直接回应用户，然后再展开分析。
不要回到题目开头做总述，不要写清单/小标题/套话。
输出2~4段口语自然段，让你的建议更加详细和可操作。
"""

    utterance = clean_text(_chain.invoke({"history": history, "context_card": context_card}))

    if is_templated(utterance):
        utterance = clean_text(_rewrite_chain.invoke({
            "history": history,
            "context_card": build_rewrite_context(utterance),
        }))

    hooks: List[Hook] = []

    # 简单动作信号：包含这些词常常意味着给了建议
    if any(k in utterance for k in ["建议", "可以先", "不妨", "试试", "下一步", "先从", "最实际的是", "落到具体就是"]):
        hooks.append(Hook(kind="action", content="给出可执行动作/策略或现实约束"))

    # 如果提供例子/场景
    if any(k in utterance for k in ["比如", "举个", "就像", "我见过", "我身边", "场景"]):
        hooks.append(Hook(kind="evidence", content="提供了一个场景/例子来支撑观点"))

    q = _extract_last_question(utterance)
    if q:
        hooks.append(Hook(kind="new_question", content=q))

    return CompanionSpeakOutput(
        speaker="实践者",
        utterance=utterance,
        hooks=hooks,
    )


async def practitioner_speak_stream(req: CompanionSpeakInput, stream_callback: Callable) -> CompanionSpeakOutput:
    """
    实践者工具流式版本：实时推送内容片段到前端
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
- 必须回应最近1-2轮发言中的具体观点或问题
- 如果前面有抽象概念，请用新例子说明（不要重复之前的例子）
- 如果前面有质疑，请给出具体的解决方案或应对方法
- 避免重复相同的场景或建议
- CRITICAL: 你的发言必须与前面某人的观点产生直接对话关系！

【发言要求】
请基于"最近讨论发言"继续往下说：优先选择一个具体场景，把"现实约束 + 具体建议"讲清楚，充分展开你的方案。
如果用户最近提出了问题或观点，你的第一句就应该直接回应用户，然后再展开分析。
不要回到题目开头做总述，不要写清单/小标题/套话。
输出2~4段口语自然段，让你的建议更加详细和可操作。
"""

    # 流式生成
    prompt_messages = _prompt.invoke({"history": history, "context_card": context_card})
    full_content = ""

    async for chunk in llm_practitioner.astream(prompt_messages):
        content = chunk.content if hasattr(chunk, 'content') else str(chunk)
        if content:
            full_content += content
            try:
                await stream_callback({
                    "type": "stream_chunk",
                    "role": "practitioner",
                    "speaker": "实践者",
                    "content": content
                })
            except Exception as e:
                print(f"[ERROR] 流式推送失败: {e}")

    utterance = clean_text(full_content)

    # 反模板检查
    if is_templated(utterance):
        print("[实践者] 检测到模板化内容，触发重写...")
        rewrite_card = build_rewrite_context(utterance)
        rewrite_messages = _prompt.invoke({"history": history, "context_card": rewrite_card})

        # 发送重写开始信号，让前端知道要替换内容
        try:
            await stream_callback({
                "type": "stream_rewrite_start",
                "role": "practitioner",
                "speaker": "实践者"
            })
        except Exception as e:
            print(f"[ERROR] 重写开始信号推送失败: {e}")

        full_content = ""

        async for chunk in llm_practitioner.astream(rewrite_messages):
            content = chunk.content if hasattr(chunk, 'content') else str(chunk)
            if content:
                full_content += content
                try:
                    await stream_callback({
                        "type": "stream_chunk",
                        "role": "practitioner",
                        "speaker": "实践者",
                        "content": content
                    })
                except Exception as e:
                    print(f"[ERROR] 重写流式推送失败: {e}")

        utterance = clean_text(full_content)
        print(f"[实践者] 重写完成，新内容长度: {len(utterance)}")

    # 推送流结束信号
    try:
        await stream_callback({
            "type": "stream_end",
            "role": "practitioner",
            "speaker": "实践者",
            "full_content": utterance
        })
    except Exception as e:
        print(f"[ERROR] 流结束信号推送失败: {e}")

    hooks: List[Hook] = []

    if any(k in utterance for k in ["建议", "可以先", "不妨", "试试", "下一步", "先从", "最实际的是", "落到具体就是"]):
        hooks.append(Hook(kind="action", content="给出可执行动作/策略或现实约束"))

    if any(k in utterance for k in ["比如", "举个", "就像", "我见过", "我身边", "场景"]):
        hooks.append(Hook(kind="evidence", content="提供了一个场景/例子来支撑观点"))

    q = _extract_last_question(utterance)
    if q:
        hooks.append(Hook(kind="new_question", content=q))

    return CompanionSpeakOutput(
        speaker="实践者",
        utterance=utterance,
        hooks=hooks,
    )
