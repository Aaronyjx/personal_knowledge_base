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

from src.legal_constants import (
    DEFINITE,
    CONDITIONAL,
    NOT_ESTABLISHED,
    REQUIRED,
    EXCLUSION,
    EXCEPTION,
    SATISFIED,
    NOT_SATISFIED,
    UNKNOWN,
)

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


VALID_ENGINE_DECISIONS = {
    DEFINITE,
    CONDITIONAL,
    NOT_ESTABLISHED,
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

    # 如果 Decision Engine 没有返回有效 Decision，
    # Adapter 不得擅自制造 CONDITIONAL。
    #
    # 返回空字符串，由调用方执行完整性检查。

    return ""

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
        mapping[condition] = REQUIRED

    for condition in _condition_list_from_rule(
        rules,
        ["exclusion_conditions", "exclusions"],
    ):
        mapping[condition] = EXCLUSION

    for condition in _condition_list_from_rule(
        rules,
        ["exceptions", "exception_conditions"],
    ):
        mapping[condition] = EXCEPTION

    return mapping

def build_fact_condition_mappings(
    decision: Any,
    rules: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    V7：Fact → Condition Mapping Formatter。

    本函数只负责：

    1. 读取 Decision Engine 已经产生的 ConditionResult。
    2. 读取 DecisionResult 中已经存在的结构化事实。
    3. 将结果格式化为 Prompt 所需的 Fact → Condition Mapping。

    本函数不负责：

    - 重新扫描 question
    - 重新抽取 LegalFacts
    - 根据 contract_sequence 推导法律条件
    - 判断 Article 14 条件
    - 创建新的法律事实
    - 创建新的 UNKNOWN
    - 修改 Decision Engine 的 ConditionResult

    V7 数据流：

        LegalFacts
            ↓
        Decision Engine
            ↓
        ConditionResult
            ↓
        DecisionResult
            ↓
        Adapter
            ↓
        Fact → Condition Mapping
            ↓
        legal_prompt.py

    Prompt 当前消费的字段保持不变：

        fact
        condition
        mapping_type
        dependency
    """

    if decision is None:
        return []

    condition_results = get_field(
        decision,
        "condition_results",
        None,
    )

    if not isinstance(condition_results, list):
        return []

    # V7 B-ready Fact Boundary：
    #
    # fact_condition_mappings["fact"] 只能表示
    # DecisionResult 中已经存在的 Explicit Facts。
    #
    # 不再使用 contract_sequence 构造新的事实文本。
    #
    # contract_sequence 属于结构化派生事实，
    # 保留在 DecisionResult 中供其他模块使用，
    # 但不能在 Adapter 层转换成看似用户原话的 fact。
    explicit_facts = get_field(
        decision,
        "explicit_facts",
        None,
    )

    if isinstance(explicit_facts, list):
        explicit_fact_texts = [
            normalize_text(fact)
            for fact in explicit_facts
            if normalize_text(fact)
        ]
        fact_text = "；".join(
            dict.fromkeys(explicit_fact_texts)
        )
    else:
        fact_text = ""

    mappings = []

    for result in condition_results:
        condition = normalize_text(
            get_field(
                result,
                "condition",
                "",
            )
        )

        if not condition:
            continue

        status = normalize_text(
            get_field(
                result,
                "status",
                UNKNOWN,
            )
        ).upper()

        reason = normalize_text(
            get_field(
                result,
                "reason",
                "",
            )
        )

        if status == SATISFIED:
            dependency = SATISFIED
        elif status == NOT_SATISFIED:
            dependency = NOT_SATISFIED
        else:
            dependency = UNKNOWN

        mapping = {
            "fact": fact_text,
            "condition": condition,
            "mapping_type": "CONDITION_RESULT",
            "dependency": dependency,
        }

        if reason:
            mapping["reason"] = reason

        mappings.append(mapping)

    return mappings

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

    # --------------------------------------------------------
    # 统一构建结构化法律规则
    # --------------------------------------------------------

    adapted_decision["rules"] = build_rules_from_articles(
        all_rules
    )

    return adapted_decision
