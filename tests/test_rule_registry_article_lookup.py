# -*- coding: utf-8 -*-

"""
RAG V6.2
Canonical Legal Rule Registry
Article Identity → Rule ID Lookup Regression Test

============================================================
测试目标
============================================================

验证 Canonical Rule Registry 是否能够根据：

    law_name
    article_number

找到对应的 Canonical Rule。

核心原则：

    Article Identity
          ↓
    Rule Registry
          ↓
    Canonical Rule

本测试不涉及：

- LegalFacts
- Fact Extraction
- Fact Matching
- ConditionResult
- Decision
- Retriever
- Ollama

当前测试预期：

    RULE-001
        中华人民共和国劳动合同法
        第十四条

    可以通过 Article Identity 找到。

同时：

    第八十二条

    当前尚未注册 Canonical Rule，
    应返回 None。

============================================================
注意
============================================================

这是 V6.2 Rule Mapper 开发前的 Registry TDD 测试。

本测试创建时：

    find_rule_by_article()

尚未存在。

因此第一次运行预期会失败。

这是正常的 RED 阶段，不代表现有 V6.1/V6.2 基线被破坏。
============================================================
"""

from __future__ import annotations

from src.legal_rule_definition import (
    RULE_ID,
)

from src.legal_rule_registry import (
    find_rule_by_article,
    get_rule,
    register_rule,
)


LAW_NAME = "中华人民共和国劳动合同法"
ARTICLE_14 = "第十四条"
ARTICLE_82 = "第八十二条"

TEST_LAW_NAME = "V6.2 测试法律"
TEST_ARTICLE_99 = "第九十九条"
TEST_RULE_ID = "RULE-TEST-002"


def test_article_14_finds_rule_001() -> None:
    """
    Article 14 应映射到 RULE-001。
    """

    rule = find_rule_by_article(
        law_name=LAW_NAME,
        article_number=ARTICLE_14,
    )

    assert rule is not None
    assert rule["rule_id"] == RULE_ID
    assert rule["law_name"] == LAW_NAME
    assert rule["article_number"] == ARTICLE_14


def test_unregistered_article_returns_none() -> None:
    """
    当前未注册 Canonical Rule 的 Article 82 应返回 None。
    """

    rule = find_rule_by_article(
        law_name=LAW_NAME,
        article_number=ARTICLE_82,
    )

    assert rule is None


def test_lookup_returns_isolated_copy() -> None:
    """
    Article Lookup 返回的 Rule 必须是独立副本。

    修改 Lookup 返回值不得污染 Registry。
    """

    first = find_rule_by_article(
        law_name=LAW_NAME,
        article_number=ARTICLE_14,
    )

    assert first is not None

    original = get_rule(RULE_ID)

    first["conditions"].append(
        "TEST_ARTICLE_LOOKUP_MUTATION"
    )

    second = find_rule_by_article(
        law_name=LAW_NAME,
        article_number=ARTICLE_14,
    )

    assert second is not None
    assert (
        second["conditions"]
        == original["conditions"]
    )


def test_lookup_does_not_match_wrong_law() -> None:
    """
    相同 Article Number 不能跨法律错误匹配。

    例如：

        其他法律 + 第十四条

    当前没有对应 Canonical Rule，
    应返回 None。
    """

    rule = find_rule_by_article(
        law_name="中华人民共和国劳动法",
        article_number=ARTICLE_14,
    )

    assert rule is None


def test_lookup_supports_runtime_registered_rule() -> None:
    """
    验证 Article Lookup 真正支持多 Rule。

    注册一个临时的 RULE-TEST-002：

        V6.2 测试法律 + 第九十九条

    然后验证：

        Article Identity
              ↓
        find_rule_by_article()
              ↓
        RULE-TEST-002

    本测试不能依赖 RULE-001 / Article 14。
    """

    temporary_rule = {
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

    register_rule(temporary_rule)

    rule = find_rule_by_article(
        law_name=TEST_LAW_NAME,
        article_number=TEST_ARTICLE_99,
    )

    assert rule is not None
    assert rule["rule_id"] == TEST_RULE_ID
    assert rule["law_name"] == TEST_LAW_NAME
    assert rule["article_number"] == TEST_ARTICLE_99


def test_runtime_registered_rule_isolated() -> None:
    """
    验证临时 Runtime Rule 的 Lookup 返回值仍然是独立副本。
    """

    rule = find_rule_by_article(
        law_name=TEST_LAW_NAME,
        article_number=TEST_ARTICLE_99,
    )

    assert rule is not None

    rule["conditions"].append(
        "TEST_RUNTIME_MUTATION"
    )

    current = find_rule_by_article(
        law_name=TEST_LAW_NAME,
        article_number=TEST_ARTICLE_99,
    )

    assert current is not None
    assert current["conditions"] == [
        "测试条件",
    ]


def test_lookup_does_not_modify_registry() -> None:
    """
    Lookup 本身不得改变 Registry。
    """

    before = get_rule(RULE_ID)

    result = find_rule_by_article(
        law_name=LAW_NAME,
        article_number=ARTICLE_14,
    )

    assert result is not None

    after = get_rule(RULE_ID)

    assert after == before


def main() -> None:
    print("=" * 70)
    print(
        "RAG V6.2 Rule Registry "
        "Article Lookup Regression Test"
    )
    print("=" * 70)

    test_article_14_finds_rule_001()
    print(
        "PASS: Article 14 → RULE-001"
    )

    test_unregistered_article_returns_none()
    print(
        "PASS: 未注册 Article → None"
    )

    test_lookup_returns_isolated_copy()
    print(
        "PASS: Lookup 返回独立副本"
    )

    test_lookup_does_not_match_wrong_law()
    print(
        "PASS: 不同法律不会错误匹配"
    )

    test_lookup_supports_runtime_registered_rule()
    print(
        "PASS: Runtime RULE-TEST-002 → Article Lookup"
    )

    test_runtime_registered_rule_isolated()
    print(
        "PASS: Runtime Rule Lookup 返回独立副本"
    )

    test_lookup_does_not_modify_registry()
    print(
        "PASS: Lookup 不修改 Registry"
    )

    print()
    print(
        "PASS: Rule Registry Article Lookup Test"
    )


if __name__ == "__main__":
    main()
