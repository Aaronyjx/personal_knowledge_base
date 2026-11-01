# -*- coding: utf-8 -*-

"""
Answer Builder Condition ID Integrity Regression Tests

测试目标：
1. 正常 Runtime Rule 与 ConditionResult 必须通过校验。
2. 不存在的 condition_id 必须被拒绝。
3. 交换 ID 后必须被拒绝。
4. 重复 ID 必须被拒绝。
5. ID 与条件文本的对应关系被破坏时必须被拒绝。
6. ID 与 condition_type 的对应关系被破坏时必须被拒绝。
7. 同时验证 strict=True 和 strict=False。
"""

from copy import deepcopy
from dataclasses import replace

import pytest

from src.legal_constants import (
    UNKNOWN,
    REQUIRED,
    EXCLUSION,
    EXCEPTION,
    CONDITIONAL,
    SATISFIED,
    NOT_SATISFIED,
    NOT_ESTABLISHED,
)
from src.legal_answer_builder import (
    build_structured_answer,
    validate_condition_structure,
)
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
    """使用正式 Canonical Rule Registry 和生产 Adapter。"""
    canonical_rule = get_rule(RULE_ID)
    return canonical_rule_to_runtime_rule(canonical_rule)


def make_decision():
    """依据正式 Runtime Rule 构造完整 DecisionResult。"""
    runtime_rule = make_runtime_rule()

    definitions = runtime_rule["condition_definitions"]
    definitions_by_name = {
        item["condition"]: item
        for item in definitions
    }

    condition_results = []

    groups = (
        (REQUIRED, runtime_rule["conditions"]),
        (EXCLUSION, runtime_rule["exclusion_conditions"]),
        (EXCEPTION, runtime_rule["exceptions"]),
    )

    for condition_type, names in groups:
        for name in names:
            definition = definitions_by_name[name]

            condition_results.append(
                ConditionResult(
                    condition_id=definition["condition_id"],
                    condition=name,
                    status=UNKNOWN,
                    reason="Condition ID 完整性回归测试",
                    condition_type=condition_type,
                )
            )

    decision = DecisionResult(
        decision=CONDITIONAL,
        condition_results=condition_results,
        explicit_facts=[],
        contract_sequence=None,
        rule_dependencies=[],
        selected_rule=deepcopy(runtime_rule),
        explanation="Condition ID 完整性回归测试",
    )

    return decision


def get_two_required_indexes(decision):
    """取得两条 REQUIRED 条件的位置，用于交换测试。"""
    indexes = [
        index
        for index, item in enumerate(decision.condition_results)
        if item.condition_type == REQUIRED
    ]

    assert len(indexes) >= 2, (
        "测试前提不满足：Runtime Rule 至少需要两条 REQUIRED 条件"
    )

    return indexes[0], indexes[1]


def mutate_unknown_id(decision):
    """将 ID 改成 Runtime Rule 中不存在的值。"""
    item = decision.condition_results[0]

    decision.condition_results[0] = replace(
        item,
        condition_id="NONEXISTENT-ID-999",
    )


def mutate_swapped_ids(decision):
    """交换两条 REQUIRED 条件的 ID，保留其他字段。"""
    first_index, second_index = get_two_required_indexes(decision)

    first = decision.condition_results[first_index]
    second = decision.condition_results[second_index]

    decision.condition_results[first_index] = replace(
        first,
        condition_id=second.condition_id,
    )
    decision.condition_results[second_index] = replace(
        second,
        condition_id=first.condition_id,
    )


def mutate_duplicate_id(decision):
    """将第二条条件的 ID 改为第一条条件的 ID。"""
    first = decision.condition_results[0]
    second = decision.condition_results[1]

    decision.condition_results[1] = replace(
        second,
        condition_id=first.condition_id,
    )


def mutate_condition_mapping(decision):
    """交换两条 REQUIRED 条件的文本，但保留各自的 ID。"""
    first_index, second_index = get_two_required_indexes(decision)

    first = decision.condition_results[first_index]
    second = decision.condition_results[second_index]

    decision.condition_results[first_index] = replace(
        first,
        condition=second.condition,
    )
    decision.condition_results[second_index] = replace(
        second,
        condition=first.condition,
    )


