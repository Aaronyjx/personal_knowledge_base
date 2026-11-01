# -*- coding: utf-8 -*-

"""
Engine validate_decision_result 独立回归测试。

测试边界：
    直接调用 Decision Engine 的 validate_decision_result()；
    不经过 Answer Builder、Prompt、LLM 或 Final Validator。

规则来源：
    正式 Canonical Rule Registry
    -> canonical_rule_to_runtime_rule()
"""

from copy import deepcopy

import pytest

from src.legal_constants import (
    DEFINITE,
    CONDITIONAL,
    NOT_ESTABLISHED,
    SATISFIED,
    NOT_SATISFIED,
    UNKNOWN,
    REQUIRED,
    EXCLUSION,
    EXCEPTION,
)
from src.legal_decision_engine import (
    ConditionResult,
    DecisionResult,
    validate_decision_result,
)
from src.legal_rule_definition import RULE_ID
from src.legal_rule_registry import get_rule
from src.legal_runtime_rule_adapter import (
    canonical_rule_to_runtime_rule,
)


@pytest.fixture
def runtime_rule():
    """通过正式 Registry 和生产 Adapter 获取 Runtime Rule。"""
    canonical_rule = get_rule(RULE_ID)
    return canonical_rule_to_runtime_rule(canonical_rule)


def make_decision(runtime_rule, decision, status_overrides=None):
    """按 Runtime Rule 顺序构造完整 DecisionResult。"""
    status_overrides = status_overrides or {}
    condition_results = []

    for definition in runtime_rule["condition_definitions"]:
        condition_id = definition["condition_id"]

        condition_results.append(
            ConditionResult(
                condition_id=condition_id,
                condition=definition["condition"],
                status=status_overrides.get(
                    condition_id,
                    {
                        REQUIRED: SATISFIED,
                        EXCLUSION: NOT_SATISFIED,
                        EXCEPTION: NOT_SATISFIED,
                    }[definition["condition_type"]],
                ),
                reason="Engine 校验器独立回归测试",
                condition_type=definition["condition_type"],
            )
        )

    return DecisionResult(
        decision=decision,
        condition_results=condition_results,
        explicit_facts=[],
        contract_sequence=None,
        rule_dependencies=[],
        selected_rule=deepcopy(runtime_rule),
        explanation="Engine 校验器独立回归测试",
        selected_rule_id=runtime_rule.get("rule_id"),
    )


def condition_id_for_type(runtime_rule, condition_type):
    """获取指定类型的第一条正式条件 ID。"""
    for definition in runtime_rule["condition_definitions"]:
        if definition["condition_type"] == condition_type:
            return definition["condition_id"]

    raise AssertionError(
        f"Runtime Rule 缺少条件类型：{condition_type}"
    )


def test_rejects_non_decision_result(runtime_rule):
    """非 DecisionResult 必须被拒绝。"""
    with pytest.raises(TypeError, match="DecisionResult"):
        validate_decision_result({}, runtime_rule)


def test_rejects_invalid_decision_status(runtime_rule):
    """非法决策状态必须被拒绝。"""
    decision = make_decision(
        runtime_rule,
        "INVALID_DECISION_STATUS",
    )

    with pytest.raises(ValueError, match="非法 Decision 状态"):
        validate_decision_result(decision, runtime_rule)


def test_unknown_cannot_produce_definite(runtime_rule):
    """存在 UNKNOWN 时，不得输出 DEFINITE。"""
    required_id = condition_id_for_type(runtime_rule, REQUIRED)
    decision = make_decision(
        runtime_rule,
        DEFINITE,
        {required_id: UNKNOWN},
    )

    with pytest.raises(ValueError, match="UNKNOWN"):
        validate_decision_result(decision, runtime_rule)


def test_unsatisfied_required_must_be_not_established(runtime_rule):
    """REQUIRED 未满足时，必须输出 NOT_ESTABLISHED。"""
    required_id = condition_id_for_type(runtime_rule, REQUIRED)
    decision = make_decision(
        runtime_rule,
        CONDITIONAL,
        {required_id: NOT_SATISFIED},
    )

    with pytest.raises(ValueError, match="REQUIRED"):
        validate_decision_result(decision, runtime_rule)


def test_triggered_exclusion_must_be_not_established(runtime_rule):
    """EXCLUSION 已触发时，必须输出 NOT_ESTABLISHED。"""
    exclusion_id = condition_id_for_type(runtime_rule, EXCLUSION)
    decision = make_decision(
        runtime_rule,
        DEFINITE,
        {exclusion_id: SATISFIED},
    )

    with pytest.raises(ValueError, match="EXCLUSION"):
        validate_decision_result(decision, runtime_rule)


def test_triggered_exception_must_be_not_established(runtime_rule):
    """EXCEPTION 已触发时，必须输出 NOT_ESTABLISHED。"""
    exception_id = condition_id_for_type(runtime_rule, EXCEPTION)
    decision = make_decision(
        runtime_rule,
        DEFINITE,
        {exception_id: SATISFIED},
    )

    with pytest.raises(ValueError, match="EXCEPTION"):
        validate_decision_result(decision, runtime_rule)


