# -*- coding: utf-8 -*-

"""
RAG V6.2 Rule-Agnostic Validator Regression Test

测试目标：

    validate_condition_structure()

必须完全依据 Runtime Rule 的
condition_definitions 验证 ConditionResult。

本测试不使用 Article 14 Canonical Rule，
也不修改 Rule Registry。

核心原则：

    Runtime Rule 定义什么结构
            ↓
    Validator 验证什么结构

因此 Validator 不得固定假设：

    ConditionResult = 8
    REQUIRED = 4
    EXCLUSION = 3
    EXCEPTION = 1
"""

from src.legal_decision_engine import (
    ConditionResult,
    validate_condition_structure,
)


def build_test_rule():
    """
    构造一个与 Article 14 完全不同的 Runtime Rule。

    结构：

        REQUIRED   × 1
        EXCLUSION  × 1
        EXCEPTION  × 1

        总计 = 3
    """
    return {
        "rule_id": "TEST-RULE-V6.2-001",
        "law_name": "V6.2 Test Law",
        "article_number": "测试条款",
        "rule_name": "Rule-Agnostic Validator Test",
        "condition_definitions": [
            {
                "condition_id": "TEST-REQUIRED-001",
                "condition": "测试必要条件",
                "condition_type": "REQUIRED",
            },
            {
                "condition_id": "TEST-EXCLUSION-001",
                "condition": "测试排除条件",
                "condition_type": "EXCLUSION",
            },
            {
                "condition_id": "TEST-EXCEPTION-001",
                "condition": "测试例外条件",
                "condition_type": "EXCEPTION",
            },
        ],
    }


def build_test_results():
    """
    构造与 Runtime Rule 完全匹配的 3 个 ConditionResult。
    """
    return [
        ConditionResult(
            condition_id="TEST-REQUIRED-001",
            condition="测试必要条件",
            condition_type="REQUIRED",
            status="SATISFIED",
            reason="测试条件满足。",
        ),
        ConditionResult(
            condition_id="TEST-EXCLUSION-001",
            condition="测试排除条件",
            condition_type="EXCLUSION",
            status="NOT_SATISFIED",
            reason="测试排除条件不成立。",
        ),
        ConditionResult(
            condition_id="TEST-EXCEPTION-001",
            condition="测试例外条件",
            condition_type="EXCEPTION",
            status="NOT_SATISFIED",
            reason="测试例外条件不成立。",
        ),
    ]


def main():
    print("=" * 70)
    print("RAG V6.2 Rule-Agnostic Validator Regression Test")
    print("=" * 70)

    rule = build_test_rule()
    condition_results = build_test_results()

    print()
    print("Runtime Rule:")
    print("  REQUIRED   = 1")
    print("  EXCLUSION  = 1")
    print("  EXCEPTION  = 1")
    print("  TOTAL      = 3")

    print()
    print("ConditionResult:")
    print(f"  TOTAL      = {len(condition_results)}")

    print()
    print("[1] 验证非 Article 14 的 3 条条件结构")

    try:
        validate_condition_structure(
            condition_results,
            rule,
        )
    except Exception as exc:
        raise AssertionError(
            "Rule-Agnostic Validator 应接受合法的 3 条 Runtime Rule："
            f"{type(exc).__name__}: {exc}"
        ) from exc

    print("PASS")

    print()
    print("[2] 验证数量不再固定为 Article 14 的 8 条")

    assert len(condition_results) != 8
    print("PASS: Validator 成功处理 3 条条件")

    print()
    print("[3] 验证 REQUIRED / EXCLUSION / EXCEPTION 数量来自 Runtime Rule")

    actual_types = [
        item.condition_type
        for item in condition_results
    ]

    expected_types = [
        "REQUIRED",
        "EXCLUSION",
        "EXCEPTION",
    ]

    assert actual_types == expected_types
    print("PASS")

    print()
    print("[4] 验证 Condition ID 来自 Runtime Rule")

    actual_ids = [
        item.condition_id
        for item in condition_results
    ]

    expected_ids = [
        definition["condition_id"]
        for definition in rule["condition_definitions"]
    ]

    assert actual_ids == expected_ids
    print("PASS")

    print()
    print("[5] 验证非法 ConditionResult 会被 Runtime Rule Validator 拦截")

    invalid_results = list(condition_results)

    invalid_results[0] = ConditionResult(
        condition_id="TEST-REQUIRED-001",
        condition="测试必要条件",
        condition_type="EXCLUSION",
        status="SATISFIED",
        reason="非法测试状态。",
    )

    try:
        validate_condition_structure(
            invalid_results,
            rule,
        )
    except ValueError:
        print("PASS: 非法 condition_type 已被拦截")
    else:
        raise AssertionError(
            "Validator 未拦截与 Runtime Rule 不一致的 condition_type。"
        )

    print()
    print("=" * 70)
    print("🎉 RAG V6.2 Rule-Agnostic Validator Test 全部通过")
    print("=" * 70)


if __name__ == "__main__":
    main()


# ============================================================
# ConditionResult Runtime Type Boundary Tests
# ============================================================

import pytest
from dataclasses import replace

from src.legal_constants import (
    SATISFIED,
    NOT_SATISFIED,
    UNKNOWN,
    REQUIRED,
    EXCLUSION,
    EXCEPTION,
)


@pytest.mark.parametrize(
    ("field", "invalid_value"),
    [
        ("condition_id", 123),
        ("condition", None),
        ("condition_type", None),
        ("status", None),
        ("status", 123),
        ("reason", None),
        ("reason", 123),
    ],
)
def test_condition_result_field_types_are_validated(
    field,
    invalid_value,
):
    rule = build_test_rule()
    results = build_test_results()

    results[0] = replace(
        results[0],
        **{field: invalid_value},
    )

    with pytest.raises((TypeError, ValueError)):
        validate_condition_structure(results, rule)


@pytest.mark.parametrize(
    "status",
    [
        SATISFIED,
        NOT_SATISFIED,
        UNKNOWN,
    ],
)
def test_condition_result_accepts_legal_status_values(status):
    rule = build_test_rule()
    results = build_test_results()

    results[0] = replace(
        results[0],
        status=status,
    )

    validate_condition_structure(results, rule)


def test_condition_result_accepts_empty_reason_string():
    rule = build_test_rule()
    results = build_test_results()

    results[0] = replace(
        results[0],
        reason="",
    )

    validate_condition_structure(results, rule)


def test_condition_structure_rejects_non_condition_result_object():
    rule = build_test_rule()
    results = build_test_results()
    results[0] = object()

    with pytest.raises((TypeError, ValueError)):
        validate_condition_structure(results, rule)
