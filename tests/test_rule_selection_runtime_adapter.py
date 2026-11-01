from __future__ import annotations

from typing import Any, Dict

from src.legal_decision_engine import (
    evaluate_rule,
    make_decision,
    select_core_rule,
)
from src.legal_fact_models import (
    ContractSequence,
    LegalFacts,
)
from src.legal_pipeline import (
    build_runtime_rule_from_retrieved_articles,
)

from src.legal_rule_registry import get_rule, register_rule
from src.legal_registry_models import ArticleLocation
from src.legal_rule_reference import create_rule_legal_reference
from src.legal_rule_selector import select_rule_from_article
from src.legal_runtime_rule_adapter import (
    canonical_rule_to_runtime_rule,
)


TEST_RULE_ID = "RULE-TEST-003"
TEST_LAW_NAME = "V6.2 Selector Adapter 测试法律"
TEST_ARTICLE = "第九十九条"


def register_test_rule() -> None:
    """
    注册一个非 Article 14 的临时 Canonical Rule。

    如果 Registry 中已经存在相同 rule_id，
    必须验证完整规则定义一致，不允许静默复用其他规则。
    """

    expected_rule = {
        "rule_id": TEST_RULE_ID,
        "law_name": TEST_LAW_NAME,
        "article_number": TEST_ARTICLE,
        "rule_name": "V6.2 Selector Adapter 测试规则",
        "conditions": [
            "测试必要条件",
        ],
        "exclusion_conditions": [
            "测试排除条件",
        ],
        "exceptions": [
            "测试例外条件",
        ],
        "condition_definitions": [
            {
                "condition_id": "TEST-003-REQUIRED-001",
                "condition": "测试必要条件",
                "condition_type": "REQUIRED",
            },
            {
                "condition_id": "TEST-003-EXCLUSION-001",
                "condition": "测试排除条件",
                "condition_type": "EXCLUSION",
            },
            {
                "condition_id": "TEST-003-EXCEPTION-001",
                "condition": "测试例外条件",
                "condition_type": "EXCEPTION",
            },
        ],
        "fact_condition_relationships": [
            {
                "relationship_id": "TEST-003-REL-REQUIRED-001-001",
                "condition_id": "TEST-003-REQUIRED-001",
                "predicate_groups": [
                    {
                        "match": "ALL",
                        "predicates": [
                            {
                                "fact_key": "worker_agreement",
                                "operator": "==",
                                "value": True,
                            }
                        ],
                    }
                ],
                "relationship_type": "PROVES_TRUE",
                "result_status": "SATISFIED",
                "reason": "测试事实可以证明测试必要条件。",
            },
            {
                "relationship_id": "TEST-003-REL-EXCLUSION-001-001",
                "condition_id": "TEST-003-EXCLUSION-001",
                "predicate_groups": [
                    {
                        "match": "ALL",
                        "predicates": [
                            {
                                "fact_key": "article_39",
                                "operator": "==",
                                "value": True,
                            }
                        ],
                    }
                ],
                "relationship_type": "PROVES_TRUE",
                "result_status": "SATISFIED",
                "reason": "测试事实可以证明测试排除条件。",
            },
            {
                "relationship_id": "TEST-003-REL-EXCEPTION-001-001",
                "condition_id": "TEST-003-EXCEPTION-001",
                "predicate_groups": [
                    {
                        "match": "ALL",
                        "predicates": [
                            {
                                "fact_key": "fixed_term_exception",
                                "operator": "==",
                                "value": True,
                            }
                        ],
                    }
                ],
                "relationship_type": "PROVES_TRUE",
                "result_status": "SATISFIED",
                "reason": "测试事实可以证明测试例外条件。",
            },
        ],
        "legal_obligations": [
            "测试义务",
        ],
        "legal_consequences": [
            "测试后果",
        ],
        "references": [
            create_rule_legal_reference(
                rule_id=TEST_RULE_ID,
                article_id="11111111-2222-4333-8444-555555555555",
                reference_type="PRIMARY",
                legal_role="测试规则主要法律依据",
                location=ArticleLocation(item_number=1),
            ).to_dict(),
        ],
    }

    try:
        existing_rule = get_rule(TEST_RULE_ID)

    except KeyError:
        register_rule(expected_rule)
        return

    if existing_rule != expected_rule:
        raise AssertionError(
            "Registry 中已存在与当前测试 fixture 不一致的规则："
            f"{TEST_RULE_ID}"
        )


