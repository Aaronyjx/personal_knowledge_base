# -*- coding: utf-8 -*-

"""
RAG V6.0-7
Legal Answer Builder

============================================================
功能
============================================================

1. 接收 V6.0-10 Legal Decision Engine 的标准决策结果
2. 接收 Retriever / Rule Context
3. 将结构化法律决策转换为最终法律回答
4. 严格区分：

       SATISFIED
       NOT_SATISFIED
       UNKNOWN

       DEFINITE
       CONDITIONAL
       NOT_ESTABLISHED

5. 严格区分法律条件类别：

       REQUIRED
       EXCLUSION
       EXCEPTION

6. 自动生成：

       【结论】
       【法律依据】
       【法律分析】
       【需要注意】

7. 禁止修改用户事实

8. 禁止把“三次”改写成“两次”

9. 禁止把 UNKNOWN 条件当成已经发生的事实

10. 禁止把 EXCLUSION 条件错误地当成普通必须满足条件

11. 禁止把 EXCEPTION 错误地加入 UNKNOWN 条件

12. 禁止在事实不足时给出绝对结论

13. 禁止引用 Context 中不存在的法律内容

14. 完整保留 Decision Engine 的条件结果

15. 支持：

       conditions
       required_conditions
       exclusion_conditions
       exceptions
       condition_results

16. 支持：

       rules
       structured_rule
       legal_basis

17. 为后续 Ollama 最终回答提供结构化 Prompt

============================================================
V6.0-7 核心修复
============================================================

V6.0-6 的问题：

    conditions
        ↓
    所有条件扁平化
        ↓
    UNKNOWN
        ↓
    Answer Builder

导致：

    exclusion_conditions
        被当成普通 UNKNOWN

以及：

    exceptions
        被错误加入 UNKNOWN

V6.0-7 改为：

    Required Conditions
        ↓
    Exclusion Conditions
        ↓
    Exceptions

分别处理。

============================================================
核心原则
============================================================

Retriever
    ↓
Structured Rules
    ↓
Decision Engine
    ↓
DecisionResult
    ↓
Answer Builder
    ↓
Ollama
    ↓
Final Validation

注意：

Legal Answer Builder 不负责重新判断法律。

法律判断仍然由：

    legal_decision_engine.py

负责。

本模块只负责：

    Decision
        ↓
    结构化表达
        ↓
    可读法律回答

============================================================
V6.0-7 接口原则
============================================================

标准字段：

    decision
    conclusion
    facts
    conditions
    required_conditions
    exclusion_conditions
    exceptions
    condition_results

    satisfied_conditions
    not_satisfied_conditions
    unknown_conditions

    rules

兼容字段：

    user_facts
    satisfied
    unsatisfied
    unknown

以及：

    structured_rule
    rule
    legal_basis

============================================================
重要说明
============================================================

本模块不会因为看到：

    “连续签订三次固定期限劳动合同”

就自行作出：

    “必须签订无固定期限劳动合同”

而是严格使用 Decision Engine 的结果。

============================================================
"""


from typing import Any, Dict, List, Optional


# ============================================================
# 常量
# ============================================================

SECTION_CONCLUSION = "【结论】"

SECTION_BASIS = "【法律依据】"

SECTION_ANALYSIS = "【法律分析】"

SECTION_NOTICE = "【需要注意】"


# ============================================================
# Decision 状态
# ============================================================

VALID_DECISIONS = {

    "DEFINITE",

    "CONDITIONAL",

    "NOT_ESTABLISHED",

}


# ============================================================
# Condition 状态
# ============================================================

VALID_CONDITION_STATUSES = {

    "SATISFIED",

    "NOT_SATISFIED",

    "UNKNOWN",

}


# ============================================================
# Condition 类型
# ============================================================

CONDITION_TYPE_REQUIRED = "REQUIRED"

CONDITION_TYPE_EXCLUSION = "EXCLUSION"

CONDITION_TYPE_EXCEPTION = "EXCEPTION"

CONDITION_TYPE_UNKNOWN = "UNKNOWN"


# ============================================================
# 工具函数
# ============================================================

def safe_text(
    value: Any,
) -> str:

    """
    安全转换文本。

    None：
        返回空字符串。

    其他类型：
        转换为字符串并去除首尾空格。
    """

    if value is None:

        return ""

    return str(
        value
    ).strip()


def unique_strings(
    values: Optional[List[Any]],
) -> List[str]:

    """
    文本列表去重。

    保持原始顺序。
    """

    if not values:

        return []

    result = []

    seen = set()

    for value in values:

        text = safe_text(
            value
        )

        if not text:

            continue

        if text in seen:

            continue

        seen.add(text)

        result.append(
            text
        )

    return result


def get_value(
    obj: Any,
    name: str,
    default: Any = None,
) -> Any:

    """
    同时兼容：

        dict

    和：

        object.attribute

    支持：

        DecisionResult

        DecisionResult.to_dict()
    """

    if obj is None:

        return default

    if isinstance(
        obj,
        dict,
    ):

        return obj.get(
            name,
            default,
        )

    return getattr(
        obj,
        name,
        default,
    )


def as_list(
    value: Any,
) -> List[Any]:

    """
    将任意输入安全转换为 List。

    None：
        []

    str / dict：
        [value]

    tuple / list：
        list(value)

    其他：
        [value]
    """

    if value is None:

        return []

    if isinstance(
        value,
        (
            list,
            tuple,
        ),
    ):

        return list(
            value
        )

    if isinstance(
        value,
        (
            str,
            dict,
        ),
    ):

        return [
            value
        ]

    return [
        value
    ]


# ============================================================
# Decision 提取
# ============================================================

def extract_decision(
    decision: Any,
) -> str:

    """
    提取 Decision 状态。

    V6.0 标准：

        DEFINITE
        CONDITIONAL
        NOT_ESTABLISHED

    兼容旧版本：

        SATISFIED
        UNSATISFIED
        NOT_SATISFIED
        UNKNOWN
    """

    value = get_value(
        decision,
        "decision",
        None,
    )

    if value is None:

        value = get_value(
            decision,
            "status",
            None,
        )

    value = safe_text(
        value
    ).upper()

    if value in VALID_DECISIONS:

        return value

    if value == "SATISFIED":

        return "DEFINITE"

    if value in {
        "UNSATISFIED",
        "NOT_SATISFIED",
    }:

        return "NOT_ESTABLISHED"

    if value == "UNKNOWN":

        return "CONDITIONAL"

    return "CONDITIONAL"


# ============================================================
# 用户事实
# ============================================================

def extract_user_facts(
    decision: Any,
) -> List[str]:

    """
    提取用户明确提供的事实。

    标准字段：

        facts

    兼容：

        user_facts

    注意：

    用户说：

        连续签订三次固定期限劳动合同

    必须保留“三次”。

    不允许改写为：

        连续订立二次固定期限劳动合同
    """

    facts = get_value(
        decision,
        "facts",
        None,
    )

    if facts is None:

        facts = get_value(
            decision,
            "user_facts",
            None,
        )

    if facts is None:

        return []

    values = as_list(
        facts
    )

    result = []

    for fact in values:

        if isinstance(
            fact,
            dict,
        ):

            text = (
                fact.get(
                    "fact"
                )
                or fact.get(
                    "text"
                )
                or fact.get(
                    "name"
                )
            )

        else:

            text = get_value(
                fact,
                "fact",
                fact,
            )

        text = safe_text(
            text
        )

        if text:

            result.append(
                text
            )

    return unique_strings(
        result
    )


# ============================================================
# Condition 文本
# ============================================================

