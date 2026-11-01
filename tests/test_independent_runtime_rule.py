# -*- coding: utf-8 -*-

"""
独立 Runtime Rule 执行回归测试。

目的：
1. 使用自定义 Condition ID 和 Relationship ID。
2. 不读取 Canonical Rule Registry。
3. 不使用 Article 14 专属 Condition ID。
4. 验证 SATISFIED → DEFINITE。
5. 验证未知事实 → CONDITIONAL。
"""

import pytest

from src.legal_decision_engine import evaluate_rule
from src.legal_fact_models import ContractSequence, LegalFacts


def build_independent_rule():
    return {
        "rule_id": "TEST-INDEPENDENT-RULE-001",
        "law_name": "Independent Test Law",
        "article_number": "Test Article",
        "rule_name": "Independent Runtime Rule",
        "conditions": ["合同数量至少为两次"],
        "exclusion_conditions": [],
        "exceptions": [],
        "condition_definitions": [
            {
                "condition_id": "TEST-REQUIRED-001",
                "condition": "合同数量至少为两次",
                "condition_type": "REQUIRED",
            }
        ],
        "fact_condition_relationships": [
            {
                "relationship_id": "TEST-REL-001",
                "condition_id": "TEST-REQUIRED-001",
                "relationship_type": "PROVES_TRUE",
                "result_status": "SATISFIED",
                "reason": "合同数量达到测试阈值。",
                "predicate_groups": [
                    {
                        "match": "ALL",
                        "predicates": [
                            {
                                "fact_key": "contract_sequence.count",
                                "operator": ">=",
                                "value": 2,
                            }
                        ],
                    }
                ],
            }
        ],
    }


def test_custom_condition_id_can_execute_without_article14_registry():
    rule = build_independent_rule()

    facts = LegalFacts(
        contract_sequence=ContractSequence(
            count=2,
            term_type="fixed",
            continuous=True,
        )
    )

    decision, results = evaluate_rule(facts=facts, rule=rule)

    assert decision == "DEFINITE"
    assert len(results) == 1
    assert results[0].condition_id == "TEST-REQUIRED-001"
    assert results[0].condition_type == "REQUIRED"
    assert results[0].status == "SATISFIED"


def test_custom_condition_id_keeps_unknown_fact_conditional():
    rule = build_independent_rule()
    facts = LegalFacts()

    decision, results = evaluate_rule(facts=facts, rule=rule)

    assert decision == "CONDITIONAL"
    assert len(results) == 1
    assert results[0].condition_id == "TEST-REQUIRED-001"
    assert results[0].status == "UNKNOWN"


def test_independent_rule_contains_no_article14_condition_ids():
    rule = build_independent_rule()

    condition_ids = {
        item["condition_id"]
        for item in rule["condition_definitions"]
    }
    relationship_ids = {
        item["relationship_id"]
        for item in rule["fact_condition_relationships"]
    }

    assert condition_ids == {"TEST-REQUIRED-001"}
    assert relationship_ids == {"TEST-REL-001"}
    assert not any(
        "ARTICLE-14" in item
        for item in condition_ids | relationship_ids
    )


if __name__ == "__main__":
    raise SystemExit(
        pytest.main(["-q", __file__])
    )
