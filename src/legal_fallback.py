# -*- coding: utf-8 -*-

"""
RAG V6.0-27
Legal Fallback Layer

============================================================
功能
============================================================

Final Validation
      ↓
Validation FAIL
      ↓
build_fallback_answer()
      ↓
Deterministic Structured Answer

本模块只负责安全 Fallback：

1. 不调用 Ollama。
2. 不重新进行法律推理。
3. 不修改 Decision。
4. 不删除 UNKNOWN。
5. 不把用户事实改写成法律规则。
6. 法律依据只来自结构化 Rules。
7. REQUIRED / EXCLUSION / EXCEPTION 保持独立语义。
8. UNKNOWN 条件逐项保留。

注意：

    build_fallback_answer() 原本位于 src/rag.py。
    本次拆分仅改变模块边界，不改变其内部业务逻辑。

============================================================
依赖边界
============================================================

本模块依赖：

    src.legal_common
        normalize_text
        ensure_list
        unique_texts

    src.legal_rule_builder
        build_rules_from_articles
        prioritize_legal_rules

    src.legal_validator
        clean_answer

其中 legal_validator 对 legal_fallback 的导入采用局部导入，
因此这里可以安全复用 clean_answer，而不形成模块初始化时的循环依赖。
"""

# ============================================================
# 标准库
# ============================================================

from typing import Any, Dict


# ============================================================
# 项目内部模块
# ============================================================

from src.legal_common import (
    ensure_list,
    normalize_text,
    unique_texts,
)

from src.legal_rule_builder import (
    build_rules_from_articles,
    prioritize_legal_rules,
)


# ============================================================
# Decision 状态
# ============================================================

DECISION_DEFINITE = "DEFINITE"

DECISION_CONDITIONAL = "CONDITIONAL"

DECISION_NOT_ESTABLISHED = "NOT_ESTABLISHED"


# ============================================================
# 最终答案结构
# ============================================================

SECTION_CONCLUSION = "【结论】"

SECTION_BASIS = "【法律依据】"

SECTION_ANALYSIS = "【法律分析】"

SECTION_NOTICE = "【需要注意】"


REQUIRED_SECTIONS = [
    SECTION_CONCLUSION,
    SECTION_BASIS,
    SECTION_ANALYSIS,
    SECTION_NOTICE,
]


# ============================================================
# Fallback 使用的 clean_answer
# ============================================================

# 不在模块导入阶段从 legal_validator 导入，避免初始化循环。
# build_fallback_answer() 真正执行到最后清理答案时再取得函数。


def _clean_answer(answer: str) -> str:
    """调用最终验证层的统一答案清理函数。"""

    from src.legal_validator import clean_answer

    return clean_answer(answer)