def extract_condition_text(
    condition: Any,
) -> str:

    """
    提取条件文本。

    支持：

        condition
        name
        text
        description
        requirement
    """

    if isinstance(
        condition,
        str,
    ):

        return safe_text(
            condition
        )

    if isinstance(
        condition,
        dict,
    ):

        for key in (
            "condition",
            "name",
            "text",
            "description",
            "requirement",
        ):

            value = safe_text(
                condition.get(
                    key,
                    "",
                )
            )

            if value:

                return value

        return ""

    for key in (
        "condition",
        "name",
        "text",
        "description",
        "requirement",
    ):

        value = safe_text(
            get_value(
                condition,
                key,
                "",
            )
        )

        if value:

            return value

    return safe_text(
        condition
    )


# ============================================================
# Condition 状态
# ============================================================

def extract_condition_status(
    condition: Any,
) -> str:

    """
    提取条件状态。

    标准：

        SATISFIED
        NOT_SATISFIED
        UNKNOWN
    """

    value = get_value(
        condition,
        "status",
        None,
    )

    if value is None:

        value = get_value(
            condition,
            "condition_status",
            None,
        )

    if value is None:

        value = get_value(
            condition,
            "result",
            None,
        )

    value = safe_text(
        value
    ).upper()

    if value in VALID_CONDITION_STATUSES:

        return value

    if value == "UNSATISFIED":

        return "NOT_SATISFIED"

    return "UNKNOWN"


# ============================================================
# Condition 原因
# ============================================================

def extract_condition_reason(
    condition: Any,
) -> str:

    """
    提取条件判断原因。
    """

    for key in (
        "reason",
        "explanation",
        "basis",
        "judgment_reason",
    ):

        value = safe_text(
            get_value(
                condition,
                key,
                "",
            )
        )

        if value:

            return value

    return ""


# ============================================================
# Condition 类型
# ============================================================

def normalize_condition_type(
    value: Any,
) -> str:

    """
    标准化 Condition 类型。

    支持：

        REQUIRED
        EXCLUSION
        EXCEPTION

    以及：

        required
        exclusion
        exception

    """

    value = safe_text(
        value
    ).upper()

    if value in {
        "REQUIRED",
        "REQUIREMENT",
        "POSITIVE",
        "MANDATORY",
    }:

        return CONDITION_TYPE_REQUIRED

    if value in {
        "EXCLUSION",
        "EXCLUDE",
        "NEGATIVE",
        "NEGATED",
    }:

        return CONDITION_TYPE_EXCLUSION

    if value in {
        "EXCEPTION",
        "EXCEPTIONS",
    }:

        return CONDITION_TYPE_EXCEPTION

    return CONDITION_TYPE_UNKNOWN


# ============================================================
# 推断 Condition 类型
# ============================================================

def infer_condition_type(
    condition: Any,
) -> str:

    """
    获取 Condition 类型。

    优先读取 Engine 明确提供的类型字段。

    支持：

        type
        condition_type
        category
        kind
        polarity

    如果 Engine 没有提供类型，
    则仅对当前已知 Article 14
    的固定结构进行有限兼容判断。

    注意：

    这里不是重新进行法律推理。

    只是恢复上游已经存在但可能
    未显式传递的 Condition Category。
    """

    for key in (
        "type",
        "condition_type",
        "category",
        "kind",
        "polarity",
    ):

        value = get_value(
            condition,
            key,
            None,
        )

        normalized = normalize_condition_type(
            value
        )

        if normalized != CONDITION_TYPE_UNKNOWN:

            return normalized

    text = extract_condition_text(
        condition
    )

    # --------------------------------------------------------
    # 当前 Article 14 的排除条件兼容识别
    # --------------------------------------------------------

    if (
        "第三十九条规定的情形"
        in text
        or "第四十条第一项规定的情形"
        in text
        or "第四十条第二项规定的情形"
        in text
    ):

        return CONDITION_TYPE_EXCLUSION

    # --------------------------------------------------------
    # 当前 Article 14 的例外条件兼容识别
    # --------------------------------------------------------

    if (
        "提出订立固定期限劳动合同"
        in text
    ):

        return CONDITION_TYPE_EXCEPTION

    return CONDITION_TYPE_REQUIRED


# ============================================================
# 标准 Condition
# ============================================================

def normalize_condition(
    condition: Any,
    default_type: str = CONDITION_TYPE_UNKNOWN,
) -> Dict[str, Any]:

    """
    将 Condition 转换为统一结构：

        {
            "condition": "...",
            "status": "...",
            "reason": "...",
            "type": "..."
        }

    注意：

    不修改 condition 文本。

    不修改用户事实。
    """

    text = extract_condition_text(
        condition
    )

    status = extract_condition_status(
        condition
    )

    reason = extract_condition_reason(
        condition
    )

    condition_type = infer_condition_type(
        condition
    )

    if (
        condition_type
        == CONDITION_TYPE_UNKNOWN
    ):

        condition_type = default_type

    return {

        "condition":
            text,

        "status":
            status,

        "reason":
            reason,

        "type":
            condition_type,

    }


# ============================================================
# 全部 Conditions
# ============================================================

def extract_conditions(
    decision: Any,
) -> List[Any]:

    """
    提取全部条件。

    优先：

        condition_results

    如果没有：

        conditions

    注意：

    condition_results 是 Decision Engine
    最重要的标准结果来源。

    """

    values = get_value(
        decision,
        "condition_results",
        None,
    )

    if values is None:

        values = get_value(
            decision,
            "conditions",
            None,
        )

    return as_list(
        values
    )


# ============================================================
# Required Conditions
# ============================================================

def extract_required_conditions(
    decision: Any,
) -> List[Any]:

    """
    提取普通必备法律条件。

    优先读取：

        required_conditions

    如果不存在，
    再从 conditions / condition_results
    中按照 type 分类。

    注意：

    EXCLUSION 和 EXCEPTION
    不应该进入这里。
    """

    values = get_value(
        decision,
        "required_conditions",
        None,
    )

    if values is not None:

        return as_list(
            values
        )

    result = []

    for condition in extract_conditions(
        decision
    ):

        normalized = normalize_condition(
            condition
        )

        if (
            normalized["type"]
            == CONDITION_TYPE_REQUIRED
        ):

            result.append(
                normalized
            )

    return result


# ============================================================
# Exclusion Conditions
# ============================================================

def extract_exclusion_conditions(
    decision: Any,
) -> List[Any]:

    """
    提取排除条件。

    优先读取：

        exclusion_conditions

    如果不存在，
    再从 conditions / condition_results
    中恢复。

    排除条件的语义：

        “存在该情形”

不是：

        “必须存在该情形”。

    因此：

        UNKNOWN

应表达为：

        尚不能确认该排除情形不存在。

    而不是：

        尚未确认该情形已经发生。
    """

    values = get_value(
        decision,
        "exclusion_conditions",
        None,
    )

    if values is not None:

        return as_list(
            values
        )

    result = []

    for condition in extract_conditions(
        decision
    ):

        normalized = normalize_condition(
            condition
        )

        if (
            normalized["type"]
            == CONDITION_TYPE_EXCLUSION
        ):

            result.append(
                normalized
            )

    return result


# ============================================================
# Exception Conditions
# ============================================================

