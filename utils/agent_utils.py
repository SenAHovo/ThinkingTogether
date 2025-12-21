"""
智能体工具模块
提供智能体相关的通用功能和数据库集成
"""

import re
from typing import Dict, Any, Optional, List
from datetime import datetime
from dev.mysql.db_utils import get_db_manager


class AgentOutputSaver:
    """智能体输出保存器"""

    def __init__(self):
        self.db_manager = get_db_manager()

    def parse_output(self, output: str) -> Dict[str, Any]:
        """
        解析智能体输出，提取结构化信息

        Args:
            output: 智能体原始输出

        Returns:
            Dict: 解析后的结构化数据
        """
        parsed = {
            'content': output,
            'consensus': None,
            'disagreements': [],
            'open_questions': [],
            'actions': [],
            'key_points': []
        }

        # 提取共识部分
        consensus_match = re.search(r'[Cc]onsensus[:\s]*\n?(.*?)(?=\n\n|\n[A-Z]|\Z)', output, re.DOTALL)
        if consensus_match:
            parsed['consensus'] = consensus_match.group(1).strip()

        # 提取分歧部分
        disagreement_matches = re.findall(r'[Dd]isagreement[:\s]*\n?(.*?)(?=\n\n|\n[A-Z]|\Z)', output, re.DOTALL)
        parsed['disagreements'] = [d.strip() for d in disagreement_matches if d.strip()]

        # 提取开放问题
        question_matches = re.findall(r'[Oo]pen[ _][Qq]uestion[:\s]*\n?(.*?)(?=\n\n|\n[A-Z]|\Z)', output, re.DOTALL)
        parsed['open_questions'] = [q.strip() for q in question_matches if q.strip()]

        # 提取关键点
        key_point_matches = re.findall(r'[-•*]\s*(.*?)(?=\n|$)', output)
        parsed['key_points'] = [point.strip() for point in key_point_matches if point.strip()]

        return parsed

    def save_agent_output_with_structure(self,
                                        speaker: str,
                                        output: str,
                                        thread_id: Optional[str] = None,
                                        turn_id: Optional[int] = None,
                                        additional_tags: Optional[Dict[str, Any]] = None) -> str:
        """
        保存智能体输出并进行结构化分析

        Args:
            speaker: 说话者名称
            output: 智能体输出内容
            thread_id: 线程ID
            turn_id: 回合ID
            additional_tags: 额外的标签

        Returns:
            str: 事件ID
        """
        # 解析输出
        parsed_output = self.parse_output(output)

        # 创建标签
        tags = {
            'timestamp': datetime.now().isoformat(),
            'speaker_type': self._get_speaker_type(speaker),
            'has_consensus': bool(parsed_output['consensus']),
            'disagreement_count': len(parsed_output['disagreements']),
            'open_question_count': len(parsed_output['open_questions']),
            'key_point_count': len(parsed_output['key_points']),
            'content_length': len(output)
        }

        # 添加额外标签
        if additional_tags:
            tags.update(additional_tags)

        # 保存主要输出
        event_id = self.db_manager.save_agent_output(
            speaker=speaker,
            content=output,
            thread_id=thread_id,
            turn_id=turn_id,
            tags=tags
        )

        # 如果有thread_id，保存结构化数据
        if thread_id:
            # 保存共识
            if parsed_output['consensus']:
                self.db_manager.save_consensus(thread_id, parsed_output['consensus'])

            # 保存分歧
            for disagreement in parsed_output['disagreements']:
                self.db_manager.save_disagreement(thread_id, disagreement)

            # 保存开放问题
            for question in parsed_output['open_questions']:
                self.db_manager.save_open_question(thread_id, question)

        return event_id

    def _get_speaker_type(self, speaker: str) -> str:
        """根据说话者名称判断类型"""
        speaker_lower = speaker.lower()
        if 'theorist' in speaker_lower:
            return 'theorist'
        elif 'organizer' in speaker_lower or 'organiser' in speaker_lower:
            return 'organizer'
        elif 'skeptic' in speaker_lower:
            return 'skeptic'
        elif 'practitioner' in speaker_lower:
            return 'practitioner'
        else:
            return 'unknown'

    def get_thread_summary(self, thread_id: str) -> Dict[str, Any]:
        """
        获取线程的摘要信息

        Args:
            thread_id: 线程ID

        Returns:
            Dict: 线程摘要信息
        """
        # 获取事件
        events = self.db_manager.get_thread_events(thread_id)

        # 获取共识、分歧和开放问题
        with self.db_manager.get_cursor() as cursor:
            # 共识
            cursor.execute("SELECT content FROM consensus WHERE thread_id = %s", (thread_id,))
            consensus_list = [row['content'] for row in cursor.fetchall()]

            # 分歧
            cursor.execute("SELECT content FROM disagreements WHERE thread_id = %s", (thread_id,))
            disagreements_list = [row['content'] for row in cursor.fetchall()]

            # 开放问题
            cursor.execute("SELECT content FROM open_questions WHERE thread_id = %s", (thread_id,))
            questions_list = [row['content'] for row in cursor.fetchall()]

        # 统计发言者
        speakers = {}
        for event in events:
            speaker = event['speaker']
            speakers[speaker] = speakers.get(speaker, 0) + 1

        return {
            'thread_id': thread_id,
            'event_count': len(events),
            'speakers': speakers,
            'consensus_count': len(consensus_list),
            'disagreement_count': len(disagreements_list),
            'open_question_count': len(questions_list),
            'latest_event': events[-1] if events else None,
            'consensus_list': consensus_list,
            'disagreements_list': disagreements_list,
            'open_questions_list': questions_list
        }


