# -*- coding: utf-8 -*-

"""
RAG V7
Reverse Status Protection Regression Test

测试目标：
1. 已确定的 EXCLUSION 条件，不得被答案重新描述为待确认。
2. 已确定的 EXCEPTION 条件，不得被答案重新描述为待确认。
3. 其他行的空 UNKNOWN 列表标题，不得错误关联到已确定条件。
4. 没有 UNKNOWN 条件时，合法的空列表标题必须通过。

本测试只调用 Validator，不启动完整 RAG，不调用 Ollama。
"""

from src.legal_condition_validator import (
    validate_unknown_conditions,
    _find_condition_text_position,
)
from src.legal_decision_engine import EXCLUSION, EXCEPTION
from src.legal_constants import NOT_SATISFIED, SATISFIED, UNKNOWN


def build_decision(condition_results):
    """构造最小化 Decision 输入。"""
    return {
        "condition_results": condition_results,
    }


def build_condition(condition, condition_type, status):
    """构造单条条件结果。"""
    return {
        "condition": condition,
        "condition_type": condition_type,
        "status": status,
    }


def run_case(name, answer, decision, expected):
    """执行一个断言并打印结果。"""
    actual = validate_unknown_conditions(answer, decision)

    if actual != expected:
        raise AssertionError(
            f"{name}：预期 {expected}，实际 {actual}"
        )

    print(f"PASS: {name}")


