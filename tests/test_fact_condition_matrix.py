# -*- coding: utf-8 -*-

"""
RAG V6.1
Fact → Condition Matrix Regression Test

============================================================
功能
============================================================

验证 V6.1 第一阶段：

    Natural Language Question
              ↓
    Legal Fact Extractor
              ↓
          LegalFacts
              ↓
    Legal Decision Engine
              ↓
       ConditionResult
              ↓
         Final Decision

============================================================
核心目标
============================================================

验证：

1. 用户事实能够正确进入 LegalFacts。

2. LegalFacts 能够正确映射到 8 个法律条件。

3. 三次固定期限劳动合同不能自动推出：
       - 已经续订
       - 劳动者已经同意续订

4. Article 39 / Article 40(1) / Article 40(2)
   的明确存在、明确不存在、未说明，
   分别保持：

       存在     → NOT_SATISFIED
       不存在   → SATISFIED
       未说明   → UNKNOWN

5. 固定期限例外同样保持状态真实性。

6. 所有 8 个条件全部 SATISFIED 时：

       Decision = DEFINITE

7. 任一 REQUIRED / EXCLUSION / EXCEPTION
   被明确触发时：

       Decision = NOT_ESTABLISHED

8. 存在 UNKNOWN 且没有 NOT_SATISFIED 时：

       Decision = CONDITIONAL

============================================================
版本说明
============================================================

测试文件名保持稳定：

    tests/test_fact_condition_matrix.py

不要把 V6.1 写入文件名。

版本信息只放在：
    - 文件注释
    - 测试输出
    - Git commit

这样便于后续 V6.2 / V6.3 持续复用。
"""

from __future__ import annotations

from typing import Dict

from src.legal_decision_engine import make_decision


# ============================================================
# 固定 8 个法律条件
# ============================================================

REQUIRED_CONDITIONS = [
    "连续订立二次固定期限劳动合同",
    "存在后续订立的劳动合同",
    "续订劳动合同",
    "劳动者提出或者同意续订、订立劳动合同",
]

EXCLUSION_CONDITIONS = [
    "劳动者存在《劳动合同法》第三十九条规定的情形",
    "劳动者存在《劳动合同法》第四十条第一项规定的情形",
    "劳动者存在《劳动合同法》第四十条第二项规定的情形",
]

EXCEPTION_CONDITIONS = [
    "劳动者提出订立固定期限劳动合同",
]

ALL_CONDITIONS = (
    REQUIRED_CONDITIONS
    + EXCLUSION_CONDITIONS
    + EXCEPTION_CONDITIONS
)


# ============================================================
# 工具函数
# ============================================================

def get_status_map(decision) -> Dict[str, str]:
    """
    将 DecisionResult 中的 8 个 ConditionResult
    转换成：

        {
            condition_name: status
        }

    只读取 Engine 已经产生的 ConditionResult，
    不重新进行任何法律判断。
    """

    result = {}

    for condition_result in decision.condition_results:
        result[condition_result.condition] = (
            condition_result.status
        )

    return result


def get_type_map(decision) -> Dict[str, str]:
    """
    将 8 个条件转换为：

        {
            condition_name: condition_type
        }
    """

    result = {}

    for condition_result in decision.condition_results:
        result[condition_result.condition] = (
            condition_result.condition_type
        )

    return result


def assert_condition_structure(decision) -> None:
    """
    验证固定 8 条条件结构。
    """

    actual_conditions = [
        condition_result.condition
        for condition_result in decision.condition_results
    ]

    assert len(actual_conditions) == 8, (
        "ConditionResult 数量错误："
        f"{len(actual_conditions)}"
    )

    assert set(actual_conditions) == set(ALL_CONDITIONS), (
        "ConditionResult 条件集合错误。\n"
        f"实际：{actual_conditions}\n"
        f"期望：{ALL_CONDITIONS}"
    )

    assert len(set(actual_conditions)) == 8, (
        "ConditionResult 存在重复条件。"
    )


def assert_condition_types(decision) -> None:
    """
    验证：

        REQUIRED   = 4
        EXCLUSION  = 3
        EXCEPTION  = 1
    """

    type_map = get_type_map(decision)

    for condition in REQUIRED_CONDITIONS:
        assert type_map[condition] == "REQUIRED", (
            f"条件类型错误：{condition}"
        )

    for condition in EXCLUSION_CONDITIONS:
        assert type_map[condition] == "EXCLUSION", (
            f"条件类型错误：{condition}"
        )

    for condition in EXCEPTION_CONDITIONS:
        assert type_map[condition] == "EXCEPTION", (
            f"条件类型错误：{condition}"
        )