def mutate_condition_type_mapping(decision):
    """修改一条条件的类别，保留 ID 和条件文本。"""
    item = decision.condition_results[0]

    replacement_type = (
        EXCLUSION
        if item.condition_type == REQUIRED
        else REQUIRED
    )

    decision.condition_results[0] = replace(
        item,
        condition_type=replacement_type,
    )


INVALID_MUTATIONS = [
    pytest.param(
        mutate_unknown_id,
        id="reject-nonexistent-id",
    ),
    pytest.param(
        mutate_swapped_ids,
        id="reject-swapped-ids",
    ),
    pytest.param(
        mutate_duplicate_id,
        id="reject-duplicate-id",
    ),
    pytest.param(
        mutate_condition_mapping,
        id="reject-condition-text-id-mismatch",
    ),
    pytest.param(
        mutate_condition_type_mapping,
        id="reject-condition-type-id-mismatch",
    ),
]


def test_valid_runtime_rule_passes_strict_validation():
    """正常输入必须通过严格校验，并可构建 StructuredAnswer。"""
    decision = make_decision()

    result = validate_condition_structure(
        decision,
        strict=False,
    )

    assert result["valid"] is True

    answer = build_structured_answer(
        decision,
        strict=True,
    )

    assert len(answer.condition_results) == len(
        decision.condition_results
    )


@pytest.mark.parametrize("mutator", INVALID_MUTATIONS)
def test_invalid_condition_id_mapping_fails_strict_validation(mutator):
    """所有 ID 身份映射错误都必须使 strict=True 拒绝构建。"""
    decision = make_decision()
    mutator(decision)

    with pytest.raises(ValueError):
        build_structured_answer(
            decision,
            strict=True,
        )


@pytest.mark.parametrize("mutator", INVALID_MUTATIONS)
def test_invalid_condition_id_mapping_fails_non_strict_validation(mutator):
    """strict=False 不应把 ID 身份映射错误报告为 valid=True。"""
    decision = make_decision()
    mutator(decision)

    result = validate_condition_structure(
        decision,
        strict=False,
    )

    assert result["valid"] is False, (
        "Builder 接受了错误的 Condition ID 映射；"
        f"mutator={mutator.__name__}, result={result!r}"
    )
# STRICT_FALSE_INTEGRITY_REGRESSION_TESTS
# ============================================================
# strict=False 前置结构与 Builder 入口回归测试
# ============================================================

def mutate_missing_condition_definitions(decision):
    """模拟 Runtime Rule 缺少 condition_definitions。"""
    decision.selected_rule.pop(
        "condition_definitions",
        None,
    )


def mutate_invalid_condition_definitions_type(decision):
    """模拟 Runtime Rule 的 condition_definitions 类型错误。"""
    decision.selected_rule["condition_definitions"] = None


@pytest.mark.parametrize(
    "mutator",
    [
        pytest.param(
            mutate_missing_condition_definitions,
            id="missing-condition-definitions",
        ),
        pytest.param(
            mutate_invalid_condition_definitions_type,
            id="invalid-condition-definitions-type",
        ),
    ],
)
def test_non_strict_validation_reports_malformed_runtime_rule(mutator):
    """畸形 Runtime Rule 在非严格模式下必须返回 valid=False。"""
    decision = make_decision()
    mutator(decision)

    result = validate_condition_structure(
        decision,
        strict=False,
    )

    assert result["valid"] is False, (
        "畸形 Runtime Rule 不得被报告为校验通过；"
        f"mutator={mutator.__name__}, result={result!r}"
    )
    assert result["errors"], (
        "校验失败时必须提供诊断错误。"
    )


@pytest.mark.parametrize("mutator", INVALID_MUTATIONS)
def test_builder_rejects_invalid_condition_id_mapping_in_non_strict_mode(
    mutator,
):
    """strict=False 不能绕过 ID 完整性校验并构建答案。"""
    decision = make_decision()
    mutator(decision)

    with pytest.raises(
        ValueError,
        match="Builder 拒绝构建无效的 ConditionResult 结构",
    ):
        build_structured_answer(
            decision,
            strict=False,
        )


