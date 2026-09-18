# -*- coding: utf-8 -*-

"""
RAG V6.0-27
Condition Status Fidelity Regression Test

============================================================
测试目标
============================================================

验证：

    Legal Decision Engine
            ↓
        ConditionResult
            ↓
    UNKNOWN 状态
            ↓
    最终答案

必须保持状态一致。

禁止：

    UNKNOWN → SATISFIED

    UNKNOWN → NOT_SATISFIED

允许：

    UNKNOWN → UNKNOWN

============================================================
测试场景
============================================================

问题：

    公司连续签订三次固定期限劳动合同后，
    是否必须签订无固定期限劳动合同？

当前 Engine 预期：

    Decision = CONDITIONAL

    ConditionResult = 8

    REQUIRED：

        连续订立二次固定期限劳动合同
            = SATISFIED

        存在后续订立的劳动合同
            = SATISFIED

        续订劳动合同
            = UNKNOWN

        劳动者提出或者同意续订、订立劳动合同
            = UNKNOWN

    EXCLUSION：

        第三十九条
            = UNKNOWN

        第四十条第一项
            = UNKNOWN

        第四十条第二项
            = UNKNOWN

    EXCEPTION：

        劳动者提出订立固定期限劳动合同
            = UNKNOWN

============================================================
测试内容
============================================================

第一组：

    故意将：

        续订劳动合同
            UNKNOWN → SATISFIED

    必须被拦截。

第二组：

    故意将：

        续订劳动合同
            UNKNOWN → NOT_SATISFIED

    必须被拦截。

第三组：

    保持：

        UNKNOWN → UNKNOWN

    必须通过。

============================================================
重要原则
============================================================

本测试只测试 Validator。

不修改：

    Legal Decision Engine
    Answer Builder
    Pipeline
    Ollama
    Deterministic Lock
"""

from src.legal_pipeline import (
    build_structured_context,
    run_decision_engine,
    run_answer_builder,
)

from src.legal_validator import (
    final_validation,
)

from src.legal_condition_validator import (
    validate_unknown_conditions,
)

from src.legal_common import (
    get_field,
)


# ============================================================
# Test Question
# ============================================================

QUESTION = (
    "公司连续签订三次固定期限劳动合同后，"
    "是否必须签订无固定期限劳动合同？"
)


# ============================================================
# Compatibility Helper
# ============================================================

def read_field(
    obj,
    name,
    default=None,
):
    """
    同时兼容：

        dict

    以及：

        DecisionResult

        ConditionResult

    等对象。
    """

    return get_field(
        obj,
        name,
        default,
    )


# ============================================================
# Build Malicious Answer
# ============================================================

def build_malicious_answer(
    renewal_status: str,
    consent_status: str,
) -> str:
    """
    构造故意篡改 UNKNOWN 状态的答案。

    参数：

        renewal_status
            续订劳动合同状态

        consent_status
            劳动者提出或者同意续订、
            订立劳动合同状态

    例如：

        UNKNOWN → SATISFIED

    或：

        UNKNOWN → NOT_SATISFIED
    """

    return f"""【结论】
目前不能仅根据现有事实确定必须签订无固定期限劳动合同。

【法律依据】
《劳动合同法》第十四条规定了无固定期限劳动合同的相关条件。

【法律分析】
1. 用户事实：
- 公司连续签订三次固定期限劳动合同

2. 条件状态：
- 连续订立二次固定期限劳动合同：已满足
- 存在后续订立的劳动合同：已满足
- 续订劳动合同：{renewal_status}
- 劳动者提出或者同意续订、订立劳动合同：{consent_status}

【需要注意】
当前仍需结合具体事实判断是否满足全部法律条件。
"""


# ============================================================
# Engine Baseline Validation
# ============================================================

