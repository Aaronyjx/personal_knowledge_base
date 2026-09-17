# -*- coding: utf-8 -*-

"""
RAG V6.0-27
Legal Decision Engine Test

============================================================
功能
============================================================

本模块从 legal_decision_engine.py 中独立拆分测试与 CLI 代码。

包含：

    1. assert_condition_status
    2. run_component_test
    3. run_additional_tests
    4. run_manual_scenario_tests
    5. run_regression_tests
    6. main

============================================================
重要说明
============================================================

本模块只负责：

    - Decision Engine 测试
    - 回归测试
    - Manual Scenario 测试
    - CLI 入口

核心法律判定逻辑仍然位于：

    src/legal_decision_engine.py

本次拆分不修改任何法律判定规则，
不修改 ConditionResult，
不修改 DecisionResult，
不修改 make_decision，
不修改 UNKNOWN / SATISFIED / NOT_SATISFIED
的判定语义。

============================================================
"""

from src.legal_decision_engine import (
    ConditionResult,
    ContractSequence,
    DecisionResult,

    SATISFIED,
    NOT_SATISFIED,
    UNKNOWN,
    CONDITIONAL,
    NOT_ESTABLISHED,
    DEFINITE,

    normalize_text,
    contains_any,
    unique_texts,
    has_completed_renewal,

    extract_explicit_facts,
    extract_contract_sequence,

    build_core_rule,
    build_rule_dependency,
    match_condition,
    validate_condition_structure,
    evaluate_rule,

    select_core_rule,
    build_decision_explanation,

    make_decision,
    validate_decision_result,

    get_condition_results,
    get_required_results,
    get_exclusion_results,
    get_exception_results,

    print_decision_result,
)


ENGINE_VERSION = "V6.0-14"


def assert_condition_status(
    decision: DecisionResult,
    condition: str,
    expected_status: str,
) -> None:
    """
    检查指定法律条件的状态。
    """

    result = next(
        (
            item
            for item in decision.condition_results
            if item.condition == condition
        ),
        None,
    )

    assert result is not None, (
        f"未找到条件：{condition}"
    )

    assert result.status == expected_status, (
        f"条件：{condition}\n"
        f"期望：{expected_status}\n"
        f"实际：{result.status}\n"
        f"原因：{result.reason}"
    )


# ============================================================
# Component Test
# ============================================================

