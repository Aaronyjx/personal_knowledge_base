# -*- coding: utf-8 -*-

"""
RAG V6.2
Canonical Legal Rule Definition

============================================================
职责
============================================================

本模块负责：

1. 定义法律规则的 Canonical Definition
2. 为不同模块提供统一的法律条件定义
3. 消除 Retriever 与 Decision Engine 之间的规则定义漂移
4. 保存 Article 14 的核心法律效果与引用信息

本模块不负责：

- LegalFacts
- Fact Extraction
- Fact Matching
- ConditionResult
- DecisionResult
- 条件判断
- Decision 计算
- Ollama
- 最终法律答案

核心原则：

    Canonical Rule Definition
              ↓
       ┌──────┴──────┐
       ↓             ↓
   Retriever   Decision Rules
                     ↓
             Legal Decision Engine
                     ↓
              ConditionResult
                     ↓
               DecisionResult

============================================================
重要设计原则
============================================================

本模块是法律规则定义的 Single Source of Truth。

特别是 Article 14 的：

- REQUIRED conditions
- EXCLUSION conditions
- EXCEPTION conditions

必须在本模块中只有一份定义。

V6.1 冻结的 Decision Engine 语义保持不变：

REQUIRED × 4
EXCLUSION × 3
EXCEPTION × 1

本模块只定义规则，不执行法律推理。
============================================================
"""

from __future__ import annotations

from typing import Any, Dict


# ============================================================
# 基础法律身份
# ============================================================

RULE_ID = "RULE-001"

LABOR_CONTRACT_LAW = "中华人民共和国劳动合同法"

LABOR_CONTRACT_LAW_ARTICLE_14 = "第十四条"

IMPLEMENTING_REGULATIONS = (
    "中华人民共和国劳动合同法实施条例"
)


# ============================================================
# Article 14 REQUIRED Conditions
# ============================================================
#
# 注意：
#
# 这里采用 V6.1 Decision Engine 已冻结的四项 REQUIRED
# 条件。
#
# 不使用 Retriever 当前旧版的三项定义。
#
# 第 2 项：
#
#     存在后续订立的劳动合同
#
# 是当前 Decision Engine 判定边界的一部分。
# ============================================================

REQUIRED_CONDITIONS = [
    "连续订立二次固定期限劳动合同",
    "存在后续订立的劳动合同",
    "续订劳动合同",
    "劳动者提出或者同意续订、订立劳动合同",
]


# ============================================================
# Article 14 EXCLUSION Conditions
# ============================================================

EXCLUSION_CONDITIONS = [
    "劳动者存在《劳动合同法》第三十九条规定的情形",
    "劳动者存在《劳动合同法》第四十条第一项规定的情形",
    "劳动者存在《劳动合同法》第四十条第二项规定的情形",
]


# ============================================================
# Article 14 EXCEPTION Conditions
# ============================================================

EXCEPTION_CONDITIONS = [
    "劳动者提出订立固定期限劳动合同",
]


# ============================================================
# Article 14 Stable Condition Identity
# ============================================================
#
# V6.2 新增：
#
# condition_id 是机器稳定身份。
#
# 重要原则：
#
# 1. condition_id 不替代原有 condition 文本
# 2. REQUIRED_CONDITIONS 等 List[str] 保持 V6.1 兼容
# 3. condition_id 不依赖列表位置
# 4. 下游模块暂时不需要修改
# 5. 本层仍然是唯一 Canonical Source
#
# 后续 V6.2 将逐步把 condition_id 传播到：
#
#     ConditionResult
#          ↓
#     DecisionResult
#          ↓
#     Answer Builder / Validator
#
# ============================================================

REQUIRED_CONDITION_IDS = [
    "ARTICLE-14-REQUIRED-001",
    "ARTICLE-14-REQUIRED-002",
    "ARTICLE-14-REQUIRED-003",
    "ARTICLE-14-REQUIRED-004",
]

EXCLUSION_CONDITION_IDS = [
    "ARTICLE-14-EXCLUSION-001",
    "ARTICLE-14-EXCLUSION-002",
    "ARTICLE-14-EXCLUSION-003",
]