def main():
    exclusion_condition = "不存在劳动合同法第三十九条规定的情形"
    exception_condition = "劳动者未提出订立固定期限劳动合同"

    # --------------------------------------------------------
    # CASE 01：
    # EXCLUSION 已为 NOT_SATISFIED，
    # 不能在同一行又将其描述为无法确认。
    # --------------------------------------------------------
    decision_01 = build_decision([
        build_condition(
            exclusion_condition,
            EXCLUSION,
            NOT_SATISFIED,
        ),
        build_condition(
            "续订劳动合同",
            "REQUIRED",
            UNKNOWN,
        ),
    ])

    answer_01 = (
        "第三十九条规定的情形无法确认。\n"
        "尚未确认条件：续订劳动合同。"
    )

    run_case(
        "CASE 01 同一行的排除条件状态反转必须拦截",
        answer_01,
        decision_01,
        False,
    )

    # --------------------------------------------------------
    # CASE 02：
    # EXCEPTION 已为 NOT_SATISFIED，
    # 不能在同一行又描述为待核实。
    # --------------------------------------------------------
    decision_02 = build_decision([
        build_condition(
            exception_condition,
            EXCEPTION,
            NOT_SATISFIED,
        ),
        build_condition(
            "续订劳动合同",
            "REQUIRED",
            UNKNOWN,
        ),
    ])

    answer_02 = (
        "劳动者提出订立固定期限劳动合同的例外情形待核实。\n"
        "尚未确认条件：续订劳动合同。"
    )

    run_case(
        "CASE 02 同一行的例外条件状态反转必须拦截",
        answer_02,
        decision_02,
        False,
    )

    # --------------------------------------------------------
    # CASE 03：
    # 空 UNKNOWN 列表标题在另一行，
    # 不得错误关联到已经确定的排除条件。
    # --------------------------------------------------------
    decision_03 = build_decision([
        build_condition(
            exclusion_condition,
            EXCLUSION,
            NOT_SATISFIED,
        ),
        build_condition(
            "续订劳动合同",
            "REQUIRED",
            UNKNOWN,
        ),
    ])

    answer_03 = (
        "第三十九条规定的情形不成立。\n"
        "尚未确认条件：无。\n"
        "尚未确认条件：续订劳动合同。"
    )

    run_case(
        "CASE 03 空列表标题不应触发反向状态保护",
        answer_03,
        decision_03,
        True,
    )

    # --------------------------------------------------------
    # CASE 04：
    # 没有任何 UNKNOWN 条件时，
    # “尚未确认条件：无”应当通过。
    # --------------------------------------------------------
    decision_04 = build_decision([
        build_condition(
            exclusion_condition,
            EXCLUSION,
            NOT_SATISFIED,
        ),
    ])

    answer_04 = (
        "第三十九条规定的情形不成立。\n"
        "尚未确认条件：- 无。"
    )

    run_case(
        "CASE 04 无 UNKNOWN 时允许合法空列表标题",
        answer_04,
        decision_04,
        True,
    )

    # --------------------------------------------------------
    # CASE 05：
    # 合法的 UNKNOWN 自然语言表达应当通过。
    # --------------------------------------------------------
    decision_05 = build_decision([
        build_condition(
            "续订劳动合同",
            "REQUIRED",
            UNKNOWN,
        ),
    ])

    answer_05 = "续订劳动合同这一条件是否满足，目前尚不能确认。"

    run_case(
        "CASE 05 合法 UNKNOWN 表达应当通过",
        answer_05,
        decision_05,
        True,
    )

    # --------------------------------------------------------
    # CASE 06：
    # 同一 UNKNOWN 条件附近出现明确 SATISFIED 状态，
    # 不能因为同时存在“尚不能确认”而放过。
    # --------------------------------------------------------
    decision_06 = build_decision([
        build_condition(
            "续订劳动合同",
            "REQUIRED",
            UNKNOWN,
        ),
    ])

    answer_06 = (
        "续订劳动合同这一条件目前尚不能确认。\n"
        "状态：SATISFIED"
    )

    run_case(
        "CASE 06 明确 SATISFIED 不得被 UNKNOWN 掩盖",
        answer_06,
        decision_06,
        False,
    )

    # --------------------------------------------------------
    # CASE 07：
    # 不同法律条件的状态必须相互隔离。
    # 第三十九条 UNKNOWN 不得被第四十条第一项的
    # SATISFIED 状态错误影响。
    # --------------------------------------------------------
    decision_07 = build_decision([
        build_condition(
            "劳动者存在《劳动合同法》第三十九条规定的情形",
            "EXCLUSION",
            UNKNOWN,
        ),
        build_condition(
            "劳动者存在《劳动合同法》第四十条第一项规定的情形",
            "EXCLUSION",
            "SATISFIED",
        ),
        build_condition(
            "续订劳动合同",
            "REQUIRED",
            UNKNOWN,
        ),
    ])

    answer_07 = (
        "劳动者存在《劳动合同法》第三十九条规定的情形，目前尚不能确认。\n"
        "劳动者存在《劳动合同法》第四十条第一项规定的情形，状态：SATISFIED。\n"
        "续订劳动合同这一条件是否满足，目前尚不能确认。"
    )

    run_case(
        "CASE 07 不同法律条件的状态必须相互隔离",
        answer_07,
        decision_07,
        True,
    )

    # --------------------------------------------------------
    # CASE 08：
    # 长法律条件不能仅凭前六个字符被视为已覆盖。
    # 即使答案含有 UNKNOWN，也必须拒绝不完整的条件表达。
    # --------------------------------------------------------
    decision_08 = build_decision([
        build_condition(
            "连续订立二次固定期限劳动合同",
            "REQUIRED",
            UNKNOWN,
        ),
    ])

    answer_08 = "连续订立二次，其他条件状态为 UNKNOWN。"

    run_case(
        "CASE 08 长条件短前缀不得被视为已覆盖",
        answer_08,
        decision_08,
        False,
    )

    # --------------------------------------------------------
    # CASE 09：
    # 完整条件加 UNKNOWN 标记应当正常通过。
    # --------------------------------------------------------
    answer_09 = "连续订立二次固定期限劳动合同，目前状态为 UNKNOWN。"

    run_case(
        "CASE 09 完整条件加 UNKNOWN 标记应当通过",
        answer_09,
        decision_08,
        True,
    )

    # --------------------------------------------------------
    # CASE 10：
    # 已知的短条件“续订劳动合同”仍应正常匹配。
    # --------------------------------------------------------
    decision_10 = build_decision([
        build_condition(
            "续订劳动合同",
            "REQUIRED",
            UNKNOWN,
        ),
    ])

    answer_10 = "续订劳动合同，目前状态为 UNKNOWN。"

    run_case(
        "CASE 10 合法短条件加 UNKNOWN 标记应当通过",
        answer_10,
        decision_10,
        True,
    )

    # --------------------------------------------------------
    # CASE 11：
    # 多个 UNKNOWN 条件中，一个条件被明确描述为 SATISFIED，
    # 不能因为另一个条件仍然未确认而通过验证。
    # --------------------------------------------------------

    decision_11 = build_decision([
        build_condition(
            "连续订立二次固定期限劳动合同",
            "REQUIRED",
            UNKNOWN,
        ),
        build_condition(
            "续订劳动合同",
            "REQUIRED",
            UNKNOWN,
        ),
    ])

    answer_11 = (
        "连续订立二次固定期限劳动合同，状态：SATISFIED。\\n"
        "续订劳动合同这一条件目前尚不能确认。"
    )

    run_case(
        "CASE 11 全局未决标记不得掩盖其他条件的 SATISFIED 状态",
        answer_11,
        decision_11,
        False,
    )

    # --------------------------------------------------------
    # CASE 12：
    # 同一行的两个 UNKNOWN 条件具有不同状态描述。
    #
    # 条件 A 被明确写成 SATISFIED；
    # 条件 B 仍然是 UNKNOWN。
    #
    # 条件 B 的未决语义不能掩盖条件 A 的状态反转。
    # --------------------------------------------------------

    decision_12 = build_decision([
        build_condition(
            "连续订立二次固定期限劳动合同",
            "REQUIRED",
            UNKNOWN,
        ),
        build_condition(
            "续订劳动合同",
            "REQUIRED",
            UNKNOWN,
        ),
    ])

    answer_12 = (
        "连续订立二次固定期限劳动合同已满足；"
        "续订劳动合同尚未确认。"
    )

    run_case(
        "CASE 12 同一行不同条件的状态必须独立判断",
        answer_12,
        decision_12,
        False,
    )

    # --------------------------------------------------------
    # CASE 13：
    # 同一个 UNKNOWN 条件在答案中重复出现。
    # 第一次正确标记为 UNKNOWN，第二次却明确标记为 SATISFIED。
    # 第一次出现的合法状态不能掩盖第二次出现的状态反转。
    # --------------------------------------------------------
    decision_13 = build_decision([
        build_condition(
            "续订劳动合同",
            "REQUIRED",
            UNKNOWN,
        ),
    ])

    answer_13 = (
        "续订劳动合同，目前状态为 UNKNOWN。\\n"
        "续订劳动合同，状态：SATISFIED。"
    )

    run_case(
        "CASE 13 同一条件重复出现时必须拦截状态反转",
        answer_13,
        decision_13,
        False,
    )

    # --------------------------------------------------------
    # CASE 14：
    # 状态标签单独占一行时，不得将另一个条件的 UNKNOWN
    # 当作当前条件的未决语义。
    # --------------------------------------------------------
    decision_14 = build_decision([
        build_condition(
            "连续订立二次固定期限劳动合同",
            "REQUIRED",
            UNKNOWN,
        ),
        build_condition(
            "续订劳动合同",
            "REQUIRED",
            UNKNOWN,
        ),
    ])

    answer_14 = (
        "连续订立二次固定期限劳动合同\\n"
        "状态：SATISFIED\\n"
        "续订劳动合同\\n"
        "状态：UNKNOWN"
    )

    run_case(
        "CASE 14 独立状态标签不得跨条件掩盖状态反转",
        answer_14,
        decision_14,
        False,
    )

    # --------------------------------------------------------
    # CASE 15：
    # 当前条件具有较短的法律关键词识别片段。
    # 其他条件插入在该片段与当前条件的明确状态之间时，
    # 不能因为局部范围提前结束而漏掉状态反转。
    # --------------------------------------------------------
    decision_15 = build_decision([
        build_condition(
            "劳动者提出或者同意续订、订立劳动合同",
            "REQUIRED",
            UNKNOWN,
        ),
        build_condition(
            "劳动者提出订立固定期限劳动合同",
            "EXCEPTION",
            UNKNOWN,
        ),
    ])

    answer_15 = (
        "劳动者提出或者同意续订；"
        "劳动者提出订立固定期限劳动合同尚未确认；"
        "劳动者提出或者同意续订、订立劳动合同已满足。"
    )

    run_case(
        "CASE 15 短识别片段不能导致状态反转漏检",
        answer_15,
        decision_15,
        False,
    )

    # --------------------------------------------------------
    # CASE 16：
    # 多个分号分隔不同句段时，前一个已满足条件的状态
    # 不得污染后一个 UNKNOWN 条件的判断。
    # --------------------------------------------------------
    decision_16 = build_decision([
        build_condition(
            "连续订立二次固定期限劳动合同",
            "REQUIRED",
            SATISFIED,
        ),
        build_condition(
            "续订劳动合同",
            "REQUIRED",
            UNKNOWN,
        ),
    ])

    answer_16 = (
        "连续订立二次固定期限劳动合同已满足；"
        "其他事项已满足；"
        "续订劳动合同尚未确认。"
    )

    run_case(
        "CASE 16 多个句段分隔符不得造成跨条件状态污染",
        answer_16,
        decision_16,
        True,
    )

    print()
    print("PASS: Reverse Status Protection Regression Test")


    # --------------------------------------------------------
    # CASE 17：
    # 四个 Engine UNKNOWN 只明确表达其中两个。
    # 全局未决表达不能替代逐条件覆盖检查。
    # --------------------------------------------------------
    decision_17 = build_decision([
        build_condition(
            "连续订立二次固定期限劳动合同",
            "REQUIRED",
            UNKNOWN,
        ),
        build_condition(
            "续订劳动合同",
            "REQUIRED",
            UNKNOWN,
        ),
        build_condition(
            "劳动者提出或者同意续订、订立劳动合同",
            "REQUIRED",
            UNKNOWN,
        ),
        build_condition(
            "不存在劳动合同法第三十九条规定的情形",
            "EXCLUSION",
            UNKNOWN,
        ),
    ])

    answer_17 = (
        "连续订立二次固定期限劳动合同尚未确认；"
        "续订劳动合同尚未确认。"
        "其他事项仍需结合具体事实判断。"
    )

    run_case(
        "CASE 17 多个 UNKNOWN 不得因部分覆盖和全局未决标记而放行",
        answer_17,
        decision_17,
        False,
    )



    # --------------------------------------------------------
    # CASE 18：
    # 条件名称含顿号时，仍须正确定位原文边界并拦截状态反转。
    # --------------------------------------------------------
    decision_18 = build_decision([
        build_condition(
            "劳动者提出或者同意续订、订立劳动合同",
            "REQUIRED",
            UNKNOWN,
        ),
        build_condition(
            "劳动者提出订立固定期限劳动合同",
            "EXCEPTION",
            UNKNOWN,
        ),
    ])

    answer_18 = (
        "劳动者提出订立固定期限劳动合同尚未确认；"
        "劳动者提出或者同意续订、订立劳动合同已满足。"
    )

    run_case(
        "CASE 18 条件名称含顿号时仍须拦截状态反转",
        answer_18,
        decision_18,
        False,
    )