def test_builder_selected_rule_is_deeply_isolated():
    """Builder 输出规则的嵌套修改不得影响原始 DecisionResult。"""

    decision = make_decision()
    before_rule = deepcopy(decision.selected_rule)

    answer = build_structured_answer(decision)

    # 顶层字典必须是独立对象。
    assert answer.selected_rule is not decision.selected_rule

    # 嵌套定义列表也必须与原始规则隔离。
    assert (
        answer.selected_rule["condition_definitions"]
        is not decision.selected_rule["condition_definitions"]
    )

    # 修改 Builder 输出中的嵌套条件，不得影响原始 DecisionResult。
    answer.selected_rule["condition_definitions"][0]["condition"] = (
        "测试用的恶意修改"
    )

    assert decision.selected_rule == before_rule


# STRICT_WHITESPACE_IDENTITY_REGRESSION_TESTS
# ============================================================
# Condition ID 原始身份值必须精确匹配
# ============================================================

def test_builder_rejects_condition_result_id_with_surrounding_whitespace():
    """ConditionResult 的 condition_id 不得通过 strip() 被静默修复。"""
    decision = make_decision()

    original = decision.condition_results[0]
    decision.condition_results[0] = replace(
        original,
        condition_id=f" {original.condition_id} ",
    )

    with pytest.raises(ValueError):
        build_structured_answer(
            decision,
            strict=True,
        )


def test_builder_rejects_runtime_definition_id_with_surrounding_whitespace():
    """Runtime Rule 定义的 condition_id 必须是规范的原始身份值。"""
    decision = make_decision()

    definition = decision.selected_rule["condition_definitions"][0]
    definition["condition_id"] = (
        f" {definition['condition_id']} "
    )

    with pytest.raises(ValueError):
        build_structured_answer(
            decision,
            strict=True,
        )

# STRICT_CONDITION_TEXT_AND_TYPE_WHITESPACE_TESTS
# ============================================================
# condition 文本和 condition_type 分类值不得通过 strip() 静默修复
# ============================================================

def test_builder_rejects_runtime_definition_condition_with_surrounding_whitespace():
    """Runtime Rule 的 condition 文本不得包含未被拒绝的首尾空格。"""
    decision = make_decision()

    definition = decision.selected_rule["condition_definitions"][0]
    definition["condition"] = f" {definition['condition']} "

    with pytest.raises(ValueError):
        build_structured_answer(decision, strict=True)


def test_builder_rejects_condition_result_text_with_surrounding_whitespace():
    """ConditionResult 的 condition 文本必须与规则定义精确匹配。"""
    decision = make_decision()

    original = decision.condition_results[0]
    decision.condition_results[0] = replace(
        original,
        condition=f" {original.condition} ",
    )

    with pytest.raises(ValueError):
        build_structured_answer(decision, strict=True)


def test_builder_rejects_condition_result_type_with_surrounding_whitespace():
    """ConditionResult 的 condition_type 不得通过 strip() 静默修复。"""
    decision = make_decision()

    original = decision.condition_results[0]
    decision.condition_results[0] = replace(
        original,
        condition_type=f" {original.condition_type} ",
    )

    with pytest.raises(ValueError):
        build_structured_answer(decision, strict=True)


# STRICT_RAW_STATUS_VALIDATION_REGRESSION_TESTS
# ============================================================
# ConditionResult 原始状态必须在结构校验阶段通过验证
# ============================================================

from types import SimpleNamespace


@pytest.mark.parametrize(
    "status",
    [
        pytest.param("INVALID_STATUS", id="invalid-status"),
        pytest.param(" UNKNOWN ", id="status-with-surrounding-whitespace"),
        pytest.param(None, id="missing-status-value"),
    ],
)
def test_non_strict_validation_rejects_invalid_raw_status(status):
    """非严格结构校验必须拒绝非法、非规范或缺失的原始状态。"""
    decision = make_decision()
    original = decision.condition_results[0]

    if status is None:
        values = {
            key: value
            for key, value in vars(original).items()
            if key != "status"
        }
        decision.condition_results[0] = SimpleNamespace(**values)
    else:
        decision.condition_results[0] = replace(
            original,
            status=status,
        )

    result = validate_condition_structure(
        decision,
        strict=False,
    )

    assert result["valid"] is False, (
        "结构校验不应接受非法原始状态；"
        f"status={status!r}, result={result!r}"
    )
    assert result["errors"], (
        "非法原始状态必须提供诊断错误。"
    )


