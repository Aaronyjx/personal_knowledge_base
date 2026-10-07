# -*- coding: utf-8 -*-

"""
RAG V7 Runtime Rule Execution Regression Test

测试目标：

    evaluate_rule()

必须能够执行一个：
    非 Article 14 固定 8 条结构
    的 Runtime Rule。

本测试不修改：
    - Rule Registry
    - Canonical Rule
    - Decision Engine 生产逻辑

核心原则：

    Runtime Rule 定义条件数量
            ↓
    evaluate_rule() 动态执行
            ↓
    ConditionResult
            ↓
    通用 Decision Logic

本测试使用一个现有的 Article 14
Condition ID 作为 Fact Matcher 的测试入口，
但 Runtime Rule 本身只包含 1 条 REQUIRED 条件。

因此本测试验证的是：

    Decision Engine 的 Runtime Rule 执行结构

而不是：

    Fact Matcher 是否已经 Rule-Agnostic。
"""

from src.legal_decision_engine import (
    evaluate_rule,
)
from src.legal_rule_definition import (
    RULE_ID,
)
from src.legal_rule_registry import (
    get_rule,
)
from src.legal_fact_models import (
    ContractSequence,
    LegalFacts,
)


def build_test_rule():
    """
    构造一个只有 1 条 REQUIRED 条件的 V7 Runtime Rule。

    关键点：

        Runtime Rule
            REQUIRED × 1

        而不是 Article 14：
            REQUIRED × 4
            EXCLUSION × 3
            EXCEPTION × 1

    使用 ARTICLE-14-REQUIRED-001
    只是为了复用现有 Canonical Fact → Condition
    Relationship 作为测试入口。

    本测试不会复制 Relationship 定义。

    Relationship 来源：

        Canonical Rule Registry
                ↓
        ARTICLE-14-REQUIRED-001
                ↓
        Synthetic Runtime Rule

    因此本测试验证的是：

        V7 Runtime Rule
            ↓
        Relationship-driven evaluate_rule()

    而不是重新定义 Article 14 法律规则。
    """

    canonical_rule = get_rule(RULE_ID)

    condition_definitions = [
        dict(item)
        for item in canonical_rule[
            "condition_definitions"
        ]
        if item["condition_id"]
        == "ARTICLE-14-REQUIRED-001"
    ]

    relationships = [
        dict(item)
        for item in canonical_rule[
            "fact_condition_relationships"
        ]
        if any(
            predicate.get("fact_key")
            for group in item.get(
                "predicate_groups",
                [],
            )
            for predicate in group.get(
                "predicates",
                [],
            )
        )
        and item["relationship_id"].startswith(
            "ARTICLE-14-REL-REQUIRED-001-"
        )
    ]

    if len(condition_definitions) != 1:
        raise AssertionError(
            "Canonical Rule 缺少 ARTICLE-14-REQUIRED-001 "
            "Condition Definition。"
        )

    if not relationships:
        raise AssertionError(
            "Canonical Rule 缺少 "
            "ARTICLE-14-REQUIRED-001 Relationship。"
        )

    return {
        "rule_id": "TEST-RULE-V7-EXECUTION-001",
        "law_name": "V7 Runtime Rule Test Law",
        "article_number": "测试条款",
        "rule_name": "Runtime Rule Execution Test",
        "conditions": [
            condition_definitions[0]["condition"],
        ],
        "exclusion_conditions": [],
        "exceptions": [],
        "condition_definitions": [
            condition_definitions[0],
        ],
        "fact_condition_relationships": relationships,
    }


def build_satisfied_facts():
    """
    构造能够满足现有 ARTICLE-14-REQUIRED-001
    Fact Matcher 的 LegalFacts。

    这里直接使用结构化事实，
    不经过自然语言抽取。
    """

    return LegalFacts(
        contract_sequence=ContractSequence(
            count=2,
            term_type="fixed",
            continuous=True,
        )
    )


def build_unknown_facts():
    """
    构造无法证明该 REQUIRED 条件的 LegalFacts。
    """

    return LegalFacts()


def test_satisfied_runtime_rule():
    """
    Runtime Rule：

        REQUIRED × 1

    满足条件时：

        ConditionResult = SATISFIED
        Decision = DEFINITE
    """

    rule = build_test_rule()
    facts = build_satisfied_facts()

    decision, condition_results = evaluate_rule(
        facts=facts,
        rule=rule,
    )

    assert decision == "DEFINITE"

    assert len(condition_results) == 1

    result = condition_results[0]

    assert result.condition_id == (
        "ARTICLE-14-REQUIRED-001"
    )

    assert result.condition_type == "REQUIRED"

    assert result.status == "SATISFIED"


def test_unknown_runtime_rule():
    """
    Runtime Rule：

        REQUIRED × 1

    无法证明条件时：

        ConditionResult = UNKNOWN
        Decision = CONDITIONAL
    """

    rule = build_test_rule()
    facts = build_unknown_facts()

    decision, condition_results = evaluate_rule(
        facts=facts,
        rule=rule,
    )

    assert decision == "CONDITIONAL"

    assert len(condition_results) == 1

    result = condition_results[0]

    assert result.condition_id == (
        "ARTICLE-14-REQUIRED-001"
    )

    assert result.condition_type == "REQUIRED"

    assert result.status == "UNKNOWN"


def main():
    print("=" * 70)
    print("RAG V6.2 Runtime Rule Execution Regression Test")
    print("=" * 70)

    print()
    print("[1] Runtime Rule REQUIRED × 1")
    test_satisfied_runtime_rule()
    print(
        "PASS: 1 条 Runtime Rule 条件 → SATISFIED → DEFINITE"
    )

    print()
    print("[2] Runtime Rule REQUIRED × 1 + UNKNOWN")
    test_unknown_runtime_rule()
    print(
        "PASS: 1 条 Runtime Rule 条件 → UNKNOWN → CONDITIONAL"
    )

    print()
    print("=" * 70)
    print(
        "🎉 RAG V6.2 Runtime Rule Execution Test 全部通过"
    )
    print("=" * 70)


if __name__ == "__main__":
    main()
