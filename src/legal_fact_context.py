# -*- coding: utf-8 -*-

"""
RAG V6.8
Legal Fact Context Boundary

============================================================
功能
============================================================

本模块负责判断：

    一个已经命中的事实模式
    是否处于用户明确事实陈述语境。

只服务于：

    Legal Fact Extraction Layer

不负责：

    - 法律条件判断
    - ConditionResult
    - DecisionResult
    - Decision
    - Retriever
    - Ollama
    - 最终答案

============================================================
核心原则
============================================================

Fact Extraction 只能从用户明确陈述中产生 LegalFacts。

以下语境不能产生事实：

    1. QUESTION
       例如：
           劳动者是否存在第三十九条规定的情形？

    2. HYPOTHETICAL
       例如：
           如果劳动者存在第三十九条规定的情形，会怎样？

但一个问题可以同时包含：

    明确事实 + 法律问题

例如：

    公司连续签订三次固定期限劳动合同后，
    是否必须签订无固定期限劳动合同？

其中：

    “公司连续签订三次固定期限劳动合同”

仍然是明确事实。

因此不能简单地因为整个 question 包含：

    “是否”

就拒绝所有事实。

============================================================
"""

from __future__ import annotations

from typing import List


# ============================================================
# 非事实语境标记
# ============================================================

QUESTION_MARKERS: List[str] = [
    "是否",
    "能否",
    "可否",
    "有没有",
    "是否有",
    "是否存在",
    "是否属于",
    "是否符合",
    "是否构成",
    "是不是",
    "有无",
]


HYPOTHETICAL_MARKERS: List[str] = [
    "如果",
    "假如",
    "假设",
    "若",
    "倘若",
    "如若",
    "一旦",
]


# ============================================================
# 分句边界
# ============================================================

CLAUSE_BOUNDARIES = set(
    "，,。！？!?；;：:\n"
)


def _clause_prefix(
    text: str,
    match_start: int,
) -> str:
    """
    获取事实模式所在分句中，
    位于事实模式之前的文本。

    例如：

        劳动者是否存在第三十九条规定的情形

    pattern：

        存在第三十九条规定的情形

    返回：

        劳动者是否

    而：

        公司连续签订三次固定期限劳动合同后，是否必须……

    pattern：

        连续签订三次固定期限劳动合同

    位于第一个分句中，因此不会被后面的“是否”污染。
    """

    prefix = text[:match_start]

    boundary = -1

    for index, char in enumerate(prefix):
        if char in CLAUSE_BOUNDARIES:
            boundary = index

    return prefix[boundary + 1:]


def _has_question_context(
    clause_prefix: str,
) -> bool:
    """
    判断事实模式之前的同一分句是否已经进入疑问语境。
    """

    return any(
        marker in clause_prefix
        for marker in QUESTION_MARKERS
    )


def _has_hypothetical_context(
    clause_prefix: str,
) -> bool:
    """
    判断事实模式之前的同一分句是否已经进入假设语境。
    """

    return any(
        marker in clause_prefix
        for marker in HYPOTHETICAL_MARKERS
    )


def is_asserted_match(
    text: str,
    match_start: int,
) -> bool:
    """
    判断一个已经命中的事实模式是否属于明确事实陈述。

    返回：

        True
            明确事实陈述。

        False
            疑问或假设语境。

    注意：

        本函数不负责寻找 pattern。
        pattern 的匹配仍由事实提取模块负责。

    这样可以保持：

        “事实模式识别”
        与
        “事实语境判断”

    两个职责独立。
    """

    clause_prefix = _clause_prefix(
        text,
        match_start,
    )

    if _has_question_context(
        clause_prefix,
    ):
        return False

    if _has_hypothetical_context(
        clause_prefix,
    ):
        return False

    return True


def contains_asserted_any(
    text: str,
    patterns: List[str],
) -> bool:
    """
    判断文本中是否存在一个处于明确事实陈述语境中的 pattern。

    与 contains_any() 的区别：

        contains_any()
            只判断字符串是否包含。

        contains_asserted_any()
            还判断命中的 pattern 是否处于：
                - QUESTION
                - HYPOTHETICAL

            语境。

    本函数只用于 Legal Fact Extraction。

    不修改 legal_common.contains_any() 的通用语义。
    """

    if not text:
        return False

    for pattern in patterns:
        if not pattern:
            continue

        start = text.find(pattern)

        while start >= 0:
            if is_asserted_match(
                text,
                start,
            ):
                return True

            next_start = start + len(pattern)

            start = text.find(
                pattern,
                next_start,
            )

    return False
