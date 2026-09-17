# -*- coding: utf-8 -*-

"""
RAG V6.0-27
Legal Deterministic Answer Layer

============================================================
功能
============================================================

本模块负责 Legal RAG 的确定性回答层。

主要职责：

    DecisionResult
          ↓
    Deterministic Answer Layer
          ↓
    Deterministic Notices
          ↓
    Deterministic Legal Basis
          ↓
    Deterministic Conclusion
          ↓
    Deterministic Replacement
          ↓
    Final Validation

============================================================

核心原则
============================================================

1. 本模块不重新进行法律推理。

2. Legal Decision Engine 才是法律结论的唯一判断来源。

3. 本模块只根据已经产生的 DecisionResult /
   Structured Decision / Answer Builder 结果生成确定性内容。

4. CONDITIONAL 必须保持条件性。

5. UNKNOWN 不得被本模块自行升级。

6. 用户事实与法律规则必须保持区分。

7. Deterministic Lock 用于防止 Ollama 改写
   Legal Decision Engine 已经确定的最终结论。

8. 本模块的拆分只改变代码组织方式，
   不改变原有法律判断逻辑。

============================================================
"""

from typing import Any, Dict, List


# ============================================================
# Decision 状态
# ============================================================

DECISION_DEFINITE = "DEFINITE"

DECISION_CONDITIONAL = "CONDITIONAL"

DECISION_NOT_ESTABLISHED = "NOT_ESTABLISHED"


# ============================================================
# Answer Condition 状态
# ============================================================

ANSWER_SATISFIED = "SATISFIED"

ANSWER_UNSATISFIED = "UNSATISFIED"

ANSWER_UNKNOWN = "UNKNOWN"


# ============================================================
# 项目内部模块
# ============================================================

from src.legal_common import (
    ensure_list,
    get_field,
    normalize_text,
)

from src.legal_decision_adapter import (
    extract_engine_decision,
    _condition_text,
)

from src.legal_rule_builder import (
    prioritize_legal_rules,
)


def build_deterministic_engine_state_block(
    decision: Dict[str, Any],
) -> str:
    """
    RAG V6.0-27
    构建确定性的 Engine 状态块。

    核心原则：

    1. Engine 是唯一法律条件判定来源。
    2. UNKNOWN 必须 1:1 保留。
    3. 已触发 EXCLUSION 必须 1:1 保留。
    4. 已触发 EXCEPTION 必须 1:1 保留。
    5. Ollama 不得修改这些内容。
    """

    def _condition_text(item: Any) -> str:
        """
        从 ConditionResult / dict / 字符串中提取 condition。
        """

        if isinstance(item, dict):
            return str(
                item.get(
                    "condition",
                    item.get(
                        "description",
                        item,
                    ),
                )
            )

        return str(
            getattr(
                item,
                "condition",
                item,
            )
        )

    unknown_conditions = decision.get(
        "unknown_conditions",
        [],
    ) or []

    triggered_exclusion_conditions = decision.get(
        "triggered_exclusion_conditions",
        [],
    ) or []

    triggered_exception_conditions = decision.get(
        "triggered_exception_conditions",
        [],
    ) or []

    engine_decision = decision.get(
        "engine_decision",
        decision.get(
            "decision",
            "UNKNOWN",
        ),
    )

    lines = []

    lines.append(
        "============================================================"
    )
    lines.append(
        "ENGINE DETERMINISTIC STATE"
    )
    lines.append(
        "============================================================"
    )

    lines.append(
        f"Engine Decision：{engine_decision}"
    )

    # --------------------------------------------------------
    # UNKNOWN
    # --------------------------------------------------------

    lines.append("")
    lines.append(
        f"UNKNOWN 条件数量：{len(unknown_conditions)}"
    )

    if unknown_conditions:

        lines.append(
            "【必须逐项保留的 UNKNOWN 条件】"
        )

        for index, condition in enumerate(
            unknown_conditions,
            start=1,
        ):
            lines.append(
                f"{index}. {_condition_text(condition)}"
            )

    else:

        lines.append(
            "无 UNKNOWN 条件。"
        )

    # --------------------------------------------------------
    # Triggered Exclusions
    # --------------------------------------------------------

    lines.append("")
    lines.append(
        f"已触发 EXCLUSION 数量："
        f"{len(triggered_exclusion_conditions)}"
    )

    if triggered_exclusion_conditions:

        lines.append(
            "【已经触发的 EXCLUSION】"
        )

        for index, condition in enumerate(
            triggered_exclusion_conditions,
            start=1,
        ):
            lines.append(
                f"{index}. {_condition_text(condition)}"
            )

    else:

        lines.append(
            "无已经触发的 EXCLUSION。"
        )

    # --------------------------------------------------------
    # Triggered Exceptions
    # --------------------------------------------------------

    lines.append("")
    lines.append(
        f"已触发 EXCEPTION 数量："
        f"{len(triggered_exception_conditions)}"
    )

    if triggered_exception_conditions:

        lines.append(
            "【已经触发的 EXCEPTION】"
        )

        for index, condition in enumerate(
            triggered_exception_conditions,
            start=1,
        ):
            lines.append(
                f"{index}. {_condition_text(condition)}"
            )

    else:

        lines.append(
            "无已经触发的 EXCEPTION。"
        )

    lines.append("")
    lines.append(
        "============================================================"
    )
    lines.append(
        "END ENGINE DETERMINISTIC STATE"
    )
    lines.append(
        "============================================================"
    )

    return "\n".join(lines)