EXCEPTION_CONDITION_IDS = [
    "ARTICLE-14-EXCEPTION-001",
]


# ============================================================
# Canonical Condition Definitions
# ============================================================
#
# 注意：
#
# condition 文本仍然来自上面的 Canonical Condition Lists。
#
# 这里增加的是稳定机器身份，而不是第二套法律条件文本。
#
# ============================================================

def build_article_14_condition_definitions() -> list[Dict[str, str]]:
    """
    构建 Article 14 的 Stable Condition Identity Metadata。

    本函数只建立：
        condition_id
        condition
        condition_type

    不执行法律推理。
    """

    definitions = []

    for condition_id, condition in zip(
        REQUIRED_CONDITION_IDS,
        REQUIRED_CONDITIONS,
    ):
        definitions.append(
            {
                "condition_id": condition_id,
                "condition": condition,
                "condition_type": "REQUIRED",
            }
        )

    for condition_id, condition in zip(
        EXCLUSION_CONDITION_IDS,
        EXCLUSION_CONDITIONS,
    ):
        definitions.append(
            {
                "condition_id": condition_id,
                "condition": condition,
                "condition_type": "EXCLUSION",
            }
        )

    for condition_id, condition in zip(
        EXCEPTION_CONDITION_IDS,
        EXCEPTION_CONDITIONS,
    ):
        definitions.append(
            {
                "condition_id": condition_id,
                "condition": condition,
                "condition_type": "EXCEPTION",
            }
        )

    return definitions


# ============================================================
# Stable Condition Identity Validation
# ============================================================

def validate_article_14_condition_identity() -> Dict[str, Any]:
    """
    验证 Article 14 Stable Condition Identity 的完整性。

    本函数只验证：
        condition_id
        condition
        condition_type

    三者之间的一致性。

    不执行法律推理。
    """

    definitions = build_article_14_condition_definitions()

    expected_conditions = (
        [
            (condition_id, condition, "REQUIRED")
            for condition_id, condition in zip(
                REQUIRED_CONDITION_IDS,
                REQUIRED_CONDITIONS,
            )
        ]
        + [
            (condition_id, condition, "EXCLUSION")
            for condition_id, condition in zip(
                EXCLUSION_CONDITION_IDS,
                EXCLUSION_CONDITIONS,
            )
        ]
        + [
            (condition_id, condition, "EXCEPTION")
            for condition_id, condition in zip(
                EXCEPTION_CONDITION_IDS,
                EXCEPTION_CONDITIONS,
            )
        ]
    )

    actual_conditions = [
        (
            item["condition_id"],
            item["condition"],
            item["condition_type"],
        )
        for item in definitions
    ]

    ids = [
        item["condition_id"]
        for item in definitions
    ]

    return {
        "valid": (
            actual_conditions == expected_conditions
            and len(definitions) == 8
            and len(set(ids)) == 8
        ),
        "definition_count": len(definitions),
        "unique_id_count": len(set(ids)),
        "expected_count": len(expected_conditions),
    }


# ============================================================
# All Article 14 Conditions
# ============================================================

ALL_CONDITIONS = (
    REQUIRED_CONDITIONS
    + EXCLUSION_CONDITIONS
    + EXCEPTION_CONDITIONS
)


# ============================================================
# Article 14 Legal Obligations
# ============================================================

LEGAL_OBLIGATIONS = [
    "用人单位应当订立无固定期限劳动合同",
]


# ============================================================
# Article 14 Legal Consequences
# ============================================================

LEGAL_CONSEQUENCES = [
    "符合第十四条规定条件时，用人单位应当订立无固定期限劳动合同",
]


# ============================================================
# Article 14 References
# ============================================================

ARTICLE_14_REFERENCES = [
    "第十四条",
    "第三十九条",
    "第四十条",
    "第四十条第一项",
    "第四十条第二项",
]


