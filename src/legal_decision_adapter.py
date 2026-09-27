# -*- coding: utf-8 -*-

"""
RAG V6.1
Legal Decision Adapter

============================================================
功能
============================================================

负责将 Legal Decision Engine 的结果适配为后续
Answer Builder / Structured Context 所需要的数据结构。

职责：

    Legal Decision Engine
            ↓
    DecisionResult
            ↓
    Legal Decision Adapter
            ↓
    Structured Decision / Context
            ↓
    Legal Answer Builder

本模块只负责 Decision Adapter 层逻辑。

不负责：

    - Retriever
    - Legal Decision Engine 核心法律判断
    - Ollama / LLM
    - Deterministic User Facts
    - Deterministic Condition Analysis
    - Final Validation

============================================================
重要原则
============================================================

1. 不改变 Legal Decision Engine 的核心判断结果。

2. 不让 Adapter 自行进行新的法律推理。

3. 保留 REQUIRED / EXCLUSION / EXCEPTION
   等结构化条件分类。

4. 保留 UNKNOWN 状态。

5. 用户事实与法律规则继续严格区分。

============================================================
"""

from typing import Any, Dict, List

from src.retriever import build_context

from src.legal_common import (
    ensure_list,
    get_field,
    get_first_field,
    get_rule_value,
    normalize_text,
)

from src.legal_rule_builder import (
    build_rules_from_articles,
    prioritize_legal_rules,
)

from src.legal_rule_definition import (
    RULE_ID,
)

from src.legal_rule_registry import (
    get_rule,
)

from src.legal_answer_builder import (
    safe_text,
)


# ============================================================
# Legal Decision Engine 状态常量
# ============================================================

DECISION_DEFINITE = "DEFINITE"

DECISION_CONDITIONAL = "CONDITIONAL"

DECISION_NOT_ESTABLISHED = "NOT_ESTABLISHED"


VALID_ENGINE_DECISIONS = {
    DECISION_DEFINITE,
    DECISION_CONDITIONAL,
    DECISION_NOT_ESTABLISHED,
}


def extract_engine_decision(
    decision: Any,
) -> str:
    # 提取 Legal Decision Engine 状态。

    value = get_first_field(
        decision,
        [
            "decision",
            "status",
        ],
        "",
    )

    value = normalize_text(value).upper()

    if value in VALID_ENGINE_DECISIONS:
        return value

    # 如果 Decision Engine 没有明确返回状态，
    # 默认按照 CONDITIONAL 处理。
    #
    # 这样比擅自判断为 DEFINITE 更安全。

    return DECISION_CONDITIONAL

def extract_condition_value(
    condition: Any,
    name: str,
) -> Any:
    return get_field(
        condition,
        name,
        None,
    )

def extract_fact_text(
    fact: Any,
) -> str:
    # Fact 可能是字符串，也可能是对象。

    if fact is None:
        return ""

    if isinstance(fact, str):
        return fact.strip()

    value = (
        get_first_field(
            fact,
            [
                "text",
                "value",
                "fact",
                "content",
            ],
            None,
        )
    )

    if value is not None:
        return normalize_text(value)

    return normalize_text(
        safe_text(fact)
    )


def _condition_text(value: Any) -> str:
    """提取单个条件对象的规范文本。"""

    if isinstance(value, dict):
        return normalize_text(
            get_first_field(
                value,
                [
                    "condition",
                    "name",
                    "text",
                    "value",
                ],
                "",
            )
        )

    return normalize_text(value)

def _condition_list_from_rule(
    rules: List[Dict[str, Any]],
    field_names: List[str],
) -> List[str]:
    """从结构化 Rules 中提取条件名称，保持原始顺序并去重。"""

    result = []

    for rule in rules:
        if not isinstance(rule, dict):
            continue

        for field_name in field_names:
            values = ensure_list(rule.get(field_name, []))
            for value in values:
                text = _condition_text(value)
                if text and text not in result:
                    result.append(text)

    return result