def extract_exception_conditions(
    decision: Any,
) -> List[Any]:

    """
    提取例外条件。

    优先读取：

        exceptions

    如果不存在，
    再从 conditions / condition_results
    中恢复。

    Exception 不属于：

        required_conditions

    也不属于：

        exclusion_conditions

    因此不能直接作为 UNKNOWN 必备条件输出。
    """

    values = get_value(
        decision,
        "exceptions",
        None,
    )

    if values is not None:

        return as_list(
            values
        )

    result = []

    for condition in extract_conditions(
        decision
    ):

        normalized = normalize_condition(
            condition
        )

        if (
            normalized["type"]
            == CONDITION_TYPE_EXCEPTION
        ):

            result.append(
                normalized
            )

    return result


# ============================================================
# 满足条件
# ============================================================

def extract_satisfied_conditions(
    decision: Any,
) -> List[str]:

    """
    提取所有 SATISFIED 条件。

    但只输出：

        REQUIRED

    类型。

    EXCLUSION / EXCEPTION
    不进入普通“已满足条件”列表。
    """

    result = []

    for condition in extract_required_conditions(
        decision
    ):

        normalized = normalize_condition(
            condition,
            CONDITION_TYPE_REQUIRED,
        )

        if (
            normalized["status"]
            == "SATISFIED"
        ):

            text = normalized[
                "condition"
            ]

            if text:

                result.append(
                    text
                )

    if not result:

        values = get_value(
            decision,
            "satisfied_conditions",
            None,
        )

        for value in as_list(
            values
        ):

            text = extract_condition_text(
                value
            )

            if text:

                result.append(
                    text
                )

    return unique_strings(
        result
    )


# ============================================================
# 不满足条件
# ============================================================

def extract_unsatisfied_conditions(
    decision: Any,
) -> List[str]:

    """
    提取：

        NOT_SATISFIED

    类型：

        REQUIRED

    """

    result = []

    for condition in extract_required_conditions(
        decision
    ):

        normalized = normalize_condition(
            condition,
            CONDITION_TYPE_REQUIRED,
        )

        if (
            normalized["status"]
            == "NOT_SATISFIED"
        ):

            text = normalized[
                "condition"
            ]

            if text:

                result.append(
                    text
                )

    if not result:

        values = get_value(
            decision,
            "not_satisfied_conditions",
            None,
        )

        if values is None:

            values = get_value(
                decision,
                "unsatisfied_conditions",
                None,
            )

        for value in as_list(
            values
        ):

            text = extract_condition_text(
                value
            )

            if text:

                result.append(
                    text
                )

    return unique_strings(
        result
    )


# ============================================================
# 未知 Required Conditions
# ============================================================

def extract_unknown_required_conditions(
    decision: Any,
) -> List[Any]:

    """
    提取：

        REQUIRED + UNKNOWN

    这才是真正需要放入：

        “尚未确认条件”

    的内容。
    """

    result = []

    for condition in extract_required_conditions(
        decision
    ):

        normalized = normalize_condition(
            condition,
            CONDITION_TYPE_REQUIRED,
        )

        if (
            normalized["status"]
            == "UNKNOWN"
        ):

            result.append(
                normalized
            )

    return result


# ============================================================
# 未知 Exclusion Conditions
# ============================================================

def extract_unknown_exclusion_conditions(
    decision: Any,
) -> List[Any]:

    """
    提取：

        EXCLUSION + UNKNOWN

    """

    result = []

    for condition in extract_exclusion_conditions(
        decision
    ):

        normalized = normalize_condition(
            condition,
            CONDITION_TYPE_EXCLUSION,
        )

        if (
            normalized["status"]
            == "UNKNOWN"
        ):

            result.append(
                normalized
            )

    return result


# ============================================================
# 未知 Exception Conditions
# ============================================================

def extract_unknown_exception_conditions(
    decision: Any,
) -> List[Any]:

    """
    提取：

        EXCEPTION + UNKNOWN

    注意：

    Exception 不是普通必备条件。

    因此不能直接进入：

        unknown_conditions

    """

    result = []

    for condition in extract_exception_conditions(
        decision
    ):

        normalized = normalize_condition(
            condition,
            CONDITION_TYPE_EXCEPTION,
        )

        if (
            normalized["status"]
            == "UNKNOWN"
        ):

            result.append(
                normalized
            )

    return result


# ============================================================
# 兼容旧接口：UNKNOWN
# ============================================================

def extract_unknown_conditions(
    decision: Any,
) -> List[Any]:

    """
    兼容旧版本接口。

    V6.0-7 新规则：

        unknown_conditions

    只代表：

        REQUIRED + UNKNOWN

    不包含：

        EXCLUSION

        EXCEPTION

    """

    result = extract_unknown_required_conditions(
        decision
    )

    if result:

        return result

    values = get_value(
        decision,
        "unknown_conditions",
        None,
    )

    if values is None:

        values = get_value(
            decision,
            "unknown",
            None,
        )

    return as_list(
        values
    )


# ============================================================
# 法律规则
# ============================================================

def extract_rules(
    rules: Any,
) -> List[Any]:

    """
    提取结构化法律规则。

    支持：

        List[dict]

        List[object]

        dict

        DecisionResult

        DecisionResult.to_dict()

    """

    if rules is None:

        return []

    # --------------------------------------------------------
    # DecisionResult
    # --------------------------------------------------------

    if not isinstance(
        rules,
        (
            list,
            tuple,
            dict,
        ),
    ):

        values = get_value(
            rules,
            "rules",
            None,
        )

        if values is None:

            values = get_value(
                rules,
                "legal_rules",
                None,
            )

        if values is None:

            return []

        return extract_rules(
            values
        )

    # --------------------------------------------------------
    # Dict
    # --------------------------------------------------------

    if isinstance(
        rules,
        dict,
    ):

        values = rules.get(
            "rules"
        )

        if values is not None:

            return as_list(
                values
            )

        values = rules.get(
            "legal_rules"
        )

        if values is not None:

            return as_list(
                values
            )

        return [
            rules
        ]

    return list(
        rules
    )


# ============================================================
# 规则字段提取
# ============================================================

def extract_nested_structured_rule(
    rule: Any,
) -> Any:

    """
    提取嵌套：

        structured_rule

    或：

        rule

    """

    structured_rule = get_value(
        rule,
        "structured_rule",
        None,
    )

    if structured_rule is not None:

        return structured_rule

    nested_rule = get_value(
        rule,
        "rule",
        None,
    )

    if nested_rule is not None:

        return nested_rule

    return None


def extract_rule_law_name(
    rule: Any,
) -> str:

    """
    提取法律名称。

    优先：

        rule.law_name

    其次：

        rule.structured_rule.law_name
    """

    value = safe_text(
        get_value(
            rule,
            "law_name",
            "",
        )
    )

    if value:

        return value

    nested = extract_nested_structured_rule(
        rule
    )

    return safe_text(
        get_value(
            nested,
            "law_name",
            "",
        )
    )


def extract_rule_article(
    rule: Any,
) -> str:

    """
    提取法条编号。
    """

    value = safe_text(
        get_value(
            rule,
            "article_number",
            "",
        )
    )

    if value:

        return value

    nested = extract_nested_structured_rule(
        rule
    )

    return safe_text(
        get_value(
            nested,
            "article_number",
            "",
        )
    )


def extract_rule_summary(
    rule: Any,
) -> str:

    """
    提取法律规则摘要。

    支持：

        rule_summary

        summary

        description

        legal_rule

    以及嵌套 structured_rule。
    """

    for key in (
        "rule_summary",
        "summary",
        "description",
        "legal_rule",
    ):

        value = safe_text(
            get_value(
                rule,
                key,
                "",
            )
        )

        if value:

            return value

    nested = extract_nested_structured_rule(
        rule
    )

    for key in (
        "rule_summary",
        "summary",
        "description",
        "legal_rule",
    ):

        value = safe_text(
            get_value(
                nested,
                key,
                "",
            )
        )

        if value:

            return value

    return ""


