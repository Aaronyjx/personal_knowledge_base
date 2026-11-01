# -*- coding: utf-8 -*-
"""LegalFacts 运行时类型边界回归测试。

第一阶段：先建立预期契约，再实现生产校验器。
允许 Optional 字段为 None；非法类型不得静默转换为 UNKNOWN。
"""

from runpy import run_path

import pytest

import src.legal_fact_models as fact_models
from src.legal_decision_engine import evaluate_rule
from src.legal_fact_models import ContractSequence, LegalFacts


def build_rule():
    """复用项目现有的独立 Runtime Rule 测试夹具。"""
    module = run_path("tests/test_independent_runtime_rule.py")
    return module["build_independent_rule"]()


def get_validator():
    """获取计划由事实模型模块提供的统一校验函数。"""
    validator = getattr(
        fact_models,
        "validate_legal_facts_runtime",
        None,
    )
    assert callable(validator), (
        "缺少 validate_legal_facts_runtime(facts) 统一事实类型校验器。"
    )
    return validator


def valid_sequence():
    return ContractSequence(
        count=3,
        term_type="fixed",
        continuous=True,
    )


def test_runtime_validator_accepts_valid_facts_and_optional_none():
    """合法事实与 Optional 字段的 None 必须被接受。"""
    facts = LegalFacts(
        explicit_facts=["用户明确表示签订过三次合同"],
        contract_sequence=None,
        completed_renewal=None,
        worker_agreement=None,
        article_39=None,
        article_40_1=None,
        article_40_2=None,
        fixed_term_exception=None,
    )

    get_validator()(facts)


@pytest.mark.parametrize(
    "field_name",
    [
        "completed_renewal",
        "worker_agreement",
        "article_39",
        "article_40_1",
        "article_40_2",
        "fixed_term_exception",
    ],
)
@pytest.mark.parametrize("invalid_value", ["yes", 1, 0])
def test_runtime_validator_rejects_invalid_optional_bool_types(
    field_name,
    invalid_value,
):
    """Optional[bool] 不能接受字符串或整数，包括 0 和 1。"""
    facts = LegalFacts()
    setattr(facts, field_name, invalid_value)

    with pytest.raises(TypeError, match=field_name):
        get_validator()(facts)


@pytest.mark.parametrize(
    "invalid_value",
    [
        "不是列表",
        {"事实": "内容"},
        ["合法字符串", 123],
        ["合法字符串", None],
    ],
)
def test_runtime_validator_rejects_invalid_explicit_facts(invalid_value):
    """explicit_facts 必须是字符串列表，不能只检查外层容器。"""
    facts = LegalFacts()
    facts.explicit_facts = invalid_value

    with pytest.raises(TypeError, match="explicit_facts"):
        get_validator()(facts)


@pytest.mark.parametrize(
    "invalid_value",
    [
        {},
        object(),
        "错误的合同序列",
        3,
    ],
)
def test_runtime_validator_rejects_invalid_contract_sequence_objects(
    invalid_value,
):
    """contract_sequence 只允许 None 或 ContractSequence 实例。"""
    facts = LegalFacts()
    facts.contract_sequence = invalid_value

    with pytest.raises(TypeError, match="contract_sequence"):
        get_validator()(facts)


@pytest.mark.parametrize(
    ("field_name", "invalid_value"),
    [
        ("count", "3"),
        ("count", 3.0),
        ("count", True),
        ("term_type", None),
        ("term_type", 123),
        ("continuous", "true"),
        ("continuous", 1),
    ],
)
def test_runtime_validator_rejects_mutated_nested_sequence_fields(
    field_name,
    invalid_value,
):
    """嵌套对象创建后被污染，也必须在运行时校验时被拒绝。"""
    facts = LegalFacts(contract_sequence=valid_sequence())
    setattr(facts.contract_sequence, field_name, invalid_value)

    with pytest.raises(TypeError, match=field_name):
        get_validator()(facts)


def test_runtime_validator_rejects_non_legal_facts_object():
    """校验器不能接受其他对象冒充 LegalFacts。"""
    with pytest.raises(TypeError, match="LegalFacts"):
        get_validator()(object())


def test_evaluate_rule_rejects_mutated_boolean_fact_type():
    """直接调用 evaluate_rule 时，非法布尔事实不能静默成为 UNKNOWN。"""
    facts = LegalFacts()
    facts.worker_agreement = "yes"

    rule = build_rule()
    predicate = rule["fact_condition_relationships"][0][
        "predicate_groups"
    ][0]["predicates"][0]
    predicate["fact_key"] = "worker_agreement"
    predicate["operator"] = "=="
    predicate["value"] = True

    with pytest.raises(TypeError, match="worker_agreement"):
        evaluate_rule(facts=facts, rule=rule)


def test_evaluate_rule_rejects_mutated_nested_object_type():
    """直接调用 evaluate_rule 时，错误嵌套对象必须被入口拒绝。"""
    facts = LegalFacts()
    facts.contract_sequence = object()

    with pytest.raises(TypeError, match="contract_sequence"):
        evaluate_rule(facts=facts, rule=build_rule())


def test_evaluate_rule_rejects_string_count_before_comparison():
    """非法 count 必须在 Predicate 比较前被拒绝，并指出字段位置。"""
    facts = LegalFacts(contract_sequence=valid_sequence())
    facts.contract_sequence.count = "3"

    with pytest.raises(TypeError, match="count"):
        evaluate_rule(facts=facts, rule=build_rule())


def test_evaluate_rule_preserves_unknown_for_valid_none_nested_fact():
    """合法 None 仍然表示事实未知，而不是类型错误。"""
    facts = LegalFacts(contract_sequence=None)

    decision, results = evaluate_rule(
        facts=facts,
        rule=build_rule(),
    )

    assert decision == "CONDITIONAL"
    assert len(results) == 1
    assert results[0].status == "UNKNOWN"


def test_evaluate_rule_rejects_invalid_facts_before_matching(monkeypatch):
    """事实类型校验失败时，不得调用 match_condition。"""
    import src.legal_decision_engine as engine

    facts = LegalFacts()
    facts.worker_agreement = "yes"
    rule = build_rule()

    def forbidden_match_condition(**kwargs):
        raise AssertionError(
            "事实类型校验失败后，不应调用 match_condition()"
        )

    monkeypatch.setattr(
        engine,
        "match_condition",
        forbidden_match_condition,
    )

    with pytest.raises(TypeError, match="worker_agreement"):
        engine.evaluate_rule(
            facts=facts,
            rule=rule,
        )


def test_make_decision_rejects_invalid_extracted_facts_before_rule_execution(
    monkeypatch,
):
    """事实提取结果不合法时，不得继续执行规则。"""
    import src.legal_decision_engine as engine

    facts = LegalFacts()
    facts.explicit_facts = "不是字符串列表"

    monkeypatch.setattr(
        engine,
        "extract_legal_facts",
        lambda question: facts,
    )

    def forbidden_evaluate_rule(**kwargs):
        raise AssertionError(
            "事实校验失败后，不应调用 evaluate_rule()"
        )

    monkeypatch.setattr(
        engine,
        "evaluate_rule",
        forbidden_evaluate_rule,
    )

    with pytest.raises(TypeError, match="explicit_facts"):
        engine.make_decision(
            question="测试事实校验边界",
            rule=build_rule(),
        )