# ============================================================
# V7 Fact → Condition Relationship Definition
# ============================================================
#
# 本层定义：
#
#     LegalFacts
#          ↓
#       Predicate
#          ↓
#       Condition
#          ↓
#        Status
#
# 本函数只定义 Canonical Legal Knowledge，
# 不读取用户事实，不执行事实匹配。
#
# Predicate operator 冻结为：
#
#     ==
#     >=
#
# 多个 predicate_groups 表示 OR。
#
# 一个 group 内的 predicates 使用 AND。
#
# None 不作为 Predicate。
#
# 事实缺失由 Decision Engine 解释为 UNKNOWN。
# ============================================================

def build_article_14_fact_condition_relationships() -> list[Dict[str, Any]]:
    """
    构建 Article 14 的 Canonical Fact → Condition Relationships。

    本函数只定义法律规则关系，不执行事实判断。
    """

    return [

        # ====================================================
        # REQUIRED-001
        #
        # 连续订立二次固定期限劳动合同
        #
        # count >= 2
        # term_type == fixed
        # continuous == True
        # ====================================================

        {
            "relationship_id": (
                "ARTICLE-14-REL-REQUIRED-001-001"
            ),
            "condition_id": (
                "ARTICLE-14-REQUIRED-001"
            ),
            "predicate_groups": [
                {
                    "match": "ALL",
                    "predicates": [
                        {
                            "fact_key": (
                                "contract_sequence.count"
                            ),
                            "operator": ">=",
                            "value": 2,
                        },
                        {
                            "fact_key": (
                                "contract_sequence.term_type"
                            ),
                            "operator": "==",
                            "value": "fixed",
                        },
                        {
                            "fact_key": (
                                "contract_sequence.continuous"
                            ),
                            "operator": "==",
                            "value": True,
                        },
                    ],
                },
            ],
            "relationship_type": "PROVES_TRUE",
            "result_status": "SATISFIED",
            "reason": (
                "连续固定期限劳动合同数量达到二次"
                "且合同连续时，可以证明该 REQUIRED 条件。"
            ),
        },

        # ====================================================
        # REQUIRED-002
        #
        # 存在后续订立的劳动合同
        #
        # Group 1：
        #     count >= 3
        #     term_type == fixed
        #
        # OR
        #
        # Group 2：
        #     completed_renewal == True
        # ====================================================

        {
            "relationship_id": (
                "ARTICLE-14-REL-REQUIRED-002-001"
            ),
            "condition_id": (
                "ARTICLE-14-REQUIRED-002"
            ),
            "predicate_groups": [
                {
                    "match": "ALL",
                    "predicates": [
                        {
                            "fact_key": (
                                "contract_sequence.count"
                            ),
                            "operator": ">=",
                            "value": 3,
                        },
                        {
                            "fact_key": (
                                "contract_sequence.term_type"
                            ),
                            "operator": "==",
                            "value": "fixed",
                        },
                    ],
                },
                {
                    "match": "ALL",
                    "predicates": [
                        {
                            "fact_key": (
                                "completed_renewal"
                            ),
                            "operator": "==",
                            "value": True,
                        },
                    ],
                },
            ],
            "relationship_type": "PROVES_TRUE",
            "result_status": "SATISFIED",
            "reason": (
                "连续固定期限劳动合同达到三次，"
                "或者已经明确完成续订时，"
                "可以证明存在后续订立的劳动合同。"
            ),
        },

        # ====================================================
        # REQUIRED-003
        #
        # 续订劳动合同
        # ====================================================

        {
            "relationship_id": (
                "ARTICLE-14-REL-REQUIRED-003-001"
            ),
            "condition_id": (
                "ARTICLE-14-REQUIRED-003"
            ),
            "predicate_groups": [
                {
                    "match": "ALL",
                    "predicates": [
                        {
                            "fact_key": (
                                "completed_renewal"
                            ),
                            "operator": "==",
                            "value": True,
                        },
                    ],
                },
            ],
            "relationship_type": "PROVES_TRUE",
            "result_status": "SATISFIED",
            "reason": (
                "明确完成续订可以证明已经续订劳动合同。"
            ),
        },

        {
            "relationship_id": (
                "ARTICLE-14-REL-REQUIRED-003-002"
            ),
            "condition_id": (
                "ARTICLE-14-REQUIRED-003"
            ),
            "predicate_groups": [
                {
                    "match": "ALL",
                    "predicates": [
                        {
                            "fact_key": (
                                "contract_sequence.count"
                            ),
                            "operator": ">=",
                            "value": 3,
                        },
                    ],
                },
            ],
            "relationship_type": "DOES_NOT_PROVE",
            "result_status": "UNKNOWN",
            "reason": (
                "合同数量达到三次本身不能证明"
                "已经完成续订劳动合同。"
            ),
        },

        # ====================================================
        # REQUIRED-004
        #
        # 劳动者提出或者同意续订、订立劳动合同
        # ====================================================

        {
            "relationship_id": (
                "ARTICLE-14-REL-REQUIRED-004-001"
            ),
            "condition_id": (
                "ARTICLE-14-REQUIRED-004"
            ),
            "predicate_groups": [
                {
                    "match": "ALL",
                    "predicates": [
                        {
                            "fact_key": (
                                "worker_agreement"
                            ),
                            "operator": "==",
                            "value": True,
                        },
                    ],
                },
            ],
            "relationship_type": "PROVES_TRUE",
            "result_status": "SATISFIED",
            "reason": (
                "明确记录劳动者提出或者同意续订、"
                "订立劳动合同时，可以证明该 REQUIRED 条件。"
            ),
        },

        {
            "relationship_id": (
                "ARTICLE-14-REL-REQUIRED-004-002"
            ),
            "condition_id": (
                "ARTICLE-14-REQUIRED-004"
            ),
            "predicate_groups": [
                {
                    "match": "ALL",
                    "predicates": [
                        {
                            "fact_key": (
                                "contract_sequence.count"
                            ),
                            "operator": ">=",
                            "value": 2,
                        },
                    ],
                },
            ],
            "relationship_type": "DOES_NOT_PROVE",
            "result_status": "UNKNOWN",
            "reason": (
                "合同数量达到二次本身不能证明"
                "劳动者已经提出或者同意续订、订立劳动合同。"
            ),
        },

        # ====================================================
        # EXCLUSION-001
        # ====================================================

        {
            "relationship_id": (
                "ARTICLE-14-REL-EXCLUSION-001-001"
            ),
            "condition_id": (
                "ARTICLE-14-EXCLUSION-001"
            ),
            "predicate_groups": [
                {
                    "match": "ALL",
                    "predicates": [
                        {
                            "fact_key": "article_39",
                            "operator": "==",
                            "value": True,
                        },
                    ],
                },
            ],
            "relationship_type": "PROVES_TRUE",
            "result_status": "SATISFIED",
            "reason": (
                "明确存在《劳动合同法》第三十九条规定情形时，"
                "该 EXCLUSION 条件成立。"
            ),
        },

        {
            "relationship_id": (
                "ARTICLE-14-REL-EXCLUSION-001-002"
            ),
            "condition_id": (
                "ARTICLE-14-EXCLUSION-001"
            ),
            "predicate_groups": [
                {
                    "match": "ALL",
                    "predicates": [
                        {
                            "fact_key": "article_39",
                            "operator": "==",
                            "value": False,
                        },
                    ],
                },
            ],
            "relationship_type": "PROVES_FALSE",
            "result_status": "NOT_SATISFIED",
            "reason": (
                "明确不存在《劳动合同法》第三十九条规定情形时，"
                "该 EXCLUSION 条件不成立。"
            ),
        },

        # ====================================================
        # EXCLUSION-002
        # ====================================================

        {
            "relationship_id": (
                "ARTICLE-14-REL-EXCLUSION-002-001"
            ),
            "condition_id": (
                "ARTICLE-14-EXCLUSION-002"
            ),
            "predicate_groups": [
                {
                    "match": "ALL",
                    "predicates": [
                        {
                            "fact_key": "article_40_1",
                            "operator": "==",
                            "value": True,
                        },
                    ],
                },
            ],
            "relationship_type": "PROVES_TRUE",
            "result_status": "SATISFIED",
            "reason": (
                "明确存在《劳动合同法》第四十条第一项规定情形时，"
                "该 EXCLUSION 条件成立。"
            ),
        },

        {
            "relationship_id": (
                "ARTICLE-14-REL-EXCLUSION-002-002"
            ),
            "condition_id": (
                "ARTICLE-14-EXCLUSION-002"
            ),
            "predicate_groups": [
                {
                    "match": "ALL",
                    "predicates": [
                        {
                            "fact_key": "article_40_1",
                            "operator": "==",
                            "value": False,
                        },
                    ],
                },
            ],
            "relationship_type": "PROVES_FALSE",
            "result_status": "NOT_SATISFIED",
            "reason": (
                "明确不存在《劳动合同法》第四十条第一项规定情形时，"
                "该 EXCLUSION 条件不成立。"
            ),
        },

        # ====================================================
        # EXCLUSION-003
        # ====================================================

        {
            "relationship_id": (
                "ARTICLE-14-REL-EXCLUSION-003-001"
            ),
            "condition_id": (
                "ARTICLE-14-EXCLUSION-003"
            ),
            "predicate_groups": [
                {
                    "match": "ALL",
                    "predicates": [
                        {
                            "fact_key": "article_40_2",
                            "operator": "==",
                            "value": True,
                        },
                    ],
                },
            ],
            "relationship_type": "PROVES_TRUE",
            "result_status": "SATISFIED",
            "reason": (
                "明确存在《劳动合同法》第四十条第二项规定情形时，"
                "该 EXCLUSION 条件成立。"
            ),
        },

        {
            "relationship_id": (
                "ARTICLE-14-REL-EXCLUSION-003-002"
            ),
            "condition_id": (
                "ARTICLE-14-EXCLUSION-003"
            ),
            "predicate_groups": [
                {
                    "match": "ALL",
                    "predicates": [
                        {
                            "fact_key": "article_40_2",
                            "operator": "==",
                            "value": False,
                        },
                    ],
                },
            ],
            "relationship_type": "PROVES_FALSE",
            "result_status": "NOT_SATISFIED",
            "reason": (
                "明确不存在《劳动合同法》第四十条第二项规定情形时，"
                "该 EXCLUSION 条件不成立。"
            ),
        },

        # ====================================================
        # EXCEPTION-001
        # ====================================================

        {
            "relationship_id": (
                "ARTICLE-14-REL-EXCEPTION-001-001"
            ),
            "condition_id": (
                "ARTICLE-14-EXCEPTION-001"
            ),
            "predicate_groups": [
                {
                    "match": "ALL",
                    "predicates": [
                        {
                            "fact_key": (
                                "fixed_term_exception"
                            ),
                            "operator": "==",
                            "value": True,
                        },
                    ],
                },
            ],
            "relationship_type": "PROVES_TRUE",
            "result_status": "SATISFIED",
            "reason": (
                "明确劳动者提出订立固定期限劳动合同时，"
                "该 EXCEPTION 条件成立。"
            ),
        },

        {
            "relationship_id": (
                "ARTICLE-14-REL-EXCEPTION-001-002"
            ),
            "condition_id": (
                "ARTICLE-14-EXCEPTION-001"
            ),
            "predicate_groups": [
                {
                    "match": "ALL",
                    "predicates": [
                        {
                            "fact_key": (
                                "fixed_term_exception"
                            ),
                            "operator": "==",
                            "value": False,
                        },
                    ],
                },
            ],
            "relationship_type": "PROVES_FALSE",
            "result_status": "NOT_SATISFIED",
            "reason": (
                "明确劳动者未提出订立固定期限劳动合同时，"
                "该 EXCEPTION 条件不成立。"
            ),
        },
    ]


