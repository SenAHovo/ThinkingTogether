# main.py
from __future__ import annotations

import os
import sys
import uuid
from types import SimpleNamespace
from typing import Dict, Callable

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dev.agents.organizer_agent import OrganizerAgent
from dev.agents.theorist_tool import theorist_speak
from dev.agents.practitioner_tool import practitioner_speak
from dev.agents.skeptic_tool import skeptic_speak

from dev.agents.rewriter_tools import rewrite_if_needed
from dev.memory.history_store import history_store
from dev.memory.state_store import init_state, set_agenda, apply_patch, advance_turn, DiscussionState, load_state_from_db


# ========== 角色工具映射 ==========
TOOLS: Dict[str, Callable] = {
    "理论家": theorist_speak,
    "实践者": practitioner_speak,
    "质疑者": skeptic_speak,
}

# ========== 三位学伴的“风格参数”（额外注入，不是固定模板） ==========
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


def call_companion(
    speaker: str,
    state: DiscussionState,
    task_hint: str,
    stance_hint: str | None,
    tail_n: int = 12,
) -> str:
    """
    调用某个学伴工具，让它“基于最近讨论发言”继续讨论。
    注意：这里用 SimpleNamespace 构造 req，避免你 companion_tool_io 的 pydantic 校验问题。
    """
    transcript_tail = history_store.tail(state.thread_id, n=tail_n)

    req = SimpleNamespace(
        thread_id=state.thread_id,
        speaker=speaker,
        state=state,
        transcript_tail=transcript_tail,
        task_hint=task_hint,
        stance_hint=stance_hint,
        style=STYLE_BY_SPEAKER[speaker],
        # 添加一个标志，强调需要关注最新内容
        focus_on_latest=True,
    )

    out = TOOLS[speaker](req)  # 返回 CompanionSpeakOutput（pydantic/dict 都行，使用属性访问）
    utterance = getattr(out, "utterance", str(out))
    utterance = rewrite_if_needed(utterance)  # 全局再兜底一次去模板
    return utterance


