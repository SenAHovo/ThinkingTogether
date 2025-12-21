# agents/rewriter_tool.py
from __future__ import annotations

from typing import Optional, Dict, Any

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda

from dev.agents._shared import clean_text, is_templated, build_rewrite_context
from dev.model_client import llm_theorist


_REWRITER_SYS = """
你是【反模板改写器】。
目标：把输入文本改写成更像真实小组讨论的口语表达，而不是报告/清单。
硬性规则：
- 只用1~2段自然段
- 禁止编号清单/项目符号/小标题/加粗(**)
- 避免套话：以下是/主要包括/综上/总之/首先其次最后
- 保留原观点与信息，不要凭空增加新点
"""

_prompt = ChatPromptTemplate.from_messages([
    ("system", _REWRITER_SYS),
    ("human", "{rewrite_card}"),
])

_chain = _prompt | llm_theorist | RunnableLambda(lambda m: m.content)


def rewrite_text(text: str) -> str:
    """无条件改写（强制口语化去模板）。"""
    rewrite_card = build_rewrite_context(text)
    out = _chain.invoke({"rewrite_card": rewrite_card})
    return clean_text(out)


def rewrite_if_needed(text: str) -> str:
    """检测到模板/清单/套话才改写。"""
    t = clean_text(text)
    if not is_templated(t):
        return t
    return rewrite_text(t)
