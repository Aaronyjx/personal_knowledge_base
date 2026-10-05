# -*- coding: utf-8 -*-

"""
RAG V6.1
Decision → Answer Boundary Regression Test

============================================================
测试目标
============================================================

验证：

    DecisionResult
          ↓
    Legal Answer Builder
          ↓
    Legal Prompt
          ↓
    模拟 Ollama 错误回答
          ↓
    Final Validation
          ↓
    Deterministic Fallback
          ↓
    Final Answer

核心原则：

1. Decision Engine 已经确定的 Decision 不得被 LLM 修改。

2. CONDITIONAL：
       不能被 LLM 改成 DEFINITE。

3. DEFINITE：
       不能被 LLM 改成 CONDITIONAL。

4. NOT_ESTABLISHED：
       不能被 LLM 改成肯定法律义务已经成立。

5. UNKNOWN：
       不能被 LLM 改成 SATISFIED。

6. SATISFIED：
       不能被 LLM 改成 UNKNOWN。

7. EXCLUSION / EXCEPTION：
       NOT_SATISFIED 必须保持“已经触发”的语义。

8. 用户事实：
       只能来自 DecisionResult.explicit_facts。

9. LLM 失败时：
       必须进入 Deterministic Fallback。

10. Fallback：
       不得重新进行法律推理，
       只能忠实表达已经存在的 DecisionResult。

============================================================
测试边界
============================================================

本测试不测试：

    Natural Language
        ↓
    LegalFacts

也不测试：

    LegalFacts
        ↓
    ConditionResult
        ↓
    Decision

这两层已经由：

    tests/test_fact_condition_matrix.py
    tests/test_fact_condition_adversarial.py
    tests/test_condition_decision_boundary.py

覆盖。

本测试只测试：

    Decision
        ↓
    Answer

============================================================
"""

from __future__ import annotations

from typing import Any, Dict, List

from src.legal_decision_engine import (
    ConditionResult,
    DecisionResult,
    RuleDependency,
    SATISFIED,
    NOT_SATISFIED,
    UNKNOWN,
    REQUIRED,
    EXCLUSION,
    EXCEPTION,
    DEFINITE,
    CONDITIONAL,
    NOT_ESTABLISHED,
    build_core_rule,
)

from src.legal_answer_builder import (
    adapt_decision_for_answer_builder,
    build_prompt_context,
)

from src.legal_answer_views import (
    build_plain_answer,
    build_answer_context,
    summarize_structured_answer,
)

from src.legal_prompt import (
    build_deterministic_engine_state_block,
    build_ollama_prompt,
)

from src.legal_answer_sanitizer import (
    clean_answer,
)

from src.legal_validator import (
    final_validation,
    validate_decision_consistency,
    validate_unknown_conditions,
)


# ============================================================
# Constants
# ============================================================

TEST_USER_FACT = (
    "公司连续签订三次固定期限劳动合同"
)

ARTICLE_39_FACT = (
    "劳动者存在《劳动合同法》第三十九条规定的情形"
)


from src.legal_rule_definition import RULE_ID
from src.legal_rule_registry import get_rule

_CANONICAL_RULE = get_rule(RULE_ID)


# ============================================================
# Stable Condition Identity
# ============================================================

CONDITION_TEXT_BY_ID = {
    str(item["condition_id"]).strip(): str(item["condition"]).strip()
    for item in _CANONICAL_RULE["condition_definitions"]
}

REQUIRED_001 = CONDITION_TEXT_BY_ID["ARTICLE-14-REQUIRED-001"]
REQUIRED_002 = CONDITION_TEXT_BY_ID["ARTICLE-14-REQUIRED-002"]
REQUIRED_003 = CONDITION_TEXT_BY_ID["ARTICLE-14-REQUIRED-003"]
REQUIRED_004 = CONDITION_TEXT_BY_ID["ARTICLE-14-REQUIRED-004"]

EXCLUSION_001 = CONDITION_TEXT_BY_ID["ARTICLE-14-EXCLUSION-001"]
EXCLUSION_002 = CONDITION_TEXT_BY_ID["ARTICLE-14-EXCLUSION-002"]
EXCLUSION_003 = CONDITION_TEXT_BY_ID["ARTICLE-14-EXCLUSION-003"]

EXCEPTION_001 = CONDITION_TEXT_BY_ID["ARTICLE-14-EXCEPTION-001"]


REQUIRED_CONDITIONS = list(
    _CANONICAL_RULE["conditions"]
)

EXCLUSION_CONDITIONS = list(
    _CANONICAL_RULE["exclusion_conditions"]
)

EXCEPTION_CONDITIONS = list(
    _CANONICAL_RULE["exceptions"]
)

ALL_CONDITIONS = (
    REQUIRED_CONDITIONS
    + EXCLUSION_CONDITIONS
    + EXCEPTION_CONDITIONS
)


# ============================================================
# Assertion Helpers
# ============================================================

def assert_equal(
    actual: Any,
    expected: Any,
    message: str,
) -> None:
    """
    简单断言。
    """

    if actual != expected:
        raise AssertionError(
            f"{message}\n"
            f"实际：{actual}\n"
            f"期望：{expected}"
        )


def assert_true(
    value: bool,
    message: str,
) -> None:
    """
    True 断言。
    """

    if not value:
        raise AssertionError(
            message
        )


def assert_false(
    value: bool,
    message: str,
) -> None:
    """
    False 断言。
    """

    if value:
        raise AssertionError(
            message
        )


# ============================================================
# Condition Factory
# ============================================================

def make_condition(
    condition: str,
    status: str,
    condition_type: str,
    reason: str = "",
) -> ConditionResult:
    """
    创建测试用 ConditionResult。

    注意：

    本测试已经进入 Decision → Answer 层。

    因此这里故意不经过 Fact Extractor，
    也不重新执行 Legal Decision Engine。

    ConditionResult 本身就是本测试的上游契约。
    """

    condition_id = next(
        (
            str(item.get("condition_id", "")).strip()
            for item in _CANONICAL_RULE.get(
                "condition_definitions",
                [],
            )
            if str(item.get("condition", "")).strip() == condition
        ),
        None,
    )

    if not condition_id:
        raise AssertionError(
            f"Canonical Rule 中未找到条件对应的 condition_id：{condition}"
        )

    return ConditionResult(
        condition_id=condition_id,
        condition=condition,
        status=status,
        reason=reason,
        condition_type=condition_type,
    )


