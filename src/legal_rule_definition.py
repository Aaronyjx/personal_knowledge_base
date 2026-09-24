# -*- coding: utf-8 -*-

"""
RAG V6.2
Canonical Legal Rule Definition

============================================================
职责
============================================================

本模块负责：

1. 定义法律规则的 Canonical Definition
2. 为不同模块提供统一的法律条件定义
3. 消除 Retriever 与 Decision Engine 之间的规则定义漂移
4. 保存 Article 14 的核心法律效果与引用信息

本模块不负责：

- LegalFacts
- Fact Extraction
- Fact Matching
- ConditionResult
- DecisionResult
- 条件判断
- Decision 计算
- Ollama
- 最终法律答案

核心原则：

    Canonical Rule Definition
              ↓
       ┌──────┴──────┐
       ↓             ↓
   Retriever   Decision Rules
                     ↓
             Legal Decision Engine
                     ↓
              ConditionResult
                     ↓
               DecisionResult

============================================================
重要设计原则
============================================================

本模块是法律规则定义的 Single Source of Truth。

特别是 Article 14 的：

- REQUIRED conditions
- EXCLUSION conditions
- EXCEPTION conditions

必须在本模块中只有一份定义。

V6.1 冻结的 Decision Engine 语义保持不变：

REQUIRED × 4
EXCLUSION × 3
EXCEPTION × 1

本模块只定义规则，不执行法律推理。
============================================================
"""

from __future__ import annotations

from typing import Any, Dict


# ============================================================
# 基础法律身份
# ============================================================

LABOR_CONTRACT_LAW = "中华人民共和国劳动合同法"

LABOR_CONTRACT_LAW_ARTICLE_14 = "第十四条"

IMPLEMENTING_REGULATIONS = (
    "中华人民共和国劳动合同法实施条例"
)


# ============================================================
# Article 14 REQUIRED Conditions
# ============================================================
#
# 注意：
#
# 这里采用 V6.1 Decision Engine 已冻结的四项 REQUIRED
# 条件。
#
# 不使用 Retriever 当前旧版的三项定义。
#
# 第 2 项：
#
#     存在后续订立的劳动合同
#
# 是当前 Decision Engine 判定边界的一部分。
# ============================================================

REQUIRED_CONDITIONS = [
    "连续订立二次固定期限劳动合同",
    "存在后续订立的劳动合同",
    "续订劳动合同",
    "劳动者提出或者同意续订、订立劳动合同",
]


# ============================================================
# Article 14 EXCLUSION Conditions
# ============================================================

EXCLUSION_CONDITIONS = [
    "劳动者存在《劳动合同法》第三十九条规定的情形",
    "劳动者存在《劳动合同法》第四十条第一项规定的情形",
    "劳动者存在《劳动合同法》第四十条第二项规定的情形",
]


# ============================================================
# Article 14 EXCEPTION Conditions
# ============================================================

EXCEPTION_CONDITIONS = [
    "劳动者提出订立固定期限劳动合同",
]


# ============================================================
# All Article 14 Conditions
# ============================================================

ALL_CONDITIONS = (
    REQUIRED_CONDITIONS
    + EXCLUSION_CONDITIONS
    + EXCEPTION_CONDITIONS
)


# ============================================================
# Article 14 Legal Obligations
# ============================================================

LEGAL_OBLIGATIONS = [
    "用人单位应当订立无固定期限劳动合同",
]


# ============================================================
# Article 14 Legal Consequences
# ============================================================

LEGAL_CONSEQUENCES = [
    "符合第十四条规定条件时，用人单位应当订立无固定期限劳动合同",
]


# ============================================================
# Article 14 References
# ============================================================

ARTICLE_14_REFERENCES = [
    "第十四条",
    "第三十九条",
    "第四十条",
    "第四十条第一项",
    "第四十条第二项",
]


# ============================================================
# Canonical Rule Builder
# ============================================================

def build_article_14_definition() -> Dict[str, Any]:
    """
    构建《劳动合同法》第十四条 Canonical Rule Definition。

    本函数只负责返回法律规则定义。

    不读取用户事实。
    不判断条件。
    不生成 ConditionResult。
    不计算 DecisionResult。
    """

    return {
        "law_name": LABOR_CONTRACT_LAW,
        "article_number": LABOR_CONTRACT_LAW_ARTICLE_14,

        "rule_name": (
            "连续订立固定期限劳动合同后"
            "订立无固定期限劳动合同"
        ),

        "conditions": list(REQUIRED_CONDITIONS),

        "exclusion_conditions": list(
            EXCLUSION_CONDITIONS
        ),

        "exceptions": list(
            EXCEPTION_CONDITIONS
        ),

        "legal_obligations": list(
            LEGAL_OBLIGATIONS
        ),

        "legal_consequences": list(
            LEGAL_CONSEQUENCES
        ),

        "references": list(
            ARTICLE_14_REFERENCES
        ),
    }


# ============================================================
# Definition Validation
# ============================================================

def validate_article_14_definition() -> Dict[str, Any]:
    """
    验证 Canonical Article 14 Rule Definition 的基本结构。

    本函数只验证规则定义本身，不执行法律判断。
    """

    definition = build_article_14_definition()

    required = definition["conditions"]
    exclusions = definition["exclusion_conditions"]
    exceptions = definition["exceptions"]

    all_conditions = (
        required
        + exclusions
        + exceptions
    )

    return {
        "valid": (
            len(required) == 4
            and len(exclusions) == 3
            and len(exceptions) == 1
            and len(all_conditions) == 8
            and len(set(all_conditions)) == 8
            and bool(definition["law_name"])
            and bool(definition["article_number"])
            and bool(definition["legal_obligations"])
            and bool(definition["legal_consequences"])
            and bool(definition["references"])
        ),
        "required_count": len(required),
        "exclusion_count": len(exclusions),
        "exception_count": len(exceptions),
        "condition_count": len(all_conditions),
        "unique_condition_count": len(
            set(all_conditions)
        ),
    }


# ============================================================
# Module Self Test
# ============================================================

def main() -> None:
    """
    Canonical Rule Definition 自检。
    """

    print("=" * 70)
    print("RAG V6.2 Canonical Rule Definition Test")
    print("=" * 70)

    definition = build_article_14_definition()

    validation = validate_article_14_definition()

    print()
    print("Law:", definition["law_name"])
    print("Article:", definition["article_number"])
    print()
    print("REQUIRED:", len(definition["conditions"]))
    print("EXCLUSION:", len(
        definition["exclusion_conditions"]
    ))
    print("EXCEPTION:", len(
        definition["exceptions"]
    ))
    print()

    for index, condition in enumerate(
        definition["conditions"],
        start=1,
    ):
        print(
            f"REQUIRED {index}: {condition}"
        )

    print()

    for index, condition in enumerate(
        definition["exclusion_conditions"],
        start=1,
    ):
        print(
            f"EXCLUSION {index}: {condition}"
        )

    print()

    for index, condition in enumerate(
        definition["exceptions"],
        start=1,
    ):
        print(
            f"EXCEPTION {index}: {condition}"
        )

    print()
    print("Validation:", validation)

    if validation["valid"]:
        print()
        print("PASS: Canonical Article 14 Rule Definition")
    else:
        print()
        print("FAIL: Canonical Article 14 Rule Definition")


if __name__ == "__main__":
    main()
