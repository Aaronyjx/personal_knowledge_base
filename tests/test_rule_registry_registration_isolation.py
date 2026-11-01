# -*- coding: utf-8 -*-

"""
Canonical Rule Registry 注册输入与读取隔离回归测试。

每个测试自行注册独立规则，不依赖其他测试的执行顺序。
"""

from src.legal_rule_registry import get_rule, register_rule


def _register_test_rule(rule_id: str) -> None:
    """为当前测试注册独立的嵌套测试规则。"""
    try:
        get_rule(rule_id)
    except KeyError:
        pass
    else:
        raise AssertionError(f"测试规则已存在，拒绝覆盖：{rule_id}")

    register_rule(
        {
            "rule_id": rule_id,
            "law_name": "Registry 隔离测试法律",
            "article_number": "第九十九条",
            "conditions": ["原始条件"],
            "condition_definitions": [
                {
                    "condition_id": "TEST-REQUIRED-001",
                    "condition": "原始条件",
                    "condition_type": "REQUIRED",
                    "metadata": {
                        "labels": ["original"],
                    },
                },
            ],
        }
    )


def test_register_rule_copies_input_deeply() -> None:
    """注册后修改原始对象，不得影响 Registry。"""
    rule_id = "RULE-TEST-REGISTRATION-INPUT-ISOLATION"

    original_rule = {
        "rule_id": rule_id,
        "law_name": "Registry 隔离测试法律",
        "article_number": "第九十九条",
        "conditions": ["原始条件"],
        "condition_definitions": [
            {
                "condition_id": "TEST-REQUIRED-001",
                "condition": "原始条件",
                "condition_type": "REQUIRED",
                "metadata": {
                    "labels": ["original"],
                },
            },
        ],
    }

    try:
        get_rule(rule_id)
    except KeyError:
        pass
    else:
        raise AssertionError(f"测试规则已存在，拒绝覆盖：{rule_id}")

    register_rule(original_rule)

    original_rule["law_name"] = "被修改的法律"
    original_rule["conditions"].append("外部新增条件")
    original_rule["condition_definitions"][0]["condition"] = "被修改的条件"
    original_rule["condition_definitions"][0]["metadata"]["labels"].append(
        "mutated"
    )

    stored_rule = get_rule(rule_id)

    assert stored_rule["law_name"] == "Registry 隔离测试法律"
    assert stored_rule["conditions"] == ["原始条件"]

    definition = stored_rule["condition_definitions"][0]
    assert definition["condition"] == "原始条件"
    assert definition["metadata"]["labels"] == ["original"]


def test_get_rule_returns_independent_nested_copy() -> None:
    """修改读取结果的嵌套字段，不得影响 Registry。"""
    rule_id = "RULE-TEST-READ-NESTED-ISOLATION"
    _register_test_rule(rule_id)

    stored_rule = get_rule(rule_id)
    stored_rule["conditions"].append("读取结果修改")
    stored_rule["condition_definitions"][0]["metadata"]["labels"].append(
        "read-mutation"
    )

    fresh_rule = get_rule(rule_id)

    assert fresh_rule["conditions"] == ["原始条件"]
    assert (
        fresh_rule["condition_definitions"][0]["metadata"]["labels"]
        == ["original"]
    )


if __name__ == "__main__":
    test_register_rule_copies_input_deeply()
    test_get_rule_returns_independent_nested_copy()
    print("PASS: 注册输入深层隔离")
    print("PASS: Registry 读取深层隔离")


def test_register_rule_rejects_non_dict_input() -> None:
    """Registry 必须明确拒绝非字典输入。"""
    from src.legal_rule_registry import list_rules

    invalid_inputs = [None, [], "not-a-rule", 123]
    before = set(list_rules())

    for invalid_rule in invalid_inputs:
        try:
            register_rule(invalid_rule)
        except ValueError:
            pass
        else:
            raise AssertionError(
                f"非字典规则应触发 ValueError：{invalid_rule!r}"
            )

    assert set(list_rules()) == before


def test_register_rule_rejects_invalid_rule_id() -> None:
    """rule_id 必须是非空字符串。"""
    from src.legal_rule_registry import list_rules

    invalid_ids = [None, "", "   ", 123, [], {}]
    before = set(list_rules())

    for index, invalid_id in enumerate(invalid_ids):
        rule = {
            "rule_id": invalid_id,
            "law_name": "输入校验测试法律",
            "article_number": f"第九十{index}条",
        }

        try:
            register_rule(rule)
        except ValueError:
            pass
        else:
            raise AssertionError(
                f"非法 rule_id 应触发 ValueError：{invalid_id!r}"
            )

    assert set(list_rules()) == before


def test_duplicate_registration_preserves_original_rule() -> None:
    """重复注册失败后，不得覆盖 Registry 中的原规则。"""
    from src.legal_rule_registry import list_rules

    rule_id = "RULE-TEST-DUPLICATE-REGISTRATION-PRESERVATION"

    try:
        get_rule(rule_id)
    except KeyError:
        pass
    else:
        raise AssertionError(f"测试规则已存在：{rule_id}")

    original_rule = {
        "rule_id": rule_id,
        "law_name": "原始法律",
        "article_number": "第九十九条",
        "conditions": ["原始条件"],
    }
    register_rule(original_rule)

    before = get_rule(rule_id)
    registry_ids_before = set(list_rules())

    duplicate_rule = {
        "rule_id": rule_id,
        "law_name": "试图覆盖的法律",
        "article_number": "第一条",
        "conditions": ["试图覆盖的条件"],
    }

    try:
        register_rule(duplicate_rule)
    except ValueError:
        pass
    else:
        raise AssertionError("重复注册应触发 ValueError")

    assert get_rule(rule_id) == before
    assert set(list_rules()) == registry_ids_before
