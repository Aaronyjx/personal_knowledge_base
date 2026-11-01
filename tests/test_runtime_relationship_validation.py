# -*- coding: utf-8 -*-

"""
RAG V7 Runtime Rule Relationship Validation Boundary Tests

本测试只验证 Runtime Rule 的通用结构边界，
不修改 Canonical Rule、Registry 或生产代码。
"""

from copy import deepcopy

import pytest

from src.legal_decision_engine import evaluate_rule

from runpy import run_path

_test_module = run_path(
    "tests/test_runtime_rule_execution.py"
)

build_test_rule = _test_module["build_test_rule"]
build_satisfied_facts = _test_module["build_satisfied_facts"]
build_unknown_facts = _test_module["build_unknown_facts"]


def _evaluate(rule):
    return evaluate_rule(
        facts=build_satisfied_facts(),
        rule=rule,
    )


def test_valid_runtime_rule_still_executes():
    rule = build_test_rule()

    decision, results = evaluate_rule(
        facts=build_satisfied_facts(),
        rule=rule,
    )

    assert decision == "DEFINITE"
    assert len(results) == 1
    assert results[0].status == "SATISFIED"


def test_unknown_runtime_rule_still_returns_conditional():
    rule = build_test_rule()

    decision, results = evaluate_rule(
        facts=build_unknown_facts(),
        rule=rule,
    )

    assert decision == "CONDITIONAL"
    assert len(results) == 1
    assert results[0].status == "UNKNOWN"


def test_rejects_non_dict_relationship():
    rule = build_test_rule()
    rule["fact_condition_relationships"].append(
        "INVALID_RELATIONSHIP"
    )

    with pytest.raises(ValueError):
        _evaluate(rule)


def test_rejects_relationship_for_unknown_condition_id():
    rule = build_test_rule()

    relationship = deepcopy(
        rule["fact_condition_relationships"][0]
    )
    relationship["relationship_id"] = (
        "TEST-REL-UNKNOWN-CONDITION"
    )
    relationship["condition_id"] = "UNKNOWN-CONDITION-ID"

    rule["fact_condition_relationships"].append(
        relationship
    )

    with pytest.raises(ValueError):
        _evaluate(rule)


def test_rejects_duplicate_relationship_id():
    rule = build_test_rule()

    duplicate = deepcopy(
        rule["fact_condition_relationships"][0]
    )
    rule["fact_condition_relationships"].append(
        duplicate
    )

    with pytest.raises(ValueError):
        _evaluate(rule)


def test_rejects_inconsistent_relationship_type_and_status():
    rule = build_test_rule()

    rule["fact_condition_relationships"][0].update({
        "relationship_type": "PROVES_TRUE",
        "result_status": "UNKNOWN",
    })

    with pytest.raises(ValueError):
        _evaluate(rule)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda rule: rule["fact_condition_relationships"][0].update(
            {"predicate_groups": "INVALID"}
        ),
        lambda rule: rule["fact_condition_relationships"][0].update(
            {"predicate_groups": []}
        ),
        lambda rule: rule["fact_condition_relationships"][0].update(
            {"predicate_groups": ["INVALID_GROUP"]}
        ),
        lambda rule: rule["fact_condition_relationships"][0][
            "predicate_groups"
        ][0].update({"match": "ANY"}),
        lambda rule: rule["fact_condition_relationships"][0][
            "predicate_groups"
        ][0].update({"predicates": "INVALID"}),
        lambda rule: rule["fact_condition_relationships"][0][
            "predicate_groups"
        ][0].update({"predicates": []}),
        lambda rule: rule["fact_condition_relationships"][0][
            "predicate_groups"
        ][0].update({"predicates": ["INVALID_PREDICATE"]}),
        lambda rule: rule["fact_condition_relationships"][0][
            "predicate_groups"
        ][0]["predicates"][0].update({"fact_key": ""}),
        lambda rule: rule["fact_condition_relationships"][0][
            "predicate_groups"
        ][0]["predicates"][0].update({"operator": "INVALID"}),
        lambda rule: rule["fact_condition_relationships"][0][
            "predicate_groups"
        ][0]["predicates"][0].update({"value": None}),
        lambda rule: rule["fact_condition_relationships"][0][
            "predicate_groups"
        ][0]["predicates"][0].update(
            {"operator": ">=", "value": True}
        ),
    ],
    ids=[
        "predicate-groups-not-list",
        "predicate-groups-empty",
        "group-not-dict",
        "invalid-match-mode",
        "predicates-not-list",
        "predicates-empty",
        "predicate-not-dict",
        "empty-fact-key",
        "invalid-operator",
        "invalid-equality-value",
        "boolean-is-not-integer-for-greater-equal",
    ],
)
def test_rejects_invalid_predicate_structure(mutate):
    rule = build_test_rule()
    mutate(rule)

    with pytest.raises(ValueError):
        _evaluate(rule)


