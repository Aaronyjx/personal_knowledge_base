# -*- coding: utf-8 -*-

"""
RAG V6.1
Legal Answer Views

============================================================
功能
============================================================

本模块负责：

    StructuredAnswer
          ↓
    展示文本 / Ollama Context / Prompt Context / Debug Summary

本模块只负责：

    1. Answer Formatting
    2. Answer Serialization
    3. Prompt Context Formatting
    4. Debug Summary

============================================================
重要架构边界
============================================================

本模块：

    不进行法律推理
    不创建 ConditionResult
    不修改 ConditionResult
    不修改 DecisionResult
    不判断 UNKNOWN
    不把 UNKNOWN 转换为 SATISFIED
    不把 UNKNOWN 转换为 NOT_SATISFIED
    不修改 CONDITIONAL / DEFINITE / NOT_ESTABLISHED

唯一合法的数据来源：

    StructuredAnswer

StructuredAnswer 本身已经由：

    Legal Decision Engine
            ↓
    Legal Answer Builder Core
            ↓
    StructuredAnswer

生成。

因此本模块只是：

    StructuredAnswer
            ↓
    View / Serialization

============================================================
循环依赖原则
============================================================

本模块不能：

    from src.legal_answer_builder import ...

否则：

    legal_answer_builder
            ↓
    legal_answer_views
            ↓
    legal_answer_builder

会形成循环依赖。

因此这里采用 Duck Typing：

    StructuredAnswer 只要具有本模块需要的字段即可。

实际运行时传入的仍然是：

    legal_answer_builder.StructuredAnswer
"""

from __future__ import annotations

from typing import Any, Dict, List


# ============================================================
# Constants
# ============================================================

VIEWS_VERSION = "V6.1"


# ============================================================
# Internal Helpers
# ============================================================

def _safe_text(value: Any) -> str:
    """
    安全转换文本。

    这里不引用 legal_answer_builder.safe_text，
    避免产生循环依赖。

    该函数只负责展示层字符串转换，
    不进行任何法律语义处理。
    """

    if value is None:
        return ""

    if isinstance(value, str):
        return value.strip()

    return str(value).strip()


def _is_structured_answer(value: Any) -> bool:
    """
    判断对象是否已经是 StructuredAnswer。

    不直接 import StructuredAnswer，
    从而避免：

        Builder → Views
        Views → Builder

    循环依赖。

    这里只检查展示层所需的关键字段。
    """

    required_attributes = (
        "decision",
        "user_facts",
        "condition_results",
        "required_conditions",
        "exclusion_conditions",
        "exception_conditions",
        "satisfied_conditions",
        "unknown_conditions",
        "not_satisfied_conditions",
        "contract_sequence",
        "legal_rules",
        "selected_rule",
        "explanation",
        "engine_version",
        "builder_version",
    )

    return all(
        hasattr(value, attribute)
        for attribute in required_attributes
    )


def _ensure_structured_answer(value: Any) -> Any:
    """
    确保得到 StructuredAnswer。

    注意：

    Views 模块不负责把 DecisionResult 转换成
    StructuredAnswer。

    如果传入的已经不是 StructuredAnswer，
    这里不会偷偷 import Builder。

    这种情况下抛出明确异常。

    兼容旧 API 的 DecisionResult → StructuredAnswer
    转换由 legal_answer_builder.py 中的兼容包装器负责。
    """

    if _is_structured_answer(value):
        return value

    raise TypeError(
        "legal_answer_views requires StructuredAnswer. "
        "DecisionResult must first be converted by "
        "legal_answer_builder.build_structured_answer()."
    )


# ============================================================
# Contract Sequence Formatting
# ============================================================

def format_contract_sequence(
    sequence: Dict[str, Any],
) -> str:
    """
    将合同序列转换成展示文本。

    注意：

    这里只进行格式化。

    不根据合同次数推导法律条件。
    """

    if not sequence:
        return ""

    count = sequence.get(
        "count",
        0,
    )

    term_type = _safe_text(
        sequence.get(
            "term_type",
            "",
        )
    )

    continuous = sequence.get(
        "continuous",
        False,
    )

    parts = []

    if count:
        parts.append(
            f"合同次数={count}"
        )

    if term_type:
        parts.append(
            f"期限类型={term_type}"
        )

    parts.append(
        "连续=True"
        if continuous
        else "连续=False"
    )

    return "；".join(parts)


# ============================================================
# Condition Group Formatting
# ============================================================