class ConversationTracker:
    """对话跟踪器，用于管理多轮对话"""

    def __init__(self):
        self.db_manager = get_db_manager()
        self.current_thread_id = None

    def start_new_thread(self) -> str:
        """开始新的对话线程"""
        self.current_thread_id = self.db_manager.generate_thread_id()
        print(f"新的对话线程已开始: {self.current_thread_id}")
        return self.current_thread_id

    def continue_thread(self, thread_id: str):
        """继续指定的对话线程"""
        self.current_thread_id = thread_id
        print(f"继续对话线程: {thread_id}")

    def save_agent_message(self, speaker: str, content: str, tags: Optional[Dict[str, Any]] = None) -> str:
        """
        保存智能体消息到当前线程

        Args:
            speaker: 说话者名称
            content: 消息内容
            tags: 额外标签

        Returns:
            str: 事件ID
        """
        if not self.current_thread_id:
            self.start_new_thread()

        saver = AgentOutputSaver()
        return saver.save_agent_output_with_structure(
            speaker=speaker,
            output=content,
            thread_id=self.current_thread_id,
            additional_tags=tags
        )

    def get_conversation_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """获取当前对话线程的历史记录"""
        if not self.current_thread_id:
            return []

        return self.db_manager.get_thread_events(self.current_thread_id, limit)

    def get_conversation_summary(self) -> Dict[str, Any]:
        """获取当前对话线程的摘要"""
        if not self.current_thread_id:
            return {}

        saver = AgentOutputSaver()
        return saver.get_thread_summary(self.current_thread_id)


# 全局对话跟踪器实例
conversation_tracker = ConversationTracker()


def get_conversation_tracker() -> ConversationTracker:
    """获取对话跟踪器实例"""
    return conversation_tracker


# 装饰器版本，用于自动保存智能体输出
def track_conversation(speaker: str, tags: Optional[Dict[str, Any]] = None):
    """
    装饰器，自动跟踪和保存智能体的对话

    Args:
        speaker: 说话者名称
        tags: 额外标签
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # 执行原函数
            result = func(*args, **kwargs)

            # 如果结果是字符串，保存到对话中
            if isinstance(result, str):
                conversation_tracker.save_agent_message(speaker, result, tags)

            return result
        return wrapper
    return decorator