@pytest.mark.parametrize(
    "field, mutation",
    [
        (
            "condition_definitions",
            "missing",
        ),
        (
            "condition_definitions",
            "empty",
        ),
        (
            "fact_condition_relationships",
            "missing",
        ),
        (
            "fact_condition_relationships",
            "empty",
        ),
    ],
    ids=[
        "missing-condition-definitions",
        "empty-condition-definitions",
        "missing-relationships",
        "empty-relationships",
    ],
)
def test_rejects_missing_or_empty_runtime_collections(field, mutation):
    rule = build_test_rule()

    if mutation == "missing":
        rule.pop(field)
    else:
        rule[field] = []

    with pytest.raises(ValueError):
        _evaluate(rule)


def test_multiple_relationships_can_cover_same_condition():
    """
    同一条件可以由多条 Relationship 覆盖。
    只要结构合法且至少一条关系匹配，规则应正常执行。
    """
    rule = build_test_rule()

    second = deepcopy(rule["fact_condition_relationships"][0])
    second["relationship_id"] = "TEST-REL-SECOND"
    rule["fact_condition_relationships"].append(second)

    decision, results = evaluate_rule(
        facts=build_satisfied_facts(),
        rule=rule,
    )

    assert decision == "DEFINITE"
    assert len(results) == 1
    assert results[0].status == "SATISFIED"


@pytest.mark.parametrize(
    ("field", "invalid_value", "error_match"),
    [
        ("condition_id", 123, "condition_id"),
        ("condition", None, "condition"),
        ("condition_type", None, "condition_type"),
    ],
    ids=[
        "integer-condition-id",
        "none-condition",
        "none-condition-type",
    ],
)
def test_rejects_invalid_condition_definition_field_types_before_matching(
    monkeypatch,
    field,
    invalid_value,
    error_match,
):
    """
    条件定义字段必须满足严格类型契约，
    不得通过 str() 转换掩盖非法输入。
    """
    import src.legal_decision_engine as engine

    rule = build_test_rule()
    rule["condition_definitions"][0][field] = invalid_value

    def forbidden_match_condition(**kwargs):
        raise AssertionError(
            "条件定义结构校验失败前不应调用 match_condition()"
        )

    monkeypatch.setattr(
        engine,
        "match_condition",
        forbidden_match_condition,
    )

    with pytest.raises(ValueError, match=error_match):
        evaluate_rule(
            facts=build_satisfied_facts(),
            rule=rule,
        )


def test_invalid_runtime_rule_is_rejected_before_fact_matching(monkeypatch):
    """
    非法 Predicate 必须在 match_condition 被调用前拒绝。
    即使输入事实满足原有条件，也不能绕过结构校验。
    """
    import src.legal_decision_engine as engine

    rule = build_test_rule()
    rule["fact_condition_relationships"][0][
        "predicate_groups"
    ][0]["predicates"][0]["operator"] = "INVALID"

    def forbidden_match_condition(**kwargs):
        raise AssertionError(
            "结构校验失败前不应调用 match_condition()"
        )

    monkeypatch.setattr(
        engine,
        "match_condition",
        forbidden_match_condition,
    )

    with pytest.raises(ValueError, match="operator"):
        evaluate_rule(
            facts=build_satisfied_facts(),
            rule=rule,
        )