def format_condition_group(
    title: str,
    conditions: List[str],
) -> List[str]:
    """
    格式化条件组。

    这里只生成展示文本。
    """

    lines = [
        title
    ]

    if not conditions:
        lines.append(
            "  - 无"
        )
        return lines

    for condition in conditions:
        lines.append(
            f"  - {condition}"
        )

    return lines


# ============================================================
# Plain Answer View
# ============================================================

def build_plain_answer(
    structured_answer: Any,
) -> str:
    """
    将 StructuredAnswer 转换成适合 Ollama
    使用的纯文本结构。

    注意：

    这里不进行法律推理。

    所有状态来自 StructuredAnswer。
    """

    structured_answer = _ensure_structured_answer(
        structured_answer
    )

    lines: List[str] = []

    lines.append(
        f"Legal Answer Builder "
        f"{structured_answer.builder_version}"
    )

    lines.append(
        ""
    )

    lines.append(
        "【Decision】"
    )

    lines.append(
        _safe_text(
            structured_answer.decision
        )
    )

    lines.append(
        ""
    )

    lines.append(
        "【用户明确事实】"
    )

    if structured_answer.user_facts:
        for fact in (
            structured_answer.user_facts
        ):
            lines.append(
                f"- {fact}"
            )
    else:
        lines.append(
            "- 未提供明确事实"
        )

    lines.append(
        ""
    )

    sequence_text = (
        format_contract_sequence(
            structured_answer.contract_sequence
        )
    )

    if sequence_text:
        lines.append(
            "【合同序列】"
        )
        lines.append(
            sequence_text
        )
        lines.append(
            ""
        )

    lines.extend(
        format_condition_group(
            "【满足条件】",
            structured_answer.satisfied_conditions,
        )
    )

    lines.append(
        ""
    )

    lines.extend(
        format_condition_group(
            "【未知条件】",
            structured_answer.unknown_conditions,
        )
    )

    lines.append(
        ""
    )

    lines.extend(
        format_condition_group(
            "【未满足条件】",
            structured_answer.not_satisfied_conditions,
        )
    )

    lines.append(
        ""
    )

    lines.extend(
        format_condition_group(
            "【REQUIRED 条件】",
            structured_answer.required_conditions,
        )
    )

    lines.append(
        ""
    )

    lines.extend(
        format_condition_group(
            "【EXCLUSION 条件】",
            structured_answer.exclusion_conditions,
        )
    )

    lines.append(
        ""
    )

    lines.extend(
        format_condition_group(
            "【EXCEPTION 条件】",
            structured_answer.exception_conditions,
        )
    )

    lines.append(
        ""
    )

    lines.append(
        "【完整 ConditionResult】"
    )

    for item in (
        structured_answer.condition_results
    ):
        lines.append(
            f"- [{item.condition_type}] "
            f"{item.status}: "
            f"{item.condition}"
        )

        if item.reason:
            lines.append(
                f"  Reason: {item.reason}"
            )

    lines.append(
        ""
    )

    lines.append(
        "【法律规则】"
    )

    if structured_answer.legal_rules:
        for rule in (
            structured_answer.legal_rules
        ):
            lines.append(
                f"- {rule}"
            )
    else:
        lines.append(
            "- 未提供"
        )

    lines.append(
        ""
    )

    lines.append(
        "【Selected Rule】"
    )

    if structured_answer.selected_rule:
        rule_name = structured_answer.selected_rule.get(
            "rule_name",
            "",
        )

        if rule_name:
            lines.append(
                rule_name
            )
        else:
            lines.append(
                "未命名法律规则"
            )
    else:
        lines.append(
            "未提供"
        )

    lines.append(
        ""
    )

    lines.append(
        "【Decision Engine Explanation】"
    )

    if structured_answer.explanation:
        lines.append(
            structured_answer.explanation
        )
    else:
        lines.append(
            "未提供"
        )

    lines.append(
        ""
    )

    lines.append(
        "【Engine Version】"
    )

    lines.append(
        structured_answer.engine_version
        or UNKNOWN
    )

    lines.append(
        ""
    )

    lines.append(
        "【Builder Version】"
    )

    lines.append(
        structured_answer.builder_version
    )

    return "\n".join(
        lines
    )


# ============================================================
# Ollama Answer Context
# ============================================================