def test_selector_returns_canonical_rule() -> None:
    """
    Production Selector 应返回 Canonical Rule。
    """

    register_test_rule()

    article = {
        "law_name": TEST_LAW_NAME,
        "article_number": TEST_ARTICLE,
        "title": TEST_ARTICLE,
    }

    canonical_rule = select_rule_from_article(article)

    assert canonical_rule is not None
    assert canonical_rule["rule_id"] == TEST_RULE_ID
    assert canonical_rule["law_name"] == TEST_LAW_NAME
    assert canonical_rule["article_number"] == TEST_ARTICLE


def test_selected_canonical_rule_converts_to_runtime_rule() -> None:
    """
    Production Selector 返回的 Canonical Rule
    应可以直接交给 Production Runtime Adapter。
    """

    register_test_rule()

    article = {
        "law_name": TEST_LAW_NAME,
        "article_number": TEST_ARTICLE,
        "title": TEST_ARTICLE,
    }

    canonical_rule = select_rule_from_article(article)

    assert canonical_rule is not None

    runtime_rule = canonical_rule_to_runtime_rule(
        canonical_rule
    )

    assert runtime_rule["rule_id"] == TEST_RULE_ID
    assert runtime_rule["law_name"] == TEST_LAW_NAME
    assert runtime_rule["article"] == TEST_ARTICLE

    assert runtime_rule["conditions"] == [
        "测试必要条件",
    ]

    assert runtime_rule["exclusion_conditions"] == [
        "测试排除条件",
    ]

    assert runtime_rule["exceptions"] == [
        "测试例外条件",
    ]

    assert len(runtime_rule["condition_definitions"]) == 3


def test_selector_adapter_chain_is_rule_agnostic() -> None:
    """
    Selector → Adapter 链路不能依赖 Article 14。

    本测试使用 Article 99 临时 Rule。
    """

    register_test_rule()

    article = {
        "law_name": TEST_LAW_NAME,
        "article_number": TEST_ARTICLE,
    }

    canonical_rule = select_rule_from_article(article)

    assert canonical_rule is not None
    assert canonical_rule["rule_id"] == TEST_RULE_ID

    runtime_rule = canonical_rule_to_runtime_rule(
        canonical_rule
    )

    assert runtime_rule["rule_id"] == TEST_RULE_ID
    assert runtime_rule["article"] == TEST_ARTICLE

    assert len(runtime_rule["conditions"]) == 1
    assert len(runtime_rule["exclusion_conditions"]) == 1
    assert len(runtime_rule["exceptions"]) == 1


def test_pipeline_production_rule_selection_uses_selector_and_adapter() -> None:
    """
    验证 V7 Pipeline Production Rule Selection Boundary。

    数据流：

        Retriever-like Article
                ↓
        build_runtime_rule_from_retrieved_articles()
                ↓
        Production Rule Selector
                ↓
        Canonical Rule
                ↓
        Runtime Rule Adapter
                ↓
        Runtime Rule

    本测试验证真正的 Production Pipeline Boundary。

    不通过 Decision Engine 的 legacy
    select_core_rule() 进行 Rule Selection。
    """

    register_test_rule()

    retrieved_articles = [
        {
            "law_name": TEST_LAW_NAME,
            "article_number": TEST_ARTICLE,
            "title": TEST_ARTICLE,
        }
    ]

    runtime_rule = build_runtime_rule_from_retrieved_articles(
        retrieved_articles
    )

    assert runtime_rule["rule_id"] == TEST_RULE_ID
    assert runtime_rule["law_name"] == TEST_LAW_NAME
    assert runtime_rule["article"] == TEST_ARTICLE

    assert runtime_rule["conditions"] == [
        "测试必要条件",
    ]

    assert runtime_rule["exclusion_conditions"] == [
        "测试排除条件",
    ]

    assert runtime_rule["exceptions"] == [
        "测试例外条件",
    ]

    assert len(runtime_rule["condition_definitions"]) == 3

    # --------------------------------------------------------
    # 验证 Pipeline 生产入口完整保留 Registry 结构化引用
    # --------------------------------------------------------

    canonical_rule = get_rule(TEST_RULE_ID)
    expected_references = canonical_rule["references"]

    # 引用内容必须完整一致。
    assert runtime_rule["references"] == expected_references

    # 验证引用关键字段没有丢失或改变。
    runtime_reference = runtime_rule["references"][0]
    canonical_reference = expected_references[0]

    assert runtime_reference["reference_id"] == canonical_reference["reference_id"]
    assert runtime_reference["rule_id"] == TEST_RULE_ID
    assert runtime_reference["article_id"] == canonical_reference["article_id"]
    assert runtime_reference["reference_type"] == "PRIMARY"
    assert runtime_reference["legal_role"] == "测试规则主要法律依据"
    assert runtime_reference["location"] == {
        "paragraph_number": None,
        "item_number": 1,
        "subitem_number": None,
    }

    # 列表、引用字典、嵌套 location 必须独立。
    assert runtime_rule["references"] is not canonical_rule["references"]
    assert runtime_reference is not canonical_reference
    assert runtime_reference["location"] is not canonical_reference["location"]

    # 修改 Runtime Rule，不得污染 Canonical Rule。
    runtime_reference["location"]["item_number"] = 99

    assert canonical_reference["location"]["item_number"] == 1

    # 重新读取 Registry，确认原始数据没有被污染。
    fresh_registry_rule = get_rule(TEST_RULE_ID)

    assert fresh_registry_rule["references"] == expected_references
    assert fresh_registry_rule["references"][0]["location"]["item_number"] == 1