def assert_engine_baseline(
    decision,
):
    """
    验证真实 Engine 基线。

    必须确认：

        Decision = CONDITIONAL

        ConditionResult = 8

        两个 REQUIRED 条件 SATISFIED

        两个 REQUIRED 条件 UNKNOWN
    """

    print()
    print(
        "检查 Engine Decision..."
    )

    engine_decision = read_field(
        decision,
        "decision",
        "",
    )

    assert engine_decision == "CONDITIONAL", (
        "Engine Decision 异常："
        f"{engine_decision}"
    )

    print(
        "✅ Engine Decision = CONDITIONAL"
    )

    # ========================================================
    # Explicit Facts
    # ========================================================

    explicit_facts = read_field(
        decision,
        "explicit_facts",
        [],
    )

    assert (
        "公司连续签订三次固定期限劳动合同"
        in explicit_facts
    ), (
        "Engine 未保留三次固定期限劳动合同事实"
    )

    print(
        "✅ Engine Explicit Fact 保留正确"
    )

    # ========================================================
    # Condition Results
    # ========================================================

    condition_results = read_field(
        decision,
        "condition_results",
        [],
    )

    assert len(condition_results) == 8, (
        "ConditionResult 数量异常："
        f"{len(condition_results)}"
    )

    print(
        "✅ ConditionResult = 8"
    )

    # ========================================================
    # Build Status Map
    # ========================================================

    result_map = {}

    for result in condition_results:

        condition = read_field(
            result,
            "condition",
            "",
        )

        status = read_field(
            result,
            "status",
            "",
        )

        result_map[
            condition
        ] = status

    # ========================================================
    # SATISFIED
    # ========================================================

    assert (
        result_map.get(
            "连续订立二次固定期限劳动合同"
        )
        == "SATISFIED"
    ), (
        "“连续订立二次固定期限劳动合同”"
        "状态不是 SATISFIED"
    )

    assert (
        result_map.get(
            "存在后续订立的劳动合同"
        )
        == "SATISFIED"
    ), (
        "“存在后续订立的劳动合同”"
        "状态不是 SATISFIED"
    )

    print(
        "✅ 两个 REQUIRED 条件 = SATISFIED"
    )

    # ========================================================
    # UNKNOWN
    # ========================================================

    assert (
        result_map.get(
            "续订劳动合同"
        )
        == "UNKNOWN"
    ), (
        "Engine 的“续订劳动合同”"
        "状态不是 UNKNOWN"
    )

    assert (
        result_map.get(
            "劳动者提出或者同意续订、订立劳动合同"
        )
        == "UNKNOWN"
    ), (
        "Engine 的“劳动者提出或者同意续订、"
        "订立劳动合同”状态不是 UNKNOWN"
    )

    print(
        "✅ 两个 REQUIRED 条件 = UNKNOWN"
    )

    # ========================================================
    # Print Complete Status
    # ========================================================

    print()
    print(
        "Engine Condition Status："
    )

    for condition, status in result_map.items():

        print(
            f"  {status:15s} "
            f"{condition}"
        )


# ============================================================
# Fallback State Validation
# ============================================================

def assert_fallback_preserves_engine_state(
    answer: str,
):
    """
    验证 Final Validation / Fallback 后：

        1. 三次合同事实仍然存在。

        2. Engine 已满足条件仍然存在。

        3. Engine UNKNOWN 条件仍然存在。

        4. UNKNOWN 没有被改写为
           SATISFIED。

        5. UNKNOWN 没有被改写为
           NOT_SATISFIED。
    """

    assert answer, (
        "最终答案为空"
    )

    # ========================================================
    # User Fact
    # ========================================================

    assert (
        "公司连续签订三次固定期限劳动合同"
        in answer
    ), (
        "❌ Final Answer 丢失三次固定期限劳动合同事实"
    )

    # ========================================================
    # SATISFIED Conditions
    # ========================================================

    assert (
        "连续订立二次固定期限劳动合同"
        in answer
    ), (
        "❌ Final Answer 丢失 SATISFIED 条件"
    )

    assert (
        "存在后续订立的劳动合同"
        in answer
    ), (
        "❌ Final Answer 丢失 SATISFIED 条件"
    )

    # ========================================================
    # UNKNOWN Conditions
    # ========================================================

    assert (
        "续订劳动合同"
        in answer
    ), (
        "❌ Final Answer 丢失 UNKNOWN 条件"
    )

    assert (
        "劳动者提出或者同意续订、订立劳动合同"
        in answer
    ), (
        "❌ Final Answer 丢失 UNKNOWN 条件"
    )

    # ========================================================
    # Forbidden Status Rewrite
    # ========================================================

    forbidden_patterns = [
        "续订劳动合同：已满足",
        "续订劳动合同：不满足",
        "劳动者提出或者同意续订、订立劳动合同：已满足",
        "劳动者提出或者同意续订、订立劳动合同：不满足",
        "续订劳动合同：SATISFIED",
        "续订劳动合同：NOT_SATISFIED",
        "劳动者提出或者同意续订、订立劳动合同：SATISFIED",
        "劳动者提出或者同意续订、订立劳动合同：NOT_SATISFIED",
    ]

    for pattern in forbidden_patterns:

        assert pattern not in answer, (
            "❌ Final Answer 存在错误状态："
            f"{pattern}"
        )

    print(
        "✅ Final Answer 保留 Engine UNKNOWN 状态"
    )