@pytest.mark.parametrize(
    "status",
    [
        pytest.param("INVALID_STATUS", id="invalid-status"),
        pytest.param(" UNKNOWN ", id="status-with-surrounding-whitespace"),
    ],
)
def test_strict_validation_rejects_invalid_raw_status(status):
    """严格结构校验必须直接拒绝非法或非规范的原始状态。"""
    decision = make_decision()
    original = decision.condition_results[0]

    decision.condition_results[0] = replace(
        original,
        status=status,
    )

    with pytest.raises(ValueError):
        validate_condition_structure(
            decision,
            strict=True,
        )


def test_valid_unknown_passes_raw_status_validation():
    """合法 UNKNOWN 必须通过结构校验且不被改变。"""
    decision = make_decision()

    result = validate_condition_structure(
        decision,
        strict=False,
    )

    assert result["valid"] is True
    assert all(
        item.status == UNKNOWN
        for item in decision.condition_results
    )


# STRICT_FALSE_ERROR_SCHEMA_REGRESSION_TEST
# ============================================================
# strict=False 异常返回结构一致性测试
# ============================================================

def test_non_strict_exception_result_contains_invalid_statuses():
    """Runtime Rule 前置结构异常时，结果仍须包含统一的状态诊断字段。"""
    decision = make_decision()
    decision.selected_rule.pop(
        "condition_definitions",
        None,
    )

    result = validate_condition_structure(
        decision,
        strict=False,
    )

    assert result["valid"] is False
    assert result["errors"]
    assert "invalid_statuses" in result
    assert isinstance(result["invalid_statuses"], list)



# RAW_CONDITION_TYPE_VALIDATION_REGRESSION_TESTS
# ============================================================
# 原始 condition_type 严格校验回归测试
# ============================================================

@pytest.mark.parametrize(
    "invalid_type",
    [" REQUIRED ", "required", "", None, 123],
)
def test_structure_validation_rejects_invalid_raw_condition_type(
    invalid_type,
):
    """结构验证不得清洗或转换非法分类值。"""
    decision = make_decision()
    original = decision.condition_results[0]

    decision.condition_results[0] = replace(
        original,
        condition_type=invalid_type,
    )

    result = validate_condition_structure(
        decision,
        strict=False,
    )

    assert result["valid"] is False
    assert result["invalid_condition_types"]


@pytest.mark.parametrize(
    "invalid_type",
    [" REQUIRED ", "required", "", None, 123],
)
def test_builder_rejects_invalid_raw_condition_type_in_non_strict_mode(
    invalid_type,
):
    """strict=False 不能让非法结构进入正式答案。"""
    decision = make_decision()
    original = decision.condition_results[0]

    decision.condition_results[0] = replace(
        original,
        condition_type=invalid_type,
    )

    with pytest.raises(ValueError):
        build_structured_answer(
            decision,
            strict=False,
        )


def test_explicit_invalid_condition_type_does_not_fall_back_to_type():
    """显式非法 condition_type 不得被合法 type 字段掩盖。"""
    from types import SimpleNamespace
    from src.legal_answer_builder import _condition_to_view

    item = SimpleNamespace(
        condition_id="TEST-REQUIRED-001",
        condition="测试法律条件",
        status=UNKNOWN,
        reason="分类字段回退测试",
        condition_type=" REQUIRED ",
        type=REQUIRED,
    )

    with pytest.raises(ValueError, match="condition_type 非法"):
        _condition_to_view(item)


def test_legacy_type_field_is_used_when_condition_type_is_absent():
    """仅缺失 condition_type 时兼容旧 type 字段。"""
    from types import SimpleNamespace
    from src.legal_answer_builder import _condition_to_view

    item = SimpleNamespace(
        condition_id="TEST-REQUIRED-001",
        condition="测试法律条件",
        status=UNKNOWN,
        reason="旧字段兼容测试",
        type=REQUIRED,
    )

    view = _condition_to_view(item)
    assert view.condition_type == REQUIRED


