from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Optional

from src.legal_rule_reference import (
    validate_rule_legal_references,
)


# ============================================================
# Canonical Rule → Runtime Rule Adapter
# ============================================================
#
# 职责：
#
#     Canonical Rule
#           ↓
#     Runtime Rule
#
# 本模块只负责：
#
# 1. Canonical Rule → Runtime Rule 的结构转换
# 2. 保留 Runtime Rule 当前执行所需字段
# 3. 深拷贝可变结构，避免 Runtime Rule 修改污染 Canonical Rule
# 4. 可选保留 Retriever 提供的 rule_text
#
# 本模块不负责：
#
# - Retriever Ranking
# - Rule Selection
# - LegalFacts
# - Condition Matching
# - Decision
# - RuleDependency
# - Ollama
# - Article 14 特殊业务逻辑
#
# Runtime Rule 最小契约：
#
#     rule_id
#     law_name
#     article
#     rule_name
#     conditions
#     exclusion_conditions
#     exceptions
#     condition_definitions
#
# Canonical Rule 中的：
#
#     article_number
#
# 映射为 Runtime Rule 的：
#
#     article
#
# Canonical metadata 处理规则：
#
#     legal_obligations：可选列表
#     legal_consequences：可选列表
#     references：可选结构化引用列表，提供时验证并保留
#     priority：不进入当前 Runtime Rule
#
# 其中：
#
#     rule_text
#
# 是可选 Runtime metadata。
# 如果调用方显式提供，则保留。
# ============================================================


_RUNTIME_RULE_REQUIRED_FIELDS = (
    "rule_id",
    "law_name",
    "article_number",
    "rule_name",
    "conditions",
    "exclusion_conditions",
    "exceptions",
    "condition_definitions",
    "fact_condition_relationships",
)


def _validate_canonical_rule(
    canonical_rule: Dict[str, Any],
) -> None:
    """
    验证输入是否满足 Canonical Rule 的最小结构要求。

    注意：
        这里只验证 Adapter 所需的结构，
        不执行 Article 14 专属 Canonical Rule 校验。
    """

    if not isinstance(canonical_rule, dict):
        raise TypeError(
            "Canonical Rule 必须是 dict"
        )

    missing_fields = [
        field
        for field in _RUNTIME_RULE_REQUIRED_FIELDS
        if field not in canonical_rule
    ]

    if missing_fields:
        raise ValueError(
            "Canonical Rule 缺少 Runtime Adapter 所需字段："
            + ", ".join(missing_fields)
        )


    # 必需的身份字段必须是非空字符串。
    string_fields = (
        "rule_id",
        "law_name",
        "article_number",
        "rule_name",
    )

    for field in string_fields:
        value = canonical_rule[field]

        if not isinstance(value, str):
            raise TypeError(
                f"Canonical Rule 字段 {field!r} 必须是 str"
            )

        if not value.strip():
            raise ValueError(
                f"Canonical Rule 字段 {field!r} 不能为空字符串"
            )

    # 必需的条件与关系字段必须是列表。
    list_fields = (
        "conditions",
        "exclusion_conditions",
        "exceptions",
        "condition_definitions",
        "fact_condition_relationships",
    )

    for field in list_fields:
        if not isinstance(canonical_rule[field], list):
            raise TypeError(
                f"Canonical Rule 字段 {field!r} 必须是 list"
            )

    # 可选字段：如果提供，则必须是列表。
    optional_list_fields = (
        "legal_obligations",
        "legal_consequences",
    )

    for field in optional_list_fields:
        if (
            field in canonical_rule
            and not isinstance(canonical_rule[field], list)
        ):
            raise TypeError(
                f"Canonical Rule 可选字段 {field!r} 必须是 list"
            )

    # references 是可选字段。
    # 一旦提供，必须是非空、合法且归属于当前规则的结构化引用列表。
    if "references" in canonical_rule:
        if not validate_rule_legal_references(
            canonical_rule["references"],
            expected_rule_id=canonical_rule["rule_id"],
        ):
            raise ValueError(
                "Canonical Rule references 必须是合法的结构化引用列表，"
                "且所有引用必须属于当前 rule_id"
            )


def canonical_rule_to_runtime_rule(
    canonical_rule: Dict[str, Any],
    rule_text: Optional[str] = None,
) -> Dict[str, Any]:
    """
    将 Canonical Rule 转换为 Runtime Rule。

    参数：
        canonical_rule:
            Canonical Rule Registry 返回的规则。

        rule_text:
            可选的 Retriever Rule Text。
            提供时写入 Runtime Rule。

    返回：
        独立的 Runtime Rule dict。

    设计原则：
        1. 不依赖具体 Rule ID
        2. 不依赖具体法律
        3. 不依赖具体 Article
        4. 不依赖固定条件数量
        5. 不加入 Article 14 专属 priority
        6. 不修改输入 Canonical Rule
    """

    _validate_canonical_rule(canonical_rule)

    runtime_rule: Dict[str, Any] = {
        "rule_id": deepcopy(
            canonical_rule["rule_id"]
        ),
        "law_name": deepcopy(
            canonical_rule["law_name"]
        ),
        "article": deepcopy(
            canonical_rule["article_number"]
        ),
        "rule_name": deepcopy(
            canonical_rule["rule_name"]
        ),
        "conditions": deepcopy(
            canonical_rule["conditions"]
        ),
        "exclusion_conditions": deepcopy(
            canonical_rule["exclusion_conditions"]
        ),
        "exceptions": deepcopy(
            canonical_rule["exceptions"]
        ),
        "condition_definitions": deepcopy(
            canonical_rule["condition_definitions"]
        ),
        "fact_condition_relationships": deepcopy(
            canonical_rule["fact_condition_relationships"]
        ),
        "legal_obligations": deepcopy(
            canonical_rule.get(
                "legal_obligations",
                [],
            )
        ),
        "legal_consequences": deepcopy(
            canonical_rule.get(
                "legal_consequences",
                [],
            )
        ),
    }

    # 保留经过验证的结构化法律引用。
    # 只有 Canonical Rule 提供该字段时才加入 Runtime Rule。
    if "references" in canonical_rule:
        runtime_rule["references"] = deepcopy(
            canonical_rule["references"]
        )

    if rule_text is not None:
        runtime_rule["rule_text"] = deepcopy(
            rule_text
        )

    return runtime_rule