def test_legacy_select_core_rule_uses_selector_and_adapter() -> None:
    """
    验证 Legacy Compatibility 的 select_core_rule()
    可以处理非 Article 14 的 Canonical Rule。

    数据流：

        Retriever-like Article
                ↓
        select_core_rule()
                ↓
        Production Selector
                ↓
        Canonical Rule
                ↓
        Runtime Rule Adapter
                ↓
        Runtime Rule

    本测试专门保留旧的 select_core_rule()
    兼容路径，防止 Legacy API 回归。

    V7 Production 已经改为：

        Retriever-like Article
                ↓
        build_runtime_rule_from_retrieved_articles()
                ↓
        Production Selector
                ↓
        Canonical Rule
                ↓
        Runtime Rule Adapter
                ↓
        Runtime Rule

    本测试不调用 Article 14 专用 build_core_rule()。
    """

    register_test_rule()

    retrieved_articles = [
        {
            "law_name": TEST_LAW_NAME,
            "article_number": TEST_ARTICLE,
            "title": TEST_ARTICLE,
        }
    ]

    runtime_rule = select_core_rule(
        retrieved_articles=retrieved_articles
    )

    assert runtime_rule["rule_id"] == TEST_RULE_ID
    assert runtime_rule["law_name"] == TEST_LAW_NAME
    assert runtime_rule["article"] == TEST_ARTICLE

    assert runtime_rule["conditions"] == [
        "测试必要条件",
    ]

    assert runtime_rule["exclusion_conditions"] == [
        "测试排除条件",
    ]

    assert runtime_rule["exceptions"] == [
        "测试例外条件",
    ]

    assert len(runtime_rule["condition_definitions"]) == 3



def test_legacy_selector_adapter_runtime_execution_chain() -> None:
    """
    验证 Legacy Compatibility 的完整 Selector → Adapter → Runtime Execution 链：

        Retriever-like Article
                ↓
        select_core_rule()
                ↓
        Canonical Rule
                ↓
        Runtime Rule Adapter
                ↓
        Runtime Rule
                ↓
        evaluate_rule()
                ↓
        Decision

    注意：

        临时 Rule 的 condition_id 使用现有
        ARTICLE-14-REQUIRED-001 Fact Matcher。

        本测试验证的是：

            Selector
                +
            Runtime Adapter
                +
            Runtime Execution

        不声称 Fact Matcher 已经 Rule-Agnostic。
    """

    register_test_rule()

    retrieved_articles = [
        {
            "law_name": TEST_LAW_NAME,
            "article_number": TEST_ARTICLE,
            "title": TEST_ARTICLE,
        }
    ]

    # --------------------------------------------------------
    # Legacy Compatibility Rule Selection
    # --------------------------------------------------------

    runtime_rule = select_core_rule(
        retrieved_articles=retrieved_articles
    )

    assert runtime_rule["rule_id"] == TEST_RULE_ID
    assert runtime_rule["article"] == TEST_ARTICLE

    # --------------------------------------------------------
    # 使用现有 Fact Matcher 的合法入口构造事实
    # --------------------------------------------------------

    facts = LegalFacts(
        contract_sequence=ContractSequence(
            count=2,
            term_type="fixed",
            continuous=True,
        )
    )

    # --------------------------------------------------------
    # Runtime Rule Execution
    # --------------------------------------------------------

    decision, condition_results = evaluate_rule(
        facts=facts,
        rule={
            **runtime_rule,
            "condition_definitions": [
                {
                    "condition_id": "ARTICLE-14-REQUIRED-001",
                    "condition": "测试必要条件",
                    "condition_type": "REQUIRED",
                }
            ],
            "fact_condition_relationships": [
                {
                    "relationship_id": "ARTICLE-14-REL-REQUIRED-001-TEST",
                    "condition_id": "ARTICLE-14-REQUIRED-001",
                    "predicate_groups": [
                        {
                            "match": "ALL",
                            "predicates": [
                                {
                                    "fact_key": "contract_sequence.count",
                                    "operator": ">=",
                                    "value": 2,
                                },
                                {
                                    "fact_key": "contract_sequence.term_type",
                                    "operator": "==",
                                    "value": "fixed",
                                },
                                {
                                    "fact_key": "contract_sequence.continuous",
                                    "operator": "==",
                                    "value": True,
                                },
                            ],
                        }
                    ],
                    "relationship_type": "PROVES_TRUE",
                    "result_status": "SATISFIED",
                    "reason": "测试事实满足 ARTICLE-14-REQUIRED-001。",
                }
            ],
        },
    )

    assert decision == "DEFINITE"

    assert len(condition_results) == 1

    result = condition_results[0]

    assert result.condition_id == (
        "ARTICLE-14-REQUIRED-001"
    )

    assert result.condition_type == "REQUIRED"
    assert result.status == "SATISFIED"