def test_reverse_status_protection_main_cases():
    """通过 pytest 自动执行 main() 中的 CASE 01–18。"""
    main()


def test_condition_position_sentence_boundaries():
    """分号和句号必须阻止跨句段拼接匹配。"""
    cases = [
        ("甲条件；乙条件", "甲乙"),
        ("甲条件。乙条件", "甲乙"),
    ]

    for line_text, condition_text in cases:
        actual = _find_condition_text_position(
            line_text,
            condition_text,
        )
        if actual is not None:
            raise AssertionError(
                f"跨句段匹配不应成功：{line_text!r} -> {actual!r}"
            )

    print("PASS: CASE 19 分号和句号不得被跨越匹配")


def test_condition_position_internal_punctuation():
    """条件名内部的顿号差异应允许匹配，偏移量仍对应原文。"""
    line_text = "前缀；劳动者提出或者同意续订、订立劳动合同已满足。"
    condition_text = "劳动者提出或者同意续订订立劳动合同"

    actual = _find_condition_text_position(
        line_text,
        condition_text,
    )
    expected_start = line_text.index("劳动者提出或者同意续订")
    expected_end = (
        line_text.index("劳动合同", expected_start)
        + len("劳动合同")
    )

    if actual != (expected_start, expected_end):
        raise AssertionError(
            f"标点容错或原文偏移错误：预期 "
            f"{(expected_start, expected_end)!r}，实际 {actual!r}"
        )

    print("PASS: CASE 20 条件内部标点容错且返回原文偏移量")