def build_fallback_answer(
    question: str,
    decision: Dict[str, Any],
) -> str:
    """
    V6.0-27 确定性 Python Fallback。

    重要原则：

    1. 不调用 Ollama。
    2. 不重新进行法律推理。
    3. 不修改 Decision。
    4. 不删除 UNKNOWN。
    5. 不把用户事实改写成法律规则。
    6. 法律依据只来自结构化 Rules。
    7. 最终结果仍然必须通过 Final Validation。
    8. REQUIRED / EXCLUSION / EXCEPTION 必须保持独立语义。
    9. EXCLUSION / EXCEPTION 的 NOT_SATISFIED 表示
       对应的排除情形 / 例外情形已经触发，
       不能输出为普通“未满足条件”。
    10. UNKNOWN 条件必须逐项保留，不能合并或丢失。

    V6.0-10 的问题是：

        Ollama Validation FAIL
                ↓
        build_plain_answer()
                ↓
        THREE_CONTRACT_FACT FAIL

    V6.0-13 不再让旧版 Answer Builder 作为安全 Fallback 的最终
    事实来源，而是直接使用已经完成的 Structured Answer 数据生成
    一个确定性的回答。

    V6.0-26 修正：

        1. 正确读取 not_satisfied_conditions。
        2. REQUIRED 的 NOT_SATISFIED 才进入“不满足必备条件”。
        3. EXCLUSION 的 NOT_SATISFIED 进入“已触发排除条件”。
        4. EXCEPTION 的 NOT_SATISFIED 进入“已触发例外条件”。
        5. UNKNOWN 条件逐项保留。
        6. 不再把 EXCLUSION 错误写成“未满足条件”。
        7. 不再把 UNKNOWN 条件错误写成“尚未确认的必备条件”。

    V6.0-27 修正：

        1. DEFINITE 结论不得再使用泛化占位语句：
               “可以按照 Decision Engine 的确定性结论处理。”

        2. DEFINITE 的最终法律结论必须直接读取
           Structured Rules 已经提供的：
               legal_obligations

        3. DEFINITE 的“法律后果”必须直接读取
           Structured Rules 已经提供的：
               legal_consequences
               legal_obligations

        4. Fallback 不重新进行法律推理。
           只负责把已经存在于 Structured Rules 中的
           确定性法律义务转换为最终回答。

        5. 如果 Structured Rules 没有提供
           legal_obligations / legal_consequences，
           不允许 Fallback 自行创造新的法律义务。
           此时只能使用安全的结构化 Decision 表述。

    V6.0-27 条件语义修正：

        REQUIRED：

            SATISFIED
                → 已满足

            NOT_SATISFIED
                → 未满足

            UNKNOWN
                → 尚未确认

        EXCLUSION：

            SATISFIED
                → 排除情形不存在 / 未触发

            NOT_SATISFIED
                → 排除情形存在 / 已触发

            UNKNOWN
                → 尚未确认

        EXCEPTION：

            SATISFIED
                → 例外情形不存在 / 未触发

            NOT_SATISFIED
                → 例外情形存在 / 已触发

            UNKNOWN
                → 尚未确认

    特别注意：

        Decision Engine 内部可以继续使用统一的
        SATISFIED / NOT_SATISFIED / UNKNOWN 状态。

        但是 Fallback 在展示和分类时，
        必须结合 condition_type 解释其语义。

        不能简单地认为：

            NOT_SATISFIED
                =
            普通“未满足条件”。

        对 EXCLUSION / EXCEPTION 而言：

            NOT_SATISFIED
                =
            对应的排除 / 例外情形已经触发。
    """

    print()
    print("=" * 70)
    print("Fallback / Deterministic Legal Answer Builder V6.0-27")
    print("=" * 70)

    question = normalize_text(
        question
    )

    engine_decision = normalize_text(
        decision.get(
            "engine_decision",
            decision.get(
                "decision",
                "",
            ),
        )
    ).upper()

    # ========================================================
    # 用户事实
    # ========================================================

    user_facts = unique_texts(
        ensure_list(
            decision.get(
                "user_facts",
                [],
            )
        )
    )

    # ========================================================
    # 不满足条件
    #
    # DecisionResult 的正式字段是：
    #
    #     not_satisfied_conditions
    #
    # 不能再使用旧的：
    #
    #     unsatisfied_conditions
    #
    # 但是这里仍然只作为兼容读取，不参与重新推理。
    # ========================================================

    not_satisfied = unique_texts(
        ensure_list(
            decision.get(
                "not_satisfied_conditions",
                decision.get(
                    "unsatisfied_conditions",
                    [],
                ),
            )
        )
    )

    # ========================================================
    # UNKNOWN
    # ========================================================

    unknown = ensure_list(
        decision.get(
            "unknown_conditions",
            [],
        )
    )

    # ========================================================
    # Structured Rules
    # ========================================================

    print()
    print("----------------------------------------------------------------------")
    print("DEBUG / Fallback Decision Fields")
    print("----------------------------------------------------------------------")
    print("decision keys:")
    print(list(decision.keys()))

    print()
    print("required_results:")
    print(decision.get("required_results"))

    print()
    print("condition_results:")
    print(decision.get("condition_results"))

    print()
    print("satisfied_conditions:")
    print(decision.get("satisfied_conditions"))

    print()
    print("required_satisfied_conditions:")
    print(decision.get("required_satisfied_conditions"))

    rules = build_rules_from_articles(
        ensure_list(
            decision.get(
                "rules",
                [],
            )
        )
    )

    # ========================================================
    # 分类条件结果
    # ========================================================

    condition_results = ensure_list(
        decision.get(
            "condition_results",
            [],
        )
    )

    # ========================================================
    # REQUIRED 条件结果
    #
    # 当前 DecisionResult 的正式结构中，
    # 所有条件统一存放在：
    #
    #     condition_results
    #
    # 每一项通过：
    #
    #     condition_type
    #
    # 或：
    #
    #     type
    #
    # 区分 REQUIRED / EXCLUSION / EXCEPTION。
    #
    # 因此不能再假定：
    #
    #     decision["required_results"]
    #
    # 一定存在。
    #
    # 这里直接从正式的 condition_results
    # 中提取 REQUIRED。
    #
    # 只做结构分类，不重新进行法律推理。
    # ========================================================

    required_results = []

    for item in condition_results:

        if not isinstance(item, dict):
            continue

        condition_type = normalize_text(
            item.get(
                "condition_type",
                item.get(
                    "type",
                    "",
                ),
            )
        ).upper()

        if condition_type == "REQUIRED":
            required_results.append(
                item
            )

    # --------------------------------------------------------
    # EXCLUSION 条件结果
    # --------------------------------------------------------

    exclusion_results = ensure_list(
        decision.get(
            "exclusion_condition_results",
            decision.get(
                "exclusion_results",
                [],
            ),
        )
    )

    # --------------------------------------------------------
    # 如果正式字段没有提供 EXCLUSION，
    # 同样从 condition_results 中提取。
    # --------------------------------------------------------

    if not exclusion_results:

        exclusion_results = []

        for item in condition_results:

            if not isinstance(item, dict):
                continue

            condition_type = normalize_text(
                item.get(
                    "condition_type",
                    item.get(
                        "type",
                        "",
                    ),
                )
            ).upper()

            if condition_type == "EXCLUSION":
                exclusion_results.append(
                    item
                )

    # --------------------------------------------------------
    # EXCEPTION 条件结果
    # --------------------------------------------------------

    exception_results = ensure_list(
        decision.get(
            "exception_condition_results",
            decision.get(
                "exception_results",
                [],
            ),
        )
    )

    # --------------------------------------------------------
    # 如果正式字段没有提供 EXCEPTION，
    # 同样从 condition_results 中提取。
    # --------------------------------------------------------

    if not exception_results:

        exception_results = []

        for item in condition_results:

            if not isinstance(item, dict):
                continue

            condition_type = normalize_text(
                item.get(
                    "condition_type",
                    item.get(
                        "type",
                        "",
                    ),
                )
            ).upper()

            if condition_type == "EXCEPTION":
                exception_results.append(
                    item
                )

    # ========================================================
    # 已满足条件
    #
    # 这里只展示 REQUIRED + SATISFIED。
    #
    # Decision Engine 的 satisfied_conditions
    # 同时可能包含：
    #
    #     REQUIRED + SATISFIED
    #     EXCLUSION + SATISFIED
    #     EXCEPTION + SATISFIED
    #
    # 其中：
    #
    #     EXCLUSION + SATISFIED
    #         = 排除情形不存在，排除条件未触发
    #
    #     EXCEPTION + SATISFIED
    #         = 例外情形不存在，例外条件未触发
    #
    # 因此不能把它们直接显示为“已满足条件”。
    #
    # 这里只读取 Decision Engine 已经分类好的
    # required_results，不重新进行法律推理。
    # ========================================================

    satisfied = []

    # ========================================================
    # 从 Decision Engine 已经生成的 condition_results 中，
    # 提取 REQUIRED + SATISFIED 条件。
    #
    # 注意：
    #
    # condition_results 是 Decision Engine 的正式条件判定结果。
    #
    # 这里仅做展示分类：
    #
    #     REQUIRED + SATISFIED
    #
    # 不重新进行任何法律推理。
    #
    # 不能直接使用 satisfied_conditions，
    # 因为 satisfied_conditions 可能同时包含：
    #
    #     REQUIRED
    #     EXCLUSION
    #     EXCEPTION
    #
    # 而 Fallback 的“已满足条件”栏目只应展示 REQUIRED。
    # ========================================================

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
                "UNKNOWN",
            )
        ).upper()

        condition_type = normalize_text(
            item.get(
                "condition_type",
                item.get(
                    "type",
                    "",
                ),
            )
        ).upper()

        if not condition:
            continue

        if (
            condition_type == "REQUIRED"
            and status == "SATISFIED"
        ):

            satisfied.append(
                condition
            )

    satisfied = unique_texts(
        satisfied
    )

    # --------------------------------------------------------
    # 如果分类结果没有提供，
    # 使用 DecisionResult 已经生成的 REQUIRED 满足条件。
    #
    # 仍然不重新推理。
    # --------------------------------------------------------

    if not satisfied:

        required_satisfied_conditions = unique_texts(
            ensure_list(
                decision.get(
                    "required_satisfied_conditions",
                    [],
                )
            )
        )

        satisfied = required_satisfied_conditions

    # ========================================================
    # 从分类结果中提取：
    #
    # 1. 不满足的 REQUIRED
    # 2. 已触发的 EXCLUSION
    # 3. 已触发的 EXCEPTION
    #
    # 注意：
    #
    # EXCLUSION / EXCEPTION 的 NOT_SATISFIED
    # 不能进入普通 not_satisfied。
    # ========================================================

    required_not_satisfied = []

    for item in required_results:

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
                "UNKNOWN",
            )
        ).upper()

        if not condition:
            continue

        if status in {
            "NOT_SATISFIED",
            "UNSATISFIED",
        }:
            required_not_satisfied.append(
                condition
            )

    required_not_satisfied = unique_texts(
        required_not_satisfied
    )

    # --------------------------------------------------------
    # 如果 Required Results 没有提供，
    # 使用 DecisionResult 已经分类好的
    # required_not_satisfied_conditions。
    #
    # 仍然不重新推理。
    # --------------------------------------------------------

    if not required_not_satisfied:

        required_not_satisfied = unique_texts(
            ensure_list(
                decision.get(
                    "required_not_satisfied_conditions",
                    [],
                )
            )
        )

    # --------------------------------------------------------
    # 已触发排除条件
    #
    # EXCLUSION 的语义：
    #
    #     SATISFIED
    #         = 排除情形不存在 / 未触发
    #
    #     NOT_SATISFIED
    #         = 排除情形存在 / 已触发
    #
    # 因此这里只收集 NOT_SATISFIED。
    # --------------------------------------------------------

    triggered_exclusions = []

    for item in exclusion_results:

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
                "UNKNOWN",
            )
        ).upper()

        if not condition:
            continue

        if status in {
            "NOT_SATISFIED",
            "UNSATISFIED",
        }:
            triggered_exclusions.append(
                condition
            )

    triggered_exclusions = unique_texts(
        triggered_exclusions
    )

    # --------------------------------------------------------
    # 如果分类结果没有提供，
    # 直接使用 DecisionResult 已经生成的字段。
    # --------------------------------------------------------

    if not triggered_exclusions:

        triggered_exclusions = unique_texts(
            ensure_list(
                decision.get(
                    "triggered_exclusion_conditions",
                    [],
                )
            )
        )

    # --------------------------------------------------------
    # 未触发排除条件
    #
    # EXCLUSION + SATISFIED
    #     = 排除情形不存在，因此没有触发排除条件。
    #
    # 这里仅用于最终自然语言展示。
    # --------------------------------------------------------

    untriggered_exclusions = []

    for item in exclusion_results:

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
                "UNKNOWN",
            )
        ).upper()

        if not condition:
            continue

        if status == "SATISFIED":

            untriggered_exclusions.append(
                condition
            )

    untriggered_exclusions = unique_texts(
        untriggered_exclusions
    )

    # ========================================================
    # 已触发例外条件
    #
    # EXCEPTION 的语义：
    #
    #     SATISFIED
    #         = 例外情形不存在 / 未触发
    #
    #     NOT_SATISFIED
    #         = 例外情形存在 / 已触发
    #
    # 因此这里只收集 NOT_SATISFIED。
    # ========================================================

    triggered_exceptions = []

    for item in exception_results:

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
                "UNKNOWN",
            )
        ).upper()

        if not condition:
            continue

        if status in {
            "NOT_SATISFIED",
            "UNSATISFIED",
        }:
            triggered_exceptions.append(
                condition
            )

    triggered_exceptions = unique_texts(
        triggered_exceptions
    )

    # --------------------------------------------------------
    # 如果分类结果没有提供，
    # 直接使用 DecisionResult 已经生成的字段。
    # --------------------------------------------------------

    if not triggered_exceptions:

        triggered_exceptions = unique_texts(
            ensure_list(
                decision.get(
                    "triggered_exception_conditions",
                    [],
                )
            )
        )

    # --------------------------------------------------------
    # 未触发例外条件
    #
    # EXCEPTION + SATISFIED
    #     = 例外情形不存在，因此没有触发例外条件。
    #
    # 这里仅用于最终自然语言展示。
    # --------------------------------------------------------

    untriggered_exceptions = []

    for item in exception_results:

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
                "UNKNOWN",
            )
        ).upper()

        if not condition:
            continue

        if status == "SATISFIED":

            untriggered_exceptions.append(
                condition
            )

    untriggered_exceptions = unique_texts(
        untriggered_exceptions
    )

    # ========================================================
    # 最终“未满足必备条件”
    #
    # 只允许 REQUIRED 条件进入这里。
    #
    # 绝对不能把：
    #
    #     EXCLUSION
    #     EXCEPTION
    #
    # 的 NOT_SATISFIED 放进来。
    # ========================================================

    required_not_satisfied = unique_texts(
        required_not_satisfied
    )

    # ========================================================
    # DEFINITE 法律义务 / 法律后果
    #
    # V6.0-27 修正：
    #
    # Fallback 不再自己生成：
    #
    #     “应当订立无固定期限劳动合同”
    #
    # 这样的法律结论。
    #
    # 而是直接读取 Structured Rules 已经提供的：
    #
    #     legal_obligations
    #     legal_consequences
    #
    # 这样可以保证：
    #
    #     Structured Rule
    #          ↓
    #     Decision Engine
    #          ↓
    #     Fallback
    #
    # 整个过程没有新的法律推理。
    #
    # 如果当前规则没有提供法律义务或法律后果，
    # Fallback 不得自行创造新的法律内容。
    # ========================================================

    definite_obligations = []
    definite_consequences = []

    for rule in rules:

        if not isinstance(rule, dict):
            continue

        legal_obligations = ensure_list(
            rule.get(
                "legal_obligations",
                [],
            )
        )

        legal_consequences = ensure_list(
            rule.get(
                "legal_consequences",
                [],
            )
        )

        for obligation in legal_obligations:

            obligation_text = normalize_text(
                obligation
            )

            if obligation_text:

                definite_obligations.append(
                    obligation_text
                )

        for consequence in legal_consequences:

            consequence_text = normalize_text(
                consequence
            )

            if consequence_text:

                definite_consequences.append(
                    consequence_text
                )

    definite_obligations = unique_texts(
        definite_obligations
    )

    definite_consequences = unique_texts(
        definite_consequences
    )

    # ========================================================
    # CONDITIONAL / DEFINITE / NOT_ESTABLISHED
    #
    # 这里只读取 Engine Decision。
    # 不重新进行法律推理。
    # ========================================================

    if engine_decision == DECISION_CONDITIONAL:

        if satisfied:

            conclusion_lines = [
                "根据现有事实及已经确认的结构化法律条件，当前至少已经满足以下条件："
                + "、".join(
                    satisfied
                )
                + "。"
            ]

        else:

            conclusion_lines = [
                "根据现有事实，当前法律结论仍属于条件性结论。"
            ]

        if unknown:

            conclusion_lines.append(
                "但结构化法律规则中仍存在尚未确认的条件，因此当前不能将 CONDITIONAL 直接转换为确定性结论。"
            )

        if triggered_exclusions:

            conclusion_lines.append(
                "同时，以下排除条件已经触发："
                + "、".join(
                    triggered_exclusions
                )
                + "。"
            )

        if triggered_exceptions:

            conclusion_lines.append(
                "同时，以下例外条件已经触发："
                + "、".join(
                    triggered_exceptions
                )
                + "。"
            )

    elif engine_decision == DECISION_DEFINITE:

        # ----------------------------------------------------
        # DEFINITE：
        #
        # 直接使用 Structured Rules 中已经存在的
        # legal_obligations。
        #
        # 不重新进行法律推理。
        # ----------------------------------------------------

        if definite_obligations:

            conclusion_lines = [
                "是。"
                + "根据已经确认的结构化法律条件，"
                + "、".join(
                    definite_obligations
                )
                + "。"
            ]

        else:

            # ------------------------------------------------
            # 如果 Structured Rules 没有提供
            # legal_obligations，
            # 不自行创造法律义务。
            #
            # 使用安全的结构化 Decision 表述。
            # ------------------------------------------------

            conclusion_lines = [
                "根据已经确认的结构化法律条件，"
                "Decision Engine 的结论为 DEFINITE。"
            ]

    elif engine_decision == DECISION_NOT_ESTABLISHED:

        conclusion_lines = [
            "根据 Decision Engine 已确认的结构化法律条件，"
            "当前不能认定已经满足相关法律规则所规定的订立无固定期限劳动合同条件。"
        ]

        if required_not_satisfied:

            conclusion_lines.append(
                "其中，以下必备条件尚未满足："
                + "、".join(
                    required_not_satisfied
                )
                + "。"
            )

        if triggered_exclusions:

            conclusion_lines.append(
                "同时，以下排除条件已经触发："
                + "、".join(
                    triggered_exclusions
                )
                + "。"
            )

        if triggered_exceptions:

            conclusion_lines.append(
                "同时，以下例外条件已经触发："
                + "、".join(
                    triggered_exceptions
                )
                + "。"
            )

    else:

        conclusion_lines = [
            "根据 Decision Engine 已确认的结构化法律条件，"
            "当前不能认定相关法律条件已经成立。"
        ]

    # ========================================================
    # 用户事实
    # ========================================================

    fact_lines = []

    if user_facts:

        for fact in user_facts:

            fact_text = normalize_text(
                fact
            )

            if fact_text:

                fact_lines.append(
                    f"- {fact_text}"
                )

    else:

        fact_lines.append(
            "- 当前没有提取到明确用户事实。"
        )

    # ========================================================
    # 已满足条件
    #
    # 这里只展示 REQUIRED + SATISFIED。
    # ========================================================

    satisfied_lines = []

    if satisfied:

        for item in satisfied:

            satisfied_lines.append(
                f"- {item}"
            )

    else:

        satisfied_lines.append(
            "- 无。"
        )

    # ========================================================
    # 不满足的 REQUIRED 条件
    #
    # 这里不是所有 NOT_SATISFIED。
    #
    # 这里只输出 REQUIRED。
    # ========================================================

    required_not_satisfied_lines = []

    if required_not_satisfied:

        for item in required_not_satisfied:

            required_not_satisfied_lines.append(
                f"- {item}"
            )

    else:

        required_not_satisfied_lines.append(
            "- 无。"
        )

    # ========================================================
    # UNKNOWN 条件
    #
    # 每一个 UNKNOWN 必须逐项输出。
    # ========================================================

    unknown_lines = []

    for item in unknown:

        if isinstance(item, dict):

            condition = normalize_text(
                item.get(
                    "condition",
                    "",
                )
            )

            reason = normalize_text(
                item.get(
                    "reason",
                    "",
                )
            )

            if not condition:
                continue

            if reason:

                unknown_lines.append(
                    f"- {condition}：{reason}"
                )

            else:

                unknown_lines.append(
                    f"- {condition}"
                )

        else:

            condition = normalize_text(
                item
            )

            if condition:

                unknown_lines.append(
                    f"- {condition}"
                )

    if not unknown_lines:

        unknown_lines.append(
            "- 无。"
        )

    # ========================================================
    # 分类条件结果
    #
    # 这里保留原始 ConditionResult 的：
    #
    #     condition
    #     status
    #     condition_type
    #     reason
    #
    # 仅用于调试和透明展示。
    #
    # 不重新进行法律推理。
    # ========================================================

    condition_result_lines = []

    for index, item in enumerate(
        condition_results,
        start=1,
    ):

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
                "UNKNOWN",
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

        reason = normalize_text(
            item.get(
                "reason",
                "",
            )
        )

        if not condition:
            continue

        line = (
            f"{index}. "
            f"condition={condition}；"
            f"status={status}；"
            f"type={condition_type}"
        )

        if reason:

            line += (
                f"；reason={reason}"
            )

        condition_result_lines.append(
            line
        )

    condition_results_text = (
        "\n".join(
            condition_result_lines
        )
        or "无。"
    )

    # ========================================================
    # 分类结果自然语言转换
    # ========================================================

    def format_category_results(
        items,
        category,
        empty="- 无。",
    ):
        """
        将内部 ConditionResult 状态转换为最终回答中的自然语言语义。

        注意：

            REQUIRED：

                SATISFIED
                    → 已满足

                NOT_SATISFIED
                    → 未满足

                UNKNOWN
                    → 尚未确认

            EXCLUSION：

                SATISFIED
                    → 未触发

                NOT_SATISFIED
                    → 已触发

                UNKNOWN
                    → 尚未确认

            EXCEPTION：

                SATISFIED
                    → 未触发

                NOT_SATISFIED
                    → 已触发

                UNKNOWN
                    → 尚未确认

        这是内部状态到自然语言语义的映射，
        不属于重新法律推理。
        """

        lines = []

        semantic_map = {

            "REQUIRED": {
                "SATISFIED": "已满足",
                "NOT_SATISFIED": "未满足",
                "UNSATISFIED": "未满足",
                "UNKNOWN": "尚未确认",
            },

            "EXCLUSION": {
                "SATISFIED": "未触发",
                "NOT_SATISFIED": "已触发",
                "UNSATISFIED": "已触发",
                "UNKNOWN": "尚未确认",
            },

            "EXCEPTION": {
                "SATISFIED": "未触发",
                "NOT_SATISFIED": "已触发",
                "UNSATISFIED": "已触发",
                "UNKNOWN": "尚未确认",
            },
        }

        category = normalize_text(
            category
        ).upper()

        category_map = semantic_map.get(
            category,
            semantic_map["REQUIRED"],
        )

        for item in items:

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
                    "UNKNOWN",
                )
            ).upper()

            reason = normalize_text(
                item.get(
                    "reason",
                    "",
                )
            )

            if not condition:
                continue

            semantic_status = category_map.get(
                status,
                "尚未确认",
            )

            line = (
                f"- [{semantic_status}] "
                f"{condition}"
            )

            if reason:

                line += (
                    f"：{reason}"
                )

            lines.append(
                line
            )

        return lines or [empty]

    exclusion_lines = format_category_results(
        exclusion_results,
        "EXCLUSION",
    )

    exception_lines = format_category_results(
        exception_results,
        "EXCEPTION",
    )

    # ========================================================
    # 法律依据
    #
    # 绝不凭记忆增加法条。
    # 所有法律依据直接来自当前 Structured Rules。
    # ========================================================

    core_basis_lines = []
    related_basis_lines = []
    seen_basis = set()

    rules = prioritize_legal_rules(
        question=question,
        rules=rules,
    )

    for rule in rules:

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

    # ========================================================
    # 核心依据与相关依据分层
    # ========================================================

    basis_lines = []

    if core_basis_lines:

        basis_lines.append(
            "【核心法律依据】"
        )

        basis_lines.extend(
            f"{index}. {citation}"
            for index, citation in enumerate(
                core_basis_lines,
                1,
            )
        )

    if related_basis_lines:

        basis_lines.append(
            "【相关法律依据】"
        )

        start_index = (
            len(core_basis_lines)
            + 1
        )

        basis_lines.extend(
            f"{index}. {citation}"
            for index, citation in enumerate(
                related_basis_lines,
                start_index,
            )
        )

    if not basis_lines:

        basis_lines.append(
            "当前没有可用于最终回答的结构化法律依据。"
        )

    # ========================================================
    # 法律分析
    # ========================================================

    analysis_lines = []

    # --------------------------------------------------------
    # 1. 用户事实
    # --------------------------------------------------------

    analysis_lines.append(
        "1. 用户事实："
    )

    analysis_lines.extend(
        fact_lines
    )

    # --------------------------------------------------------
    # 2. 已满足条件
    # --------------------------------------------------------

    analysis_lines.append(
        "2. 已满足条件："
    )

    analysis_lines.extend(
        satisfied_lines
    )

    # --------------------------------------------------------
    # 3. 不满足的必备条件
    # --------------------------------------------------------

    analysis_lines.append(
        "3. 不满足的必备条件："
    )

    analysis_lines.extend(
        required_not_satisfied_lines
    )

    # --------------------------------------------------------
    # 4. 已触发排除条件
    # --------------------------------------------------------

    analysis_lines.append(
        "4. 已触发排除条件："
    )

    if triggered_exclusions:

        for item in triggered_exclusions:

            analysis_lines.append(
                f"- {item}"
            )

    else:

        analysis_lines.append(
            "- 无。"
        )

    # --------------------------------------------------------
    # 未触发排除条件
    #
    # EXCLUSION + SATISFIED
    # 表示排除情形不存在，因此排除条件没有被触发。
    #
    # 不能将其显示为“已满足条件”。
    # --------------------------------------------------------

    if untriggered_exclusions:

        analysis_lines.append(
            "未触发排除条件："
        )

        for item in untriggered_exclusions:

            analysis_lines.append(
                f"- {item}"
            )

    # --------------------------------------------------------
    # 5. 已触发例外条件
    # --------------------------------------------------------

    analysis_lines.append(
        "5. 已触发例外条件："
    )

    if triggered_exceptions:

        for item in triggered_exceptions:

            analysis_lines.append(
                f"- {item}"
            )

    else:

        analysis_lines.append(
            "- 无。"
        )

    # --------------------------------------------------------
    # 未触发例外条件
    #
    # EXCEPTION + SATISFIED
    # 表示例外情形不存在，因此例外条件没有被触发。
    #
    # 不能将其显示为“已满足条件”。
    # --------------------------------------------------------

    if untriggered_exceptions:

        analysis_lines.append(
            "未触发例外条件："
        )

        for item in untriggered_exceptions:

            analysis_lines.append(
                f"- {item}"
            )

    # --------------------------------------------------------
    # 6. 尚未确认条件
    #
    # 注意：
    #
    # UNKNOWN 不应该被写成“尚未确认的必备条件”，
    # 因为其中可能包含 EXCLUSION / EXCEPTION。
    # ========================================================

    analysis_lines.append(
        "6. 尚未确认条件："
    )

    analysis_lines.extend(
        unknown_lines
    )

    # --------------------------------------------------------
    # 7. 法律后果
    # --------------------------------------------------------

    analysis_lines.append(
        "7. 法律后果："
    )

    if engine_decision == DECISION_CONDITIONAL:

        analysis_lines.append(
            "- 当前属于条件性结论，在关键事实尚未确认之前，不能直接将条件性 Decision 转换为确定性结论。"
        )

    elif engine_decision == DECISION_DEFINITE:

        # ----------------------------------------------------
        # DEFINITE：
        #
        # 直接读取 Structured Rules 已经提供的
        # legal_consequences。
        #
        # 如果 legal_consequences 为空，
        # 再使用 legal_obligations。
        #
        # 这不是重新推理，只是结构化字段展示。
        # ----------------------------------------------------

        if definite_consequences:

            for consequence in definite_consequences:

                analysis_lines.append(
                    f"- {consequence}"
                )

        elif definite_obligations:

            for obligation in definite_obligations:

                analysis_lines.append(
                    f"- {obligation}"
                )

        else:

            analysis_lines.append(
                "- Decision Engine 已确认当前 Decision 为 DEFINITE，"
                "但 Structured Rules 未提供具体 legal_obligations 或 legal_consequences。"
            )

    elif engine_decision == DECISION_NOT_ESTABLISHED:

        analysis_lines.append(
            "- 根据 Decision Engine 的 NOT_ESTABLISHED 结论，"
            "当前不能认定已经满足相关法律规则所规定的订立无固定期限劳动合同条件。"
        )

    else:

        analysis_lines.append(
            "- 根据 Decision Engine 已确认的结构化法律条件，"
            "当前不能认定相关法律条件已经成立。"
        )

    # ========================================================
    # 需要注意
    #
    # 这里暂时保留兼容内容。
    #
    # answer_question() 在 Final Validation 之后，
    # 会再次调用 build_deterministic_notices()
    # 并用确定性 UNKNOWN 列表替换这里的内容。
    #
    # 因此最终输出中的【需要注意】不依赖这里的自然语言。
    # ========================================================

    notice_lines = []

    if unknown:

        notice_lines.append(
            "- 当前存在尚未确认的条件，不能自行将 UNKNOWN 条件视为已经成立。"
        )

        notice_lines.append(
            "- UNKNOWN 条件的最终列表及顺序以 Structured Decision 为准。"
        )

    if triggered_exclusions:

        notice_lines.append(
            "- 已触发排除条件不得写成普通“未满足条件”。"
        )

    if triggered_exceptions:

        notice_lines.append(
            "- 已触发例外条件不得写成普通“未满足条件”。"
        )

    if not notice_lines:

        notice_lines.append(
            "- 最终回答仅依据当前结构化 Decision 和 Rules，不新增结构化数据之外的法律判断。"
        )

    # ========================================================
    # 组装最终答案
    # ========================================================

    answer = (
        SECTION_CONCLUSION
        + "\n"
        + "\n".join(
            conclusion_lines
        )
        + "\n\n"
        + SECTION_BASIS
        + "\n"
        + "\n".join(
            basis_lines
        )
        + "\n\n"
        + SECTION_ANALYSIS
        + "\n"
        + "\n".join(
            analysis_lines
        )
        + "\n\n"
        + SECTION_NOTICE
        + "\n"
        + "\n".join(
            notice_lines
        )
    )

    return _clean_answer(
        answer
    )