def test_selector_adapter_chain_preserves_isolation() -> None:
    """
    Selector 返回 Canonical Rule，
    Adapter 返回 Runtime Rule。

    修改 Runtime Rule 不得污染 Registry。
    """

    register_test_rule()

    article = {
        "law_name": TEST_LAW_NAME,
        "article_number": TEST_ARTICLE,
    }

    canonical_rule = select_rule_from_article(article)

    assert canonical_rule is not None

    runtime_rule = canonical_rule_to_runtime_rule(
        canonical_rule
    )

    runtime_rule["conditions"].append(
        "RUNTIME-ONLY-MUTATION"
    )

    runtime_rule["condition_definitions"].append(
        {
            "condition_id": "RUNTIME-ONLY-MUTATION",
            "condition": "Runtime Only Mutation",
            "condition_type": "REQUIRED",
        }
    )

    fresh_rule = get_rule(TEST_RULE_ID)

    assert "RUNTIME-ONLY-MUTATION" not in (
        fresh_rule["conditions"]
    )

    assert all(
        item["condition_id"] != "RUNTIME-ONLY-MUTATION"
        for item in fresh_rule["condition_definitions"]
    )



def test_legacy_make_decision_uses_selected_rule() -> None:
    """
    验证 Legacy make_decision 入口使用 Selector 选出的规则。

    不传入 rule，强制走 Legacy 兼容分支；
    通过自定义规则的 Condition ID 验证实际执行规则。
    """
    register_test_rule()

    question = "公司连续签订三次固定期限劳动合同。"

    retrieved_articles = [
        {
            "law_name": TEST_LAW_NAME,
            "article_number": TEST_ARTICLE,
            "title": TEST_ARTICLE,
        }
    ]

    # 故意不传 rule，验证 Legacy 兼容入口。
    decision = make_decision(
        question=question,
        retrieved_articles=retrieved_articles,
    )

    condition_results = getattr(
        decision,
        "condition_results",
        [],
    ) or []

    actual_condition_ids = [
        getattr(item, "condition_id", None)
        for item in condition_results
    ]

    expected_condition_ids = [
        "TEST-003-REQUIRED-001",
        "TEST-003-EXCLUSION-001",
        "TEST-003-EXCEPTION-001",
    ]

    assert actual_condition_ids == expected_condition_ids, (
        "Legacy make_decision 未执行预期的测试规则。"
        f" expected={expected_condition_ids!r},"
        f" actual={actual_condition_ids!r}"
    )

    print("  Decision:", getattr(decision, "decision", None))
    print("  Rule ID:", TEST_RULE_ID)
    print("  Condition IDs:", actual_condition_ids)