# ============================================================
# DecisionResult Factory
# ============================================================

def make_decision_result(
    decision: str,
    statuses: Dict[str, str],
    explicit_facts: List[str] | None = None,
) -> DecisionResult:
    """
    创建一个完整的 8 条 ConditionResult DecisionResult。

    statuses：

        {
            condition_name: status
        }

    必须覆盖全部 8 条条件。
    """

    explicit_facts = (
        list(explicit_facts)
        if explicit_facts is not None
        else [TEST_USER_FACT]
    )

    missing = [
        condition
        for condition in ALL_CONDITIONS
        if condition not in statuses
    ]

    if missing:
        raise AssertionError(
            "测试 DecisionResult 缺少 Condition 状态："
            + ", ".join(missing)
        )

    condition_results: List[ConditionResult] = []

    for condition in REQUIRED_CONDITIONS:

        condition_results.append(
            make_condition(
                condition=condition,
                status=statuses[condition],
                condition_type=REQUIRED,
                reason=(
                    "Decision → Answer 边界测试"
                ),
            )
        )

    for condition in EXCLUSION_CONDITIONS:

        condition_results.append(
            make_condition(
                condition=condition,
                status=statuses[condition],
                condition_type=EXCLUSION,
                reason=(
                    "Decision → Answer 边界测试"
                ),
            )
        )

    for condition in EXCEPTION_CONDITIONS:

        condition_results.append(
            make_condition(
                condition=condition,
                status=statuses[condition],
                condition_type=EXCEPTION,
                reason=(
                    "Decision → Answer 边界测试"
                ),
            )
        )

    rule = build_core_rule()

    dependency = RuleDependency(
        rule_name="劳动合同法第十四条",
        satisfied_by_fact=[
            "连续订立二次固定期限劳动合同",
            "存在后续订立的劳动合同",
        ],
        not_proven_by_fact=[
            "续订劳动合同",
            "劳动者提出或者同意续订、订立劳动合同",
        ],
        explanation=(
            "本测试使用已经确定的 DecisionResult，"
            "不重新进行法律事实推理。"
        ),
    )

    result = DecisionResult(
        decision=decision,
        condition_results=condition_results,
        explicit_facts=explicit_facts,
        contract_sequence=None,
        rule_dependencies=[
            dependency,
        ],
        selected_rule=rule,
        explanation=(
            f"测试 Decision = {decision}"
        ),
        engine_version="V6.1-TEST",
    )

    return result


# ============================================================
# Validation Decision Dict
# ============================================================

def decision_to_validation_dict(
    decision: DecisionResult,
) -> Dict[str, Any]:
    """
    将 DecisionResult 转换成 Final Validation 所需要的 Dict。

    注意：

    Decision Engine 的原始 DecisionResult：

        decision

    Pipeline Validation Adapter：

        engine_decision

    因此这里明确建立：

        engine_decision = DecisionResult.decision

    不进行任何状态转换。
    """

    rule = dict(
        decision.selected_rule
    )

    condition_results = [
        item.to_dict()
        for item in decision.condition_results
    ]

    return {
        "engine_decision": decision.decision,

        "decision": decision.decision,

        "condition_results": condition_results,

        "engine_condition_results_count": (
            len(condition_results)
        ),

        "explicit_facts": list(
            decision.explicit_facts
        ),

        "user_facts": list(
            decision.explicit_facts
        ),

        "satisfied_conditions": (
            decision.satisfied_conditions
        ),

        "unknown_conditions": (
            decision.unknown_conditions
        ),

        "not_satisfied_conditions": (
            decision.not_satisfied_conditions
        ),

        "required_not_satisfied_conditions": (
            decision.required_not_satisfied_conditions
        ),

        "triggered_exclusion_conditions": (
            decision.triggered_exclusion_conditions
        ),

        "triggered_exception_conditions": (
            decision.triggered_exception_conditions
        ),

        "rules": [
            rule,
        ],

        "selected_rule": rule,

        "rule_dependencies": [
            item.to_dict()
            for item in decision.rule_dependencies
        ],

        "explanation": decision.explanation,

        "engine_version": decision.engine_version,

        "raw_decision": decision,
    }


# ============================================================
# Complete Condition Status
# ============================================================

def all_satisfied_statuses() -> Dict[str, str]:
    """
    全部 8 条 SATISFIED。
    """

    return {
        condition: SATISFIED
        for condition in ALL_CONDITIONS
    }


def conditional_statuses() -> Dict[str, str]:
    """
    构造标准 CONDITIONAL：

        REQUIRED 1 = SATISFIED
        REQUIRED 2 = SATISFIED
        REQUIRED 3 = UNKNOWN
        REQUIRED 4 = UNKNOWN

        EXCLUSION = UNKNOWN
        EXCEPTION = UNKNOWN
    """

    return {
        REQUIRED_001: SATISFIED,
        REQUIRED_002: SATISFIED,
        REQUIRED_003: UNKNOWN,
        REQUIRED_004: UNKNOWN,

        EXCLUSION_001: UNKNOWN,
        EXCLUSION_002: UNKNOWN,
        EXCLUSION_003: UNKNOWN,

        EXCEPTION_001: UNKNOWN,
    }


