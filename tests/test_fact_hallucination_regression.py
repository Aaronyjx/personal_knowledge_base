# -*- coding: utf-8 -*-

from src.legal_pipeline import (
    build_structured_context,
    run_decision_engine,
    run_answer_builder,
)
from src.legal_validator import final_validation
from src.legal_common import get_field


QUESTION = (
    "公司连续签订三次固定期限劳动合同后，"
    "是否必须签订无固定期限劳动合同？"
)


def read_field(obj, name, default=None):
    """同时兼容 dict 和 DecisionResult。"""
    if isinstance(obj, dict):
        return obj.get(name, default)

    value = get_field(
        obj,
        name,
        default,
    )

    if value is None:
        return default

    return value


def extract_user_fact_section(answer: str) -> str:
    """
    仅提取“1. 用户事实”区域。

    注意：
    “2. 已满足条件”
    “3. 不满足的必备条件”
    等均属于后续结构，不能进入用户事实区域。
    """

    if not answer:
        return ""

    text = (
        answer
        .replace("\r\n", "\n")
        .replace("\r", "\n")
    )

    start_patterns = [
        "1. 用户事实：",
        "用户事实：",
        "【用户事实】",
    ]

    start = -1
    marker_used = None

    for marker in start_patterns:
        position = text.find(marker)

        if position >= 0:
            start = position
            marker_used = marker
            break

    if start < 0:
        return ""

    section = text[
        start + len(marker_used):
    ]

    # 用户事实区域结束：
    # 任何新的顶层编号项目，
    # 或新的正式 Section。
    end_patterns = [
        "\n2. ",
        "\n3. ",
        "\n4. ",
        "\n5. ",
        "\n6. ",
        "\n7. ",
        "\n8. ",
        "\n【法律依据】",
        "\n【法律分析】",
        "\n【需要注意】",
        "\n【结论】",
    ]

    positions = []

    for marker in end_patterns:
        position = section.find(marker)

        if position >= 0:
            positions.append(position)

    if positions:
        section = section[:min(positions)]

    return section.strip()


