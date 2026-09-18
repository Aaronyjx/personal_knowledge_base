# -*- coding: utf-8 -*-

"""
RAG V6.0-27

Legal Condition Validator

============================================================
功能
============================================================

负责 Legal RAG 的 Condition Safety 验证。

包含：

1. validate_answer_structure()
2. validate_no_manufactured_unknown()
3. validate_legal_condition_invention()
4. validate_conditional_state()
5. validate_unknown_conditions()

============================================================
职责边界
============================================================

本模块只负责：

    Condition Safety

具体包括：

    1. 答案结构安全
    2. 禁止制造不存在的 UNKNOWN
    3. 禁止臆造法律条件
    4. CONDITIONAL 状态安全
    5. UNKNOWN 条件语义保真

============================================================
本模块不负责
============================================================

- 用户事实忠实性
- Fact → Condition 映射
- DecisionResult 生成
- Legal Decision Engine 判定
- Decision Adapter
- Answer Builder
- Ollama 调用
- 法律依据 / Citation Validation
- Decision Consistency
- Final Validation
- Fallback
- 重新计算法律结论

============================================================
设计原则
============================================================

Validator 只能验证已经产生的结构化结果。

不得在 Validation 阶段重新推导法律结论。

============================================================
版本
============================================================

V6.0-27
"""

import re

from typing import (
    Any,
    Dict,
    List,
)

from src.legal_common import (
    ensure_list,
    normalize_text,
)

from src.legal_answer_sanitizer import (
    REQUIRED_SECTIONS,
)


# ============================================================
# Legal Decision Engine 状态
# ============================================================

DECISION_CONDITIONAL = "CONDITIONAL"


def validate_answer_structure(
    answer: str,
) -> bool:

    if not answer:
        return False

    for section in REQUIRED_SECTIONS:

        if answer.count(section) != 1:
            return False

    # 检查标题顺序。

    positions = [
        answer.find(section)
        for section in REQUIRED_SECTIONS
    ]

    if positions != sorted(positions):
        return False

    return True


def validate_no_manufactured_unknown(
    answer: str,
    decision: Dict[str, Any],
) -> bool:
    """
    V6.0-27：禁止对已经明确存在的合同事实再次制造 UNKNOWN。

    注意：

    “续订劳动合同”本身仍然可以是 Engine 返回的 UNKNOWN。
    本检查只禁止把用户已经明确给出的：

        公司连续签订三次固定期限劳动合同

    再写成“第三份合同是否存在”等重复事实确认。
    """

    facts = ensure_list(
        decision.get("user_facts", [])
    )

    fact_text = "；".join(
        normalize_text(item)
        for item in facts
    )

    if not (
        "三次" in fact_text
        and "固定期限劳动合同" in fact_text
    ):
        return True

    answer_text = normalize_text(answer)

    forbidden = [
        "第三次合同是否存在",
        "第三次合同是否已经存在",
        "第三份合同是否存在",
        "第三份合同是否已经存在",
        "是否已经签订第三份合同",
        "是否已经签订第三次合同",
        "第三次是否属于连续合同序列",
        "第三次合同是否属于连续合同序列",
    ]

    unresolved = [
        "是否",
        "尚不明确",
        "尚未明确",
        "无法确认",
        "不能确认",
        "需要进一步确认",
        "需进一步确认",
        "仍需确认",
        "需要进一步判断",
        "需进一步判断",
        "无法判断",
        "不能判断",
        "尚待确认",
        "待确认",
    ]

    for pattern in forbidden:
        if pattern in answer_text and any(
            marker in answer_text
            for marker in unresolved
        ):
            return False

    return True