def not_established_statuses() -> Dict[str, str]:
    """
    Article 39 EXCLUSION 已触发。

    CASE 03 的测试目标：

        REQUIRED：
            全部 SATISFIED

        EXCLUSION：
            第三十九条 = SATISFIED
            第四十条第一项 = NOT_SATISFIED
            第四十条第二项 = NOT_SATISFIED

        EXCEPTION：
            NOT_SATISFIED

    V6.1 语义：

        EXCLUSION = SATISFIED
        = 排除情形已经成立，因此触发 NOT_ESTABLISHED。

        EXCLUSION = NOT_SATISFIED
        = 排除情形不存在，因此没有触发。

        EXCEPTION = NOT_SATISFIED
        = 例外情形不存在，因此没有触发。

    本函数专门构造“仅 Article 39 触发”的
    NOT_ESTABLISHED DecisionResult。
    """

    statuses = all_satisfied_statuses()

    # --------------------------------------------------------
    # Article 39：明确触发 EXCLUSION
    # --------------------------------------------------------

    statuses[
        EXCLUSION_001
    ] = SATISFIED

    # --------------------------------------------------------
    # Article 40(1)：明确不存在排除情形
    # --------------------------------------------------------

    statuses[
        EXCLUSION_002
    ] = NOT_SATISFIED

    # --------------------------------------------------------
    # Article 40(2)：明确不存在排除情形
    # --------------------------------------------------------

    statuses[
        EXCLUSION_003
    ] = NOT_SATISFIED

    # --------------------------------------------------------
    # Exception：明确不存在例外情形
    # --------------------------------------------------------

    statuses[
        EXCEPTION_001
    ] = NOT_SATISFIED

    return statuses

# ============================================================
# Valid Answer Factory
# ============================================================

def build_valid_answer(
    decision: str,
    unknown_conditions: List[str],
    triggered_exclusions: List[str] | None = None,
    triggered_exceptions: List[str] | None = None,
) -> str:
    """
    创建一个结构正确的测试答案。

    该答案用于确认 Validator 的正常边界，
    不是测试 Ollama 自由生成能力。
    """

    triggered_exclusions = (
        triggered_exclusions or []
    )

    triggered_exceptions = (
        triggered_exceptions or []
    )

    if decision == CONDITIONAL:

        conclusion = (
            "当前法律结论为条件性结论。"
            "当前事实尚不足以作出确定性结论。"
        )

    elif decision == DEFINITE:

        conclusion = (
            "当前法律结论为确定性结论。"
        )

    elif decision == NOT_ESTABLISHED:

        conclusion = (
            "当前事实下，相关排除或例外条件已经触发，"
            "因此当前不能建立相应的法律结论。"
        )

    else:

        conclusion = (
            f"当前 Engine Decision = {decision}"
        )

    analysis_lines = [
        "用户事实：",
        f"- {TEST_USER_FACT}",
        "",
        "条件状态：",
    ]

    for condition in ALL_CONDITIONS:

        if condition in unknown_conditions:

            status_text = "未知"

        elif condition in triggered_exclusions:

            status_text = "已触发"

        elif condition in triggered_exceptions:

            status_text = "已触发"

        else:

            status_text = "已满足"

        analysis_lines.append(
            f"- {condition}：{status_text}"
        )

    notice_lines = []

    for condition in unknown_conditions:

        notice_lines.append(
            f"- {condition}"
        )

    if not notice_lines:

        notice_lines.append(
            "- 无"
        )

    return (
        "【结论】\n"
        f"{conclusion}\n\n"
        "【法律依据】\n"
        "《中华人民共和国劳动合同法》第十四条\n\n"
        "【法律分析】\n"
        + "\n".join(analysis_lines)
        + "\n\n"
        "【需要注意】\n"
        + "\n".join(notice_lines)
    )


# ============================================================
# CASE 01
# CONDITIONAL 不能被 LLM 改成 DEFINITE
# ============================================================

def case_01_conditional_cannot_become_definite() -> None:

    print()
    print("=" * 70)
    print(
        "CASE 01: CONDITIONAL 不得被 LLM 改成 DEFINITE"
    )
    print("=" * 70)

    decision = make_decision_result(
        decision=CONDITIONAL,
        statuses=conditional_statuses(),
    )

    validation_decision = (
        decision_to_validation_dict(
            decision
        )
    )

    structured = (
        adapt_decision_for_answer_builder(
            decision
        )
    )

    assert_equal(
        structured.decision,
        CONDITIONAL,
        "Answer Builder 不得修改 Decision",
    )

    prompt_context = build_prompt_context(
        structured
    )

    assert_true(
        "CONDITIONAL" in prompt_context,
        "Prompt Context 必须保留 CONDITIONAL",
    )

    deterministic_state = (
        build_deterministic_engine_state_block(
            validation_decision
        )
    )

    assert_true(
        "CONDITIONAL" in deterministic_state,
        "Deterministic State 必须保留 CONDITIONAL",
    )

    malicious_answer = (
        "【结论】\n"
        "公司已经当然必须签订无固定期限劳动合同。\n\n"
        "【法律依据】\n"
        "《中华人民共和国劳动合同法》第十四条\n\n"
        "【法律分析】\n"
        f"用户事实：{TEST_USER_FACT}\n"
        "所有条件均已满足。\n\n"
        "【需要注意】\n"
        "无"
    )

    cleaned = clean_answer(
        malicious_answer
    )

    # ========================================================
    # CONDITIONAL 边界验证
    # ========================================================
    #
    # CONDITIONAL → DEFINITE 的拦截责任不属于
    # validate_decision_consistency()。
    #
    # 真正的边界是：
    #
    #     malicious LLM answer
    #             ↓
    #     final_validation()
    #             ↓
    #     validate_conditional_state()
    #             ↓
    #     Deterministic Fallback
    #             ↓
    #     最终仍然保持 CONDITIONAL
    #
    # 因此这里直接验证 Final Validation。
    # ========================================================

    final_answer = final_validation(
        answer=cleaned,
        question=TEST_USER_FACT,
        decision=validation_decision,
    )

    assert_true(
        "条件性结论" in final_answer,
        "最终答案必须恢复 CONDITIONAL",
    )

    assert_false(
        "已经当然必须签订" in final_answer,
        "最终答案不得保留 LLM 的确定性幻觉",
    )

    assert_true(
        "续订劳动合同" in final_answer,
        "UNKNOWN 条件必须保留",
    )

    print("PASS")


# ============================================================
# CASE 02
# DEFINITE 不能被 LLM 降级为 CONDITIONAL
# ============================================================