# ============================================================
# V7 Fact → Condition Relationship Validation
# ============================================================

def validate_article_14_fact_condition_relationships() -> Dict[str, Any]:
    """
    验证 Article 14 Fact → Condition Relationship Schema。

    只验证 Canonical Relationship Definition 的结构，
    不执行任何用户事实判断。
    """

    relationships = (
        build_article_14_fact_condition_relationships()
    )

    valid_condition_ids = set(
        REQUIRED_CONDITION_IDS
        + EXCLUSION_CONDITION_IDS
        + EXCEPTION_CONDITION_IDS
    )

    valid_relationship_types = {
        "PROVES_TRUE",
        "PROVES_FALSE",
        "DOES_NOT_PROVE",
    }

    valid_result_statuses = {
        "SATISFIED",
        "NOT_SATISFIED",
        "UNKNOWN",
    }

    valid_operators = {
        "==",
        ">=",
    }

    relationship_ids = []
    covered_condition_ids = set()

    valid = isinstance(
        relationships,
        list,
    )

    if valid:

        for relationship in relationships:

            if not isinstance(
                relationship,
                dict,
            ):
                valid = False
                break

            required_keys = {
                "relationship_id",
                "condition_id",
                "predicate_groups",
                "relationship_type",
                "result_status",
                "reason",
            }

            if not required_keys.issubset(
                relationship.keys()
            ):
                valid = False
                break

            relationship_id = (
                relationship["relationship_id"]
            )

            condition_id = (
                relationship["condition_id"]
            )

            predicate_groups = (
                relationship["predicate_groups"]
            )

            relationship_type = (
                relationship["relationship_type"]
            )

            result_status = (
                relationship["result_status"]
            )

            relationship_ids.append(
                relationship_id
            )

            covered_condition_ids.add(
                condition_id
            )

            if (
                not isinstance(
                    relationship_id,
                    str,
                )
                or not relationship_id
            ):
                valid = False
                break

            if condition_id not in valid_condition_ids:
                valid = False
                break

            if (
                not isinstance(
                    predicate_groups,
                    list,
                )
                or not predicate_groups
            ):
                valid = False
                break

            if (
                relationship_type
                not in valid_relationship_types
            ):
                valid = False
                break

            if (
                result_status
                not in valid_result_statuses
            ):
                valid = False
                break

            if (
                relationship_type
                == "PROVES_TRUE"
                and result_status != "SATISFIED"
            ):
                valid = False
                break

            if (
                relationship_type
                == "PROVES_FALSE"
                and result_status != "NOT_SATISFIED"
            ):
                valid = False
                break

            if (
                relationship_type
                == "DOES_NOT_PROVE"
                and result_status != "UNKNOWN"
            ):
                valid = False
                break

            for group in predicate_groups:

                if not isinstance(
                    group,
                    dict,
                ):
                    valid = False
                    break

                if group.get("match") != "ALL":
                    valid = False
                    break

                predicates = group.get(
                    "predicates"
                )

                if (
                    not isinstance(
                        predicates,
                        list,
                    )
                    or not predicates
                ):
                    valid = False
                    break

                for predicate in predicates:

                    if not isinstance(
                        predicate,
                        dict,
                    ):
                        valid = False
                        break

                    predicate_keys = {
                        "fact_key",
                        "operator",
                        "value",
                    }

                    if not predicate_keys.issubset(
                        predicate.keys()
                    ):
                        valid = False
                        break

                    fact_key = predicate[
                        "fact_key"
                    ]

                    operator = predicate[
                        "operator"
                    ]

                    if (
                        not isinstance(
                            fact_key,
                            str,
                        )
                        or not fact_key
                    ):
                        valid = False
                        break

                    if operator not in valid_operators:
                        valid = False
                        break

                if not valid:
                    break

            if not valid:
                break

    unique_relationship_id_count = len(
        set(relationship_ids)
    )

    expected_condition_count = 8

    return {
        "valid": (
            valid
            and len(relationship_ids)
            == unique_relationship_id_count
            and len(covered_condition_ids)
            == expected_condition_count
            and covered_condition_ids
            == valid_condition_ids
        ),
        "relationship_count": len(
            relationships
        ),
        "unique_relationship_id_count": (
            unique_relationship_id_count
        ),
        "covered_condition_count": len(
            covered_condition_ids
        ),
        "expected_condition_count": (
            expected_condition_count
        ),
    }