def run_one_topic(topic: str) -> bool:
    """
    跑一轮话题讨论。
    返回 True 表示继续外层循环（输入新话题），False 表示退出程序。
    """
    thread_id = uuid.uuid4().hex[:12]

    # 尝试从数据库加载已有状态，如果没有则创建新的
    state = load_state_from_db(thread_id)
    if not state:
        state = init_state(thread_id=thread_id, topic=topic)
    else:
        state.topic = topic  # 更新话题

    organizer = OrganizerAgent()

    # 记录用户给出的"话题"（公开发言）
    history_store.record_user(thread_id, topic, tags=["topic"], topic=topic)
    advance_turn(state, "用户")

    # 组织者开场（公开发言）+ 初始化 agenda
    opening, agenda_items, active_item_id = organizer.open(topic, history_store.tail(thread_id, 8))
    opening = rewrite_if_needed(opening)
    history_store.record_speaker(thread_id, "组织者", opening, tags=["opening"])
    advance_turn(state, "组织者")

    set_agenda(state, agenda_items, active_item_id)
    state.phase = "discussion"

    print(f"\n=== 新话题（thread_id={thread_id}）：{topic} ===")
    print("\n--- 组织者开场 ---")
    print(opening)

    MAX_STEPS = 30  # 防止无限循环
    step = 0

    while step < MAX_STEPS:
        step += 1

        # 组织者动态路由：决定下一位发言者 + 任务提示
        decision = organizer.route(state, history_store.tail(thread_id, 12))
        next_speaker = decision["next_speaker"]
        task_hint = decision["task_hint"]
        stance_hint = decision.get("stance_hint")

        # 调用对应学伴工具，减少历史上下文以提高针对性
        utterance = call_companion(
            speaker=next_speaker,
            state=state,
            task_hint=task_hint,
            stance_hint=stance_hint,
            tail_n=6,  # 减少到最近6条，避免被过多历史信息干扰
        )

        # 记录学伴公开发言
        history_store.record_speaker(thread_id, next_speaker, utterance)
        advance_turn(state, next_speaker)

        print(f"\n--- {next_speaker} ---")
        print(utterance)

        # 组织者从最新公开发言中提炼 patch 并更新 state
        patch = organizer.update_from_new_public_event(state, history_store.tail(thread_id, 12))
        apply_patch(state, patch)

        # 统一的用户交互询问：每次智能体发言后都询问用户
        user_input = input(f"\n{next_speaker}发言完毕。你可以：直接发言参与讨论、回车继续、/end总结、/new新话题、/quit退出\n> ").strip()

        # 处理控制命令
        if user_input.lower() in {"/quit", "quit", "exit"}:
            return False
        if user_input.lower() == "/end":
            break
        if user_input.lower() == "/new":
            break

        # 如果用户输入了内容，则让智能体回应
        if user_input:
            print(f"\n--- 用户：{user_input} ---")

            # 用户公开发言写入共享历史
            history_store.record_user(thread_id, user_input, tags=["interject"], topic=topic)
            state.last_user_interjection = user_input
            advance_turn(state, "用户")

            # 用户插话会改变走向：让组织者从插话中提炼更新
            patch2 = organizer.update_from_new_public_event(state, history_store.tail(thread_id, 12))
            apply_patch(state, patch2)

            # 分析用户问题类型，选择合适的智能体回应
            if any(kw in user_input.lower() for kw in ["什么是", "如何", "怎么", "为什么", "哪些"]):
                # 学习类问题，优先理论家
                responder = "理论家"
                task_hint = f"请直接回答用户的问题：{user_input}，用具体例子说明概念。"
            elif any(kw in user_input.lower() for kw in ["技能", "框架", "工具", "方法"]):
                # 实践类问题，优先实践者
                responder = "实践者"
                task_hint = f"请具体回答用户关于{user_input}的问题，给出实际的学习路径建议。"
            else:
                # 其他问题，选择还没发言的角色
                available = [s for s in ["理论家", "实践者", "质疑者"] if s != next_speaker]
                responder = available[0] if available else "理论家"
                task_hint = f"请回应用户提出的问题：{user_input}"

            # 调用智能体直接回应用户
            response = call_companion(
                speaker=responder,
                state=state,
                task_hint=task_hint,
                stance_hint=None,
                tail_n=8,  # 包含用户问题的最近8条记录
            )

            # 记录回应
            history_store.record_speaker(thread_id, responder, response)
            advance_turn(state, responder)

            print(f"\n--- {responder} ---")
            print(response)

            # 更新状态
            patch3 = organizer.update_from_new_public_event(state, history_store.tail(thread_id, 12))
            apply_patch(state, patch3)

    # 组织者总结收尾
    state.phase = "closing"
    summary = organizer.finalize(state, history_store.tail(thread_id, 20))
    summary = rewrite_if_needed(summary)
    history_store.record_speaker(thread_id, "组织者", summary, tags=["summary"])
    advance_turn(state, "组织者")

    print("\n--- 组织者总结 ---")
    print(summary)
    print(f"\n（本话题结束，thread_id={thread_id}，历史条数={history_store.size(thread_id)}）\n")

    return True


def show_database_stats():
    """显示数据库统计信息"""
    if os.getenv('USE_PERSISTENT_STORAGE', 'true').lower() != 'true':
        print("持久化存储未启用")
        return

    try:
        from dev.mysql.persistent_store import persistent_history_store
        # 这里可以添加更多统计功能
        print("数据库统计功能正在开发中...")
    except Exception as e:
        print(f"获取统计信息失败: {e}")


def main():
    print("=== 智炬五维：协同学习对话（集成数据库版）===")
    print("命令：输入话题开始 /stats统计 /quit退出")
    print(f"持久化存储: {'启用' if os.getenv('USE_PERSISTENT_STORAGE', 'true').lower() == 'true' else '禁用'}\n")

    while True:
        user_input = input("User(话题/命令)> ").strip()
        if not user_input:
            continue

        # 处理命令
        if user_input.lower() in {"/quit", "quit", "exit"}:
            break
        elif user_input.lower() == "/stats":
            show_database_stats()
            continue
        elif user_input.startswith("/"):
            print(f"未知命令: {user_input}")
            continue

        # 运行话题讨论
        cont = run_one_topic(user_input)
        if not cont:
            break


if __name__ == "__main__":
    main()