def validate_legal_condition_invention(
    answer: str,
    decision: Dict[str, Any],
) -> bool:
    """
    V6.0-27：法律条件防臆造验证。

    核心原则：

        Ollama 只能表达 Structured Decision / Rules 中已经存在的
        法律条件，不能自行创造新的法律前提、例外或义务条件。

    V6.0-19 暴露的问题：

        Structured Decision = CONDITIONAL
                ↓
        Ollama 自行补充“劳动者未明确提出订立无固定期限劳动合同”等条件
                ↓
        原有 UNKNOWN / CONDITIONAL Validation 仍可能通过

    因此 V6.0-22 增加一层独立验证：

    1. 收集当前 Structured Rules 的全部结构化文本。
    2. 对明显的“法律条件发明”表达进行拦截。
    3. 特别禁止把“劳动者未提出订立无固定期限劳动合同”写成
       无固定期限劳动合同的前置条件，除非 Structured Rules 明确包含
       该条件。
    4. 禁止使用笼统的“劳动者不符合条件”替代具体结构化法律条件。
    5. 不禁止合法引用 Rules 中真实存在的“劳动者提出订立固定期限劳动合同”
       等条件；是否允许必须以 Structured Rules 实际内容为准。

    返回：
        True  = 未发现结构化法律条件之外的明显新增条件。
        False = 发现法律条件臆造。
    """

    if not answer:
        return False

    answer_text = normalize_text(answer)

    rules = ensure_list(
        decision.get(
            "rules",
            [],
        )
    )

    # --------------------------------------------------------
    # 构建 Structured Rules 文本。
    # --------------------------------------------------------
    #
    # 不要求规则必须使用固定字段。
    # 尽可能收集所有常见结构化字段，避免误伤真实规则条件。
    # --------------------------------------------------------

    rule_text_parts = []

    preferred_fields = [
        "law_name",
        "article_number",
        "article_text",
        "rule_summary",
        "condition",
        "conditions",
        "requirements",
        "requirement",
        "exception",
        "exceptions",
        "rule_text",
        "text",
        "legal_effect",
        "legal_consequence",
    ]

    def append_rule_value(value: Any):
        if isinstance(value, dict):
            for nested_value in value.values():
                append_rule_value(nested_value)
        elif isinstance(value, list):
            for nested_value in value:
                append_rule_value(nested_value)
        else:
            text = normalize_text(value)
            if text:
                rule_text_parts.append(text)

    for rule in rules:
        if isinstance(rule, dict):
            for field in preferred_fields:
                if field in rule:
                    append_rule_value(rule.get(field))
        else:
            append_rule_value(rule)

    rule_text = "；".join(rule_text_parts)

    # --------------------------------------------------------
    # 明显的法律条件臆造模式。
    # --------------------------------------------------------
    #
    # 注意：
    #
    # 不能仅仅因为回答“提到了”错误条件，就认定模型臆造了该条件。
    #
    # 例如：
    #
    #     “不能将‘劳动者未提出订立无固定期限劳动合同’
    #      作为本题的判断前提。”
    #
    # 这是在“否定错误条件”，不是在“创造错误条件”。
    #
    # 因此必须区分：
    #
    #     正向使用错误条件
    #
    # 与：
    #
    #     否定 / 禁止 / 纠正错误条件
    #
    # --------------------------------------------------------

    invented_patterns = [
        "劳动者未明确提出订立无固定期限劳动合同",
        "劳动者未提出订立无固定期限劳动合同",
        "劳动者未明确提出签订无固定期限劳动合同",
        "劳动者未提出签订无固定期限劳动合同",
        "劳动者没有提出订立无固定期限劳动合同",
        "劳动者没有提出签订无固定期限劳动合同",
        "劳动者未明确要求订立无固定期限劳动合同",
        "劳动者未明确要求签订无固定期限劳动合同",
        "劳动者没有要求订立无固定期限劳动合同",
        "劳动者没有要求签订无固定期限劳动合同",
        "劳动者必须明确提出订立无固定期限劳动合同",
        "劳动者必须明确提出签订无固定期限劳动合同",
        "劳动者必须提出订立无固定期限劳动合同",
        "劳动者必须提出签订无固定期限劳动合同",
        "劳动者需要明确提出订立无固定期限劳动合同",
        "劳动者需要明确提出签订无固定期限劳动合同",
        "劳动者需要提出订立无固定期限劳动合同",
        "劳动者需要提出签订无固定期限劳动合同",
        "劳动者不符合订立无固定期限劳动合同的条件",
        "劳动者不符合签订无固定期限劳动合同的条件",
        "劳动者不符合无固定期限劳动合同的条件",
        "劳动者不具备订立无固定期限劳动合同的条件",
        "劳动者不具备签订无固定期限劳动合同的条件",
        "劳动者不具备无固定期限劳动合同的条件",
    ]

    # --------------------------------------------------------
    # 判断某个错误条件是否只是被“否定/禁止/纠正”提及。
    # --------------------------------------------------------

    negation_patterns = [
        "不能将",
        "不能把",
        "不得将",
        "不得把",
        "不应将",
        "不应把",
        "禁止将",
        "禁止把",
        "不可将",
        "不可把",
        "不宜将",
        "不能认为",
        "不得认为",
        "不应认为",
        "不能视为",
        "不得视为",
        "不应视为",
        "并不能证明",
        "不能证明",
        "不足以证明",
        "不足以认定",
        "不能据此认定",
        "不能据此认为",
        "不属于",
        "并非",
        "不是",
        "并不能作为",
        "不能作为",
        "不得作为",
        "不应作为",
        "不应当作为",
    ]

    # --------------------------------------------------------
    # 逐项检查。
    # --------------------------------------------------------

    for pattern in invented_patterns:

        position = answer_text.find(pattern)

        if position < 0:
            continue

        # 取出错误条件前面的有限上下文。
        #
        # 中文法律回答中，否定性表达通常会紧邻被否定的条件。
        context_start = max(
            0,
            position - 40,
        )

        prefix_context = answer_text[
            context_start:position
        ]

        # 如果错误条件只是出现在：
        #
        #     不能将……
        #     不得把……
        #     不能证明……
        #
        # 等纠错性上下文中，则不能判定为“臆造”。
        if any(
            marker in prefix_context
            for marker in negation_patterns
        ):
            continue

        # 如果 Structured Rules 明确存在该条件，
        # 则也不能视为新条件。
        if pattern in rule_text:
            continue

        # 到这里才认为模型真正把该错误条件当作
        # 当前法律判断的一个实质性前提。
        return False

    # 如果 Rules 中没有对应条件，则属于新增法律条件。
    for pattern in invented_patterns:
        if pattern in answer_text and pattern not in rule_text:
            return False

    # --------------------------------------------------------
    # “其他法定条件”笼统化检查。
    # --------------------------------------------------------
    #
    # “其他法定条件”本身不是法律依据。
    # 如果它被写成当前 UNKNOWN / 免责条件，而 Rules 中没有
    # 对应的具体例外或条件，就属于模型自行扩张。
    # --------------------------------------------------------

    vague_condition_patterns = [
        "其他法定条件",
        "其他法律条件",
        "其他法定要求",
        "其他法律要求",
        "不符合其他法定条件",
        "不符合其他法律条件",
        "存在其他法定条件",
        "存在其他法律条件",
    ]

    has_structured_exception = any(
        field in rule_text
        for field in [
            "例外",
            "除外",
            "不适用",
            "终止",
            "解除",
            "固定期限劳动合同",
        ]
    )

    # 仅当模型把笼统条件写成新的判断依据时拦截。
    # “结构化法律规则中仍存在尚未确认的条件”属于流程性表达，
    # 不在这里拦截。
    for pattern in vague_condition_patterns:
        if pattern not in answer_text:
            continue

        structural_reference_patterns = [
            "结构化",
            "规则中",
            "法律依据中",
            "法律规则中",
            "已经确认",
            "尚未确认",
            "未确认",
        ]

        if any(
            marker in answer_text
            for marker in structural_reference_patterns
        ):
            continue

        if not has_structured_exception:
            return False

    return True


