# -*- coding: utf-8 -*-

"""
RAG V6.0-27
Legal Pipeline Orchestration

============================================================
功能
============================================================

本模块负责 Legal RAG Pipeline 的运行编排。

主要流程：

    Structured Context
            ↓
    Legal Decision Engine
            ↓
    Answer Builder
            ↓
    Ollama
            ↓
    Deterministic User Facts
            ↓
    Deterministic Condition Analysis
            ↓
    Deterministic Legal Basis
            ↓
    Final Validation
            ↓
    Deterministic Conclusion
            ↓
    Deterministic Notices
            ↓
    Final Answer

本次拆分原则：

    1. 不修改法律判定逻辑。
    2. 不修改 Decision Engine。
    3. 不修改 Answer Builder。
    4. 不修改 Ollama 调用逻辑。
    5. 不修改 Deterministic Lock。
    6. 不修改 Final Validation。
    7. 仅将 Pipeline 编排函数从 rag.py 独立出来。

原始函数：

    run_decision_engine()
    run_answer_builder()
    answer_question()

版本号仍由代码内部维护。
文件名不包含版本号。
"""

from typing import Any, Dict, List


# ============================================================
# Legal Common
# ============================================================

from src.legal_common import (
    ensure_list,
    get_field,
    normalize_text,
)


# ============================================================
# Legal Decision Engine
# ============================================================

from src.legal_decision_engine import (
    make_decision,
)


# ============================================================
# Legal Decision Adapter
# ============================================================

from src.legal_decision_adapter import (
    extract_engine_decision,
    merge_rules_into_decision,
    build_fact_condition_mappings,
    build_structured_context,
)


# ============================================================
# Legal Answer Builder
# ============================================================

from src.legal_answer_builder import (
    adapt_decision_for_answer_builder as builder_adapt_decision,
    get_value,
    safe_text,
    SATISFIED,
    UNKNOWN,
    NOT_SATISFIED,
)


# ============================================================
# Legal Prompt
# ============================================================

from src.legal_prompt import (
    build_ollama_prompt,
)


# ============================================================
# Legal LLM
# ============================================================

from src.legal_llm import (
    OLLAMA_MODEL,
    call_ollama,
)


# ============================================================
# Legal Validator
# ============================================================

from src.legal_validator import (
    final_validation,
)


# ============================================================
# Legal Fallback
# ============================================================

from src.legal_fallback import (
    build_fallback_answer,
)


# ============================================================
# Deterministic User Facts
# ============================================================

from src.deterministic_user_facts import (
    inject_deterministic_user_facts,
)


# ============================================================
# Deterministic Condition Analysis
# ============================================================

from src.inject_deterministic_condition_analysis import (
    inject_deterministic_condition_analysis,
)


# ============================================================
# Deterministic Answer
# ============================================================

from src.legal_deterministic_answer import (
    build_deterministic_legal_basis,
    replace_deterministic_legal_basis,
    build_deterministic_conclusion,
    replace_deterministic_conclusion,
    build_deterministic_notices,
    replace_deterministic_notices,
)


# ============================================================
# Pipeline Version
# ============================================================

RAG_VERSION = "V6.0-27"


# ============================================================
# Original Pipeline Functions
# ============================================================

def run_decision_engine(
    question: str,
    rules: List[Dict[str, Any]],
) -> Any:

    print()
    print("=" * 70)
    print("Step 2 / Legal Decision Engine V6.0-14")
    print("=" * 70)

    print()
    print(
        f"Rules：{len(rules)}"
    )

    try:

        decision = make_decision(
            question=question,
            rules=rules,
        )

    except TypeError:

        # 兼容部分旧版 Decision Engine
        # 可能使用位置参数。

        decision = make_decision(
            question,
            rules,
        )

    status = extract_engine_decision(
        decision
    )

    print()
    print(
        f"Decision：{status}"
    )

    condition_results = ensure_list(
        get_field(
            decision,
            "condition_results",
            [],
        )
    )

    facts = ensure_list(
        get_field(
            decision,
            "explicit_facts",
            get_field(
                decision,
                "facts",
                [],
            ),
        )
    )

    print(
        f"Condition Results："
        f"{len(condition_results)}"
    )

    print(
        f"Explicit Facts："
        f"{len(facts)}"
    )

    return decision