@pytest.mark.parametrize(
    ("definitive_type", "definitive_status", "expected_decision"),
    [
        ("PROVES_TRUE", "SATISFIED", "DEFINITE"),
        ("PROVES_FALSE", "NOT_SATISFIED", "NOT_ESTABLISHED"),
    ],
    ids=["satisfied", "not_satisfied"],
)
@pytest.mark.parametrize(
    "reverse_relationships",
    [False, True],
    ids=[
        "definitive_then_unknown",
        "unknown_then_definitive",
    ],
)
def test_unknown_does_not_override_definitive_result(
    definitive_type,
    definitive_status,
    expected_decision,
    reverse_relationships,
):
    """
    UNKNOWN 不构成反向证据。

    两种确定性结论都必须与 Relationship 顺序无关：
        SATISFIED + UNKNOWN -> SATISFIED
        UNKNOWN + SATISFIED -> SATISFIED
        NOT_SATISFIED + UNKNOWN -> NOT_SATISFIED
        UNKNOWN + NOT_SATISFIED -> NOT_SATISFIED
    """
    rule = build_test_rule()

    definitive_relationship = deepcopy(
        rule["fact_condition_relationships"][0]
    )
    definitive_relationship["relationship_id"] = (
        "TEST-REL-DEFINITIVE"
    )
    definitive_relationship["relationship_type"] = definitive_type
    definitive_relationship["result_status"] = definitive_status

    unknown_relationship = deepcopy(
        definitive_relationship
    )
    unknown_relationship["relationship_id"] = (
        "TEST-REL-UNKNOWN"
    )
    unknown_relationship["relationship_type"] = "DOES_NOT_PROVE"
    unknown_relationship["result_status"] = "UNKNOWN"

    relationships = [
        definitive_relationship,
        unknown_relationship,
    ]

    if reverse_relationships:
        relationships.reverse()

    rule["fact_condition_relationships"] = relationships

    decision, results = evaluate_rule(
        facts=build_satisfied_facts(),
        rule=rule,
    )

    assert decision == expected_decision
    assert len(results) == 1
    assert results[0].status == definitive_status




@pytest.mark.parametrize(
    "reverse_relationships",
    [False, True],
    ids=["true-then-false", "false-then-true"],
)
def test_conflicting_matching_relationships_are_rejected_in_any_order(
    reverse_relationships,
):
    """同一条件的确定结论冲突必须与 Relationship 顺序无关。"""
    rule = build_test_rule()

    satisfied_relationship = deepcopy(
        rule["fact_condition_relationships"][0]
    )
    satisfied_relationship["relationship_id"] = "TEST-REL-TRUE"
    satisfied_relationship["relationship_type"] = "PROVES_TRUE"
    satisfied_relationship["result_status"] = "SATISFIED"

    rejected_relationship = deepcopy(
        satisfied_relationship
    )
    rejected_relationship["relationship_id"] = "TEST-REL-FALSE"
    rejected_relationship["relationship_type"] = "PROVES_FALSE"
    rejected_relationship["result_status"] = "NOT_SATISFIED"

    relationships = [
        satisfied_relationship,
        rejected_relationship,
    ]

    if reverse_relationships:
        relationships.reverse()

    rule["fact_condition_relationships"] = relationships

    with pytest.raises(ValueError, match="冲突"):
        evaluate_rule(
            facts=build_satisfied_facts(),
            rule=rule,
        )



