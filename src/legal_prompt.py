# -*- coding: utf-8 -*-

"""
Legal Prompt Builder
从 RAG V6.0-27 原始 rag.py 拆分。

包含：build_deterministic_engine_state_block()、build_ollama_prompt()
"""

from typing import Any, Dict, List


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

# ============================================================
# Ollama Prompt
# ============================================================

def build_ollama_prompt(
    question: str,
    decision: Dict[str, Any],
) -> str:
    """
    RAG V6.0-27
    Ollama 最终回答 Prompt

    ============================================================
    核心原则
    ============================================================

    1. Legal Decision Engine 是唯一法律条件判定来源。
    2. Ollama 只能解释 Engine 已经形成的 DecisionResult。
    3. Ollama 不得重新进行法律条件判断。
    4. Ollama 不得新增用户事实。
    5. Ollama 不得把 UNKNOWN 推断为 SATISFIED。
    6. Ollama 不得把 UNKNOWN 推断为 NOT_SATISFIED。
    7. Ollama 不得把 SATISFIED 改写成 UNKNOWN。
    8. Ollama 不得把 NOT_SATISFIED 改写成 UNKNOWN。
    9. EXCLUSION / EXCEPTION 中的 NOT_SATISFIED
       表示该排除条件 / 例外条件已经触发。
    10. 最终回答必须保持 Engine Decision 不变。
    11. 法律条文中的列举事项不得自动转换为本案事实。
    12. Engine 只确认概括性事实时，Ollama 必须保持概括性表达。
    """

    from typing import Any, Dict, List

    prompt_parts: List[str] = []

    # ========================================================
    # 基础身份
    # ========================================================

    prompt_parts.append(
        "你是一个法律问答系统中的最终答案生成器。\n"
        "你的职责不是重新进行法律推理，而是严格根据已经由 Legal Decision Engine "
        "计算完成的结构化结果生成自然语言法律回答。\n"
    )

    # ========================================================
    # 用户问题
    # ========================================================

    prompt_parts.append(
        "\n============================================================\n"
        "用户问题\n"
        "============================================================\n"
        f"\n{question}\n"
    )

    # ========================================================
    # Engine Decision
    # ========================================================

    engine_decision = decision.get(
        "engine_decision",
        decision.get("decision", "UNKNOWN"),
    )

    prompt_parts.append(
        "\n============================================================\n"
        "Engine Decision\n"
        "============================================================\n"
        f"\n{engine_decision}\n"
        "\n"
        "【最高优先级规则】\n"
        "以上 Engine Decision 是 Legal Decision Engine 的最终判定结果。\n"
        "你必须原样遵守该 Decision，不得重新计算、修改、覆盖或推翻。\n"
    )

    # ========================================================
    # Decision Semantics
    # ========================================================

    prompt_parts.append(
        "\n============================================================\n"
        "Decision 语义\n"
        "============================================================\n"
        "\n"
        "DEFINITE：\n"
        "表示 Engine 已经确认相关必要条件全部满足，并且不存在已经触发的排除条件或例外条件。\n"
        "\n"
        "CONDITIONAL：\n"
        "表示目前没有已经确认的不满足条件、已经触发的排除条件或已经触发的例外条件，"
        "但仍存在 UNKNOWN 条件，因此当前结论具有条件性。\n"
        "\n"
        "NOT_ESTABLISHED：\n"
        "表示当前不能建立题目所询问的法律义务或法律结论。\n"
        "NOT_ESTABLISHED 不等于“所有 REQUIRED 条件都不满足”。\n"
        "它可能由以下任一情况造成：\n"
        "1. REQUIRED 条件存在 NOT_SATISFIED；\n"
        "2. EXCLUSION 条件存在 NOT_SATISFIED，即排除条件已经触发；\n"
        "3. EXCEPTION 条件存在 NOT_SATISFIED，即例外条件已经触发。\n"
        "\n"
        "因此，生成 NOT_ESTABLISHED 回答时，必须准确指出 Engine 已确认的实际原因，"
        "不得笼统表述为“所有条件均不满足”。\n"
    )

    # ========================================================
    # Decision Statistics
    # ========================================================

    condition_results = decision.get(
        "condition_results",
        decision.get("conditions", []),
    )

    if condition_results is None:
        condition_results = []

    satisfied_conditions = decision.get(
        "satisfied_conditions",
        [],
    ) or []

    unknown_conditions = decision.get(
        "unknown_conditions",
        [],
    ) or []

    not_satisfied_conditions = decision.get(
        "not_satisfied_conditions",
        [],
    ) or []

    required_results = decision.get(
        "required_condition_results",
        [],
    ) or []

    exclusion_results = decision.get(
        "exclusion_condition_results",
        [],
    ) or []

    exception_results = decision.get(
        "exception_results",
        [],
    ) or []

    required_not_satisfied_conditions = decision.get(
        "required_not_satisfied_conditions",
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

    prompt_parts.append(
        "\n============================================================\n"
        "Decision Structure Statistics\n"
        "============================================================\n"
        f"\n"
        f"Condition Results = {len(condition_results)}\n"
        f"REQUIRED = {len(required_results)}\n"
        f"EXCLUSION = {len(exclusion_results)}\n"
        f"EXCEPTION = {len(exception_results)}\n"
        f"SATISFIED Conditions = {len(satisfied_conditions)}\n"
        f"UNKNOWN Conditions = {len(unknown_conditions)}\n"
        f"NOT_SATISFIED Conditions = {len(not_satisfied_conditions)}\n"
        f"Required Not Satisfied = {len(required_not_satisfied_conditions)}\n"
        f"Triggered Exclusions = {len(triggered_exclusion_conditions)}\n"
        f"Triggered Exceptions = {len(triggered_exception_conditions)}\n"
    )

    # ========================================================
    # Decision Categories
    # ========================================================

    def _category_result_text(
        title: str,
        results: List[Any],
    ) -> str:
        """
        将 ConditionResult 分类结果转换为 Prompt 文本。
        """

        lines: List[str] = [
            f"\n--- {title} ---"
        ]

        if not results:
            lines.append("无")
            return "\n".join(lines)

        for index, result in enumerate(results, start=1):

            if isinstance(result, dict):
                condition = result.get(
                    "condition",
                    result.get("description", ""),
                )

                status = result.get(
                    "status",
                    result.get("result", ""),
                )

                category = result.get(
                    "category",
                    "",
                )

                reason = result.get(
                    "reason",
                    "",
                )

            else:
                condition = getattr(
                    result,
                    "condition",
                    "",
                )

                status = getattr(
                    result,
                    "status",
                    "",
                )

                category = getattr(
                    result,
                    "category",
                    "",
                )

                reason = getattr(
                    result,
                    "reason",
                    "",
                )

            lines.append(
                f"{index}. "
                f"category={category}; "
                f"status={status}; "
                f"condition={condition}; "
                f"reason={reason}"
            )

        return "\n".join(lines)

    prompt_parts.append(
        "\n============================================================\n"
        "Condition Results - REQUIRED\n"
        "============================================================\n"
        + _category_result_text(
            "REQUIRED",
            required_results,
        )
    )

    prompt_parts.append(
        "\n============================================================\n"
        "Condition Results - EXCLUSION\n"
        "============================================================\n"
        + _category_result_text(
            "EXCLUSION",
            exclusion_results,
        )
    )

    prompt_parts.append(
        "\n============================================================\n"
        "Condition Results - EXCEPTION\n"
        "============================================================\n"
        + _category_result_text(
            "EXCEPTION",
            exception_results,
        )
    )

    # ========================================================
    # Raw ConditionResult
    # ========================================================

    prompt_parts.append(
        "\n============================================================\n"
        "Raw ConditionResult\n"
        "============================================================\n"
        "\n"
        "以下 ConditionResult 是法律条件状态的最高优先级数据来源。\n"
        "生成最终回答时必须优先依据这些结果。\n"
        "\n"
    )

    for index, result in enumerate(
        condition_results,
        start=1,
    ):

        if isinstance(result, dict):

            condition = result.get(
                "condition",
                result.get("description", ""),
            )

            category = result.get(
                "category",
                "",
            )

            status = result.get(
                "status",
                result.get("result", ""),
            )

            reason = result.get(
                "reason",
                "",
            )

            fact = result.get(
                "fact",
                "",
            )

        else:

            condition = getattr(
                result,
                "condition",
                "",
            )

            category = getattr(
                result,
                "category",
                "",
            )

            status = getattr(
                result,
                "status",
                "",
            )

            reason = getattr(
                result,
                "reason",
                "",
            )

            fact = getattr(
                result,
                "fact",
                "",
            )

        prompt_parts.append(
            f"{index}. "
            f"category={category}; "
            f"status={status}; "
            f"condition={condition}; "
            f"fact={fact}; "
            f"reason={reason}"
        )

    # ========================================================
    # Condition Status Semantics
    # ========================================================

    prompt_parts.append(
        "\n============================================================\n"
        "Condition Status 语义\n"
        "============================================================\n"
        "\n"
        "REQUIRED 条件：\n"
        "1. SATISFIED = 该必备条件已经满足。\n"
        "2. NOT_SATISFIED = 该必备条件没有满足。\n"
        "3. UNKNOWN = 当前信息不足，无法确认该必备条件是否满足。\n"
        "\n"
        "EXCLUSION 条件：\n"
        "1. SATISFIED = 排除条件没有被确认触发。\n"
        "2. NOT_SATISFIED = 排除条件已经触发。\n"
        "3. UNKNOWN = 当前信息不足，无法确认是否触发排除条件。\n"
        "\n"
        "EXCEPTION 条件：\n"
        "1. SATISFIED = 例外条件没有被确认触发。\n"
        "2. NOT_SATISFIED = 例外条件已经触发。\n"
        "3. UNKNOWN = 当前信息不足，无法确认是否触发例外条件。\n"
        "\n"
        "特别重要：\n"
        "EXCLUSION / EXCEPTION 中的 NOT_SATISFIED 不能解释为“该条件不成立”。\n"
        "在本系统的语义中，它表示该排除条件 / 例外条件已经触发。\n"
    )

    # ========================================================
    # User Facts
    # ========================================================

    user_facts = decision.get(
        "user_facts",
        decision.get(
            "explicit_facts",
            [],
        ),
    ) or []

    prompt_parts.append(
        "\n============================================================\n"
        "Engine Explicit Facts\n"
        "============================================================\n"
        "\n"
    )

    if user_facts:

        for index, fact in enumerate(
            user_facts,
            start=1,
        ):
            prompt_parts.append(
                f"{index}. {fact}\n"
            )

    else:
        prompt_parts.append(
            "无。\n"
        )

    # ========================================================
    # User Fact Preservation — Hard Requirement
    # ========================================================

    prompt_parts.append(
        "\n============================================================\n"
        "USER FACT PRESERVATION — HARD REQUIREMENT\n"
        "============================================================\n"
        "\n"
        "Engine Explicit Facts 是已经由 Decision Engine 提取并确认的用户事实。\n"
        "这些事实不是可选参考信息，而是最终答案必须保留的事实数据。\n"
        "\n"
        "【绝对要求】\n"
        "\n"
        "1. Engine Explicit Facts 有多少条，最终【法律分析】中的“用户事实”"
        "就必须明确保留多少条。\n"
        "\n"
        "2. 不得遗漏任何一条 Engine Explicit Fact。\n"
        "\n"
        "3. 不得因为某一用户事实同时对应某一个 ConditionResult，"
        "就省略该用户事实。\n"
        "\n"
        "4. ConditionResult 是法律条件状态数据，"
        "Engine Explicit Facts 是用户事实数据，二者不能相互替代。\n"
        "\n"
        "5. 法律依据中的法条内容不能代替 Engine Explicit Facts。\n"
        "\n"
        "6. Legal Rules 中出现的法律条件不能代替用户事实。\n"
        "\n"
        "7. 用户事实必须在【法律分析】中单独列出，"
        "建议使用“1. 用户事实：”作为明确的小节。\n"
        "\n"
        "8. 用户事实可以进行自然语言等价改写，"
        "但不得改变事实的核心含义。\n"
        "\n"
        "9. 合同次数属于不可改变的事实：\n"
        "“两次”不得改写成“三次”；\n"
        "“三次”不得改写成“两次”。\n"
        "\n"
        "10. 用户已经明确陈述“续签/续订劳动合同”的，"
        "最终答案不得遗漏该续签/续订事实。\n"
        "\n"
        "11. 用户已经明确陈述某一法定情形存在的，"
        "最终答案不得仅保留法律条件名称而删除该用户事实。\n"
        "\n"
        "12. 不得因为某一个事实已经作为 EXCLUSION、EXCEPTION 或 REQUIRED"
        "条件出现，就认为该事实已经被输出而无需再次保留。\n"
        "\n"
        "13. 最终答案中的“用户事实”必须能够逐条对应 Engine Explicit Facts。\n"
        "\n"
        "【事实数量锁定】\n"
        f"Engine Explicit Facts 数量 = {len(user_facts)}\n"
        "\n"
    )

    if user_facts:

        prompt_parts.append(
            "【必须逐条保留的用户事实】\n"
        )

        for index, fact in enumerate(
            user_facts,
            start=1,
        ):
            prompt_parts.append(
                f"USER FACT #{index}：{fact}\n"
            )

        prompt_parts.append(
            "\n"
            "【最终输出要求】\n"
            f"最终【法律分析】必须明确保留以上 {len(user_facts)} 条用户事实。\n"
            "不得遗漏、合并、删除或改变任何一条用户事实。\n"
            "如果某一事实同时属于法律条件，也必须在“用户事实”部分单独保留。\n"
        )

    else:

        prompt_parts.append(
            "当前 Engine Explicit Facts = 0。\n"
            "不得自行创造用户事实。\n"
        )

    # ========================================================
    # User Fact Exact Preservation — Final Hard Lock
    # ========================================================

    prompt_parts.append(
        "\n============================================================\n"
        "USER FACT EXACT PRESERVATION — FINAL HARD LOCK\n"
        "============================================================\n"
        "\n"
        "以下 Engine Explicit Facts 是最终答案中的原始事实集合。\n"
        "最终答案不得对这些事实进行摘要、压缩、筛选或合并。\n"
        "\n"
        "【绝对禁止】\n"
        "\n"
        "1. 禁止把多条用户事实合并成一条。\n"
        "\n"
        "2. 禁止认为某条事实已经出现在 ConditionResult 中，"
        "因此可以不再输出该事实。\n"
        "\n"
        "3. 禁止只输出导致 Decision = NOT_ESTABLISHED 的事实。\n"
        "\n"
        "4. 禁止只输出你认为最重要的用户事实。\n"
        "\n"
        "5. 禁止根据法律依据、法律条件或排除条件重新筛选用户事实。\n"
        "\n"
        "6. 禁止删除“连续签订两次固定期限劳动合同”这一事实。\n"
        "\n"
        "7. 禁止删除“后来又续签了劳动合同”这一事实。\n"
        "\n"
        "8. 如果用户明确陈述某一法定情形存在，该情形才属于用户事实；"
        "如果仅作为 ConditionResult 出现，则只能作为法律条件状态处理，"
        "不得自动转化为用户事实。\n"
        "\n"
        "9. 禁止改变合同次数。\n"
        "“两次”必须保持为“两次”，不得改写为“三次”。\n"
        "\n"
        "10. 禁止把“续签了劳动合同”改写成用户没有明确陈述的"
        "“劳动者提出续签”或者“劳动者同意续签”。\n"
        "\n"
        "11. 禁止把“存在第三十九条规定的情形”扩展成具体第三十九条"
        "情形，除非 Engine Explicit Facts 中已经明确存在该具体事实。\n"
        "\n"
        "【机械保留规则】\n"
        "\n"
        f"Engine Explicit Facts 总数 = {len(user_facts)}。\n"
        f"最终答案必须明确出现 {len(user_facts)} 条用户事实。\n"
        "\n"
        "这里的“明确出现”是指：每一条 Engine Explicit Fact 都必须在"
        "“用户事实”部分单独形成一条事实记录。\n"
        "\n"
        "不能通过其他章节间接表达来代替。\n"
        "不能通过 ConditionResult 间接表达来代替。\n"
        "不能通过法律依据间接表达来代替。\n"
        "不能通过结论间接表达来代替。\n"
        "\n"
    )

    if user_facts:
        prompt_parts.append(
            "【最终用户事实清单——必须逐条输出】\n"
        )

        for index, fact in enumerate(
            user_facts,
            start=1,
        ):
            prompt_parts.append(
                f"FACT #{index}：{fact}\n"
            )

        prompt_parts.append(
            "\n"
            "【输出模板约束】\n"
            "最终【法律分析】必须包含：\n"
            "1. 用户事实：\n"
        )

        for index, fact in enumerate(
            user_facts,
            start=1,
        ):
            prompt_parts.append(
                f"- 用户事实 #{index}：{fact}\n"
            )

        prompt_parts.append(
            "\n"
            "以上事实必须全部保留。\n"
            "之后才能继续输出“已满足条件”“已触发排除条件”"
            "“尚未确认条件”等法律分析内容。\n"
        )

    # ========================================================
    # Fact-Condition Mapping
    # ========================================================

    fact_condition_mappings = decision.get(
        "fact_condition_mappings",
        [],
    ) or []

    prompt_parts.append(
        "\n============================================================\n"
        "Fact → Condition Mapping\n"
        "============================================================\n"
        "\n"
    )

    if fact_condition_mappings:

        for index, mapping in enumerate(
            fact_condition_mappings,
            start=1,
        ):

            if isinstance(mapping, dict):

                fact = mapping.get(
                    "fact",
                    "",
                )

                condition = mapping.get(
                    "condition",
                    "",
                )

                status = mapping.get(
                    "status",
                    "",
                )

            else:

                fact = getattr(
                    mapping,
                    "fact",
                    "",
                )

                condition = getattr(
                    mapping,
                    "condition",
                    "",
                )

                status = getattr(
                    mapping,
                    "status",
                    "",
                )

            prompt_parts.append(
                f"{index}. "
                f"fact={fact}; "
                f"condition={condition}; "
                f"status={status}\n"
            )

    else:

        prompt_parts.append(
            "无。\n"
        )

    # ========================================================
    # Required / Exclusion / Exception Explanation
    # ========================================================

    prompt_parts.append(
        "\n============================================================\n"
        "Decision Explanation\n"
        "============================================================\n"
        "\n"
        "以下内容用于帮助你解释 Engine 的最终判定。\n"
        "不得修改其中已经确定的状态。\n"
        "\n"
        f"已满足条件 = {satisfied_conditions}\n"
        f"尚不确定条件 = {unknown_conditions}\n"
        f"不满足必备条件 = {required_not_satisfied_conditions}\n"
        f"已触发排除条件 = {triggered_exclusion_conditions}\n"
        f"已触发例外条件 = {triggered_exception_conditions}\n"
    )

    # ========================================================
    # Final Output State Integrity
    # ========================================================

    prompt_parts.append(
        "\n============================================================\n"
        "最终输出状态完整性规则\n"
        "============================================================\n"
        "\n"
        "最终回答中的事实和条件状态必须与 Engine 完全一致，不得发生状态逆转。\n"
        "\n"
        "1. Engine = SATISFIED：只能表达为已经满足；不得写成尚未确认、需核实。\n"
        "\n"
        "2. Engine = NOT_SATISFIED：必须保持 NOT_SATISFIED 的原始语义。\n"
        "   对 EXCLUSION / EXCEPTION，必须表达为“已经触发”；不得写成需核实。\n"
        "\n"
        "3. Engine = UNKNOWN：只有 UNKNOWN 才能进入【需要注意】作为待确认事项。\n"
        "\n"
        "4. 已确认的 EXCLUSION 不得在【需要注意】中再次写成待核实。\n"
        "\n"
        "5. 不得把已经确认的事实改写成假设事实。\n"
        "\n"
        "6. 不得使用“如果……”“若……”“假如……”创造 Engine 未提供的反事实场景。\n"
        "\n"
        "7. 不得使用“如……等”“例如……”自行举出用户未提供的具体事实。\n"
        "\n"
        "8. 对第三十九条、第四十条等法定情形，如果 Engine 只确认条文层级，"
        "只能使用 Engine 提供的完整条件名称，不得自行举例具体行为或具体情形。\n"
        "\n"
        "9. 【需要注意】只能列出 Engine 明确标记为 UNKNOWN 的条件，"
        "并且应尽量使用其原始 condition 文本。\n"
        "\n"
        "10. 不得因为法律依据中出现其它条款，就自行添加本案的法律责任、赔偿、"
        "二倍工资等法律后果，除非 Engine explanation / condition result "
        "已经明确要求表达该法律后果，或者用户明确询问该法律后果。\n"
        "\n"
        "11. 法律条文中的列举事项、举例事项、行为类型、事实类型，"
        "除非已经明确出现在用户问题或 Engine Explicit Facts 中，"
        "否则一律不得视为本案用户事实。\n"
    )

    # ========================================================
    # Deterministic Condition Output Mapping
    # ========================================================

    prompt_parts.append(
        "\n============================================================\n"
        "确定性条件输出映射\n"
        "============================================================\n"
        "\n"
        "最终回答必须逐项保持以下 Engine 状态，不得遗漏、合并或改变状态。\n"
        "\n"
        f"SATISFIED 条件数量：{len(satisfied_conditions)}\n"
        f"UNKNOWN 条件数量：{len(unknown_conditions)}\n"
        f"NOT_SATISFIED 条件数量：{len(not_satisfied_conditions)}\n"
        f"已触发 EXCLUSION 数量：{len(triggered_exclusion_conditions)}\n"
        f"已触发 EXCEPTION 数量：{len(triggered_exception_conditions)}\n"
        "\n"
    )

    if unknown_conditions:
        prompt_parts.append(
            "【必须保留的 UNKNOWN 条件】\n"
        )

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

            prompt_parts.append(
                f"UNKNOWN #{index}：{condition_text}\n"
            )

        prompt_parts.append(
            "\n"
            "强制要求：\n"
            "1. 【需要注意】必须覆盖以上全部 UNKNOWN 条件。\n"
            "2. 不得遗漏任何一个 UNKNOWN 条件。\n"
            "3. 不得增加不属于 UNKNOWN 的条件。\n"
            "4. 不得把 UNKNOWN 改写成已经满足或已经触发。\n"
            "5. 尽量直接使用以上 condition 原文。\n"
        )
    else:
        prompt_parts.append(
            "当前没有 UNKNOWN 条件。\n"
            "【需要注意】不得自行创造待确认事项。\n"
        )

    if triggered_exclusion_conditions:
        prompt_parts.append(
            "\n"
            "【已经触发的 EXCLUSION】\n"
        )

        for index, condition in enumerate(
            triggered_exclusion_conditions,
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

            prompt_parts.append(
                f"EXCLUSION #{index}：{condition_text}\n"
            )

        prompt_parts.append(
            "\n"
            "强制要求：\n"
            "1. 以上 EXCLUSION 已经由 Engine 确认触发。\n"
            "2. 最终回答必须明确表达“已经触发”。\n"
            "3. 禁止使用“可能”“可能构成”“或许”“视情况”等不确定表达。\n"
            "4. 禁止把该 EXCLUSION 放入【需要注意】作为 UNKNOWN。\n"
            "5. 禁止要求用户再次确认该 EXCLUSION 是否存在。\n"
            "6. 禁止自行举出该法条下的具体行为或具体案例。\n"
            "7. 如果 EXCLUSION 的 condition 仅为概括性法定情形，"
            "必须保持该概括性表达，不得自行具体化。\n"
        )

    if triggered_exception_conditions:
        prompt_parts.append(
            "\n"
            "【已经触发的 EXCEPTION】\n"
        )

        for index, condition in enumerate(
            triggered_exception_conditions,
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

            prompt_parts.append(
                f"EXCEPTION #{index}：{condition_text}\n"
            )

        prompt_parts.append(
            "\n"
            "强制要求：\n"
            "以上 EXCEPTION 已经由 Engine 确认触发。\n"
            "必须表达为已经触发，不得改写为 UNKNOWN。\n"
            "如果 EXCEPTION 的 condition 仅为概括性法定情形，"
            "不得自行具体化其中的行为或事实。\n"
        )

    # ========================================================
    # Anti-Hallucination Rules
    # ========================================================

    prompt_parts.append(
        "\n============================================================\n"
        "事实边界与反幻觉规则\n"
        "============================================================\n"
        "\n"
        "你只能使用以下信息来源：\n"
        "1. 用户问题；\n"
        "2. Engine Explicit Facts；\n"
        "3. Raw ConditionResult；\n"
        "4. Fact → Condition Mapping；\n"
        "5. Engine Decision Explanation；\n"
        "6. 已提供的法律依据。\n"
        "\n"
        "特别说明：Raw ConditionResult 仅用于判断法律条件的状态，"
        "不得作为“用户事实”的来源。\n"
        "\n"
        "其中必须严格区分“本案事实”和“法律规则”。\n"
        "\n"
        "【本案事实的唯一来源】\n"
        "【用户事实与 ConditionResult 绝对隔离规则】\n"
        "\n"
        "这是最高优先级的事实边界规则：\n"
        "\n"
        "1. 只有 Engine Explicit Facts 中列出的内容，才能标记为“用户事实”。\n"
        "2. Raw ConditionResult 中的 condition、fact、reason、status、condition_type、type 等字段，"
        "无论内容是什么、无论状态是 SATISFIED、UNKNOWN 还是 NOT_SATISFIED，"
        "都不得自动转换为用户事实。\n"
        "3. ConditionResult 中出现“劳动者存在某种情形”的句子，"
        "仍然只是法律条件，不代表用户已经陈述该事实。\n"
        "4. UNKNOWN 的 ConditionResult 特别禁止称为“用户事实”。\n"
        "5. EXCLUSION 或 EXCEPTION 类型的 ConditionResult，"
        "除非同一事实已经明确存在于 Engine Explicit Facts 中，否则不得称为用户事实。\n"
        "6. “Engine 已确认条件”不等于“Engine 已确认用户事实”。\n"
        "7. “ConditionResult 已确认”只表示该条件的状态已经由 Engine 确定，"
        "不表示该条件对应的事实已经发生。\n"
        "8. 最终答案中出现“用户事实”四个字时，"
        "其后的每一条内容必须能够逐字对应 Engine Explicit Facts 中的一项。\n"
        "\n"
        "当前 Engine Explicit Facts 是唯一允许用于构建“用户事实”列表的数据源。\n"
        "【最终输出事实硬约束】\n"
        "最终答案中的“用户事实”只能来自 Engine Explicit Facts。\n"
        "本次 Engine Explicit Facts 只有以下事实：\n"
        f"{chr(10).join('- ' + str(fact) for fact in user_facts)}\n"
        "\n"
        "最终答案中的“用户事实”必须严格等于上述事实集合。\n"
        "不得从 ConditionResult 新增任何用户事实。\n"
        "不得把 UNKNOWN 条件写成用户事实。\n"
        "不得把 EXCLUSION 条件写成用户事实。\n"
        "不得把 EXCEPTION 条件写成用户事实。\n"
        "不得把 Legal Rules 中的法律条件写成用户事实。\n"
        "不得把法律条文中的列举事项写成用户已经发生的事实。\n"
        "如果某项内容不在上述 Engine Explicit Facts 中，即使它出现在 ConditionResult、"
        "Legal Rules、法律条文或分析说明中，也不得标记为“用户事实”。\n"
        "\n"
        "【UNKNOWN 语义绝对锁定】\n"
        "UNKNOWN 不等于 NOT_SATISFIED。\n"
        "UNKNOWN 不等于条件未满足。\n"
        "UNKNOWN 不等于条件已经触发。\n"
        "UNKNOWN 只能表达为当前事实不足以确认该条件是否成立或是否触发。\n"
        "不得使用“条件未满足”“已经不成立”“已经不存在”等表述替代 UNKNOWN。\n"
        "\n"
        "【CONDITIONAL 输出措辞锁定】\n"
        "当 Engine Decision = CONDITIONAL 时，禁止写“当前条件尚未满足”。\n"
        "禁止写“条件未满足”。\n"
        "禁止写“条件不成立”。\n"
        "禁止写“已经不满足”。\n"
        "禁止将 UNKNOWN 描述为 NOT_SATISFIED。\n"
        "必须明确表达为：当前存在尚未确认的条件，"
        "因此暂时不能作出确定性结论。\n"
        "\n"
        "Raw ConditionResult 只用于判断法律条件状态，"
        "不得因为 ConditionResult 中存在 fact、condition 或其它文字，"
        "就将其自动视为用户事实。\n"
        "\n"
        "Engine 已确认的 SATISFIED / UNKNOWN / NOT_SATISFIED 状态，"
        "属于法律条件状态，不属于用户事实来源。\n"
        "\n"
        "【法律规则不是本案事实】\n"
        "Legal Rules 中出现的法条内容、法律定义、法律列举、行为类型、"
        "举例事项和法律后果，仅属于法律规则信息。\n"
        "不得因为这些内容出现在 Legal Rules 中，就认为用户已经发生这些行为。\n"
        "\n"
        "严禁：\n"
        "1. 新增用户没有说过的事实；\n"
        "2. 根据法律条文自行推测具体行为；\n"
        "3. 根据某一法条自行举出具体案例；\n"
        "4. 将法律条文中的示例当成本案事实；\n"
        "5. 将法律条文中的列举行为当成本案已经发生的行为；\n"
        "6. 将 UNKNOWN 推断为 SATISFIED；\n"
        "7. 将 UNKNOWN 推断为 NOT_SATISFIED；\n"
        "8. 将 SATISFIED 改写为 UNKNOWN；\n"
        "9. 将 NOT_SATISFIED 改写为 UNKNOWN；\n"
        "10. 自行添加反事实条件；\n"
        "11. 自行添加用户没有询问的法律责任后果；\n"
        "12. 将概括性的 Engine 条件自动具体化为某一种具体行为。\n"
        "\n"
        "特别禁止：\n"
        "如果用户只提供“存在《劳动合同法》第三十九条规定的情形”，"
        "且 Engine 只确认“劳动者存在《劳动合同法》第三十九条规定的情形”，\n"
        "则最终回答只能保持这一概括性表达。\n"
        "\n"
        "禁止自行扩展为：\n"
        "“严重违反规章制度”；\n"
        "“严重失职”；\n"
        "“营私舞弊”；\n"
        "“被依法追究刑事责任”；\n"
        "或者第三十九条规定的其它具体行为。\n"
        "\n"
        "除非上述具体事实明确出现在用户问题或 Engine Explicit Facts 中。\n"
        "Raw ConditionResult 只能用于判断法律条件状态，"
        "不得作为用户事实来源。\n"
    )

    # ========================================================
    # UNKNOWN Rules
    # ========================================================

    prompt_parts.append(
        "\n============================================================\n"
        "UNKNOWN 条件处理规则\n"
        "============================================================\n"
        "\n"
        "UNKNOWN 表示当前资料不足，不能确认该条件是否成立。\n"
        "\n"
        "UNKNOWN 不等于 SATISFIED。\n"
        "UNKNOWN 不等于 NOT_SATISFIED。\n"
        "\n"
        "因此：\n"
        "1. 不得自行补充 UNKNOWN 条件的事实；\n"
        "2. 不得自行推断 UNKNOWN 条件已经满足；\n"
        "3. 不得自行推断 UNKNOWN 条件已经触发；\n"
        "4. 可以在【需要注意】中指出这些条件尚未确认；\n"
        "5. 必须尽量使用 Engine 给出的原始 condition 文本。\n"
    )

    # ========================================================
    # NOT_ESTABLISHED Rules
    # ========================================================

    prompt_parts.append(
        "\n============================================================\n"
        "NOT_ESTABLISHED 特别规则\n"
        "============================================================\n"
        "\n"
        "当 Engine Decision = NOT_ESTABLISHED 时：\n"
        "\n"
        "1. 不得写成“所有条件均不满足”。\n"
        "\n"
        "2. 不得写成“所有 REQUIRED 条件均不满足”，除非 Engine 明确显示所有 REQUIRED 条件均为 NOT_SATISFIED。\n"
        "\n"
        "3. 必须指出造成 NOT_ESTABLISHED 的已确认原因。\n"
        "\n"
        "4. 如果存在 REQUIRED + NOT_SATISFIED，说明相应必备条件没有满足。\n"
        "\n"
        "5. 如果存在 EXCLUSION + NOT_SATISFIED，必须说明相应排除条件已经触发。\n"
        "\n"
        "6. 如果存在 EXCEPTION + NOT_SATISFIED，必须说明相应例外条件已经触发。\n"
        "\n"
        "7. 必须区分 SATISFIED、NOT_SATISFIED 和 UNKNOWN。\n"
        "\n"
        "8. UNKNOWN 必须继续保持 UNKNOWN。\n"
        "\n"
        "9. 如果 Required Not Satisfied = 0，"
        "但 Triggered Exclusions > 0，则不要说“必备条件没有满足”，"
        "而应以“排除条件已经触发”为当前不能建立法律义务的直接原因。\n"
        "\n"
        "10. 如果 Triggered Exceptions > 0，"
        "则应以“例外条件已经触发”为当前不能建立法律义务的直接原因。\n"
    )

    # ========================================================
    # Legal Rules
    # ========================================================

    legal_rules = decision.get(
        "legal_rules",
        decision.get(
            "rules",
            [],
        ),
    ) or []

    prompt_parts.append(
        "\n============================================================\n"
        "Legal Rules\n"
        "============================================================\n"
        "\n"
    )

    if legal_rules:
        for index, rule in enumerate(
            legal_rules,
            start=1,
        ):

            if isinstance(rule, dict):

                law_name = rule.get(
                    "law_name",
                    rule.get(
                        "law",
                        rule.get(
                            "title",
                            "",
                        ),
                    ),
                )

                article_number = rule.get(
                    "article_number",
                    rule.get(
                        "article",
                        rule.get(
                            "article_no",
                            "",
                        ),
                    ),
                )

                rule_summary = rule.get(
                    "rule_summary",
                    rule.get(
                        "summary",
                        rule.get(
                            "content",
                            rule.get(
                                "text",
                                "",
                            ),
                        ),
                    ),
                )

            else:

                law_name = getattr(
                    rule,
                    "law_name",
                    getattr(
                        rule,
                        "law",
                        getattr(
                            rule,
                            "title",
                            "",
                        ),
                    ),
                )

                article_number = getattr(
                    rule,
                    "article_number",
                    getattr(
                        rule,
                        "article",
                        getattr(
                            rule,
                            "article_no",
                            "",
                        ),
                    ),
                )

                rule_summary = getattr(
                    rule,
                    "rule_summary",
                    getattr(
                        rule,
                        "summary",
                        getattr(
                            rule,
                            "content",
                            getattr(
                                rule,
                                "text",
                                "",
                            ),
                        ),
                    ),
                )

            prompt_parts.append(
                f"{index}. "
                f"law_name={law_name}; "
                f"article_number={article_number}; "
                f"rule_summary={rule_summary}\n"
            )

    else:

        prompt_parts.append(
            "无。\n"
        )

    # ========================================================
    # Legal Rules Usage Boundary
    # ========================================================

    prompt_parts.append(
        "\n============================================================\n"
        "Legal Rules 使用边界\n"
        "============================================================\n"
        "\n"
        "Legal Rules 只能用于解释 Engine 已经作出的条件判断。\n"
        "\n"
        "Legal Rules 是法律依据，不是用户事实数据库。\n"
        "\n"
        "【核心法律依据规则】\n"
        "Legal Rules 中的 rule_priority = CORE 表示该规则是直接回答当前问题的主要法律依据。\n"
        "Legal Rules 中的 rule_priority = RELATED 表示该规则属于相关、辅助、"
        "例外、法律后果或其他补充法律依据。\n"
        "\n"
        "当 Legal Rules 同时存在 CORE 和 RELATED 规则时，"
        "应当理解为 CORE 规则优先，RELATED 规则作为补充。\n"
        "\n"
        "如果 CORE 规则中存在 importance = CRITICAL、"
        "classification = 核心法条或 structured_rule = True 的规则，"
        "该规则具有更高的核心法律依据优先级。\n"
        "\n"
        "RELATED 规则不得因为其内容涉及排除条件、例外条件、法律后果或其他辅助事项，"
        "而取代 CORE 规则成为主要法律依据。\n"
        "\n"
        "如果某一 RELATED 规则只是 CORE 规则所引用的排除条件或辅助规定，"
        "应当将其理解为 CORE 规则的辅助法律依据，"
        "不得将该 RELATED 规则解释为取代 CORE 规则的主要法律依据。\n"
        "\n"
        "【最终法律依据输出边界】\n"
        "最终答案中的“【法律依据】”由 Python 根据当前 Structured Rules "
        "和 rule_priority 确定性生成。\n"
        "Ollama 不得自行重新选择、替换、删除或增加最终法律依据。\n"
        "\n"
        "Ollama 可以对已经提供的 CORE 和 RELATED 法律依据进行解释，"
        "但不得根据自己的法律知识重新检索、补充或替换法律条文。\n"
        "\n"
        "不得因为某一 RELATED 规则涉及排除条件、例外条件或法律后果，"
        "就将该规则排列在 CORE 规则之前。\n"
        "\n"
        "【法律规则与用户事实严格分离】\n"
        "法律规则中的具体行为、具体情形、排除条件、例外条件和法律后果，"
        "均属于法律规则内容，不属于用户事实。\n"
        "\n"
        "即使 Legal Rules 中完整列出了某一法条的多个具体行为、"
        "具体情形或法律后果，也不得因此认定本案已经发生这些行为或情形。\n"
        "\n"
        "只有当某一具体行为已经明确出现在用户问题或 "
        "Engine Explicit Facts 中时，"
        "才可以在最终回答中将该具体行为作为本案用户事实进行表述。\n"
        "\n"
        "Raw ConditionResult 不属于用户事实来源。\n"
        "\n"
        "【条件表述边界】\n"
        "如果 Engine 的 condition 仅为概括性表述，"
        "最终回答必须继续使用概括性表述，"
        "不得根据 Legal Rules 自行扩展为更加具体的事实。\n"
        "\n"
        "不得因为检索结果中存在其它法律条文，"
        "就自行扩大 Engine 已经作出的法律判断。\n"
        "\n"
        "尤其不得仅因为检索到了某个责任条款，"
        "就在最终回答中自行增加二倍工资、赔偿、违约责任、解除责任等法律后果。\n"
        "\n"
        "如果用户没有询问法律责任后果，且 Engine 没有明确要求表达该后果，"
        "不要主动展开责任后果。\n"
    )

    # ========================================================
    # Final Output Format
    # ========================================================

    prompt_parts.append(
        "\n============================================================\n"
        "最终回答格式\n"
        "============================================================\n"
        "\n"
        "最终回答必须严格使用以下四个标题：\n"
        "\n"
        "【结论】\n"
        "【法律依据】\n"
        "【法律分析】\n"
        "【需要注意】\n"
        "\n"
        "不得增加第五个标题。\n"
        "\n"
        "【结论】：\n"
        "只表达 Engine Decision 及其已经确认的直接原因。\n"
        "如果存在 EXCLUSION + NOT_SATISFIED，"
        "必须明确说明该排除条件已经触发。\n"
        "不得加入反事实、假设或用户未提供的具体情形。\n"
        "\n"
        "【法律依据】：\n"
        "只引用已经提供且与当前 Engine Decision 直接相关的法律依据。\n"
        "法律依据中的具体列举事项不得自动转换为本案事实。\n"
        "不得借助其它法律条文自行扩展新的法律后果。\n"
        "\n"
        "【法律分析】：\n"
        "只解释已经存在的 ConditionResult。\n"
        "不得将 NOT_SATISFIED 改成 UNKNOWN。\n"
        "不得将 UNKNOWN 改成确定状态。\n"
        "不得自行举例。\n"
        "不得把法律条文中的具体行为写成用户已经实施的具体行为，"
        "除非该行为已经明确存在于 Engine 事实数据中。\n"
        "\n"
        "【需要注意】：\n"
        "只能列出 UNKNOWN 条件。\n"
        "已经 SATISFIED 的条件不得写入这里。\n"
        "已经触发的 EXCLUSION / EXCEPTION 不得写入这里。\n"
        "不得把已经确认的排除条件再次写成“需要核实”。\n"
    )

    # ========================================================
    # Deterministic Engine State
    # ========================================================

    deterministic_state = (
        build_deterministic_engine_state_block(
            decision
        )
    )

    prompt_parts.append(
        "\n"
        + deterministic_state
        + "\n"
    )

    # ========================================================
    # Final Generation Rules
    # ========================================================

    prompt_parts.append(
        "\n============================================================\n"
        "最终生成要求\n"
        "============================================================\n"
        "\n"
        "现在请根据以上 Engine 数据生成最终法律回答。\n"
        "\n"
        "【最终事实边界锁定】\n"
        "在生成最终回答前，必须执行以下规则：\n"
        "\n"
        "1. 先读取用户问题和 Engine Explicit Facts，确定本案事实。\n"
        "2. 再读取 Raw ConditionResult，确定每个条件的状态。\n"
        "3. Legal Rules 只用于提供法律依据，不得用来补充本案事实。\n"
        "4. 如果用户事实或 Engine 条件只有概括性表述，必须保持概括性。\n"
        "5. 不得从法条列举内容中挑选一个具体行为作为本案事实。\n"
        "6. 不得为了使回答更具体而自行补充事实。\n"
        "7. 不得把法律条文中的例子、列举、定义转换成用户已经发生的事实。\n"
        "8. 不得使用 Engine 没有提供的具体行为证明已经发生了某种事实。\n"
        "\n"
        "【当前系统的强制事实映射原则】\n"
        "用户事实 = Engine 明确确认的事实。\n"
        "法律规则 = 法律规则。\n"
        "二者不得混合。\n"
        "\n"
        "【最终用户事实数量硬锁定】\n"
        f"Engine Explicit Facts 数量 = {len(user_facts)}。\n"
        f"最终答案中的“用户事实”必须明确输出 {len(user_facts)} 条。\n"
        "每一条 Engine Explicit Fact 都必须单独出现。\n"
        "不得合并、摘要、筛选、删除或隐含表达。\n"
        "导致 NOT_ESTABLISHED 的事实，也不得因此成为唯一输出的用户事实。\n"
        "\n"
        "【用户事实逐条保留规则】\n"
        f"Engine Explicit Facts 数量 = {len(user_facts)}。\n"
        f"最终【法律分析】中的“用户事实”必须明确保留 {len(user_facts)} 条。\n"
        "每一条都必须能够对应 Engine Explicit Facts 中的一条事实。\n"
        "不得因为该事实已经出现在 ConditionResult、EXCLUSION、"
        "REQUIRED 或其它结构中，就省略用户事实本身。\n"
        "不得只输出某一个最重要的用户事实。\n"
        "不得只输出导致 NOT_ESTABLISHED 的事实。\n"
        "必须完整保留全部用户事实。\n"
        "\n"
        "例如，如果 Engine 仅确认：\n"
        "“劳动者存在《劳动合同法》第三十九条规定的情形”\n"
        "\n"
        "则允许：\n"
        "“劳动者存在《劳动合同法》第三十九条规定的情形，"
        "该排除条件已经触发。”\n"
        "\n"
        "但禁止：\n"
        "“劳动者严重违反用人单位规章制度。”\n"
        "“劳动者严重失职。”\n"
        "“劳动者被依法追究刑事责任。”\n"
        "以及其它未经 Engine 确认的第三十九条具体行为。\n"
        "\n"
        "再次强调：\n"
        "Engine Decision 是最终法律判定，不允许修改。\n"
        "ConditionResult 是条件状态的最高优先级来源。\n"
        "不得自行重新推理。\n"
        "不得新增事实。\n"
        "不得自行举例。\n"
        "不得创造反事实。\n"
        "不得改变 SATISFIED / NOT_SATISFIED / UNKNOWN 的状态。\n"
        "EXCLUSION / EXCEPTION 的 NOT_SATISFIED 表示已经触发。\n"
        "【需要注意】只能写 UNKNOWN。\n"
        "法律条文中的具体列举事项不得自动成为本案事实。\n"
        "\n"
                "\n"
        "============================================================\n"
        "最终状态锁定\n"
        "============================================================\n"
        "\n"
        "下面的 ENGINE DETERMINISTIC STATE 是 Python 根据 Legal Decision Engine "
        "直接生成的确定性状态数据。\n"
        "\n"
        "这是最终答案中的不可修改数据。\n"
        "\n"
        "【绝对禁止】\n"
        "1. 不得增加 UNKNOWN 条件。\n"
        "2. 不得删除 UNKNOWN 条件。\n"
        "3. 不得合并 UNKNOWN 条件。\n"
        "4. 不得拆分 UNKNOWN 条件。\n"
        "5. 不得改变 UNKNOWN 条件的原文含义。\n"
        "6. 不得把 UNKNOWN 改成 SATISFIED。\n"
        "7. 不得把 UNKNOWN 改成 NOT_SATISFIED。\n"
        "8. 不得把已经触发的 EXCLUSION 改成 UNKNOWN。\n"
        "9. 不得把已经触发的 EXCEPTION 改成 UNKNOWN。\n"
        "10. 不得从 Legal Rules 增加新的 UNKNOWN 条件。\n"
        "11. 不得使用“其他可能影响……”等 Engine 没有提供的条件。\n"
        "\n"
        "【UNKNOWN 一一对应规则】\n"
        "如果 ENGINE DETERMINISTIC STATE 显示 UNKNOWN 条件数量为 N，\n"
        "则最终【需要注意】必须恰好列出 N 项。\n"
        "\n"
        "每一项必须对应 ENGINE DETERMINISTIC STATE 中的一项 UNKNOWN。\n"
        "\n"
        "不得合并，例如：\n"
        "“第四十条第一项、第二项规定的情形”\n"
        "不能代替两个独立的 UNKNOWN 条件。\n"
        "\n"
        "不得概括，例如：\n"
        "“其他可能影响劳动合同续订的情形”\n"
        "不得作为 UNKNOWN。\n"
        "\n"
        "【EXCLUSION 一一对应规则】\n"
        "已经触发的 EXCLUSION 必须明确表达为“已经触发”。\n"
        "禁止使用：\n"
        "“可能”\n"
        "“可能构成”\n"
        "“或许”\n"
        "“视情况而定”\n"
        "\n"
        "【事实具体化禁止】\n"
        "如果 ENGINE DETERMINISTIC STATE 中只有：\n"
        "“劳动者存在《劳动合同法》第三十九条规定的情形”\n"
        "\n"
        "则最终回答只能使用该概括性事实。\n"
        "\n"
        "不得根据 Legal Rules 中的第三十九条、第四十条或者实施条例中的列举内容，"
        "自行选择具体行为作为本案事实。\n"
        "\n"
        "特别禁止把：\n"
        "“劳动者存在《劳动合同法》第三十九条规定的情形”\n"
        "扩展成：\n"
        "“严重违反规章制度”\n"
        "“严重失职”\n"
        "“营私舞弊”\n"
        "“被依法追究刑事责任”\n"
        "或者其它具体行为。\n"
        "\n"
        "这些具体行为只有在用户问题或者 Engine Explicit Facts 明确出现时才允许使用。\n"
        "\n"
        "请直接输出最终法律回答，不要解释你的生成过程。\n"
    )

    return "".join(prompt_parts)