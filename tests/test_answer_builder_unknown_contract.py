# -*- coding: utf-8 -*-

"""
StructuredAnswer UNKNOWN 兼容契约回归测试。

测试规则来源于正式 Canonical Rule Registry，
并通过生产 Runtime Rule Adapter 构造 selected_rule。

验证：
1. unknown_conditions 只包含 REQUIRED + UNKNOWN。
2. EXCLUSION / EXCEPTION 的 UNKNOWN 不进入该兼容字段。
3. 所有条件的真实状态仍完整保留在 condition_results。
4. Builder 不改变 Decision Engine 已产生的状态。
5. 测试条件结构动态来源于 Runtime Rule，不另造规则。
"""

from copy import deepcopy

from src.legal_constants import (
    SATISFIED,
    UNKNOWN,
    REQUIRED,
    EXCLUSION,
    EXCEPTION,
    CONDITIONAL,
)
from src.legal_answer_builder import build_structured_answer
from src.legal_decision_engine import (
    ConditionResult,
    DecisionResult,
)
from src.legal_rule_definition import RULE_ID
from src.legal_rule_registry import get_rule
from src.legal_runtime_rule_adapter import (
    canonical_rule_to_runtime_rule,
)


def make_runtime_rule():
    """通过正式 Registry 和 Adapter 获取 Runtime Rule。"""
    canonical_rule = get_rule(RULE_ID)
    return canonical_rule_to_runtime_rule(canonical_rule)


def make_condition_results(runtime_rule):
    """按 Runtime Rule 动态构造完整 ConditionResult。"""

    definitions = runtime_rule["condition_definitions"]

    if not isinstance(definitions, list):
        raise AssertionError(
            "Runtime Rule.condition_definitions 必须是 list"
        )

    definitions_by_name = {}

    for definition in definitions:
        if not isinstance(definition, dict):
            raise AssertionError(
                "Runtime Rule.condition_definitions 元素必须是 dict"
            )

        condition_name = definition.get("condition")
        condition_id = definition.get("condition_id")

        if not isinstance(condition_name, str) or not condition_name:
            raise AssertionError(
                f"Runtime Rule 存在非法 condition：{definition!r}"
            )

        if not isinstance(condition_id, str) or not condition_id:
            raise AssertionError(
                f"Runtime Rule 存在非法 condition_id：{definition!r}"
            )

        if condition_name in definitions_by_name:
            raise AssertionError(
                f"Runtime Rule 存在重复条件定义：{condition_name}"
            )

        definitions_by_name[condition_name] = condition_id

    condition_results = []

    groups = (
        (REQUIRED, runtime_rule["conditions"]),
        (EXCLUSION, runtime_rule["exclusion_conditions"]),
        (EXCEPTION, runtime_rule["exceptions"]),
    )

    for condition_type, condition_names in groups:
        for condition_name in condition_names:
            if condition_name not in definitions_by_name:
                raise AssertionError(
                    "Runtime Rule 条件缺少 condition_definitions："
                    f"{condition_name}"
                )

            # 将前两条 REQUIRED 设为 SATISFIED；
            # 其余条件设为 UNKNOWN。
            if (
                condition_type == REQUIRED
                and sum(
                    item.condition_type == REQUIRED
                    for item in condition_results
                ) < 2
            ):
                status = SATISFIED
            else:
                status = UNKNOWN

            condition_results.append(
                ConditionResult(
                    condition_id=definitions_by_name[condition_name],
                    condition=condition_name,
                    status=status,
                    reason="UNKNOWN 兼容契约测试",
                    condition_type=condition_type,
                )
            )

    return condition_results


def make_decision():
    """构造结构与真实 Runtime Rule 一致的 DecisionResult。"""

    runtime_rule = make_runtime_rule()
    condition_results = make_condition_results(runtime_rule)

    decision = DecisionResult(
        decision=CONDITIONAL,
        condition_results=condition_results,
        explicit_facts=[
            "用于测试的明确事实",
        ],
        contract_sequence=None,
        rule_dependencies=[],
        selected_rule=deepcopy(runtime_rule),
        explanation="UNKNOWN 兼容契约测试",
    )

    return decision, runtime_rule


def test_unknown_conditions_contains_only_required_unknown():
    """兼容字段只包含 REQUIRED + UNKNOWN。"""

    decision, runtime_rule = make_decision()
    answer = build_structured_answer(decision)

    expected = [
        name
        for name in runtime_rule["conditions"]
        if any(
            item.condition == name
            and item.condition_type == REQUIRED
            and item.status == UNKNOWN
            for item in decision.condition_results
        )
    ]

    assert answer.unknown_conditions == expected


def test_exclusion_and_exception_unknown_are_preserved_in_condition_results():
    """非 REQUIRED 的 UNKNOWN 不进入兼容字段，但完整状态仍保留。"""

    decision, runtime_rule = make_decision()
    answer = build_structured_answer(decision)

    before = {
        item.condition_id: (
            item.status,
            item.condition_type,
        )
        for item in decision.condition_results
    }

    after = {
        item.condition_id: (
            item.status,
            item.condition_type,
        )
        for item in answer.condition_results
    }

    assert after == before

    for condition_type, names in (
        (EXCLUSION, runtime_rule["exclusion_conditions"]),
        (EXCEPTION, runtime_rule["exceptions"]),
    ):
        for name in names:
            original = next(
                item
                for item in decision.condition_results
                if item.condition == name
            )

            if original.status == UNKNOWN:
                assert name not in answer.unknown_conditions

                converted = next(
                    item
                    for item in answer.condition_results
                    if item.condition == name
                )

                assert converted.status == UNKNOWN
                assert converted.condition_type == condition_type


def test_builder_preserves_all_condition_statuses():
    """Builder 转换前后不得改变条件状态或 Runtime Rule。"""

    decision, runtime_rule = make_decision()

    before_statuses = {
        item.condition_id: item.status
        for item in decision.condition_results
    }
    before_rule = deepcopy(decision.selected_rule)

    answer = build_structured_answer(decision)

    after_statuses = {
        item.condition_id: item.status
        for item in answer.condition_results
    }

    assert after_statuses == before_statuses
    assert decision.selected_rule == before_rule
    assert answer.selected_rule == runtime_rule
    assert len(answer.condition_results) == len(
        runtime_rule["conditions"]
        + runtime_rule["exclusion_conditions"]
        + runtime_rule["exceptions"]
    )