@pytest.mark.parametrize(
    "unknown_first",
    [False, True],
    ids=["definitive-first", "unknown-first"],
)
def test_definitive_relationship_reason_is_independent_of_unknown_order(
    unknown_first,
):
    """UNKNOWN 不应覆盖确定性结果及其解释。"""
    rule = build_test_rule()

    definitive = deepcopy(
        rule["fact_condition_relationships"][0]
    )
    definitive["relationship_id"] = "TEST-REL-DEFINITIVE"
    definitive["relationship_type"] = "PROVES_TRUE"
    definitive["result_status"] = "SATISFIED"
    definitive["reason"] = "确定性关系的测试解释"

    unknown = deepcopy(definitive)
    unknown["relationship_id"] = "TEST-REL-UNKNOWN"
    unknown["relationship_type"] = "DOES_NOT_PROVE"
    unknown["result_status"] = "UNKNOWN"
    unknown["reason"] = "UNKNOWN 关系的测试解释"

    relationships = [definitive, unknown]
    if unknown_first:
        relationships.reverse()

    rule["fact_condition_relationships"] = relationships

    decision, results = evaluate_rule(
        facts=build_satisfied_facts(),
        rule=rule,
    )

    assert decision == "DEFINITE"
    assert len(results) == 1
    assert results[0].status == "SATISFIED"
    assert results[0].reason == "确定性关系的测试解释"


def test_first_matching_definitive_reason_is_preserved():
    """多条同状态确定性关系命中时，使用第一条确定性解释。"""
    rule = build_test_rule()

    first = deepcopy(
        rule["fact_condition_relationships"][0]
    )
    first["relationship_id"] = "TEST-REL-FIRST"
    first["relationship_type"] = "PROVES_TRUE"
    first["result_status"] = "SATISFIED"
    first["reason"] = "第一条确定性解释"

    second = deepcopy(first)
    second["relationship_id"] = "TEST-REL-SECOND"
    second["reason"] = "第二条确定性解释"

    rule["fact_condition_relationships"] = [first, second]

    decision, results = evaluate_rule(
        facts=build_satisfied_facts(),
        rule=rule,
    )

    assert decision == "DEFINITE"
    assert len(results) == 1
    assert results[0].status == "SATISFIED"
    assert results[0].reason == "第一条确定性解释"

def test_conflicting_matching_relationships_are_rejected():
    """
    同一条件的多个 Relationship 同时命中，
    如果映射到相互矛盾的状态，执行器必须拒绝静默选择。
    """
    rule = build_test_rule()

    satisfied_relationship = deepcopy(
        rule["fact_condition_relationships"][0]
    )
    satisfied_relationship["relationship_id"] = "TEST-REL-TRUE"
    satisfied_relationship["relationship_type"] = "PROVES_TRUE"
    satisfied_relationship["result_status"] = "SATISFIED"

    rejected_relationship = deepcopy(
        satisfied_relationship
    )
    rejected_relationship["relationship_id"] = "TEST-REL-FALSE"
    rejected_relationship["relationship_type"] = "PROVES_FALSE"
    rejected_relationship["result_status"] = "NOT_SATISFIED"

    # 使用相同谓词，确保两条 Relationship 同时命中。
    rule["fact_condition_relationships"] = [
        satisfied_relationship,
        rejected_relationship,
    ]

    with pytest.raises(ValueError, match="冲突"):
        evaluate_rule(
            facts=build_satisfied_facts(),
            rule=rule,
        )


@pytest.mark.parametrize(
    ("reason_present", "reason_value"),
    [
        (False, None),
        (True, ""),
        (True, "   "),
        (True, None),
        (True, 123),
    ],
    ids=[
        "missing-reason",
        "empty-reason",
        "whitespace-reason",
        "none-reason",
        "non-string-reason",
    ],
)
def test_runtime_relationship_rejects_invalid_reason(
    reason_present,
    reason_value,
):
    """Runtime Relationship 的 reason 必须是非空字符串。"""
    rule = build_test_rule()
    relationship = rule["fact_condition_relationships"][0]

    if reason_present:
        relationship["reason"] = reason_value
    else:
        relationship.pop("reason", None)

    with pytest.raises(ValueError, match="reason"):
        _evaluate(rule)