def run_component_test() -> None:
    """
    V6.0-16 Component Test。

    验证核心问题：

        公司连续签订三次固定期限劳动合同后，
        是否必须签订无固定期限劳动合同？

    预期：

        Decision = CONDITIONAL

        REQUIRED = 4
        EXCLUSION = 3
        EXCEPTION = 1

        TOTAL = 8

        SATISFIED：

            连续订立二次固定期限劳动合同
            存在后续订立的劳动合同

        UNKNOWN：

            续订劳动合同
            劳动者提出或者同意续订、订立劳动合同
            第39条
            第40条第一项
            第40条第二项
            劳动者提出固定期限
    """

    print()
    print("=" * 70)

    print(
        f"Legal Decision Engine {ENGINE_VERSION}"
    )

    print("=" * 70)

    question = (
        "公司连续签订三次固定期限劳动合同后，"
        "是否必须签订无固定期限劳动合同？"
    )

    print()

    print(
        "Test Question:"
    )

    print(
        question
    )

    decision = make_decision(
        question
    )

    print_decision_result(
        decision
    )

    print()

    print(
        "Running assertions..."
    )

    # --------------------------------------------------------
    # Decision
    # --------------------------------------------------------

    assert decision.decision == CONDITIONAL

    # --------------------------------------------------------
    # Explicit Fact
    # --------------------------------------------------------

    assert (
        "公司连续签订三次固定期限劳动合同"
        in decision.explicit_facts
    )

    # --------------------------------------------------------
    # Contract Sequence
    # --------------------------------------------------------

    assert decision.contract_sequence is not None

    assert (
        decision.contract_sequence.count
        == 3
    )

    assert (
        decision.contract_sequence.term_type
        == "fixed"
    )

    assert (
        decision.contract_sequence.continuous
        is True
    )

    # --------------------------------------------------------
    # Condition Count
    # --------------------------------------------------------

    assert (
        len(decision.condition_results)
        == 8
    )

    assert (
        len(get_required_results(decision))
        == 4
    )

    assert (
        len(get_exclusion_results(decision))
        == 3
    )

    assert (
        len(get_exception_results(decision))
        == 1
    )

    # --------------------------------------------------------
    # Required 1
    # --------------------------------------------------------

    assert_condition_status(
        decision,
        "连续订立二次固定期限劳动合同",
        SATISFIED,
    )

    # --------------------------------------------------------
    # Required 2
    # --------------------------------------------------------

    assert_condition_status(
        decision,
        "存在后续订立的劳动合同",
        SATISFIED,
    )

    # --------------------------------------------------------
    # Required 3
    # --------------------------------------------------------

    assert_condition_status(
        decision,
        "续订劳动合同",
        UNKNOWN,
    )

    # --------------------------------------------------------
    # Required 4
    # --------------------------------------------------------

    assert_condition_status(
        decision,
        "劳动者提出或者同意续订、订立劳动合同",
        UNKNOWN,
    )

    # --------------------------------------------------------
    # Exclusion
    # --------------------------------------------------------

    assert_condition_status(
        decision,
        "劳动者存在《劳动合同法》第三十九条规定的情形",
        UNKNOWN,
    )

    assert_condition_status(
        decision,
        "劳动者存在《劳动合同法》第四十条第一项规定的情形",
        UNKNOWN,
    )

    assert_condition_status(
        decision,
        "劳动者存在《劳动合同法》第四十条第二项规定的情形",
        UNKNOWN,
    )

    # --------------------------------------------------------
    # Exception
    # --------------------------------------------------------

    assert_condition_status(
        decision,
        "劳动者提出订立固定期限劳动合同",
        UNKNOWN,
    )

    # --------------------------------------------------------
    # Satisfied Set
    # --------------------------------------------------------

    assert set(
        decision.satisfied_conditions
    ) == {
        "连续订立二次固定期限劳动合同",
        "存在后续订立的劳动合同",
    }

    # --------------------------------------------------------
    # Unknown Set
    # --------------------------------------------------------

    assert set(
        decision.unknown_conditions
    ) == {
        "续订劳动合同",
        "劳动者提出或者同意续订、订立劳动合同",
        "劳动者存在《劳动合同法》第三十九条规定的情形",
        "劳动者存在《劳动合同法》第四十条第一项规定的情形",
        "劳动者存在《劳动合同法》第四十条第二项规定的情形",
        "劳动者提出订立固定期限劳动合同",
    }

    assert (
        len(decision.not_satisfied_conditions)
        == 0
    )

    assert (
        len(
            decision.required_not_satisfied_conditions
        )
        == 0
    )

    assert (
        len(
            decision.triggered_exclusion_conditions
        )
        == 0
    )

    assert (
        len(
            decision.triggered_exception_conditions
        )
        == 0
    )

    validate_decision_result(
        decision
    )

    print()

    print(
        "All Component Test assertions passed."
    )

    print()

    print(
        "============================================================"
    )

    print(
        "V6.0-16 Component Test PASSED"
    )

    print(
        "============================================================"
    )


# ============================================================
# Additional Tests
# ============================================================