# ============================================================
# 法律依据
# ============================================================

def build_legal_basis(
    rules: Any,
) -> List[str]:

    """
    构建法律依据。

    标准输出：

        《中华人民共和国劳动合同法》第十四条：规则摘要

    注意：

    只允许输出传入规则中真实存在的内容。

    不自行增加法条。

    同时支持：

        顶层 law_name

        顶层 article_number

        顶层 rule_summary

    以及：

        structured_rule.law_name

        structured_rule.article_number

        structured_rule.rule_summary
    """

    rule_list = extract_rules(
        rules
    )

    result = []

    seen = set()

    for rule in rule_list:

        law_name = extract_rule_law_name(
            rule
        )

        article = extract_rule_article(
            rule
        )

        summary = extract_rule_summary(
            rule
        )

        if not law_name and not article:

            continue

        if law_name and article:

            title = (
                f"《{law_name}》"
                f"{article}"
            )

        elif law_name:

            title = (
                f"《{law_name}》"
            )

        else:

            title = article

        if summary:

            text = (
                f"{title}："
                f"{summary}"
            )

        else:

            text = title

        key = text.strip()

        if key in seen:

            continue

        seen.add(key)

        result.append(
            text
        )

    return result


# ============================================================
# 结论
# ============================================================

def build_conclusion(
    decision: Any,
) -> str:

    """
    根据 Decision Engine 状态生成结论。

    不重新判断法律。

    如果 DecisionResult 已经提供：

        conclusion

    则优先使用。

    """

    status = extract_decision(
        decision
    )

    conclusion = safe_text(
        get_value(
            decision,
            "conclusion",
            "",
        )
    )

    if conclusion:

        return conclusion

    if status == "DEFINITE":

        return (
            "根据现有事实及已经确认的法律条件，"
            "相关法律条件已经满足。"
        )

    if status == "NOT_ESTABLISHED":

        return (
            "根据现有事实，"
            "尚不能确认已经满足相关法律规则的全部条件。"
        )

    return (
        "根据现有事实，"
        "不能直接作出绝对结论。"
        "仍有关键事实需要进一步确认。"
    )


# ============================================================
# Required Condition 格式化
# ============================================================

def format_required_condition(
    condition: Any,
) -> str:

    """
    格式化普通必备条件。
    """

    normalized = normalize_condition(
        condition,
        CONDITION_TYPE_REQUIRED,
    )

    text = normalized[
        "condition"
    ]

    status = normalized[
        "status"
    ]

    reason = normalized[
        "reason"
    ]

    if not text:

        return ""

    if status == "SATISFIED":

        prefix = "已满足"

    elif status == "NOT_SATISFIED":

        prefix = "不满足"

    else:

        prefix = "尚未确认"

    if reason:

        return (
            f"{prefix}：{text}"
            f"（{reason}）"
        )

    return (
        f"{prefix}：{text}"
    )


# ============================================================
# Exclusion Condition 格式化
# ============================================================

def format_exclusion_condition(
    condition: Any,
) -> str:

    """
    格式化排除条件。

    关键语义：

    原始条件：

        劳动者存在第三十九条规定的情形

    UNKNOWN：

        尚不能确认不存在该排除情形

    而不是：

        尚未确认劳动者存在第三十九条规定的情形

    """

    normalized = normalize_condition(
        condition,
        CONDITION_TYPE_EXCLUSION,
    )

    text = normalized[
        "condition"
    ]

    status = normalized[
        "status"
    ]

    reason = normalized[
        "reason"
    ]

    if not text:

        return ""

    if status == "SATISFIED":

        prefix = (
            "已确认存在排除情形"
        )

    elif status == "NOT_SATISFIED":

        prefix = (
            "已确认不存在排除情形"
        )

    else:

        prefix = (
            "尚不能确认不存在排除情形"
        )

    if reason:

        return (
            f"{prefix}：{text}"
            f"（{reason}）"
        )

    return (
        f"{prefix}：{text}"
    )


# ============================================================
# Exception 格式化
# ============================================================

def format_exception_condition(
    condition: Any,
) -> str:

    """
    格式化例外条件。

    Exception 不作为普通必备条件。

    只在：

        【需要注意】

    中进行提示。
    """

    normalized = normalize_condition(
        condition,
        CONDITION_TYPE_EXCEPTION,
    )

    text = normalized[
        "condition"
    ]

    status = normalized[
        "status"
    ]

    reason = normalized[
        "reason"
    ]

    if not text:

        return ""

    if status == "SATISFIED":

        prefix = (
            "已确认存在例外情形"
        )

    elif status == "NOT_SATISFIED":

        prefix = (
            "已确认不存在该例外情形"
        )

    else:

        prefix = (
            "尚未确认是否存在该例外情形"
        )

    if reason:

        return (
            f"{prefix}：{text}"
            f"（{reason}）"
        )

    return (
        f"{prefix}：{text}"
    )


# ============================================================
# 法律分析
# ============================================================

def build_analysis(
    decision: Any,
) -> List[str]:

    """
    构建结构化法律分析。

    顺序：

        1. 用户事实
        2. 法律规则
        3. 必备条件
        4. 排除条件
        5. 法律后果

    Exception 不作为普通条件，
    单独进入“需要注意”。
    """

    result = []

    facts = extract_user_facts(
        decision
    )

    required = extract_required_conditions(
        decision
    )

    exclusion = extract_exclusion_conditions(
        decision
    )

    # --------------------------------------------------------
    # 1. 用户事实
    # --------------------------------------------------------

    result.append(
        "1. 用户事实："
    )

    if facts:

        for fact in facts:

            result.append(
                f"   - {fact}"
            )

    else:

        result.append(
            "   - 当前没有提取到明确用户事实。"
        )

    # --------------------------------------------------------
    # 2. 法律规则
    # --------------------------------------------------------

    result.append(
        "2. 法律规则："
    )

    result.append(
        "   根据 Decision Engine 已确认的结构化法律规则，"
        "应当逐项判断相关条件，"
        "不能仅根据单一事实直接得出最终法律结论。"
    )

    # --------------------------------------------------------
    # 3. 必备条件
    # --------------------------------------------------------

    result.append(
        "3. 必备条件："
    )

    required_output = []

    for condition in required:

        text = format_required_condition(
            condition
        )

        if text:

            required_output.append(
                text
            )

    if required_output:

        for text in required_output:

            result.append(
                f"   - {text}"
            )

    else:

        result.append(
            "   - 当前没有可用的必备条件判断结果。"
        )

    # --------------------------------------------------------
    # 4. 排除条件
    # --------------------------------------------------------

    result.append(
        "4. 排除条件："
    )

    exclusion_output = []

    for condition in exclusion:

        text = format_exclusion_condition(
            condition
        )

        if text:

            exclusion_output.append(
                text
            )

    if exclusion_output:

        for text in exclusion_output:

            result.append(
                f"   - {text}"
            )

    else:

        result.append(
            "   - 当前没有可用的排除条件判断结果。"
        )

    # --------------------------------------------------------
    # 5. 法律后果
    # --------------------------------------------------------

    result.append(
        "5. 法律后果："
    )

    status = extract_decision(
        decision
    )

    if status == "DEFINITE":

        result.append(
            "   - Decision Engine 已确认相关法律条件满足，"
            "应按照结构化法律规则确定相应法律后果。"
        )

    elif status == "NOT_ESTABLISHED":

        result.append(
            "   - 当前已经确认的事实不足以支持"
            "相关法律规则产生确定的法律后果。"
        )

    else:

        result.append(
            "   - 当前属于条件性结论，"
            "在关键事实尚未确认之前，"
            "不能直接认定最终法律后果。"
        )

    return result


