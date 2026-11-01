# -*- coding: utf-8 -*-

"""Canonical Rule Definition 边界与语义一致性回归测试。"""

from copy import deepcopy

import pytest

from src.legal_rule_definition import (
    build_article_14_definition,
    validate_article_14_definition,
    validate_article_14_fact_condition_relationships,
)


def _first_relationship(definition):
    return definition["fact_condition_relationships"][0]


def _first_predicate(definition):
    return _first_relationship(definition)["predicate_groups"][0]["predicates"][0]


@pytest.mark.parametrize(
    "bad_input",
    [
        None,
        [],
        "invalid",
        123,
        {"conditions": None},
    ],
    ids=[
        "none",
        "list",
        "string",
        "integer",
        "conditions-none",
    ],
)
def test_validator_rejects_malformed_top_level_inputs(bad_input):
    result = validate_article_14_definition(bad_input)
    assert result["valid"] is False


@pytest.mark.parametrize(
    "mutate",
    [
        pytest.param(
            lambda d: d["fact_condition_relationships"].__setitem__(0, None),
            id="relationship-item-none",
        ),
        pytest.param(
            lambda d: _first_relationship(d).__setitem__(
                "predicate_groups", None
            ),
            id="predicate-groups-none",
        ),
        pytest.param(
            lambda d: _first_relationship(d)["predicate_groups"].__setitem__(
                0, None
            ),
            id="predicate-group-item-none",
        ),
        pytest.param(
            lambda d: _first_relationship(d)["predicate_groups"][0][
                "predicates"
            ].__setitem__(0, None),
            id="predicate-item-none",
        ),
    ],
)
def test_validator_rejects_broken_nested_relationship_structures(mutate):
    definition = build_article_14_definition()
    mutate(definition)

    result = validate_article_14_definition(definition)
    assert result["valid"] is False


@pytest.mark.parametrize(
    "mutate",
    [
        pytest.param(
            lambda d: _first_relationship(d).__setitem__(
                "condition_id", "UNKNOWN-CONDITION-ID"
            ),
            id="unknown-condition-id",
        ),
        pytest.param(
            lambda d: _first_relationship(d).__setitem__(
                "relationship_id", ""
            ),
            id="empty-relationship-id",
        ),
        pytest.param(
            lambda d: d["condition_definitions"][1].__setitem__(
                "condition_id",
                d["condition_definitions"][0]["condition_id"],
            ),
            id="duplicate-condition-id",
        ),
        pytest.param(
            lambda d: d["condition_definitions"][0].__setitem__(
                "condition", "人为替换的条件文本"
            ),
            id="condition-text-mismatch",
        ),
    ],
)
def test_validator_rejects_cross_field_inconsistency(mutate):
    definition = build_article_14_definition()
    mutate(definition)

    result = validate_article_14_definition(definition)
    assert result["valid"] is False


@pytest.mark.parametrize(
    "mutate",
    [
        pytest.param(
            lambda d: _first_relationship(d).__setitem__(
                "result_status", "NOT_SATISFIED"
            ),
            id="proves-true-status-conflict",
        ),
        pytest.param(
            lambda d: (
                _first_relationship(d).__setitem__(
                    "relationship_type", "PROVES_FALSE"
                ),
                _first_relationship(d).__setitem__(
                    "result_status", "SATISFIED"
                ),
            ),
            id="proves-false-status-conflict",
        ),
        pytest.param(
            lambda d: (
                _first_relationship(d).__setitem__(
                    "relationship_type", "DOES_NOT_PROVE"
                ),
                _first_relationship(d).__setitem__(
                    "result_status", "SATISFIED"
                ),
            ),
            id="does-not-prove-status-conflict",
        ),
        pytest.param(
            lambda d: _first_predicate(d).__setitem__("fact_key", "   "),
            id="blank-fact-key",
        ),
        pytest.param(
            lambda d: _first_relationship(d)["predicate_groups"][0].__setitem__(
                "match", "ANY"
            ),
            id="invalid-predicate-match",
        ),
        pytest.param(
            lambda d: (
                _first_predicate(d).__setitem__("operator", ">="),
                _first_predicate(d).__setitem__("value", True),
            ),
            id="boolean-value-for-greater-equal",
        ),
        pytest.param(
            lambda d: _first_relationship(d).__setitem__(
                "predicate_groups", []
            ),
            id="empty-predicate-groups",
        ),
    ],
)
def test_validator_rejects_semantically_inconsistent_relationships(mutate):
    definition = build_article_14_definition()
    mutate(definition)

    result = validate_article_14_definition(definition)
    assert result["valid"] is False