def build_deterministic_notices(
    decision: Dict[str, Any],
) -> str:
    """
    根据 Engine 的 UNKNOWN 条件生成确定性的【需要注意】。

    核心原则：

    1. UNKNOWN 条件完全来自 Legal Decision Engine。
    2. Ollama 不参与 UNKNOWN 条件的增删。
    3. Ollama 不允许合并 UNKNOWN 条件。
    4. 每一个 UNKNOWN 条件必须逐项输出。
    5. 输出顺序保持 Engine 顺序。
    """

    unknown_conditions = decision.get(
        "unknown_conditions",
        [],
    ) or []

    lines = [
        "【需要注意】"
    ]

    if not unknown_conditions:

        lines.append(
            "当前没有 Engine 标记为 UNKNOWN 的条件。"
        )

        return "\n".join(lines)

    for index, condition in enumerate(
        unknown_conditions,
        start=1,
    ):

        if isinstance(condition, dict):

            condition_text = condition.get(
                "condition",
                condition.get(
                    "description",
                    str(condition),
                ),
            )

        else:

            condition_text = getattr(
                condition,
                "condition",
                str(condition),
            )

        lines.append(
            f"{index}. {condition_text}"
        )

    return "\n".join(lines)

def replace_deterministic_notices(
    answer: str,
    deterministic_notices: str,
) -> str:
    """
    用 Python 确定性生成的【需要注意】替换 Ollama 原有内容。

    核心原则：

    1. 【需要注意】只替换当前章节。
    2. 保留【结论】。
    3. 保留【法律依据】。
    4. 保留【法律分析】。
    5. 不允许因为替换【需要注意】而删除前面的章节。
    6. 【需要注意】应当是最终答案的最后一个正式章节。
    """

    if not answer:
        return deterministic_notices

    marker = "【需要注意】"

    if marker not in answer:

        return (
            answer.rstrip()
            + "\n\n"
            + deterministic_notices
        )

    prefix = answer.split(
        marker,
        1,
    )[0].rstrip()

    return (
        prefix
        + "\n\n"
        + deterministic_notices
    )

def build_deterministic_legal_basis(
    question: str,
    rules: List[Dict[str, Any]],
) -> str:
    """
    根据当前 Structured Rules 确定性生成【法律依据】。

    核心原则：

    1. 法律依据只能来自当前 Structured Rules。
    2. 不允许 Ollama 自行选择、增加或替换法律依据。
    3. CORE 规则优先于 RELATED 规则。
    4. CORE 规则中的 CRITICAL / 核心法条 / structured_rule
       优先作为首要法律依据。
    5. 不凭模型记忆增加法条。
    6. 不将 EXCLUSION / EXCEPTION 条件本身错误地提升为
       核心法律依据。
    """

    if not isinstance(rules, list):
        rules = []

    ordered_rules = prioritize_legal_rules(
        question=question,
        rules=rules,
    )

    core_basis_lines = []
    related_basis_lines = []

    seen_basis = set()

    for rule in ordered_rules:

        if not isinstance(rule, dict):
            continue

        law_name = normalize_text(
            rule.get(
                "law_name",
                "",
            )
        )

        article_number = normalize_text(
            rule.get(
                "article_number",
                "",
            )
        )

        if not law_name or not article_number:
            continue

        citation = (
            f"《{law_name}》"
            f"{article_number}"
        )

        if citation in seen_basis:
            continue

        seen_basis.add(
            citation
        )

        priority = normalize_text(
            rule.get(
                "rule_priority",
                "RELATED",
            )
        ).upper()

        if priority == "CORE":

            core_basis_lines.append(
                citation
            )

        else:

            related_basis_lines.append(
                citation
            )

    lines = [
        "【法律依据】"
    ]

    if core_basis_lines:

        lines.append(
            "【核心法律依据】"
        )

        lines.extend(
            f"{index}. {citation}"
            for index, citation in enumerate(
                core_basis_lines,
                start=1,
            )
        )

    if related_basis_lines:

        lines.append(
            "【相关法律依据】"
        )

        start_index = (
            len(core_basis_lines)
            + 1
        )

        lines.extend(
            f"{index}. {citation}"
            for index, citation in enumerate(
                related_basis_lines,
                start=start_index,
            )
        )

    if len(lines) == 1:

        lines.append(
            "当前没有可用于最终回答的结构化法律依据。"
        )

    return "\n".join(lines)