# ============================================================
# 需要注意
# ============================================================

def build_notices(
    decision: Any,
) -> List[str]:

    """
    构建需要注意事项。

    特别处理：

        CONDITIONAL

        UNKNOWN Required Conditions

        UNKNOWN Exclusion Conditions

        UNKNOWN Exceptions

        三次固定期限劳动合同

    """

    result = []

    status = extract_decision(
        decision
    )

    # --------------------------------------------------------
    # CONDITIONAL
    # --------------------------------------------------------

    if status == "CONDITIONAL":

        result.append(
            "当前属于条件性结论，"
            "不能将尚未确认的事实视为已经发生。"
        )

    # --------------------------------------------------------
    # Required UNKNOWN
    # --------------------------------------------------------

    unknown_required = (
        extract_unknown_required_conditions(
            decision
        )
    )

    for condition in unknown_required:

        normalized = normalize_condition(
            condition,
            CONDITION_TYPE_REQUIRED,
        )

        text = normalized[
            "condition"
        ]

        reason = normalized[
            "reason"
        ]

        if not text:

            continue

        if reason:

            result.append(
                f"需要进一步确认："
                f"{text}"
                f"（{reason}）"
            )

        else:

            result.append(
                f"需要进一步确认："
                f"{text}"
            )

    # --------------------------------------------------------
    # Exclusion UNKNOWN
    # --------------------------------------------------------

    unknown_exclusion = (
        extract_unknown_exclusion_conditions(
            decision
        )
    )

    for condition in unknown_exclusion:

        text = format_exclusion_condition(
            condition
        )

        if text:

            result.append(
                f"需要进一步确认：{text}"
            )

    # --------------------------------------------------------
    # Exception UNKNOWN
    # --------------------------------------------------------

    unknown_exception = (
        extract_unknown_exception_conditions(
            decision
        )
    )

    for condition in unknown_exception:

        text = format_exception_condition(
            condition
        )

        if text:

            result.append(
                f"需要注意例外情形：{text}"
            )

    # --------------------------------------------------------
    # 三次固定期限劳动合同特殊保护
    # --------------------------------------------------------

    facts = extract_user_facts(
        decision
    )

    fact_text = "；".join(
        facts
    )

    if (
        "三次"
        in fact_text
        and "固定期限劳动合同"
        in fact_text
    ):

        result.append(
            "用户明确描述的是“连续签订三次固定期限劳动合同”，"
            "该事实必须保持原意，"
            "不能直接改写为法律规则中的“连续订立二次固定期限劳动合同”。"
        )

    # --------------------------------------------------------
    # 默认
    # --------------------------------------------------------

    if not result:

        result.append(
            "最终法律结论应以已经确认的事实、"
            "有效法律法规及具体合同情况为基础。"
        )

    return unique_strings(
        result
    )


# ============================================================
# 构建结构化答案
# ============================================================

def build_answer_structure(
    decision: Any,
    rules: Any = None,
) -> Dict[str, Any]:

    """
    构建结构化法律答案。

    返回：

        {
            "decision": "...",
            "conclusion": "...",
            "legal_basis": [...],
            "analysis": [...],
            "notices": [...],

            "required_conditions": [...],
            "exclusion_conditions": [...],
            "exceptions": [...],

            "condition_results": [...]
        }

    V6.0-7 特别增加：

        required_conditions
        exclusion_conditions
        exceptions
        condition_results

    用于后续 Validator 做结构化完整性检查。
    """

    status = extract_decision(
        decision
    )

    if rules is None:

        rules = get_value(
            decision,
            "rules",
            [],
        )

    required_conditions = [
        normalize_condition(
            condition,
            CONDITION_TYPE_REQUIRED,
        )
        for condition
        in extract_required_conditions(
            decision
        )
    ]

    exclusion_conditions = [
        normalize_condition(
            condition,
            CONDITION_TYPE_EXCLUSION,
        )
        for condition
        in extract_exclusion_conditions(
            decision
        )
    ]

    exceptions = [
        normalize_condition(
            condition,
            CONDITION_TYPE_EXCEPTION,
        )
        for condition
        in extract_exception_conditions(
            decision
        )
    ]

    all_condition_results = (
        required_conditions
        + exclusion_conditions
        + exceptions
    )

    return {

        "decision":
            status,

        "conclusion":
            build_conclusion(
                decision
            ),

        "legal_basis":
            build_legal_basis(
                rules
            ),

        "analysis":
            build_analysis(
                decision
            ),

        "notices":
            build_notices(
                decision
            ),

        "required_conditions":
            required_conditions,

        "exclusion_conditions":
            exclusion_conditions,

        "exceptions":
            exceptions,

        "condition_results":
            all_condition_results,

    }


# ============================================================
# Prompt：法律依据
# ============================================================

def format_legal_basis(
    legal_basis: List[str],
) -> str:

    """
    格式化法律依据。
    """

    if not legal_basis:

        return (
            "当前没有可直接引用的结构化法律依据。"
        )

    lines = []

    for index, item in enumerate(
        legal_basis,
        start=1,
    ):

        lines.append(
            f"{index}. {item}"
        )

    return "\n".join(
        lines
    )


# ============================================================
# Prompt：法律分析
# ============================================================

def format_analysis(
    analysis: List[str],
) -> str:

    """
    格式化法律分析。
    """

    if not analysis:

        return (
            "当前没有结构化法律分析内容。"
        )

    return "\n".join(
        analysis
    )


# ============================================================
# Prompt：需要注意
# ============================================================

def format_notices(
    notices: List[str],
) -> str:

    """
    格式化注意事项。
    """

    if not notices:

        return (
            "无特别注意事项。"
        )

    lines = []

    for notice in notices:

        lines.append(
            f"- {notice}"
        )

    return "\n".join(
        lines
    )


# ============================================================
# Prompt：Condition Summary
# ============================================================

def format_condition_summary(
    structure: Dict[str, Any],
) -> str:

    """
    将结构化条件完整提供给 Ollama。

    这里明确区分：

        REQUIRED
        EXCLUSION
        EXCEPTION

    防止 LLM 把三类条件混为一谈。
    """

    lines = []

    required = structure.get(
        "required_conditions",
        [],
    )

    exclusion = structure.get(
        "exclusion_conditions",
        [],
    )

    exceptions = structure.get(
        "exceptions",
        [],
    )

    # --------------------------------------------------------
    # REQUIRED
    # --------------------------------------------------------

    lines.append(
        "【REQUIRED 必备条件】"
    )

    if required:

        for condition in required:

            text = condition.get(
                "condition",
                "",
            )

            status = condition.get(
                "status",
                "UNKNOWN",
            )

            reason = condition.get(
                "reason",
                "",
            )

            line = (
                f"- {text}"
                f" | 状态：{status}"
            )

            if reason:

                line += (
                    f" | 原因：{reason}"
                )

            lines.append(
                line
            )

    else:

        lines.append(
            "- 无"
        )

    # --------------------------------------------------------
    # EXCLUSION
    # --------------------------------------------------------

    lines.append(
        "【EXCLUSION 排除条件】"
    )

    if exclusion:

        for condition in exclusion:

            text = condition.get(
                "condition",
                "",
            )

            status = condition.get(
                "status",
                "UNKNOWN",
            )

            reason = condition.get(
                "reason",
                "",
            )

            line = (
                f"- {text}"
                f" | 状态：{status}"
            )

            if reason:

                line += (
                    f" | 原因：{reason}"
                )

            lines.append(
                line
            )

    else:

        lines.append(
            "- 无"
        )

    # --------------------------------------------------------
    # EXCEPTION
    # --------------------------------------------------------

    lines.append(
        "【EXCEPTION 例外条件】"
    )

    if exceptions:

        for condition in exceptions:

            text = condition.get(
                "condition",
                "",
            )

            status = condition.get(
                "status",
                "UNKNOWN",
            )

            reason = condition.get(
                "reason",
                "",
            )

            line = (
                f"- {text}"
                f" | 状态：{status}"
            )

            if reason:

                line += (
                    f" | 原因：{reason}"
                )

            lines.append(
                line
            )

    else:

        lines.append(
            "- 无"
        )

    return "\n".join(
        lines
    )