# ============================================================
# Canonical Rule Builder
# ============================================================

def build_article_14_definition() -> Dict[str, Any]:
    """
    构建《劳动合同法》第十四条 Canonical Rule Definition。

    本函数只负责返回法律规则定义。

    不读取用户事实。
    不判断条件。
    不生成 ConditionResult。
    不计算 DecisionResult。
    """

    return {
        "rule_id": RULE_ID,
        "law_name": LABOR_CONTRACT_LAW,
        "article_number": LABOR_CONTRACT_LAW_ARTICLE_14,

        "rule_name": (
            "连续订立固定期限劳动合同后"
            "订立无固定期限劳动合同"
        ),

        "conditions": list(REQUIRED_CONDITIONS),

        "exclusion_conditions": list(
            EXCLUSION_CONDITIONS
        ),

        "exceptions": list(
            EXCEPTION_CONDITIONS
        ),

        # V6.2 Stable Condition Identity。
        #
        # 保留上面的三个 List[str] 字段，
        # 供 V6.1 下游模块继续使用。
        "condition_definitions": (
            build_article_14_condition_definitions()
        ),

        # V7 Canonical Fact → Condition Relationships。
        #
        # 该字段独立于 condition_definitions。
        # condition_definitions 只负责 Condition Identity；
        # relationship 则负责 Fact → Predicate → Condition。
        "fact_condition_relationships": (
            build_article_14_fact_condition_relationships()
        ),

        "legal_obligations": list(
            LEGAL_OBLIGATIONS
        ),

        "legal_consequences": list(
            LEGAL_CONSEQUENCES
        ),

        "references": list(
            ARTICLE_14_REFERENCES
        ),
    }