def build_answer_context(
    structured_answer: Any,
) -> Dict[str, Any]:
    """
    构建 Ollama 可以使用的结构化 Context。

    目的：

        让 LLM 只能基于 Engine 已经确定的信息回答。

    不在这里进行法律判断。
    """

    structured_answer = _ensure_structured_answer(
        structured_answer
    )

    return {
        "decision":
            structured_answer.decision,

        "user_facts":
            list(
                structured_answer.user_facts
            ),

        "satisfied_conditions":
            list(
                structured_answer.satisfied_conditions
            ),

        "unknown_conditions":
            list(
                structured_answer.unknown_conditions
            ),

        "not_satisfied_conditions":
            list(
                structured_answer.not_satisfied_conditions
            ),

        "required_conditions":
            list(
                structured_answer.required_conditions
            ),

        "exclusion_conditions":
            list(
                structured_answer.exclusion_conditions
            ),

        "exception_conditions":
            list(
                structured_answer.exception_conditions
            ),

        "contract_sequence":
            dict(
                structured_answer.contract_sequence
            ),

        "legal_rules":
            list(
                structured_answer.legal_rules
            ),

        "selected_rule":
            structured_answer.selected_rule,

        "explanation":
            structured_answer.explanation,

        "condition_results": [
            item.to_dict()
            for item in (
                structured_answer.condition_results
            )
        ],

        "engine_version":
            structured_answer.engine_version,

        "builder_version":
            structured_answer.builder_version,
    }


# ============================================================
# Prompt Context
# ============================================================

def build_prompt_context(
    structured_answer: Any,
) -> str:
    """
    构建 Ollama Prompt Context。

    该 Context 明确要求模型：

        1. 不重新推理 Condition
        2. 不改变 Decision
        3. 不把 UNKNOWN 写成确定事实
        4. 不增加不存在的事实
    """

    structured_answer = _ensure_structured_answer(
        structured_answer
    )

    plain_answer = build_plain_answer(
        structured_answer
    )

    return (
        "以下内容来自 Legal Decision Engine "
        "和 Legal Answer Builder。\n"
        "回答时必须严格遵守结构化法律状态，"
        "不得重新创造事实或修改法律条件。\n\n"
        "特别要求：\n"
        "1. 用户事实与法律规则条件必须区分。\n"
        "2. SATISFIED 必须保持为已满足。\n"
        "3. UNKNOWN 必须保持为未知，"
        "不能擅自变成已满足或不满足。\n"
        "4. NOT_SATISFIED 必须保持为未满足。\n"
        "5. CONDITIONAL 必须保持为条件性结论。\n"
        "6. 不得因为合同次数而自动推定所有法律条件成立。\n"
        "7. 不得增加 Decision Engine 没有提供的事实。\n\n"
        "================ STRUCTURED ANSWER "
        "================\n"
        f"{plain_answer}\n"
        "================ END STRUCTURED ANSWER "
        "================"
    )


# ============================================================
# Debug Summary
# ============================================================

def summarize_structured_answer(
    structured_answer: Any,
) -> str:
    """
    输出简洁调试摘要。
    """

    structured_answer = _ensure_structured_answer(
        structured_answer
    )

    total = len(
        structured_answer.condition_results
    )

    required_count = len(
        structured_answer.required_conditions
    )

    exclusion_count = len(
        structured_answer.exclusion_conditions
    )

    exception_count = len(
        structured_answer.exception_conditions
    )

    lines = [
        "Structured Answer Summary",
        "=" * 60,
        f"Decision: {structured_answer.decision}",
        f"User Facts: "
        f"{len(structured_answer.user_facts)}",
        f"Condition Results: {total}",
        f"REQUIRED: {required_count}",
        f"EXCLUSION: {exclusion_count}",
        f"EXCEPTION: {exception_count}",
        f"Satisfied: "
        f"{len(structured_answer.satisfied_conditions)}",
        f"Unknown: "
        f"{len(structured_answer.unknown_conditions)}",
        f"Not Satisfied: "
        f"{len(structured_answer.not_satisfied_conditions)}",
        f"Engine Version: "
        f"{structured_answer.engine_version}",
        f"Builder Version: "
        f"{structured_answer.builder_version}",
    ]

    return "\n".join(
        lines
    )


# ============================================================
# Public API
# ============================================================

__all__ = [
    "VIEWS_VERSION",
    "format_contract_sequence",
    "format_condition_group",
    "build_plain_answer",
    "build_answer_context",
    "build_prompt_context",
    "summarize_structured_answer",
]