# ============================================================
# Ollama Prompt
# ============================================================

def build_answer_prompt(
    question: str,
    decision: Any,
    rules: Any = None,
) -> str:

    """
    构建最终 Ollama Prompt。

    Ollama 不负责重新判断法律。

    Ollama 只负责：

        结构化决策
            ↓
        自然语言表达
    """

    question = safe_text(
        question
    )

    structure = build_answer_structure(
        decision=decision,
        rules=rules,
    )

    status = structure[
        "decision"
    ]

    conclusion = structure[
        "conclusion"
    ]

    legal_basis = structure[
        "legal_basis"
    ]

    analysis = structure[
        "analysis"
    ]

    notices = structure[
        "notices"
    ]

    condition_summary = (
        format_condition_summary(
            structure
        )
    )

    return f"""
你是一名严谨的中国劳动法法律智能问答助手。

你的任务不是重新进行法律推理。

法律判断已经由 Legal Decision Engine 完成。

你的任务只有一个：

根据结构化法律决策结果，
将其转换成准确、克制、自然的中文法律回答。

====================
用户问题
====================

{question}

====================
Decision
====================

{status}

====================
Decision 结论
====================

{conclusion}

====================
用户明确事实
====================

{chr(10).join("- " + x for x in extract_user_facts(decision)) or "- 无"}

====================
结构化法律依据
====================

{format_legal_basis(legal_basis)}

====================
结构化条件
====================

{condition_summary}

====================
结构化法律分析
====================

{format_analysis(analysis)}

====================
需要注意
====================

{format_notices(notices)}

====================
严格规则
====================

1. 不得修改用户明确提供的事实。

2. 如果用户说：
“连续签订三次固定期限劳动合同”，
必须保持“三次”。

3. 不得把用户事实改写成：
“连续订立二次固定期限劳动合同”。

4. “连续订立二次固定期限劳动合同”
是法律规则中的条件，
不是对用户“三次”事实的改写。

5. REQUIRED 是普通必备法律条件。

6. EXCLUSION 是排除条件。

7. EXCLUSION 条件不能理解成：
“法律要求该情形发生”。

8. 如果 EXCLUSION 状态为 UNKNOWN，
必须表达为：
“尚不能确认不存在该排除情形”。

9. EXCEPTION 是例外情形。

10. EXCEPTION 不得自动写成普通 UNKNOWN 必备条件。

11. 不得把 EXCEPTION 自动增加为用户事实。

12. 如果 Decision 为 CONDITIONAL，
最终回答必须保持条件性。

13. 可以使用：
“如果……则……”
“在……条件成立的情况下……”
“如果相关条件均满足……”

14. 不得把假设条件写成已经发生的事实。

15. 不得把 UNKNOWN 自动解释成 NOT_SATISFIED。

16. 不得把 NOT_SATISFIED 自动解释成 UNKNOWN。

17. 不得增加结构化法律依据之外的具体法律条文。

18. 不得自行增加新的法律条件。

19. 不得删除 Decision Engine 已经提供的关键条件。

20. 不得改变：
“应当”
“可以”
“不得”
等法律义务强度。

21. 不得输出思考过程。

22. 不得输出：
“我的思考是”
“分析过程是”
“让我分析”
等内容。

23. 四个标题必须严格使用：

【结论】

【法律依据】

【法律分析】

【需要注意】

24. 四个标题各只能出现一次。

25. 不得重复完整答案。

26. 语言使用中文。

27. 表达准确、克制。

28. 如果结构化 Decision 是 CONDITIONAL，
不得输出确定性结论：
“公司一定必须……”
除非 Decision Engine 本身已经明确给出确定性结论。

====================
最终要求
====================

只输出最终法律回答。

不要输出额外说明。
"""


# ============================================================
# 本地纯 Python 最终答案
# ============================================================

def build_plain_answer(
    question: str,
    decision: Any,
    rules: Any = None,
) -> str:

    """
    不经过 Ollama，
    直接生成结构化法律回答。

    用于：

        Ollama 失败

        Ollama Validation 失败

        安全 Fallback
    """

    structure = build_answer_structure(
        decision=decision,
        rules=rules,
    )

    conclusion = structure[
        "conclusion"
    ]

    legal_basis = structure[
        "legal_basis"
    ]

    analysis = structure[
        "analysis"
    ]

    notices = structure[
        "notices"
    ]

    parts = []

    # --------------------------------------------------------
    # 【结论】
    # --------------------------------------------------------

    parts.append(
        SECTION_CONCLUSION
    )

    parts.append(
        conclusion
    )

    parts.append("")

    # --------------------------------------------------------
    # 【法律依据】
    # --------------------------------------------------------

    parts.append(
        SECTION_BASIS
    )

    parts.append(
        format_legal_basis(
            legal_basis
        )
    )

    parts.append("")

    # --------------------------------------------------------
    # 【法律分析】
    # --------------------------------------------------------

    parts.append(
        SECTION_ANALYSIS
    )

    parts.append(
        format_analysis(
            analysis
        )
    )

    parts.append("")

    # --------------------------------------------------------
    # 【需要注意】
    # --------------------------------------------------------

    parts.append(
        SECTION_NOTICE
    )

    parts.append(
        format_notices(
            notices
        )
    )

    return "\n".join(
        parts
    ).strip()


# ============================================================
# Demo Decision
# ============================================================

