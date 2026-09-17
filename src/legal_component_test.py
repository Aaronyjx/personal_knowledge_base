# -*- coding: utf-8 -*-

"""
RAG V6.0-27
Legal Component Test

============================================================
功能
============================================================

独立的法律 RAG 组件测试模块。

本文件从 src/rag.py 中拆分 component_test()。

注意：
    - 本次拆分只调整代码文件边界。
    - 不改变原有测试逻辑。
    - 不改变法律判定逻辑。
    - 不改变测试数据。
    - 不改变断言条件。
    - 保留原有中文注释。
    - 版本号只存在于代码内部，不写入文件名。
============================================================
"""

from typing import Any, Dict, List

from src.legal_common import (
    ensure_list,
    get_field,
    normalize_text,
)

from src.legal_decision_adapter import (
    _condition_text,
    build_structured_context,
)

from src.legal_pipeline import (
    run_decision_engine,
    run_answer_builder,
)

from src.legal_validator import (
    validate_fact_condition_mapping,
)

RAG_VERSION = "V6.0-27"

DECISION_CONDITIONAL = "CONDITIONAL"

ANSWER_CONDITIONAL = "CONDITIONAL"


def component_test():
    """
    RAG V6.0-26-FIXED Component Test。

    本测试不依赖 Ollama 生成结果，专门验证 V6.0-25 新增的：

        Fact
          ↓
        Condition
          ↓
        Rule Dependency
          ↓
        Legal Consequence

    测试重点：

    1. “连续签订三次固定期限劳动合同”必须映射为：
           连续订立二次固定期限劳动合同 = SATISFIED

    2. “三次”不得自动证明：
           - 续订劳动合同
           - 劳动者提出或者同意续订、订立劳动合同
           - 第39条 / 第40条排除情形不存在
           - 劳动者未提出订立固定期限劳动合同

    3. Required / Exclusion / Exception 必须保持独立分类。

    4. unknown_conditions 只能包含 Required UNKNOWN。

    5. 不允许把法律条件偷换成：
           “劳动者是否提出或同意订立无固定期限劳动合同”。

    6. Final Fact-to-Condition Validation 必须接受正确表达，
       拒绝错误的条件偷换。
    """

    print()
    print("=" * 70)
    print(f"RAG {RAG_VERSION} Component Test")
    print("=" * 70)

    question = (
        "公司连续签订三次固定期限劳动合同后，"
        "是否必须签订无固定期限劳动合同？"
    )

    print()
    print(f"问题：{question}")

    # --------------------------------------------------------
    # Step 1：Retriever / Structured Context
    # --------------------------------------------------------

    context_data = build_structured_context(
        question=question,
        top_k=5,
        score_threshold=0.55,
    )

    rules = ensure_list(context_data.get("rules", []))

    assert len(rules) > 0, (
        "V6.0-27 Component Test：没有检索到任何法律规则"
    )

    print()
    print(f"Structured Rules：{len(rules)}")

    # --------------------------------------------------------
    # Step 2：Legal Decision Engine
    # --------------------------------------------------------

    decision = run_decision_engine(
        question=question,
        rules=rules,
    )

    engine_condition_results = ensure_list(
        get_field(decision, "condition_results", [])
    )

    assert len(engine_condition_results) == 8, (
        "V6.0-27 Component Test：Engine Condition Results 应为 8"
    )

    print(f"Engine Condition Results：{len(engine_condition_results)}")

    # --------------------------------------------------------
    # Step 3：Answer Builder Adapter
    # --------------------------------------------------------

    adapted = run_answer_builder(
        decision=decision,
        rules=rules,
        question=question,
    )

    assert adapted["engine_decision"] == DECISION_CONDITIONAL, (
        "V6.0-27 Component Test：Engine Decision 应为 CONDITIONAL"
    )

    assert adapted["decision"] == ANSWER_CONDITIONAL, (
        "V6.0-27 Component Test：Builder Decision 应为 CONDITIONAL"
    )

    # --------------------------------------------------------
    # Test 1：用户事实保持原意
    # --------------------------------------------------------

    facts = ensure_list(adapted.get("user_facts", []))

    assert any(
        "三次" in normalize_text(fact)
        and "固定期限劳动合同" in normalize_text(fact)
        for fact in facts
    ), (
        "V6.0-27 Component Test：用户事实“三次固定期限劳动合同”丢失"
    )

    print("✅ Test 1：用户事实“三次固定期限劳动合同”保持原意")

    # --------------------------------------------------------
    # Test 2：Fact → Condition Numeric Threshold Mapping
    # --------------------------------------------------------

    mappings = ensure_list(
        adapted.get("fact_condition_mappings", [])
    )

    three_mapping = next(
        (
            item for item in mappings
            if isinstance(item, dict)
            and normalize_text(item.get("condition", ""))
            == "连续订立二次固定期限劳动合同"
        ),
        None,
    )

    assert three_mapping is not None, (
        "V6.0-27 Component Test：缺少“三次→二次”数量门槛映射"
    )

    assert normalize_text(
        three_mapping.get("status", "")
    ).upper() == "SATISFIED", (
        "V6.0-27 Component Test：三次→二次数量门槛必须为 SATISFIED"
    )

    assert normalize_text(
        three_mapping.get("mapping_type", "")
    ) == "NUMERIC_THRESHOLD", (
        "V6.0-27 Component Test：映射类型必须为 NUMERIC_THRESHOLD"
    )

    print(
        "✅ Test 2：三次固定期限合同 → 连续订立二次固定期限劳动合同 = SATISFIED"
    )

    # --------------------------------------------------------
    # Test 3：Mapping 不得越权证明其它条件
    # --------------------------------------------------------

    does_not_prove = ensure_list(
        three_mapping.get("does_not_prove", [])
    )

    forbidden_proofs = {
        "续订劳动合同",
        "劳动者提出或者同意续订、订立劳动合同",
        "不存在第三十九条规定情形",
        "不存在第四十条第一项规定情形",
        "不存在第四十条第二项规定情形",
        "劳动者未提出订立固定期限劳动合同",
    }

    assert forbidden_proofs.issubset(
        set(normalize_text(item) for item in does_not_prove)
    ), (
        "V6.0-27 Component Test：三次合同的 does_not_prove 信息不完整"
    )

    print("✅ Test 3：三次事实不得越权证明其它法律条件")

    # --------------------------------------------------------
    # Test 4：Required / Exclusion / Exception 分类
    # --------------------------------------------------------

    required_results = ensure_list(
        adapted.get("required_condition_results", [])
    )
    exclusion_results = ensure_list(
        adapted.get("exclusion_condition_results", [])
    )
    exception_results = ensure_list(
        adapted.get("exception_results", [])
    )

    assert len(required_results) == 4, (
        "V6.0-27 Component Test：Required Condition Results 应为 4"
    )
    assert len(exclusion_results) == 3, (
        "V6.0-27 Component Test：Exclusion Condition Results 应为 3"
    )
    assert len(exception_results) == 1, (
        "V6.0-27 Component Test：Exception Results 应为 1"
    )

    required_names = {
        normalize_text(item.get("condition", ""))
        for item in required_results
        if isinstance(item, dict)
    }
    exclusion_names = {
        normalize_text(item.get("condition", ""))
        for item in exclusion_results
        if isinstance(item, dict)
    }
    exception_names = {
        normalize_text(item.get("condition", ""))
        for item in exception_results
        if isinstance(item, dict)
    }

    assert required_names.isdisjoint(exclusion_names), (
        "V6.0-27 Component Test：Required / Exclusion 条件发生重复"
    )
    assert required_names.isdisjoint(exception_names), (
        "V6.0-27 Component Test：Required / Exception 条件发生重复"
    )
    assert exclusion_names.isdisjoint(exception_names), (
        "V6.0-27 Component Test：Exclusion / Exception 条件发生重复"
    )

    print("✅ Test 4：Required / Exclusion / Exception 分类正确")

    # --------------------------------------------------------
    # Test 5：三次事实只能满足数量门槛
    # --------------------------------------------------------

    satisfied = set(
        normalize_text(item)
        for item in ensure_list(
            adapted.get("satisfied_conditions", [])
        )
    )

    assert satisfied == {
        "连续订立二次固定期限劳动合同",
        "存在后续订立的劳动合同",
    }, (
        "V6.0-27 Component Test：当前事实下应满足数量门槛和后续合同存在条件"
    )

    print("✅ Test 5：当前事实仅自动满足数量门槛")

    # --------------------------------------------------------
    # Test 6：Required UNKNOWN 必须恰好为 2
    # --------------------------------------------------------

    unknown_conditions = ensure_list(
        adapted.get("unknown_conditions", [])
    )

    unknown_names = {
        _condition_text(item)
        for item in unknown_conditions
        if _condition_text(item)
    }

    assert unknown_names == {
        "续订劳动合同",
        "劳动者提出或者同意续订、订立劳动合同",
    }, (
        "V6.0-27 Component Test：Required UNKNOWN 条件集合错误"
    )

    print("✅ Test 6：Required UNKNOWN = 2，且只包含两个必备条件")

    # --------------------------------------------------------
    # Test 7：Exclusion / Exception 不得混入 unknown_conditions
    # --------------------------------------------------------

    forbidden_unknown_names = (
        exclusion_names | exception_names
    )

    assert unknown_names.isdisjoint(forbidden_unknown_names), (
        "V6.0-27 Component Test：Exclusion / Exception 被错误加入 unknown_conditions"
    )

    print("✅ Test 7：Exclusion / Exception 未混入普通 UNKNOWN")

    # --------------------------------------------------------
    # Test 8：Condition Dependency 不允许条件偷换
    # --------------------------------------------------------

    correct_answer = (
        "公司连续签订三次固定期限劳动合同，已经达到连续订立二次固定期限劳动合同的数量门槛；"
        "但仍需判断续订劳动合同以及劳动者提出或者同意续订、订立劳动合同等法定条件。"
        "现有事实不能直接证明劳动者已经提出或者同意下一次订立劳动合同，也不能证明不存在法定排除情形。"
    )

    assert validate_fact_condition_mapping(
        answer=correct_answer,
        question=question,
        decision=adapted,
    ), (
        "V6.0-27 Component Test：正确的 Fact → Condition 表达未通过验证"
    )

    wrong_answer_1 = (
        "因为连续签订三次固定期限劳动合同，所以已经证明劳动者同意订立无固定期限劳动合同。"
    )

    assert not validate_fact_condition_mapping(
        answer=wrong_answer_1,
        question=question,
        decision=adapted,
    ), (
        "V6.0-27 Component Test：错误的无固定期限合同条件偷换未被拦截"
    )

    wrong_answer_2 = (
        "第三次合同是否存在仍然需要确认。"
    )

    assert not validate_fact_condition_mapping(
        answer=wrong_answer_2,
        question=question,
        decision=adapted,
    ), (
        "V6.0-27 Component Test：错误的第三次合同存在性判断未被拦截"
    )

    print("✅ Test 8：Fact → Condition 条件偷换验证正确")

    # --------------------------------------------------------
    # Test 9：Rule Dependency 结构完整性
    # --------------------------------------------------------

    assert three_mapping.get("dependency") == (
        "THREE_CONTRACTS_MEET_TWO_CONTRACT_THRESHOLD"
    ), (
        "V6.0-27 Component Test：Rule Dependency 标识错误"
    )

    assert normalize_text(
        three_mapping.get("fact", "")
    ) == "公司连续签订三次固定期限劳动合同", (
        "V6.0-27 Component Test：Mapping fact 必须保持用户事实原意"
    )

    print("✅ Test 9：Rule Dependency 结构完整")

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("Component Test Result")
    print("=" * 70)
    print()
    print(f"Engine Decision：{adapted['engine_decision']}")
    print(f"Builder Decision：{adapted['decision']}")
    print(f"Rules：{len(adapted['rules'])}")
    print(f"Facts：{len(adapted['user_facts'])}")
    print(f"Required Conditions：{len(required_results)}")
    print(f"Exclusion Conditions：{len(exclusion_results)}")
    print(f"Exceptions：{len(exception_results)}")
    print(f"Satisfied Conditions：{len(adapted['satisfied_conditions'])}")
    print(f"Unknown Conditions：{len(unknown_conditions)}")
    print(f"Fact Mappings：{len(mappings)}")
    print()
    print("🎉 RAG V6.0-27 Component Test 全部通过")

    return adapted

