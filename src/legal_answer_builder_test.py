# -*- coding: utf-8 -*-

"""
RAG V6.0-14
Legal Answer Builder Test
============================================================

功能
============================================================

本模块负责：

    Legal Answer Builder
          ↓
    Component Test
          ↓
    Decision Compatibility Test

本模块仅包含：

    - 测试数据构造
    - Component Test
    - Decision Compatibility Test
    - Test CLI

生产代码仍位于：

    src/legal_answer_builder.py

============================================================
"""

from __future__ import annotations

from typing import Any, Dict, List

from src.legal_decision_engine import (
    ConditionResult,
    DecisionResult,
)

from src.legal_answer_builder import (
    BUILDER_VERSION,

    SATISFIED,
    NOT_SATISFIED,
    UNKNOWN,

    REQUIRED,
    EXCLUSION,
    EXCEPTION,

    DEFINITE,
    CONDITIONAL,
    NOT_ESTABLISHED,

    EXPECTED_REQUIRED_CONDITIONS,
    EXPECTED_EXCLUSION_CONDITIONS,
    EXPECTED_EXCEPTION_CONDITIONS,
    EXPECTED_TOTAL_CONDITIONS,

    ConditionView,
    StructuredAnswer,

    safe_text,
    get_value,
    normalize_list,
    unique_strings,

    adapt_decision_for_answer_builder,
    build_answer_context,
    build_plain_answer,
    build_prompt_context,
    summarize_structured_answer,

)


def _make_test_condition(
    condition: str,
    status: str,
    condition_type: str,
    reason: str = "",
) -> ConditionView:
    """
    仅用于 Builder Component Test 的展示对象。

    注意：

    真实生产环境中 ConditionResult
    必须由 Decision Engine 创建。

    这里创建的是 ConditionView，
    不是 ConditionResult。
    """

    return ConditionView(
        condition=condition,
        status=status,
        reason=reason,
        condition_type=condition_type,
    )


def _make_test_structured_answer() -> StructuredAnswer:
    """
    创建 Builder 自身 Component Test 数据。

    不模拟法律推理。

    只是验证 Builder 的结构和格式化能力。
    """

    conditions = [
        _make_test_condition(
            EXPECTED_REQUIRED_CONDITIONS[0],
            SATISFIED,
            REQUIRED,
            "测试：条件满足。",
        ),

        _make_test_condition(
            EXPECTED_REQUIRED_CONDITIONS[1],
            SATISFIED,
            REQUIRED,
            "测试：后续合同存在。",
        ),

        _make_test_condition(
            EXPECTED_REQUIRED_CONDITIONS[2],
            UNKNOWN,
            REQUIRED,
            "测试：无法仅根据合同次数确定。",
        ),

        _make_test_condition(
            EXPECTED_REQUIRED_CONDITIONS[3],
            UNKNOWN,
            REQUIRED,
            "测试：用户未提供相关事实。",
        ),

        _make_test_condition(
            EXPECTED_EXCLUSION_CONDITIONS[0],
            UNKNOWN,
            EXCLUSION,
            "测试：用户未提供相关事实。",
        ),

        _make_test_condition(
            EXPECTED_EXCLUSION_CONDITIONS[1],
            UNKNOWN,
            EXCLUSION,
            "测试：用户未提供相关事实。",
        ),

        _make_test_condition(
            EXPECTED_EXCLUSION_CONDITIONS[2],
            UNKNOWN,
            EXCLUSION,
            "测试：用户未提供相关事实。",
        ),

        _make_test_condition(
            EXPECTED_EXCEPTION_CONDITIONS[0],
            UNKNOWN,
            EXCEPTION,
            "测试：用户未提供相关事实。",
        ),
    ]

    return StructuredAnswer(
        decision=CONDITIONAL,

        user_facts=[
            "公司连续签订三次固定期限劳动合同",
        ],

        satisfied_conditions=[
            EXPECTED_REQUIRED_CONDITIONS[0],
            EXPECTED_REQUIRED_CONDITIONS[1],
        ],

        unknown_conditions=[
            EXPECTED_REQUIRED_CONDITIONS[2],
            EXPECTED_REQUIRED_CONDITIONS[3],
            EXPECTED_EXCLUSION_CONDITIONS[0],
            EXPECTED_EXCLUSION_CONDITIONS[1],
            EXPECTED_EXCLUSION_CONDITIONS[2],
            EXPECTED_EXCEPTION_CONDITIONS[0],
        ],

        not_satisfied_conditions=[],

        required_conditions=[
            *EXPECTED_REQUIRED_CONDITIONS,
        ],

        exclusion_conditions=[
            *EXPECTED_EXCLUSION_CONDITIONS,
        ],

        exception_conditions=[
            *EXPECTED_EXCEPTION_CONDITIONS,
        ],

        condition_results=conditions,

        legal_rules=[
            "劳动合同法相关无固定期限劳动合同规则",
        ],

        rule_dependencies=[],

        contract_sequence={
            "count": 3,
            "term_type": "fixed",
            "continuous": True,
        },

        selected_rule=(
            "连续订立固定期限劳动合同后"
            "订立无固定期限劳动合同的规则"
        ),

        explanation=(
            "测试 Decision=CONDITIONAL。"
            "部分条件已经满足，"
            "仍存在需要进一步确认的法律事实。"
        ),

        engine_version="V6.0-14",

        builder_version=BUILDER_VERSION,
    )