def case_02_definite_cannot_become_conditional() -> None:

    print()
    print("=" * 70)
    print(
        "CASE 02: DEFINITE 不得被 LLM 降级为 CONDITIONAL"
    )
    print("=" * 70)

    decision = make_decision_result(
        decision=DEFINITE,
        statuses=all_satisfied_statuses(),
    )

    validation_decision = (
        decision_to_validation_dict(
            decision
        )
    )

    structured = (
        adapt_decision_for_answer_builder(
            decision
        )
    )

    assert_equal(
        structured.decision,
        DEFINITE,
        "Answer Builder 不得修改 DEFINITE",
    )

    prompt = build_ollama_prompt(
        question=TEST_USER_FACT,
        decision=validation_decision,
    )

    assert_true(
        "DEFINITE" in prompt,
        "Prompt 必须明确包含 DEFINITE",
    )

    malicious_answer = (
        "【结论】\n"
        "当前条件尚未确认，无法作出确定性结论。\n"
        "当前条件尚未确认，无法作出确定性结论。\n"
        "当前条件尚未确认，无法作出确定性结论。\n\n"
        "【法律依据】\n"
        "《中华人民共和国劳动合同法》第十四条\n\n"
        "【法律分析】\n"
        f"用户事实：{TEST_USER_FACT}\n"
        "部分条件未知。\n\n"
        "【需要注意】\n"
        "部分条件未知。"
    )

    cleaned = clean_answer(
        malicious_answer
    )

    # ========================================================
    # DEFINITE 边界验证
    # ========================================================
    #
    # validate_decision_consistency()
    # 不负责所有 Decision 状态转换。
    #
    # DEFINITE → CONDITIONAL / UNKNOWN 的真正安全边界
    # 由 final_validation() 完成。
    #
    # 如果 LLM 将 Engine 已经确认的 DEFINITE
    # 降级为“条件性”“未知”等结论，
    # Final Validation 必须拒绝该回答并恢复
    # Deterministic Legal Answer。
    # ========================================================

    final_answer = final_validation(
        answer=cleaned,
        question=TEST_USER_FACT,
        decision=validation_decision,
    )

    assert_true(
        "确定性结论" in final_answer,
        "最终答案必须保持 DEFINITE",
    )

    assert_false(
        "条件性结论" in final_answer,
        "DEFINITE 不得被降级为 CONDITIONAL",
    )

    assert_false(
        "无法确定" in final_answer,
        "DEFINITE 不得被降级为未知结论",
    )

    print("PASS")


# ============================================================
# CASE 03
# NOT_ESTABLISHED 不能被 LLM 改成肯定结论
# ============================================================

def case_03_not_established_cannot_become_positive() -> None:

    print()
    print("=" * 70)
    print(
        "CASE 03: NOT_ESTABLISHED 不得被 LLM 改成肯定结论"
    )
    print("=" * 70)

    decision = make_decision_result(
        decision=NOT_ESTABLISHED,
        statuses=not_established_statuses(),
        explicit_facts=[
            TEST_USER_FACT,
            ARTICLE_39_FACT,
        ],
    )

    validation_decision = (
        decision_to_validation_dict(
            decision
        )
    )

    assert_equal(
        len(
            decision.triggered_exclusion_conditions
        ),
        1,
        "Article 39 必须被识别为已触发 EXCLUSION",
    )

    malicious_answer = (
        "【结论】\n"
        "因此当然必须签订无固定期限劳动合同。\n\n"
        "【法律依据】\n"
        "《中华人民共和国劳动合同法》第十四条\n\n"
        "【法律分析】\n"
        f"- {TEST_USER_FACT}\n"
        f"- {ARTICLE_39_FACT}\n"
        "但是这些情况不影响必须签订合同。\n\n"
        "【需要注意】\n"
        "无"
    )

    cleaned = clean_answer(
        malicious_answer
    )

    consistency = validate_decision_consistency(
        cleaned,
        validation_decision,
    )

    assert_false(
        consistency,
        "NOT_ESTABLISHED 的肯定义务结论必须被拒绝",
    )

    final_answer = final_validation(
        answer=cleaned,
        question=TEST_USER_FACT,
        decision=validation_decision,
    )

    assert_true(
        "已经触发" in final_answer,
        "最终答案必须保留 EXCLUSION 已触发语义",
    )

    assert_false(
        "当然必须签订" in final_answer,
        "最终答案不得保留肯定义务幻觉",
    )

    print("PASS")


# ============================================================
# CASE 04
# UNKNOWN 不能变成 SATISFIED
# ============================================================

def case_04_unknown_cannot_become_satisfied() -> None:

    print()
    print("=" * 70)
    print(
        "CASE 04: UNKNOWN 不得被 LLM 改成 SATISFIED"
    )
    print("=" * 70)

    decision = make_decision_result(
        decision=CONDITIONAL,
        statuses=conditional_statuses(),
    )

    validation_decision = (
        decision_to_validation_dict(
            decision
        )
    )

    malicious_answer = (
        "【结论】\n"
        "当前法律结论为条件性结论。\n\n"
        "【法律依据】\n"
        "《中华人民共和国劳动合同法》第十四条\n\n"
        "【法律分析】\n"
        f"用户事实：{TEST_USER_FACT}\n"
        "续订劳动合同：已满足。\n"
        "劳动者提出或者同意续订、订立劳动合同：已满足。\n\n"
        "【需要注意】\n"
        "无"
    )

    cleaned = clean_answer(
        malicious_answer
    )

    unknown_validation = validate_unknown_conditions(
        cleaned,
        validation_decision,
    )

    assert_false(
        unknown_validation,
        "UNKNOWN 被写成已满足时必须被拒绝",
    )

    final_answer = final_validation(
        answer=cleaned,
        question=TEST_USER_FACT,
        decision=validation_decision,
    )

    assert_true(
        "续订劳动合同" in final_answer,
        "最终答案必须保留 UNKNOWN 条件",
    )

    assert_true(
        "劳动者提出或者同意续订、订立劳动合同"
        in final_answer,
        "最终答案必须保留第二个 UNKNOWN 条件",
    )

    print("PASS")


# ============================================================
# CASE 05
# SATISFIED 不能被 LLM 改成 UNKNOWN
# ============================================================

