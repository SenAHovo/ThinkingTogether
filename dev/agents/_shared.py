# agents/_shared.py
from __future__ import annotations

import random
import re
from typing import Iterable, Optional, Sequence


# -------------------------
# 反模板规则（全局统一）
# -------------------------
DEFAULT_BANNED_PHRASES: list[str] = [
    "以下是", "主要包括", "综上", "总之", "具体体现在", "主要体现在",
    "首先", "其次", "最后", "总体而言", "总体来说", "全面", "概述",
]

# 常见“报告/清单”形态：编号、项目符号、小标题
LISTY_RE = re.compile(
    r"(^|\n)\s*\d+\.\s+|(^|\n)\s*-\s+|(^|\n)\s*•\s+|(^|\n)\s*##+"
)

# 你可以按需扩充：更强的“作文腔”判定
ESSAYISH_RE = re.compile(r"(因此|所以|由此可见|综上所述|从而|总而言之)")


def clean_text(s: str) -> str:
    """轻量清洗：合并空白、去首尾空格。"""
    s = (s or "").replace("\r\n", "\n").strip()
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def excerpt(s: str, max_len: int = 180) -> str:
    s = clean_text(s).replace("\n", " ")
    return (s[:max_len] + "…") if len(s) > max_len else s


def pick_tic(style) -> str:
    """从 style.tics 随机选一个口头禅（如果没有就返回空）。"""
    try:
        tics = getattr(style, "tics", None) or []
        return random.choice(tics) if tics else ""
    except Exception:
        return ""


def taboos_text(style) -> str:
    """把 style.taboos 格式化成一行字符串。"""
    try:
        taboos = getattr(style, "taboos", None) or []
        return ", ".join(taboos) if taboos else "（无）"
    except Exception:
        return "（无）"


def is_listy(text: str) -> bool:
    """是否明显是清单/标题式输出。"""
    return bool(LISTY_RE.search(text or ""))


def has_banned_phrases(
    text: str,
    banned_phrases: Optional[Sequence[str]] = None,
) -> bool:
    banned = banned_phrases or DEFAULT_BANNED_PHRASES
    t = text or ""
    return any(p in t for p in banned)


def is_templated(
    text: str,
    banned_phrases: Optional[Sequence[str]] = None,
    extra_banned: Optional[Iterable[str]] = None,
    ban_bold_markdown: bool = True,
) -> bool:
    """
    判定是否“模板化/报告化”：
    - 列表/标题
    - 套话短语
    - （可选）Markdown 加粗
    """
    t = text or ""
    if is_listy(t):
        return True
    banned = list(banned_phrases or DEFAULT_BANNED_PHRASES)
    if extra_banned:
        banned.extend(list(extra_banned))
    if any(p in t for p in banned):
        return True
    if ban_bold_markdown and ("**" in t):
        return True
    return False


def build_rewrite_context(original: str) -> str:
    """
    生成“改写指令”（给同一个角色链或 rewriter 使用）。
    注意：这里不是固定模板，而是“反模板+口语化”要求。
    """
    original = clean_text(original)
    return (
        "请把下面这段内容改写成更像真实小组讨论的口语表达：\n"
        "- 只用1~2段自然段\n"
        "- 不要编号列表/项目符号/小标题/加粗(**)\n"
        "- 避免‘以下是/综上/主要包括/首先其次最后’等套话\n"
        "- 保留原有观点，但说得更像人聊天\n"
        "下面是需要改写的原文：\n"
        f"{original}"
    )
