from dataclasses import fields

from src.legal_decision_engine import (
    ConditionResult,
    NOT_SATISFIED,
    REQUIRED,
    SATISFIED,
    UNKNOWN,
    RuleDependency,
    build_rule_dependency,
)


def make_result(status, condition="测试法律条件"):
    """构造用于 RuleDependency 边界测试的 ConditionResult。"""
    return ConditionResult(
        condition_id="TEST-REQUIRED-001",
        condition=condition,
        status=status,
        reason="RuleDependency 边界测试",
        condition_type=REQUIRED,
    )


def make_rule_dependency(results):
    """通过生产函数构造 RuleDependency。"""
    return build_rule_dependency(
        condition_results=results,
        rule={"rule_id": "TEST-RULE-001"},
    )


def test_all_satisfied_does_not_claim_unproven_conditions():
    dependency = make_rule_dependency([
        make_result(SATISFIED),
    ])

    assert dependency.not_proven_by_fact == []
    assert "仍存在未被事实充分证明的法律条件" not in dependency.explanation


def test_unknown_is_not_described_as_definitive():
    dependency = make_rule_dependency([
        make_result(UNKNOWN),
    ])

    assert dependency.not_proven_by_fact == ["测试法律条件"]
    assert "当前条件均已获得明确状态" not in dependency.explanation


def test_not_satisfied_remains_in_legacy_not_proven_field():
    dependency = make_rule_dependency([
        make_result(NOT_SATISFIED),
    ])

    assert dependency.satisfied_by_fact == []
    assert dependency.not_proven_by_fact == ["测试法律条件"]


def test_rule_dependency_legacy_fields_and_serialization_are_preserved():
    dependency = RuleDependency(
        rule_name="测试规则",
        satisfied_by_fact=["已满足条件"],
        not_proven_by_fact=["尚未证明条件"],
        explanation="兼容性测试",
    )

    assert [item.name for item in fields(RuleDependency)] == [
        "rule_name",
        "satisfied_by_fact",
        "not_proven_by_fact",
        "explanation",
    ]

    assert dependency.to_dict() == {
        "rule_name": "测试规则",
        "satisfied_by_fact": ["已满足条件"],
        "not_proven_by_fact": ["尚未证明条件"],
        "explanation": "兼容性测试",
    }


def test_all_satisfied_explanation_reports_no_unproven_conditions():
    dependency = make_rule_dependency([
        make_result(SATISFIED),
    ])

    assert "当前条件均已获得明确状态" in dependency.explanation
    assert "当前仍存在未被事实充分证明的法律条件" not in dependency.explanation


def test_unknown_explanation_reports_unproven_conditions():
    dependency = make_rule_dependency([
        make_result(UNKNOWN),
    ])

    assert "当前仍存在未被事实充分证明的法律条件" in dependency.explanation
    assert "当前条件均已获得明确状态" not in dependency.explanation
