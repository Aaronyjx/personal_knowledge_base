# -*- coding: utf-8 -*-

"""
RAG V6.1
Legal Decision Rules

============================================================
职责
============================================================

本模块只负责：

1. Article 14 固定条件定义
2. Article 39 / Article 40 排除条件定义
3. Exception 条件定义
4. Article 39 / 40 组合否定模式
5. Article 14 核心规则结构构建

本模块不负责：

- LegalFacts
- ConditionResult
- DecisionResult
- 条件判断
- Decision 计算
- Ollama
- 最终法律答案

核心原则：

    Rule Definition
        ↓
    Legal Decision Engine
        ↓
    ConditionResult
        ↓
    DecisionResult
============================================================
"""

from __future__ import annotations

from typing import Any, Dict


LABOR_CONTRACT_LAW = "中华人民共和国劳动合同法"

LABOR_CONTRACT_LAW_ARTICLE_14 = "第十四条"


IMPLEMENTING_REGULATIONS = (
    "中华人民共和国劳动合同法实施条例"
)


REQUIRED_CONDITIONS = [
    "连续订立二次固定期限劳动合同",
    "存在后续订立的劳动合同",
    "续订劳动合同",
    "劳动者提出或者同意续订、订立劳动合同",
]


EXCLUSION_CONDITIONS = [
    "劳动者存在《劳动合同法》第三十九条规定的情形",
    "劳动者存在《劳动合同法》第四十条第一项规定的情形",
    "劳动者存在《劳动合同法》第四十条第二项规定的情形",
]


EXCEPTION_CONDITIONS = [
    "劳动者提出订立固定期限劳动合同",
]


ALL_CONDITIONS = (
    REQUIRED_CONDITIONS
    + EXCLUSION_CONDITIONS
    + EXCEPTION_CONDITIONS
)


COMBINED_ARTICLE_39_40_NEGATIVE_PATTERNS = [
    "不存在劳动合同法第三十九条和第四十条第一项、第二项规定的情形",
    "不存在《劳动合同法》第三十九条和第四十条第一项、第二项规定的情形",
    "不存在劳动合同法第三十九条和第四十条第一项及第二项规定的情形",
    "不存在《劳动合同法》第三十九条和第四十条第一项及第二项规定的情形",
    "不存在劳动合同法第三十九条、第四十条第一项、第二项规定的情形",
    "不存在《劳动合同法》第三十九条、第四十条第一项、第二项规定的情形",
    "没有劳动合同法第三十九条和第四十条第一项、第二项规定的情形",
    "没有《劳动合同法》第三十九条和第四十条第一项、第二项规定的情形",
    "没有劳动合同法第三十九条和第四十条第一项及第二项规定的情形",
    "没有《劳动合同法》第三十九条和第四十条第一项及第二项规定的情形",
    "不具有劳动合同法第三十九条和第四十条第一项、第二项规定的情形",
    "不具有《劳动合同法》第三十九条和第四十条第一项、第二项规定的情形",
    "不具有劳动合同法第三十九条和第四十条第一项及第二项规定的情形",
    "不具有《劳动合同法》第三十九条和第四十条第一项及第二项规定的情形",
]


def build_core_rule() -> Dict[str, Any]:
    """
    构建《劳动合同法》第十四条核心规则。
    """

    return {
        "law_name": LABOR_CONTRACT_LAW,

        "article": LABOR_CONTRACT_LAW_ARTICLE_14,

        "rule_name": (
            "连续订立固定期限劳动合同后"
            "订立无固定期限劳动合同"
        ),

        "rule_text": (
            "连续订立二次固定期限劳动合同，"
            "且不存在法律规定的排除或者例外情形，"
            "在符合法定续订及劳动者意思表示等条件时，"
            "依法判断是否应当订立无固定期限劳动合同。"
        ),

        "conditions": list(
            REQUIRED_CONDITIONS
        ),

        "exclusion_conditions": list(
            EXCLUSION_CONDITIONS
        ),

        "exceptions": list(
            EXCEPTION_CONDITIONS
        ),

        "priority": "ARTICLE_14",
    }
