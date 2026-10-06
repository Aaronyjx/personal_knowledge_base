from __future__ import annotations

from typing import Any, Dict

from src.legal_decision_engine import (
    evaluate_rule,
    select_core_rule,
)
from src.legal_fact_models import (
    ContractSequence,
    LegalFacts,
)
from src.legal_rule_registry import get_rule, register_rule
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

    目的：
        验证 Production Rule Selector 与
        Production Runtime Adapter 可以串联工作。
    """

    try:
        get_rule(TEST_RULE_ID)
        return
    except KeyError:
        pass

    register_rule(
        {
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
            "legal_obligations": [
                "测试义务",
            ],
            "legal_consequences": [
                "测试后果",
            ],
            "references": [
                TEST_ARTICLE,
            ],
        }
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


def test_production_select_core_rule_uses_selector_and_adapter() -> None:
    """
    验证生产 Decision Engine 的 select_core_rule()
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



def test_production_selector_adapter_runtime_execution_chain() -> None:
    """
    验证 V6.2 完整生产链：

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
    # Production Rule Selection
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
            test_production_select_core_rule_uses_selector_and_adapter,
            "Production select_core_rule → Selector → Adapter",
        ),
        (
            test_production_selector_adapter_runtime_execution_chain,
            "Production Selector → Adapter → Runtime Execution",
        ),
    ]

    for test, description in tests:
        test()
        print(f"PASS: {description}")

    print()
    print(
        "PASS: Rule Selection → Runtime Adapter Integration Test"
    )


if __name__ == "__main__":
    main()