def case_05_satisfied_cannot_become_unknown() -> None:

    print()
    print("=" * 70)
    print(
        "CASE 05: SATISFIED 不得被 LLM 改成 UNKNOWN"
    )
    print("=" * 70)

    decision = make_decision_result(
        decision=DEFINITE,
        statuses=all_satisfied_statuses(),
    )

    validation_decision = (
        decision_to_validation_dict(
            decision
        )
    )

    malicious_answer = (
        "【结论】\n"
        "当前条件尚未确认，无法作出确定性结论。\n"
        "当前条件尚未确认，无法作出确定性结论。\n"
        "当前条件尚未确认，无法作出确定性结论。\n\n"
        "【法律依据】\n"
        "《中华人民共和国劳动合同法》第十四条\n\n"
        "【法律分析】\n"
        f"用户事实：{TEST_USER_FACT}\n"
        "连续订立二次固定期限劳动合同：未知。\n"
        "存在后续订立的劳动合同：未知。\n\n"
        "【需要注意】\n"
        "以上条件未知。"
    )

    cleaned = clean_answer(
        malicious_answer
    )

    final_answer = final_validation(
        answer=cleaned,
        question=TEST_USER_FACT,
        decision=validation_decision,
    )

    assert_true(
        "确定性结论" in final_answer,
        "DEFINITE 被大幅降级后，最终答案必须恢复确定性结论",
    )

    assert_false(
        "条件性结论" in final_answer,
        "DEFINITE 不得被降级为 CONDITIONAL",
    )

    assert_false(
        "当前条件尚未确认" in final_answer,
        "DEFINITE 不得被降级为 UNKNOWN",
    )

    print("PASS")


# ============================================================
# CASE 06
# EXCLUSION NOT_SATISFIED 必须保持“已触发”
# ============================================================

def case_06_exclusion_semantics_preserved() -> None:

    print()
    print("=" * 70)
    print(
        "CASE 06: EXCLUSION NOT_SATISFIED 语义必须保持"
    )
    print("=" * 70)

    decision = make_decision_result(
        decision=NOT_ESTABLISHED,
        statuses=not_established_statuses(),
        explicit_facts=[
            TEST_USER_FACT,
            ARTICLE_39_FACT,
        ],
    )

    validation_decision = (
        decision_to_validation_dict(
            decision
        )
    )

    deterministic_state = (
        build_deterministic_engine_state_block(
            validation_decision
        )
    )

    assert_true(
        "NOT_SATISFIED" in deterministic_state,
        "Deterministic State 必须保留 NOT_SATISFIED",
    )

    assert_true(
        "已经触发" in deterministic_state,
        "Deterministic State 必须表达 EXCLUSION 已触发",
    )

    malicious_answer = (
        "【结论】\n"
        "当前无法确认劳动者是否存在第三十九条情形。\n\n"
        "【法律依据】\n"
        "《中华人民共和国劳动合同法》第十四条\n\n"
        "【法律分析】\n"
        f"- {TEST_USER_FACT}\n"
        f"- {ARTICLE_39_FACT}\n"
        "第三十九条情形尚不确定。\n\n"
        "【需要注意】\n"
        "请继续核实第三十九条情形。"
    )

    cleaned = clean_answer(
        malicious_answer
    )

    final_answer = final_validation(
        answer=cleaned,
        question=TEST_USER_FACT,
        decision=validation_decision,
    )

    assert_true(
        "已经触发" in final_answer,
        "最终答案必须恢复 EXCLUSION 已触发语义",
    )

    print("PASS")


# ============================================================
# CASE 07
# LLM 不得制造新的 UNKNOWN
# ============================================================

def case_07_llm_cannot_manufacture_unknown() -> None:

    print()
    print("=" * 70)
    print(
        "CASE 07: LLM 不得制造 Engine 没有提供的 UNKNOWN"
    )
    print("=" * 70)

    decision = make_decision_result(
        decision=DEFINITE,
        statuses=all_satisfied_statuses(),
    )

    validation_decision = (
        decision_to_validation_dict(
            decision
        )
    )

    malicious_answer = (
        "【结论】\n"
        "当前法律结论为确定性结论。\n\n"
        "【法律依据】\n"
        "《中华人民共和国劳动合同法》第十四条\n\n"
        "【法律分析】\n"
        f"用户事实：{TEST_USER_FACT}\n"
        "所有 Engine 条件均已满足。\n\n"
        "【需要注意】\n"
        "还需要核实员工是否曾经口头提出过其他要求。\n"
    )

    cleaned = clean_answer(
        malicious_answer
    )

    result = validate_unknown_conditions(
        cleaned,
        validation_decision,
    )

    assert_false(
        result,
        "LLM 制造 Engine 不存在的 UNKNOWN 必须被拒绝",
    )

    final_answer = final_validation(
        answer=cleaned,
        question=TEST_USER_FACT,
        decision=validation_decision,
    )

    assert_false(
        "口头提出过其他要求" in final_answer,
        "最终答案不得保留 LLM 制造的 UNKNOWN",
    )

    print("PASS")


# ============================================================
# CASE 08
# User Fact 不得由 LLM 扩展
# ============================================================

def case_08_user_fact_cannot_be_expanded() -> None:

    print()
    print(
        "=" * 70
    )
    print(
        "CASE 08: LLM 不得扩展 Engine Explicit Facts"
    )
    print("=" * 70)

    decision = make_decision_result(
        decision=CONDITIONAL,
        statuses=conditional_statuses(),
    )

    validation_decision = (
        decision_to_validation_dict(
            decision
        )
    )

    malicious_answer = (
        "【结论】\n"
        "当前法律结论为条件性结论。\n\n"
        "【法律依据】\n"
        "《中华人民共和国劳动合同法》第十四条\n\n"
        "【法律分析】\n"
        f"用户事实：{TEST_USER_FACT}\n"
        "公司已经完成劳动合同续订，"
        "劳动者也明确同意续订。\n\n"
        "【需要注意】\n"
        "续订劳动合同\n"
        "劳动者提出或者同意续订、订立劳动合同"
    )

    cleaned = clean_answer(
        malicious_answer
    )

    final_answer = final_validation(
        answer=cleaned,
        question=TEST_USER_FACT,
        decision=validation_decision,
    )

    assert_false(
        "公司已经完成劳动合同续订"
        in final_answer,
        "最终答案不得新增 completed renewal 事实",
    )

    assert_false(
        "劳动者也明确同意续订"
        in final_answer,
        "最终答案不得新增 worker agreement 事实",
    )

    assert_true(
        "续订劳动合同" in final_answer,
        "真正的 UNKNOWN 条件必须保留",
    )

    print("PASS")