def main():

    print("=" * 70)
    print("RAG V6.0-27 用户事实幻觉回归测试")
    print("=" * 70)

    print()
    print("问题：")
    print(QUESTION)

    # ========================================================
    # 1. Retriever
    # ========================================================

    print()
    print("[1/6] 构建真实 Structured Context")

    context_data = build_structured_context(
        question=QUESTION,
    )

    rules = context_data.get(
        "rules",
        [],
    )

    print(
        f"Rules: {len(rules)}"
    )

    # ========================================================
    # 2. Decision Engine
    # ========================================================

    print()
    print("[2/6] 运行真实 Legal Decision Engine")

    decision = run_decision_engine(
        question=QUESTION,
        rules=rules,
    )

    engine_decision = read_field(
        decision,
        "decision",
    )

    explicit_facts = read_field(
        decision,
        "explicit_facts",
        [],
    )

    condition_results = read_field(
        decision,
        "condition_results",
        [],
    )

    print(
        f"Decision: {engine_decision}"
    )

    print(
        f"Explicit Facts: {explicit_facts}"
    )

    print(
        f"Condition Results: "
        f"{len(condition_results)}"
    )

    # ========================================================
    # Engine 原始事实基线
    #
    # 当前问题的 Engine 应当只确认：
    #
    #   公司连续签订三次固定期限劳动合同
    #
    # 不应出现：
    #
    #   劳动者已经同意续订劳动合同
    #
    #   劳动者已经提出续订劳动合同
    #
    #   劳动者已经同意订立无固定期限劳动合同
    # ========================================================

    normalized_explicit_facts = [
        str(fact).strip()
        for fact in explicit_facts
        if str(fact).strip()
    ]

    expected_three_contract_fact = (
        "公司连续签订三次固定期限劳动合同"
    )

    if expected_three_contract_fact not in normalized_explicit_facts:
        print()
        print("❌ 回归测试失败：")
        print(
            "   Engine 未确认“三次固定期限劳动合同”原始事实"
        )
        print(
            f"   Engine Explicit Facts: "
            f"{normalized_explicit_facts}"
        )
        raise SystemExit(1)

    forbidden_engine_facts = [
        "劳动者已经同意续订劳动合同",
        "劳动者已经提出续订劳动合同",
        "劳动者已经同意订立无固定期限劳动合同",
        "劳动者已经提出订立无固定期限劳动合同",
    ]

    for forbidden_fact in forbidden_engine_facts:
        if forbidden_fact in normalized_explicit_facts:
            print()
            print("❌ 回归测试失败：")
            print(
                "   Engine 错误确认了未提供的用户事实："
            )
            print(
                f"   {forbidden_fact}"
            )
            raise SystemExit(1)

    # ========================================================
    # 3. Answer Builder
    # ========================================================

    print()
    print("[3/6] 运行真实 Answer Builder")

    structured_decision = run_answer_builder(
        decision=decision,
        rules=rules,
        question=QUESTION,
    )

    structured_engine_decision = read_field(
        structured_decision,
        "decision",
    )

    print(
        f"Builder Decision: "
        f"{structured_engine_decision}"
    )

    # ========================================================
    # 4. 第一组回归：
    # 故意制造第39条用户事实幻觉
    # ========================================================

    print()
    print(
        "[4/6] 第一组：构造带有第39条幻觉事实的答案"
    )

    hallucinated_article_39_answer = """【结论】
目前不能仅根据现有事实确定必须签订无固定期限劳动合同。

【法律依据】
《劳动合同法》第十四条规定了无固定期限劳动合同的相关情形。

【法律分析】
1. 用户事实：
- 公司连续签订三次固定期限劳动合同
- 劳动者存在《劳动合同法》第三十九条规定的情形

2. 条件状态：
- 续订劳动合同：未知
- 劳动者提出或者同意续订、订立劳动合同：未知

【需要注意】
还需要结合具体事实进一步判断。
"""

    injected_article_39_facts = (
        extract_user_fact_section(
            hallucinated_article_39_answer
        )
    )

    print()
    print("故意注入的用户事实：")
    print(injected_article_39_facts)

    print()
    print("运行真实 final_validation")

    final_answer_article_39 = final_validation(
        answer=hallucinated_article_39_answer,
        question=QUESTION,
        decision=structured_decision,
    )

    final_user_fact_section_article_39 = (
        extract_user_fact_section(
            final_answer_article_39
        )
    )

    print()
    print("=" * 70)
    print("第一组最终用户事实区域")
    print("=" * 70)

    print(final_user_fact_section_article_39)

    # ========================================================
    # 第一组回归断言 1：
    # 第39条不能成为用户事实
    # ========================================================

    normalized_final_article_39 = (
        final_user_fact_section_article_39
        .replace(
            "《中华人民共和国劳动合同法》",
            "《劳动合同法》",
        )
    )

    has_article_39_user_fact = (
        "第三十九条" in normalized_final_article_39
        and "情形" in normalized_final_article_39
    )

    if has_article_39_user_fact:
        print()
        print("❌ 第一组回归测试失败：")
        print(
            "   第39条事实仍然进入最终用户事实区域"
        )
        raise SystemExit(1)

    # ========================================================
    # 第一组回归断言 2：
    # Engine 原始事实必须保留
    # ========================================================

    has_three_contract_fact_article_39 = (
        "三次" in final_user_fact_section_article_39
        and "固定期限劳动合同"
        in final_user_fact_section_article_39
    )

    if not has_three_contract_fact_article_39:
        print()
        print("❌ 第一组回归测试失败：")
        print(
            "   Engine 已确认的“三次固定期限劳动合同”事实丢失"
        )
        raise SystemExit(1)

    # ========================================================
    # 第一组回归断言 3：
    # 最终答案不能仍然触发 USER_FACT_VALIDATION
    #
    # 这里重新直接验证最终答案。
    # 如果仍然失败，说明 Fallback 本身没有真正修复。
    # ========================================================

    print()
    print("=" * 70)
    print("第一组：重新验证最终答案")
    print("=" * 70)

    revalidated_article_39_answer = final_validation(
        answer=final_answer_article_39,
        question=QUESTION,
        decision=structured_decision,
    )

    revalidated_article_39_user_fact_section = (
        extract_user_fact_section(
            revalidated_article_39_answer
        )
    )

    has_article_39_after_revalidation = (
        "第三十九条"
        in revalidated_article_39_user_fact_section
        and "情形"
        in revalidated_article_39_user_fact_section
    )

    if has_article_39_after_revalidation:
        print()
        print("❌ 第一组回归测试失败：")
        print(
            "   最终答案重新验证后仍包含第39条用户事实"
        )
        raise SystemExit(1)

    print()
    print("✅ 第一组通过：")
    print(
        "   ① 未经 Engine 确认的第39条用户事实被拒绝"
    )
    print(
        "   ② Engine 已确认的三次合同事实被保留"
    )
    print(
        "   ③ 最终答案重新验证通过"
    )

    # ========================================================
    # 5. 第二组回归：
    # 故意制造“劳动者已经同意续订劳动合同”
    # 用户事实幻觉
    #
    # 注意：
    #
    # Engine 的 explicit_facts 只有：
    #
    #   公司连续签订三次固定期限劳动合同
    #
    # Engine 同时明确判断：
    #
    #   续订劳动合同 = UNKNOWN
    #   劳动者提出或者同意续订、订立劳动合同 = UNKNOWN
    #
    # 因此：
    #
    #   “劳动者已经同意续订劳动合同”
    #
    # 是未经 Engine 确认的新用户事实。
    # ========================================================

    print()
    print(
        "[5/6] 第二组：构造“劳动者已经同意续订劳动合同”幻觉事实"
    )

    hallucinated_consent_answer = """【结论】
目前不能仅根据现有事实确定必须签订无固定期限劳动合同。

【法律依据】
《劳动合同法》第十四条规定了无固定期限劳动合同的相关情形。

【法律分析】
1. 用户事实：
- 公司连续签订三次固定期限劳动合同
- 劳动者已经同意续订劳动合同

2. 条件状态：
- 续订劳动合同：未知
- 劳动者提出或者同意续订、订立劳动合同：未知

【需要注意】
还需要结合具体事实进一步判断。
"""

    injected_consent_facts = (
        extract_user_fact_section(
            hallucinated_consent_answer
        )
    )

    print()
    print("故意注入的用户事实：")
    print(injected_consent_facts)

    # ========================================================
    # 第二组回归断言 1：
    # 注入内容确实包含故意制造的同意事实
    #
    # 防止测试本身写错，导致“没有测试到目标”。
    # ========================================================

    if "劳动者已经同意续订劳动合同" not in (
        injected_consent_facts
    ):
        print()
        print("❌ 第二组回归测试配置失败：")
        print(
            "   未成功注入“劳动者已经同意续订劳动合同”"
        )
        raise SystemExit(1)

    # ========================================================
    # 第二组：
    # 运行真实 final_validation
    # ========================================================

    print()
    print("运行真实 final_validation")

    final_answer_consent = final_validation(
        answer=hallucinated_consent_answer,
        question=QUESTION,
        decision=structured_decision,
    )

    final_user_fact_section_consent = (
        extract_user_fact_section(
            final_answer_consent
        )
    )

    print()
    print("=" * 70)
    print("第二组最终用户事实区域")
    print("=" * 70)

    print(final_user_fact_section_consent)

    # ========================================================
    # 第二组回归断言 2：
    # “劳动者已经同意续订劳动合同”
    # 不能进入最终用户事实区域
    # ========================================================

    has_hallucinated_consent_fact = (
        "劳动者已经同意续订劳动合同"
        in final_user_fact_section_consent
    )

    if has_hallucinated_consent_fact:
        print()
        print("❌ 第二组回归测试失败：")
        print(
            "   未经 Engine 确认的"
            "“劳动者已经同意续订劳动合同”"
            "仍然进入最终用户事实区域"
        )
        raise SystemExit(1)

    # ========================================================
    # 第二组回归断言 3：
    # Engine 原始三次合同事实必须继续保留
    # ========================================================

    has_three_contract_fact_consent = (
        "三次" in final_user_fact_section_consent
        and "固定期限劳动合同"
        in final_user_fact_section_consent
    )

    if not has_three_contract_fact_consent:
        print()
        print("❌ 第二组回归测试失败：")
        print(
            "   Engine 已确认的“三次固定期限劳动合同”事实丢失"
        )
        raise SystemExit(1)

    # ========================================================
    # 6. 第二组重新验证：
    # Fallback 修复后的答案必须稳定
    # ========================================================

    print()
    print("=" * 70)
    print("第二组：重新验证最终答案")
    print("=" * 70)

    revalidated_consent_answer = final_validation(
        answer=final_answer_consent,
        question=QUESTION,
        decision=structured_decision,
    )

    revalidated_consent_user_fact_section = (
        extract_user_fact_section(
            revalidated_consent_answer
        )
    )

    has_consent_after_revalidation = (
        "劳动者已经同意续订劳动合同"
        in revalidated_consent_user_fact_section
    )

    if has_consent_after_revalidation:
        print()
        print("❌ 第二组回归测试失败：")
        print(
            "   最终答案重新验证后仍包含"
            "“劳动者已经同意续订劳动合同”"
        )
        raise SystemExit(1)

    has_three_contract_after_revalidation = (
        "三次"
        in revalidated_consent_user_fact_section
        and "固定期限劳动合同"
        in revalidated_consent_user_fact_section
    )

    if not has_three_contract_after_revalidation:
        print()
        print("❌ 第二组回归测试失败：")
        print(
            "   最终答案重新验证后"
            "“三次固定期限劳动合同”事实丢失"
        )
        raise SystemExit(1)

    # ========================================================
    # 7. 第三组回归：
    # 故意制造 Condition → User Fact 反向污染
    #
    # 核心验证：
    #
    #   Engine Condition ≠ User Fact
    #
    # 当前 Engine 原始事实只有：
    #
    #   公司连续签订三次固定期限劳动合同
    #
    # 但是 Engine 的条件判断中存在：
    #
    #   续订劳动合同 = UNKNOWN
    #
    #   劳动者提出或者同意续订、订立劳动合同 = UNKNOWN
    #
    # 因此下面两个内容虽然是 Engine Condition，
    # 但绝对不能被写入“用户事实”区域：
    #
    #   已经完成劳动合同续订
    #
    #   劳动者提出或者同意续订劳动合同
    #
    # 这一组用于验证：
    #
    #   Condition → User Fact
    #
    # 的反向污染能够被拒绝。
    # ========================================================

    print()
    print(
        "[7/8] 第三组：构造 Condition → User Fact 反向污染"
    )

    hallucinated_condition_as_fact_answer = """【结论】
目前不能仅根据现有事实确定必须签订无固定期限劳动合同。

【法律依据】
《劳动合同法》第十四条规定了无固定期限劳动合同的相关情形。

【法律分析】
1. 用户事实：
- 公司连续签订三次固定期限劳动合同
- 已经完成劳动合同续订
- 劳动者提出或者同意续订劳动合同

2. 条件状态：
- 续订劳动合同：未知
- 劳动者提出或者同意续订、订立劳动合同：未知

【需要注意】
还需要结合具体事实进一步判断。
"""

    injected_condition_as_fact_section = (
        extract_user_fact_section(
            hallucinated_condition_as_fact_answer
        )
    )

    print()
    print("故意注入的用户事实：")
    print(injected_condition_as_fact_section)

    # ========================================================
    # 第三组回归断言 1：
    # 测试配置本身必须正确
    #
    # 确保两个 Condition 确实被故意放入
    # “用户事实”区域。
    # ========================================================

    if (
        "已经完成劳动合同续订"
        not in injected_condition_as_fact_section
    ):
        print()
        print("❌ 第三组回归测试配置失败：")
        print(
            "   未成功注入“已经完成劳动合同续订”"
        )
        raise SystemExit(1)

    if (
        "劳动者提出或者同意续订劳动合同"
        not in injected_condition_as_fact_section
    ):
        print()
        print("❌ 第三组回归测试配置失败：")
        print(
            "   未成功注入"
            "“劳动者提出或者同意续订劳动合同”"
        )
        raise SystemExit(1)

    # ========================================================
    # 第三组：
    # 运行真实 final_validation
    # ========================================================

    print()
    print("运行真实 final_validation")

    final_answer_condition_as_fact = final_validation(
        answer=hallucinated_condition_as_fact_answer,
        question=QUESTION,
        decision=structured_decision,
    )

    final_user_fact_section_condition_as_fact = (
        extract_user_fact_section(
            final_answer_condition_as_fact
        )
    )

    print()
    print("=" * 70)
    print("第三组最终用户事实区域")
    print("=" * 70)

    print(final_user_fact_section_condition_as_fact)

    # ========================================================
    # 第三组回归断言 2：
    # “已经完成劳动合同续订”
    # 不能进入最终用户事实区域
    # ========================================================

    has_renewal_as_user_fact = (
        "已经完成劳动合同续订"
        in final_user_fact_section_condition_as_fact
    )

    if has_renewal_as_user_fact:
        print()
        print("❌ 第三组回归测试失败：")
        print(
            "   Engine Condition"
            "“续订劳动合同”"
            "被错误转换成用户事实"
        )
        raise SystemExit(1)

    # ========================================================
    # 第三组回归断言 3：
    # “劳动者提出或者同意续订劳动合同”
    # 不能进入最终用户事实区域
    # ========================================================

    has_consent_condition_as_user_fact = (
        "劳动者提出或者同意续订劳动合同"
        in final_user_fact_section_condition_as_fact
    )

    if has_consent_condition_as_user_fact:
        print()
        print("❌ 第三组回归测试失败：")
        print(
            "   Engine Condition"
            "“劳动者提出或者同意续订劳动合同”"
            "被错误转换成用户事实"
        )
        raise SystemExit(1)

    # ========================================================
    # 第三组回归断言 4：
    # Engine 原始三次合同事实必须继续保留
    # ========================================================

    has_three_contract_fact_condition_as_fact = (
        "三次"
        in final_user_fact_section_condition_as_fact
        and "固定期限劳动合同"
        in final_user_fact_section_condition_as_fact
    )

    if not has_three_contract_fact_condition_as_fact:
        print()
        print("❌ 第三组回归测试失败：")
        print(
            "   Engine 已确认的"
            "“三次固定期限劳动合同”事实丢失"
        )
        raise SystemExit(1)

    # ========================================================
    # 第三组重新验证：
    # Fallback 修复后的答案必须稳定
    # ========================================================

    print()
    print("=" * 70)
    print("第三组：重新验证最终答案")
    print("=" * 70)

    revalidated_condition_as_fact_answer = final_validation(
        answer=final_answer_condition_as_fact,
        question=QUESTION,
        decision=structured_decision,
    )

    revalidated_condition_as_fact_user_section = (
        extract_user_fact_section(
            revalidated_condition_as_fact_answer
        )
    )

    # --------------------------------------------------------
    # 重新验证：
    # Condition 不得变成 User Fact
    # --------------------------------------------------------

    if (
        "已经完成劳动合同续订"
        in revalidated_condition_as_fact_user_section
    ):
        print()
        print("❌ 第三组回归测试失败：")
        print(
            "   最终答案重新验证后仍包含"
            "“已经完成劳动合同续订”"
        )
        raise SystemExit(1)

    if (
        "劳动者提出或者同意续订劳动合同"
        in revalidated_condition_as_fact_user_section
    ):
        print()
        print("❌ 第三组回归测试失败：")
        print(
            "   最终答案重新验证后仍包含"
            "“劳动者提出或者同意续订劳动合同”"
        )
        raise SystemExit(1)

    # --------------------------------------------------------
    # 重新验证：
    # Engine User Fact 必须保留
    # --------------------------------------------------------

    if not (
        "三次"
        in revalidated_condition_as_fact_user_section
        and "固定期限劳动合同"
        in revalidated_condition_as_fact_user_section
    ):
        print()
        print("❌ 第三组回归测试失败：")
        print(
            "   最终答案重新验证后"
            "“三次固定期限劳动合同”事实丢失"
        )
        raise SystemExit(1)

    print()
    print("✅ 第三组通过：")
    print(
        "   ① “已经完成劳动合同续订”"
        "未被允许作为用户事实"
    )
    print(
        "   ② “劳动者提出或者同意续订劳动合同”"
        "未被允许作为用户事实"
    )
    print(
        "   ③ Engine 已确认的三次合同事实被保留"
    )
    print(
        "   ④ 最终答案重新验证通过"
    )

    # ========================================================
    # 最终通过
    # ========================================================

    print()
    print("=" * 70)
    print("回归测试结果")
    print("=" * 70)

    print()
    print("🎉 RAG V6.0-27 用户事实幻觉回归测试全部通过")

    print()
    print("第一组：第39条幻觉事实")
    print(
        "   ✅ 未经 Engine 确认的第39条用户事实被拒绝"
    )
    print(
        "   ✅ Engine 已确认的三次合同事实被保留"
    )
    print(
        "   ✅ 最终答案重新验证通过"
    )

    print()
    print("第二组：劳动者同意续订幻觉事实")
    print(
        "   ✅ 未经 Engine 确认的“劳动者已经同意续订劳动合同”被拒绝"
    )
    print(
        "   ✅ Engine 已确认的三次合同事实被保留"
    )
    print(
        "   ✅ 最终答案重新验证通过"
    )


if __name__ == "__main__":
    main()