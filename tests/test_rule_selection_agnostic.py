from __future__ import annotations

from typing import Any, Dict, Optional

from src.legal_rule_registry import register_rule
from src.legal_rule_selector import select_rule_from_article


LAW_NAME = "中华人民共和国劳动合同法"
ARTICLE_14 = "第十四条"

TEST_LAW_NAME = "V6.2 测试法律"
TEST_ARTICLE_99 = "第九十九条"
TEST_RULE_ID = "RULE-TEST-002"


def register_test_rule() -> None:
    """
    注册临时 RULE-TEST-002。
    """

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


def test_unregistered_article_selection() -> None:
    article = {
        "law_name": LAW_NAME,
        "article_number": "第八十二条",
        "rule_text": "Unregistered article",
    }

    rule = select_rule_from_article(article)

    assert rule is None


def test_wrong_law_selection() -> None:
    article = {
        "law_name": "中华人民共和国劳动法",
        "article_number": ARTICLE_14,
        "rule_text": "Wrong law",
    }

    rule = select_rule_from_article(article)

    assert rule is None


def test_missing_article_identity() -> None:
    article = {
        "law_name": LAW_NAME,
        "rule_text": "Missing article number",
    }

    rule = select_rule_from_article(article)

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
        "RAG V6.2 Rule Selection Agnostic Regression Test"
    )
    print("=" * 70)

    test_article_14_selection()
    print("PASS: Article 14 → RULE-001")

    test_runtime_rule_selection()
    print(
        "PASS: Runtime Article 99 → RULE-TEST-002"
    )

    test_unregistered_article_selection()
    print(
        "PASS: 未注册 Article → None"
    )

    test_wrong_law_selection()
    print(
        "PASS: 不同法律不会错误选择 Rule"
    )

    test_missing_article_identity()
    print(
        "PASS: 缺少 Article Identity → None"
    )

    test_selection_returns_isolated_rule()
    print(
        "PASS: Rule Selection 返回独立副本"
    )

    print()
    print(
        "PASS: Rule Selection Agnostic Test"
    )


if __name__ == "__main__":
    main()
