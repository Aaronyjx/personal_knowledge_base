#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
RAG V6.10 LegalFacts → ConditionResult Boundary Regression Test

测试目标：
    LegalFacts → match_condition() → ConditionResult

核心原则：
    1. match_condition() 只能读取 LegalFacts。
    2. 不允许从自然语言问题、检索文章、规则解释等上下文重新推导事实。
    3. None 必须保持 UNKNOWN。
    4. 一个 LegalFacts 字段只能影响其对应的条件。
    5. 三次固定期限劳动合同不能自动推出：
         - 已完成续订
         - 劳动者同意续订/订立
         - 第39条排除情形
         - 第40条第1项排除情形
         - 第40条第2项排除情形
         - 固定期限合同例外

运行：
    PYTHONPATH="$PWD" python tests/test_legal_facts_condition_boundary.py
"""

from dataclasses import replace

from src.legal_decision_engine import (
    LegalFacts,
    match_condition,
)
from src.legal_rule_registry import get_rule
from src.legal_rule_definition import RULE_ID


# ============================================================
# Canonical Condition Registry
# ============================================================

RULE = get_rule(RULE_ID)

CONDITION_DEFINITIONS = RULE["condition_definitions"]

CONDITIONS = {
    item["condition_id"]: item
    for item in CONDITION_DEFINITIONS
}

REQUIRED_001 = "ARTICLE-14-REQUIRED-001"
REQUIRED_002 = "ARTICLE-14-REQUIRED-002"
REQUIRED_003 = "ARTICLE-14-REQUIRED-003"
REQUIRED_004 = "ARTICLE-14-REQUIRED-004"

EXCLUSION_001 = "ARTICLE-14-EXCLUSION-001"
EXCLUSION_002 = "ARTICLE-14-EXCLUSION-002"
EXCLUSION_003 = "ARTICLE-14-EXCLUSION-003"

EXCEPTION_001 = "ARTICLE-14-EXCEPTION-001"

ALL_CONDITION_IDS = [
    REQUIRED_001,
    REQUIRED_002,
    REQUIRED_003,
    REQUIRED_004,
    EXCLUSION_001,
    EXCLUSION_002,
    EXCLUSION_003,
    EXCEPTION_001,
]


# ============================================================
# Status Constants
# ============================================================

SATISFIED = "SATISFIED"
NOT_SATISFIED = "NOT_SATISFIED"
UNKNOWN = "UNKNOWN"


# ============================================================
# Helpers
# ============================================================

def make_contract_sequence(count=3):
    """
    创建三次连续固定期限劳动合同事实。

    注意：
        这里只表示合同数量、期限类型和连续性。
        不表示：
            - 已经完成续订；
            - 劳动者已经同意；
            - 第39条/第40条情形不存在；
            - 固定期限合同例外存在或不存在。
    """
    # 延迟导入，兼容当前项目中 ContractSequence 的实际定义位置。
    from src.legal_decision_engine import ContractSequence

    return ContractSequence(
        count=count,
        term_type="fixed",
        continuous=True,
    )


def evaluate(condition_id, facts):
    """
    使用 canonical condition definition 调用 match_condition()。
    """
    definition = CONDITIONS[condition_id]

    result = match_condition(
        facts=facts,
        condition_id=condition_id,
        condition=definition["condition"],
        condition_type=definition["condition_type"],
    )

    return result


def assert_status(condition_id, facts, expected):
    result = evaluate(condition_id, facts)

    assert result.condition_id == condition_id, (
        f"{condition_id}: condition_id 不一致："
        f"{result.condition_id!r}"
    )

    assert result.status == expected, (
        f"{condition_id}: "
        f"expected={expected!r}, actual={result.status!r}; "
        f"reason={result.reason!r}"
    )

    return result


def assert_all_statuses(facts, expected):
    """
    expected:
        {
            condition_id: status,
            ...
        }
    """
    for condition_id in ALL_CONDITION_IDS:
        assert condition_id in expected, (
            f"测试期望缺少条件：{condition_id}"
        )

        assert_status(
            condition_id,
            facts,
            expected[condition_id],
        )


def statuses(facts):
    return {
        condition_id: evaluate(
            condition_id,
            facts,
        ).status
        for condition_id in ALL_CONDITION_IDS
    }


# ============================================================
# CASE 01
# 三次固定期限合同不能自动推出其他事实
# ============================================================

def test_three_fixed_term_contracts_boundary():
    print("=" * 70)
    print("CASE 01  三次固定期限合同：不得自动推出其他事实")
    print("=" * 70)

    facts = LegalFacts(
        explicit_facts=[
            "公司连续签订三次固定期限劳动合同。"
        ],
        contract_sequence=make_contract_sequence(3),
        completed_renewal=None,
        worker_agreement=None,
        article_39=None,
        article_40_1=None,
        article_40_2=None,
        fixed_term_exception=None,
    )

    expected = {
        REQUIRED_001: SATISFIED,
        REQUIRED_002: SATISFIED,
        REQUIRED_003: UNKNOWN,
        REQUIRED_004: UNKNOWN,
        EXCLUSION_001: UNKNOWN,
        EXCLUSION_002: UNKNOWN,
        EXCLUSION_003: UNKNOWN,
        EXCEPTION_001: UNKNOWN,
    }

    assert_all_statuses(facts, expected)

    print("PASS")
    print("  REQUIRED-001  → SATISFIED")
    print("  REQUIRED-002  → SATISFIED")
    print("  REQUIRED-003  → UNKNOWN")
    print("  REQUIRED-004  → UNKNOWN")
    print("  EXCLUSION-001 → UNKNOWN")
    print("  EXCLUSION-002 → UNKNOWN")
    print("  EXCLUSION-003 → UNKNOWN")
    print("  EXCEPTION-001 → UNKNOWN")
    print()


# ============================================================
# CASE 02
# completed_renewal 只能影响 REQUIRED-003
# ============================================================

def test_completed_renewal_isolated():
    print("=" * 70)
    print("CASE 02  completed_renewal 字段隔离")
    print("=" * 70)

    base_facts = LegalFacts(
        explicit_facts=[],
        contract_sequence=make_contract_sequence(3),
        completed_renewal=None,
        worker_agreement=None,
        article_39=None,
        article_40_1=None,
        article_40_2=None,
        fixed_term_exception=None,
    )

    renewed_facts = replace(
        base_facts,
        completed_renewal=True,
    )

    before = statuses(base_facts)
    after = statuses(renewed_facts)

    assert before[REQUIRED_003] == UNKNOWN
    assert after[REQUIRED_003] == SATISFIED

    for condition_id in ALL_CONDITION_IDS:
        if condition_id == REQUIRED_003:
            continue

        assert before[condition_id] == after[condition_id], (
            f"completed_renewal 不应影响 {condition_id}: "
            f"before={before[condition_id]!r}, "
            f"after={after[condition_id]!r}"
        )

    print("PASS")
    print("  completed_renewal=None → REQUIRED-003 UNKNOWN")
    print("  completed_renewal=True → REQUIRED-003 SATISFIED")
    print("  其他 7 个条件状态保持不变")
    print()


# ============================================================
# CASE 03
# worker_agreement 只能影响 REQUIRED-004
# ============================================================

def test_worker_agreement_isolated():
    print("=" * 70)
    print("CASE 03  worker_agreement 字段隔离")
    print("=" * 70)

    base_facts = LegalFacts(
        explicit_facts=[],
        contract_sequence=make_contract_sequence(3),
        completed_renewal=None,
        worker_agreement=None,
        article_39=None,
        article_40_1=None,
        article_40_2=None,
        fixed_term_exception=None,
    )

    agreed_facts = replace(
        base_facts,
        worker_agreement=True,
    )

    before = statuses(base_facts)
    after = statuses(agreed_facts)

    assert before[REQUIRED_004] == UNKNOWN
    assert after[REQUIRED_004] == SATISFIED

    for condition_id in ALL_CONDITION_IDS:
        if condition_id == REQUIRED_004:
            continue

        assert before[condition_id] == after[condition_id], (
            f"worker_agreement 不应影响 {condition_id}: "
            f"before={before[condition_id]!r}, "
            f"after={after[condition_id]!r}"
        )

    print("PASS")
    print("  worker_agreement=None → REQUIRED-004 UNKNOWN")
    print("  worker_agreement=True → REQUIRED-004 SATISFIED")
    print("  其他 7 个条件状态保持不变")
    print()


# ============================================================
# CASE 04
# Article 39 只能影响 EXCLUSION-001
# ============================================================

def test_article_39_isolated():
    print("=" * 70)
    print("CASE 04  article_39 字段隔离")
    print("=" * 70)

    base_facts = LegalFacts(
        contract_sequence=make_contract_sequence(3),
        article_39=None,
    )

    excluded_facts = replace(
        base_facts,
        article_39=True,
    )

    before = statuses(base_facts)
    after = statuses(excluded_facts)

    assert before[EXCLUSION_001] == UNKNOWN
    assert after[EXCLUSION_001] == SATISFIED

    for condition_id in ALL_CONDITION_IDS:
        if condition_id == EXCLUSION_001:
            continue

        assert before[condition_id] == after[condition_id], (
            f"article_39 不应影响 {condition_id}: "
            f"before={before[condition_id]!r}, "
            f"after={after[condition_id]!r}"
        )

    print("PASS")
    print("  article_39=None → EXCLUSION-001 UNKNOWN")
    print("  article_39=True → EXCLUSION-001 SATISFIED")
    print("  其他 7 个条件状态保持不变")
    print()


# ============================================================
# CASE 05
# Article 40(1) 只能影响 EXCLUSION-002
# ============================================================

def test_article_40_1_isolated():
    print("=" * 70)
    print("CASE 05  article_40_1 字段隔离")
    print("=" * 70)

    base_facts = LegalFacts(
        contract_sequence=make_contract_sequence(3),
        article_40_1=None,
    )

    excluded_facts = replace(
        base_facts,
        article_40_1=True,
    )

    before = statuses(base_facts)
    after = statuses(excluded_facts)

    assert before[EXCLUSION_002] == UNKNOWN
    assert after[EXCLUSION_002] == SATISFIED

    for condition_id in ALL_CONDITION_IDS:
        if condition_id == EXCLUSION_002:
            continue

        assert before[condition_id] == after[condition_id], (
            f"article_40_1 不应影响 {condition_id}: "
            f"before={before[condition_id]!r}, "
            f"after={after[condition_id]!r}"
        )

    print("PASS")
    print("  article_40_1=None → EXCLUSION-002 UNKNOWN")
    print("  article_40_1=True → EXCLUSION-002 SATISFIED")
    print("  其他 7 个条件状态保持不变")
    print()


# ============================================================
# CASE 06
# Article 40(2) 只能影响 EXCLUSION-003
# ============================================================

def test_article_40_2_isolated():
    print("=" * 70)
    print("CASE 06  article_40_2 字段隔离")
    print("=" * 70)

    base_facts = LegalFacts(
        contract_sequence=make_contract_sequence(3),
        article_40_2=None,
    )

    excluded_facts = replace(
        base_facts,
        article_40_2=True,
    )

    before = statuses(base_facts)
    after = statuses(excluded_facts)

    assert before[EXCLUSION_003] == UNKNOWN
    assert after[EXCLUSION_003] == SATISFIED

    for condition_id in ALL_CONDITION_IDS:
        if condition_id == EXCLUSION_003:
            continue

        assert before[condition_id] == after[condition_id], (
            f"article_40_2 不应影响 {condition_id}: "
            f"before={before[condition_id]!r}, "
            f"after={after[condition_id]!r}"
        )

    print("PASS")
    print("  article_40_2=None → EXCLUSION-003 UNKNOWN")
    print("  article_40_2=True → EXCLUSION-003 SATISFIED")
    print("  其他 7 个条件状态保持不变")
    print()


# ============================================================
# CASE 07
# fixed_term_exception 只能影响 EXCEPTION-001
# ============================================================

def test_fixed_term_exception_isolated():
    print("=" * 70)
    print("CASE 07  fixed_term_exception 字段隔离")
    print("=" * 70)

    base_facts = LegalFacts(
        contract_sequence=make_contract_sequence(3),
        fixed_term_exception=None,
    )

    exception_facts = replace(
        base_facts,
        fixed_term_exception=True,
    )

    before = statuses(base_facts)
    after = statuses(exception_facts)

    assert before[EXCEPTION_001] == UNKNOWN
    assert after[EXCEPTION_001] == SATISFIED

    for condition_id in ALL_CONDITION_IDS:
        if condition_id == EXCEPTION_001:
            continue

        assert before[condition_id] == after[condition_id], (
            f"fixed_term_exception 不应影响 {condition_id}: "
            f"before={before[condition_id]!r}, "
            f"after={after[condition_id]!r}"
        )

    print("PASS")
    print("  fixed_term_exception=None → EXCEPTION-001 UNKNOWN")
    print("  fixed_term_exception=True → EXCEPTION-001 SATISFIED")
    print("  其他 7 个条件状态保持不变")
    print()


# ============================================================
# CASE 08
# False 必须严格产生 NOT_SATISFIED
# ============================================================

def test_explicit_false_status():
    print("=" * 70)
    print("CASE 08  明确 False 必须产生 NOT_SATISFIED")
    print("=" * 70)

    cases = [
        (
            "article_39",
            EXCLUSION_001,
        ),
        (
            "article_40_1",
            EXCLUSION_002,
        ),
        (
            "article_40_2",
            EXCLUSION_003,
        ),
        (
            "fixed_term_exception",
            EXCEPTION_001,
        ),
    ]

    for field_name, condition_id in cases:
        facts = LegalFacts(
            contract_sequence=make_contract_sequence(3),
        )

        facts = replace(
            facts,
            **{field_name: False},
        )

        result = evaluate(
            condition_id,
            facts,
        )

        assert result.status == NOT_SATISFIED, (
            f"{field_name} = False 时，"
            f"{condition_id} 应为 NOT_SATISFIED，"
            f"实际为 {result.status!r}"
        )

        print(
            f"  {field_name}=False "
            f"→ {condition_id} → NOT_SATISFIED"
        )

    print("PASS")
    print()


# ============================================================
# CASE 09
# None 必须严格保持 UNKNOWN
# ============================================================

def test_none_status_fidelity():
    print("=" * 70)
    print("CASE 09  None 必须保持 UNKNOWN")
    print("=" * 70)

    facts = LegalFacts(
        contract_sequence=make_contract_sequence(3),
        completed_renewal=None,
        worker_agreement=None,
        article_39=None,
        article_40_1=None,
        article_40_2=None,
        fixed_term_exception=None,
    )

    results = statuses(facts)

    expected_unknown = [
        REQUIRED_003,
        REQUIRED_004,
        EXCLUSION_001,
        EXCLUSION_002,
        EXCLUSION_003,
        EXCEPTION_001,
    ]

    for condition_id in expected_unknown:
        assert results[condition_id] == UNKNOWN, (
            f"{condition_id}: "
            f"None 不得升级为 {results[condition_id]!r}"
        )

        print(
            f"  {condition_id} → UNKNOWN"
        )

    print("PASS")
    print()


# ============================================================
# Main
# ============================================================

def main():
    print()
    print("=" * 70)
    print("RAG V6.10 LegalFacts → ConditionResult Boundary Regression Test")
    print("=" * 70)
    print()
    print("测试目标：")
    print("  LegalFacts → ConditionResult")
    print()
    print("核心原则：")
    print("  UNKNOWN 不得自动升级")
    print("  一个事实字段不得影响其他条件")
    print("  三次固定期限合同不得自动推出隐含事实")
    print()

    tests = [
        test_three_fixed_term_contracts_boundary,
        test_completed_renewal_isolated,
        test_worker_agreement_isolated,
        test_article_39_isolated,
        test_article_40_1_isolated,
        test_article_40_2_isolated,
        test_fixed_term_exception_isolated,
        test_explicit_false_status,
        test_none_status_fidelity,
    ]

    passed = 0

    for test in tests:
        test()
        passed += 1

    print("=" * 70)
    print(f"V6.10 LegalFacts → ConditionResult Boundary: PASS")
    print(f"PASS {passed}/{len(tests)}")
    print("=" * 70)


if __name__ == "__main__":
    main()