# ============================================================
# CASE 09
# Builder / Prompt / Validator Decision 一致性
# ============================================================

def case_09_decision_consistency_across_layers() -> None:

    print()
    print("=" * 70)
    print(
        "CASE 09: Builder → Prompt → Validator Decision 一致性"
    )
    print("=" * 70)

    decision = make_decision_result(
        decision=CONDITIONAL,
        statuses=conditional_statuses(),
    )

    validation_decision = (
        decision_to_validation_dict(
            decision
        )
    )

    structured = (
        adapt_decision_for_answer_builder(
            decision
        )
    )

    assert_equal(
        structured.decision,
        CONDITIONAL,
        "Builder Decision 必须保持 CONDITIONAL",
    )

    prompt_context = build_prompt_context(
        structured
    )

    assert_true(
        "CONDITIONAL" in prompt_context,
        "Builder Prompt Context 必须包含 CONDITIONAL",
    )

    prompt = build_ollama_prompt(
        question=TEST_USER_FACT,
        decision=validation_decision,
    )

    assert_true(
        "CONDITIONAL" in prompt,
        "Final Prompt 必须包含 CONDITIONAL",
    )

    deterministic_state = (
        build_deterministic_engine_state_block(
            validation_decision
        )
    )

    assert_true(
        "CONDITIONAL" in deterministic_state,
        "Deterministic State 必须包含 CONDITIONAL",
    )

    assert_equal(
        validation_decision[
            "engine_decision"
        ],
        CONDITIONAL,
        "Validator Decision 必须保持 CONDITIONAL",
    )

    print("PASS")


# ============================================================
# CASE 10
# UNKNOWN 一一对应
# ============================================================

def case_10_unknown_one_to_one() -> None:

    print()
    print("=" * 70)
    print(
        "CASE 10: UNKNOWN 条件一一对应"
    )
    print("=" * 70)

    decision = make_decision_result(
        decision=CONDITIONAL,
        statuses=conditional_statuses(),
    )

    validation_decision = (
        decision_to_validation_dict(
            decision
        )
    )

    unknown_conditions = (
        decision.unknown_conditions
    )

    assert_equal(
        len(unknown_conditions),
        6,
        "标准 CONDITIONAL 必须有 6 个 UNKNOWN",
    )

    deterministic_state = (
        build_deterministic_engine_state_block(
            validation_decision
        )
    )

    for condition in unknown_conditions:

        assert_true(
            condition in deterministic_state,
            "Deterministic State 缺少 UNKNOWN："
            + condition,
        )

    malicious_answer = build_valid_answer(
        decision=CONDITIONAL,
        unknown_conditions=unknown_conditions,
    )

    final_answer = final_validation(
        answer=malicious_answer,
        question=TEST_USER_FACT,
        decision=validation_decision,
    )

    for condition in unknown_conditions:

        assert_true(
            condition in final_answer,
            "最终答案缺少 UNKNOWN 条件："
            + condition,
        )

    print("PASS")






# ============================================================
# CASE 11
# Stable Condition ID → Answer Layer State Fidelity
# ============================================================

