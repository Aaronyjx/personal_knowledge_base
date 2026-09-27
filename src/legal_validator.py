from src.legal_constants import (
    DEFINITE,
    CONDITIONAL,
    NOT_ESTABLISHED,
)

# -*- coding: utf-8 -*-

"""
RAG V6.1
Legal Validation Layer

============================================================
功能
============================================================

负责 Legal RAG 的最终答案验证与安全边界检查。

主要职责：

    1. 答案清洗与结构验证
    2. 用户事实忠实性验证
    3. Fact → Condition 映射验证
    4. Decision 与答案一致性验证
    5. UNKNOWN / CONDITIONAL 安全验证
    6. 法律条件防臆造验证
    7. 法律依据与 Citation 验证
    8. Decision Engine ConditionResult 完整性验证
    9. Condition Category 完整性验证
    10. 最终 Validation 与安全 Fallback 调度

本模块不负责：

    - Structured Article → Rule
    - Legal Decision Engine 判定
    - Decision Adapter
    - Answer Builder
    - Ollama Prompt / LLM 调用

原则：

    Validation 只能验证已经产生的结构化结果，
    不得在验证阶段重新推导法律结论。
============================================================
"""

import re
from typing import Any, Dict, List

from src.legal_common import (
    ensure_list,
    get_field,
    get_rule_value,
    normalize_text,
)

from src.legal_fact_validator import (
    validate_fact_condition_mapping,
    validate_user_facts,
    validate_three_contract_fact,
)

from src.legal_rule_builder import (
    build_rules_from_articles,
)

from src.legal_answer_sanitizer import (
    clean_answer,
)


from src.legal_condition_validator import (
    validate_answer_structure,
    validate_no_manufactured_unknown,
    validate_legal_condition_invention,
    validate_conditional_state,
    validate_unknown_conditions,
)



# ============================================================
# Legal Decision Engine 状态
# ============================================================


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
















from src.legal_basis_validator import (
    validate_legal_basis,
)


def validate_decision_consistency(
    answer: str,
    decision: Dict[str, Any],
) -> bool:

    engine_status = normalize_text(
        decision.get(
            "engine_decision",
            "",
        )
    ).upper()

    if engine_status == DEFINITE:

        forbidden = [
            "尚不能确认",
            "无法确认是否满足",
            "条件尚未确认",
            "无法作出确定性结论",
            "当前条件未知",
            "部分条件未知",
            "以上条件未知",
        ]

        # ========================================================
        # DEFINITE 语义边界
        # ========================================================
        #
        # Engine 已经判定：
        #
        #     DEFINITE
        #
        # 则 Ollama 不得把最终法律结论降级为：
        #
        #     UNKNOWN
        #     CONDITIONAL
        #
        # 特别是不能出现：
        #
        #     “条件尚未确认”
        #     “无法作出确定性结论”
        #     “部分条件未知”
        #
        # 这些表达直接否定 Engine 的 DEFINITE 决策。
        #
        # 注意：
        #
        # 这里只检查最终答案中的确定性状态表达，
        # 不重新进行法律推理。
        # ========================================================

        for pattern in forbidden:

            if pattern in answer:
                return False

    if engine_status == NOT_ESTABLISHED:

        # ========================================================
        # NOT_ESTABLISHED 语义边界
        # ========================================================
        #
        # NOT_ESTABLISHED 的含义是：
        #
        #     当前事实下，法律要件尚未被完整确认，
        #     因此不能作出已经满足全部条件的确定性结论。
        #
        # 特别注意：
        #
        #     NOT_ESTABLISHED
        #
        # 不能被 Ollama 改写成：
        #
        #     “无需签订”
        #     “不需要签订”
        #     “不必签订”
        #     “没有义务签订”
        #
        # 因为这些表达是在作出“法律义务不存在”的
        # 确定性结论，而不是表达“当前尚不能确认”。
        #
        # 本检查只针对最终回答的结论语义，
        # 不修改 Legal Decision Engine 本身。
        # ========================================================

        forbidden = [
            # ----------------------------------------------------
            # 明确表示无需履行义务
            # ----------------------------------------------------
            "无需签订",
            "无需订立",
            "不需要签订",
            "不需要订立",
            "不必签订",
            "不必订立",
            "没有义务签订",
            "没有义务订立",

            # ----------------------------------------------------
            # 明确表示不存在签订义务
            # ----------------------------------------------------
            "不存在签订义务",
            "不存在订立义务",
            "不存在签订无固定期限劳动合同的义务",
            "不存在订立无固定期限劳动合同的义务",

            # ----------------------------------------------------
            # 明确表示已经排除法律义务
            # ----------------------------------------------------
            "排除了签订无固定期限劳动合同的法律义务",
            "排除了订立无固定期限劳动合同的法律义务",
            "排除签订无固定期限劳动合同的法律义务",
            "排除订立无固定期限劳动合同的法律义务",
            "已经排除签订无固定期限劳动合同的义务",
            "已经排除订立无固定期限劳动合同的义务",

            # ----------------------------------------------------
            # 确定性“因此/所以/故”结论
            # ----------------------------------------------------
            "因此无需签订",
            "因此无需订立",
            "因此不需要签订",
            "因此不需要订立",
            "因此不必签订",
            "因此不必订立",
            "故无需签订",
            "故无需订立",
            "故不需要签订",
            "故不需要订立",
            "故不必签订",
            "故不必订立",

            # ----------------------------------------------------
            # 原有确定性表达
            # ----------------------------------------------------
            "已经确定满足全部条件",
            "已经完全满足全部条件",
            "当然必须签订",
            "一定必须签订",
        ]

        for pattern in forbidden:

            if pattern in answer:
                return False

    return True