def main() -> None:
    print("=" * 70)
    print(
        "RAG V6.2 Rule Selection → Runtime Adapter Integration Test"
    )
    print("=" * 70)

    tests = [
        (
            test_selector_returns_canonical_rule,
            "Production Selector → Canonical Rule",
        ),
        (
            test_selected_canonical_rule_converts_to_runtime_rule,
            "Canonical Rule → Production Runtime Adapter",
        ),
        (
            test_selector_adapter_chain_is_rule_agnostic,
            "Selector → Adapter Rule-Agnostic",
        ),
        (
            test_selector_adapter_chain_preserves_isolation,
            "Selector → Adapter 隔离性",
        ),
        (
            test_pipeline_production_rule_selection_uses_selector_and_adapter,
            "Production select_core_rule → Selector → Adapter",
        ),
        (
            test_legacy_selector_adapter_runtime_execution_chain,
            "Production Selector → Adapter → Runtime Execution",
        ),
        (
            test_legacy_make_decision_uses_selected_rule,
            "Legacy make_decision → Selected Rule Runtime Execution",
        ),
        (
            test_legacy_select_core_rule_fails_without_matching_rule,
            "Legacy Selector → ValueError Without Matching Rule",
        ),
    ]

    for test, description in tests:
        test()
        print(f"PASS: {description}")

    print()
    print(
        "PASS: Rule Selection → Runtime Adapter Integration Test"
    )





def test_legacy_select_core_rule_fails_without_matching_rule() -> None:
    """
    验证没有匹配规则时显式失败，不得静默回退到 Article 14。
    """
    import pytest

    with pytest.raises(
        ValueError,
        match="Retriever Rules 中没有找到对应的 Canonical Rule",
    ):
        select_core_rule(retrieved_articles=[])


if __name__ == "__main__":
    main()


def test_selector_adapter_preserves_registry_structured_references() -> None:
    """
    验证 Selector → Registry → Adapter 的结构化引用完整性。

    检查：
        1. Candidate Article 的 references 不能覆盖 Registry。
        2. Selector 必须返回 Registry 中的完整结构化引用。
        3. Adapter 必须完整传递 references。
        4. Runtime Rule 的嵌套 location 必须独立于 Canonical Rule。
        5. 修改 Runtime Rule 不得污染 Registry。
    """

    register_test_rule()

    # 读取 Registry 中的权威引用。
    registry_rule = get_rule(TEST_RULE_ID)

    expected_references = registry_rule["references"]

    assert len(expected_references) == 1

    # Candidate Article 故意携带另一条合法但不同的引用。
    candidate_reference = create_rule_legal_reference(
        rule_id=TEST_RULE_ID,
        article_id="22222222-3333-4444-8555-666666666666",
        reference_type="RELATED",
        legal_role="Retriever Candidate 提供的非权威引用",
        location=ArticleLocation(item_number=2),
    ).to_dict()

    article = {
        "law_name": TEST_LAW_NAME,
        "article_number": TEST_ARTICLE,
        "references": [
            candidate_reference,
        ],
    }

    # --------------------------------------------------------
    # A. Selector 必须返回 Registry 中的引用
    # --------------------------------------------------------

    canonical_rule = select_rule_from_article(article)

    assert canonical_rule is not None
    assert canonical_rule["rule_id"] == TEST_RULE_ID

    assert canonical_rule["references"] == expected_references

    assert canonical_rule["references"] != article["references"]

    assert (
        canonical_rule["references"][0]["article_id"]
        == "11111111-2222-4333-8444-555555555555"
    )

    assert (
        canonical_rule["references"][0]["location"]["item_number"]
        == 1
    )

    # --------------------------------------------------------
    # B. Adapter 必须完整传递结构化引用
    # --------------------------------------------------------

    runtime_rule = canonical_rule_to_runtime_rule(
        canonical_rule
    )

    assert runtime_rule["references"] == expected_references

    assert runtime_rule["references"] is not canonical_rule["references"]

    assert (
        runtime_rule["references"][0]
        is not canonical_rule["references"][0]
    )

    assert (
        runtime_rule["references"][0]["location"]
        is not canonical_rule["references"][0]["location"]
    )

    # --------------------------------------------------------
    # C. 修改 Runtime Rule 不得污染 Canonical Rule
    # --------------------------------------------------------

    runtime_rule["references"][0]["location"]["item_number"] = 99

    assert (
        canonical_rule["references"][0]["location"]["item_number"]
        == 1
    )

    # --------------------------------------------------------
    # D. 修改 Runtime Rule 不得污染 Registry
    # --------------------------------------------------------

    fresh_registry_rule = get_rule(TEST_RULE_ID)

    assert (
        fresh_registry_rule["references"]
        == expected_references
    )

    assert (
        fresh_registry_rule["references"][0]["location"]["item_number"]
        == 1
    )