def test_condition_position_repeated_text():
    """start 应使搜索定位到后一次重复条件。"""
    line_text = "续订劳动合同已满足；续订劳动合同尚未确认"
    condition_text = "续订劳动合同"

    first = _find_condition_text_position(
        line_text,
        condition_text,
    )
    second_start = first[1] if first is not None else 0
    second = _find_condition_text_position(
        line_text,
        condition_text,
        start=second_start,
    )

    expected_second = line_text.rindex(condition_text)
    if second != (
        expected_second,
        expected_second + len(condition_text),
    ):
        raise AssertionError(
            f"重复条件定位错误：实际 {second!r}"
        )

    print("PASS: CASE 21 start 参数应定位后一次重复条件")


def test_comma_separated_unknown_does_not_pollute_satisfied():
    """前一个 UNKNOWN 条件的状态不得污染后一个 SATISFIED 条件。"""
    decision = build_decision([
        build_condition("条件甲", "REQUIRED", UNKNOWN),
        build_condition("条件乙", "REQUIRED", SATISFIED),
    ])

    answer = "条件甲尚未确认，条件乙已满足。"

    run_case(
        "CASE 22 逗号分隔时 UNKNOWN 不得污染后一个 SATISFIED 条件",
        answer,
        decision,
        True,
    )


