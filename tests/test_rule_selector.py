from __future__ import annotations

from typing import Any, Dict

from src.legal_rule_registry import register_rule
from src.legal_rule_selector import (
    select_rule_from_article,
    select_rule_from_articles,
)


LAW_NAME = "中华人民共和国劳动合同法"
ARTICLE_14 = "第十四条"

TEST_LAW_NAME = "V6.2 测试法律"
TEST_ARTICLE_99 = "第九十九条"
TEST_RULE_ID = "RULE-TEST-002"


_TEST_RULE_REGISTERED = False


def register_test_rule() -> None:
    """
    注册临时第二规则。

    用于证明生产 Rule Selector
    不依赖 RULE-001 / Article 14。

    同一测试进程中只注册一次，
    避免重复 Rule ID 触发 Registry 的重复注册保护。
    """

    global _TEST_RULE_REGISTERED

    if _TEST_RULE_REGISTERED:
        return

    register_rule(
        {
            "rule_id": TEST_RULE_ID,
            "law_name": TEST_LAW_NAME,
            "article_number": TEST_ARTICLE_99,
            "rule_name": "V6.2 临时测试规则",
            "conditions": [
                "测试条件",
            ],
            "exclusion_conditions": [],
            "exceptions": [],
            "condition_definitions": [
                {
                    "condition_id": "TEST-REQUIRED-001",
                    "condition": "测试条件",
                    "condition_type": "REQUIRED",
                },
            ],
            "legal_obligations": [
                "测试义务",
            ],
            "legal_consequences": [
                "测试法律后果",
            ],
            "references": [
                TEST_ARTICLE_99,
            ],
        }
    )

    _TEST_RULE_REGISTERED = True


def test_article_14_selection() -> None:
    article = {
        "law_name": LAW_NAME,
        "article_number": ARTICLE_14,
        "rule_text": "Article 14 test",
    }

    rule = select_rule_from_article(article)

    assert rule is not None
    assert rule["rule_id"] == "RULE-001"
    assert rule["law_name"] == LAW_NAME
    assert rule["article_number"] == ARTICLE_14


def test_runtime_rule_selection() -> None:
    register_test_rule()

    article = {
        "law_name": TEST_LAW_NAME,
        "article_number": TEST_ARTICLE_99,
        "rule_text": "Article 99 test",
    }

    rule = select_rule_from_article(article)

    assert rule is not None
    assert rule["rule_id"] == TEST_RULE_ID
    assert rule["law_name"] == TEST_LAW_NAME
    assert rule["article_number"] == TEST_ARTICLE_99


def test_unregistered_article() -> None:
    article = {
        "law_name": LAW_NAME,
        "article_number": "第八十二条",
    }

    rule = select_rule_from_article(article)

    assert rule is None


def test_missing_article_identity() -> None:
    article = {
        "law_name": LAW_NAME,
    }

    rule = select_rule_from_article(article)

    assert rule is None


def test_invalid_article_input() -> None:
    rule = select_rule_from_article(
        "invalid"  # type: ignore[arg-type]
    )

    assert rule is None


def test_multiple_articles_selects_registered_rule() -> None:
    register_test_rule()

    articles = [
        {
            "law_name": LAW_NAME,
            "article_number": "第八十二条",
        },
        {
            "law_name": TEST_LAW_NAME,
            "article_number": TEST_ARTICLE_99,
        },
    ]

    rule = select_rule_from_articles(articles)

    assert rule is not None
    assert rule["rule_id"] == TEST_RULE_ID


def test_multiple_articles_returns_none_when_unregistered() -> None:
    articles = [
        {
            "law_name": LAW_NAME,
            "article_number": "第八十二条",
        },
        {
            "law_name": "中华人民共和国劳动法",
            "article_number": ARTICLE_14,
        },
    ]

    rule = select_rule_from_articles(articles)

    assert rule is None


def test_selection_returns_isolated_rule() -> None:
    article = {
        "law_name": LAW_NAME,
        "article_number": ARTICLE_14,
    }

    first = select_rule_from_article(article)
    second = select_rule_from_article(article)

    assert first is not None
    assert second is not None

    first["conditions"].append(
        "TEST_SELECTION_MUTATION"
    )

    assert second["conditions"] != first["conditions"]


def main() -> None:
    print("=" * 70)
    print(
        "RAG V6.2 Production Rule Selector Regression Test"
    )
    print("=" * 70)

    test_article_14_selection()
    print("PASS: Production Selector Article 14 → RULE-001")

    test_runtime_rule_selection()
    print(
        "PASS: Production Selector Runtime Article 99 "
        "→ RULE-TEST-002"
    )

    test_unregistered_article()
    print(
        "PASS: Production Selector 未注册 Article → None"
    )

    test_missing_article_identity()
    print(
        "PASS: Production Selector 缺少 Article Identity → None"
    )

    test_invalid_article_input()
    print(
        "PASS: Production Selector 非法输入 → None"
    )

    test_multiple_articles_selects_registered_rule()
    print(
        "PASS: Production Selector 多 Article → Runtime Rule"
    )

    test_multiple_articles_returns_none_when_unregistered()
    print(
        "PASS: Production Selector 多 Article 无匹配 → None"
    )

    test_selection_returns_isolated_rule()
    print(
        "PASS: Production Selector 返回独立 Rule"
    )

    print()
    print(
        "PASS: Production Rule Selector Regression Test"
    )


if __name__ == "__main__":
    main()
