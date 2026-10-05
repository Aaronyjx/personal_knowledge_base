# -*- coding: utf-8 -*-

"""
RAG V6.3
Decision Authority Boundary Regression Test

============================================================
测试目标
============================================================

验证：

    Legal Decision Engine
            ↓
        Engine Decision
            ↓
    Deterministic Conclusion
            ↓
        Final Answer

必须保持 Decision Authority 一致。

核心原则：

    Decision Engine 是唯一法律决策来源。

    Ollama 不得改变：

        DEFINITE
        CONDITIONAL
        NOT_ESTABLISHED

============================================================
攻击场景
============================================================

1. Engine = DEFINITE
   Ollama 故意输出 CONDITIONAL

   最终必须保持：

       DEFINITE

2. Engine = DEFINITE
   Ollama 故意输出 NOT_ESTABLISHED

   最终必须保持：

       DEFINITE

3. Engine = CONDITIONAL
   Ollama 故意输出 DEFINITE

   最终必须保持：

       CONDITIONAL

4. Engine = CONDITIONAL
   Ollama 故意输出 NOT_ESTABLISHED

   最终必须保持：

       CONDITIONAL

5. Engine = NOT_ESTABLISHED
   Ollama 故意输出 DEFINITE

   最终必须保持：

       NOT_ESTABLISHED

6. Engine = NOT_ESTABLISHED
   Ollama 故意输出 CONDITIONAL

   最终必须保持：

       NOT_ESTABLISHED

============================================================
测试边界
============================================================

本测试不修改：

    Legal Decision Engine
    ConditionResult
    Answer Builder
    Ollama
    Final Validation

只验证：

    build_deterministic_conclusion()
    replace_deterministic_conclusion()

是否严格服从 Engine Decision。
"""

from src.legal_deterministic_answer import (
    build_deterministic_conclusion,
    replace_deterministic_conclusion,
)


DEFINITE = "DEFINITE"
CONDITIONAL = "CONDITIONAL"
NOT_ESTABLISHED = "NOT_ESTABLISHED"

SATISFIED = "SATISFIED"
UNKNOWN = "UNKNOWN"
REQUIRED = "REQUIRED"


REQUIRED_CONDITION_1 = "连续订立二次固定期限劳动合同"
REQUIRED_CONDITION_2 = "存在后续订立的劳动合同"
REQUIRED_CONDITION_3 = "续订劳动合同"


def make_decision(decision):
    """
    构造最小 Decision 输入。

    注意：

        本测试不重新执行法律判断。

        decision 由测试场景直接指定，
        用于验证 Deterministic Lock
        是否服从 Engine Decision。
    """

    if decision == DEFINITE:

        condition_results = [
            {
                "condition": REQUIRED_CONDITION_1,
                "status": SATISFIED,
                "condition_type": REQUIRED,
            },
            {
                "condition": REQUIRED_CONDITION_2,
                "status": SATISFIED,
                "condition_type": REQUIRED,
            },
            {
                "condition": REQUIRED_CONDITION_3,
                "status": SATISFIED,
                "condition_type": REQUIRED,
            },
        ]

    elif decision == CONDITIONAL:

        condition_results = [
            {
                "condition": REQUIRED_CONDITION_1,
                "status": SATISFIED,
                "condition_type": REQUIRED,
            },
            {
                "condition": REQUIRED_CONDITION_2,
                "status": SATISFIED,
                "condition_type": REQUIRED,
            },
            {
                "condition": REQUIRED_CONDITION_3,
                "status": UNKNOWN,
                "condition_type": REQUIRED,
            },
        ]

    elif decision == NOT_ESTABLISHED:

        condition_results = [
            {
                "condition": REQUIRED_CONDITION_1,
                "status": "NOT_SATISFIED",
                "condition_type": REQUIRED,
            },
            {
                "condition": REQUIRED_CONDITION_2,
                "status": UNKNOWN,
                "condition_type": REQUIRED,
            },
            {
                "condition": REQUIRED_CONDITION_3,
                "status": UNKNOWN,
                "condition_type": REQUIRED,
            },
        ]

    else:
        raise AssertionError(
            f"非法测试 Decision：{decision}"
        )

    return {
        "engine_decision": decision,
        "decision": decision,
        "condition_results": condition_results,
    }