def test_comma_separated_satisfied_does_not_pollute_unknown():
    """前一个 SATISFIED 条件不得掩盖后一个 UNKNOWN 条件的状态反转。"""
    decision = build_decision([
        build_condition("条件甲", "REQUIRED", SATISFIED),
        build_condition("条件乙", "REQUIRED", UNKNOWN),
    ])

    answer = "条件甲已满足，条件乙已满足。"

    run_case(
        "CASE 23 逗号分隔时不得用前一个条件的状态掩盖后一个条件",
        answer,
        decision,
        False,
    )



# CASE 24-26: UNKNOWN 状态矛盾表达回归测试



def test_all_unknown_conditions_mentioned_but_only_one_unresolved():
    """
    全部 Engine UNKNOWN 条件均出现，
    但只有一个条件明确表达未决状态时，必须拒绝。
    """
    decision = build_decision([
        build_condition(
            "连续订立二次固定期限劳动合同",
            "REQUIRED",
            UNKNOWN,
        ),
        build_condition(
            "续订劳动合同",
            "REQUIRED",
            UNKNOWN,
        ),
        build_condition(
            "劳动者提出或者同意续订、订立劳动合同",
            "REQUIRED",
            UNKNOWN,
        ),
        build_condition(
            "不存在劳动合同法第三十九条规定的情形",
            "EXCLUSION",
            UNKNOWN,
        ),
    ])

    answer = (
        "连续订立二次固定期限劳动合同尚未确认；"
        "续订劳动合同；"
        "劳动者提出或者同意续订、订立劳动合同；"
        "不存在劳动合同法第三十九条规定的情形。"
        "其他事项仍需结合具体事实判断。"
    )

    run_case(
        "CASE 19 全部 UNKNOWN 条件均出现但只有一个明确未决状态",
        answer,
        decision,
        False,
    )




def test_all_unknown_conditions_listed_under_explicit_unknown_heading():
    """明确声明整份条件清单均为 UNKNOWN 时，应当允许通过。"""
    decision = build_decision([
        build_condition(
            "连续订立二次固定期限劳动合同",
            "REQUIRED",
            UNKNOWN,
        ),
        build_condition(
            "续订劳动合同",
            "REQUIRED",
            UNKNOWN,
        ),
        build_condition(
            "劳动者提出或者同意续订、订立劳动合同",
            "REQUIRED",
            UNKNOWN,
        ),
        build_condition(
            "不存在劳动合同法第三十九条规定的情形",
            "EXCLUSION",
            UNKNOWN,
        ),
    ])

    answer = (
        "以下四个条件的状态均为 UNKNOWN，尚未确认："
        "连续订立二次固定期限劳动合同；"
        "续订劳动合同；"
        "劳动者提出或者同意续订、订立劳动合同；"
        "不存在劳动合同法第三十九条规定的情形。"
    )

    run_case(
        "正向对照：明确的全局 UNKNOWN 声明覆盖完整条件清单",
        answer,
        decision,
        True,
    )


