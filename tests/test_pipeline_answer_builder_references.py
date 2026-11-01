from copy import deepcopy

from src.legal_rule_definition import RULE_ID
from src.legal_rule_registry import get_rule
from src.legal_runtime_rule_adapter import canonical_rule_to_runtime_rule
from src.legal_decision_engine import (
    ConditionResult,
    DecisionResult,
    UNKNOWN,
)
from src.legal_pipeline import run_answer_builder


def build_article_14_decision():
    """
    使用真实 Article 14 Canonical Rule 构造合法 DecisionResult。
    不启动 Retriever、Embedding 或 LLM。
    """

    canonical_rule = get_rule(RULE_ID)

    assert canonical_rule is not None

    runtime_rule = canonical_rule_to_runtime_rule(
        canonical_rule
    )

    condition_results = []

    for definition in runtime_rule["condition_definitions"]:
        condition_results.append(
            ConditionResult(
                condition_id=definition["condition_id"],
                condition=definition["condition"],
                status=UNKNOWN,
                reason="测试夹具：条件事实尚未提供",
                condition_type=definition["condition_type"],
            )
        )

    decision = DecisionResult(
        decision="CONDITIONAL",
        condition_results=condition_results,
        explicit_facts=[],
        contract_sequence=None,
        rule_dependencies=[],
        selected_rule=runtime_rule,
        selected_rule_id=runtime_rule["rule_id"],
        explanation="Answer Builder 结构化引用回归测试",
    )

    return decision, deepcopy(canonical_rule["references"])


def build_answer():
    decision, canonical_references = build_article_14_decision()

    answer = run_answer_builder(
        decision=decision,
        rules=[],
        question="公司连续签订三次固定期限劳动合同后，是否必须签订无固定期限劳动合同？",
    )

    return decision, answer, canonical_references


def test_run_answer_builder_preserves_article_14_references():
    """
    验证真实 Pipeline Answer Builder 输出完整保留四条结构化引用。
    """

    _, answer, canonical_references = build_answer()

    selected_rule = answer["selected_rule"]

    assert selected_rule["rule_id"] == RULE_ID
    assert selected_rule["references"] == canonical_references

    references = selected_rule["references"]

    assert len(references) == 4

    assert [item["reference_type"] for item in references] == [
        "PRIMARY",
        "EXCLUSION",
        "EXCLUSION",
        "EXCLUSION",
    ]

    article_40_references = [
        item
        for item in references
        if item["article_id"]
        == "561177d9-231b-5031-b894-f0f0a0a56256"
    ]

    assert len(article_40_references) == 2

    assert [
        item["location"]["item_number"]
        for item in article_40_references
    ] == [1, 2]


def test_run_answer_builder_preserves_nested_reference_isolation():
    """
    验证修改 Builder 输出中的嵌套 location，
    不会反向修改 Engine DecisionResult 中的引用。
    """

    decision, answer, canonical_references = build_answer()

    original_references = deepcopy(
        decision.selected_rule["references"]
    )

    output_references = answer["selected_rule"]["references"]

    output_references[2]["location"]["item_number"] = 99

    assert (
        decision.selected_rule["references"]
        == original_references
    )

    assert (
        decision.selected_rule["references"]
        == canonical_references
    )

    assert (
        output_references[2]["location"]["item_number"]
        == 99
    )