def build_deterministic_conclusion(
    decision: Dict[str, Any],
) -> str:
    """
    根据 Legal Decision Engine 的最终 Decision，
    确定性生成【结论】。

    核心原则：

    1. Decision Engine 是最终法律结论的唯一来源。
    2. Ollama 不得决定 DEFINITE / CONDITIONAL / NOT_ESTABLISHED。
    3. Ollama 不得把 CONDITIONAL 改写成 NOT_ESTABLISHED。
    4. Ollama 不得把 UNKNOWN 改写成 NOT_SATISFIED。
    5. Python 最终覆盖 Ollama 原有【结论】。
    6. 结论只允许表达 Engine 已经确认的状态。
    """

    engine_decision = extract_engine_decision(
        decision
    )

    condition_results = ensure_list(
        get_field(
            decision,
            "condition_results",
            [],
        )
    )

    required_satisfied = []
    required_not_satisfied = []
    unknown_conditions = []

    triggered_exclusions = []
    triggered_exceptions = []

    for item in condition_results:

        if not isinstance(item, dict):
            continue

        condition = normalize_text(
            item.get(
                "condition",
                "",
            )
        )

        status = normalize_text(
            item.get(
                "status",
                "",
            )
        ).upper()

        condition_type = normalize_text(
            item.get(
                "condition_type",
                item.get(
                    "type",
                    "REQUIRED",
                ),
            )
        ).upper()

        if not condition:
            continue

        # ----------------------------------------------------
        # REQUIRED
        # ----------------------------------------------------

        if condition_type == "REQUIRED":

            if status == ANSWER_SATISFIED:

                required_satisfied.append(
                    condition
                )

            elif status in {
                "NOT_SATISFIED",
                ANSWER_UNSATISFIED,
            }:

                required_not_satisfied.append(
                    condition
                )

            elif status == ANSWER_UNKNOWN:

                unknown_conditions.append(
                    condition
                )

        # ----------------------------------------------------
        # EXCLUSION
        #
        # EXCLUSION + NOT_SATISFIED
        # = 排除条件已经触发
        # ----------------------------------------------------

        elif condition_type == "EXCLUSION":

            if status in {
                "NOT_SATISFIED",
                ANSWER_UNSATISFIED,
            }:

                triggered_exclusions.append(
                    condition
                )

            elif status == ANSWER_UNKNOWN:

                unknown_conditions.append(
                    condition
                )

        # ----------------------------------------------------
        # EXCEPTION
        #
        # EXCEPTION + NOT_SATISFIED
        # = 例外条件已经触发
        # ----------------------------------------------------

        elif condition_type == "EXCEPTION":

            if status in {
                "NOT_SATISFIED",
                ANSWER_UNSATISFIED,
            }:

                triggered_exceptions.append(
                    condition
                )

            elif status == ANSWER_UNKNOWN:

                unknown_conditions.append(
                    condition
                )

    # ========================================================
    # DEFINITE
    # ========================================================

    if engine_decision == DECISION_DEFINITE:

        return (
            "Decision Engine 已确认当前满足相关法律条件，"
            "可以作出确定性法律结论。"
        )

    # ========================================================
    # CONDITIONAL
    # ========================================================

    if engine_decision == DECISION_CONDITIONAL:

        lines = [
            "Decision Engine 判定当前法律结论为条件性结论。"
        ]

        if required_satisfied:

            lines.append(
                "当前已经确认满足以下条件："
                + "、".join(
                    required_satisfied
                )
                + "。"
            )

        if unknown_conditions:

            lines.append(
                "但当前仍存在尚未确认的条件，"
                "因此暂时不能作出确定性结论。"
            )

        if triggered_exclusions:

            lines.append(
                "同时，以下排除条件已经触发："
                + "、".join(
                    triggered_exclusions
                )
                + "。"
            )

        if triggered_exceptions:

            lines.append(
                "同时，以下例外条件已经触发："
                + "、".join(
                    triggered_exceptions
                )
                + "。"
            )

        return "\n".join(
            lines
        )

    # ========================================================
    # NOT_ESTABLISHED
    # ========================================================

    if engine_decision == DECISION_NOT_ESTABLISHED:

        lines = [
            "Decision Engine 已确认当前不能认定满足相关法律条件。"
        ]

        if required_not_satisfied:

            lines.append(
                "原因是以下必备条件已经确认未满足："
                + "、".join(
                    required_not_satisfied
                )
                + "。"
            )

        if triggered_exclusions:

            lines.append(
                "同时，以下排除条件已经触发："
                + "、".join(
                    triggered_exclusions
                )
                + "。"
            )

        if triggered_exceptions:

            lines.append(
                "同时，以下例外条件已经触发："
                + "、".join(
                    triggered_exceptions
                )
                + "。"
            )

        return "\n".join(
            lines
        )

    # ========================================================
    # 未知 Decision
    # ========================================================

    return (
        "Decision Engine 未返回有效的最终法律结论。"
    )