def run_answer_builder(
    decision: Any,
    rules: List[Dict[str, Any]],
    question: str = "",
) -> Dict[str, Any]:
    """
    执行 Legal Answer Builder。

    RAG V6.0-27

    当前职责：

        DecisionResult
             ↓
        Legal Answer Builder
             ↓
        StructuredAnswer
             ↓
        to_dict()
             ↓
        Pipeline Compatibility Layer
             ↓
        Structured Decision

    重要：

    本函数不进行法律推理。

    法律结论完全来自：

        Legal Decision Engine

    Answer Builder 只负责：

        1. 将 DecisionResult 转换为 StructuredAnswer
        2. 合并 Retriever 法律规则
        3. 构建 Fact → Condition Mapping
        4. 保留 Pipeline 所需的兼容字段
        5. 输出 Step 3 调试信息

    ConditionResult 的：

        REQUIRED
        EXCLUSION
        EXCEPTION

    以及：

        SATISFIED
        UNKNOWN
        NOT_SATISFIED

    均由 src.legal_answer_builder.py 负责分类。

    本函数不得重新进行法律推理。
    """

    print()
    print("=" * 70)
    print("Step 3 / Legal Answer Builder V6.0-27")
    print("=" * 70)

    # ========================================================
    # 1. Engine Decision
    # ========================================================

    engine_decision = extract_engine_decision(
        decision
    )

    if not engine_decision:

        raise ValueError(
            "Decision Engine 未返回有效 decision"
        )

    # ========================================================
    # 2. Engine ConditionResult
    #
    # V6.0-27 强制要求：
    #
    #     ConditionResult = 8
    #
    # 这里仍然属于 Pipeline 完整性保护。
    #
    # 但不再自己分类 ConditionResult。
    # ========================================================

    engine_condition_results = ensure_list(
        get_field(
            decision,
            "condition_results",
            [],
        )
    )

    if not engine_condition_results:

        raise ValueError(
            "Decision Engine 未返回 condition_results"
        )

    if len(engine_condition_results) != 8:

        raise ValueError(
            "V6.0-27 要求 "
            f"ConditionResult = 8，"
            f"当前为 {len(engine_condition_results)}"
        )

    # ========================================================
    # 3. StructuredAnswer
    #
    # 正式 Answer Builder 已经负责：
    #
    #     DecisionResult
    #          ↓
    #     StructuredAnswer
    #
    # 包括：
    #
    #     user_facts
    #     satisfied_conditions
    #     unknown_conditions
    #     not_satisfied_conditions
    #     required_conditions
    #     exclusion_conditions
    #     exception_conditions
    #     condition_results
    #     legal_rules
    #     rule_dependencies
    #     contract_sequence
    # ========================================================

    structured_answer = (
        builder_adapt_decision(
            decision=decision,
            strict=True,
        )
    )

    # StructuredAnswer 是正式数据结构。
    #
    # rag.py 后续 Pipeline 仍然使用 dict，
    # 因此这里统一转换一次。
    adapted = structured_answer.to_dict()

    # ========================================================
    # 4. Pipeline Compatibility Fields
    # ========================================================

    adapted["engine_decision"] = (
        engine_decision
    )

    adapted["decision"] = (
        engine_decision
    )

    adapted["raw_decision"] = (
        decision
    )

    adapted[
        "engine_condition_results_count"
    ] = len(
        engine_condition_results
    )

    # ========================================================
    # 6. Merge Retriever Rules
    #
    # Decision Engine 的规则 +
    # Retriever 的规则
    #
    # 最终统一进入：
    #
    #     adapted["rules"]
    # ========================================================

    adapted = merge_rules_into_decision(
        adapted_decision=adapted,
        rules=rules,
    )

    # ========================================================
    # 7. Fact → Condition Mapping
    #
    # 该功能目前仍属于 rag.py 的 Pipeline
    # compatibility layer。
    #
    # 不属于 StructuredAnswer 的标准字段。
    # ========================================================

    adapted[
        "fact_condition_mappings"
    ] = build_fact_condition_mappings(
        decision=decision,
        rules=ensure_list(
            adapted.get(
                "rules",
                [],
            )
        ),
    )

    # ========================================================
    # 8. V6.0-27 Condition Statistics
    #
    # StructuredAnswer 已经完成分类。
    #
    # 这里不再重新遍历 ConditionResult。
    #
    # 直接读取 StructuredAnswer 的结果。
    # ========================================================

    satisfied_conditions = ensure_list(
        adapted.get(
            "satisfied_conditions",
            [],
        )
    )

    unknown_conditions = ensure_list(
        adapted.get(
            "unknown_conditions",
            [],
        )
    )

    not_satisfied_conditions = ensure_list(
        adapted.get(
            "not_satisfied_conditions",
            [],
        )
    )

    required_conditions = ensure_list(
        adapted.get(
            "required_conditions",
            [],
        )
    )

    exclusion_conditions = ensure_list(
        adapted.get(
            "exclusion_conditions",
            [],
        )
    )

    exception_conditions = ensure_list(
        adapted.get(
            "exception_conditions",
            [],
        )
    )

    # ========================================================
    # 9. Compatibility Lists
    #
    # 保留 V6.0-27 原有字段名称。
    # ========================================================

    adapted[
        "required_not_satisfied_conditions"
    ] = [
        condition
        for condition in not_satisfied_conditions
        if condition in required_conditions
    ]

    adapted[
        "triggered_exclusion_conditions"
    ] = [
        condition
        for condition in satisfied_conditions
        if condition in exclusion_conditions
    ]

    adapted[
        "triggered_exception_conditions"
    ] = [
        condition
        for condition in satisfied_conditions
        if condition in exception_conditions
    ]

    adapted[
        "required_condition_results"
    ] = [
        item
        for item in ensure_list(
            adapted.get(
                "condition_results",
                [],
            )
        )
        if isinstance(item, dict)
        and item.get(
            "condition_type"
        ) == "REQUIRED"
    ]

    adapted[
        "exclusion_condition_results"
    ] = [
        item
        for item in ensure_list(
            adapted.get(
                "condition_results",
                [],
            )
        )
        if isinstance(item, dict)
        and item.get(
            "condition_type"
        ) == "EXCLUSION"
    ]

    adapted[
        "exception_results"
    ] = [
        item
        for item in ensure_list(
            adapted.get(
                "condition_results",
                [],
            )
        )
        if isinstance(item, dict)
        and item.get(
            "condition_type"
        ) == "EXCEPTION"
    ]

    # ========================================================
    # 10. Condition Count Validation
    #
    # V6.0-27
    #
    # 注意：
    #
    # StructuredAnswer 的 unknown_conditions
    # 只表示 REQUIRED 类型的 UNKNOWN。
    #
    # EXCLUSION / EXCEPTION 的 UNKNOWN 不进入
    # unknown_conditions。
    #
    # 因此不能再使用：
    #
    #     satisfied
    #     + unknown_conditions
    #     + not_satisfied
    #     == ConditionResult 总数
    #
    # 进行完整状态覆盖验证。
    #
    # 完整 8 条 ConditionResult 的状态统计，
    # 必须直接来自 Engine ConditionResult。
    # ========================================================

    satisfied_count = len(
        satisfied_conditions
    )

    unknown_count = len(
        unknown_conditions
    )

    not_satisfied_count = len(
        not_satisfied_conditions
    )

    # --------------------------------------------------------
    # 从 Engine 原始 ConditionResult 统计完整状态
    # --------------------------------------------------------

    engine_satisfied_count = 0
    engine_unknown_count = 0
    engine_not_satisfied_count = 0

    for item in engine_condition_results:

        status = safe_text(
            get_value(
                item,
                "status",
                "",
            )
        )

        if status == SATISFIED:
            engine_satisfied_count += 1

        elif status == UNKNOWN:
            engine_unknown_count += 1

        elif status == NOT_SATISFIED:
            engine_not_satisfied_count += 1

    # --------------------------------------------------------
    # Engine 状态必须完整覆盖所有 ConditionResult
    # --------------------------------------------------------

    if (
        engine_satisfied_count
        + engine_unknown_count
        + engine_not_satisfied_count
        != len(engine_condition_results)
    ):

        raise ValueError(
            "Engine Condition 状态统计异常："
            f"SATISFIED={engine_satisfied_count}, "
            f"UNKNOWN={engine_unknown_count}, "
            f"NOT_SATISFIED={engine_not_satisfied_count}, "
            f"TOTAL={len(engine_condition_results)}"
        )

    # --------------------------------------------------------
    # StructuredAnswer 的 REQUIRED 状态视图必须正确
    #
    # unknown_conditions 只允许包含 REQUIRED UNKNOWN。
    # --------------------------------------------------------

    required_unknown_count = sum(
        1
        for item in ensure_list(
            adapted.get(
                "required_condition_results",
                [],
            )
        )
        if safe_text(
            get_value(
                item,
                "status",
                "",
            )
        ) == UNKNOWN
    )

    if (
        unknown_count
        != required_unknown_count
    ):

        raise ValueError(
            "StructuredAnswer REQUIRED UNKNOWN "
            "统计异常："
            f"unknown_conditions={unknown_count}, "
            f"required_unknown={required_unknown_count}"
        )

    # --------------------------------------------------------
    # 当前 V6.0-27 兼容字段：
    #
    # satisfied_conditions /
    # not_satisfied_conditions
    #
    # 仍然保持完整状态语义。
    # --------------------------------------------------------

    if (
        satisfied_count
        != engine_satisfied_count
    ):

        raise ValueError(
            "StructuredAnswer SATISFIED 状态统计异常："
            f"structured={satisfied_count}, "
            f"engine={engine_satisfied_count}"
        )

    if (
        not_satisfied_count
        != engine_not_satisfied_count
    ):

        raise ValueError(
            "StructuredAnswer NOT_SATISFIED "
            "状态统计异常："
            f"structured={not_satisfied_count}, "
            f"engine={engine_not_satisfied_count}"
        )

    # ========================================================
    # 11. Decision Consistency
    # ========================================================

    if adapted.get(
        "decision"
    ) != engine_decision:

        raise ValueError(
            "Answer Builder 修改了 Decision Engine 结论："
            f"engine={engine_decision}, "
            f"structured={adapted.get('decision')}"
        )

    # ========================================================
    # 12. Step 3 Debug Summary
    # ========================================================

    print()
    print(
        f"Engine Decision："
        f"{engine_decision}"
    )

    print(
        f"Structured Decision："
        f"{adapted.get('decision')}"
    )

    print(
        f"User Facts："
        f"{len(ensure_list(adapted.get('user_facts', [])))}"
    )

    print(
        f"Condition Results："
        f"{len(engine_condition_results)}"
    )

    print(
        f"REQUIRED："
        f"{len(required_conditions)}"
    )

    print(
        f"EXCLUSION："
        f"{len(exclusion_conditions)}"
    )

    print(
        f"EXCEPTION："
        f"{len(exception_conditions)}"
    )

    print(
        f"Satisfied Conditions："
        f"{satisfied_count}"
    )

    print(
        f"Required Unknown Conditions："
        f"{unknown_count}"
    )

    print(
        f"All Engine UNKNOWN Conditions："
        f"{engine_unknown_count}"
    )

    print(
        f"NOT_SATISFIED Conditions："
        f"{not_satisfied_count}"
    )

    print(
        f"Required Not Satisfied："
        f"{len(adapted.get('required_not_satisfied_conditions', []))}"
    )

    print(
        f"Triggered Exclusions："
        f"{len(adapted.get('triggered_exclusion_conditions', []))}"
    )

    print(
        f"Triggered Exceptions："
        f"{len(adapted.get('triggered_exception_conditions', []))}"
    )

    print(
        f"Legal Rules："
        f"{len(ensure_list(adapted.get('rules', [])))}"
    )

    return adapted
    """
    执行 Legal Answer Builder。

    RAG V6.0-27

    当前职责：

        DecisionResult
             ↓
        Legal Answer Builder
             ↓
        StructuredAnswer
             ↓
        to_dict()
             ↓
        Pipeline Compatibility Layer
             ↓
        Structured Decision

    重要：

    本函数不进行法律推理。

    法律结论完全来自：

        Legal Decision Engine

    Answer Builder 只负责：

        1. 将 DecisionResult 转换为 StructuredAnswer
        2. 合并 Retriever 法律规则
        3. 构建 Fact → Condition Mapping
        4. 保留 Pipeline 所需的兼容字段
        5. 输出 Step 3 调试信息

    ConditionResult 的：

        REQUIRED
        EXCLUSION
        EXCEPTION

    以及：

        SATISFIED
        UNKNOWN
        NOT_SATISFIED

    均由 src.legal_answer_builder.py 负责分类。

    本函数不得重新进行法律推理。
    """

    print()
    print("=" * 70)
    print("Step 3 / Legal Answer Builder V6.0-27")
    print("=" * 70)

    # ========================================================
    # 1. Engine Decision
    # ========================================================

    engine_decision = extract_engine_decision(
        decision
    )

    if not engine_decision:

        raise ValueError(
            "Decision Engine 未返回有效 decision"
        )

    # ========================================================
    # 2. Engine ConditionResult
    #
    # V6.0-27 强制要求：
    #
    #     ConditionResult = 8
    #
    # 这里仍然属于 Pipeline 完整性保护。
    #
    # 但不再自己分类 ConditionResult。
    # ========================================================

    engine_condition_results = ensure_list(
        get_field(
            decision,
            "condition_results",
            [],
        )
    )

    if not engine_condition_results:

        raise ValueError(
            "Decision Engine 未返回 condition_results"
        )

    if len(engine_condition_results) != 8:

        raise ValueError(
            "V6.0-27 要求 "
            f"ConditionResult = 8，"
            f"当前为 {len(engine_condition_results)}"
        )

    # ========================================================
    # 3. StructuredAnswer
    #
    # 正式 Answer Builder 已经负责：
    #
    #     DecisionResult
    #          ↓
    #     StructuredAnswer
    #
    # 包括：
    #
    #     user_facts
    #     satisfied_conditions
    #     unknown_conditions
    #     not_satisfied_conditions
    #     required_conditions
    #     exclusion_conditions
    #     exception_conditions
    #     condition_results
    #     legal_rules
    #     rule_dependencies
    #     contract_sequence
    # ========================================================

    structured_answer = (
        builder_adapt_decision(
            decision=decision,
            strict=True,
        )
    )

    # StructuredAnswer 是正式数据结构。
    #
    # rag.py 后续 Pipeline 仍然使用 dict，
    # 因此这里统一转换一次。
    adapted = structured_answer.to_dict()

    # ========================================================
    # 4. Pipeline Compatibility Fields
    # ========================================================

    adapted["engine_decision"] = (
        engine_decision
    )

    adapted["decision"] = (
        engine_decision
    )

    adapted["raw_decision"] = (
        decision
    )

    adapted[
        "engine_condition_results_count"
    ] = len(
        engine_condition_results
    )

    # ========================================================
    # 7. Fact → Condition Mapping
    #
    # 该功能目前仍属于 rag.py 的 Pipeline
    # compatibility layer。
    #
    # 不属于 StructuredAnswer 的标准字段。
    # ========================================================

    adapted[
        "fact_condition_mappings"
    ] = build_fact_condition_mappings(
        decision=decision,
        rules=ensure_list(
            adapted.get(
                "rules",
                [],
            )
        ),
    )

    # ========================================================
    # 8. V6.0-27 Condition Statistics
    #
    # StructuredAnswer 已经完成分类。
    #
    # 这里不再重新遍历 ConditionResult。
    #
    # 直接读取 StructuredAnswer 的结果。
    # ========================================================

    satisfied_conditions = ensure_list(
        adapted.get(
            "satisfied_conditions",
            [],
        )
    )

    unknown_conditions = ensure_list(
        adapted.get(
            "unknown_conditions",
            [],
        )
    )

    not_satisfied_conditions = ensure_list(
        adapted.get(
            "not_satisfied_conditions",
            [],
        )
    )

    required_conditions = ensure_list(
        adapted.get(
            "required_conditions",
            [],
        )
    )

    exclusion_conditions = ensure_list(
        adapted.get(
            "exclusion_conditions",
            [],
        )
    )

    exception_conditions = ensure_list(
        adapted.get(
            "exception_conditions",
            [],
        )
    )

    # ========================================================
    # 9. Compatibility Lists
    #
    # 保留 V6.0-27 原有字段名称。
    # ========================================================

    adapted[
        "required_not_satisfied_conditions"
    ] = [
        condition
        for condition in not_satisfied_conditions
        if condition in required_conditions
    ]

    adapted[
        "triggered_exclusion_conditions"
    ] = [
        condition
        for condition in satisfied_conditions
        if condition in exclusion_conditions
    ]

    adapted[
        "triggered_exception_conditions"
    ] = [
        condition
        for condition in satisfied_conditions
        if condition in exception_conditions
    ]

    adapted[
        "required_condition_results"
    ] = [
        item
        for item in ensure_list(
            adapted.get(
                "condition_results",
                [],
            )
        )
        if isinstance(item, dict)
        and item.get(
            "condition_type"
        ) == "REQUIRED"
    ]

    adapted[
        "exclusion_condition_results"
    ] = [
        item
        for item in ensure_list(
            adapted.get(
                "condition_results",
                [],
            )
        )
        if isinstance(item, dict)
        and item.get(
            "condition_type"
        ) == "EXCLUSION"
    ]

    adapted[
        "exception_results"
    ] = [
        item
        for item in ensure_list(
            adapted.get(
                "condition_results",
                [],
            )
        )
        if isinstance(item, dict)
        and item.get(
            "condition_type"
        ) == "EXCEPTION"
    ]

    # ========================================================
    # 10. Condition Count Validation
    #
    # 直接根据正式 StructuredAnswer 分类结果统计。
    #
    # 三类状态应该完整覆盖 8 个 ConditionResult。
    # ========================================================

    satisfied_count = len(
        satisfied_conditions
    )

    unknown_count = len(
        unknown_conditions
    )

    not_satisfied_count = len(
        not_satisfied_conditions
    )

    if (
        satisfied_count
        + unknown_count
        + not_satisfied_count
        != len(engine_condition_results)
    ):

        raise ValueError(
            "StructuredAnswer Condition 状态统计异常："
            f"SATISFIED={satisfied_count}, "
            f"UNKNOWN={unknown_count}, "
            f"NOT_SATISFIED={not_satisfied_count}, "
            f"TOTAL={len(engine_condition_results)}"
        )

    # ========================================================
    # 11. Decision Consistency
    # ========================================================

    if adapted.get(
        "decision"
    ) != engine_decision:

        raise ValueError(
            "Answer Builder 修改了 Decision Engine 结论："
            f"engine={engine_decision}, "
            f"structured={adapted.get('decision')}"
        )

    # ========================================================
    # 12. Step 3 Debug Summary
    # ========================================================

    print()
    print(
        f"Engine Decision："
        f"{engine_decision}"
    )

    print(
        f"Structured Decision："
        f"{adapted.get('decision')}"
    )

    print(
        f"User Facts："
        f"{len(ensure_list(adapted.get('user_facts', [])))}"
    )

    print(
        f"Condition Results："
        f"{len(engine_condition_results)}"
    )

    print(
        f"REQUIRED："
        f"{len(required_conditions)}"
    )

    print(
        f"EXCLUSION："
        f"{len(exclusion_conditions)}"
    )

    print(
        f"EXCEPTION："
        f"{len(exception_conditions)}"
    )

    print(
        f"Satisfied Conditions："
        f"{satisfied_count}"
    )

    print(
        f"Required Unknown Conditions："
        f"{unknown_count}"
    )

    print(
        f"All Engine UNKNOWN Conditions："
        f"{engine_unknown_count}"
    )

    print(
        f"NOT_SATISFIED Conditions："
        f"{not_satisfied_count}"
    )

    print(
        f"Required Not Satisfied："
        f"{len(adapted.get('required_not_satisfied_conditions', []))}"
    )

    print(
        f"Triggered Exclusions："
        f"{len(adapted.get('triggered_exclusion_conditions', []))}"
    )

    print(
        f"Triggered Exceptions："
        f"{len(adapted.get('triggered_exception_conditions', []))}"
    )

    print(
        f"Legal Rules："
        f"{len(ensure_list(adapted.get('rules', [])))}"
    )

    return adapted