def assert_lock(
    engine_decision,
    malicious_ollama_conclusion,
):
    """
    验证：

        Engine Decision
            ↓
        Deterministic Conclusion
            ↓
        Final Answer

    不受恶意 Ollama 结论影响。
    """

    decision = make_decision(
        engine_decision
    )

    deterministic_conclusion = (
        build_deterministic_conclusion(
            decision
        )
    )

    malicious_answer = (
        "【结论】\n"
        + malicious_ollama_conclusion
        + "\n\n"
        + "【法律依据】\n"
        + "《劳动合同法》第十四条。\n\n"
        + "【法律分析】\n"
        + "这是故意与 Engine Decision 相反的测试答案。\n\n"
        + "【需要注意】\n"
        + "这是 Decision Authority Boundary 测试。\n"
    )

    final_answer = (
        replace_deterministic_conclusion(
            answer=malicious_answer,
            deterministic_conclusion=(
                deterministic_conclusion
            ),
        )
    )

    assert (
        deterministic_conclusion
        in final_answer
    ), (
        "Deterministic Conclusion 未进入最终答案："
        f"{final_answer}"
    )

    assert (
        malicious_ollama_conclusion
        not in final_answer
    ), (
        "❌ Ollama 恶意结论突破 Decision Authority："
        f"{malicious_ollama_conclusion}"
    )


def test_definite_blocks_conditional():

    assert_lock(
        DEFINITE,
        "当前条件尚未全部满足，属于条件性结论。",
    )


def test_definite_blocks_not_established():

    assert_lock(
        DEFINITE,
        "目前不能认定满足无固定期限劳动合同的条件。",
    )


def test_conditional_blocks_definite():

    assert_lock(
        CONDITIONAL,
        "已经确定必须签订无固定期限劳动合同。",
    )


def test_conditional_blocks_not_established():

    assert_lock(
        CONDITIONAL,
        "已经确定不需要签订无固定期限劳动合同。",
    )


def test_not_established_blocks_definite():

    assert_lock(
        NOT_ESTABLISHED,
        "已经确定必须签订无固定期限劳动合同。",
    )


def test_not_established_blocks_conditional():

    assert_lock(
        NOT_ESTABLISHED,
        "目前属于条件性结论。",
    )


def main():

    print("=" * 70)
    print(
        "RAG V6.3 Decision Authority Boundary Regression Test"
    )
    print("=" * 70)

    tests = [
        (
            "DEFINITE → Ollama CONDITIONAL",
            test_definite_blocks_conditional,
        ),
        (
            "DEFINITE → Ollama NOT_ESTABLISHED",
            test_definite_blocks_not_established,
        ),
        (
            "CONDITIONAL → Ollama DEFINITE",
            test_conditional_blocks_definite,
        ),
        (
            "CONDITIONAL → Ollama NOT_ESTABLISHED",
            test_conditional_blocks_not_established,
        ),
        (
            "NOT_ESTABLISHED → Ollama DEFINITE",
            test_not_established_blocks_definite,
        ),
        (
            "NOT_ESTABLISHED → Ollama CONDITIONAL",
            test_not_established_blocks_conditional,
        ),
    ]

    for name, test in tests:

        print()
        print(
            f"CASE: {name}"
        )

        test()

        print(
            "  ✅ PASS"
        )

    print()
    print("=" * 70)
    print(
        "🎉 V6.3 Decision Authority Boundary PASS"
    )
    print("=" * 70)


if __name__ == "__main__":
    main()