# ============================================================
# Definition Validation
# ============================================================

def validate_article_14_definition() -> Dict[str, Any]:
    """
    验证 Canonical Article 14 Rule Definition 的基本结构。

    本函数只验证规则定义本身，不执行法律判断。
    """

    definition = build_article_14_definition()

    required = definition["conditions"]
    exclusions = definition["exclusion_conditions"]
    exceptions = definition["exceptions"]

    all_conditions = (
        required
        + exclusions
        + exceptions
    )

    condition_identity_validation = (
        validate_article_14_condition_identity()
    )

    relationship_validation = (
        validate_article_14_fact_condition_relationships()
    )

    return {
        "valid": (
            len(required) == 4
            and len(exclusions) == 3
            and len(exceptions) == 1
            and len(all_conditions) == 8
            and len(set(all_conditions)) == 8
            and bool(definition["law_name"])
            and bool(definition["article_number"])
            and bool(definition["legal_obligations"])
            and bool(definition["legal_consequences"])
            and bool(definition["references"])
            and condition_identity_validation["valid"]
            and relationship_validation["valid"]
        ),
        "required_count": len(required),
        "exclusion_count": len(exclusions),
        "exception_count": len(exceptions),
        "condition_count": len(all_conditions),
        "unique_condition_count": len(
            set(all_conditions)
        ),
        "condition_identity": (
            condition_identity_validation
        ),
        "fact_condition_relationships": (
            relationship_validation
        ),
    }


