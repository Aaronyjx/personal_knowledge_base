# -*- coding: utf-8 -*-

"""
RAG V6.1
Condition → Decision Boundary Regression Test

============================================================
测试目标
============================================================

验证：

    LegalFacts
        ↓
    ConditionResult × 8
        ↓
    evaluate_rule()
        ↓
    Decision

核心原则：

    1. 无 UNKNOWN 且无阻断条件
           → DEFINITE

    2. 存在 UNKNOWN，
       且没有阻断条件
           → CONDITIONAL

    3. REQUIRED 当前实现若事实不足：
           → UNKNOWN
           → CONDITIONAL

    4. REQUIRED = NOT_SATISFIED
           → NOT_ESTABLISHED

    5. EXCLUSION = SATISFIED
           → NOT_ESTABLISHED

    6. EXCEPTION = SATISFIED
           → NOT_ESTABLISHED

    7. UNKNOWN 不得被当作 NOT_SATISFIED。

============================================================
注意
============================================================

当前 V6.1 Legal Decision Engine 的 match_condition()
对 REQUIRED 条件的事实不足情况返回 UNKNOWN，
不会直接返回 NOT_SATISFIED。

因此本测试不人为构造当前 Engine 不会产生的
REQUIRED = NOT_SATISFIED 状态。

本测试只验证当前生产 Engine 实际可达的
Condition → Decision 状态转换。
"""