def validate_engine_condition_completeness(
    decision: Dict[str, Any],
) -> bool:
    """
    V6.0-27：验证 Decision Engine V6.0-14 的 ConditionResult 完整性。

    正常结构固定为：

        REQUIRED   = 4
        EXCLUSION  = 3
        EXCEPTION  = 1
        TOTAL      = 8

    CONDITIONAL 情况下如果不是完整 8 条，必须进入安全 Fallback，
    RAG 不得自行补条件。
    """

    if not isinstance(decision, dict):
        return False

    engine_decision = normalize_text(
        decision.get("engine_decision", "")
    ).upper()

    count = decision.get(
        "engine_condition_results_count",
        None,
    )

    if not isinstance(count, int):
        raw_decision = decision.get("raw_decision")
        count = len(
            ensure_list(
                get_field(
                    raw_decision,
                    "condition_results",
                    [],
                )
            )
        )

    if engine_decision == CONDITIONAL:
        return count == 8

    return count == 0 or count == 8


def validate_condition_categories(
    decision: Dict[str, Any],
) -> bool:
    """
    V6.0-27：严格验证 Engine V6.0-14 的三类 ConditionResult。

        REQUIRED   = 4
        EXCLUSION  = 3
        EXCEPTION  = 1
        TOTAL      = 8

    分类直接来自 ConditionResult.condition_type / type，
    不再从 Rules 猜测类别。
    """

    if not isinstance(decision, dict):
        return False

    results = ensure_list(
        decision.get("condition_results", [])
    )

    if len(results) != 8:
        return False

    counts = {
        "REQUIRED": 0,
        "EXCLUSION": 0,
        "EXCEPTION": 0,
    }

    names = set()

    for item in results:
        if not isinstance(item, dict):
            return False

        condition = normalize_text(
            item.get("condition", "")
        )
        status = normalize_text(
            item.get("status", "")
        ).upper()
        category = normalize_text(
            item.get(
                "condition_type",
                item.get(
                    "category",
                    item.get("type", ""),
                ),
            )
        ).upper()

        if not condition or not category:
            return False

        if category not in counts:
            return False

        if status not in {
            "SATISFIED",
            "NOT_SATISFIED",
            "UNKNOWN",
            "UNSATISFIED",
        }:
            return False

        if condition in names:
            return False

        names.add(condition)
        counts[category] += 1

    return counts == {
        "REQUIRED": 4,
        "EXCLUSION": 3,
        "EXCEPTION": 1,
    }