def run_additional_tests() -> None:
    """
    V6.0-16 额外测试。

    重点验证：

        1. 三次合同
        2. 明确续订 + 明确同意
        3. 明确第39条排除
        4. 明确“不存在第39条”
        5. 明确“不存在第40条第一项”
        6. 明确“不存在第40条第二项”
        7. 明确“没有提出固定期限”
        8. 准备续订不能等同于已经续订
        9. 同意续订不能自动等于已经完成续订
        10. 第39条 + 第40条第一、二项组合否定
    """

    print()
    print("=" * 70)

    print(
        "Additional Tests"
    )

    print("=" * 70)

    # ========================================================
    # Test 1
    # 三次固定期限
    # ========================================================

    question_1 = (
        "公司连续签订三次固定期限劳动合同后，"
        "是否必须签订无固定期限劳动合同？"
    )

    result_1 = make_decision(
        question_1
    )

    assert result_1.decision == CONDITIONAL

    assert (
        len(result_1.condition_results)
        == 8
    )

    # ========================================================
    # Test 2
    # 明确续订 + 劳动者同意
    # ========================================================

    question_2 = (
        "公司连续签订两次固定期限劳动合同，"
        "之后续订劳动合同，劳动者同意续订，"
        "劳动者没有提出订立固定期限劳动合同。"
    )

    result_2 = make_decision(
        question_2
    )

    assert_condition_status(
        result_2,
        "连续订立二次固定期限劳动合同",
        SATISFIED,
    )

    assert_condition_status(
        result_2,
        "存在后续订立的劳动合同",
        SATISFIED,
    )

    assert_condition_status(
        result_2,
        "续订劳动合同",
        SATISFIED,
    )

    assert_condition_status(
        result_2,
        "劳动者提出或者同意续订、订立劳动合同",
        SATISFIED,
    )

    # --------------------------------------------------------
    # 明确没有提出固定期限
    # --------------------------------------------------------

    assert_condition_status(
        result_2,
        "劳动者提出订立固定期限劳动合同",
        SATISFIED,
    )

    # ========================================================
    # Test 3
    # 明确存在第39条
    # ========================================================

    question_3 = (
        "公司连续签订三次固定期限劳动合同，"
        "劳动者存在劳动合同法第三十九条规定的情形，"
        "是否必须签订无固定期限劳动合同？"
    )

    result_3 = make_decision(
        question_3
    )

    assert_condition_status(
        result_3,
        "劳动者存在《劳动合同法》第三十九条规定的情形",
        NOT_SATISFIED,
    )

    assert (
        result_3.decision
        == NOT_ESTABLISHED
    )

    assert (
        "劳动者存在《劳动合同法》第三十九条规定的情形"
        in result_3.triggered_exclusion_conditions
    )

    # ========================================================
    # Test 4
    # 明确不存在第39条
    # ========================================================

    question_4 = (
        "公司连续签订三次固定期限劳动合同，"
        "劳动者不存在劳动合同法第三十九条规定的情形。"
    )

    result_4 = make_decision(
        question_4
    )

    assert_condition_status(
        result_4,
        "劳动者存在《劳动合同法》第三十九条规定的情形",
        SATISFIED,
    )

    # ========================================================
    # Test 5
    # 明确不存在第40条第一项
    # ========================================================

    question_5 = (
        "公司连续签订三次固定期限劳动合同，"
        "劳动者不存在劳动合同法第四十条第一项规定的情形。"
    )

    result_5 = make_decision(
        question_5
    )

    assert_condition_status(
        result_5,
        "劳动者存在《劳动合同法》第四十条第一项规定的情形",
        SATISFIED,
    )

    # ========================================================
    # Test 6
    # 明确不存在第40条第二项
    # ========================================================

    question_6 = (
        "公司连续签订三次固定期限劳动合同，"
        "劳动者不存在劳动合同法第四十条第二项规定的情形。"
    )

    result_6 = make_decision(
        question_6
    )

    assert_condition_status(
        result_6,
        "劳动者存在《劳动合同法》第四十条第二项规定的情形",
        SATISFIED,
    )

    # ========================================================
    # Test 7
    # 明确没有提出固定期限
    # ========================================================

    question_7 = (
        "公司连续签订三次固定期限劳动合同，"
        "劳动者没有提出订立固定期限劳动合同。"
    )

    result_7 = make_decision(
        question_7
    )

    assert_condition_status(
        result_7,
        "劳动者提出订立固定期限劳动合同",
        SATISFIED,
    )

    # ========================================================
    # Test 8
    # 准备续订不能证明已经续订
    # ========================================================

    question_8 = (
        "公司连续签订两次固定期限劳动合同，"
        "公司准备与劳动者续订劳动合同。"
    )

    result_8 = make_decision(
        question_8
    )

    assert_condition_status(
        result_8,
        "续订劳动合同",
        UNKNOWN,
    )

    assert_condition_status(
        result_8,
        "存在后续订立的劳动合同",
        UNKNOWN,
    )

    # ========================================================
    # Test 9
    # 同意续订不能自动证明已经完成续订
    # ========================================================

    question_9 = (
        "公司连续签订两次固定期限劳动合同，"
        "劳动者同意续订劳动合同。"
    )

    result_9 = make_decision(
        question_9
    )

    assert_condition_status(
        result_9,
        "劳动者提出或者同意续订、订立劳动合同",
        SATISFIED,
    )

    assert_condition_status(
        result_9,
        "续订劳动合同",
        UNKNOWN,
    )

    assert_condition_status(
        result_9,
        "存在后续订立的劳动合同",
        UNKNOWN,
    )

    # ========================================================
    # Test 10
    # 已经续订 + 同意续订
    # ========================================================

    question_10 = (
        "公司连续签订两次固定期限劳动合同，"
        "之后已经续订劳动合同，"
        "劳动者也同意续订，"
        "劳动者没有提出订立固定期限劳动合同。"
    )

    result_10 = make_decision(
        question_10
    )

    assert_condition_status(
        result_10,
        "存在后续订立的劳动合同",
        SATISFIED,
    )

    assert_condition_status(
        result_10,
        "续订劳动合同",
        SATISFIED,
    )

    assert_condition_status(
        result_10,
        "劳动者提出或者同意续订、订立劳动合同",
        SATISFIED,
    )

    assert_condition_status(
        result_10,
        "劳动者提出订立固定期限劳动合同",
        SATISFIED,
    )

    # ========================================================
    # Test 11
    # 完整正向场景
    #
    # 这是 V6.0-16 最重要的新增回归测试。
    #
    # 用户明确给出：
    #
    #   1. 连续签订两次固定期限劳动合同
    #   2. 后来又续签劳动合同
    #   3. 劳动者也同意续订
    #   4. 不存在第39条情形
    #   5. 不存在第40条第一项情形
    #   6. 不存在第40条第二项情形
    #   7. 没有提出订立固定期限劳动合同
    #
    # 预期：
    #
    #   8 / 8 = SATISFIED
    #   UNKNOWN = 0
    #   NOT_SATISFIED = 0
    #   Decision = DEFINITE
    # ========================================================

    question_11 = (
        "公司连续签订两次固定期限劳动合同，"
        "后来又续签了劳动合同，"
        "劳动者也同意续订，"
        "且不存在劳动合同法第三十九条和"
        "第四十条第一项、第二项规定的情形，"
        "劳动者也没有提出订立固定期限劳动合同，"
        "是否必须签订无固定期限劳动合同？"
    )

    result_11 = make_decision(
        question_11
    )

    # --------------------------------------------------------
    # Decision
    # --------------------------------------------------------

    assert (
        result_11.decision
        == DEFINITE
    )

    # --------------------------------------------------------
    # Condition Count
    # --------------------------------------------------------

    assert (
        len(result_11.condition_results)
        == 8
    )

    # --------------------------------------------------------
    # REQUIRED 1
    # --------------------------------------------------------

    assert_condition_status(
        result_11,
        "连续订立二次固定期限劳动合同",
        SATISFIED,
    )

    # --------------------------------------------------------
    # REQUIRED 2
    # --------------------------------------------------------

    assert_condition_status(
        result_11,
        "存在后续订立的劳动合同",
        SATISFIED,
    )

    # --------------------------------------------------------
    # REQUIRED 3
    # --------------------------------------------------------

    assert_condition_status(
        result_11,
        "续订劳动合同",
        SATISFIED,
    )

    # --------------------------------------------------------
    # REQUIRED 4
    # --------------------------------------------------------

    assert_condition_status(
        result_11,
        "劳动者提出或者同意续订、订立劳动合同",
        SATISFIED,
    )

    # --------------------------------------------------------
    # EXCLUSION 1
    # --------------------------------------------------------

    assert_condition_status(
        result_11,
        "劳动者存在《劳动合同法》第三十九条规定的情形",
        SATISFIED,
    )

    # --------------------------------------------------------
    # EXCLUSION 2
    # --------------------------------------------------------

    assert_condition_status(
        result_11,
        "劳动者存在《劳动合同法》第四十条第一项规定的情形",
        SATISFIED,
    )

    # --------------------------------------------------------
    # EXCLUSION 3
    # --------------------------------------------------------

    assert_condition_status(
        result_11,
        "劳动者存在《劳动合同法》第四十条第二项规定的情形",
        SATISFIED,
    )

    # --------------------------------------------------------
    # EXCEPTION
    # --------------------------------------------------------

    assert_condition_status(
        result_11,
        "劳动者提出订立固定期限劳动合同",
        SATISFIED,
    )

    # --------------------------------------------------------
    # Satisfied Count
    # --------------------------------------------------------

    assert (
        len(
            result_11.satisfied_conditions
        )
        == 8
    )

    # --------------------------------------------------------
    # Unknown Count
    # --------------------------------------------------------

    assert (
        len(
            result_11.unknown_conditions
        )
        == 0
    )

    # --------------------------------------------------------
    # Not Satisfied Count
    # --------------------------------------------------------

    assert (
        len(
            result_11.not_satisfied_conditions
        )
        == 0
    )

    # --------------------------------------------------------
    # Required Not Satisfied
    # --------------------------------------------------------

    assert (
        len(
            result_11.required_not_satisfied_conditions
        )
        == 0
    )

    # --------------------------------------------------------
    # Triggered Exclusions
    # --------------------------------------------------------

    assert (
        len(
            result_11.triggered_exclusion_conditions
        )
        == 0
    )

    # --------------------------------------------------------
    # Triggered Exceptions
    # --------------------------------------------------------

    assert (
        len(
            result_11.triggered_exception_conditions
        )
        == 0
    )

    # --------------------------------------------------------
    # Explicit Facts
    # --------------------------------------------------------

    assert (
        "连续订立二次固定期限劳动合同"
        in result_11.explicit_facts
    )

    assert (
        "存在明确续订劳动合同事实"
        in result_11.explicit_facts
    )

    assert (
        "劳动者明确提出或者同意续订、订立劳动合同"
        in result_11.explicit_facts
    )

    assert (
        "劳动者不存在《劳动合同法》第三十九条规定的情形"
        in result_11.explicit_facts
    )

    assert (
        "劳动者不存在《劳动合同法》第四十条第一项规定的情形"
        in result_11.explicit_facts
    )

    assert (
        "劳动者不存在《劳动合同法》第四十条第二项规定的情形"
        in result_11.explicit_facts
    )

    # --------------------------------------------------------
    # Validation
    # --------------------------------------------------------

    validate_decision_result(
        result_11
    )

    # ========================================================
    # Print
    # ========================================================

    print()

    print(
        "Additional tests passed."
    )

    print()

    print(
        "V6.0-16 negative-fact tests PASSED."
    )

    print()

    print(
        "V6.0-16 complete positive scenario PASSED."
    )