def test_explicit_unknown_heading_cannot_override_condition_status_conflict():
    """整体声明 UNKNOWN，不得掩盖某个条件被明确标记为已满足。"""
    decision = build_decision([
        build_condition(
            "连续订立二次固定期限劳动合同",
            "REQUIRED",
            UNKNOWN,
        ),
        build_condition(
            "续订劳动合同",
            "REQUIRED",
            UNKNOWN,
        ),
        build_condition(
            "劳动者提出或者同意续订、订立劳动合同",
            "REQUIRED",
            UNKNOWN,
        ),
        build_condition(
            "不存在劳动合同法第三十九条规定的情形",
            "EXCLUSION",
            UNKNOWN,
        ),
    ])

    answer = (
        "以下四个条件的状态均为 UNKNOWN，尚未确认："
        "连续订立二次固定期限劳动合同；"
        "续订劳动合同已满足，但该事项仍待确认；"
        "劳动者提出或者同意续订、订立劳动合同；"
        "不存在劳动合同法第三十九条规定的情形。"
    )

    run_case(
        "整体 UNKNOWN 声明不能掩盖单项已满足状态",
        answer,
        decision,
        False,
    )


def test_explicit_unknown_heading_cannot_override_not_satisfied_conflict():
    """整体声明 UNKNOWN，不得掩盖某个条件被明确标记为不满足。"""
    decision = build_decision([
        build_condition(
            "连续订立二次固定期限劳动合同",
            "REQUIRED",
            UNKNOWN,
        ),
        build_condition(
            "续订劳动合同",
            "REQUIRED",
            UNKNOWN,
        ),
        build_condition(
            "劳动者提出或者同意续订、订立劳动合同",
            "REQUIRED",
            UNKNOWN,
        ),
        build_condition(
            "不存在劳动合同法第三十九条规定的情形",
            "EXCLUSION",
            UNKNOWN,
        ),
    ])

    answer = (
        "以下四个条件的状态均为 UNKNOWN，尚未确认："
        "连续订立二次固定期限劳动合同；"
        "续订劳动合同不满足，但该事项仍待确认；"
        "劳动者提出或者同意续订、订立劳动合同；"
        "不存在劳动合同法第三十九条规定的情形。"
    )

    run_case(
        "整体 UNKNOWN 声明不能掩盖单项不满足状态",
        answer,
        decision,
        False,
    )


def test_unknown_conflict_with_yi_man_zu():
    decision = build_decision([
        build_condition("续订劳动合同", "REQUIRED", "UNKNOWN")
    ])
    run_case(
        "CASE 24：UNKNOWN + 已满足 + 待确认",
        "续订劳动合同已满足，但该事项仍待确认。",
        decision,
        False,
    )


def test_unknown_conflict_with_condition_established():
    decision = build_decision([
        build_condition("续订劳动合同", "REQUIRED", "UNKNOWN")
    ])
    run_case(
        "CASE 25：UNKNOWN + 该条件成立 + 尚未确认",
        "续订劳动合同该条件成立，但仍尚未确认。",
        decision,
        False,
    )


def test_unknown_conflict_with_not_satisfied():
    decision = build_decision([
        build_condition("续订劳动合同", "REQUIRED", "UNKNOWN")
    ])
    run_case(
        "CASE 26：UNKNOWN + 不满足 + 待确认",
        "续订劳动合同不满足，但仍待确认。",
        decision,
        False,
    )


def test_each_unknown_condition_must_keep_its_own_unresolved_status():
    """每个 UNKNOWN 条件分别表达未决状态时应当通过。"""
    decision = build_decision([
        build_condition("条件甲", "REQUIRED", UNKNOWN),
        build_condition("条件乙", "REQUIRED", UNKNOWN),
        build_condition("条件丙", "EXCLUSION", UNKNOWN),
    ])

    answer = (
        "条件甲尚未确认；"
        "条件乙目前无法确认；"
        "条件丙仍待核实。"
    )

    run_case(
        "每个 UNKNOWN 条件分别保留未决状态",
        answer,
        decision,
        True,
    )