def test_valid_conditional_passes(runtime_rule):
    """有 UNKNOWN 且无阻断条件时，CONDITIONAL 应通过。"""
    condition_results = []

    for definition in runtime_rule["condition_definitions"]:
        condition_results.append(
            ConditionResult(
                condition_id=definition["condition_id"],
                condition=definition["condition"],
                status=UNKNOWN,
                reason="合法 CONDITIONAL 测试",
                condition_type=definition["condition_type"],
            )
        )

    decision = DecisionResult(
        decision=CONDITIONAL,
        condition_results=condition_results,
        explicit_facts=[],
        contract_sequence=None,
        rule_dependencies=[],
        selected_rule=deepcopy(runtime_rule),
        explanation="合法 CONDITIONAL 测试",
        selected_rule_id=runtime_rule.get("rule_id"),
    )

    validate_decision_result(decision, runtime_rule)


def test_valid_definite_passes(runtime_rule):
    """所有条件满足且无 UNKNOWN 时，DEFINITE 应通过。"""
    decision = make_decision(runtime_rule, DEFINITE)

    validate_decision_result(decision, runtime_rule)


@pytest.mark.parametrize(
    ("condition_type", "status"),
    [
        (REQUIRED, NOT_SATISFIED),
        (EXCLUSION, SATISFIED),
        (EXCEPTION, SATISFIED),
    ],
)
def test_blocking_condition_allows_not_established(
    runtime_rule,
    condition_type,
    status,
):
    """任一阻断条件成立时，NOT_ESTABLISHED 应通过。"""
    target_id = condition_id_for_type(
        runtime_rule,
        condition_type,
    )

    decision = make_decision(
        runtime_rule,
        NOT_ESTABLISHED,
        {target_id: status},
    )

    validate_decision_result(decision, runtime_rule)

def test_rejects_selected_rule_identity_mismatch(runtime_rule):
    """selected_rule 与传入 Runtime Rule 身份不一致时必须拒绝。"""
    decision = make_decision(runtime_rule, DEFINITE)
    decision.selected_rule["rule_id"] = "RULE-OTHER-TEST"

    with pytest.raises(ValueError):
        validate_decision_result(decision, runtime_rule)

def test_rejects_rule_identity_mutation_on_both_sides(runtime_rule):
    """两份规则字典被同步篡改时，独立身份快照仍必须拦截。"""
    decision = make_decision(runtime_rule, DEFINITE)

    decision.selected_rule["rule_id"] = "RULE-OTHER-TEST"
    runtime_rule["rule_id"] = "RULE-OTHER-TEST"

    with pytest.raises(ValueError, match="身份"):
        validate_decision_result(decision, runtime_rule)


@pytest.mark.parametrize(
    ("field", "invalid_value", "error_type", "message"),
    [
        ("runtime_rule_id", None, ValueError, "Runtime Rule"),
        ("runtime_rule_id", "", ValueError, "Runtime Rule"),
        ("runtime_rule_id", 123, ValueError, "Runtime Rule"),
        ("selected_rule_id", None, ValueError, "selected_rule"),
        ("selected_rule_id", "", ValueError, "selected_rule"),
        ("selected_rule_id", 123, ValueError, "selected_rule"),
        ("identity_snapshot", None, ValueError, "身份快照"),
        ("identity_snapshot", "", ValueError, "身份快照"),
        ("identity_snapshot", 123, ValueError, "身份快照"),
    ],
)
def test_rejects_invalid_rule_identity_fields(
    runtime_rule,
    field,
    invalid_value,
    error_type,
    message,
):
    """任一规则身份字段缺失、为空或类型错误时必须拒绝。"""
    decision = make_decision(runtime_rule, DEFINITE)

    if field == "runtime_rule_id":
        runtime_rule["rule_id"] = invalid_value
    elif field == "selected_rule_id":
        decision.selected_rule["rule_id"] = invalid_value
    else:
        decision.selected_rule_id = invalid_value

    with pytest.raises(error_type, match=message):
        validate_decision_result(decision, runtime_rule)

@pytest.mark.parametrize(
    "invalid_rule",
    [None, "not-a-dict"],
)
def test_rejects_non_dict_runtime_rule(runtime_rule, invalid_rule):
    """传入的 Runtime Rule 不是字典时必须拒绝。"""
    decision = make_decision(runtime_rule, DEFINITE)

    with pytest.raises(TypeError, match="rule 必须为字典"):
        validate_decision_result(decision, invalid_rule)


@pytest.mark.parametrize(
    "invalid_selected_rule",
    [None, "not-a-dict"],
)
def test_rejects_non_dict_selected_rule(
    runtime_rule,
    invalid_selected_rule,
):
    """DecisionResult.selected_rule 不是字典时必须拒绝。"""
    decision = make_decision(runtime_rule, DEFINITE)
    decision.selected_rule = invalid_selected_rule

    with pytest.raises(TypeError, match="selected_rule 必须为字典"):
        validate_decision_result(decision, runtime_rule)