@pytest.mark.parametrize(
    "mutate",
    [
        pytest.param(
            lambda d: d["fact_condition_relationships"][0].__setitem__(
                "relationship_id",
                "REPLACED-RELATIONSHIP-ID",
            ),
            id="relationship-id-replaced",
        ),
        pytest.param(
            lambda d: _first_predicate(d).__setitem__(
                "fact_key",
                "another.valid.fact_key",
            ),
            id="fact-key-replaced",
        ),
        pytest.param(
            lambda d: _first_predicate(d).__setitem__(
                "value",
                3,
            ),
            id="predicate-value-replaced",
        ),
        pytest.param(
            lambda d: (
                _first_predicate(d).__setitem__("operator", "=="),
                _first_predicate(d).__setitem__("value", 2),
            ),
            id="predicate-operator-replaced",
        ),
        pytest.param(
            lambda d: _first_relationship(d)["predicate_groups"][0][
                "predicates"
            ].pop(),
            id="predicate-removed",
        ),
        pytest.param(
            lambda d: _first_relationship(d).__setitem__(
                "reason",
                "替换后的非空关系说明",
            ),
            id="reason-replaced",
        ),
    ],
)
def test_validator_rejects_noncanonical_relationship_content(mutate):
    """字段结构仍然合法，但偏离 Canonical Builder 时必须拒绝。"""
    definition = build_article_14_definition()
    mutate(definition)

    result = validate_article_14_definition(definition)

    assert result["valid"] is False


def test_standalone_relationship_validator_accepts_explicit_canonical_content():
    """独立 Relationship Validator 应接受显式传入的标准关系。"""
    definition = build_article_14_definition()

    result = validate_article_14_fact_condition_relationships({
        "fact_condition_relationships": definition["fact_condition_relationships"]
    })

    assert result["valid"] is True
    assert result["relationship_count"] == 14
    assert result["unique_relationship_id_count"] == 14


@pytest.mark.parametrize(
    "mutate",
    [
        pytest.param(
            lambda d: d["fact_condition_relationships"][0].__setitem__(
                "relationship_id",
                "REPLACED-RELATIONSHIP-ID",
            ),
            id="relationship-id-replaced",
        ),
        pytest.param(
            lambda d: _first_predicate(d).__setitem__(
                "fact_key",
                "another.valid.fact_key",
            ),
            id="fact-key-replaced",
        ),
        pytest.param(
            lambda d: _first_predicate(d).__setitem__(
                "value",
                3,
            ),
            id="predicate-value-replaced",
        ),
        pytest.param(
            lambda d: (
                _first_predicate(d).__setitem__("operator", "=="),
                _first_predicate(d).__setitem__("value", 2),
            ),
            id="predicate-operator-replaced",
        ),
        pytest.param(
            lambda d: _first_relationship(d)["predicate_groups"][0][
                "predicates"
            ].pop(),
            id="predicate-removed",
        ),
        pytest.param(
            lambda d: _first_relationship(d).__setitem__(
                "reason",
                "替换后的非空关系说明",
            ),
            id="reason-replaced",
        ),
    ],
)
def test_standalone_relationship_validator_rejects_noncanonical_content(
    mutate,
):
    """独立 Validator 必须拒绝结构合法但偏离 Canonical Builder 的关系。"""
    definition = build_article_14_definition()
    mutate(definition)

    result = validate_article_14_fact_condition_relationships({
        "fact_condition_relationships": definition["fact_condition_relationships"]
    })

    assert result["valid"] is False


def test_validator_does_not_mutate_supplied_definition():
    definition = build_article_14_definition()
    before = deepcopy(definition)

    validate_article_14_definition(definition)

    assert definition == before



def test_article_14_canonical_identity_fields_must_match():
    """身份字段即使仍是非空字符串，也不能偏离 Canonical Definition。"""
    from copy import deepcopy

    baseline = build_article_14_definition()

    mutations = {
        "rule_id": "OTHER_RULE",
        "rule_name": "其他规则",
        "law_name": "其他法律",
        "article_number": "第九十九条",
    }

    assert validate_article_14_definition(baseline)["valid"] is True

    for field, altered_value in mutations.items():
        definition = deepcopy(baseline)
        definition[field] = altered_value

        result = validate_article_14_definition(definition)
        assert result["valid"] is False, (
            f"{field} 被替换后仍被接受：{result!r}"
        )
