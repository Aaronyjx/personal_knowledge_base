from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict

from src.legal_rule_registry import (
    get_rule,
    register_rule,
)
from src.legal_rule_definition import RULE_ID
from src.legal_rule_reference import (
    create_rule_legal_reference,
)


TEST_LAW_NAME = "V6.2 Runtime Adapter 测试法律"
TEST_ARTICLE_99 = "第九十九条"
TEST_ARTICLE_ID = "11111111-2222-4333-8444-555555555555"
TEST_RULE_ID = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"


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
        "fact_condition_relationships": [
            {
                "relationship_id": "TEST-REL-REQUIRED-001",
                "condition_id": "TEST-REQUIRED-001",
                "predicate_groups": [
                    {
                        "match": "ALL",
                        "predicates": [
                            {
                                "fact_key": "test.required",
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
                "relationship_id": "TEST-REL-EXCLUSION-001",
                "condition_id": "TEST-EXCLUSION-001",
                "predicate_groups": [
                    {
                        "match": "ALL",
                        "predicates": [
                            {
                                "fact_key": "test.exclusion",
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
                "relationship_id": "TEST-REL-EXCEPTION-001",
                "condition_id": "TEST-EXCEPTION-001",
                "predicate_groups": [
                    {
                        "match": "ALL",
                        "predicates": [
                            {
                                "fact_key": "test.exception",
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
            "测试法律后果",
        ],
        "references": [
            create_rule_legal_reference(
                rule_id=TEST_RULE_ID,
                article_id=TEST_ARTICLE_ID,
                reference_type="RELATED",
                legal_role="测试规则关联法律依据",
            ).to_dict(),
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
        "fact_condition_relationships",
    }

    assert required_fields.issubset(
        runtime_rule.keys()
    )


def test_adapter_rejects_non_dict_input() -> None:
    """Adapter 应拒绝非 dict 的 Canonical Rule 输入。"""
    import pytest
    from src.legal_runtime_rule_adapter import (
        canonical_rule_to_runtime_rule,
    )

    with pytest.raises(TypeError, match="Canonical Rule 必须是 dict"):
        canonical_rule_to_runtime_rule(None)  # type: ignore[arg-type]



def test_adapter_rejects_missing_required_fields() -> None:
    """Adapter 应拒绝缺少必需字段的 Canonical Rule。"""
    import pytest
    from src.legal_runtime_rule_adapter import (
        canonical_rule_to_runtime_rule,
    )

    with pytest.raises(
        ValueError,
        match="Canonical Rule 缺少 Runtime Adapter 所需字段",
    ):
        canonical_rule_to_runtime_rule({})


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



def test_runtime_nested_mutation_does_not_modify_canonical_rule() -> None:
    """
    修改 Runtime Rule 中的嵌套字段，不得污染 Canonical Rule。
    """

    register_test_rule()

    canonical_rule = get_rule(TEST_RULE_ID)

    from src.legal_runtime_rule_adapter import (
        canonical_rule_to_runtime_rule,
    )

    runtime_rule = canonical_rule_to_runtime_rule(
        canonical_rule
    )

    # 在 Runtime Rule 中增加嵌套数据，模拟真实规则的扩展字段。
    runtime_rule["condition_definitions"][0]["metadata"] = {
        "labels": ["original"],
    }

    # 重新转换，确认 Adapter 复制的是传入 Canonical Rule 的内容。
    # metadata 不属于原始规则，因此这里单独构造带嵌套字段的输入。
    canonical_with_nested_data = deepcopy(canonical_rule)
    canonical_with_nested_data["condition_definitions"][0][
        "metadata"
    ] = {"labels": ["original"]}

    runtime_with_nested_data = canonical_rule_to_runtime_rule(
        canonical_with_nested_data
    )

    runtime_with_nested_data["condition_definitions"][0][
        "metadata"
    ]["labels"].append("runtime-mutation")

    assert canonical_with_nested_data["condition_definitions"][0][
        "metadata"
    ]["labels"] == ["original"]

def test_adapter_rejects_invalid_required_field_types() -> None:
    """Adapter 应拒绝必需字段的错误类型及空字符串。"""
    import pytest

    from src.legal_runtime_rule_adapter import (
        canonical_rule_to_runtime_rule,
    )

    invalid_cases = [
        ("rule_id", 123, TypeError),
        ("law_name", None, TypeError),
        ("article_number", [], TypeError),
        ("rule_name", "", ValueError),
        ("conditions", None, TypeError),
        ("exclusion_conditions", "invalid", TypeError),
        ("exceptions", {}, TypeError),
        ("condition_definitions", "invalid", TypeError),
        ("fact_condition_relationships", {}, TypeError),
    ]

    for field, invalid_value, expected_exception in invalid_cases:
        canonical_rule = build_test_canonical_rule()
        canonical_rule[field] = invalid_value

        with pytest.raises(expected_exception):
            canonical_rule_to_runtime_rule(canonical_rule)


def test_adapter_rejects_invalid_optional_list_types() -> None:
    """可选法律义务和法律后果存在时，也必须是列表。"""
    import pytest

    from src.legal_runtime_rule_adapter import (
        canonical_rule_to_runtime_rule,
    )

    for field in ("legal_obligations", "legal_consequences"):
        canonical_rule = build_test_canonical_rule()
        canonical_rule[field] = "invalid"

        with pytest.raises(TypeError):
            canonical_rule_to_runtime_rule(canonical_rule)


def test_article_14_references_are_preserved_in_runtime() -> None:
    """Article 14 的结构化引用应完整进入 Runtime Rule。"""

    register_test_rule()

    canonical_rule = get_rule(RULE_ID)

    from src.legal_runtime_rule_adapter import (
        canonical_rule_to_runtime_rule,
    )

    runtime_rule = canonical_rule_to_runtime_rule(canonical_rule)

    assert runtime_rule["references"] == canonical_rule["references"]
    assert len(runtime_rule["references"]) == 4

    assert [
        item["reference_type"]
        for item in runtime_rule["references"]
    ] == [
        "PRIMARY",
        "EXCLUSION",
        "EXCLUSION",
        "EXCLUSION",
    ]

    assert runtime_rule["references"][2]["location"]["item_number"] == 1
    assert runtime_rule["references"][3]["location"]["item_number"] == 2


def test_runtime_references_are_deepcopied() -> None:
    """修改 Runtime 引用的嵌套 location 不得污染 Canonical Rule。"""

    register_test_rule()

    canonical_rule = get_rule(RULE_ID)

    from src.legal_runtime_rule_adapter import (
        canonical_rule_to_runtime_rule,
    )

    runtime_rule = canonical_rule_to_runtime_rule(canonical_rule)

    assert runtime_rule["references"] == canonical_rule["references"]
    assert runtime_rule["references"] is not canonical_rule["references"]
    assert runtime_rule["references"][2] is not canonical_rule["references"][2]
    assert (
        runtime_rule["references"][2]["location"]
        is not canonical_rule["references"][2]["location"]
    )

    runtime_rule["references"][2]["location"]["item_number"] = 99

    assert canonical_rule["references"][2]["location"]["item_number"] == 1


def test_adapter_accepts_rule_without_references() -> None:
    """没有 references 字段的通用 Canonical Rule 仍然可以转换。"""

    from src.legal_runtime_rule_adapter import (
        canonical_rule_to_runtime_rule,
    )

    canonical_rule = build_test_canonical_rule()
    canonical_rule.pop("references")

    runtime_rule = canonical_rule_to_runtime_rule(canonical_rule)

    assert "references" not in runtime_rule


def test_adapter_rejects_legacy_string_references() -> None:
    """Adapter 必须拒绝旧字符串引用列表。"""

    import pytest

    from src.legal_runtime_rule_adapter import (
        canonical_rule_to_runtime_rule,
    )

    canonical_rule = build_test_canonical_rule()
    canonical_rule["references"] = [TEST_ARTICLE_99]

    with pytest.raises(
        ValueError,
        match="references 必须是合法的结构化引用列表",
    ):
        canonical_rule_to_runtime_rule(canonical_rule)


def test_adapter_rejects_reference_from_another_rule() -> None:
    """引用所属 rule_id 必须与当前 Canonical Rule 一致。"""

    import pytest

    from src.legal_runtime_rule_adapter import (
        canonical_rule_to_runtime_rule,
    )

    canonical_rule = build_test_canonical_rule()
    canonical_rule["references"][0]["rule_id"] = (
        "99999999-8888-4777-8666-555555555555"
    )

    with pytest.raises(
        ValueError,
        match="references 必须是合法的结构化引用列表",
    ):
        canonical_rule_to_runtime_rule(canonical_rule)


def test_adapter_rejects_malformed_references() -> None:
    """缺少结构化引用必要字段时必须拒绝。"""

    import pytest

    from src.legal_runtime_rule_adapter import (
        canonical_rule_to_runtime_rule,
    )

    canonical_rule = build_test_canonical_rule()
    canonical_rule["references"] = [{"unexpected": "field"}]

    with pytest.raises(
        ValueError,
        match="references 必须是合法的结构化引用列表",
    ):
        canonical_rule_to_runtime_rule(canonical_rule)


def test_adapter_rejects_empty_references() -> None:
    """显式提供空列表时必须拒绝，而不是当作省略字段。"""

    import pytest

    from src.legal_runtime_rule_adapter import (
        canonical_rule_to_runtime_rule,
    )

    canonical_rule = build_test_canonical_rule()
    canonical_rule["references"] = []

    with pytest.raises(
        ValueError,
        match="references 必须是合法的结构化引用列表",
    ):
        canonical_rule_to_runtime_rule(canonical_rule)