# UNKNOWN_CONDITIONS_TYPE_BOUNDARY_REGRESSION_TESTS
# ============================================================

def test_unknown_conditions_include_only_required_unknown():
    """unknown_conditions 只能包含 REQUIRED 且状态为 UNKNOWN 的条件。"""
    decision = make_decision()

    answer = build_structured_answer(decision)

    expected_required_unknown = [
        item.condition
        for item in decision.condition_results
        if (
            item.condition_type == REQUIRED
            and item.status == UNKNOWN
        )
    ]

    non_required_unknown = [
        item.condition
        for item in decision.condition_results
        if (
            item.condition_type in {EXCLUSION, EXCEPTION}
            and item.status == UNKNOWN
        )
    ]

    assert answer.unknown_conditions == expected_required_unknown

    for condition in non_required_unknown:
        assert condition not in answer.unknown_conditions, (
            "EXCLUSION 或 EXCEPTION 条件不得进入 unknown_conditions："
            f"{condition}"
        )

    # 非 REQUIRED 条件仍须保留在完整的条件结果中。
    answer_condition_ids = {
        view.condition_id
        for view in answer.condition_results
    }
    decision_non_required_ids = {
        item.condition_id
        for item in decision.condition_results
        if item.condition_type in {EXCLUSION, EXCEPTION}
    }

    assert decision_non_required_ids.issubset(answer_condition_ids)


def test_builder_rejects_invalid_status_in_non_strict_mode():
    """strict=False 也不得让非法状态进入正式 StructuredAnswer。"""
    decision = make_decision()
    original_item = decision.condition_results[0]

    decision.condition_results[0] = replace(
        original_item,
        status=" UNKNOWN ",
    )

    with pytest.raises(ValueError):
        build_structured_answer(
            decision,
            strict=False,
        )


# MIXED_STATUS_SUMMARY_CONSISTENCY_REGRESSION_TEST
# ============================================================

def test_mixed_status_summaries_match_condition_results():
    """混合状态下，汇总列表必须忠实反映完整条件结果。"""
    decision = make_decision()

    indexes_by_type = {
        REQUIRED: [],
        EXCLUSION: [],
        EXCEPTION: [],
    }

    for index, item in enumerate(decision.condition_results):
        indexes_by_type[item.condition_type].append(index)

    # 验证测试前提，避免规则变化后测试静默失效。
    assert len(indexes_by_type[REQUIRED]) >= 2
    assert len(indexes_by_type[EXCLUSION]) >= 2
    assert len(indexes_by_type[EXCEPTION]) >= 1

    # 构造不同类型、不同状态的组合。
    status_changes = {
        indexes_by_type[REQUIRED][0]: SATISFIED,
        indexes_by_type[REQUIRED][1]: NOT_SATISFIED,
        indexes_by_type[EXCLUSION][0]: SATISFIED,
        indexes_by_type[EXCLUSION][1]: NOT_SATISFIED,
        indexes_by_type[EXCEPTION][0]: SATISFIED,
    }

    for index, new_status in status_changes.items():
        decision.condition_results[index] = replace(
            decision.condition_results[index],
            status=new_status,
        )

    # REQUIRED 未满足、EXCLUSION 已触发或 EXCEPTION 已触发，
    # 均与 NOT_ESTABLISHED 的决策结果一致。
    decision.decision = NOT_ESTABLISHED

    answer = build_structured_answer(decision)

    # 汇总列表必须与原始 ConditionResult 状态一致。
    expected_satisfied = [
        item.condition
        for item in decision.condition_results
        if item.status == SATISFIED
    ]

    expected_not_satisfied = [
        item.condition
        for item in decision.condition_results
        if item.status == NOT_SATISFIED
    ]

    expected_required_unknown = [
        item.condition
        for item in decision.condition_results
        if (
            item.condition_type == REQUIRED
            and item.status == UNKNOWN
        )
    ]

    assert answer.satisfied_conditions == expected_satisfied
    assert answer.not_satisfied_conditions == expected_not_satisfied
    assert answer.unknown_conditions == expected_required_unknown

    # 完整 ConditionView 必须保留每条条件的身份、分类和原始状态。
    assert len(answer.condition_results) == len(
        decision.condition_results
    )

    for source, view in zip(
        decision.condition_results,
        answer.condition_results,
    ):
        assert view.condition_id == source.condition_id
        assert view.condition == source.condition
        assert view.condition_type == source.condition_type
        assert view.status == source.status

    # 排除条件和例外条件即使已经 SATISFIED，
    # 也必须保留在完整结果中。
    for condition_type in (EXCLUSION, EXCEPTION):
        expected_ids = {
            item.condition_id
            for item in decision.condition_results
            if (
                item.condition_type == condition_type
                and item.status == SATISFIED
            )
        }

        actual_ids = {
            view.condition_id
            for view in answer.condition_results
            if (
                view.condition_type == condition_type
                and view.status == SATISFIED
            )
        }

        assert actual_ids == expected_ids