# ============================================================
# Module Self Test
# ============================================================

def main() -> None:
    """
    Canonical Rule Definition 自检。
    """

    print("=" * 70)
    print("RAG V6.2 Canonical Rule Definition Test")
    print("=" * 70)

    definition = build_article_14_definition()

    validation = validate_article_14_definition()

    print()
    print("Law:", definition["law_name"])
    print("Article:", definition["article_number"])
    print()
    print("REQUIRED:", len(definition["conditions"]))
    print("EXCLUSION:", len(
        definition["exclusion_conditions"]
    ))
    print("EXCEPTION:", len(
        definition["exceptions"]
    ))
    print()

    for index, condition in enumerate(
        definition["conditions"],
        start=1,
    ):
        print(
            f"REQUIRED {index}: {condition}"
        )

    print()

    for index, condition in enumerate(
        definition["exclusion_conditions"],
        start=1,
    ):
        print(
            f"EXCLUSION {index}: {condition}"
        )

    print()

    for index, condition in enumerate(
        definition["exceptions"],
        start=1,
    ):
        print(
            f"EXCEPTION {index}: {condition}"
        )

    print()
    print("Validation:", validation)

    if validation["valid"]:
        print()
        print("PASS: Canonical Article 14 Rule Definition")
    else:
        print()
        print("FAIL: Canonical Article 14 Rule Definition")


if __name__ == "__main__":
    main()
