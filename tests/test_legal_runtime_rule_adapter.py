from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict

from src.legal_rule_registry import (
    get_rule,
    register_rule,
)
from src.legal_rule_definition import RULE_ID


TEST_LAW_NAME = "V6.2 测试法律"
TEST_ARTICLE_99 = "第九十九条"
TEST_RULE_ID = "RULE-TEST-002"


def build_test_canonical_rule() -> Dict[str, Any]:
    """
    构造一个与 Article 14 无关的临时 Canonical Rule。

    目的：
        验证 Canonical → Runtime Adapter
        不依赖 Article 14 固定条件数量、
        Condition ID 或 Article 14 特殊字段。
    """

    return {
        "rule_id": TEST_RULE_ID,
        "law_name": TEST_LAW_NAME,
        "article_number": TEST_ARTICLE_99,
        "rule_name": "V6.2 临时测试规则",
        "conditions": [
            "测试条件一",
        ],
        "exclusion_conditions": [
            "测试排除条件",
        ],
        "exceptions": [
            "测试例外条件",
        ],
        "condition_definitions": [
            {
                "condition_id": "TEST-REQUIRED-001",
                "condition": "测试条件一",
                "condition_type": "REQUIRED",
            },
            {
                "condition_id": "TEST-EXCLUSION-001",
                "condition": "测试排除条件",
                "condition_type": "EXCLUSION",
            },
            {
                "condition_id": "TEST-EXCEPTION-001",
                "condition": "测试例外条件",
                "condition_type": "EXCEPTION",
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


def register_test_rule() -> None:
    """
    注册临时 Canonical Rule。

    Registry 已存在时不重复注册。
    """

    try:
        get_rule(TEST_RULE_ID)
        return
    except KeyError:
        pass

    register_rule(
        build_test_canonical_rule()
    )


def test_article_14_canonical_to_runtime() -> None:
    """
    Article 14 Canonical Rule 可以转换成 Runtime Rule。
    """

    register_test_rule()

    canonical_rule = get_rule(RULE_ID)

    from src.legal_runtime_rule_adapter import (
        canonical_rule_to_runtime_rule,
    )

    runtime_rule = canonical_rule_to_runtime_rule(
        canonical_rule
    )

    assert isinstance(runtime_rule, dict)

    assert runtime_rule["rule_id"] == canonical_rule["rule_id"]
    assert runtime_rule["law_name"] == canonical_rule["law_name"]
    assert runtime_rule["article"] == canonical_rule["article_number"]
    assert runtime_rule["rule_name"] == canonical_rule["rule_name"]

    assert runtime_rule["conditions"] == canonical_rule["conditions"]
    assert (
        runtime_rule["exclusion_conditions"]
        == canonical_rule["exclusion_conditions"]
    )
    assert (
        runtime_rule["exceptions"]
        == canonical_rule["exceptions"]
    )
    assert (
        runtime_rule["condition_definitions"]
        == canonical_rule["condition_definitions"]
    )


def test_non_article_14_canonical_to_runtime() -> None:
    """
    非 Article 14 Canonical Rule 同样可以转换。
    """

    register_test_rule()

    canonical_rule = get_rule(TEST_RULE_ID)

    from src.legal_runtime_rule_adapter import (
        canonical_rule_to_runtime_rule,
    )

    runtime_rule = canonical_rule_to_runtime_rule(
        canonical_rule
    )

    assert runtime_rule["rule_id"] == TEST_RULE_ID
    assert runtime_rule["law_name"] == TEST_LAW_NAME
    assert runtime_rule["article"] == TEST_ARTICLE_99

    assert runtime_rule["conditions"] == [
        "测试条件一",
    ]

    assert runtime_rule["exclusion_conditions"] == [
        "测试排除条件",
    ]

    assert runtime_rule["exceptions"] == [
        "测试例外条件",
    ]

    assert len(runtime_rule["condition_definitions"]) == 3


def test_runtime_rule_has_no_article_14_priority() -> None:
    """
    Runtime Rule 不应产生 Article 14 专属 priority。
    """

    register_test_rule()

    canonical_rule = get_rule(TEST_RULE_ID)

    from src.legal_runtime_rule_adapter import (
        canonical_rule_to_runtime_rule,
    )

    runtime_rule = canonical_rule_to_runtime_rule(
        canonical_rule
    )

    assert "priority" not in runtime_rule


def test_runtime_rule_condition_counts_are_dynamic() -> None:
    """
    Runtime Rule 的条件数量来自 Canonical Rule，
    不固定假设 Article 14 的 4/3/1。
    """

    register_test_rule()

    canonical_rule = get_rule(TEST_RULE_ID)

    from src.legal_runtime_rule_adapter import (
        canonical_rule_to_runtime_rule,
    )

    runtime_rule = canonical_rule_to_runtime_rule(
        canonical_rule
    )

    assert len(runtime_rule["conditions"]) == 1
    assert len(runtime_rule["exclusion_conditions"]) == 1
    assert len(runtime_rule["exceptions"]) == 1
    assert len(runtime_rule["condition_definitions"]) == 3


def test_runtime_rule_isolated_from_canonical_rule() -> None:
    """
    Runtime Rule 修改不能污染 Canonical Rule。
    """

    register_test_rule()

    canonical_rule = get_rule(TEST_RULE_ID)

    from src.legal_runtime_rule_adapter import (
        canonical_rule_to_runtime_rule,
    )

    runtime_rule = canonical_rule_to_runtime_rule(
        canonical_rule
    )

    runtime_rule["conditions"].append(
        "RUNTIME_MUTATION"
    )

    runtime_rule["condition_definitions"].append(
        {
            "condition_id": "RUNTIME-MUTATION",
            "condition": "Runtime Mutation",
            "condition_type": "REQUIRED",
        }
    )

    fresh_canonical_rule = get_rule(TEST_RULE_ID)

    assert "RUNTIME_MUTATION" not in (
        fresh_canonical_rule["conditions"]
    )

    assert all(
        item["condition_id"] != "RUNTIME-MUTATION"
        for item in fresh_canonical_rule[
            "condition_definitions"
        ]
    )


def test_optional_rule_text_is_preserved() -> None:
    """
    Retriever 提供的 rule_text 可以作为可选 Runtime metadata。
    """

    register_test_rule()

    canonical_rule = get_rule(TEST_RULE_ID)

    from src.legal_runtime_rule_adapter import (
        canonical_rule_to_runtime_rule,
    )

    runtime_rule = canonical_rule_to_runtime_rule(
        canonical_rule,
        rule_text="V6.2 Runtime Rule Test Text",
    )

    assert (
        runtime_rule["rule_text"]
        == "V6.2 Runtime Rule Test Text"
    )


def test_runtime_rule_minimum_contract() -> None:
    """
    Runtime Rule 必须至少满足当前 Decision Engine
    已确认的结构契约。
    """

    register_test_rule()

    canonical_rule = get_rule(TEST_RULE_ID)

    from src.legal_runtime_rule_adapter import (
        canonical_rule_to_runtime_rule,
    )

    runtime_rule = canonical_rule_to_runtime_rule(
        canonical_rule
    )

    required_fields = {
        "rule_id",
        "law_name",
        "article",
        "rule_name",
        "conditions",
        "exclusion_conditions",
        "exceptions",
        "condition_definitions",
    }

    assert required_fields.issubset(
        runtime_rule.keys()
    )


def main() -> None:
    print("=" * 70)
    print(
        "RAG V6.2 Canonical → Runtime Rule Adapter Regression Test"
    )
    print("=" * 70)

    tests = [
        (
            test_article_14_canonical_to_runtime,
            "Article 14 Canonical → Runtime",
        ),
        (
            test_non_article_14_canonical_to_runtime,
            "非 Article 14 Canonical → Runtime",
        ),
        (
            test_runtime_rule_has_no_article_14_priority,
            "Runtime Rule 不包含 Article 14 priority",
        ),
        (
            test_runtime_rule_condition_counts_are_dynamic,
            "Runtime Rule 条件数量动态化",
        ),
        (
            test_runtime_rule_isolated_from_canonical_rule,
            "Runtime Rule 与 Canonical Rule 隔离",
        ),
        (
            test_optional_rule_text_is_preserved,
            "可选 rule_text 保留",
        ),
        (
            test_runtime_rule_minimum_contract,
            "Runtime Rule 最小契约",
        ),
    ]

    for test, description in tests:
        test()
        print(f"PASS: {description}")

    print()
    print(
        "PASS: Canonical → Runtime Rule Adapter Boundary Test"
    )


if __name__ == "__main__":
    main()
