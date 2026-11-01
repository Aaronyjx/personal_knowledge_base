# -*- coding: utf-8 -*-

"""
Canonical Rule Registry 启动校验测试。

验证内置 Article 14 规则只有通过 Canonical Definition Validator
后才能进入初始化结果。
"""

from typing import Any, Dict

import pytest

import src.legal_rule_registry as registry


def test_initial_registry_accepts_valid_canonical_definition(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Validator 明确通过时，应返回内置规则。"""
    definition: Dict[str, Any] = {
        "rule_id": registry.RULE_ID,
        "test_marker": "valid",
    }

    monkeypatch.setattr(
        registry,
        "build_article_14_definition",
        lambda: definition,
    )
    monkeypatch.setattr(
        registry,
        "validate_article_14_definition",
        lambda value: {"valid": True},
    )

    result = registry._build_initial_registry()

    assert result == {registry.RULE_ID: definition}
    assert result[registry.RULE_ID] is definition



def test_initial_registry_propagates_validator_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Validator 自身发生异常时，初始化不得继续。"""
    definition: Dict[str, Any] = {
        "rule_id": registry.RULE_ID,
        "test_marker": "validator-error",
    }

    def raise_validator_error(value: Dict[str, Any]) -> Dict[str, Any]:
        raise ValueError("测试用：Validator 内部异常")

    monkeypatch.setattr(
        registry,
        "build_article_14_definition",
        lambda: definition,
    )
    monkeypatch.setattr(
        registry,
        "validate_article_14_definition",
        raise_validator_error,
    )

    with pytest.raises(ValueError, match="Validator 内部异常"):
        registry._build_initial_registry()

def test_initial_registry_rejects_invalid_canonical_definition(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Validator 不通过时，必须抛出 RuntimeError。"""
    definition: Dict[str, Any] = {
        "rule_id": registry.RULE_ID,
        "test_marker": "invalid",
    }
    validation = {
        "valid": False,
        "errors": ["测试用：Canonical Definition 无效"],
    }

    monkeypatch.setattr(
        registry,
        "build_article_14_definition",
        lambda: definition,
    )
    monkeypatch.setattr(
        registry,
        "validate_article_14_definition",
        lambda value: validation,
    )

    with pytest.raises(RuntimeError, match="内置 Article 14 Canonical Rule 验证失败"):
        registry._build_initial_registry()