def assert_contract_sequence(
    decision,
    expected_count: int,
) -> None:
    """
    验证合同序列事实。
    """

    sequence = decision.contract_sequence

    assert sequence is not None, (
        "ContractSequence 不应为 None。"
    )

    assert sequence.count == expected_count, (
        "合同次数错误："
        f"实际={sequence.count}, "
        f"期望={expected_count}"
    )

    assert sequence.term_type == "fixed", (
        "合同类型错误："
        f"{sequence.term_type}"
    )

    assert sequence.continuous is True, (
        "continuous 应为 True。"
    )


def assert_fact_contains(
    decision,
    expected_fact: str,
) -> None:
    """
    验证 Explicit Facts 中包含指定事实。
    """

    assert expected_fact in decision.explicit_facts, (
        "缺少预期 Explicit Fact："
        f"{expected_fact}\n"
        f"实际：{decision.explicit_facts}"
    )


def assert_fact_not_contains(
    decision,
    forbidden_fact: str,
) -> None:
    """
    验证 Explicit Facts 中没有错误生成的事实。

    用于防止：

        合同次数
            ↓
        自动生成“已经续订”

    或：

        合同次数
            ↓
        自动生成“劳动者同意”
    """

    assert forbidden_fact not in decision.explicit_facts, (
        "发现不应存在的 Explicit Fact："
        f"{forbidden_fact}\n"
        f"实际：{decision.explicit_facts}"
    )


def assert_status(
    status_map: Dict[str, str],
    condition: str,
    expected_status: str,
) -> None:
    """
    验证指定法律条件状态。
    """

    actual_status = status_map.get(condition)

    assert actual_status == expected_status, (
        f"条件状态错误：{condition}\n"
        f"实际：{actual_status}\n"
        f"期望：{expected_status}"
    )


def assert_all_statuses(
    status_map: Dict[str, str],
    conditions,
    expected_status: str,
) -> None:
    """
    批量验证条件状态。
    """

    for condition in conditions:
        assert_status(
            status_map,
            condition,
            expected_status,
        )


def print_case_result(
    case_no: str,
    title: str,
    question: str,
    decision,
) -> None:
    """
    打印单个 CASE 的核心结果。
    """

    status_map = get_status_map(decision)

    print()
    print("=" * 70)
    print(f"{case_no}  {title}")
    print("=" * 70)

    print("问题：")
    print(question)

    print()
    print(f"Decision: {decision.decision}")

    if decision.contract_sequence is not None:
        sequence = decision.contract_sequence
        print(
            "Contract Sequence: "
            f"count={sequence.count}, "
            f"term_type={sequence.term_type}, "
            f"continuous={sequence.continuous}"
        )

    print()
    print("Explicit Facts:")

    for fact in decision.explicit_facts:
        print(f"  - {fact}")

    print()
    print("Condition Status:")

    for condition in ALL_CONDITIONS:
        print(
            f"  [{status_map[condition]:15}] "
            f"{condition}"
        )


# ============================================================
# CASE 01
# 三次固定期限合同
# ============================================================

def case_01_three_contracts_only():
    question = (
        "公司连续签订三次固定期限劳动合同。"
    )

    decision = make_decision(question)

    assert_condition_structure(decision)
    assert_condition_types(decision)

    assert decision.decision == "CONDITIONAL"

    assert_contract_sequence(
        decision,
        expected_count=3,
    )

    assert_fact_contains(
        decision,
        "公司连续签订三次固定期限劳动合同",
    )

    assert_fact_not_contains(
        decision,
        "已经续订劳动合同",
    )

    assert_fact_not_contains(
        decision,
        "劳动者明确提出或者同意续订、订立劳动合同",
    )

    status_map = get_status_map(decision)

    assert_status(
        status_map,
        REQUIRED_CONDITIONS[0],
        "SATISFIED",
    )

    assert_status(
        status_map,
        REQUIRED_CONDITIONS[1],
        "SATISFIED",
    )

    assert_status(
        status_map,
        REQUIRED_CONDITIONS[2],
        "UNKNOWN",
    )

    assert_status(
        status_map,
        REQUIRED_CONDITIONS[3],
        "UNKNOWN",
    )

    assert_all_statuses(
        status_map,
        EXCLUSION_CONDITIONS,
        "UNKNOWN",
    )

    assert_status(
        status_map,
        EXCEPTION_CONDITIONS[0],
        "UNKNOWN",
    )

    print_case_result(
        "CASE 01",
        "三次固定期限合同：不能自动推出续订和劳动者同意",
        question,
        decision,
    )


