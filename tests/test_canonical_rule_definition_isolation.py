# -*- coding: utf-8 -*-

"""Canonical Rule Definition 深层对象隔离回归测试。"""

from src.legal_rule_definition import build_article_14_definition


def test_definition_builds_independent_nested_objects():
    """两次构建的定义及深层嵌套对象必须相互独立。"""
    first = build_article_14_definition()
    second = build_article_14_definition()

    assert first is not second

    for key in (
        "conditions",
        "exclusion_conditions",
        "exceptions",
        "condition_definitions",
        "fact_condition_relationships",
        "legal_obligations",
        "legal_consequences",
        "references",
    ):
        assert first[key] is not second[key], (
            f"{key} 不应共享同一个列表对象"
        )

    assert (
        first["condition_definitions"][0]
        is not second["condition_definitions"][0]
    )

    first_relationship = first["fact_condition_relationships"][0]
    second_relationship = second["fact_condition_relationships"][0]

    assert first_relationship is not second_relationship
    assert (
        first_relationship["predicate_groups"]
        is not second_relationship["predicate_groups"]
    )

    first_group = first_relationship["predicate_groups"][0]
    second_group = second_relationship["predicate_groups"][0]

    assert first_group is not second_group
    assert first_group["predicates"] is not second_group["predicates"]
    assert first_group["predicates"][0] is not second_group["predicates"][0]


def test_mutating_one_definition_does_not_pollute_another():
    """修改一个定义的深层字段，不得影响另一次构建的定义。"""
    first = build_article_14_definition()
    second = build_article_14_definition()

    original_condition = second["condition_definitions"][0]["condition"]
    original_predicate_value = (
        second["fact_condition_relationships"][0]
        ["predicate_groups"][0]["predicates"][0]["value"]
    )

    first["condition_definitions"][0]["condition"] = "测试修改条件"
    first["fact_condition_relationships"][0][
        "predicate_groups"
    ][0]["predicates"][0]["value"] = 999

    assert (
        second["condition_definitions"][0]["condition"]
        == original_condition
    )

    assert (
        second["fact_condition_relationships"][0]
        ["predicate_groups"][0]["predicates"][0]["value"]
        == original_predicate_value
    )


def test_validate_article_14_definition_reports_valid_baseline():
    """标准 Article 14 Canonical Definition 应通过完整结构验证。"""
    from src.legal_rule_definition import validate_article_14_definition

    result = validate_article_14_definition()

    assert result["valid"] is True
    assert result["required_count"] == 4
    assert result["exclusion_count"] == 3
    assert result["exception_count"] == 1
    assert result["condition_count"] == 8
    assert result["unique_condition_count"] == 8

    identity = result["condition_identity"]
    assert identity["valid"] is True
    assert identity["definition_count"] == 8
    assert identity["unique_id_count"] == 8
    assert identity["expected_count"] == 8

    relationships = result["fact_condition_relationships"]
    assert relationships["valid"] is True
    assert relationships["relationship_count"] == 14
    assert relationships["unique_relationship_id_count"] == 14
    assert relationships["covered_condition_count"] == 8
    assert relationships["expected_condition_count"] == 8


def test_validator_rejects_mutated_definition():
    """验证器应检查传入对象，而不是另行构建的标准定义。"""
    from copy import deepcopy
    from src.legal_rule_definition import validate_article_14_definition

    mutations = [
        (
            "条件文本被篡改",
            lambda rule: rule["conditions"].__setitem__(
                0, "篡改后的条件"
            ),
        ),
        (
            "条件身份定义缺失",
            lambda rule: rule["condition_definitions"].pop(),
        ),
        (
            "事实条件关系缺失",
            lambda rule: rule["fact_condition_relationships"].pop(),
        ),
        (
            "关系 ID 重复",
            lambda rule: rule["fact_condition_relationships"][1].__setitem__(
                "relationship_id",
                rule["fact_condition_relationships"][0]["relationship_id"],
            ),
        ),
    ]

    for label, mutate in mutations:
        definition = build_article_14_definition()
        mutate(definition)

        result = validate_article_14_definition(definition)

        assert result["valid"] is False, (
            f"验证器未识别损坏场景：{label}"
        )


