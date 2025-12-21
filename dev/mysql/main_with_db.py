# main_with_db.py - 集成数据库功能的版本
from __future__ import annotations

import uuid
import sys
import os
from types import SimpleNamespace
from typing import Dict, Callable

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dev.agents.organizer_agent import OrganizerAgent
from dev.agents.theorist_tool import theorist_speak
from dev.agents.practitioner_tool import practitioner_speak
from dev.agents.skeptic_tool import skeptic_speak
from dev.agents.rewriter_tools import rewrite_if_needed
from dev.memory.history_store import history_store
from dev.memory.state_store import init_state, set_agenda, apply_patch, advance_turn, DiscussionState

# 导入数据库工具
from dev.mysql.db_utils import get_db_manager
from utils.agent_utils import AgentOutputSaver, get_conversation_tracker


# ========== 角色工具映射 ==========
TOOLS: Dict[str, Callable] = {
    "理论家": theorist_speak,
    "实践者": practitioner_speak,
    "质疑者": skeptic_speak,
}

# ========== 三位学伴的"风格参数"（额外注入，不是固定模板） ==========
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


class DatabaseIntegratedMain:
    """集成数据库功能的主程序类"""

    def __init__(self):
        self.db_manager = get_db_manager()
        self.output_saver = AgentOutputSaver()
        self.conversation_tracker = get_conversation_tracker()

        # 初始化数据库连接
        if not self.db_manager.connect():
            raise Exception("无法连接到数据库")

    def __del__(self):
        """析构函数，确保数据库连接关闭"""
        if hasattr(self, 'db_manager'):
            self.db_manager.disconnect()

    def call_companion_with_db(
        self,
        speaker: str,
        state: DiscussionState,
        task_hint: str,
        stance_hint: str | None,
        tail_n: int = 12,
    ) -> str:
        """
        调用某个学伴工具并保存到数据库
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
            focus_on_latest=True,
        )

        # 调用智能体工具
        out = TOOLS[speaker](req)
        utterance = getattr(out, "utterance", str(out))
        utterance = rewrite_if_needed(utterance)

        # 保存到数据库
        try:
            event_id = self.output_saver.save_agent_output_with_structure(
                speaker=speaker,
                output=utterance,
                thread_id=state.thread_id,
                turn_id=getattr(state, 'turn_count', 1),
                additional_tags={
                    'task_hint': task_hint,
                    'stance_hint': stance_hint,
                    'phase': getattr(state, 'phase', 'unknown')
                }
            )
            print(f"[DB保存] 事件ID: {event_id}")
        except Exception as e:
            print(f"[DB错误] 保存失败: {e}")

        return utterance

    def save_user_input_to_db(self, thread_id: str, user_input: str, input_type: str = "interjection"):
        """保存用户输入到数据库"""
        try:
            event_id = self.db_manager.save_agent_output(
                speaker="用户",
                content=user_input,
                thread_id=thread_id,
                tags={
                    'input_type': input_type,
                    'is_user': True
                }
            )
            print(f"[DB保存] 用户输入已保存: {event_id}")
        except Exception as e:
            print(f"[DB错误] 保存用户输入失败: {e}")

    def save_organizer_output(self, thread_id: str, content: str, output_type: str):
        """保存组织者输出到数据库"""
        try:
            event_id = self.output_saver.save_agent_output_with_structure(
                speaker="组织者",
                output=content,
                thread_id=thread_id,
                additional_tags={
                    'output_type': output_type,
                    'is_organizer': True
                }
            )
            print(f"[DB保存] 组织者{output_type}已保存: {event_id}")
        except Exception as e:
            print(f"[DB错误] 保存组织者{output_type}失败: {e}")

    def run_one_topic_with_db(self, topic: str) -> bool:
        """
        跑一轮话题讨论并保存到数据库
        返回 True 表示继续外层循环（输入新话题），False 表示退出程序
        """
        # 生成新的线程ID并开始对话跟踪
        thread_id = uuid.uuid4().hex[:12]
        self.conversation_tracker.continue_thread(thread_id)

        state = init_state(thread_id=thread_id, topic=topic)
        organizer = OrganizerAgent()

        # 保存用户提出的话题
        history_store.record_user(thread_id, topic, tags=["topic"])
        advance_turn(state, "用户")
        self.save_user_input_to_db(thread_id, topic, "topic")

        # 组织者开场
        opening, agenda_items, active_item_id = organizer.open(topic, history_store.tail(thread_id, 8))
        opening = rewrite_if_needed(opening)

        history_store.record_speaker(thread_id, "组织者", opening, tags=["opening"])
        advance_turn(state, "组织者")
        self.save_organizer_output(thread_id, opening, "opening")

        set_agenda(state, agenda_items, active_item_id)
        state.phase = "discussion"

        print(f"\n=== 新话题（thread_id={thread_id}）：{topic} ===")
        print("\n--- 组织者开场 ---")
        print(opening)

        MAX_STEPS = 30
        step = 0

        while step < MAX_STEPS:
            step += 1

            # 组织者动态路由
            decision = organizer.route(state, history_store.tail(thread_id, 12))
            next_speaker = decision["next_speaker"]
            task_hint = decision["task_hint"]
            stance_hint = decision.get("stance_hint")

            # 调用智能体并保存到数据库
            utterance = self.call_companion_with_db(
                speaker=next_speaker,
                state=state,
                task_hint=task_hint,
                stance_hint=stance_hint,
                tail_n=6,
            )

            # 记录到历史存储
            history_store.record_speaker(thread_id, next_speaker, utterance)
            advance_turn(state, next_speaker)

            print(f"\n--- {next_speaker} ---")
            print(utterance)

            # 组织者更新状态
            patch = organizer.update_from_new_public_event(state, history_store.tail(thread_id, 12))
            apply_patch(state, patch)

            # 用户交互
            user_input = input(f"\n{next_speaker}发言完毕。你可以：直接发言参与讨论、回车继续、/end总结、/new新话题、/quit退出\n> ").strip()

            # 处理控制命令
            if user_input.lower() in {"/quit", "quit", "exit"}:
                return False
            if user_input.lower() == "/end":
                break
            if user_input.lower() == "/new":
                break

            # 处理用户输入
            if user_input:
                print(f"\n--- 用户：{user_input} ---")

                # 保存用户输入
                history_store.record_user(thread_id, user_input, tags=["interject"])
                state.last_user_interjection = user_input
                advance_turn(state, "用户")
                self.save_user_input_to_db(thread_id, user_input, "interjection")

                # 用户插话后的状态更新
                patch2 = organizer.update_from_new_public_event(state, history_store.tail(thread_id, 12))
                apply_patch(state, patch2)

                # 选择回应的智能体
                if any(kw in user_input.lower() for kw in ["什么是", "如何", "怎么", "为什么", "哪些"]):
                    responder = "理论家"
                    task_hint = f"请直接回答用户的问题：{user_input}，用具体例子说明概念。"
                elif any(kw in user_input.lower() for kw in ["技能", "框架", "工具", "方法"]):
                    responder = "实践者"
                    task_hint = f"请具体回答用户关于{user_input}的问题，给出实际的学习路径建议。"
                else:
                    available = [s for s in ["理论家", "实践者", "质疑者"] if s != next_speaker]
                    responder = available[0] if available else "理论家"
                    task_hint = f"请回应用户提出的问题：{user_input}"

                # 智能体回应用户
                response = self.call_companion_with_db(
                    speaker=responder,
                    state=state,
                    task_hint=task_hint,
                    stance_hint=None,
                    tail_n=8,
                )

                # 记录回应
                history_store.record_speaker(thread_id, responder, response)
                advance_turn(state, responder)

                print(f"\n--- {responder} ---")
                print(response)

                # 更新状态
                patch3 = organizer.update_from_new_public_event(state, history_store.tail(thread_id, 12))
                apply_patch(state, patch3)

        # 组织者总结
        state.phase = "closing"
        summary = organizer.finalize(state, history_store.tail(thread_id, 20))
        summary = rewrite_if_needed(summary)

        history_store.record_speaker(thread_id, "组织者", summary, tags=["summary"])
        advance_turn(state, "组织者")
        self.save_organizer_output(thread_id, summary, "summary")

        print("\n--- 组织者总结 ---")
        print(summary)
        print(f"\n（本话题结束，thread_id={thread_id}，历史条数={history_store.size(thread_id)}）\n")

        # 显示数据库统计信息
        try:
            thread_summary = self.output_saver.get_thread_summary(thread_id)
            print(f"[数据库统计] 事件数: {thread_summary['event_count']}, "
                  f"发言者: {list(thread_summary['speakers'].keys())}, "
                  f"共识: {thread_summary['consensus_count']}, "
                  f"分歧: {thread_summary['disagreement_count']}, "
                  f"开放问题: {thread_summary['open_question_count']}")
        except Exception as e:
            print(f"[DB错误] 获取统计信息失败: {e}")

        return True

    def show_recent_conversations(self, limit: int = 5):
        """显示最近的对话线程"""
        try:
            recent_threads = self.db_manager.get_latest_threads(limit)
            if recent_threads:
                print(f"\n=== 最近的 {len(recent_threads)} 个对话线程 ===")
                for thread in recent_threads:
                    print(f"线程ID: {thread['thread_id']}")
                    print(f"事件数: {thread['event_count']}")
                    print(f"发言者: {thread['speakers']}")
                    print(f"最后活动: {thread['latest_event_time']}")
                    print("-" * 40)
            else:
                print("暂无对话记录")
        except Exception as e:
            print(f"获取最近对话失败: {e}")

    def search_conversations(self, keyword: str, limit: int = 10):
        """搜索对话内容"""
        try:
            events = self.db_manager.search_events(keyword, limit)
            if events:
                print(f"\n=== 搜索结果：'{keyword}'（{len(events)}条） ===")
                for event in events:
                    print(f"[{event['created_at']}] {event['speaker']}: {event['content'][:100]}...")
                    print(f"  线程ID: {event['thread_id']}")
                    print("-" * 40)
            else:
                print(f"未找到包含'{keyword}'的对话")
        except Exception as e:
            print(f"搜索失败: {e}")


def main():
    """主函数"""
    print("=== 智炬五维：协同学习对话（数据库集成版）===")
    print("功能：输入话题开始；/recent查看最近对话；/search关键词搜索；/quit退出。\n")

    try:
        app = DatabaseIntegratedMain()

        # 显示欢迎信息和最近对话
        app.show_recent_conversations(3)

        while True:
            user_input = input("User(话题/命令)> ").strip()
            if not user_input:
                continue

            # 处理命令
            if user_input.lower() in {"/quit", "quit", "exit"}:
                break
            elif user_input.lower() == "/recent":
                app.show_recent_conversations()
                continue
            elif user_input.lower().startswith("/search"):
                parts = user_input.split(maxsplit=1)
                keyword = parts[1] if len(parts) > 1 else ""
                if keyword:
                    app.search_conversations(keyword)
                else:
                    print("请提供搜索关键词，例如：/search 人工智能")
                continue
            elif user_input.startswith("/"):
                print(f"未知命令: {user_input}，支持的命令：/recent, /search, /quit")
                continue

            # 运行话题讨论
            cont = app.run_one_topic_with_db(user_input)
            if not cont:
                break

    except Exception as e:
        print(f"程序初始化失败: {e}")
        print("请检查数据库连接配置和依赖包安装")
        return 1

    print("感谢使用！")
    return 0


if __name__ == "__main__":
    exit(main())