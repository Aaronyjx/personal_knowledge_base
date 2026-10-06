# -*- coding: utf-8 -*-

"""
RAG V6.2
Canonical Legal Rule Registry

============================================================
职责
============================================================

本模块负责：

1. 注册 Canonical Legal Rule
2. 按 rule_id 获取 Canonical Rule
3. 列出当前已经注册的 Canonical Rule

本模块不负责：

- LegalFacts
- Fact Extraction
- Fact Matching
- ConditionResult
- DecisionResult
- Decision 计算
- Retriever
- Qdrant
- Ollama
- 最终法律答案

核心原则：

    legal_rule_definition.py
              ↓
       Canonical Rule
              ↓
       legal_rule_registry.py
              ↓
        Rule Lookup
              ↓
       Decision Engine

Registry 不复制 Rule 内容，只保存 Canonical Rule Definition
的引用。
============================================================
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List

from src.legal_rule_definition import (
    RULE_ID,
    build_article_14_definition,
)


# ============================================================
# Canonical Rule Registry
# ============================================================

_RULE_REGISTRY: Dict[str, Dict[str, Any]] = {
    RULE_ID: build_article_14_definition(),
}


# ============================================================
# Registry API
# ============================================================

def register_rule(rule: Dict[str, Any]) -> None:
    """
    注册一个 Canonical Rule。

    rule 必须包含唯一的 rule_id。
    """

    rule_id = rule.get("rule_id")

    if not rule_id:
        raise ValueError("Canonical Rule 缺少 rule_id")

    if rule_id in _RULE_REGISTRY:
        raise ValueError(
            f"Canonical Rule 已经注册：{rule_id}"
        )

    _RULE_REGISTRY[rule_id] = rule


def get_rule(rule_id: str) -> Dict[str, Any]:
    """
    根据 rule_id 获取 Canonical Rule。
    """

    if rule_id not in _RULE_REGISTRY:
        raise KeyError(
            f"Canonical Rule 不存在：{rule_id}"
        )

    return deepcopy(_RULE_REGISTRY[rule_id])


def list_rules() -> List[str]:
    """
    返回当前已经注册的 Rule ID。
    """

    return list(_RULE_REGISTRY.keys())


def find_rule_by_article(
    law_name: str,
    article_number: str,
) -> Dict[str, Any] | None:
    """
    根据法律名称和条文号查找 Canonical Rule。

    本函数只负责：

        Article Identity
            ↓
        Canonical Rule

    不负责：

    - Retriever
    - Rule Ranking
    - LegalFacts
    - Condition Matching
    - Decision

    匹配方式：

        law_name + article_number

    必须与 Canonical Rule 中的字段精确一致。

    找不到对应 Canonical Rule 时返回 None。

    返回值使用 deepcopy，
    防止调用方修改 Registry 内部对象。
    """

    for rule in _RULE_REGISTRY.values():

        if (
            rule.get("law_name") == law_name
            and rule.get("article_number") == article_number
        ):
            return deepcopy(rule)

    return None


# ============================================================
# Module Self Test
# ============================================================

def test_registry_isolation() -> None:
    """
    Registry 隔离回归测试。

    外部调用方获得的 Rule 必须是独立副本。
    修改返回对象不得污染 Registry 内部 Canonical Rule。
    """
    first = get_rule(RULE_ID)
    second = get_rule(RULE_ID)

    assert first is not second
    assert first["conditions"] is not second["conditions"]

    original_required = list(second["conditions"])
    original_exclusion = list(second["exclusion_conditions"])
    original_exception = list(second["exceptions"])

    first["conditions"].append("TEST_MUTATION")
    first["exclusion_conditions"].append("TEST_MUTATION")
    first["exceptions"].append("TEST_MUTATION")

    current = get_rule(RULE_ID)

    assert current["conditions"] == original_required
    assert current["exclusion_conditions"] == original_exclusion
    assert current["exceptions"] == original_exception


def main() -> None:
    """
    Canonical Rule Registry 自检。
    """

    print("=" * 70)
    print("RAG V6.2 Canonical Legal Rule Registry Test")
    print("=" * 70)

    rule_ids = list_rules()

    print()
    print("Registered Rules:", rule_ids)

    rule = get_rule(RULE_ID)

    print("Rule ID:", rule["rule_id"])
    print("Law:", rule["law_name"])
    print("Article:", rule["article_number"])
    print("Required:", len(rule["conditions"]))
    print("Exclusion:", len(rule["exclusion_conditions"]))
    print("Exception:", len(rule["exceptions"]))

    assert rule["rule_id"] == RULE_ID
    assert rule["conditions"] == build_article_14_definition()["conditions"]
    assert rule["exclusion_conditions"] == build_article_14_definition()["exclusion_conditions"]
    assert rule["exceptions"] == build_article_14_definition()["exceptions"]

    print()
    test_registry_isolation()
    print("PASS: Canonical Legal Rule Registry")


if __name__ == "__main__":
    main()
