# -*- coding: utf-8 -*-

"""
RAG V6.1
Fact → Condition Adversarial Regression Test

============================================================
测试目标
============================================================

本测试不是验证“正常事实组合是否能够得到正确结论”。

正常组合已经由：

    tests/test_fact_condition_matrix.py

负责。

本测试专门攻击 Fact Layer → Condition Layer 之间的边界，
验证系统不能进行非法的反向推理、事实污染和 UNKNOWN 升级。

核心不变量：

    1. 三次固定期限合同
       不能推出“已经完成续订”

    2. 劳动者同意续订
       不能推出“已经完成续订”

    3. 已经完成续订
       不能推出“劳动者同意续订”

    4. 不存在《劳动合同法》第三十九条情形
       只能影响 Article 39 EXCLUSION

    5. Article 39 的明确事实
       不能污染 Article 40(1)、Article 40(2)

    6. UNKNOWN
       不能被后续层升级为 SATISFIED

    7. UNKNOWN
       不能被后续层升级为 NOT_SATISFIED

    8. 任何单一事实都不能跨字段污染 LegalFacts

============================================================
测试链路
============================================================

Natural Language
      ↓
Legal Fact Extractor
      ↓
LegalFacts
      ↓
Legal Decision Engine
      ↓
ConditionResult
      ↓
DecisionResult

本文件只测试 Fact → Condition 边界。

不测试 Ollama。

不依赖 LLM。

============================================================
运行方式
============================================================

    PYTHONPATH=. python tests/test_fact_condition_adversarial.py

============================================================
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Tuple

from src.legal_fact_extractor import extract_legal_facts
from src.legal_decision_engine import make_decision


# ============================================================
# 固定条件名称
# ============================================================

REQUIRED_1 = "连续订立二次固定期限劳动合同"
REQUIRED_2 = "存在后续订立的劳动合同"
REQUIRED_3 = "续订劳动合同"
REQUIRED_4 = "劳动者提出或者同意续订、订立劳动合同"

EXCLUSION_39 = "劳动者存在《劳动合同法》第三十九条规定的情形"
EXCLUSION_40_1 = "劳动者存在《劳动合同法》第四十条第一项规定的情形"
EXCLUSION_40_2 = "劳动者存在《劳动合同法》第四十条第二项规定的情形"

EXCEPTION_FIXED = "劳动者提出订立固定期限劳动合同"


ALL_CONDITIONS = [
    REQUIRED_1,
    REQUIRED_2,
    REQUIRED_3,
    REQUIRED_4,
    EXCLUSION_39,
    EXCLUSION_40_1,
    EXCLUSION_40_2,
    EXCEPTION_FIXED,
]


# ============================================================
# 通用辅助函数
# ============================================================

def _status_name(status: Any) -> str:
    """
    兼容 ConditionStatus 枚举以及字符串状态。

    当前系统的状态核心是：

        SATISFIED
        UNKNOWN
        NOT_SATISFIED

    测试不依赖具体 Enum 实现方式。
    """
    if status is None:
        return ""

    value = getattr(status, "value", None)

    if isinstance(value, str):
        return value

    name = getattr(status, "name", None)

    if isinstance(name, str):
        return name

    return str(status)


def _condition_results(decision: Any) -> List[Any]:
    """
    获取 DecisionResult.condition_results。

    兼容对象属性不存在时的显式失败。
    """
    results = getattr(decision, "condition_results", None)

    if results is None:
        raise AssertionError(
            "DecisionResult 缺少 condition_results，"
            "无法进行 Fact → Condition 对抗测试。"
        )

    return list(results)


def _find_condition(
    decision: Any,
    condition_name: str,
) -> Any:
    """
    按 ConditionResult.condition 查找指定条件。

    注意：
        ConditionResult 的真实字段名是：

            condition

        不是：

            condition_name
    """
    results = _condition_results(decision)

    for result in results:
        name = getattr(result, "condition", None)

        if name == condition_name:
            return result

    available = [
        getattr(result, "condition", None)
        for result in results
    ]

    raise AssertionError(
        f"未找到条件：{condition_name}\n"
        f"当前条件：{available}"
    )

def _condition_status(
    decision: Any,
    condition_name: str,
) -> str:
    """
    获取指定条件的标准状态名称。
    """
    result = _find_condition(decision, condition_name)

    status = getattr(result, "status", None)

    if status is None:
        raise AssertionError(
            f"ConditionResult 缺少 status：{condition_name}"
        )

    return _status_name(status)


def _assert_status(
    decision: Any,
    condition_name: str,
    expected: str,
) -> None:
    """
    断言指定 ConditionResult 状态。
    """
    actual = _condition_status(
        decision,
        condition_name,
    )

    if actual != expected:
        raise AssertionError(
            f"条件状态错误：\n"
            f"条件：{condition_name}\n"
            f"期望：{expected}\n"
            f"实际：{actual}"
        )


def _assert_fact_none(
    facts: Any,
    field_name: str,
) -> None:
    """
    断言 LegalFacts 某字段保持 None。
    """
    actual = getattr(facts, field_name, None)

    if actual is not None:
        raise AssertionError(
            f"事实污染：{field_name} 应为 None，"
            f"实际为 {actual!r}"
        )


def _assert_fact_true(
    facts: Any,
    field_name: str,
) -> None:
    """
    断言 LegalFacts 某字段为 True。
    """
    actual = getattr(facts, field_name, None)

    if actual is not True:
        raise AssertionError(
            f"事实提取错误：{field_name} "
            f"应为 True，实际为 {actual!r}"
        )


def _assert_fact_false(
    facts: Any,
    field_name: str,
) -> None:
    """
    断言 LegalFacts 某字段为 False。
    """
    actual = getattr(facts, field_name, None)

    if actual is not False:
        raise AssertionError(
            f"事实提取错误：{field_name} "
            f"应为 False，实际为 {actual!r}"
        )


def _assert_decision_state(
    decision: Any,
    expected: str,
) -> None:
    """
    断言 DecisionResult.engine_decision。
    """
    actual = getattr(decision, "decision", None)

    if actual is None:
        actual = getattr(decision, "engine_decision", None)

    actual_name = _status_name(actual)

    if actual_name != expected:
        raise AssertionError(
            f"DecisionResult 判定错误："
            f"期望 {expected}，实际 {actual_name}"
        )


def _assert_all_unknown_except(
    decision: Any,
    exceptions: Iterable[str],
) -> None:
    """
    检查除指定条件外，其余条件全部保持 UNKNOWN。

    用于验证：

        单一事实
        ↓
        只能影响对应条件

    而不能污染其它条件。
    """
    allowed = set(exceptions)

    for condition_name in ALL_CONDITIONS:
        if condition_name in allowed:
            continue

        actual = _condition_status(
            decision,
            condition_name,
        )

        if actual != "UNKNOWN":
            raise AssertionError(
                f"条件污染：\n"
                f"条件：{condition_name}\n"
                f"实际状态：{actual}\n"
                f"期望：UNKNOWN"
            )


def _print_case(
    number: int,
    title: str,
) -> None:
    print()
    print("=" * 70)
    print(f"CASE {number:02d}: {title}")
    print("=" * 70)


# ============================================================
# CASE 01
# 三次固定期限合同不能推出“已经完成续订”
# ============================================================

def test_case_01_three_contracts_not_completed_renewal() -> None:
    _print_case(
        1,
        "三次固定期限合同不能推出已经完成续订",
    )

    question = (
        "公司连续签订三次固定期限劳动合同。"
    )

    facts = extract_legal_facts(question)

    sequence = facts.contract_sequence

    if sequence is None:
        raise AssertionError(
            "三次固定期限合同没有提取出 contract_sequence"
        )

    if sequence.count != 3:
        raise AssertionError(
            f"contract_sequence.count 应为 3，"
            f"实际为 {sequence.count}"
        )

    if sequence.term_type != "fixed":
        raise AssertionError(
            f"term_type 应为 fixed，"
            f"实际为 {sequence.term_type}"
        )

    if sequence.continuous is not True:
        raise AssertionError(
            "continuous 应为 True"
        )

    _assert_fact_none(
        facts,
        "completed_renewal",
    )

    _assert_fact_none(
        facts,
        "worker_agreement",
    )

    decision = make_decision(question)

    _assert_status(
        decision,
        REQUIRED_1,
        "SATISFIED",
    )

    _assert_status(
        decision,
        REQUIRED_2,
        "SATISFIED",
    )

    _assert_status(
        decision,
        REQUIRED_3,
        "UNKNOWN",
    )

    _assert_status(
        decision,
        REQUIRED_4,
        "UNKNOWN",
    )

    _assert_all_unknown_except(
        decision,
        {
            REQUIRED_1,
            REQUIRED_2,
        },
    )

    print("PASS")


# ============================================================
# CASE 02
# 劳动者同意续订不能推出“已经完成续订”
# ============================================================

def test_case_02_agreement_not_completed_renewal() -> None:
    _print_case(
        2,
        "劳动者同意续订不能推出已经完成续订",
    )

    question = (
        "公司连续签订三次固定期限劳动合同，"
        "劳动者同意续订劳动合同。"
    )

    facts = extract_legal_facts(question)

    _assert_fact_true(
        facts,
        "worker_agreement",
    )

    _assert_fact_none(
        facts,
        "completed_renewal",
    )

    decision = make_decision(question)

    _assert_status(
        decision,
        REQUIRED_1,
        "SATISFIED",
    )

    _assert_status(
        decision,
        REQUIRED_2,
        "SATISFIED",
    )

    _assert_status(
        decision,
        REQUIRED_3,
        "UNKNOWN",
    )

    _assert_status(
        decision,
        REQUIRED_4,
        "SATISFIED",
    )

    print("PASS")


# ============================================================
# CASE 03
# 已完成续订不能推出劳动者同意
# ============================================================

def test_case_03_completed_renewal_not_worker_agreement() -> None:
    _print_case(
        3,
        "已经完成续订不能推出劳动者同意",
    )

    question = (
        "公司连续签订三次固定期限劳动合同，"
        "双方已经完成劳动合同续订。"
    )

    facts = extract_legal_facts(question)

    _assert_fact_true(
        facts,
        "completed_renewal",
    )

    _assert_fact_none(
        facts,
        "worker_agreement",
    )

    decision = make_decision(question)

    _assert_status(
        decision,
        REQUIRED_1,
        "SATISFIED",
    )

    _assert_status(
        decision,
        REQUIRED_2,
        "SATISFIED",
    )

    _assert_status(
        decision,
        REQUIRED_3,
        "SATISFIED",
    )

    _assert_status(
        decision,
        REQUIRED_4,
        "UNKNOWN",
    )

    print("PASS")


# ============================================================
# CASE 04
# 三次合同 + 完成续订
# 不能自动得到劳动者同意
# ============================================================

def test_case_04_completed_renewal_does_not_imply_agreement() -> None:
    _print_case(
        4,
        "完成续订不能自动推出劳动者同意",
    )

    question = (
        "公司连续签订三次固定期限劳动合同，"
        "已经完成劳动合同续订。"
    )

    facts = extract_legal_facts(question)

    _assert_fact_true(
        facts,
        "completed_renewal",
    )

    _assert_fact_none(
        facts,
        "worker_agreement",
    )

    decision = make_decision(question)

    _assert_status(
        decision,
        REQUIRED_3,
        "SATISFIED",
    )

    _assert_status(
        decision,
        REQUIRED_4,
        "UNKNOWN",
    )

    if _condition_status(decision, REQUIRED_4) == "SATISFIED":
        raise AssertionError(
            "反向事实推理错误："
            "completed_renewal 不得推出 worker_agreement"
        )

    print("PASS")


# ============================================================
# CASE 05
# 同意续订不能推出已经完成续订
# 使用完整法律表达再次攻击
# ============================================================

def test_case_05_legal_wording_agreement_not_renewal() -> None:
    _print_case(
        5,
        "完整法律表述中的同意续订不能推出已经完成续订",
    )

    question = (
        "公司连续签订三次固定期限劳动合同，"
        "劳动者明确提出或者同意续订、订立劳动合同。"
    )

    facts = extract_legal_facts(question)

    _assert_fact_true(
        facts,
        "worker_agreement",
    )

    _assert_fact_none(
        facts,
        "completed_renewal",
    )

    decision = make_decision(question)

    _assert_status(
        decision,
        REQUIRED_4,
        "SATISFIED",
    )

    _assert_status(
        decision,
        REQUIRED_3,
        "UNKNOWN",
    )

    print("PASS")


# ============================================================
# CASE 06
# Article 39 否定事实只能影响 Article 39 EXCLUSION
# ============================================================

def test_case_06_article_39_negative_does_not_contaminate_other_exclusions() -> None:
    _print_case(
        6,
        "Article 39 不存在只能影响 Article 39 EXCLUSION",
    )

    question = (
        "公司连续签订三次固定期限劳动合同，"
        "劳动者不存在《劳动合同法》第三十九条规定的情形。"
    )

    facts = extract_legal_facts(question)

    _assert_fact_false(
        facts,
        "article_39",
    )

    _assert_fact_none(
        facts,
        "article_40_1",
    )

    _assert_fact_none(
        facts,
        "article_40_2",
    )

    decision = make_decision(question)

    _assert_status(
        decision,
        EXCLUSION_39,
        "NOT_SATISFIED",
    )

    _assert_status(
        decision,
        EXCLUSION_40_1,
        "UNKNOWN",
    )

    _assert_status(
        decision,
        EXCLUSION_40_2,
        "UNKNOWN",
    )

    print("PASS")


# ============================================================
# CASE 07
# Article 39 否定事实不能推出 DEFINITE
# ============================================================

def test_case_07_single_negative_exclusion_fact_not_definite() -> None:
    _print_case(
        7,
        "单独确认 Article 39 不存在不能直接得到 DEFINITE",
    )

    question = (
        "公司连续签订三次固定期限劳动合同，"
        "劳动者不存在《劳动合同法》第三十九条规定的情形。"
    )

    facts = extract_legal_facts(question)

    _assert_fact_false(
        facts,
        "article_39",
    )

    decision = make_decision(question)

    _assert_status(
        decision,
        EXCLUSION_39,
        "NOT_SATISFIED",
    )

    _assert_status(
        decision,
        EXCLUSION_40_1,
        "UNKNOWN",
    )

    _assert_status(
        decision,
        EXCLUSION_40_2,
        "UNKNOWN",
    )

    _assert_status(
        decision,
        EXCEPTION_FIXED,
        "UNKNOWN",
    )

    _assert_decision_state(
        decision,
        "CONDITIONAL",
    )

    print("PASS")


# ============================================================
# CASE 08
# UNKNOWN 条件保持 UNKNOWN
# ============================================================

def test_case_08_unknown_conditions_never_upgrade() -> None:
    _print_case(
        8,
        "UNKNOWN 条件不得升级为 SATISFIED 或 NOT_SATISFIED",
    )

    question = (
        "公司连续签订三次固定期限劳动合同。"
    )

    decision = make_decision(question)

    unknown_conditions = [
        REQUIRED_3,
        REQUIRED_4,
        EXCLUSION_39,
        EXCLUSION_40_1,
        EXCLUSION_40_2,
        EXCEPTION_FIXED,
    ]

    for condition_name in unknown_conditions:
        actual = _condition_status(
            decision,
            condition_name,
        )

        if actual != "UNKNOWN":
            raise AssertionError(
                f"UNKNOWN 升级错误：\n"
                f"条件：{condition_name}\n"
                f"实际：{actual}\n"
                f"期望：UNKNOWN"
            )

    _assert_decision_state(
        decision,
        "CONDITIONAL",
    )

    print("PASS")


# ============================================================
# 额外边界检查
# ============================================================

def test_no_cross_field_contamination() -> None:
    """
    对 LegalFacts 做最终字段隔离检查。

    三种核心事实之间不能互相生成：

        contract_sequence
        completed_renewal
        worker_agreement
    """

    print()
    print("=" * 70)
    print("FACT ISOLATION CHECK")
    print("=" * 70)

    cases: List[Tuple[str, str]] = [
        (
            "公司连续签订三次固定期限劳动合同。",
            "contract_sequence",
        ),
        (
            "劳动者同意续订劳动合同。",
            "worker_agreement",
        ),
        (
            "双方已经完成劳动合同续订。",
            "completed_renewal",
        ),
    ]

    for question, source_field in cases:
        facts = extract_legal_facts(question)

        fields = [
            "contract_sequence",
            "completed_renewal",
            "worker_agreement",
        ]

        for field_name in fields:
            if field_name == source_field:
                continue

            actual = getattr(
                facts,
                field_name,
                None,
            )

            if actual is not None:
                raise AssertionError(
                    f"事实字段污染：\n"
                    f"问题：{question}\n"
                    f"来源字段：{source_field}\n"
                    f"污染字段：{field_name}\n"
                    f"实际值：{actual!r}"
                )

    print("PASS")


# ============================================================
# 主测试入口
# ============================================================

def main() -> None:
    print()
    print("=" * 70)
    print("RAG V6.1 Fact → Condition Adversarial Test")
    print("=" * 70)
    print()
    print("测试目标：")
    print("  Fact → LegalFacts → ConditionResult")
    print()
    print("核心原则：")
    print("  三次合同 ≠ 已完成续订")
    print("  同意续订 ≠ 已完成续订")
    print("  已完成续订 ≠ 劳动者同意")
    print("  Article 39 否定事实 ≠ 其它排除条件")
    print("  UNKNOWN ≠ SATISFIED")
    print("  UNKNOWN ≠ NOT_SATISFIED")

    test_case_01_three_contracts_not_completed_renewal()
    test_case_02_agreement_not_completed_renewal()
    test_case_03_completed_renewal_not_worker_agreement()
    test_case_04_completed_renewal_does_not_imply_agreement()
    test_case_05_legal_wording_agreement_not_renewal()
    test_case_06_article_39_negative_does_not_contaminate_other_exclusions()
    test_case_07_single_negative_exclusion_fact_not_definite()
    test_case_08_unknown_conditions_never_upgrade()
    test_no_cross_field_contamination()

    print()
    print("=" * 70)
    print("🎉 RAG V6.1 Fact → Condition Adversarial Test 全部通过")
    print("=" * 70)
    print()
    print("验证完成：")
    print("  ✓ 三次合同不会伪造 completed_renewal")
    print("  ✓ worker_agreement 不会伪造 completed_renewal")
    print("  ✓ completed_renewal 不会伪造 worker_agreement")
    print("  ✓ Article 39 不会污染 Article 40")
    print("  ✓ 单一排除事实不会直接产生 DEFINITE")
    print("  ✓ UNKNOWN 状态保持 UNKNOWN")
    print("  ✓ LegalFacts 字段之间不存在交叉污染")


if __name__ == "__main__":
    main()