def case_11_stable_condition_id_state_fidelity() -> None:

    print()
    print("=" * 70)
    print(
        "CASE 11: Stable Condition ID → "
        "Answer Layer State Fidelity"
    )
    print("=" * 70)

    # ========================================================
    # 使用现有 Decision → Answer 测试工厂构造完整 8 条条件
    # ========================================================

    statuses = {
        REQUIRED_001: SATISFIED,
        REQUIRED_002: SATISFIED,
        REQUIRED_003: UNKNOWN,
        REQUIRED_004: UNKNOWN,

        EXCLUSION_001: UNKNOWN,
        EXCLUSION_002: UNKNOWN,
        EXCLUSION_003: UNKNOWN,

        EXCEPTION_001: UNKNOWN,
    }

    decision = make_decision_result(
        decision=CONDITIONAL,
        statuses=statuses,
        explicit_facts=[
            TEST_USER_FACT,
        ],
    )

    # ========================================================
    # 1. Engine ConditionResult 必须严格为 8 条
    # ========================================================

    condition_results = decision.condition_results

    assert_equal(
        len(condition_results),
        8,
        "Engine ConditionResult 必须严格为 8 条",
    )

    # ========================================================
    # 2. Stable Condition ID → Engine Status
    # ========================================================

    expected_status_by_id = {
        "ARTICLE-14-REQUIRED-001": SATISFIED,
        "ARTICLE-14-REQUIRED-002": SATISFIED,
        "ARTICLE-14-REQUIRED-003": UNKNOWN,
        "ARTICLE-14-REQUIRED-004": UNKNOWN,

        "ARTICLE-14-EXCLUSION-001": UNKNOWN,
        "ARTICLE-14-EXCLUSION-002": UNKNOWN,
        "ARTICLE-14-EXCLUSION-003": UNKNOWN,

        "ARTICLE-14-EXCEPTION-001": UNKNOWN,
    }

    actual_status_by_id = {
        result.condition_id: result.status
        for result in condition_results
    }

    assert_equal(
        set(actual_status_by_id),
        set(expected_status_by_id),
        "Engine ConditionResult 的 Stable ID 集合异常",
    )

    assert_equal(
        actual_status_by_id,
        expected_status_by_id,
        "Stable Condition ID → Status 映射异常",
    )

    print(
        "PASS: 8 个 Stable Condition ID 全部存在"
    )

    print(
        "PASS: Engine 状态 = SATISFIED × 2 + UNKNOWN × 6"
    )

    # ========================================================
    # 3. 验证 ConditionResult 的类型也与 Stable ID 一致
    # ========================================================

    expected_type_by_id = {
        "ARTICLE-14-REQUIRED-001": REQUIRED,
        "ARTICLE-14-REQUIRED-002": REQUIRED,
        "ARTICLE-14-REQUIRED-003": REQUIRED,
        "ARTICLE-14-REQUIRED-004": REQUIRED,

        "ARTICLE-14-EXCLUSION-001": EXCLUSION,
        "ARTICLE-14-EXCLUSION-002": EXCLUSION,
        "ARTICLE-14-EXCLUSION-003": EXCLUSION,

        "ARTICLE-14-EXCEPTION-001": EXCEPTION,
    }

    actual_type_by_id = {
        result.condition_id: result.condition_type
        for result in condition_results
    }

    assert_equal(
        actual_type_by_id,
        expected_type_by_id,
        "Stable Condition ID → Condition Type 映射异常",
    )

    print(
        "PASS: Stable Condition ID → Condition Type 映射正确"
    )

    # ========================================================
    # 4. 转换成 Final Validation 使用的 Decision Dict
    # ========================================================

    validation_decision = decision_to_validation_dict(
        decision
    )

    # ========================================================
    # 5. 模拟 LLM 恶意修改全部 6 个 UNKNOWN
    #
    # REQUIRED UNKNOWN × 2
    # EXCLUSION UNKNOWN × 3
    # EXCEPTION UNKNOWN × 1
    # ========================================================

    malicious_answer = (
        "【结论】\n"
        "目前不能仅根据现有事实确定必须签订无固定期限劳动合同。\n\n"
        "【法律依据】\n"
        "《中华人民共和国劳动合同法》第十四条。\n\n"
        "【法律分析】\n"
        f"- 用户事实：{TEST_USER_FACT}\n"
        "- 连续订立二次固定期限劳动合同：已满足\n"
        "- 存在后续订立的劳动合同：已满足\n"
        "- 续订劳动合同：已满足\n"
        "- 劳动者提出或者同意续订、订立劳动合同：不满足\n"
        "- 劳动者存在《劳动合同法》第三十九条规定的情形：已满足\n"
        "- 劳动者存在《劳动合同法》第四十条第一项规定的情形：不满足\n"
        "- 劳动者存在《劳动合同法》第四十条第二项规定的情形：已满足\n"
        "- 劳动者提出订立固定期限劳动合同：不满足\n\n"
        "【需要注意】\n"
        "当前仍需结合具体事实判断。"
    )

    # ========================================================
    # 6. Validator 必须拒绝 UNKNOWN 状态篡改
    # ========================================================

    validation = validate_unknown_conditions(
        malicious_answer,
        validation_decision,
    )

    assert_false(
        validation,
        "Validator 未拦截 UNKNOWN 状态篡改",
    )

    print(
        "PASS: Validator 拦截 UNKNOWN 状态篡改"
    )

    # ========================================================
    # 7. Final Validation 必须回到 Engine State
    # ========================================================

    final_answer = final_validation(
        answer=clean_answer(
            malicious_answer
        ),
        question=TEST_USER_FACT,
        decision=validation_decision,
    )

    assert_true(
        bool(final_answer),
        "Final Validation 未返回最终答案",
    )

    assert_equal(
        validation_decision["decision"],
        CONDITIONAL,
        "Final Validation 不得修改 Engine Decision",
    )

    print(
        "PASS: Decision = CONDITIONAL"
    )

    # ========================================================
    # 8. Final Answer 必须保留全部 6 个 UNKNOWN 条件
    # ========================================================

    unknown_conditions = [
        "续订劳动合同",
        "劳动者提出或者同意续订、订立劳动合同",
        "劳动者存在《劳动合同法》第三十九条规定的情形",
        "劳动者存在《劳动合同法》第四十条第一项规定的情形",
        "劳动者存在《劳动合同法》第四十条第二项规定的情形",
        "劳动者提出订立固定期限劳动合同",
    ]

    for condition in unknown_conditions:

        assert_true(
            condition in final_answer,
            "最终答案缺少 Engine UNKNOWN 条件："
            + condition,
        )

    print(
        "PASS: REQUIRED UNKNOWN × 2 保留"
    )

    print(
        "PASS: EXCLUSION UNKNOWN × 3 保留"
    )

    print(
        "PASS: EXCEPTION UNKNOWN × 1 保留"
    )

    # ========================================================
    # 9. Final Answer 不得保留恶意的确定状态
    # ========================================================

    forbidden_patterns = [
        "续订劳动合同：已满足",
        "续订劳动合同：不满足",

        "劳动者提出或者同意续订、订立劳动合同：已满足",
        "劳动者提出或者同意续订、订立劳动合同：不满足",

        "劳动者存在《劳动合同法》第三十九条规定的情形：已满足",
        "劳动者存在《劳动合同法》第三十九条规定的情形：不满足",

        "劳动者存在《劳动合同法》第四十条第一项规定的情形：已满足",
        "劳动者存在《劳动合同法》第四十条第一项规定的情形：不满足",

        "劳动者存在《劳动合同法》第四十条第二项规定的情形：已满足",
        "劳动者存在《劳动合同法》第四十条第二项规定的情形：不满足",

        "劳动者提出订立固定期限劳动合同：已满足",
        "劳动者提出订立固定期限劳动合同：不满足",
    ]

    for pattern in forbidden_patterns:

        assert_false(
            pattern in final_answer,
            "最终答案存在 UNKNOWN 状态反转："
            + pattern,
        )

    print(
        "PASS: 6 个 UNKNOWN 均未被改写"
    )

    print()
    print(
        "CASE 11 PASS"
    )


# ============================================================
# CASE 12
# Answer View Contract
# ============================================================