# ============================================================
# Manual Scenario Test
# ============================================================

def run_manual_scenario_tests() -> None:
    """
    输出关键场景的完整 DecisionResult。

    该测试主要用于人工观察，
    不作为 RAG Pipeline 的正式输入。

    V6.0-16 边界回归测试：

    A. 三次固定期限合同
    B. 已经续订 + 劳动者同意
    C. 准备续订
    D. 存在第39条情形

    E. 两次合同 + 后来已经续签
    F. 两次合同 + 准备续签
    G. 两次合同 + 计划续签
    H. 两次合同 + 劳动者同意续订
    I. 已经续订 + 劳动者没有同意
    J. 已经续订 + 劳动者同意 + 提出订立固定期限合同
    K. 完整正向场景

    这些场景用于验证：

    - 已经完成的续订与准备续订不能混淆
    - 后续合同与续订事实之间的逻辑关系
    - 劳动者同意不能被自动推定
    - EXCEPTION 条件能够正确识别
    - 组合否定能够同时识别三个 EXCLUSION
    """

    scenarios = [

        # ====================================================
        # 场景 A
        # ====================================================

        (
            "场景 A：三次固定期限合同",
            (
                "公司连续签订三次固定期限劳动合同后，"
                "是否必须签订无固定期限劳动合同？"
            ),
        ),

        # ====================================================
        # 场景 B
        # ====================================================

        (
            "场景 B：已经续订且劳动者同意",
            (
                "公司连续签订两次固定期限劳动合同，"
                "之后已经续订劳动合同，"
                "劳动者同意续订，"
                "劳动者没有提出订立固定期限劳动合同。"
            ),
        ),

        # ====================================================
        # 场景 C
        # ====================================================

        (
            "场景 C：准备续订",
            (
                "公司连续签订两次固定期限劳动合同，"
                "公司准备与劳动者续订劳动合同。"
            ),
        ),

        # ====================================================
        # 场景 D
        # ====================================================

        (
            "场景 D：存在第39条",
            (
                "公司连续签订三次固定期限劳动合同，"
                "劳动者存在劳动合同法第三十九条规定的情形。"
            ),
        ),

        # ====================================================
        # 场景 E
        # 两次合同 + 后来已经续签
        # ====================================================

        (
            "场景 E：后来已经续签",
            (
                "公司连续签订两次固定期限劳动合同，"
                "后来已经续签劳动合同。"
            ),
        ),

        # ====================================================
        # 场景 F
        # 两次合同 + 准备续签
        # ====================================================

        (
            "场景 F：准备续签",
            (
                "公司连续签订两次固定期限劳动合同，"
                "准备续签劳动合同。"
            ),
        ),

        # ====================================================
        # 场景 G
        # 两次合同 + 计划续签
        # ====================================================

        (
            "场景 G：计划续签",
            (
                "公司连续签订两次固定期限劳动合同，"
                "计划续签劳动合同。"
            ),
        ),

        # ====================================================
        # 场景 H
        # 两次合同 + 劳动者同意续订
        # ====================================================

        (
            "场景 H：劳动者同意续订",
            (
                "公司连续签订两次固定期限劳动合同，"
                "劳动者同意续订劳动合同。"
            ),
        ),

        # ====================================================
        # 场景 I
        # 已经续订 + 劳动者没有同意
        # ====================================================

        (
            "场景 I：已经续订，但劳动者没有同意",
            (
                "公司连续签订两次固定期限劳动合同，"
                "已经续订劳动合同，"
                "但劳动者没有同意续订。"
            ),
        ),

        # ====================================================
        # 场景 J
        # 已经续订 + 劳动者同意 + 提出固定期限
        # ====================================================

        (
            "场景 J：例外条件被触发",
            (
                "公司连续签订两次固定期限劳动合同，"
                "之后已经续订劳动合同，"
                "劳动者同意续订，"
                "并且劳动者提出订立固定期限劳动合同。"
            ),
        ),

        # ====================================================
        # 场景 K
        # 完整正向场景
        # ====================================================

        (
            "场景 K：完整正向场景",
            (
                "公司连续签订两次固定期限劳动合同，"
                "后来又续签了劳动合同，"
                "劳动者也同意续订，"
                "且不存在劳动合同法第三十九条和"
                "第四十条第一项、第二项规定的情形，"
                "劳动者也没有提出订立固定期限劳动合同，"
                "是否必须签订无固定期限劳动合同？"
            ),
        ),
    ]

    # ========================================================
    # 逐个执行场景
    # ========================================================

    for title, question in scenarios:

        print()
        print("=" * 70)

        print(
            title
        )

        print("=" * 70)

        print()

        print(
            f"问题：{question}"
        )

        decision = make_decision(
            question
        )

        print_decision_result(
            decision
        )