def validate_conditional_state(
    answer: str,
    decision: Dict[str, Any],
) -> bool:

    engine_status = normalize_text(
        decision.get(
            "engine_decision",
            "",
        )
    ).upper()

    if engine_status != DECISION_CONDITIONAL:
        return True

    # CONDITIONAL 状态必须保留条件性。
    #
    # 检查是否存在明显的绝对性表达。

    absolute_patterns = [
        "一定必须",
        "必然必须",
        "当然必须",
        "无条件必须",
        "肯定必须",
        "一定应当",
        "必然应当",
    ]

    for pattern in absolute_patterns:

        if pattern in answer:
            return False

    # 至少应当出现一个条件性表达。

    conditional_patterns = [
        "如果",
        "若",
        "在",
        "条件成立",
        "符合条件",
        "视情况",
        "视具体情况",
        "取决于",
        "仍需结合",
        "还需结合",
        "尚需确认",
        "仍需确认",
        "仍待确认",
        "需要进一步确认",
        "需要进一步核实",
        "还需进一步判断",
        "不能直接认定",
        "无法直接认定",
        "尚不能认定",
        "尚不能确认",
        "无法作出最终判断",
        "不能作出最终判断",
    ]

    for pattern in conditional_patterns:

        if pattern in answer:
            return True

    return False