# ============================================================
# Component Test
# ============================================================

def run_component_test() -> None:
    """
    Builder Component Test。

    验证：

        1. StructuredAnswer
        2. ConditionView
        3. Condition 分类
        4. 状态分类
        5. Plain Answer
        6. Prompt Context
        7. 用户事实与规则条件分离
        8. 8 条 Condition 结构
    """

    print(
        "=" * 70
    )

    print(
        f"Legal Answer Builder "
        f"{BUILDER_VERSION}"
    )

    print(
        "=" * 70
    )

    answer = (
        _make_test_structured_answer()
    )

    # --------------------------------------------------------
    # Basic Decision
    # --------------------------------------------------------

    assert (
        answer.decision
        == CONDITIONAL
    ), (
        "Decision 应为 CONDITIONAL"
    )

    # --------------------------------------------------------
    # User Fact
    # --------------------------------------------------------

    assert (
        "公司连续签订三次固定期限劳动合同"
        in answer.user_facts
    ), (
        "用户事实缺失"
    )

    # --------------------------------------------------------
    # Condition Count
    # --------------------------------------------------------

    assert (
        len(answer.condition_results)
        == 8
    ), (
        "ConditionResult 展示数量必须为 8"
    )

    # --------------------------------------------------------
    # Category Count
    # --------------------------------------------------------

    assert (
        len(answer.required_conditions)
        == 4
    ), (
        "REQUIRED 必须为 4"
    )

    assert (
        len(answer.exclusion_conditions)
        == 3
    ), (
        "EXCLUSION 必须为 3"
    )

    assert (
        len(answer.exception_conditions)
        == 1
    ), (
        "EXCEPTION 必须为 1"
    )

    # --------------------------------------------------------
    # Status Count
    # --------------------------------------------------------

    assert (
        len(answer.satisfied_conditions)
        == 2
    ), (
        "测试中 SATISFIED 必须为 2"
    )

    assert (
        len(answer.unknown_conditions)
        == 6
    ), (
        "测试中 UNKNOWN 必须为 6"
    )

    assert (
        len(answer.not_satisfied_conditions)
        == 0
    ), (
        "测试中 NOT_SATISFIED 必须为 0"
    )

    # --------------------------------------------------------
    # Critical Fact / Condition Separation
    # --------------------------------------------------------

    assert (
        "公司连续签订三次固定期限劳动合同"
        in answer.user_facts
    )

    assert (
        "连续订立二次固定期限劳动合同"
        in answer.required_conditions
    )

    assert (
        "公司连续签订三次固定期限劳动合同"
        not in answer.required_conditions
    ), (
        "用户事实不能被错误转换成法律规则条件"
    )

    # --------------------------------------------------------
    # UNKNOWN Preservation
    # --------------------------------------------------------

    assert (
        "续订劳动合同"
        in answer.unknown_conditions
    ), (
        "续订劳动合同必须保持 UNKNOWN"
    )

    assert (
        "劳动者提出或者同意续订、订立劳动合同"
        in answer.unknown_conditions
    ), (
        "劳动者提出或者同意续订、订立劳动合同"
        "必须保持 UNKNOWN"
    )

    # --------------------------------------------------------
    # Condition Type
    # --------------------------------------------------------

    required_views = [
        item
        for item in answer.condition_results
        if item.condition_type == REQUIRED
    ]

    exclusion_views = [
        item
        for item in answer.condition_results
        if item.condition_type == EXCLUSION
    ]

    exception_views = [
        item
        for item in answer.condition_results
        if item.condition_type == EXCEPTION
    ]

    assert (
        len(required_views)
        == 4
    )

    assert (
        len(exclusion_views)
        == 3
    )

    assert (
        len(exception_views)
        == 1
    )

    # --------------------------------------------------------
    # Plain Answer
    # --------------------------------------------------------

    plain = build_plain_answer(
        answer
    )

    assert (
        "CONDITIONAL"
        in plain
    )

    assert (
        "公司连续签订三次固定期限劳动合同"
        in plain
    )

    assert (
        "续订劳动合同"
        in plain
    )

    # --------------------------------------------------------
    # Prompt Context
    # --------------------------------------------------------

    prompt_context = (
        build_prompt_context(
            answer
        )
    )

    assert (
        "UNKNOWN"
        in prompt_context
    )

    assert (
        "不得重新创造事实"
        in prompt_context
    )

    # --------------------------------------------------------
    # Context
    # --------------------------------------------------------

    context = build_answer_context(
        answer
    )

    assert (
        context["decision"]
        == CONDITIONAL
    )

    assert (
        len(
            context["condition_results"]
        )
        == 8
    )

    # --------------------------------------------------------
    # Output
    # --------------------------------------------------------

    print(
        ""
    )

    print(
        "Decision:"
    )

    print(
        f"  {answer.decision}"
    )

    print(
        ""
    )

    print(
        "User Facts:"
    )

    for fact in answer.user_facts:
        print(
            f"  - {fact}"
        )

    print(
        ""
    )

    print(
        "Condition Results:"
    )

    for index, item in enumerate(
        answer.condition_results,
        start=1,
    ):
        print(
            f"  {index}. "
            f"[{item.condition_type}] "
            f"{item.status}"
        )

        print(
            f"     {item.condition}"
        )

    print(
        ""
    )

    print(
        "Condition Structure:"
    )

    print(
        f"  REQUIRED   = "
        f"{len(answer.required_conditions)}"
    )

    print(
        f"  EXCLUSION  = "
        f"{len(answer.exclusion_conditions)}"
    )

    print(
        f"  EXCEPTION  = "
        f"{len(answer.exception_conditions)}"
    )

    print(
        f"  TOTAL      = "
        f"{len(answer.condition_results)}"
    )

    print(
        ""
    )

    print(
        "Satisfied Conditions:"
    )

    for condition in (
        answer.satisfied_conditions
    ):
        print(
            f"  - {condition}"
        )

    print(
        ""
    )

    print(
        "Unknown Conditions:"
    )

    for condition in (
        answer.unknown_conditions
    ):
        print(
            f"  - {condition}"
        )

    print(
        ""
    )

    print(
        summarize_structured_answer(
            answer
        )
    )

    print(
        ""
    )

    print(
        "All assertions passed."
    )

    print(
        ""
    )

    print(
        f"{BUILDER_VERSION} "
        "Component Test PASSED"
    )