def final_validation(
    answer: str,
    question: str,
    decision: Dict[str, Any],
) -> str:
    """
    RAG V6.1 Final Validation。

    最终验证层负责：

        Ollama Answer
              ↓
        Structural Validation
              ↓
        Fact Validation
              ↓
        Condition Validation
              ↓
        Legal Basis Validation
              ↓
        PASS / Deterministic Fallback

    核心原则：

    1. 不修改 Legal Decision Engine 输出。
    2. 不由 Validation 层重新进行法律推理。
    3. Ollama 失败或验证失败时，只允许使用确定性的 Python Fallback。
    4. Fallback 仍然必须经过同一套安全验证。
    5. 如果 Engine 的 ConditionResult 不完整，绝不由 RAG 自行补条件。
    6. 最终绝不返回未经验证的 Ollama 原始答案。
    """

    print()
    print("=" * 70)
    print("Step 5 / Final Validation")
    print("=" * 70)

    from src.legal_fallback import build_fallback_answer

    question = normalize_text(question)
    answer = clean_answer(answer)

    if not isinstance(decision, dict):
        print()
        print("⚠️ Decision 不是有效 Dict，使用空安全回答。")
        return build_fallback_answer(
            question=question,
            decision={},
        )

    def run_checks(
        text: str,
        question: str,
        decision: Dict[str, Any],
    ) -> List[str]:

        failures: List[str] = []

        if not text:
            failures.append("EMPTY")
            return failures

        # ============================================================
        # Final Validation 1：Engine Condition Completeness
        # ============================================================

        if not validate_engine_condition_completeness(
            decision
        ):
            failures.append(
                "ENGINE_CONDITION_COMPLETENESS"
            )

        # ============================================================
        # Final Validation 2：Condition Category
        # ============================================================

        if not validate_condition_categories(
            decision
        ):
            failures.append(
                "CONDITION_CATEGORY"
            )

        # ============================================================
        # Final Validation 3：答案结构
        # ============================================================

        if not validate_answer_structure(
            text
        ):
            failures.append(
                "ANSWER_STRUCTURE"
            )

        # ============================================================
        # Final Validation 4：用户事实保真
        # ============================================================

        if not validate_user_facts(
            text,
            decision,
        ):
            failures.append(
                "USER_FACT_VALIDATION"
            )

        # ============================================================
        # Final Validation 5：三次合同事实
        # ============================================================

        if not validate_three_contract_fact(
            text,
            decision,
        ):
            failures.append(
                "THREE_CONTRACT_FACT"
            )

        # ============================================================
        # Final Validation 6：Fact → Condition Mapping
        # ============================================================

        if not validate_fact_condition_mapping(
            text,
            question,
            decision,
        ):
            failures.append(
                "FACT_CONDITION_MAPPING"
            )

        # ============================================================
        # Final Validation 7：禁止制造 UNKNOWN
        # ============================================================

        if not validate_no_manufactured_unknown(
            text,
            decision,
        ):
            failures.append(
                "MANUFACTURED_UNKNOWN"
            )

        # ============================================================
        # Final Validation 8：禁止发明法律条件
        # ============================================================

        if not validate_legal_condition_invention(
            text,
            decision,
        ):
            failures.append(
                "LEGAL_CONDITION_INVENTION"
            )

        # ============================================================
        # Final Validation 9：Conditional 状态
        # ============================================================

        if not validate_conditional_state(
            text,
            decision,
        ):
            failures.append(
                "CONDITIONAL"
            )

        # ============================================================
        # Final Validation 10：UNKNOWN 条件
        # ============================================================

        if not validate_unknown_conditions(
            text,
            decision,
        ):
            failures.append(
                "UNKNOWN"
            )

        # ============================================================
        # Final Validation 11：法律依据
        # ============================================================

        rules = ensure_list(
            decision.get(
                "rules",
                []
            )
        )

        if not validate_legal_basis(
            text,
            rules,
        ):
            failures.append(
                "LEGAL_BASIS"
            )

        # ============================================================
        # Final Validation 12：Decision Consistency
        # ============================================================

        if not validate_decision_consistency(
            text,
            decision,
        ):
            failures.append(
                "DECISION_CONSISTENCY"
            )

        return failures

    # ========================================================
    # DEBUG：Final Validation 实际输入诊断
    #
    # V6.0-27
    #
    # 用于定位：
    #
    #     ANSWER_STRUCTURE
    #
    # 是否真的由 validate_answer_structure()
    # 返回 False 导致。
    #
    # 注意：
    #
    # 这里只是诊断代码，不修改 answer。
    # ========================================================

    print()
    print("=" * 70)
    print("=" * 70)

    print(answer)

    print()
    print("DEBUG / Section Counts")

    for section in REQUIRED_SECTIONS:
        print(
            f"{section}: "
            f"{answer.count(section)}"
        )

    print()
    print("DEBUG / Section Positions")

    for section in REQUIRED_SECTIONS:
        print(
            f"{section}: "
            f"{answer.find(section)}"
        )

    print()
    print(
        "DEBUG / validate_answer_structure:",
        validate_answer_structure(answer),
    )

    print("=" * 70)

    failures = run_checks(
        answer,
        question,
        decision,
    )

    if not failures:
        print()
        print("✅ 最终答案验证通过")
        return answer

    print()
    print(
        "⚠️ Ollama 回答未通过 Validation："
        + ", ".join(failures)
    )

    # --------------------------------------------------------
    # 安全 Fallback
    # --------------------------------------------------------
    #
    # 只要任意一项验证失败，就不能继续信任 Ollama 输出。
    # Fallback 使用已经完成的 Structured Decision / Rules，
    # 不重新推理，也不补充 Decision Engine 没有提供的条件。
    # --------------------------------------------------------

    print()
    print("⚠️ V6.1 启用安全 Fallback。")

    fallback = build_fallback_answer(
        question=question,
        decision=decision,
    )
    fallback = clean_answer(fallback)

    fallback_failures = run_checks(
        fallback,
        question,
        decision,
    )

    if not fallback_failures:
        print()
        print("✅ Fallback 最终答案验证通过")
        return fallback

    print()
    print(
        "⚠️ Fallback 仍未通过全部 Validation："
        + ", ".join(fallback_failures)
    )

    # 最后返回确定性的结构化 Fallback，而不是返回未经验证的 Ollama 答案。
    # 不递归调用 final_validation，避免无限递归。
    return fallback