def create_demo_decision() -> Dict[str, Any]:

    """
    创建 V6.0-7 标准测试结果。

    这里模拟当前真实问题：

        公司连续签订三次固定期限劳动合同后，
        是否必须签订无固定期限劳动合同？

    特别注意：

    结构明确区分：

        REQUIRED
        EXCLUSION
        EXCEPTION

    总 Condition Results：

        3 + 3 + 1 = 7
    """

    return {

        "decision":
            "CONDITIONAL",

        "conclusion":
            (
                "根据现有事实，不能直接作出绝对结论。"
                "已经确认部分法律条件，"
                "但仍有关键事实需要进一步确认。"
            ),

        "facts": [

            {
                "fact":
                    "连续签订三次固定期限劳动合同",

                "status":
                    "EXPLICIT",
            },

        ],

        # ----------------------------------------------------
        # REQUIRED
        # ----------------------------------------------------

        "required_conditions": [

            {
                "condition":
                    "连续订立二次固定期限劳动合同",

                "status":
                    "SATISFIED",

                "type":
                    "REQUIRED",

                "reason":
                    (
                        "用户明确说明连续签订三次固定期限劳动合同，"
                        "因此合同次数事实足以支持达到连续订立二次固定期限劳动合同的数量门槛。"
                    ),
            },

            {
                "condition":
                    "续订劳动合同",

                "status":
                    "UNKNOWN",

                "type":
                    "REQUIRED",

                "reason":
                    (
                        "用户没有明确说明相关合同是否属于法律意义上的续订劳动合同。"
                    ),
            },

            {
                "condition":
                    "劳动者提出或者同意续订、订立劳动合同",

                "status":
                    "UNKNOWN",

                "type":
                    "REQUIRED",

                "reason":
                    (
                        "用户没有提供劳动者是否提出或者同意续订、订立劳动合同的事实。"
                    ),
            },

        ],

        # ----------------------------------------------------
        # EXCLUSION
        # ----------------------------------------------------

        "exclusion_conditions": [

            {
                "condition":
                    "劳动者存在《劳动合同法》第三十九条规定的情形",

                "status":
                    "UNKNOWN",

                "type":
                    "EXCLUSION",

                "reason":
                    (
                        "用户没有提供劳动者是否存在第三十九条规定情形的事实，"
                        "因此尚不能确认不存在该排除情形。"
                    ),
            },

            {
                "condition":
                    "劳动者存在《劳动合同法》第四十条第一项规定的情形",

                "status":
                    "UNKNOWN",

                "type":
                    "EXCLUSION",

                "reason":
                    (
                        "用户没有提供是否存在第四十条第一项规定情形的事实，"
                        "因此尚不能确认不存在该排除情形。"
                    ),
            },

            {
                "condition":
                    "劳动者存在《劳动合同法》第四十条第二项规定的情形",

                "status":
                    "UNKNOWN",

                "type":
                    "EXCLUSION",

                "reason":
                    (
                        "用户没有提供是否存在第四十条第二项规定情形的事实，"
                        "因此尚不能确认不存在该排除情形。"
                    ),
            },

        ],

        # ----------------------------------------------------
        # EXCEPTION
        # ----------------------------------------------------

        "exceptions": [

            {
                "condition":
                    "劳动者提出订立固定期限劳动合同",

                "status":
                    "UNKNOWN",

                "type":
                    "EXCEPTION",

                "reason":
                    (
                        "用户没有说明劳动者是否提出订立固定期限劳动合同。"
                    ),
            },

        ],

        # ----------------------------------------------------
        # 保留兼容字段
        # ----------------------------------------------------

        "conditions": [

            {
                "condition":
                    "连续订立二次固定期限劳动合同",

                "status":
                    "SATISFIED",

                "type":
                    "REQUIRED",

                "reason":
                    (
                        "用户明确说明连续签订三次固定期限劳动合同。"
                    ),
            },

            {
                "condition":
                    "续订劳动合同",

                "status":
                    "UNKNOWN",

                "type":
                    "REQUIRED",

                "reason":
                    (
                        "用户没有明确说明相关合同是否属于法律意义上的续订劳动合同。"
                    ),
            },

            {
                "condition":
                    "劳动者提出或者同意续订、订立劳动合同",

                "status":
                    "UNKNOWN",

                "type":
                    "REQUIRED",

                "reason":
                    (
                        "用户没有提供劳动者是否提出或者同意续订、订立劳动合同的事实。"
                    ),
            },

            {
                "condition":
                    "劳动者存在《劳动合同法》第三十九条规定的情形",

                "status":
                    "UNKNOWN",

                "type":
                    "EXCLUSION",

                "reason":
                    (
                        "尚不能确认不存在该排除情形。"
                    ),
            },

            {
                "condition":
                    "劳动者存在《劳动合同法》第四十条第一项规定的情形",

                "status":
                    "UNKNOWN",

                "type":
                    "EXCLUSION",

                "reason":
                    (
                        "尚不能确认不存在该排除情形。"
                    ),
            },

            {
                "condition":
                    "劳动者存在《劳动合同法》第四十条第二项规定的情形",

                "status":
                    "UNKNOWN",

                "type":
                    "EXCLUSION",

                "reason":
                    (
                        "尚不能确认不存在该排除情形。"
                    ),
            },

            {
                "condition":
                    "劳动者提出订立固定期限劳动合同",

                "status":
                    "UNKNOWN",

                "type":
                    "EXCEPTION",

                "reason":
                    (
                        "用户没有说明劳动者是否提出订立固定期限劳动合同。"
                    ),
            },

        ],

        "condition_results": [

            {
                "condition":
                    "连续订立二次固定期限劳动合同",

                "status":
                    "SATISFIED",

                "type":
                    "REQUIRED",

                "reason":
                    "合同次数已经达到二次数量门槛。",
            },

            {
                "condition":
                    "续订劳动合同",

                "status":
                    "UNKNOWN",

                "type":
                    "REQUIRED",

                "reason":
                    "用户没有明确说明。",
            },

            {
                "condition":
                    "劳动者提出或者同意续订、订立劳动合同",

                "status":
                    "UNKNOWN",

                "type":
                    "REQUIRED",

                "reason":
                    "用户没有提供相关事实。",
            },

            {
                "condition":
                    "劳动者存在《劳动合同法》第三十九条规定的情形",

                "status":
                    "UNKNOWN",

                "type":
                    "EXCLUSION",

                "reason":
                    "尚不能确认不存在该排除情形。",
            },

            {
                "condition":
                    "劳动者存在《劳动合同法》第四十条第一项规定的情形",

                "status":
                    "UNKNOWN",

                "type":
                    "EXCLUSION",

                "reason":
                    "尚不能确认不存在该排除情形。",
            },

            {
                "condition":
                    "劳动者存在《劳动合同法》第四十条第二项规定的情形",

                "status":
                    "UNKNOWN",

                "type":
                    "EXCLUSION",

                "reason":
                    "尚不能确认不存在该排除情形。",
            },

            {
                "condition":
                    "劳动者提出订立固定期限劳动合同",

                "status":
                    "UNKNOWN",

                "type":
                    "EXCEPTION",

                "reason":
                    "用户没有说明。",
            },

        ],

        # ----------------------------------------------------
        # 法律规则
        # ----------------------------------------------------

        "rules": [

            {
                "law_name":
                    "中华人民共和国劳动合同法",

                "article_number":
                    "第十四条",

                "rule_summary":
                    (
                        "符合《劳动合同法》第十四条规定条件时，"
                        "应当订立无固定期限劳动合同。"
                    ),
            },

            {
                "law_name":
                    "中华人民共和国劳动合同法",

                "article_number":
                    "第三十九条",

                "rule_summary":
                    (
                        "劳动者有法定情形时，"
                        "用人单位可以解除劳动合同。"
                    ),
            },

            {
                "law_name":
                    "中华人民共和国劳动合同法",

                "article_number":
                    "第四十条",

                "rule_summary":
                    (
                        "存在法定情形时，"
                        "用人单位可以解除劳动合同。"
                    ),
            },

        ],
    }


# ============================================================
# V6.0-7 测试
# ============================================================