def validate_unknown_conditions(
    answer: str,
    decision: Dict[str, Any],
) -> bool:
    """
    V6.0-16 UNKNOWN 语义验证。

    V6.0-13 的问题是：
    UNKNOWN 验证只接受少量固定关键词。
    Ollama 即使正确表达“该事实目前无法确认”，
    只要没有命中固定词表，也会被误判为 UNKNOWN FAIL。

    V6.0-15 改为“语义标记 + 结构化 UNKNOWN 内容”双重验证：

    1. 接受多种表达“未知/待核实/材料不足/无法作出最终判断”的句式。
    2. 同时允许 UNKNOWN 条件本身出现在回答中。
    3. 对明显的确定性表达保持保守，不因为出现“条件”二字就通过。

    V6.0-16 修复：

    1. 不再因为命中任意一个 UNKNOWN 语义关键词就直接返回 True。
    2. 当 Engine 存在多个 UNKNOWN 条件时，逐项验证 UNKNOWN 条件是否被回答保留。
    3. 明确支持：
           “UNKNOWN”
           “未知”
           “尚未确认”
           “尚不明确”
           “无法确认”
           “待进一步确认”
           等表达。
    4. 如果回答明确列出了 Engine 的 UNKNOWN 条件，
       即使没有使用“无法确认”等固定句式，也允许通过。
    5. 中文条件没有天然空格，因此不再依赖 split()
       来判断 UNKNOWN 条件是否出现。
    6. 对较长条件使用“关键片段”匹配，而不是要求完整字符串完全一致。
    7. 至少要求大部分 UNKNOWN 条件被正确表达，
       防止模型只写一个 UNKNOWN 条件就通过。
    8. 如果回答明确声明“其他条件状态为 UNKNOWN”，
       并完整列出 Engine 的 UNKNOWN 条件，应当通过。
    """

    unknown = ensure_list(
        decision.get(
            "unknown_conditions",
            [],
        )
    )

    # --------------------------------------------------------
    # Engine 没有 UNKNOWN 条件
    # --------------------------------------------------------
    #
    # 如果 Decision Engine 没有任何 UNKNOWN 条件，
    # 那么回答中自然不需要表达 UNKNOWN。
    # --------------------------------------------------------

    if not unknown:
        return True

    answer_text = normalize_text(answer)

    if not answer_text:
        return False

    # ========================================================
    # 第一层：广义 UNKNOWN / 待确认语义标记
    # ========================================================
    #
    # 不再依赖单一固定短语。
    # 这些表达均可以合理表示“当前材料不足以确认”。
    #
    # V6.0-16 新增：
    #
    #   UNKNOWN
    #   未知
    #   未确定
    #   状态为 UNKNOWN
    #   条件为 UNKNOWN
    #   尚不确定
    #
    # 这是因为 Ollama 可能直接复制 Engine 的结构化状态，
    # 而不是改写成“无法确认”。
    # --------------------------------------------------------

    unresolved_patterns = [
        "UNKNOWN",
        "unknown",
        "未知",
        "未确定",
        "尚未确定",
        "未能确定",
        "未确认",
        "尚未提供",
        "未提供",
        "没有提供",
        "未说明",
        "尚未说明",
        "没有说明",
        "未明确",
        "尚未明确",
        "尚未确认",
        "尚不明确",
        "尚不确定",
        "无法确认",
        "不能确认",
        "难以确认",
        "不足以确认",
        "无法判断",
        "不能判断",
        "难以判断",
        "无法作出判断",
        "不能作出判断",
        "无法作出最终判断",
        "不能作出最终判断",
        "无法作出最终认定",
        "不能作出最终认定",
        "无法直接认定",
        "不能直接认定",
        "尚不能认定",
        "尚不能确认",
        "尚不能判断",
        "目前不能确认",
        "目前无法确认",
        "目前无法判断",
        "目前无法认定",
        "当前不能确认",
        "当前无法确认",
        "当前无法判断",
        "当前无法认定",
        "现阶段无法",
        "现阶段不能",
        "现有材料不足",
        "材料不足",
        "事实不足",
        "证据不足以确认",
        "信息不足以确认",
        "目前材料不足以",
        "现有信息不足以",
        "需要进一步确认",
        "需要进一步核实",
        "还需要进一步确认",
        "还需进一步确认",
        "还需要核实",
        "仍需确认",
        "仍需进一步确认",
        "仍待确认",
        "待进一步确认",
        "待核实",
        "有待核实",
        "尚待核实",
        "尚需确认",
        "尚需进一步确认",
        "需要补充事实",
        "需要补充材料",
        "需要补充信息",
        "需补充事实",
        "需补充材料",
        "需补充信息",
        "最终结论仍取决于",
        "最终判断仍取决于",
        "还需结合",
        "仍需结合",
        "需要结合其他",
        "是否存在其他法定情形尚不能",
        "是否存在法定例外目前无法",
    ]

    has_unresolved_marker = any(
        pattern in answer_text
        for pattern in unresolved_patterns
    )

    # ========================================================
    # 第二层：提取 Engine 的 UNKNOWN 条件
    # ========================================================
    #
    # V6.0-16 不再使用：
    #
    #     condition_core.split()
    #
    # 因为中文条件通常没有空格。
    #
    # 例如：
    #
    #     劳动者提出或者同意续订、订立劳动合同
    #
    # 整个字符串很可能被 split() 当成一个 token。
    #
    # 因此这里直接对中文连续字符串进行关键片段匹配。
    # ========================================================

    normalized_conditions: List[str] = []

    for item in unknown:

        if isinstance(item, dict):

            condition = normalize_text(
                item.get(
                    "condition",
                    item.get(
                        "description",
                        "",
                    ),
                )
            )

        else:

            condition = normalize_text(item)

        if condition:
            normalized_conditions.append(condition)

    # --------------------------------------------------------
    # 如果 Engine 有 UNKNOWN，但没有成功提取条件文本，
    # 则退回到 UNKNOWN 语义标记验证。
    # --------------------------------------------------------

    if not normalized_conditions:

        return has_unresolved_marker

    # ========================================================
    # V6.0-27 Condition Status Fidelity
    # ========================================================
    #
    # Engine 明确返回 UNKNOWN 的条件：
    #
    #     UNKNOWN
    #
    # 不允许 Ollama 在最终答案中将其改写成：
    #
    #     SATISFIED
    #     NOT_SATISFIED
    #
    # 注意：
    #
    # 这里不能简单地全局搜索：
    #
    #     “满足”
    #     “不满足”
    #
    # 因为合法的 UNKNOWN 表达本身可能包含：
    #
    #     “是否满足该条件目前尚不能确认”
    #
    # 因此必须把：
    #
    #     UNKNOWN 条件
    #
    # 与：
    #
    #     明确状态表达
    #
    # 进行条件级关联。
    #
    # ========================================================

    def condition_status_conflict(
        condition: str,
    ) -> bool:
        """
        V6.0-27：检测 Engine UNKNOWN 条件是否被答案篡改状态。

        返回：

            True
                = 发现 UNKNOWN → SATISFIED /
                  UNKNOWN → NOT_SATISFIED

            False
                = 未发现明确状态篡改。

        这里只验证状态保真，
        不重新判断法律条件本身。
        """

        condition = normalize_text(condition)

        if not condition:
            return False

        condition_core = re.sub(
            r"[，。；：、（）()【】\[\]“”‘’：;,.!?！？]",
            "",
            condition,
        ).strip()

        if not condition_core:
            return False

        # ----------------------------------------------------
        # 建立当前 UNKNOWN 条件的识别片段。
        # ----------------------------------------------------

        fragments: List[str] = []

        if len(condition_core) >= 4:
            fragments.append(condition_core)

        if len(condition_core) >= 8:
            fragments.append(condition_core[:8])

        if len(condition_core) >= 12:
            fragments.append(condition_core[:12])

        if len(condition_core) >= 16:
            fragments.append(condition_core[:16])

        legal_keywords = [
            "续订劳动合同",
            "提出或者同意续订",
            "提出或者同意订立",
            "第三十九条规定的情形",
            "第四十条第一项规定的情形",
            "第四十条第二项规定的情形",
            "提出订立固定期限劳动合同",
        ]

        for keyword in legal_keywords:

            if keyword in condition_core:
                fragments.append(keyword)

        # 去重。
        unique_fragments: List[str] = []

        for fragment in fragments:

            fragment = fragment.strip()

            if not fragment:
                continue

            if fragment not in unique_fragments:
                unique_fragments.append(fragment)

        if not unique_fragments:
            return False

        # ----------------------------------------------------
        # 强状态表达。
        #
        # 只使用能够明确表示 Condition Status 的表达，
        # 避免把“是否满足”“满足条件后”等正常语言误判。
        # ----------------------------------------------------

        satisfied_patterns = [
            "SATISFIED",
            "状态为SATISFIED",
            "状态：SATISFIED",
            "状态:Satisfied",
            "已满足条件",
            "已满足",
            "满足该条件",
            "满足这一条件",
            "该条件成立",
            "条件已经成立",
            "条件已成立",
        ]

        not_satisfied_patterns = [
            "NOT_SATISFIED",
            "状态为NOT_SATISFIED",
            "状态：NOT_SATISFIED",
            "状态:NOT_SATISFIED",
            "UNSATISFIED",
            "状态为UNSATISFIED",
            "不满足条件",
            "不满足该条件",
            "不满足这一条件",
            "该条件不成立",
            "条件不成立",
            "条件未成立",
            "未满足该条件",
            "未满足这一条件",
        ]

        unresolved_patterns_local = [
            "UNKNOWN",
            "状态为UNKNOWN",
            "状态：UNKNOWN",
            "状态:UNKNOWN",
            "未知",
            "未确定",
            "未确认",
            "尚未确认",
            "尚不明确",
            "尚不确定",
            "无法确认",
            "不能确认",
            "不足以确认",
            "无法判断",
            "不能判断",
            "尚不能认定",
            "尚不能确认",
            "待进一步确认",
            "仍需确认",
            "尚需确认",
            "有待核实",
        ]

        # ----------------------------------------------------
        # 对每一个识别片段寻找其在答案中的位置。
        #
        # 使用局部窗口，而不是全局关键词判断。
        # ----------------------------------------------------

        for fragment in unique_fragments:

            search_start = 0

            while True:

                position = answer_text.find(
                    fragment,
                    search_start,
                )

                if position < 0:
                    break

                context_start = max(
                    0,
                    position - 100,
                )

                context_end = min(
                    len(answer_text),
                    position + len(fragment) + 120,
                )

                context = answer_text[
                    context_start:context_end
                ]

                # ------------------------------------------------
                # 如果当前局部上下文明确属于 UNKNOWN 表达，
                # 则 SATISFIED / NOT_SATISFIED 关键词不能简单
                # 通过“上下文碰巧出现”来判定冲突。
                #
                # 例如：
                #
                #     是否满足该条件，目前尚不能确认
                #
                # 这里是合法 UNKNOWN。
                # ------------------------------------------------

                has_unresolved = any(
                    marker in context
                    for marker in unresolved_patterns_local
                )

                # ------------------------------------------------
                # 明确的结构化状态标签。
                #
                # 例如：
                #
                #     已满足条件：
                #     - 续订劳动合同
                #
                #     不满足的必备条件：
                #     - 续订劳动合同
                #
                #     状态：SATISFIED
                #     条件状态：NOT_SATISFIED
                # ------------------------------------------------

                explicit_satisfied = any(
                    pattern in context
                    for pattern in satisfied_patterns
                )

                explicit_not_satisfied = any(
                    pattern in context
                    for pattern in not_satisfied_patterns
                )

                # ------------------------------------------------
                # 如果同一局部上下文同时存在明确的 UNKNOWN
                # 和确定性状态，需要进一步判断。
                #
                # “UNKNOWN 条件目前已经满足”属于状态矛盾，
                # 仍然必须拦截。
                #
                # 只有真正的“是否满足……尚不能确认”这种
                # 未决表达才允许保留。
                # ------------------------------------------------

                if explicit_satisfied:

                    if not has_unresolved:
                        return True

                    # 对于：
                    #
                    #     “是否满足该条件目前尚不能确认”
                    #
                    # 不能因为“满足”两个字出现就误判。
                    #
                    # 如果同时出现结构化“已满足条件”、
                    # “状态为 SATISFIED”等强状态标签，
                    # 即使附近还有 UNKNOWN，也必须拦截。
                    strong_satisfied = any(
                        pattern in context
                        for pattern in [
                            "SATISFIED",
                            "状态为SATISFIED",
                            "状态：SATISFIED",
                            "已满足条件",
                            "状态为 SATISFIED",
                            "条件状态：SATISFIED",
                        ]
                    )

                    if strong_satisfied:
                        return True

                if explicit_not_satisfied:

                    if not has_unresolved:
                        return True

                    strong_not_satisfied = any(
                        pattern in context
                        for pattern in [
                            "NOT_SATISFIED",
                            "状态为NOT_SATISFIED",
                            "状态：NOT_SATISFIED",
                            "UNSATISFIED",
                            "不满足条件",
                            "状态为 NOT_SATISFIED",
                            "条件状态：NOT_SATISFIED",
                        ]
                    )

                    if strong_not_satisfied:
                        return True

                search_start = (
                    position + len(fragment)
                )

        return False

    # ========================================================
    # V6.0-27：逐项检查 UNKNOWN 状态是否被篡改。
    # ========================================================

    for condition in normalized_conditions:

        if condition_status_conflict(condition):

            return False

    # ========================================================
    # 第三层：为每一个 UNKNOWN 条件提取关键片段
    # ========================================================
    #
    # 目的不是要求模型逐字复制条件，
    # 而是判断该 UNKNOWN 条件是否被实际表达。
    #
    # 例如 Engine：
    #
    #     劳动者提出或者同意续订、订立劳动合同
    #
    # 回答：
    #
    #     劳动者是否提出或者同意续订、订立劳动合同，
    #     目前尚未确认。
    #
    # 应当判定为该 UNKNOWN 条件已经正确表达。
    #
    # 同时允许模型略微改写：
    #
    #     是否由劳动者提出或者同意续订劳动合同，
    #     目前无法确认。
    #
    # 也应当判定为正确。
    # ========================================================

    def build_condition_fragments(
        condition: str,
    ) -> List[str]:
        """
        从一个 UNKNOWN 条件中提取若干具有辨识度的关键片段。
        """

        condition = normalize_text(condition)

        if not condition:
            return []

        # ----------------------------------------------------
        # 去除标点。
        # ----------------------------------------------------

        condition_core = re.sub(
            r"[，。；：、（）()【】\[\]“”‘’：;,.!?！？]",
            "",
            condition,
        )

        condition_core = condition_core.strip()

        if not condition_core:
            return []

        fragments: List[str] = []

        # ----------------------------------------------------
        # 完整条件本身是最强匹配项。
        # ----------------------------------------------------

        if len(condition_core) >= 4:
            fragments.append(condition_core)

        # ----------------------------------------------------
        # 中文条件通常较长。
        #
        # 提取前部、中部、后部关键片段。
        # ----------------------------------------------------

        if len(condition_core) >= 8:
            fragments.append(
                condition_core[:8]
            )

        if len(condition_core) >= 12:
            fragments.append(
                condition_core[:12]
            )

        if len(condition_core) >= 16:
            fragments.append(
                condition_core[:16]
            )

        # ----------------------------------------------------
        # 针对劳动合同法律条件的常见核心短语。
        # ----------------------------------------------------

        legal_keywords = [
            "连续订立二次固定期限劳动合同",
            "连续签订二次固定期限劳动合同",
            "连续订立两次固定期限劳动合同",
            "连续签订两次固定期限劳动合同",
            "存在后续订立的劳动合同",
            "续订劳动合同",
            "提出或者同意续订",
            "提出或者同意订立",
            "提出订立固定期限劳动合同",
            "第三十九条规定的情形",
            "第四十条第一项规定的情形",
            "第四十条第二项规定的情形",
        ]

        for keyword in legal_keywords:

            if keyword in condition_core:
                fragments.append(keyword)

        # ----------------------------------------------------
        # 去重，同时保持原顺序。
        # ----------------------------------------------------

        unique_fragments: List[str] = []

        for fragment in fragments:

            fragment = fragment.strip()

            if not fragment:
                continue

            if fragment not in unique_fragments:
                unique_fragments.append(fragment)

        return unique_fragments

    # ========================================================
    # 第四层：逐项验证 UNKNOWN 条件
    # ========================================================
    #
    # V6.0-16 核心修复：
    #
    # 不再：
    #
    #     任意一个条件出现
    #         +
    #     任意一个 UNKNOWN 关键词出现
    #         =
    #     PASS
    #
    # 而是：
    #
    #     Engine UNKNOWN 条件
    #         ↓
    #     逐项检查
    #         ↓
    #     统计已经被回答表达的 UNKNOWN 条件
    #
    # 这样才能真正验证 Engine → Ollama 的 UNKNOWN 保真度。
    # ========================================================

    matched_conditions: List[str] = []

    for condition in normalized_conditions:

        fragments = build_condition_fragments(
            condition
        )

        if not fragments:
            continue

        # ----------------------------------------------------
        # 完整条件命中。
        # ----------------------------------------------------

        condition_mentioned = any(
            fragment in answer_text
            for fragment in fragments
            if len(fragment) >= 8
        )

        if condition_mentioned:

            matched_conditions.append(
                condition
            )

            continue

        # ----------------------------------------------------
        # 如果没有完整关键片段命中，
        # 再检查短关键词组合。
        # ----------------------------------------------------

        condition_core = re.sub(
            r"[，。；：、（）()【】\[\]“”‘’：;,.!?！？]",
            "",
            condition,
        )

        keyword_groups: List[List[str]] = []

        if "劳动者提出或者同意续订、订立劳动合同" in condition:
            keyword_groups.append(
                [
                    "劳动者",
                    "提出",
                    "同意",
                    "续订",
                ]
            )

            keyword_groups.append(
                [
                    "劳动者",
                    "提出",
                    "同意",
                    "订立",
                    "劳动合同",
                ]
            )

        elif "第三十九条" in condition:
            keyword_groups.append(
                [
                    "第三十九条",
                    "情形",
                ]
            )

        elif "第四十条第一项" in condition:
            keyword_groups.append(
                [
                    "第四十条第一项",
                    "情形",
                ]
            )

        elif "第四十条第二项" in condition:
            keyword_groups.append(
                [
                    "第四十条第二项",
                    "情形",
                ]
            )

        elif "提出订立固定期限劳动合同" in condition:
            keyword_groups.append(
                [
                    "提出",
                    "订立",
                    "固定期限劳动合同",
                ]
            )

        else:
            keyword_groups.append(
                [
                    condition_core[:6]
                ]
            )

        group_matched = False

        for group in keyword_groups:

            if all(
                keyword in answer_text
                for keyword in group
            ):
                group_matched = True
                break

        if group_matched:

            matched_conditions.append(
                condition
            )

    # ========================================================
    # 第五层：计算 UNKNOWN 条件覆盖率
    # ========================================================
    #
    # 正常情况下，Engine 有几个 UNKNOWN，
    # Ollama 就应该表达几个 UNKNOWN。
    #
    # 对本项目当前法律 RAG：
    #
    #     UNKNOWN = 4
    #
    # 正确回答：
    #
    #     4 / 4
    #
    # 应当 PASS。
    #
    # 如果只回答：
    #
    #     1 / 4
    #
    # 则不能认为 UNKNOWN 已经完整保真。
    # ========================================================

    matched_count = len(
        matched_conditions
    )

    unknown_count = len(
        normalized_conditions
    )

    # --------------------------------------------------------
    # 所有 UNKNOWN 条件都被明确表达。
    # --------------------------------------------------------

    if matched_count == unknown_count:

        # ----------------------------------------------------
        # 如果回答明确出现 UNKNOWN / 未确认语义，
        # 直接通过。
        #
        # 例如：
        #
        #     其他条件状态为 UNKNOWN：
        #     - 条件 A
        #     - 条件 B
        #     - 条件 C
        #     - 条件 D
        # ----------------------------------------------------

        if has_unresolved_marker:
            return True

        # ----------------------------------------------------
        # 即使没有出现固定 UNKNOWN 关键词，
        # 只要每一个 Engine UNKNOWN 条件都被保留，
        # 并且回答使用明显的未决结构，也允许通过。
        # ----------------------------------------------------

        unresolved_structure_patterns = [
            "是否存在",
            "是否具有",
            "是否符合",
            "是否属于",
            "是否满足",
            "是否发生",
            "是否具备",
            "取决于",
            "有待",
            "视",
            "尚需",
            "仍需",
            "待",
        ]

        if any(
            pattern in answer_text
            for pattern in unresolved_structure_patterns
        ):
            return True

        # ----------------------------------------------------
        # 如果条件本身全部被保留，但没有任何 UNKNOWN
        # 语义，也不能贸然认定为 UNKNOWN。
        # ----------------------------------------------------

        return False

    # ========================================================
    # 第六层：允许少量自然语言改写，但保持严格
    # ========================================================
    #
    # 某些回答可能没有逐项完整复制 Engine 条件，
    # 而是将多个 UNKNOWN 条件合并描述。
    #
    # 如果回答明确声明：
    #
    #     其他条件状态为 UNKNOWN
    #
    # 且至少有一半 UNKNOWN 条件被明确列出，
    # 可以认为 UNKNOWN 语义基本被保留。
    #
    # 但不能只因为出现一个“尚未确认”就通过。
    # ========================================================

    if has_unresolved_marker:

        # ----------------------------------------------------
        # 少于 2 个 UNKNOWN 条件时，
        # 必须至少匹配其中一个。
        # ----------------------------------------------------

        if unknown_count == 1:

            return matched_count == 1

        # ----------------------------------------------------
        # 多个 UNKNOWN 条件：
        # 至少覆盖一半。
        # ----------------------------------------------------

        minimum_required = (
            unknown_count + 1
        ) // 2

        if matched_count >= minimum_required:

            return True

    # ========================================================
    # 第七层：结构化 UNKNOWN 表达
    # ========================================================
    #
    # 即使没有出现：
    #
    #     尚未确认
    #     无法确认
    #     UNKNOWN
    #
    # 如果回答明确把条件写成：
    #
    #     是否……
    #     取决于……
    #     有待……
    #
    # 并且覆盖足够多的 Engine UNKNOWN 条件，
    # 仍然可以通过。
    # ========================================================

    unresolved_structure_patterns = [
        "是否存在",
        "是否具有",
        "是否符合",
        "是否属于",
        "是否满足",
        "是否发生",
        "是否具备",
        "取决于",
        "有待",
        "视",
        "尚需",
        "仍需",
        "待",
    ]

    has_unresolved_structure = any(
        pattern in answer_text
        for pattern in unresolved_structure_patterns
    )

    if has_unresolved_structure:

        if unknown_count == 1:
            return matched_count == 1

        minimum_required = (
            unknown_count + 1
        ) // 2

        if matched_count >= minimum_required:
            return True

    # ========================================================
    # 最终：UNKNOWN 验证失败
    # ========================================================
    #
    # 说明：
    #
    # Engine 明确存在 UNKNOWN 条件，
    # 但 Ollama 没有充分保留这些 UNKNOWN 条件的语义。
    #
    # 这种情况下必须 FAIL，
    # 防止 Ollama 把“不确定”错误表达成确定结论。
    # ========================================================

    return False