# ============================================================
# CASE 02
# 三次合同 + 已经续订
# ============================================================

def case_02_completed_renewal():
    question = (
        "公司连续签订三次固定期限劳动合同，"
        "之后已经续订劳动合同。"
    )

    decision = make_decision(question)

    assert_condition_structure(decision)
    assert_condition_types(decision)

    assert decision.decision == "CONDITIONAL"

    assert_contract_sequence(
        decision,
        expected_count=3,
    )

    status_map = get_status_map(decision)

    assert_status(
        status_map,
        REQUIRED_CONDITIONS[0],
        "SATISFIED",
    )

    assert_status(
        status_map,
        REQUIRED_CONDITIONS[1],
        "SATISFIED",
    )

    assert_status(
        status_map,
        REQUIRED_CONDITIONS[2],
        "SATISFIED",
    )

    assert_status(
        status_map,
        REQUIRED_CONDITIONS[3],
        "UNKNOWN",
    )

    assert_all_statuses(
        status_map,
        EXCLUSION_CONDITIONS,
        "UNKNOWN",
    )

    assert_status(
        status_map,
        EXCEPTION_CONDITIONS[0],
        "UNKNOWN",
    )

    assert_fact_not_contains(
        decision,
        "劳动者明确提出或者同意续订、订立劳动合同",
    )

    print_case_result(
        "CASE 02",
        "已经续订：不能自动推出劳动者同意",
        question,
        decision,
    )


# ============================================================
# CASE 03
# 三次合同 + 员工同意续订
# ============================================================

def case_03_worker_agreement():
    question = (
        "公司连续签订三次固定期限劳动合同，"
        "员工也同意续订劳动合同。"
    )

    decision = make_decision(question)

    assert_condition_structure(decision)
    assert_condition_types(decision)

    assert decision.decision == "CONDITIONAL"

    assert_contract_sequence(
        decision,
        expected_count=3,
    )

    status_map = get_status_map(decision)

    assert_status(
        status_map,
        REQUIRED_CONDITIONS[0],
        "SATISFIED",
    )

    assert_status(
        status_map,
        REQUIRED_CONDITIONS[1],
        "SATISFIED",
    )

    assert_status(
        status_map,
        REQUIRED_CONDITIONS[2],
        "UNKNOWN",
    )

    assert_status(
        status_map,
        REQUIRED_CONDITIONS[3],
        "SATISFIED",
    )

    assert_all_statuses(
        status_map,
        EXCLUSION_CONDITIONS,
        "UNKNOWN",
    )

    assert_status(
        status_map,
        EXCEPTION_CONDITIONS[0],
        "UNKNOWN",
    )

    assert_fact_not_contains(
        decision,
        "已经续订劳动合同",
    )

    print_case_result(
        "CASE 03",
        "劳动者同意：不能自动推出已经完成续订",
        question,
        decision,
    )


# ============================================================
# CASE 04
# 三次合同 + 已续订 + 劳动者同意
# ============================================================

def case_04_required_all_satisfied():
    question = (
        "公司连续签订三次固定期限劳动合同，"
        "之后已经续订劳动合同，"
        "员工也同意续订劳动合同。"
    )

    decision = make_decision(question)

    assert_condition_structure(decision)
    assert_condition_types(decision)

    assert_contract_sequence(
        decision,
        expected_count=3,
    )

    status_map = get_status_map(decision)

    assert_all_statuses(
        status_map,
        REQUIRED_CONDITIONS,
        "SATISFIED",
    )

    assert_all_statuses(
        status_map,
        EXCLUSION_CONDITIONS,
        "UNKNOWN",
    )

    assert_status(
        status_map,
        EXCEPTION_CONDITIONS[0],
        "UNKNOWN",
    )

    assert decision.decision == "CONDITIONAL"

    print_case_result(
        "CASE 04",
        "四项 REQUIRED 全满足，但排除/例外仍 UNKNOWN",
        question,
        decision,
    )


# ============================================================
# CASE 05
# Article 39 存在
# ============================================================