# ============================================================
# DecisionResult Compatibility Test
# ============================================================

def run_decision_compatibility_test() -> None:
    """
    使用一个模拟 DecisionResult dict
    验证 Builder 与 Decision Engine 输出结构兼容。

    注意：

    这里只模拟 Engine 的输出结构，
    不模拟 Engine 的法律推理过程。
    """

    decision = {
        "decision": CONDITIONAL,

        "explicit_facts": [
            "公司连续签订三次固定期限劳动合同",
        ],

        "condition_results": [
            {
                "condition":
                    EXPECTED_REQUIRED_CONDITIONS[0],
                "status":
                    SATISFIED,
                "reason":
                    "数量门槛满足。",
                "condition_type":
                    REQUIRED,
            },
            {
                "condition":
                    EXPECTED_REQUIRED_CONDITIONS[1],
                "status":
                    SATISFIED,
                "reason":
                    "存在后续合同。",
                "condition_type":
                    REQUIRED,
            },
            {
                "condition":
                    EXPECTED_REQUIRED_CONDITIONS[2],
                "status":
                    UNKNOWN,
                "reason":
                    "无法仅根据合同次数确认。",
                "condition_type":
                    REQUIRED,
            },
            {
                "condition":
                    EXPECTED_REQUIRED_CONDITIONS[3],
                "status":
                    UNKNOWN,
                "reason":
                    "用户未提供。",
                "condition_type":
                    REQUIRED,
            },
            {
                "condition":
                    EXPECTED_EXCLUSION_CONDITIONS[0],
                "status":
                    UNKNOWN,
                "reason":
                    "用户未提供。",
                "condition_type":
                    EXCLUSION,
            },
            {
                "condition":
                    EXPECTED_EXCLUSION_CONDITIONS[1],
                "status":
                    UNKNOWN,
                "reason":
                    "用户未提供。",
                "condition_type":
                    EXCLUSION,
            },
            {
                "condition":
                    EXPECTED_EXCLUSION_CONDITIONS[2],
                "status":
                    UNKNOWN,
                "reason":
                    "用户未提供。",
                "condition_type":
                    EXCLUSION,
            },
            {
                "condition":
                    EXPECTED_EXCEPTION_CONDITIONS[0],
                "status":
                    UNKNOWN,
                "reason":
                    "用户未提供。",
                "condition_type":
                    EXCEPTION,
            },
        ],

        "contract_sequence": {
            "count": 3,
            "term_type": "fixed",
            "continuous": True,
        },

        "rule_dependencies": [],

        "selected_rule":
            "劳动合同法相关规则",

        "explanation":
            "Decision=CONDITIONAL",

        "engine_version":
            "V6.0-14",
    }

    answer = (
        adapt_decision_for_answer_builder(
            decision
        )
    )

    assert (
        isinstance(
            answer,
            StructuredAnswer,
        )
    )

    assert (
        answer.decision
        == CONDITIONAL
    )

    assert (
        len(
            answer.condition_results
        )
        == 8
    )

    assert (
        len(
            answer.required_conditions
        )
        == 4
    )

    assert (
        len(
            answer.exclusion_conditions
        )
        == 3
    )

    assert (
        len(
            answer.exception_conditions
        )
        == 1
    )

    assert (
        "续订劳动合同"
        in answer.unknown_conditions
    )

    print(
        "DecisionResult compatibility test PASSED"
    )


# ============================================================
# Main
# ============================================================

def main() -> None:
    """
    Builder 独立测试入口。
    """

    print(
        ""
    )

    print(
        "=" * 70
    )

    print(
        f"Legal Answer Builder "
        f"{BUILDER_VERSION}"
    )

    print(
        "=" * 70
    )

    print(
        ""
    )

    print(
        "请选择测试："
    )

    print(
        ""
    )

    print(
        "1. Component Test"
    )

    print(
        "2. DecisionResult Compatibility Test"
    )

    print(
        "3. 全部测试"
    )

    print(
        ""
    )

    choice = input(
        "请输入 1、2 或 3："
    ).strip()

    print(
        ""
    )

    if choice == "1":

        run_component_test()

    elif choice == "2":

        run_decision_compatibility_test()

    elif choice == "3":

        run_component_test()

        print(
            ""
        )

        run_decision_compatibility_test()

    else:

        print(
            "输入无效，请输入 1、2 或 3。"
        )


# ============================================================
# Entry Point
# ============================================================

if __name__ == "__main__":
    main()