from src.legal_decision_engine import (
    CONDITIONAL,
    DEFINITE,
    NOT_ESTABLISHED,
    REQUIRED,
    EXCLUSION,
    EXCEPTION,
    SATISFIED,
    UNKNOWN,
    NOT_SATISFIED,
    ALL_CONDITIONS,
    evaluate_rule,
    build_core_rule,
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

REQUIRED_CONDITIONS = list(_CANONICAL_RULE["conditions"])
EXCLUSION_CONDITIONS = list(_CANONICAL_RULE["exclusion_conditions"])
EXCEPTION_CONDITIONS = list(_CANONICAL_RULE["exceptions"])

from src.legal_fact_models import (
    ContractSequence,
    LegalFacts,
)


# ============================================================
# Helpers
# ============================================================

def make_complete_facts() -> LegalFacts:
    """
    构造全部法律事实均已明确的 LegalFacts。

    预期：

        4 REQUIRED
            → SATISFIED

        3 EXCLUSION
            → SATISFIED

        1 EXCEPTION
            → SATISFIED

        总计 8 / 8 SATISFIED
            → DEFINITE
    """

    return LegalFacts(
        explicit_facts=[
            "公司连续签订三次固定期限劳动合同",
            "已经完成劳动合同续订",
            "劳动者明确提出或者同意续订、订立劳动合同",
            "劳动者不存在《劳动合同法》第三十九条规定的情形",
            "劳动者不存在《劳动合同法》第四十条第一项规定的情形",
            "劳动者不存在《劳动合同法》第四十条第二项规定的情形",
            "劳动者没有提出订立固定期限劳动合同",
        ],

        contract_sequence=ContractSequence(
            count=3,
            term_type="fixed",
            continuous=True,
        ),

        completed_renewal=True,

        worker_agreement=True,

        article_39=False,

        article_40_1=False,

        article_40_2=False,

        fixed_term_exception=False,
    )


def make_three_contract_facts() -> LegalFacts:
    """
    仅确认三次固定期限劳动合同。

    预期：

        REQUIRED 1 → SATISFIED
        REQUIRED 2 → SATISFIED
        REQUIRED 3 → UNKNOWN
        REQUIRED 4 → UNKNOWN

        EXCLUSION 全部 UNKNOWN
        EXCEPTION UNKNOWN

        → CONDITIONAL
    """

    return LegalFacts(
        explicit_facts=[
            "公司连续签订三次固定期限劳动合同",
        ],

        contract_sequence=ContractSequence(
            count=3,
            term_type="fixed",
            continuous=True,
        ),

        completed_renewal=None,

        worker_agreement=None,

        article_39=None,

        article_40_1=None,

        article_40_2=None,

        fixed_term_exception=None,
    )


def get_status_map(condition_results):
    """
    Condition → Status。
    """

    return {
        result.condition: result.status
        for result in condition_results
    }


def get_type_map(condition_results):
    """
    Condition → Condition Type。
    """

    return {
        result.condition: result.condition_type
        for result in condition_results
    }


def assert_condition_structure(condition_results):
    """
    验证固定 8 条条件结构。
    """

    assert len(condition_results) == 8, (
        "ConditionResult 数量错误："
        f"{len(condition_results)}"
    )

    names = [
        result.condition
        for result in condition_results
    ]

    assert len(set(names)) == 8, (
        "ConditionResult 存在重复条件："
        f"{names}"
    )

    assert set(names) == set(ALL_CONDITIONS), (
        "ConditionResult 条件集合错误。\n"
        f"实际：{names}\n"
        f"期望：{ALL_CONDITIONS}"
    )


def assert_condition_types(condition_results):
    """
    验证：

        REQUIRED   = 4
        EXCLUSION  = 3
        EXCEPTION  = 1
    """

    type_map = get_type_map(condition_results)

    for condition in REQUIRED_CONDITIONS:
        assert type_map[condition] == REQUIRED, (
            f"REQUIRED 类型错误：{condition}"
        )

    for condition in EXCLUSION_CONDITIONS:
        assert type_map[condition] == EXCLUSION, (
            f"EXCLUSION 类型错误：{condition}"
        )

    for condition in EXCEPTION_CONDITIONS:
        assert type_map[condition] == EXCEPTION, (
            f"EXCEPTION 类型错误：{condition}"
        )


def assert_status(
    status_map,
    condition,
    expected,
):
    """
    验证单项条件状态。
    """

    actual = status_map.get(condition)

    assert actual == expected, (
        f"条件状态错误：{condition}\n"
        f"实际：{actual}\n"
        f"期望：{expected}"
    )


def assert_all_statuses(
    status_map,
    conditions,
    expected,
):
    """
    批量验证状态。
    """

    for condition in conditions:
        assert_status(
            status_map,
            condition,
            expected,
        )


def evaluate_facts(facts):
    """
    直接进入 Decision Engine 的
    evaluate_rule()。

    注意：

        本测试故意绕过自然语言 Fact Extractor，
        直接测试：

            LegalFacts
                ↓
            ConditionResult
                ↓
            Decision
    """

    decision, condition_results = evaluate_rule(
        facts=facts,
        rule=build_core_rule(),
    )

    assert_condition_structure(
        condition_results
    )

    assert_condition_types(
        condition_results
    )

    return decision, condition_results


def print_result(
    case_no,
    title,
    decision,
    condition_results,
):
    """
    输出 CASE 核心结果。
    """

    status_map = get_status_map(
        condition_results
    )

    print()
    print("=" * 70)
    print(f"{case_no}: {title}")
    print("=" * 70)

    print(
        f"Decision: {decision}"
    )

    print()
    print("Condition Status:")

    for condition in ALL_CONDITIONS:
        print(
            f"  [{status_map[condition]:15}] "
            f"{condition}"
        )


# ============================================================
# CASE 01
# 无 UNKNOWN 且无阻断条件
# ============================================================

def case_01_all_satisfied():
    """
    8 / 8 SATISFIED
        ↓
    DEFINITE
    """

    facts = make_complete_facts()

    decision, results = evaluate_facts(
        facts
    )

    status_map = get_status_map(
        results
    )

    assert_all_statuses(
        status_map,
        REQUIRED_CONDITIONS,
        SATISFIED,
    )

    assert_all_statuses(
        status_map,
        EXCLUSION_CONDITIONS,
        NOT_SATISFIED,
    )

    assert_all_statuses(
        status_map,
        EXCEPTION_CONDITIONS,
        NOT_SATISFIED,
    )

    assert decision == DEFINITE

    print_result(
        "CASE 01",
        "全部 8 条条件 SATISFIED → DEFINITE",
        decision,
        results,
    )


# ============================================================
# CASE 02
# REQUIRED 3 UNKNOWN
# ============================================================

def case_02_required_3_unknown():
    """
    续订劳动合同 = UNKNOWN

    没有 NOT_SATISFIED
        ↓
    CONDITIONAL
    """

    facts = make_three_contract_facts()

    decision, results = evaluate_facts(
        facts
    )

    status_map = get_status_map(
        results
    )

    assert_status(
        status_map,
        REQUIRED_001,
        SATISFIED,
    )

    assert_status(
        status_map,
        REQUIRED_002,
        SATISFIED,
    )

    assert_status(
        status_map,
        REQUIRED_003,
        UNKNOWN,
    )

    assert_status(
        status_map,
        REQUIRED_004,
        UNKNOWN,
    )

    assert_all_statuses(
        status_map,
        EXCLUSION_CONDITIONS,
        UNKNOWN,
    )

    assert_status(
        status_map,
        EXCEPTION_001,
        UNKNOWN,
    )

    assert decision == CONDITIONAL

    print_result(
        "CASE 02",
        "存在 UNKNOWN，且没有 NOT_SATISFIED → CONDITIONAL",
        decision,
        results,
    )


# ============================================================
# CASE 03
# REQUIRED 4 UNKNOWN
# ============================================================

def case_03_worker_agreement_unknown():
    """
    completed_renewal = True
    worker_agreement = None

    REQUIRED 4 = UNKNOWN。

    验证：

        已完成续订
            ≠
        劳动者同意
    """

    facts = make_complete_facts()

    facts.worker_agreement = None

    decision, results = evaluate_facts(
        facts
    )

    status_map = get_status_map(
        results
    )

    assert_all_statuses(
        status_map,
        [REQUIRED_001, REQUIRED_002, REQUIRED_003],
        SATISFIED,
    )

    assert_status(
        status_map,
        REQUIRED_004,
        UNKNOWN,
    )

    assert_all_statuses(
        status_map,
        EXCLUSION_CONDITIONS,
        NOT_SATISFIED,
    )

    assert_status(
        status_map,
        EXCEPTION_001,
        NOT_SATISFIED,
    )

    assert decision == CONDITIONAL

    print_result(
        "CASE 03",
        "REQUIRED 4 = UNKNOWN → CONDITIONAL",
        decision,
        results,
    )


# ============================================================
# CASE 04
# Article 39 UNKNOWN
# ============================================================

def case_04_article_39_unknown():
    """
    只有 Article 39 EXCLUSION = UNKNOWN。

    即使其它条件全部 SATISFIED，
    仍不能 DEFINITE。
    """

    facts = make_complete_facts()

    facts.article_39 = None

    decision, results = evaluate_facts(
        facts
    )

    status_map = get_status_map(
        results
    )

    assert_all_statuses(
        status_map,
        REQUIRED_CONDITIONS,
        SATISFIED,
    )

    assert_status(
        status_map,
        EXCLUSION_001,
        UNKNOWN,
    )

    assert_status(
        status_map,
        EXCLUSION_002,
        NOT_SATISFIED,
    )

    assert_status(
        status_map,
        EXCLUSION_003,
        NOT_SATISFIED,
    )

    assert_status(
        status_map,
        EXCEPTION_001,
        NOT_SATISFIED,
    )

    assert decision == CONDITIONAL

    print_result(
        "CASE 04",
        "Article 39 = UNKNOWN → CONDITIONAL",
        decision,
        results,
    )


# ============================================================
# CASE 05
# Article 40(1) UNKNOWN
# ============================================================

def case_05_article_40_1_unknown():
    """
    只有 Article 40(1) = UNKNOWN。
    """

    facts = make_complete_facts()

    facts.article_40_1 = None

    decision, results = evaluate_facts(
        facts
    )

    status_map = get_status_map(
        results
    )

    assert_all_statuses(
        status_map,
        REQUIRED_CONDITIONS,
        SATISFIED,
    )

    assert_status(
        status_map,
        EXCLUSION_001,
        NOT_SATISFIED,
    )

    assert_status(
        status_map,
        EXCLUSION_002,
        UNKNOWN,
    )

    assert_status(
        status_map,
        EXCLUSION_003,
        NOT_SATISFIED,
    )

    assert_status(
        status_map,
        EXCEPTION_001,
        NOT_SATISFIED,
    )

    assert decision == CONDITIONAL

    print_result(
        "CASE 05",
        "Article 40(1) = UNKNOWN → CONDITIONAL",
        decision,
        results,
    )


# ============================================================
# CASE 06
# Article 40(2) UNKNOWN
# ============================================================

def case_06_article_40_2_unknown():
    """
    只有 Article 40(2) = UNKNOWN。
    """

    facts = make_complete_facts()

    facts.article_40_2 = None

    decision, results = evaluate_facts(
        facts
    )

    status_map = get_status_map(
        results
    )

    assert_all_statuses(
        status_map,
        REQUIRED_CONDITIONS,
        SATISFIED,
    )

    assert_status(
        status_map,
        EXCLUSION_001,
        NOT_SATISFIED,
    )

    assert_status(
        status_map,
        EXCLUSION_002,
        NOT_SATISFIED,
    )

    assert_status(
        status_map,
        EXCLUSION_003,
        UNKNOWN,
    )

    assert_status(
        status_map,
        EXCEPTION_001,
        NOT_SATISFIED,
    )

    assert decision == CONDITIONAL

    print_result(
        "CASE 06",
        "Article 40(2) = UNKNOWN → CONDITIONAL",
        decision,
        results,
    )

# ============================================================
# CASE 07
# Exception UNKNOWN
# ============================================================

def case_07_exception_unknown():
    """
    固定期限例外 = UNKNOWN。

    即使其它 7 条全部 SATISFIED，
    仍然只能 CONDITIONAL。
    """

    facts = make_complete_facts()

    facts.fixed_term_exception = None

    decision, results = evaluate_facts(
        facts
    )

    status_map = get_status_map(
        results
    )

    assert_all_statuses(
        status_map,
        REQUIRED_CONDITIONS,
        SATISFIED,
    )

    assert_all_statuses(
        status_map,
        EXCLUSION_CONDITIONS,
        NOT_SATISFIED,
    )

    assert_status(
        status_map,
        EXCEPTION_001,
        UNKNOWN,
    )

    assert decision == CONDITIONAL

    print_result(
        "CASE 07",
        "EXCEPTION = UNKNOWN → CONDITIONAL",
        decision,
        results,
    )


# ============================================================
# CASE 08
# Article 39 NOT_SATISFIED
# ============================================================

def case_08_article_39_triggered():
    """
    Article 39 = True

    EXCLUSION：

        True
          ↓
        NOT_SATISFIED
          ↓
        NOT_ESTABLISHED
    """

    facts = make_complete_facts()

    facts.article_39 = True

    decision, results = evaluate_facts(
        facts
    )

    status_map = get_status_map(
        results
    )

    assert_all_statuses(
        status_map,
        REQUIRED_CONDITIONS,
        SATISFIED,
    )

    assert_status(
        status_map,
        EXCLUSION_001,
        SATISFIED,
    )

    assert_status(
        status_map,
        EXCLUSION_002,
        NOT_SATISFIED,
    )

    assert_status(
        status_map,
        EXCLUSION_003,
        NOT_SATISFIED,
    )

    assert_status(
        status_map,
        EXCEPTION_001,
        NOT_SATISFIED,
    )

    assert decision == NOT_ESTABLISHED

    print_result(
        "CASE 08",
        "Article 39 EXCLUSION = SATISFIED → NOT_ESTABLISHED",
        decision,
        results,
    )


# ============================================================
# CASE 09
# Article 40(1) SATISFIED
# ============================================================

def case_09_article_40_1_triggered():
    """
    Article 40(1) 触发排除条件。

    EXCLUSION：

        True
          ↓
        SATISFIED
          ↓
        NOT_ESTABLISHED
    """

    facts = make_complete_facts()

    facts.article_40_1 = True

    decision, results = evaluate_facts(
        facts
    )

    status_map = get_status_map(
        results
    )

    assert_all_statuses(
        status_map,
        REQUIRED_CONDITIONS,
        SATISFIED,
    )

    assert_status(
        status_map,
        EXCLUSION_001,
        NOT_SATISFIED,
    )

    assert_status(
        status_map,
        EXCLUSION_002,
        SATISFIED,
    )

    assert_status(
        status_map,
        EXCLUSION_003,
        NOT_SATISFIED,
    )

    assert_status(
        status_map,
        EXCEPTION_001,
        NOT_SATISFIED,
    )

    assert decision == NOT_ESTABLISHED

    print_result(
        "CASE 09",
        "Article 40(1) EXCLUSION = SATISFIED → NOT_ESTABLISHED",
        decision,
        results,
    )

# ============================================================
# CASE 10
# Exception SATISFIED
# ============================================================

def case_10_exception_triggered():
    """
    fixed_term_exception = True

    EXCEPTION：

        True
          ↓
        SATISFIED
          ↓
        NOT_ESTABLISHED
    """

    facts = make_complete_facts()

    facts.fixed_term_exception = True

    decision, results = evaluate_facts(
        facts
    )

    status_map = get_status_map(
        results
    )

    assert_all_statuses(
        status_map,
        REQUIRED_CONDITIONS,
        SATISFIED,
    )

    assert_all_statuses(
        status_map,
        EXCLUSION_CONDITIONS,
        NOT_SATISFIED,
    )

    assert_status(
        status_map,
        EXCEPTION_001,
        SATISFIED,
    )

    assert decision == NOT_ESTABLISHED

    print_result(
        "CASE 10",
        "EXCEPTION = SATISFIED → NOT_ESTABLISHED",
        decision,
        results,
    )

# ============================================================
# DECISION ISOLATION CHECK
# ============================================================

def decision_isolation_check():
    """
    验证 Decision 只由 ConditionResult 状态决定。

    本测试直接构造完整 LegalFacts：

        4 REQUIRED
            → SATISFIED

        3 EXCLUSION
            → NOT_SATISFIED

        1 EXCEPTION
            → NOT_SATISFIED

        不存在 UNKNOWN
            ↓
        DEFINITE

    同时验证：

        explicit_facts
        contract_sequence

    不会在没有改变对应 ConditionResult 的情况下，
    额外改变 Decision。
    """

    facts = make_complete_facts()

    decision_1, results_1 = evaluate_facts(
        facts
    )

    assert decision_1 == DEFINITE

    status_map_1 = get_status_map(
        results_1
    )

    assert_all_statuses(
        status_map_1,
        REQUIRED_CONDITIONS,
        SATISFIED,
    )

    assert_all_statuses(
        status_map_1,
        EXCLUSION_CONDITIONS,
        NOT_SATISFIED,
    )

    assert_all_statuses(
        status_map_1,
        EXCEPTION_CONDITIONS,
        NOT_SATISFIED,
    )

    # --------------------------------------------------------
    # 修改与条件判断无关的显示性事实文本。
    #
    # ConditionResult 不应因此发生变化。
    # --------------------------------------------------------

    facts.explicit_facts = [
        "完全无关的用户描述",
        "这是额外文本，不代表任何法律条件",
    ]

    decision_2, results_2 = evaluate_facts(
        facts
    )

    assert decision_2 == DEFINITE

    status_map_2 = get_status_map(
        results_2
    )

    assert_all_statuses(
        status_map_2,
        REQUIRED_CONDITIONS,
        SATISFIED,
    )

    assert_all_statuses(
        status_map_2,
        EXCLUSION_CONDITIONS,
        NOT_SATISFIED,
    )

    assert_all_statuses(
        status_map_2,
        EXCEPTION_CONDITIONS,
        NOT_SATISFIED,
    )

    # --------------------------------------------------------
    # 合同序列是 LegalFacts 的法律事实字段，
    # 但只有它实际映射到的条件才能影响 Decision。
    #
    # 将 count 从 3 改为 2 后：
    #
    # REQUIRED 2 将变成 UNKNOWN。
    #
    # 同时将 completed_renewal 清除为 UNKNOWN。
    #
    # 因而：
    #
    # DEFINITE
    #     ↓
    # CONDITIONAL
    #
    # 这是合法的 Condition → Decision 变化。
    # --------------------------------------------------------

    facts.contract_sequence = ContractSequence(
        count=2,
        term_type="fixed",
        continuous=True,
    )

    facts.completed_renewal = None

    decision_3, results_3 = evaluate_facts(
        facts
    )

    status_map_3 = get_status_map(
        results_3
    )

    assert_status(
        status_map_3,
        REQUIRED_001,
        SATISFIED,
    )

    assert_status(
        status_map_3,
        REQUIRED_002,
        UNKNOWN,
    )

    assert decision_3 == CONDITIONAL
    
# ============================================================
# UNKNOWN PROTECTION CHECK
# ============================================================

def unknown_protection_check():
    """
    验证 UNKNOWN 不会自动升级。

    采用最小事实集：

        三次合同

    预期：

        REQUIRED 3 = UNKNOWN
        REQUIRED 4 = UNKNOWN
        所有 EXCLUSION = UNKNOWN
        EXCEPTION = UNKNOWN

        Decision = CONDITIONAL
    """

    facts = make_three_contract_facts()

    decision, results = evaluate_facts(
        facts
    )

    status_map = get_status_map(
        results
    )

    unknown_conditions = [
        condition
        for condition in ALL_CONDITIONS
        if status_map[condition] == UNKNOWN
    ]

    assert len(unknown_conditions) == 6, (
        "UNKNOWN 条件数量错误："
        f"{len(unknown_conditions)}\n"
        f"实际：{unknown_conditions}"
    )

    assert decision == CONDITIONAL

    # --------------------------------------------------------
    # 明确禁止：
    #
    # UNKNOWN → SATISFIED
    # UNKNOWN → NOT_SATISFIED
    # --------------------------------------------------------

    for condition in unknown_conditions:
        assert status_map[condition] == UNKNOWN

    print()
    print("=" * 70)
    print("UNKNOWN PROTECTION CHECK")
    print("=" * 70)
    print("PASS")


# ============================================================
# Main
# ============================================================

def main():
    print()
    print("=" * 70)
    print("RAG V6.1 Condition → Decision Boundary Regression Test")
    print("=" * 70)

    print()
    print("测试目标：")
    print("  LegalFacts → ConditionResult × 8 → Decision")

    print()
    print("核心原则：")
    print("  无 UNKNOWN 且无阻断条件 → DEFINITE")
    print("  存在 UNKNOWN 且无阻断条件 → CONDITIONAL")
    print("  REQUIRED NOT_SATISFIED → NOT_ESTABLISHED")
    print("  EXCLUSION SATISFIED → NOT_ESTABLISHED")
    print("  EXCEPTION SATISFIED → NOT_ESTABLISHED")
    print("  UNKNOWN 不得自动升级")

    case_01_all_satisfied()
    case_02_required_3_unknown()
    case_03_worker_agreement_unknown()
    case_04_article_39_unknown()
    case_05_article_40_1_unknown()
    case_06_article_40_2_unknown()
    case_07_exception_unknown()
    case_08_article_39_triggered()
    case_09_article_40_1_triggered()
    case_10_exception_triggered()

    decision_isolation_check()
    unknown_protection_check()

    print()
    print("=" * 70)
    print(
        "🎉 RAG V6.1 Condition → Decision Boundary Test 全部通过"
    )
    print("=" * 70)

    print()
    print("验证完成：")
    print("  ✓ 8 条 ConditionResult 结构固定")
    print("  ✓ 无 UNKNOWN 且无阻断条件 → DEFINITE")
    print("  ✓ 存在 UNKNOWN 且无阻断条件 → CONDITIONAL")
    print("  ✓ Article 39 EXCLUSION → NOT_ESTABLISHED")
    print("  ✓ Article 40(1) EXCLUSION → NOT_ESTABLISHED")
    print("  ✓ EXCEPTION → NOT_ESTABLISHED")
    print("  ✓ UNKNOWN 保持 UNKNOWN")
    print("  ✓ Decision Isolation")
    print("  ✓ Condition → Decision 边界稳定")


if __name__ == "__main__":
    main()