def case_05_article_39_triggered():
    question = (
        "公司连续签订三次固定期限劳动合同，"
        "之后已经续订劳动合同，"
        "员工也同意续订劳动合同，"
        "劳动者存在《劳动合同法》第三十九条规定的情形。"
    )

    decision = make_decision(question)

    assert_condition_structure(decision)
    assert_condition_types(decision)

    status_map = get_status_map(decision)

    assert_all_statuses(
        status_map,
        REQUIRED_CONDITIONS,
        "SATISFIED",
    )

    assert_status(
        status_map,
        EXCLUSION_CONDITIONS[0],
        "NOT_SATISFIED",
    )

    assert_status(
        status_map,
        EXCLUSION_CONDITIONS[1],
        "UNKNOWN",
    )

    assert_status(
        status_map,
        EXCLUSION_CONDITIONS[2],
        "UNKNOWN",
    )

    assert_status(
        status_map,
        EXCEPTION_CONDITIONS[0],
        "UNKNOWN",
    )

    assert decision.decision == "NOT_ESTABLISHED"

    print_case_result(
        "CASE 05",
        "Article 39 明确存在：排除条件触发",
        question,
        decision,
    )


# ============================================================
# CASE 06
# Article 40(1) 存在
# ============================================================

def case_06_article_40_1_triggered():
    question = (
        "公司连续签订三次固定期限劳动合同，"
        "之后已经续订劳动合同，"
        "员工也同意续订劳动合同，"
        "劳动者存在《劳动合同法》第四十条第一项规定的情形。"
    )

    decision = make_decision(question)

    assert_condition_structure(decision)
    assert_condition_types(decision)

    status_map = get_status_map(decision)

    assert_all_statuses(
        status_map,
        REQUIRED_CONDITIONS,
        "SATISFIED",
    )

    assert_status(
        status_map,
        EXCLUSION_CONDITIONS[0],
        "UNKNOWN",
    )

    assert_status(
        status_map,
        EXCLUSION_CONDITIONS[1],
        "NOT_SATISFIED",
    )

    assert_status(
        status_map,
        EXCLUSION_CONDITIONS[2],
        "UNKNOWN",
    )

    assert_status(
        status_map,
        EXCEPTION_CONDITIONS[0],
        "UNKNOWN",
    )

    assert decision.decision == "NOT_ESTABLISHED"

    print_case_result(
        "CASE 06",
        "Article 40(1) 明确存在：排除条件触发",
        question,
        decision,
    )


# ============================================================
# CASE 07
# Article 40(2) 存在
# ============================================================

def case_07_article_40_2_triggered():
    question = (
        "公司连续签订三次固定期限劳动合同，"
        "之后已经续订劳动合同，"
        "员工也同意续订劳动合同，"
        "劳动者存在《劳动合同法》第四十条第二项规定的情形。"
    )

    decision = make_decision(question)

    assert_condition_structure(decision)
    assert_condition_types(decision)

    status_map = get_status_map(decision)

    assert_all_statuses(
        status_map,
        REQUIRED_CONDITIONS,
        "SATISFIED",
    )

    assert_status(
        status_map,
        EXCLUSION_CONDITIONS[0],
        "UNKNOWN",
    )

    assert_status(
        status_map,
        EXCLUSION_CONDITIONS[1],
        "UNKNOWN",
    )

    assert_status(
        status_map,
        EXCLUSION_CONDITIONS[2],
        "NOT_SATISFIED",
    )

    assert_status(
        status_map,
        EXCEPTION_CONDITIONS[0],
        "UNKNOWN",
    )

    assert decision.decision == "NOT_ESTABLISHED"

    print_case_result(
        "CASE 07",
        "Article 40(2) 明确存在：排除条件触发",
        question,
        decision,
    )


# ============================================================
# CASE 08
# 固定期限劳动合同例外
# ============================================================

def case_08_fixed_term_exception():
    question = (
        "公司连续签订三次固定期限劳动合同，"
        "之后已经续订劳动合同，"
        "员工也同意续订劳动合同，"
        "劳动者提出订立固定期限劳动合同。"
    )

    decision = make_decision(question)

    assert_condition_structure(decision)
    assert_condition_types(decision)

    status_map = get_status_map(decision)

    assert_all_statuses(
        status_map,
        REQUIRED_CONDITIONS,
        "SATISFIED",
    )

    assert_all_statuses(
        status_map,
        EXCLUSION_CONDITIONS,
        "UNKNOWN",
    )

    assert_status(
        status_map,
        EXCEPTION_CONDITIONS[0],
        "NOT_SATISFIED",
    )

    assert decision.decision == "NOT_ESTABLISHED"

    print_case_result(
        "CASE 08",
        "固定期限例外明确触发",
        question,
        decision,
    )