# ============================================================
# Regression Test
# ============================================================

def run_regression_tests() -> None:
    """
    V6.0-16 回归测试。

    将 A-K 场景从：

        人工观察

    提升为：

        自动断言。

    目标：

        每次修改 Decision Engine 后，
        可以快速确认核心逻辑没有回归。

    V6.0-16 新增：

        Scenario K

        完整正向场景：

            公司连续签订两次固定期限劳动合同，
            后来又续签了劳动合同，
            劳动者也同意续订，
            且不存在劳动合同法第三十九条和
            第四十条第一项、第二项规定的情形，
            劳动者也没有提出订立固定期限劳动合同。

        预期：

            Decision = DEFINITE

            8 个条件全部 SATISFIED
    """

    print()
    print("=" * 70)

    print(
        "V6.0-16 Regression Tests"
    )

    print("=" * 70)

    scenarios = [

        {
            "name": "A",
            "question": (
                "公司连续签订三次固定期限劳动合同后，"
                "是否必须签订无固定期限劳动合同？"
            ),
            "decision": CONDITIONAL,
            "statuses": {
                "连续订立二次固定期限劳动合同":
                    SATISFIED,

                "存在后续订立的劳动合同":
                    SATISFIED,

                "续订劳动合同":
                    UNKNOWN,

                "劳动者提出或者同意续订、订立劳动合同":
                    UNKNOWN,

                "劳动者存在《劳动合同法》第三十九条规定的情形":
                    UNKNOWN,

                "劳动者存在《劳动合同法》第四十条第一项规定的情形":
                    UNKNOWN,

                "劳动者存在《劳动合同法》第四十条第二项规定的情形":
                    UNKNOWN,

                "劳动者提出订立固定期限劳动合同":
                    UNKNOWN,
            },
        },

        {
            "name": "B",
            "question": (
                "公司连续签订两次固定期限劳动合同，"
                "之后已经续订劳动合同，"
                "劳动者同意续订，"
                "劳动者没有提出订立固定期限劳动合同。"
            ),
            "decision": CONDITIONAL,
            "statuses": {
                "连续订立二次固定期限劳动合同":
                    SATISFIED,

                "存在后续订立的劳动合同":
                    SATISFIED,

                "续订劳动合同":
                    SATISFIED,

                "劳动者提出或者同意续订、订立劳动合同":
                    SATISFIED,

                "劳动者提出订立固定期限劳动合同":
                    SATISFIED,
            },
        },

        {
            "name": "C",
            "question": (
                "公司连续签订两次固定期限劳动合同，"
                "公司准备与劳动者续订劳动合同。"
            ),
            "decision": CONDITIONAL,
            "statuses": {
                "连续订立二次固定期限劳动合同":
                    SATISFIED,

                "存在后续订立的劳动合同":
                    UNKNOWN,

                "续订劳动合同":
                    UNKNOWN,

                "劳动者提出或者同意续订、订立劳动合同":
                    UNKNOWN,
            },
        },

        {
            "name": "D",
            "question": (
                "公司连续签订三次固定期限劳动合同，"
                "劳动者存在劳动合同法第三十九条规定的情形。"
            ),
            "decision": NOT_ESTABLISHED,
            "statuses": {
                "连续订立二次固定期限劳动合同":
                    SATISFIED,

                "存在后续订立的劳动合同":
                    SATISFIED,

                "劳动者存在《劳动合同法》第三十九条规定的情形":
                    NOT_SATISFIED,
            },
        },

        {
            "name": "E",
            "question": (
                "公司连续签订两次固定期限劳动合同，"
                "后来已经续签劳动合同。"
            ),
            "decision": CONDITIONAL,
            "statuses": {
                "连续订立二次固定期限劳动合同":
                    SATISFIED,

                "存在后续订立的劳动合同":
                    SATISFIED,

                "续订劳动合同":
                    SATISFIED,

                "劳动者提出或者同意续订、订立劳动合同":
                    UNKNOWN,
            },
        },

        {
            "name": "F",
            "question": (
                "公司连续签订两次固定期限劳动合同，"
                "准备续签劳动合同。"
            ),
            "decision": CONDITIONAL,
            "statuses": {
                "连续订立二次固定期限劳动合同":
                    SATISFIED,

                "存在后续订立的劳动合同":
                    UNKNOWN,

                "续订劳动合同":
                    UNKNOWN,
            },
        },

        {
            "name": "G",
            "question": (
                "公司连续签订两次固定期限劳动合同，"
                "计划续签劳动合同。"
            ),
            "decision": CONDITIONAL,
            "statuses": {
                "连续订立二次固定期限劳动合同":
                    SATISFIED,

                "存在后续订立的劳动合同":
                    UNKNOWN,

                "续订劳动合同":
                    UNKNOWN,
            },
        },

        {
            "name": "H",
            "question": (
                "公司连续签订两次固定期限劳动合同，"
                "劳动者同意续订劳动合同。"
            ),
            "decision": CONDITIONAL,
            "statuses": {
                "连续订立二次固定期限劳动合同":
                    SATISFIED,

                "存在后续订立的劳动合同":
                    UNKNOWN,

                "续订劳动合同":
                    UNKNOWN,

                "劳动者提出或者同意续订、订立劳动合同":
                    SATISFIED,
            },
        },

        {
            "name": "I",
            "question": (
                "公司连续签订两次固定期限劳动合同，"
                "已经续订劳动合同，"
                "但劳动者没有同意续订。"
            ),
            "decision": CONDITIONAL,
            "statuses": {
                "连续订立二次固定期限劳动合同":
                    SATISFIED,

                "存在后续订立的劳动合同":
                    SATISFIED,

                "续订劳动合同":
                    SATISFIED,

                "劳动者提出或者同意续订、订立劳动合同":
                    UNKNOWN,
            },
        },

        {
            "name": "J",
            "question": (
                "公司连续签订两次固定期限劳动合同，"
                "之后已经续订劳动合同，"
                "劳动者同意续订，"
                "并且劳动者提出订立固定期限劳动合同。"
            ),
            "decision": NOT_ESTABLISHED,
            "statuses": {
                "连续订立二次固定期限劳动合同":
                    SATISFIED,

                "存在后续订立的劳动合同":
                    SATISFIED,

                "续订劳动合同":
                    SATISFIED,

                "劳动者提出或者同意续订、订立劳动合同":
                    SATISFIED,

                "劳动者提出订立固定期限劳动合同":
                    NOT_SATISFIED,
            },
        },

        # ====================================================
        # Scenario K
        # 完整正向场景
        # ====================================================

        {
            "name": "K",
            "question": (
                "公司连续签订两次固定期限劳动合同，"
                "后来又续签了劳动合同，"
                "劳动者也同意续订，"
                "且不存在劳动合同法第三十九条和"
                "第四十条第一项、第二项规定的情形，"
                "劳动者也没有提出订立固定期限劳动合同，"
                "是否必须签订无固定期限劳动合同？"
            ),
            "decision": DEFINITE,
            "statuses": {
                "连续订立二次固定期限劳动合同":
                    SATISFIED,

                "存在后续订立的劳动合同":
                    SATISFIED,

                "续订劳动合同":
                    SATISFIED,

                "劳动者提出或者同意续订、订立劳动合同":
                    SATISFIED,

                "劳动者存在《劳动合同法》第三十九条规定的情形":
                    SATISFIED,

                "劳动者存在《劳动合同法》第四十条第一项规定的情形":
                    SATISFIED,

                "劳动者存在《劳动合同法》第四十条第二项规定的情形":
                    SATISFIED,

                "劳动者提出订立固定期限劳动合同":
                    SATISFIED,
            },
        },
    ]

    passed = 0

    failed = 0

    for scenario in scenarios:

        name = scenario["name"]

        question = scenario["question"]

        expected_decision = scenario["decision"]

        expected_statuses = scenario["statuses"]

        print()

        print(
            f"[Scenario {name}]"
        )

        try:

            decision = make_decision(
                question
            )

            assert (
                decision.decision
                == expected_decision
            ), (
                f"Decision 期望 "
                f"{expected_decision}，"
                f"实际 "
                f"{decision.decision}"
            )

            for (
                condition,
                expected_status,
            ) in expected_statuses.items():

                assert_condition_status(
                    decision,
                    condition,
                    expected_status,
                )

            # ------------------------------------------------
            # Scenario K 强制检查：
            # 必须是完整 8 条 SATISFIED。
            # ------------------------------------------------

            if name == "K":

                assert (
                    len(
                        decision.condition_results
                    )
                    == 8
                ), (
                    "Scenario K 必须包含 8 个条件。"
                )

                assert (
                    len(
                        decision.satisfied_conditions
                    )
                    == 8
                ), (
                    "Scenario K 必须全部 SATISFIED。"
                )

                assert (
                    len(
                        decision.unknown_conditions
                    )
                    == 0
                ), (
                    "Scenario K 不允许存在 UNKNOWN。"
                )

                assert (
                    len(
                        decision.not_satisfied_conditions
                    )
                    == 0
                ), (
                    "Scenario K 不允许存在 NOT_SATISFIED。"
                )

                assert (
                    decision.decision
                    == DEFINITE
                ), (
                    "Scenario K 必须输出 DEFINITE。"
                )

                # --------------------------------------------
                # 组合否定必须产生三个明确事实。
                # --------------------------------------------

                assert (
                    "劳动者不存在《劳动合同法》第三十九条规定的情形"
                    in decision.explicit_facts
                )

                assert (
                    "劳动者不存在《劳动合同法》第四十条第一项规定的情形"
                    in decision.explicit_facts
                )

                assert (
                    "劳动者不存在《劳动合同法》第四十条第二项规定的情形"
                    in decision.explicit_facts
                )

            # ------------------------------------------------
            # 分类结果一致性检查
            # ------------------------------------------------

            if expected_decision == NOT_ESTABLISHED:

                assert (
                    len(
                        decision.not_satisfied_conditions
                    )
                    > 0
                )

            print(
                f"  Scenario {name}: PASS"
            )

            passed += 1

        except AssertionError as exc:

            print(
                f"  Scenario {name}: FAIL"
            )

            print(
                f"  Reason: {exc}"
            )

            failed += 1

    print()
    print("=" * 70)

    print(
        "Regression Test Result"
    )

    print("=" * 70)

    print()

    print(
        f"PASS: {passed}"
    )

    print(
        f"FAIL: {failed}"
    )

    print()

    if failed == 0:

        print(
            "ALL REGRESSION TESTS PASSED"
        )

    else:

        raise AssertionError(
            f"Regression Tests failed: "
            f"{failed}"
        )


# ============================================================
# Module Entry
# ============================================================

def main() -> None:
    """
    模块入口。
    """

    print()
    print("=" * 70)

    print(
        f"Legal Decision Engine {ENGINE_VERSION}"
    )

    print("=" * 70)

    print()

    print(
        "请选择测试："
    )

    print()

    print(
        "1. Component Test"
    )

    print(
        "2. Additional Tests"
    )

    print(
        "3. 全部测试"
    )

    print(
        "4. Manual Scenario Tests"
    )

    print(
        "5. Regression Tests"
    )

    print()

    try:

        choice = input(
            "请输入 1、2、3、4 或 5："
        ).strip()

    except EOFError:

        choice = "1"

    if choice == "1":

        run_component_test()

    elif choice == "2":

        run_additional_tests()

    elif choice == "3":

        run_component_test()

        run_additional_tests()

    elif choice == "4":

        run_manual_scenario_tests()

    elif choice == "5":

        run_regression_tests()

    else:

        print(
            "输入无效，默认运行 Component Test。"
        )

        run_component_test()


# ============================================================
# Execute
# ============================================================

if __name__ == "__main__":

    main()