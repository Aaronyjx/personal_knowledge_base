from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Optional


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
# 以下 Canonical metadata 不进入当前 Runtime Rule：
#
#     legal_obligations
#     legal_consequences
#     references
#     priority
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
    }

    if rule_text is not None:
        runtime_rule["rule_text"] = deepcopy(
            rule_text
        )

    return runtime_rule