# ============================================================
# Main Regression Test
# ============================================================

def main():

    print("=" * 70)
    print(
        "RAG V6.0-27 "
        "Condition Status Fidelity 回归测试"
    )
    print("=" * 70)

    print()
    print(
        "问题："
    )

    print(
        QUESTION
    )

    # ========================================================
    # [1/7]
    # Structured Context
    # ========================================================

    print()
    print(
        "[1/7] 构建真实 Structured Context"
    )

    context_data = build_structured_context(
        question=QUESTION,
        top_k=5,
        score_threshold=0.55,
    )

    assert context_data, (
        "Structured Context 为空"
    )

    rules = context_data.get(
        "rules",
        [],
    )

    assert rules, (
        "Structured Context 未返回 rules"
    )

    print()
    print(
        "Structured Rules：",
        len(rules),
    )

    print(
        "✅ Structured Context 构建完成"
    )

    # ========================================================
    # [2/7]
    # Real Decision Engine
    # ========================================================

    print()
    print(
        "[2/7] 运行真实 Legal Decision Engine"
    )

    decision = run_decision_engine(
        question=QUESTION,
        rules=rules,
    )

    assert decision is not None, (
        "Decision Engine 未返回结果"
    )

    assert_engine_baseline(
        decision
    )

    # ========================================================
    # [3/7]
    # Real Answer Builder
    # ========================================================

    print()
    print(
        "[3/7] 运行真实 Legal Answer Builder"
    )

    builder_result = run_answer_builder(
        decision=decision,
        rules=rules,
        question=QUESTION,
    )

    assert builder_result, (
        "Answer Builder 未返回结果"
    )

    builder_decision = read_field(
        builder_result,
        "decision",
        "",
    )

    assert builder_decision == "CONDITIONAL", (
        "Builder Decision 异常："
        f"{builder_decision}"
    )

    print(
        "Builder Decision：",
        builder_decision,
    )

    print(
        "✅ Answer Builder 基线确认"
    )

    # ========================================================
    # [4/7]
    # UNKNOWN → SATISFIED
    # ========================================================

    print()
    print(
        "[4/7] 第一组："
        "UNKNOWN → SATISFIED"
    )

    malicious_satisfied = (
        build_malicious_answer(
            renewal_status="已满足",
            consent_status="已满足",
        )
    )

    print()
    print(
        "恶意答案状态："
    )

    print(
        "  续订劳动合同：已满足"
    )

    print(
        "  劳动者提出或者同意续订、订立劳动合同：已满足"
    )

    # --------------------------------------------------------
    # Direct Validator
    # --------------------------------------------------------

    print()
    print(
        "运行 validate_unknown_conditions..."
    )

    validation_1 = (
        validate_unknown_conditions(
            malicious_satisfied,
            builder_result,
        )
    )

    print(
        "validate_unknown_conditions =",
        validation_1,
    )

    assert validation_1 is False, (
        "❌ Condition Status Fidelity "
        "没有拦截 UNKNOWN → SATISFIED"
    )

    print(
        "✅ UNKNOWN → SATISFIED 已被拦截"
    )

    # --------------------------------------------------------
    # Final Validation
    # --------------------------------------------------------

    print()
    print(
        "运行 final_validation..."
    )

    final_1 = final_validation(
        answer=malicious_satisfied,
        question=QUESTION,
        decision=builder_result,
    )

    assert final_1, (
        "final_validation 没有返回最终答案"
    )

    assert_fallback_preserves_engine_state(
        final_1
    )

    print(
        "✅ final_validation 拒绝恶意状态"
    )

    # ========================================================
    # [5/7]
    # UNKNOWN → NOT_SATISFIED
    # ========================================================

    print()
    print(
        "[5/7] 第二组："
        "UNKNOWN → NOT_SATISFIED"
    )

    malicious_not_satisfied = (
        build_malicious_answer(
            renewal_status="不满足",
            consent_status="不满足",
        )
    )

    print()
    print(
        "恶意答案状态："
    )

    print(
        "  续订劳动合同：不满足"
    )

    print(
        "  劳动者提出或者同意续订、订立劳动合同：不满足"
    )

    # --------------------------------------------------------
    # Direct Validator
    # --------------------------------------------------------

    print()
    print(
        "运行 validate_unknown_conditions..."
    )

    validation_2 = (
        validate_unknown_conditions(
            malicious_not_satisfied,
            builder_result,
        )
    )

    print(
        "validate_unknown_conditions =",
        validation_2,
    )

    assert validation_2 is False, (
        "❌ Condition Status Fidelity "
        "没有拦截 UNKNOWN → NOT_SATISFIED"
    )

    print(
        "✅ UNKNOWN → NOT_SATISFIED 已被拦截"
    )

    # --------------------------------------------------------
    # Final Validation
    # --------------------------------------------------------

    print()
    print(
        "运行 final_validation..."
    )

    final_2 = final_validation(
        answer=malicious_not_satisfied,
        question=QUESTION,
        decision=builder_result,
    )

    assert final_2, (
        "final_validation 没有返回最终答案"
    )

    assert_fallback_preserves_engine_state(
        final_2
    )

    print(
        "✅ final_validation 拒绝恶意状态"
    )

    # ========================================================
    # [6/7]
    # UNKNOWN → UNKNOWN
    # ========================================================

    print()
    print(
        "[6/7] 第三组："
        "UNKNOWN → UNKNOWN"
    )

    correct_answer = (
        build_malicious_answer(
            renewal_status="未知",
            consent_status="未知",
        )
    )

    print()
    print(
        "正确答案状态："
    )

    print(
        "  续订劳动合同：未知"
    )

    print(
        "  劳动者提出或者同意续订、订立劳动合同：未知"
    )

    # --------------------------------------------------------
    # Direct Validator
    # --------------------------------------------------------

    print()
    print(
        "运行 validate_unknown_conditions..."
    )

    validation_3 = (
        validate_unknown_conditions(
            correct_answer,
            builder_result,
        )
    )

    print(
        "validate_unknown_conditions =",
        validation_3,
    )

    assert validation_3 is True, (
        "❌ 正确的 UNKNOWN 状态被错误拒绝"
    )

    print(
        "✅ UNKNOWN → UNKNOWN 正常通过"
    )

    # --------------------------------------------------------
    # Final Validation
    # --------------------------------------------------------

    print()
    print(
        "运行 final_validation..."
    )

    final_3 = final_validation(
        answer=correct_answer,
        question=QUESTION,
        decision=builder_result,
    )

    assert final_3, (
        "final_validation 没有返回最终答案"
    )

    print(
        "✅ 正常答案 final_validation 通过"
    )

    # ========================================================
    # [7/7]
    # Final Consistency
    # ========================================================

    print()
    print(
        "[7/7] 最终状态一致性检查"
    )

    final_decision = read_field(
        builder_result,
        "decision",
        "",
    )

    assert final_decision == "CONDITIONAL", (
        "最终 Decision 被修改："
        f"{final_decision}"
    )

    assert (
        "续订劳动合同"
        in final_3
    ), (
        "最终答案缺少“续订劳动合同”"
    )

    assert (
        "劳动者提出或者同意续订、订立劳动合同"
        in final_3
    ), (
        "最终答案缺少"
        "“劳动者提出或者同意续订、订立劳动合同”"
    )

    print(
        "✅ Decision = CONDITIONAL"
    )

    print(
        "✅ UNKNOWN 条件仍然存在"
    )

    # ========================================================
    # Final Result
    # ========================================================

    print()
    print("=" * 70)
    print(
        "RAG V6.0-27 "
        "Condition Status Fidelity "
        "回归测试全部通过"
    )
    print("=" * 70)

    print()
    print(
        "测试结果："
    )

    print(
        "  ① UNKNOWN → SATISFIED"
    )

    print(
        "     ✅ Validator 拦截"
    )

    print(
        "     ✅ Final Validation 拒绝"
    )

    print(
        "     ✅ Fallback 保留 Engine 状态"
    )

    print()

    print(
        "  ② UNKNOWN → NOT_SATISFIED"
    )

    print(
        "     ✅ Validator 拦截"
    )

    print(
        "     ✅ Final Validation 拒绝"
    )

    print(
        "     ✅ Fallback 保留 Engine 状态"
    )

    print()

    print(
        "  ③ UNKNOWN → UNKNOWN"
    )

    print(
        "     ✅ Validator 通过"
    )

    print(
        "     ✅ Final Validation 通过"
    )

    print(
        "     ✅ Decision 保持 CONDITIONAL"
    )

    print()
    print(
        "🎉 Condition Status Fidelity "
        "回归测试完成。"
    )


# ============================================================
# Main
# ============================================================

if __name__ == "__main__":
    main()