def replace_deterministic_conclusion(
    answer: str,
    deterministic_conclusion: str,
) -> str:
    """
    用 Python 确定性生成的【结论】
    替换 Ollama 原有【结论】内容。

    核心原则：

    1. Ollama 不负责最终法律结论。
    2. 只替换【结论】章节。
    3. 必须保留【法律依据】。
    4. 必须保留【法律分析】。
    5. 必须保留【需要注意】。
    """

    if not answer:
        return (
            "【结论】\n"
            + deterministic_conclusion
        )

    marker = "【结论】"

    if marker not in answer:

        return (
            marker
            + "\n"
            + deterministic_conclusion
            + "\n\n"
            + answer.lstrip()
        )

    before_conclusion, after_conclusion = (
        answer.split(
            marker,
            1,
        )
    )

    next_markers = [
        "【法律依据】",
        "【法律分析】",
        "【需要注意】",
    ]

    next_positions = []

    for next_marker in next_markers:

        position = after_conclusion.find(
            next_marker
        )

        if position >= 0:

            next_positions.append(
                position
            )

    if next_positions:

        next_position = min(
            next_positions
        )

        remaining_sections = (
            after_conclusion[
                next_position:
            ].lstrip()
        )

        return (
            before_conclusion.rstrip()
            + "\n\n"
            + "【结论】"
            + "\n"
            + deterministic_conclusion
            + "\n\n"
            + remaining_sections
        )

    return (
        before_conclusion.rstrip()
        + "\n\n"
        + "【结论】"
        + "\n"
        + deterministic_conclusion
    )

def replace_deterministic_legal_basis(
    answer: str,
    deterministic_legal_basis: str,
) -> str:
    """
    用 Python 确定性生成的【法律依据】
    替换 Ollama 原有的【法律依据】内容。

    核心原则：

    1. Ollama 不得自行选择最终法律依据。
    2. Ollama 不得删除 Structured Rules 已确定的核心法律依据。
    3. Ollama 不得将 RELATED 法条提升为 CORE 法条。
    4. Ollama 不得增加当前 Structured Rules 之外的新法条。
    5. 只替换【法律依据】章节本身。
    6. 必须保留【法律分析】。
    7. 必须保留【需要注意】。
    8. 不允许因为替换法律依据而删除后续章节。
    """

    if not answer:
        return deterministic_legal_basis

    marker = "【法律依据】"

    if marker not in answer:
        return (
            answer.rstrip()
            + "\n\n"
            + deterministic_legal_basis
        )

    before_basis, after_basis = answer.split(
        marker,
        1,
    )

    before_basis = before_basis.rstrip()

    # --------------------------------------------------------
    # 查找【法律依据】之后的下一个正式章节
    #
    # 注意：
    #
    # 【法律依据】后面可能继续存在：
    #
    # 【法律分析】
    # 【需要注意】
    #
    # 必须保留这些章节，不能像旧版本一样
    # 直接丢弃 after_basis。
    # --------------------------------------------------------

    next_markers = [
        "【法律分析】",
        "【需要注意】",
        "【结论】",
    ]

    next_positions = []

    for next_marker in next_markers:
        position = after_basis.find(
            next_marker
        )

        if position >= 0:
            next_positions.append(
                position
            )

    # --------------------------------------------------------
    # 找到后续章节
    # --------------------------------------------------------

    if next_positions:

        next_position = min(
            next_positions
        )

        remaining_sections = (
            after_basis[
                next_position:
            ].lstrip()
        )

        return (
            before_basis
            + "\n\n"
            + deterministic_legal_basis
            + "\n\n"
            + remaining_sections
        )

    # --------------------------------------------------------
    # 没有后续章节
    #
    # 直接用确定性的法律依据替换
    # Ollama 原有法律依据。
    # --------------------------------------------------------

    return (
        before_basis
        + "\n\n"
        + deterministic_legal_basis
    )