def _condition_category_map(
    rules: List[Dict[str, Any]],
) -> Dict[str, str]:
    """
    建立条件名称 → 类别映射。

    类别严格来自 Structured Rules：

        REQUIRED   必备条件
        EXCLUSION  排除条件
        EXCEPTION  例外条件

    不根据自然语言问题自行创造类别。
    """

    mapping = {}

    for condition in _condition_list_from_rule(
        rules,
        ["conditions", "required_conditions"],
    ):
        mapping[condition] = "REQUIRED"

    for condition in _condition_list_from_rule(
        rules,
        ["exclusion_conditions", "exclusions"],
    ):
        mapping[condition] = "EXCLUSION"

    for condition in _condition_list_from_rule(
        rules,
        ["exceptions", "exception_conditions"],
    ):
        mapping[condition] = "EXCEPTION"

    return mapping

def build_fact_condition_mappings(
    decision: Any,
    rules: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    V6.1：Fact-to-Condition Mapping + Rule Dependency。

    核心原则：

    1. Legal Decision Engine 是唯一的事实抽取与法律条件判断来源。
    2. Adapter 不再重新扫描 question。
    3. Adapter 直接读取 DecisionResult.contract_sequence。
    4. “连续签订三次固定期限劳动合同”只能用于证明
       “连续订立二次固定期限劳动合同”的数量门槛。
    5. 不得由“三次合同”推导：
           - 续订劳动合同
           - 劳动者提出或者同意续订、订立劳动合同
           - 不存在第三十九条情形
           - 不存在第四十条第一、二项情形
           - 劳动者未提出订立固定期限劳动合同
    6. Mapping 只记录事实覆盖关系，不修改 Decision Engine 状态。

    V6.1 数据流：

        Question
            ↓
        extract_legal_facts()
            ↓
        LegalFacts
            ↓
        DecisionResult
            ↓
        Adapter
            ↓
        Fact → Condition Mapping
    """

    # --------------------------------------------------------
    # 1. 从 DecisionResult 获取 ContractSequence
    #
    # Decision Engine 已经完成唯一一次事实抽取。
    #
    # Adapter 禁止再次扫描 question。
    # --------------------------------------------------------

    contract_sequence = get_field(
        decision,
        "contract_sequence",
        None,
    )

    if contract_sequence is None:
        return []

    # --------------------------------------------------------
    # 2. 读取结构化合同序列
    # --------------------------------------------------------

    count = get_field(
        contract_sequence,
        "count",
        None,
    )

    term_type = normalize_text(
        get_field(
            contract_sequence,
            "term_type",
            "",
        )
    ).lower()

    continuous = get_field(
        contract_sequence,
        "continuous",
        None,
    )

    # --------------------------------------------------------
    # 3. 数量门槛判断
    #
    # 注意：
    #
    # 三次固定期限合同
    #     ↓
    # 达到“连续订立二次固定期限劳动合同”的数量门槛
    #
    # 但不代表：
    #
    #     续订已经发生
    #     劳动者已经同意下一次续订
    #     排除条件不存在
    #     例外条件不存在
    # --------------------------------------------------------

    try:
        contract_count = int(count)
    except (TypeError, ValueError):
        return []

    has_three_contract_fact = (
        contract_count >= 3
        and term_type == "fixed"
        and continuous is True
    )

    if not has_three_contract_fact:
        return []

    # --------------------------------------------------------
    # 4. 从 Structured Rules 中确认目标条件确实存在。
    #
    # Adapter 不自行创造 Condition。
    # --------------------------------------------------------

    normalized_rules = build_rules_from_articles(
        rules
    )

    canonical_rule = get_rule(RULE_ID)

    canonical_conditions = canonical_rule["conditions"]
    canonical_exclusion_conditions = (
        canonical_rule["exclusion_conditions"]
    )
    canonical_exception_conditions = (
        canonical_rule["exceptions"]
    )

    # ========================================================
    # V6.1：集中建立语义条件别名
    #
    # 条件来源仍然唯一来自 Canonical Rule Registry。
    # 这里不重新定义条件，也不改变条件顺序。
    #
    # 目的：
    #   将 positional coupling 集中在本映射区域，
    #   避免业务逻辑直接散落使用 canonical_conditions[N]。
    # ========================================================

    target_condition = canonical_conditions[0]

    renewal_condition = canonical_conditions[2]
    worker_agreement_condition = canonical_conditions[3]

    article_39_condition = canonical_exclusion_conditions[0]
    article_40_1_condition = canonical_exclusion_conditions[1]
    article_40_2_condition = canonical_exclusion_conditions[2]

    fixed_term_exception_condition = canonical_exception_conditions[0]

    for rule in normalized_rules:

        conditions = ensure_list(
            get_rule_value(
                rule,
                "conditions",
                "required_conditions",
            )
        )

        for item in conditions:

            if _condition_text(item) != target_condition:
                continue

            return [
                {
                    "fact": "公司连续签订三次固定期限劳动合同",
                    "condition": target_condition,
                    "mapping_type": "NUMERIC_THRESHOLD",
                    "dependency": (
                        "THREE_CONTRACTS_MEET_TWO_CONTRACT_THRESHOLD"
                    ),
                    "reason": (
                        "Decision Engine 的 LegalFacts 已明确记录"
                        "连续三次固定期限劳动合同；三次已经达到"
                        "连续订立二次固定期限劳动合同的最低数量门槛。"
                    ),
                    "does_not_prove": [
                        renewal_condition,
                        worker_agreement_condition,
                        article_39_condition,
                        article_40_1_condition,
                        article_40_2_condition,
                        fixed_term_exception_condition,
                    ],
                }
            ]

    return []

def merge_rules_into_decision(
    adapted_decision: Dict[str, Any],
    rules: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    将结构化法律规则合并到 Answer Builder 输出。

    RAG V6.1

    数据流：

        Retriever
            ↓
        rules
            ↓
        build_rules_from_articles()
            ↓
        Structured Legal Rules
            ↓
        adapted_decision["rules"]

    ========================================================
    重要设计原则
    ========================================================

    StructuredAnswer 中存在：

        legal_rules

    但：

        legal_rules

    是用于答案展示的法律依据文本，
    不是结构化 Rule。

    因此：

        legal_rules
            ×
        build_rules_from_articles()

    绝对不能再次执行。

    否则字符串形式的法律依据会被错误转换为：

        malformed rule

    ========================================================

    本函数只处理真正的结构化 Rule。
    """

    # --------------------------------------------------------
    # Decision Engine 可能保留已有的结构化 rules。
    #
    # 但当前 StructuredAnswer.to_dict() 中的：
    #
    #     legal_rules
    #
    # 是展示文本，不应进入这里。
    #
    # 因此这里只接受真正的 dict rule。
    # --------------------------------------------------------

    existing_rules = ensure_list(
        adapted_decision.get(
            "rules",
            [],
        )
    )

    structured_existing_rules = [
        rule
        for rule in existing_rules
        if isinstance(rule, dict)
    ]

    # --------------------------------------------------------
    # Retriever Rules
    # --------------------------------------------------------

    retriever_rules = [
        rule
        for rule in ensure_list(rules)
        if isinstance(rule, dict)
    ]

    # --------------------------------------------------------
    # 合并
    #
    # 当前 V6.0-27 的 Retriever 已经提供完整结构化法律依据。
    #
    # 因此：
    #
    #     existing structured rules
    #           +
    #     retriever rules
    #
    # 进行统一规范化。
    # --------------------------------------------------------

    all_rules = (
        structured_existing_rules
        + retriever_rules
    )

    print("\n" + "-" * 70)
    print("DEBUG / all_rules")
    print("-" * 70)
    print("all_rules type:", type(all_rules))
    print(
        "all_rules count:",
        len(all_rules)
        if isinstance(all_rules, (list, tuple, dict))
        else "N/A",
    )
    print("all_rules:", all_rules)

    # --------------------------------------------------------
    # 统一构建结构化法律规则
    # --------------------------------------------------------

    adapted_decision["rules"] = build_rules_from_articles(
        all_rules
    )

    print("\n" + "-" * 70)
    print("DEBUG / adapted_decision rules")
    print("-" * 70)
    print(
        "rules type:",
        type(adapted_decision.get("rules")),
    )
    print(
        "rules count:",
        len(adapted_decision.get("rules", [])),
    )
    print(
        "rules:",
        adapted_decision.get("rules"),
    )

    return adapted_decision