def run_test():

    print()
    print("=" * 70)
    print("RAG V6.0-7 - Legal Answer Builder")
    print("=" * 70)

    question = (
        "公司连续签订三次固定期限劳动合同后，"
        "是否必须签订无固定期限劳动合同？"
    )

    decision = create_demo_decision()

    rules = decision[
        "rules"
    ]

    print()
    print("问题：")
    print(question)

    # --------------------------------------------------------
    # 构建结构
    # --------------------------------------------------------

    structure = build_answer_structure(
        decision=decision,
        rules=rules,
    )

    print()
    print("=" * 70)
    print("Condition Structure")
    print("=" * 70)

    required = structure[
        "required_conditions"
    ]

    exclusion = structure[
        "exclusion_conditions"
    ]

    exceptions = structure[
        "exceptions"
    ]

    condition_results = structure[
        "condition_results"
    ]

    print()
    print(
        "Required Conditions：",
        len(required)
    )

    print(
        "Exclusion Conditions：",
        len(exclusion)
    )

    print(
        "Exceptions：",
        len(exceptions)
    )

    print(
        "Condition Results：",
        len(condition_results)
    )

    # --------------------------------------------------------
    # 数量测试
    # --------------------------------------------------------

    if len(required) != 3:

        raise AssertionError(
            "Required Conditions 数量错误"
        )

    if len(exclusion) != 3:

        raise AssertionError(
            "Exclusion Conditions 数量错误"
        )

    if len(exceptions) != 1:

        raise AssertionError(
            "Exceptions 数量错误"
        )

    if len(condition_results) != 7:

        raise AssertionError(
            "Condition Results 应为 7"
        )

    # --------------------------------------------------------
    # 类型测试
    # --------------------------------------------------------

    for condition in required:

        if (
            condition["type"]
            != CONDITION_TYPE_REQUIRED
        ):

            raise AssertionError(
                "Required Condition 类型错误"
            )

    for condition in exclusion:

        if (
            condition["type"]
            != CONDITION_TYPE_EXCLUSION
        ):

            raise AssertionError(
                "Exclusion Condition 类型错误"
            )

    for condition in exceptions:

        if (
            condition["type"]
            != CONDITION_TYPE_EXCEPTION
        ):

            raise AssertionError(
                "Exception 类型错误"
            )

    print()
    print(
        "✅ Required / Exclusion / Exception 分类正确"
    )

    # --------------------------------------------------------
    # UNKNOWN 测试
    # --------------------------------------------------------

    unknown_required = (
        extract_unknown_required_conditions(
            decision
        )
    )

    unknown_exclusion = (
        extract_unknown_exclusion_conditions(
            decision
        )
    )

    unknown_exception = (
        extract_unknown_exception_conditions(
            decision
        )
    )

    if len(unknown_required) != 2:

        raise AssertionError(
            "Required UNKNOWN 应为 2"
        )

    if len(unknown_exclusion) != 3:

        raise AssertionError(
            "Exclusion UNKNOWN 应为 3"
        )

    if len(unknown_exception) != 1:

        raise AssertionError(
            "Exception UNKNOWN 应为 1"
        )

    print(
        "✅ UNKNOWN 分类正确"
    )

    # --------------------------------------------------------
    # 旧接口 unknown_conditions
    # 只能得到 Required UNKNOWN
    # --------------------------------------------------------

    unknown_conditions = (
        extract_unknown_conditions(
            decision
        )
    )

    if len(unknown_conditions) != 2:

        raise AssertionError(
            "unknown_conditions 不应包含 Exclusion / Exception"
        )

    print(
        "✅ unknown_conditions 不再错误包含 Exclusion / Exception"
    )

    # --------------------------------------------------------
    # Exception 不得出现在普通分析 UNKNOWN 中
    # --------------------------------------------------------

    analysis = build_analysis(
        decision
    )

    analysis_text = "\n".join(
        analysis
    )

    if (
        "劳动者提出订立固定期限劳动合同"
        in analysis_text
    ):

        raise AssertionError(
            "Exception 被错误加入普通法律分析条件"
        )

    print(
        "✅ Exception 未错误加入普通法律分析"
    )

    # --------------------------------------------------------
    # 排除条件语义测试
    # --------------------------------------------------------

    notices = build_notices(
        decision
    )

    notices_text = "\n".join(
        notices
    )

    if (
        "尚不能确认不存在排除情形"
        not in notices_text
    ):

        raise AssertionError(
            "Exclusion UNKNOWN 语义错误"
        )

    if (
        "尚未确认劳动者存在"
        in notices_text
    ):

        raise AssertionError(
            "错误地将 Exclusion UNKNOWN 表达为存在情形未知"
        )

    print(
        "✅ Exclusion UNKNOWN 语义正确"
    )

    # --------------------------------------------------------
    # 用户事实测试
    # --------------------------------------------------------

    answer = build_plain_answer(
        question=question,
        decision=decision,
        rules=rules,
    )

    if (
        "连续签订三次固定期限劳动合同"
        not in answer
    ):

        raise AssertionError(
            "用户事实丢失"
        )

    if (
        "连续签订二次固定期限劳动合同"
        in answer
    ):

        raise AssertionError(
            "错误：用户事实被改写成二次"
        )

    print(
        "✅ 用户事实“三次”保持不变"
    )

    # --------------------------------------------------------
    # 四段式标题测试
    # --------------------------------------------------------

    required_sections = [

        SECTION_CONCLUSION,

        SECTION_BASIS,

        SECTION_ANALYSIS,

        SECTION_NOTICE,

    ]

    for section in required_sections:

        count = answer.count(
            section
        )

        if count != 1:

            raise AssertionError(
                f"{section} 出现 {count} 次"
            )

    print(
        "✅ 四段式结构正确"
    )

    # --------------------------------------------------------
    # 法律依据
    # --------------------------------------------------------

    if (
        "《中华人民共和国劳动合同法》第十四条"
        not in answer
    ):

        raise AssertionError(
            "缺少第十四条法律依据"
        )

    print(
        "✅ 法律依据正确"
    )

    # --------------------------------------------------------
    # CONDITIONAL
    # --------------------------------------------------------

    if (
        "不能直接作出绝对结论"
        not in answer
    ):

        raise AssertionError(
            "CONDITIONAL 结论错误"
        )

    print(
        "✅ CONDITIONAL 结论正确"
    )

    # --------------------------------------------------------
    # Condition 完整性
    # --------------------------------------------------------

    if (
        len(condition_results)
        != 7
    ):

        raise AssertionError(
            "Condition Results 完整性错误"
        )

    print(
        "✅ Engine Condition Results = 7"
    )

    # --------------------------------------------------------
    # Prompt 测试
    # --------------------------------------------------------

    prompt = build_answer_prompt(
        question=question,
        decision=decision,
        rules=rules,
    )

    if (
        "【REQUIRED 必备条件】"
        not in prompt
    ):

        raise AssertionError(
            "Prompt 缺少 REQUIRED 分类"
        )

    if (
        "【EXCLUSION 排除条件】"
        not in prompt
    ):

        raise AssertionError(
            "Prompt 缺少 EXCLUSION 分类"
        )

    if (
        "【EXCEPTION 例外条件】"
        not in prompt
    ):

        raise AssertionError(
            "Prompt 缺少 EXCEPTION 分类"
        )

    print(
        "✅ Ollama Prompt Condition Category 正确"
    )

    # --------------------------------------------------------
    # 输出
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("结构化答案")
    print("=" * 70)

    print()
    print(answer)

    print()
    print("=" * 70)
    print("V6.0-7 测试结果")
    print("=" * 70)

    print()
    print(
        "✅ Decision 状态正确"
    )

    print(
        "✅ 用户事实“三次”保持不变"
    )

    print(
        "✅ Required Conditions 正确"
    )

    print(
        "✅ Exclusion Conditions 正确"
    )

    print(
        "✅ Exceptions 正确"
    )

    print(
        "✅ UNKNOWN 分类正确"
    )

    print(
        "✅ Exclusion UNKNOWN 语义正确"
    )

    print(
        "✅ Exception 未错误进入普通条件"
    )

    print(
        "✅ Condition Results = 7"
    )

    print(
        "✅ 法律依据正确输出"
    )

    print(
        "✅ CONDITIONAL 结论正确"
    )

    print(
        "✅ Ollama Prompt 分类正确"
    )

    print(
        "🎉 V6.0-7 Legal Answer Builder 测试通过"
    )

    return answer


# ============================================================
# Module Entry
# ============================================================

if __name__ == "__main__":

    run_test()