def case_12_answer_view_contract() -> None:
    """
    验证 StructuredAnswer → Answer Views 的稳定输出契约。

    本测试不进行法律推理。

    只验证：

        StructuredAnswer
            ↓
        Plain Answer
        Answer Context
        Structured Summary
    """

    print()
    print("=" * 70)
    print(
        "CASE 12: Answer View Contract"
    )
    print("=" * 70)

    decision = make_decision_result(
        decision=CONDITIONAL,
        statuses=conditional_statuses(),
    )

    structured = (
        adapt_decision_for_answer_builder(
            decision
        )
    )

    # ========================================================
    # Plain Answer
    # ========================================================

    plain = build_plain_answer(
        structured
    )

    assert_true(
        "CONDITIONAL" in plain,
        "Plain Answer 必须保留 CONDITIONAL",
    )

    assert_true(
        TEST_USER_FACT in plain,
        "Plain Answer 必须保留用户明确事实",
    )

    assert_true(
        REQUIRED_003 in plain,
        "Plain Answer 必须保留 UNKNOWN 条件",
    )

    assert_true(
        "UNKNOWN" in plain,
        "Plain Answer 必须保留 UNKNOWN 状态",
    )

    # ========================================================
    # Answer Context
    # ========================================================

    context = build_answer_context(
        structured
    )

    assert_equal(
        context.get("decision"),
        CONDITIONAL,
        "Answer Context 必须保留 Decision",
    )

    assert_true(
        TEST_USER_FACT
        in context.get("user_facts", []),
        "Answer Context 必须保留用户事实",
    )

    assert_true(
        REQUIRED_001
        in context.get("satisfied_conditions", []),
        "Answer Context 必须保留 SATISFIED 条件",
    )

    assert_true(
        REQUIRED_003
        in context.get("unknown_conditions", []),
        "Answer Context 必须保留 UNKNOWN 条件",
    )

    assert_equal(
        len(
            context.get(
                "required_conditions",
                [],
            )
        ),
        4,
        "Answer Context REQUIRED 条件数量必须为 4",
    )

    assert_equal(
        len(
            context.get(
                "exclusion_conditions",
                [],
            )
        ),
        3,
        "Answer Context EXCLUSION 条件数量必须为 3",
    )

    assert_equal(
        len(
            context.get(
                "exception_conditions",
                [],
            )
        ),
        1,
        "Answer Context EXCEPTION 条件数量必须为 1",
    )

    # ========================================================
    # Structured Summary
    # ========================================================

    summary = (
        summarize_structured_answer(
            structured
        )
    )

    assert_true(
        "Decision: CONDITIONAL" in summary,
        "Summary 必须保留 Decision",
    )

    assert_true(
        "Condition Results: 8" in summary,
        "Summary 必须保留 Condition Results 数量",
    )

    assert_true(
        "REQUIRED: 4" in summary,
        "Summary 必须保留 REQUIRED 数量",
    )

    assert_true(
        "EXCLUSION: 3" in summary,
        "Summary 必须保留 EXCLUSION 数量",
    )

    assert_true(
        "EXCEPTION: 1" in summary,
        "Summary 必须保留 EXCEPTION 数量",
    )

    assert_true(
        "Satisfied: 2" in summary,
        "Summary 必须保留 SATISFIED 数量",
    )

    assert_true(
        "Unknown: 2" in summary,
        "Summary 必须保留 UNKNOWN 数量",
    )

    assert_true(
        "Not Satisfied: 0" in summary,
        "Summary 必须保留 NOT_SATISFIED 数量",
    )

    print(
        "CASE 12 PASS"
    )


# ============================================================
# Main
# ============================================================

def main() -> None:

    print()
    print("=" * 70)
    print(
        "RAG V6.1 Decision → Answer Boundary Regression Test"
    )
    print("=" * 70)

    print()
    print(
        "测试目标："
    )
    print(
        "  DecisionResult"
        " → Answer Builder"
        " → Prompt"
        " → LLM Answer"
        " → Final Validation"
        " → Final Answer"
    )

    print()
    print(
        "核心原则："
    )
    print(
        "  CONDITIONAL 不得变成 DEFINITE"
    )
    print(
        "  DEFINITE 不得被 LLM 降级"
    )
    print(
        "  NOT_ESTABLISHED 不得变成肯定义务"
    )
    print(
        "  UNKNOWN 不得变成 SATISFIED"
    )
    print(
        "  SATISFIED 不得变成 UNKNOWN"
    )
    print(
        "  EXCLUSION / EXCEPTION 语义必须保持"
    )
    print(
        "  LLM 不得制造新的 UNKNOWN"
    )
    print(
        "  LLM 不得扩展用户事实"
    )

    case_01_conditional_cannot_become_definite()

    case_02_definite_cannot_become_conditional()

    case_03_not_established_cannot_become_positive()

    case_04_unknown_cannot_become_satisfied()

    case_05_satisfied_cannot_become_unknown()

    case_06_exclusion_semantics_preserved()

    case_07_llm_cannot_manufacture_unknown()

    case_08_user_fact_cannot_be_expanded()

    case_09_decision_consistency_across_layers()

    case_10_unknown_one_to_one()
    case_11_stable_condition_id_state_fidelity()

    case_12_answer_view_contract()

    print()
    print("=" * 70)
    print(
        "🎉 RAG V6.1 Decision → Answer Boundary Test 全部通过"
    )
    print("=" * 70)

    print()
    print("验证完成：")
    print(
        "  ✓ Decision → Answer Builder 状态保持"
    )
    print(
        "  ✓ Builder → Prompt 状态保持"
    )
    print(
        "  ✓ CONDITIONAL 不得升级为 DEFINITE"
    )
    print(
        "  ✓ DEFINITE 不得被 LLM 降级"
    )
    print(
        "  ✓ NOT_ESTABLISHED 不得变成肯定义务"
    )
    print(
        "  ✓ UNKNOWN 不得变成 SATISFIED"
    )
    print(
        "  ✓ SATISFIED 不得变成 UNKNOWN"
    )
    print(
        "  ✓ EXCLUSION / EXCEPTION 语义保持"
    )
    print(
        "  ✓ LLM 不得制造 UNKNOWN"
    )
    print(
        "  ✓ LLM 不得扩展用户事实"
    )
    print(
        "  ✓ UNKNOWN 一一对应"
    )


if __name__ == "__main__":
    main()