def test_validator_rejects_malformed_inputs_without_raising():
    """非法定义和错误字段类型应返回 valid=False，而不是意外抛出异常。"""
    from copy import deepcopy
    from src.legal_rule_definition import (
        validate_article_14_definition,
        validate_article_14_condition_identity,
        validate_article_14_fact_condition_relationships,
    )

    assert validate_article_14_definition()["valid"] is True
    assert validate_article_14_definition(None)["valid"] is False
    assert validate_article_14_definition([])["valid"] is False

    # 子验证器：无参数时使用标准定义，显式 None 必须被拒绝。
    assert validate_article_14_condition_identity()["valid"] is True
    assert validate_article_14_condition_identity(None)["valid"] is False

    assert validate_article_14_fact_condition_relationships()["valid"] is True
    assert validate_article_14_fact_condition_relationships(None)["valid"] is False
    assert validate_article_14_definition("not a definition")["valid"] is False

    malformed_definitions = []

    missing_identity = build_article_14_definition()
    missing_identity.pop("condition_definitions")
    malformed_definitions.append(("缺少 condition_definitions", missing_identity))

    missing_relationships = build_article_14_definition()
    missing_relationships.pop("fact_condition_relationships")
    malformed_definitions.append(("缺少 fact_condition_relationships", missing_relationships))

    wrong_condition_type = build_article_14_definition()
    wrong_condition_type["conditions"] = "不是列表"
    malformed_definitions.append(("conditions 类型错误", wrong_condition_type))

    non_string_condition = build_article_14_definition()
    non_string_condition["conditions"][0] = {"unexpected": "dict"}
    malformed_definitions.append(("条件列表包含非字符串", non_string_condition))

    malformed_relationship_type = build_article_14_definition()
    malformed_relationship_type["fact_condition_relationships"][0][
        "relationship_type"
    ] = []
    malformed_definitions.append(("relationship_type 类型错误", malformed_relationship_type))

    malformed_result_status = build_article_14_definition()
    malformed_result_status["fact_condition_relationships"][0][
        "result_status"
    ] = []
    malformed_definitions.append(("result_status 类型错误", malformed_result_status))


    malformed_reason = build_article_14_definition()
    malformed_reason["fact_condition_relationships"][0]["reason"] = []
    malformed_definitions.append(("reason 类型错误", malformed_reason))

    malformed_fact_key = build_article_14_definition()
    malformed_fact_key["fact_condition_relationships"][0][
        "predicate_groups"
    ][0]["predicates"][0]["fact_key"] = []
    malformed_definitions.append(("fact_key 类型错误", malformed_fact_key))

    malformed_value = build_article_14_definition()
    malformed_value["fact_condition_relationships"][0][
        "predicate_groups"
    ][0]["predicates"][0]["value"] = {"unexpected": "dict"}
    malformed_definitions.append(("value 类型错误", malformed_value))

    malformed_predicate_groups = build_article_14_definition()
    malformed_predicate_groups["fact_condition_relationships"][0][
        "predicate_groups"
    ] = [{"match": "ALL", "predicates": [None]}]
    malformed_definitions.append(("predicate 结构错误", malformed_predicate_groups))

    malformed_rule_id = build_article_14_definition()
    malformed_rule_id["rule_id"] = "   "
    malformed_definitions.append(("rule_id 为空白字符串", malformed_rule_id))

    malformed_rule_name = build_article_14_definition()
    malformed_rule_name["rule_name"] = None
    malformed_definitions.append(("rule_name 类型错误", malformed_rule_name))

    malformed_obligations = build_article_14_definition()
    malformed_obligations["legal_obligations"] = ["有效内容", None]
    malformed_definitions.append(("legal_obligations 含非字符串", malformed_obligations))

    malformed_consequences = build_article_14_definition()
    malformed_consequences["legal_consequences"] = ["   "]
    malformed_definitions.append(("legal_consequences 含空白字符串", malformed_consequences))

    malformed_references = build_article_14_definition()
    malformed_references["references"] = [{"unexpected": "dict"}]
    malformed_definitions.append(("references 含非字符串", malformed_references))

    malformed_operator = build_article_14_definition()
    malformed_operator["fact_condition_relationships"][0][
        "predicate_groups"
    ][0]["predicates"][0]["operator"] = []
    malformed_definitions.append(("operator 类型错误", malformed_operator))

    for label, definition in malformed_definitions:
        result = validate_article_14_definition(definition)
        assert result["valid"] is False, f"未拒绝异常输入：{label}"
