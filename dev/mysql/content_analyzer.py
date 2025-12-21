"""
智能内容分析器
用于从智能体输出中准确提取结构化信息
"""

import re
import json
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ExtractedContent:
    """提取的结构化内容"""
    consensus: List[str]
    disagreements: List[str]
    open_questions: List[str]
    key_points: List[str]
    action_items: List[str]
    emotions: Dict[str, float]
    topics: List[str]
    keywords: List[Tuple[str, float]]


class ContentAnalyzer:
    """智能内容分析器"""

    def __init__(self):
        # 共识关键词模式
        self.consensus_patterns = [
            r'(?:共识|一致|同意|大家都觉得|普遍认为)[：:]\s*(.+?)(?=\n\n|\n[A-Z\u4e00-\u9fa5]|\Z)',
            r'(?:(?:我们|大家)都)?(?:同意|认为|觉得|确认)[：:]\s*(.+?)(?=\n\n|\n[A-Z\u4e00-\u9fa5]|\Z)',
            r'(?:(?:达成|形成|取得))共?识[：:]\s*(.+?)(?=\n\n|\n[A-Z\u4e00-\u9fa5]|\Z)',
        ]

        # 分歧关键词模式
        self.disagreement_patterns = [
            r'(?:分歧|不同意见|争议|异议|争论|矛盾)[：:]\s*(.+?)(?=\n\n|\n[A-Z\u4e00-\u9fa5]|\Z)',
            r'(?:有(?:人|人觉得|人认为|人担心))[\s,，]*(.+?)(?=\n\n|\n[A-Z\u4e00-\u9fa5]|\Z)',
            r'(?:反对|质疑|不同意|怀疑|担心)[：:]\s*(.+?)(?=\n\n|\n[A-Z\u4e00-\u9fa5]|\Z)',
            r'(?:然而|但是|可是|不过|另一方面)[，,]\s*(.+?)(?=\n\n|\n[A-Z\u4e00-\u9fa5]|\Z)',
        ]

        # 开放问题模式
        self.question_patterns = [
            r'(?:开放问题|待解问题|需要考虑|值得思考)[：:]\s*(.+?)(?=\n\n|\n[A-Z\u4e00-\u9fa5]|\Z)',
            r'[？?](?!\s*(?:[。！!]|$))\s*(.+?)(?=\n\n|\n[A-Z\u4e00-\u9fa5]|\Z)',
            r'(?:如何|怎么|什么|为什么|哪些|是否|能否)[：:]?\s*(.+?)[？?]',
            r'需要(?:解决|回答|考虑)[：:]\s*(.+?)(?=\n\n|\n[A-Z\u4e00-\u9fa5]|\Z)',
        ]

        # 关键点模式
        self.key_point_patterns = [
            r'[-•*]\s*(.+?)(?=\n|$)',
            r'(\d+[.)]\s*|（\d+）)\s*(.+?)(?=\n|$)',
            r'(?:关键点|要点|重点|核心)[：:]\s*(.+?)(?=\n|$)',
            r'(?:总结|概括)[：:]\s*(.+?)(?=\n|$)',
        ]

        # 行动项模式
        self.action_patterns = [
            r'(?:建议|推荐|提议|行动)[：:]\s*(.+?)(?=\n\n|\n[A-Z\u4e00-\u9fa5]|\Z)',
            r'(?:下一步|接下来|需要做|应该)[：:]\s*(.+?)(?=\n\n|\n[A-Z\u4e00-\u9fa5]|\Z)',
            r'(?:具体|落地|执行)[：:]\s*(.+?)(?=\n\n|\n[A-Z\u4e00-\u9fa5]|\Z)',
        ]

        # 情感词汇
        self.emotion_words = {
            '积极': {'好', '棒', '优秀', '赞同', '同意', '支持', '乐观', '期待', '希望', '兴奋', '满意'},
            '消极': {'差', '糟糕', '反对', '质疑', '担心', '悲观', '焦虑', '失望', '沮丧', '愤怒', '不满'},
            '中性': {'考虑', '分析', '评估', '观察', '思考', '讨论', '研究', '观察'}
        }

        # 停用词
        self.stop_words = {
            '的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好', '自己', '这',
            '也', '而', '或', '及', '与其', '若是', '只要', '与其', '宁可', '尽管', '即使', '无论', '不管', '无论如何', '虽然', '虽说', '固然', '虽然', '不过', '可是', '然而', '只是', '不料', '没想',
        }

    def extract_content(self, content: str) -> ExtractedContent:
        """
        从内容中提取结构化信息

        Args:
            content: 待分析的文本内容

        Returns:
            ExtractedContent: 提取的结构化内容
        """
        content = content.strip()

        consensus = self._extract_patterns(content, self.consensus_patterns)
        disagreements = self._extract_patterns(content, self.disagreement_patterns)
        open_questions = self._extract_patterns(content, self.question_patterns)
        key_points = self._extract_patterns(content, self.key_point_patterns)
        action_items = self._extract_patterns(content, self.action_patterns)
        emotions = self._extract_emotions(content)
        topics = self._extract_topics(content)
        keywords = self._extract_keywords(content)

        # 智能分析：如果没有明确的结构化信息，尝试从内容中推断
        if not consensus and not disagreements and not open_questions:
            inferred = self._infer_structure_from_content(content)
            if inferred['consensus']:
                consensus.extend(inferred['consensus'])
            if inferred['disagreements']:
                disagreements.extend(inferred['disagreements'])
            if inferred['questions']:
                open_questions.extend(inferred['questions'])

        return ExtractedContent(
            consensus=consensus,
            disagreements=disagreements,
            open_questions=open_questions,
            key_points=key_points,
            action_items=action_items,
            emotions=emotions,
            topics=topics,
            keywords=keywords
        )

    def _infer_structure_from_content(self, content: str) -> Dict[str, List[str]]:
        """
        从内容中推断隐含的结构化信息

        Args:
            content: 文本内容

        Returns:
            Dict: 推断出的结构化信息
        """
        result = {
            'consensus': [],
            'disagreements': [],
            'questions': []
        }

        # 分句分析
        sentences = re.split(r'[。！？]', content)

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            # 推断共识：表达共同观点或普遍认同的内容
            if any(phrase in sentence for phrase in [
                '我们都', '大家都', '共同', '一致', '通常', '一般来说',
                '实际上是', '事实上', '很清楚', '很明显'
            ]):
                if len(sentence) > 10:  # 过滤太短的句子
                    result['consensus'].append(sentence)

            # 推断分歧：表达对比或不同观点的内容
            elif any(phrase in sentence for phrase in [
                '不同于', '对比之下', '相对而言', '然而', '但是', '不过',
                '另一方面', '区别在于', '差异是', '相反'
            ]):
                if len(sentence) > 10:
                    result['disagreements'].append(sentence)

            # 推断问题：包含疑问词或询问性质的内容
            elif any(phrase in sentence for phrase in [
                '如何', '怎么', '什么', '为什么', '哪些', '是否',
                '能否', '值得思考', '需要明确', '问题是'
            ]):
                if len(sentence) > 10:
                    result['questions'].append(sentence)

        return result

    def _extract_patterns(self, content: str, patterns: List[str]) -> List[str]:
        """根据正则表达式模式提取内容"""
        results = []
        for pattern in patterns:
            matches = re.findall(pattern, content, re.DOTALL | re.IGNORECASE | re.MULTILINE)
            for match in matches:
                cleaned = self._clean_text(match)
                if cleaned and len(cleaned) > 5:  # 过滤太短的内容
                    if cleaned not in results:  # 去重
                        results.append(cleaned)
        return results

    def _extract_emotions(self, content: str) -> Dict[str, float]:
        """提取情感倾向"""
        emotion_counts = {emotion: 0 for emotion in self.emotion_words.keys()}
        total_words = 0

        # 按字符分割，简单统计
        for emotion_type, words in self.emotion_words.items():
            for word in words:
                count = content.count(word)
                emotion_counts[emotion_type] += count

        total = sum(emotion_counts.values())
        if total == 0:
            return {'中性': 1.0}

        # 归一化
        emotions = {}
        for emotion, count in emotion_counts.items():
            if count > 0:
                emotions[emotion] = count / total

        return emotions

    def _extract_topics(self, content: str) -> List[str]:
        """提取话题关键词"""
        # 简单的话题提取：找出经常出现的名词性短语
        # 这里使用简化的方法，实际项目中可以使用更复杂的NLP算法

        # 查找可能是话题的短语
        topic_patterns = [
            r'关于([^，。！？\n]+)',
            r'对([^，。！？\n]+)的',
            r'([^，。！？\n]{2,8})问题',
            r'([^，。！？\n]{2,8})方案',
            r'([^，。！？\n]{2,8})方法',
            r'([^，。！？\n]{2,8})策略',
        ]

        topics = []
        for pattern in topic_patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                if len(match) >= 2 and len(match) <= 8:
                    topics.append(match.strip())

        # 去重并返回
        return list(set(topics))

    def _extract_keywords(self, content: str) -> List[Tuple[str, float]]:
        """提取关键词和权重"""
        import jieba
        import jieba.analyse

        # 如果没有jieba，使用简单的方法
        try:
            # 使用jieba进行关键词提取
            keywords = jieba.analyse.extract_tags(content, topK=10, withWeight=True)
            return [(word, float(weight)) for word, weight in keywords]
        except:
            # 简单的关键词提取：分词并统计词频
            words = re.findall(r'[\u4e00-\u9fa5]+', content)  # 提取中文词汇
            word_count = {}

            for word in words:
                if len(word) >= 2 and word not in self.stop_words:
                    word_count[word] = word_count.get(word, 0) + 1

            # 按频率排序
            sorted_words = sorted(word_count.items(), key=lambda x: x[1], reverse=True)
            total_count = sum(word_count.values())

            # 归一化权重
            keywords = []
            for word, count in sorted_words[:10]:  # 取前10个
                weight = count / total_count if total_count > 0 else 0
                keywords.append((word, weight))

            return keywords

    def _clean_text(self, text: str) -> str:
        """清理文本"""
        if not text:
            return ""

        # 移除多余的空白字符
        text = re.sub(r'\s+', ' ', text.strip())

        # 移除常见的格式化符号
        text = re.sub(r'[^\w\s\u4e00-\u9fa5。！？；，：""''（）【】]', '', text)

        # 移除列表标记
        text = re.sub(r'^\s*[-•*]\s*', '', text)
        text = re.sub(r'^\s*\d+[.)]\s*', '', text)

        return text.strip()

    def analyze_speaker_type(self, content: str, speaker: str) -> str:
        """分析说话者类型"""
        if "理论家" in speaker:
            return "theorist"
        elif "实践者" in speaker:
            return "practitioner"
        elif "质疑者" in speaker:
            return "skeptic"
        elif "组织者" in speaker:
            return "organizer"
        elif "用户" in speaker:
            return "user"
        else:
            # 根据内容特征推断
            extracted = self.extract_content(content)
            if extracted.consensus and not extracted.disagreements:
                return "organizer"  # 倾向于总结的可能是组织者
            elif extracted.disagreements and not extracted.consensus:
                return "skeptic"  # 倾向于质疑的可能是质疑者
            elif extracted.action_items:
                return "practitioner"  # 倾向于行动的可能是实践者
            else:
                return "theorist"  # 默认为理论家

    def get_content_metadata(self, content: str, speaker: str) -> Dict[str, Any]:
        """获取内容的元数据"""
        extracted = self.extract_content(content)
        speaker_type = self.analyze_speaker_type(content, speaker)

        return {
            'speaker_type': speaker_type,
            'content_length': len(content),
            'has_consensus': len(extracted.consensus) > 0,
            'has_disagreement': len(extracted.disagreements) > 0,
            'has_questions': len(extracted.open_questions) > 0,
            'has_key_points': len(extracted.key_points) > 0,
            'has_action_items': len(extracted.action_items) > 0,
            'consensus_count': len(extracted.consensus),
            'disagreement_count': len(extracted.disagreements),
            'question_count': len(extracted.open_questions),
            'key_point_count': len(extracted.key_points),
            'action_count': len(extracted.action_items),
            'primary_emotion': max(extracted.emotions.items(), key=lambda x: x[1])[0] if extracted.emotions else 'neutral',
            'topic_count': len(extracted.topics),
            'keyword_count': len(extracted.keywords),
            'complexity_score': self._calculate_complexity(content),
            'timestamp': datetime.now().isoformat()
        }

    def _calculate_complexity(self, content: str) -> float:
        """计算内容复杂度"""
        # 简单的复杂度计算
        factors = {
            'length_factor': min(len(content) / 1000, 1.0),  # 长度因子
            'sentence_count': len(re.findall(r'[。！？]', content)),  # 句子数量
            'question_ratio': content.count('？') + content.count('?'),  # 问题比例
            'structure_words': content.count('因为') + content.count('所以') + content.count('但是'),  # 逻辑词汇
        }

        # 归一化计算
        complexity = (
            factors['length_factor'] * 0.3 +
            min(factors['sentence_count'] / 10, 1.0) * 0.2 +
            min(factors['question_ratio'] / 5, 1.0) * 0.3 +
            min(factors['structure_words'] / 5, 1.0) * 0.2
        )

        return round(complexity, 3)


# 全局分析器实例
content_analyzer = ContentAnalyzer()


def get_content_analyzer() -> ContentAnalyzer:
    """获取内容分析器实例"""
    return content_analyzer