# STRUCTURED_ANSWER_SERIALIZATION_STATUS_REGRESSION_TEST
# ============================================================

def test_structured_answer_to_dict_preserves_mixed_statuses():
    """序列化不得丢失或改变条件状态、分类及身份信息。"""
    decision = make_decision()

    indexes_by_type = {
        REQUIRED: [],
        EXCLUSION: [],
        EXCEPTION: [],
    }

    for index, item in enumerate(decision.condition_results):
        indexes_by_type[item.condition_type].append(index)

    # 确认当前 Runtime Rule 仍具备本测试需要的条件结构。
    assert len(indexes_by_type[REQUIRED]) >= 2
    assert len(indexes_by_type[EXCLUSION]) >= 2
    assert len(indexes_by_type[EXCEPTION]) >= 1

    status_changes = {
        indexes_by_type[REQUIRED][0]: SATISFIED,
        indexes_by_type[REQUIRED][1]: NOT_SATISFIED,
        indexes_by_type[EXCLUSION][0]: SATISFIED,
        indexes_by_type[EXCLUSION][1]: NOT_SATISFIED,
        indexes_by_type[EXCEPTION][0]: SATISFIED,
    }

    for index, new_status in status_changes.items():
        decision.condition_results[index] = replace(
            decision.condition_results[index],
            status=new_status,
        )

    decision.decision = NOT_ESTABLISHED

    answer = build_structured_answer(decision)
    payload = answer.to_dict()

    # 1. 汇总列表在序列化后必须保持原值和顺序。
    assert payload["satisfied_conditions"] == answer.satisfied_conditions
    assert payload["unknown_conditions"] == answer.unknown_conditions
    assert (
        payload["not_satisfied_conditions"]
        == answer.not_satisfied_conditions
    )

    # 2. 每条 ConditionView 必须序列化成包含全部身份字段的字典。
    expected_results = [
        view.to_dict()
        for view in answer.condition_results
    ]

    assert payload["condition_results"] == expected_results
    assert len(payload["condition_results"]) == len(
        decision.condition_results
    )

    # 3. 校验 ID、文本、状态、分类和兼容字段。
    for source, serialized in zip(
        decision.condition_results,
        payload["condition_results"],
    ):
        assert serialized["condition_id"] == source.condition_id
        assert serialized["condition"] == source.condition
        assert serialized["status"] == source.status
        assert serialized["condition_type"] == source.condition_type
        assert serialized["type"] == source.condition_type

    # 4. 序列化结果中，排除条件与例外条件仍保留各自状态。
    for condition_type in (EXCLUSION, EXCEPTION):
        expected = {
            item.condition_id: item.status
            for item in decision.condition_results
            if item.condition_type == condition_type
        }

        actual = {
            item["condition_id"]: item["status"]
            for item in payload["condition_results"]
            if item["condition_type"] == condition_type
        }

        assert actual == expected


def test_to_dict_selected_rule_isolation():
    """
    回归测试：修改序列化结果中的 selected_rule，
    不得反向修改 StructuredAnswer 内部的规则对象。
    """
    answer = build_structured_answer(
        make_decision()
    )

    original_rule = answer.selected_rule

    assert isinstance(original_rule, dict), (
        "测试前提不成立：selected_rule 应当是 dict，"
        f"实际类型为 {type(original_rule).__name__}"
    )

    original_snapshot = deepcopy(original_rule)
    payload = answer.to_dict()

    assert isinstance(payload["selected_rule"], dict)

    # 序列化结果必须与原始规则对象相互隔离。
    payload["selected_rule"]["__serialization_isolation_probe__"] = True

    assert answer.selected_rule == original_snapshot, (
        "发现引用泄漏：修改 to_dict() 返回的 selected_rule "
        "影响了 StructuredAnswer 内部的 selected_rule"
    )