def test_generic_unresolved_statement_cannot_cover_other_unknown_conditions():
    """一个条件的未决表达及泛化结论不能替代其他条件的状态。"""
    decision = build_decision([
        build_condition("条件甲", "REQUIRED", UNKNOWN),
        build_condition("条件乙", "REQUIRED", UNKNOWN),
        build_condition("条件丙", "EXCLUSION", UNKNOWN),
    ])

    answer = (
        "条件甲尚未确认；"
        "条件乙；"
        "条件丙。"
        "其他事项仍需结合具体事实判断。"
    )

    run_case(
        "泛化未决表达不能替代逐项 UNKNOWN 状态",
        answer,
        decision,
        False,
    )


if __name__ == "__main__":
    main()
    test_comma_separated_unknown_does_not_pollute_satisfied()
    test_comma_separated_satisfied_does_not_pollute_unknown()
    test_condition_position_sentence_boundaries()
    test_condition_position_internal_punctuation()
    test_unknown_conflict_with_yi_man_zu()
    test_unknown_conflict_with_condition_established()
    test_unknown_conflict_with_not_satisfied()
    test_condition_position_repeated_text()


def test_explicit_unknown_heading_requires_each_condition_unresolved():
    """整体 UNKNOWN 标题不能替代每个条件自己的未决状态。"""
    decision = build_decision([
        build_condition(
            "连续订立二次固定期限劳动合同",
            "REQUIRED",
            UNKNOWN,
        ),
        build_condition(
            "续订劳动合同",
            "REQUIRED",
            UNKNOWN,
        ),
        build_condition(
            "劳动者提出或者同意续订、订立劳动合同",
            "REQUIRED",
            UNKNOWN,
        ),
        build_condition(
            "不存在劳动合同法第三十九条规定的情形",
            "EXCLUSION",
            UNKNOWN,
        ),
    ])

    answer = (
        "以下四个条件的状态均为 UNKNOWN，尚未确认："
        "连续订立二次固定期限劳动合同尚未确认；"
        "续订劳动合同；"
        "劳动者提出或者同意续订、订立劳动合同；"
        "不存在劳动合同法第三十九条规定的情形。"
    )

    run_case(
        "整体 UNKNOWN 标题不得替代逐项未决状态",
        answer,
        decision,
        False,
    )




def test_explicit_unknown_heading_rejects_unlocatable_condition():
    """整体 UNKNOWN 标题不能代替无法独立定位的条件。"""
    decision = build_decision([
        build_condition(
            "劳动者提出或者同意续订、订立劳动合同",
            "REQUIRED",
            UNKNOWN,
        ),
        build_condition(
            "不存在劳动合同法第三十九条规定的情形",
            "EXCLUSION",
            UNKNOWN,
        ),
    ])

    # 两组短关键词散落在不同句子中。
    # 覆盖计数可能通过，但答案没有完整表达两个条件，
    # 且没有为任一条件提供独立的未决状态。
    answer = (
        "以下两个条件的状态均为 UNKNOWN："
        "劳动者提出了相关意见。"
        "劳动合同已经订立。"
        "第三十九条规定了相关情形。"
        "其他事实仍需结合具体情况判断。"
    )

    run_case(
        "整体 UNKNOWN 标题不得掩盖条件无法独立定位",
        answer,
        decision,
        False,
    )


def test_explicit_unknown_heading_rejects_keyword_only_false_coverage():
    """整体 UNKNOWN 标题不能绕过无法独立定位的条件。"""
    decision = build_decision([
        build_condition(
            "劳动者提出或者同意续订、订立劳动合同",
            "REQUIRED",
            UNKNOWN,
        ),
        build_condition(
            "不存在劳动合同法第三十九条规定的情形",
            "EXCLUSION",
            UNKNOWN,
        ),
    ])

    # 关键词分散在不同句子中，旧逻辑会把两个条件都计入覆盖率，
    # 但两个完整条件均无法独立定位，且没有单项未决表达。
    answer = (
        "以下两个条件的状态均为 UNKNOWN："
        "劳动者提出了相关意见。"
        "另有同意续订的讨论。"
        "劳动合同已经订立。"
        "第三十九条规定了相关情形。"
        "其他事实仍需结合具体情况判断。"
    )

    run_case(
        "整体 UNKNOWN 标题不得绕过关键词覆盖误判",
        answer,
        decision,
        False,
    )