def test_runtime_relationship_accepts_nonempty_reason():
    """Runtime Relationship 的合法非空 reason 应允许规则执行。"""
    rule = build_test_rule()
    relationship = rule["fact_condition_relationships"][0]
    relationship["reason"] = "该关系具有明确的事实判断依据"

    decision, results = evaluate_rule(
        facts=build_satisfied_facts(),
        rule=rule,
    )

    assert decision == "DEFINITE"
    assert len(results) == 1
    assert results[0].status == "SATISFIED"


def test_rejects_nonexistent_fact_path_before_fact_matching(monkeypatch):
    """
    不存在的 fact_key 必须在事实匹配前被拒绝，
    不能被当作事实不满足或 UNKNOWN。
    """
    import src.legal_decision_engine as engine

    rule = build_test_rule()
    predicate = rule["fact_condition_relationships"][0][
        "predicate_groups"
    ][0]["predicates"][0]
    predicate["fact_key"] = "contract_sequence.cout"

    def forbidden_match_condition(**kwargs):
        raise AssertionError(
            "非法 fact_key 必须在调用 match_condition() 前被拒绝"
        )

    monkeypatch.setattr(
        engine,
        "match_condition",
        forbidden_match_condition,
    )

    with pytest.raises(ValueError, match="fact_key|字段|路径"):
        evaluate_rule(
            facts=build_satisfied_facts(),
            rule=rule,
        )


def test_none_nested_fact_object_keeps_valid_path_unknown():
    """
    contract_sequence 是合法字段，即使当前值为 None，
    contract_sequence.count 仍是合法路径。
    这种情况应保留未知事实语义。
    """
    from src.legal_fact_models import LegalFacts

    rule = build_test_rule()
    facts = LegalFacts(contract_sequence=None)

    decision, results = evaluate_rule(
        facts=facts,
        rule=rule,
    )

    assert decision == "CONDITIONAL"
    assert len(results) == 1
    assert results[0].status == "UNKNOWN"
def test_rejects_fact_key_with_surrounding_whitespace(monkeypatch):
    """
    fact_key 前后带空格必须在事实匹配前被拒绝，
    不得只在校验时 strip、执行时却读取原始路径。
    """
    import src.legal_decision_engine as engine

    rule = build_test_rule()
    predicate = rule["fact_condition_relationships"][0][
        "predicate_groups"
    ][0]["predicates"][0]
    predicate["fact_key"] = " worker_agreement "

    def forbidden_match_condition(**kwargs):
        raise AssertionError(
            "带空格的 fact_key 必须在调用 match_condition() 前被拒绝"
        )

    monkeypatch.setattr(
        engine,
        "match_condition",
        forbidden_match_condition,
    )

    with pytest.raises(ValueError, match="fact_key|字段|路径"):
        evaluate_rule(
            facts=build_satisfied_facts(),
            rule=rule,
        )


def test_rejects_unrelated_dataclass_before_fact_matching(monkeypatch):
    """
    即使无关 dataclass 声明了合法的嵌套字段路径，
    也必须在 match_condition() 执行前拒绝。
    """
    from dataclasses import dataclass
    from src.legal_fact_models import ContractSequence
    import src.legal_decision_engine as engine

    @dataclass
    class UnrelatedFacts:
        contract_sequence: ContractSequence | None = None

    rule = build_test_rule()

    def forbidden_match_condition(**kwargs):
        raise AssertionError(
            "无关 dataclass 必须在调用 match_condition() 前被拒绝"
        )

    monkeypatch.setattr(
        engine,
        "match_condition",
        forbidden_match_condition,
    )

    with pytest.raises(ValueError, match="LegalFacts|事实模型|事实输入"):
        evaluate_rule(
            facts=UnrelatedFacts(),
            rule=rule,
        )