# ============================================================
# CASE 09
# 明确不存在 Article 39 / 40 情形
# ============================================================

def case_09_no_exclusions():
    question = (
        "公司连续签订三次固定期限劳动合同，"
        "之后已经续订劳动合同，"
        "员工也同意续订劳动合同，"
        "不存在劳动合同法第三十九条和"
        "第四十条第一项、第二项规定的情形，"
        "劳动者没有提出订立固定期限劳动合同。"
    )

    decision = make_decision(question)

    assert_condition_structure(decision)
    assert_condition_types(decision)

    status_map = get_status_map(decision)

    assert_all_statuses(
        status_map,
        REQUIRED_CONDITIONS,
        "SATISFIED",
    )

    assert_all_statuses(
        status_map,
        EXCLUSION_CONDITIONS,
        "SATISFIED",
    )

    assert_status(
        status_map,
        EXCEPTION_CONDITIONS[0],
        "SATISFIED",
    )

    assert decision.decision == "DEFINITE"

    print_case_result(
        "CASE 09",
        "完整事实 + 明确不存在排除/例外",
        question,
        decision,
    )


# ============================================================
# CASE 10
# 完整正向闭环
# ============================================================

def case_10_full_definite():
    question = (
        "公司连续签订三次固定期限劳动合同，"
        "之后已经续订劳动合同，"
        "劳动者明确提出或者同意续订、订立劳动合同，"
        "劳动者不存在《劳动合同法》第三十九条规定的情形，"
        "劳动者不存在《劳动合同法》第四十条第一项规定的情形，"
        "劳动者不存在《劳动合同法》第四十条第二项规定的情形，"
        "劳动者没有提出订立固定期限劳动合同。"
    )

    decision = make_decision(question)

    assert_condition_structure(decision)
    assert_condition_types(decision)

    assert_contract_sequence(
        decision,
        expected_count=3,
    )

    status_map = get_status_map(decision)

    # --------------------------------------------------------
    # 四个 REQUIRED
    # --------------------------------------------------------

    assert_all_statuses(
        status_map,
        REQUIRED_CONDITIONS,
        "SATISFIED",
    )

    # --------------------------------------------------------
    # 三个 EXCLUSION
    # --------------------------------------------------------

    assert_all_statuses(
        status_map,
        EXCLUSION_CONDITIONS,
        "SATISFIED",
    )

    # --------------------------------------------------------
    # 一个 EXCEPTION
    # --------------------------------------------------------

    assert_status(
        status_map,
        EXCEPTION_CONDITIONS[0],
        "SATISFIED",
    )

    # --------------------------------------------------------
    # 最终：
    #
    # 8 / 8 SATISFIED
    #
    # → DEFINITE
    # --------------------------------------------------------

    assert decision.decision == "DEFINITE"

    print_case_result(
        "CASE 10",
        "8 条法律条件全部 SATISFIED → DEFINITE",
        question,
        decision,
    )


# ============================================================
# Test Runner
# ============================================================

def main() -> None:
    print()
    print("=" * 70)
    print("RAG V6.1 Fact → Condition Matrix Regression Test")
    print("=" * 70)

    print()
    print("固定条件数量：8")
    print("REQUIRED：4")
    print("EXCLUSION：3")
    print("EXCEPTION：1")

    case_01_three_contracts_only()
    case_02_completed_renewal()
    case_03_worker_agreement()
    case_04_required_all_satisfied()
    case_05_article_39_triggered()
    case_06_article_40_1_triggered()
    case_07_article_40_2_triggered()
    case_08_fixed_term_exception()
    case_09_no_exclusions()
    case_10_full_definite()

    print()
    print("=" * 70)
    print("🎉 RAG V6.1 Fact → Condition Matrix 全部通过")
    print("=" * 70)
    print()
    print("验证完成：")
    print("  ✓ Fact Layer")
    print("  ✓ LegalFacts")
    print("  ✓ Fact → Condition Mapping")
    print("  ✓ 8 条 ConditionResult")
    print("  ✓ UNKNOWN 不被错误升级")
    print("  ✓ EXCLUSION 触发逻辑")
    print("  ✓ EXCEPTION 触发逻辑")
    print("  ✓ 完整事实 → DEFINITE")
    print()


if __name__ == "__main__":
    main()