def test_boundary_rejects_unrelated_unresolved_statement():
    """合法 UNKNOWN 条件之外，不得额外制造无关的待核实事项。"""
    decision = build_decision([
        build_condition("续订劳动合同", "REQUIRED", UNKNOWN),
        build_condition(
            "劳动者提出或者同意续订、订立劳动合同",
            "REQUIRED",
            UNKNOWN,
        ),
    ])

    # 两个 Engine UNKNOWN 条件都分别保留了未决状态。
    # 额外事项与上述条件之间插入长文本，避免局部窗口误关联。
    neutral_text = "补充说明：" + "相关背景信息仅作记录。" * 12
    answer = (
        "续订劳动合同目前尚未确认；"
        "劳动者提出或者同意续订、订立劳动合同目前尚未确认。"
        + neutral_text
        + "员工是否曾经收到另一份内部通知，待核实。"
    )

    run_case(
        "边界校验拒绝与 Engine UNKNOWN 无关的待核实事项",
        answer,
        decision,
        False,
    )


def test_unknown_exclusion_rejects_answer_missing_negation():
    """答案遗漏 UNKNOWN 排除条件中的否定词时必须拒绝。"""
    condition = "不存在劳动合同法第三十九条规定的情形"

    decision = build_decision([
        build_condition(condition, "EXCLUSION", UNKNOWN),
    ])

    # 答案保留了法律关键词和未决表达，却遗漏了条件中的“不存在”。
    answer = "劳动合同法第三十九条规定的情形，目前尚不能确认。"

    run_case(
        "UNKNOWN 排除条件遗漏否定词必须拦截",
        answer,
        decision,
        False,
    )


def test_unknown_exception_rejects_answer_missing_negation():
    """答案遗漏 UNKNOWN 例外条件中的否定词时必须拒绝。"""
    condition = "劳动者未提出订立固定期限劳动合同"

    decision = build_decision([
        build_condition(condition, "EXCEPTION", UNKNOWN),
    ])

    # 答案遗漏“未”，改变了 Engine 条件的语义。
    answer = "劳动者提出订立固定期限劳动合同，目前尚不能确认。"

    run_case(
        "UNKNOWN 例外条件遗漏否定词必须拦截",
        answer,
        decision,
        False,
    )


def test_boundary_rejects_unrelated_unknown_after_engine_unknown():
    """Engine UNKNOWN 不得为后续无关事项提供身份关联。"""
    decision = build_decision([
        build_condition(
            "续订劳动合同",
            "REQUIRED",
            UNKNOWN,
        ),
    ])

    answer = (
        "续订劳动合同尚未确认。"
        "员工是否收到另一份内部通知，仍需确认。"
    )

    run_case(
        "边界校验拒绝后置的无关 UNKNOWN",
        answer,
        decision,
        False,
    )


def test_boundary_rejects_unrelated_unknown_before_engine_unknown():
    """调换顺序后，无关 UNKNOWN 仍不得通过边界校验。"""
    decision = build_decision([
        build_condition(
            "续订劳动合同",
            "REQUIRED",
            UNKNOWN,
        ),
    ])

    answer = (
        "员工是否收到另一份内部通知，仍需确认。"
        "续订劳动合同尚未确认。"
    )

    run_case(
        "边界校验拒绝前置的无关 UNKNOWN",
        answer,
        decision,
        False,
    )


def test_global_unknown_heading_allows_complete_condition_list():
    """整体 UNKNOWN 声明可以覆盖完整列出的多个 Engine UNKNOWN 条件。"""
    decision = build_decision([
        build_condition(
            "续订劳动合同",
            "REQUIRED",
            UNKNOWN,
        ),
        build_condition(
            "劳动者提出或者同意续订、订立劳动合同",
            "REQUIRED",
            UNKNOWN,
        ),
    ])

    answer = (
        "以下两个条件的状态均为 UNKNOWN，尚未确认："
        "续订劳动合同；"
        "劳动者提出或者同意续订、订立劳动合同。"
    )

    run_case(
        "正向对照：整体 UNKNOWN 声明覆盖完整的两个条件",
        answer,
        decision,
        True,
    )