def answer_question(
    question: str,
    top_k: int = 5,
    score_threshold: float = 0.55,
    model: str = OLLAMA_MODEL,
) -> str:

    print()
    print("=" * 70)
    print(
        f"RAG {RAG_VERSION} - 法律智能问答"
    )
    print("=" * 70)

    question = normalize_text(question)

    print()
    print(
        f"用户问题：{question}"
    )

    if not question:

        print()
        print(
            "⚠️ 用户问题不能为空。"
        )

        return ""

    # ========================================================
    # Step 1
    # ========================================================

    context_data = build_structured_context(
        question=question,
        top_k=top_k,
        score_threshold=score_threshold,
    )

    rules = context_data.get(
        "rules",
        [],
    )

    # ========================================================
    # Step 2
    # ========================================================

    decision = run_decision_engine(
        question=question,
        rules=rules,
    )

    # ========================================================
    # Step 3
    # ========================================================

    structured_decision = run_answer_builder(
        decision=decision,
        rules=rules,
        question=question,
    )

    # ========================================================
    # Step 4
    # Ollama
    #
    # 注意：
    #
    # V6.0-11 修正：
    #
    # 这里只输出一次 Step 4 / Ollama。
    #
    # call_ollama() 本身不再重复打印 Step 4。
    # ========================================================

    prompt = build_ollama_prompt(
        question=question,
        decision=structured_decision,
    )

    try:

        print()
        print("=" * 70)
        print("Step 4 / Ollama")
        print("=" * 70)

        print()
        print(
            f"Model：{model}"
        )

        answer = call_ollama(
            prompt=prompt,
            model=model,
        )

    except Exception as exc:

        print()
        print(
            "⚠️ Ollama 调用失败："
            f"{exc}"
        )

        print()
        print(
            "⚠️ 使用纯 Python Legal Answer Builder fallback。"
        )

        answer = build_fallback_answer(
            question=question,
            decision=structured_decision,
        )

    # ========================================================
    # Step 5
    #
    # V6.0-27：
    #
    # 在 Final Validation 之前，
    # 由 Python 根据 Decision Engine 的用户事实，
    # 确定性恢复 / 覆盖 Ollama 的“用户事实”部分。
    #
    # 注意：
    #
    # 这里不是重新提取用户事实。
    #
    # 用户事实已经由 Legal Decision Engine 确定。
    #
    # Python 这里只负责保证：
    #
    #     Engine User Facts
    #            ↓
    #     Deterministic Injection
    #            ↓
    #     Final Validation
    #
    # 防止 Ollama 漏掉用户事实。
    # ========================================================

    print("\n" + "=" * 70)
    print("DEBUG / Ollama Raw Answer")
    print("=" * 70)
    print(answer)
    print("=" * 70)

    answer = inject_deterministic_user_facts(
        answer=answer,
        decision=structured_decision,
    )

    print()
    print("=" * 70)
    print("DEBUG / Deterministic User Facts Injected")
    print("=" * 70)
    print(answer)
    print("=" * 70)

    # ========================================================
    # Step 6-D
    #
    # V6.0-27：
    #
    # 在 Final Validation 之前，
    # 由 Python 根据 Decision Engine 的完整
    # ConditionResult，确定性恢复 / 覆盖 Ollama
    # 的“条件状态”部分。
    #
    # 注意：
    #
    # 这里不是重新进行法律判断。
    #
    # 所有条件状态已经由 Legal Decision Engine 确定。
    #
    # Python 这里只负责保证：
    #
    #     Engine ConditionResult
    #              ↓
    #     Deterministic Injection
    #              ↓
    #     Final Validation
    #
    # 必须逐条保留全部 ConditionResult。
    #
    # 特别注意：
    #
    #     unknown_conditions
    #
    # 当前只表示：
    #
    #     REQUIRED + UNKNOWN
    #
    # 因此这里不能使用 unknown_conditions。
    #
    # 必须直接读取：
    #
    #     decision["condition_results"]
    #
    # 从而保证：
    #
    #     SATISFIED     → 已满足
    #     UNKNOWN       → 未知
    #     NOT_SATISFIED → 未满足
    #
    # 且 EXCLUSION / EXCEPTION 类型的 UNKNOWN
    # 也必须逐条保留。
    # ========================================================

    answer = inject_deterministic_condition_analysis(
        answer=answer,
        decision=structured_decision,
    )

    print()
    print("=" * 70)
    print("DEBUG / Deterministic Condition Analysis Injected")
    print("=" * 70)
    print(answer)
    print("=" * 70)

    # ========================================================
    # Deterministic Legal Basis
    #
    # Ollama 不负责最终法律依据选择。
    #
    # 法律依据直接来自当前 Structured Rules，
    # 并按照 CORE / RELATED 进行确定性排序。
    #
    # 这样可以防止 Ollama 将第39条、第40条等
    # 排除条件错误地提升为核心法律依据。
    # ========================================================

    deterministic_legal_basis = build_deterministic_legal_basis(
        question=question,
        rules=rules,
    )

    answer = replace_deterministic_legal_basis(
        answer=answer,
        deterministic_legal_basis=deterministic_legal_basis,
    )

    print()
    print("=" * 70)
    print("DEBUG / BEFORE final_validation")
    print("=" * 70)
    print(answer)
    print()
    print("DEBUG / BEFORE final_validation Section Counts")

    for section in [
        "【结论】",
        "【法律依据】",
        "【法律分析】",
        "【需要注意】",
    ]:
        print(
            f"{section}: "
            f"{answer.count(section)}"
        )

    print("=" * 70)

    answer = final_validation(
        answer=answer,
        question=question,
        decision=structured_decision,
    )

    # ============================================================
    # Deterministic Conclusion
    #
    # 注意：
    #
    # Final Validation 可能通过 Ollama 原始答案，
    # 但这并不意味着 Ollama 有权决定最终法律结论。
    #
    # Engine Decision 才是唯一法律决策来源。
    #
    # 因此在 Final Validation 完成以后，
    # 必须再次使用 Python 根据 Decision Engine
    # 确定性锁定【结论】。
    #
    # 这样可以防止 Ollama 出现：
    #
    # CONDITIONAL
    # ↓
    # “当前条件未满足”
    #
    # 这种错误的语义降级。
    # ============================================================

    deterministic_conclusion = (
        build_deterministic_conclusion(
            decision=structured_decision,
        )
    )

    answer = replace_deterministic_conclusion(
        answer=answer,
        deterministic_conclusion=deterministic_conclusion,
    )


    # ============================================================
    # Deterministic Notices
    #
    # 注意：
    # 必须放在 Final Validation 之后。
    # 因为 Final Validation 失败时可能启动 Fallback，
    # Fallback 会重新生成 answer。
    # 因此只有在 Final Validation 完成以后，
    # 才能最终锁定【需要注意】。
    # ============================================================

    deterministic_notices = build_deterministic_notices(
        decision=structured_decision,
    )

    answer = replace_deterministic_notices(
        answer=answer,
        deterministic_notices=deterministic_notices,
    )

    print()
    print("=" * 70)
    print("DEBUG / After Replace Deterministic Notices")
    print("=" * 70)
    print(answer)
    print("=" * 70)

    # ========================================================
    # Final Output
    # ========================================================

    print()
    print("=" * 70)
    print(
        f"RAG {RAG_VERSION} 最终回答"
    )
    print("=" * 70)

    print()
    print(answer)

    return answer