# ============================================================
# ContractSequence 原始字段类型边界回归测试
# ============================================================

@pytest.mark.parametrize(
    "sequence",
    [
        pytest.param(
            {
                "count": ["3"],
                "term_type": "fixed",
                "continuous": True,
            },
            id="dict-count-list",
        ),
        pytest.param(
            {
                "count": 3,
                "term_type": {"value": "fixed"},
                "continuous": True,
            },
            id="dict-term-type-dict",
        ),
        pytest.param(
            {
                "count": 3,
                "term_type": "fixed",
                "continuous": "false",
            },
            id="dict-continuous-string",
        ),
        pytest.param(
            __import__("types").SimpleNamespace(
                count=["3"],
                term_type="fixed",
                continuous=True,
            ),
            id="object-count-list",
        ),
        pytest.param(
            __import__("types").SimpleNamespace(
                count=3,
                term_type={"value": "fixed"},
                continuous=True,
            ),
            id="object-term-type-dict",
        ),
        pytest.param(
            __import__("types").SimpleNamespace(
                count=3,
                term_type="fixed",
                continuous="false",
            ),
            id="object-continuous-string",
        ),
    ],
)
def test_builder_rejects_invalid_contract_sequence_field_types(sequence):
    """
    Builder 必须拒绝非法的 ContractSequence 原始字段类型。

    不允许：
    1. 将错误类型静默转换成合法类型。
    2. 将非法的嵌套可变对象写入 StructuredAnswer。
    """
    decision = make_decision()
    decision.contract_sequence = sequence

    with pytest.raises(ValueError):
        build_structured_answer(decision)


def test_builder_rejects_boolean_contract_sequence_count():
    """
    Python 中 bool 是 int 的子类。

    count=True 不能作为合法合同次数通过 Builder 校验。
    """
    decision = make_decision()
    decision.contract_sequence = {
        "count": True,
        "term_type": "fixed",
        "continuous": True,
    }

    with pytest.raises(ValueError):
        build_structured_answer(decision)


# RUNTIME_RULE_DEFINITION_TYPE_REGRESSION_TESTS
# ============================================================
# Runtime Rule.condition_definitions.condition_type 原始类型校验
# ============================================================

@pytest.mark.parametrize(
    "invalid_type",
    [
        pytest.param([], id="list"),
        pytest.param({}, id="dict"),
        pytest.param(123, id="integer"),
    ],
)
def test_runtime_definition_rejects_non_string_condition_type_strict(
    invalid_type,
):
    """
    Runtime Rule 定义中的 condition_type 必须是字符串。

    strict=True：
        列表、字典、整数等非法类型统一抛出 ValueError。
    """
    decision = make_decision()

    definition = decision.selected_rule["condition_definitions"][0]
    definition["condition_type"] = invalid_type

    with pytest.raises(ValueError):
        validate_condition_structure(
            decision,
            strict=True,
        )


@pytest.mark.parametrize(
    "invalid_type",
    [
        pytest.param([], id="list"),
        pytest.param({}, id="dict"),
        pytest.param(123, id="integer"),
    ],
)
def test_runtime_definition_reports_non_string_condition_type_non_strict(
    invalid_type,
):
    """
    Runtime Rule 定义中的非法 condition_type 在非严格模式下
    必须返回 valid=False 和诊断信息。
    """
    decision = make_decision()

    definition = decision.selected_rule["condition_definitions"][0]
    definition["condition_type"] = invalid_type

    result = validate_condition_structure(
        decision,
        strict=False,
    )

    assert result["valid"] is False
    assert result["errors"]


def test_runtime_definition_accepts_all_canonical_condition_types():
    """
    Runtime Rule 的三种规范 condition_type 必须正常通过校验。
    """
    decision = make_decision()

    result = validate_condition_structure(
        decision,
        strict=True,
    )

    assert result["valid"] is True
    assert result["errors"] == []
