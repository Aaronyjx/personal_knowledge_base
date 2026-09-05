# -*- coding: utf-8 -*-

"""
RAG V6.0-8
End-to-End Test

文件：
    tests/test_rag_v6_e2e.py

功能：

1. 测试完整 RAG V6 流程
2. 测试 Retriever
3. 测试 Legal Rule Extractor
4. 测试 Rule Normalizer
5. 测试 Legal Decision Engine
6. 测试 Legal Answer Builder
7. 测试 Legal Answer Validator
8. 测试最终法律答案
9. 检查事实一致性
10. 检查第十四条条件化判断
11. 检查第八十二条前提条件
12. 检查答案结构
13. 检查重复章节
14. 检查禁止表达
15. 检查思考过程泄露

本测试属于：

    End-to-End Integration Test

完整流程：

    用户问题
        ↓
    RAG V6
        ↓
    Retriever
        ↓
    Legal Rule Extractor
        ↓
    Rule Normalizer
        ↓
    Legal Decision Engine
        ↓
    Legal Answer Builder
        ↓
    Legal Answer Validator
        ↓
    最终法律答案
"""


import sys
from pathlib import Path


# ============================================================
# 项目路径
# ============================================================

PROJECT_ROOT = Path(
    __file__
).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:

    sys.path.insert(
        0,
        str(PROJECT_ROOT),
    )


# ============================================================
# 测试问题
# ============================================================

QUESTION = (
    "公司连续签订三次固定期限劳动合同后，"
    "是否必须签订无固定期限劳动合同？"
)


# ============================================================
# 测试统计
# ============================================================

TOTAL_TESTS = 0
PASSED_TESTS = 0
FAILED_TESTS = 0


# ============================================================
# 测试结果
# ============================================================

def record_test(
    name: str,
    passed: bool,
    detail: str = "",
):

    global TOTAL_TESTS
    global PASSED_TESTS
    global FAILED_TESTS

    TOTAL_TESTS += 1

    if passed:

        PASSED_TESTS += 1

        print(
            f"  ✅ {name}"
        )

    else:

        FAILED_TESTS += 1

        print(
            f"  ❌ {name}"
        )

        if detail:

            print(
                f"     {detail}"
            )


# ============================================================
# 导入 RAG V6
# ============================================================

def load_rag():

    print()
    print("=" * 70)
    print("TEST 1 - RAG V6 导入")
    print("=" * 70)

    try:

        from src.rag_v6 import (
            answer_question,
        )

        record_test(
            "src.rag_v6 导入",
            True,
        )

        return answer_question

    except Exception as e:

        record_test(
            "src.rag_v6 导入",
            False,
            str(e),
        )

        raise


# ============================================================
# 检查最终答案是否为空
# ============================================================

def check_answer_exists(
    answer: str,
) -> bool:

    return bool(
        answer
        and answer.strip()
    )


# ============================================================
# 检查答案结构
# ============================================================

def check_structure(
    answer: str,
) -> bool:

    required_sections = [

        "【结论】",

        "【法律依据】",

        "【法律分析】",

        "【需要注意】",

    ]

    for section in required_sections:

        if section not in answer:

            return False

    return True


# ============================================================
# 检查章节不能重复
# ============================================================

def check_duplicate_sections(
    answer: str,
) -> bool:

    sections = [

        "【结论】",

        "【法律依据】",

        "【法律分析】",

        "【需要注意】",

    ]

    for section in sections:

        count = answer.count(
            section
        )

        if count != 1:

            return False

    return True


# ============================================================
# 检查禁止法律表达
# ============================================================

def check_forbidden_expressions(
    answer: str,
) -> bool:

    forbidden = [

        "三次固定期限劳动合同自动转为无固定期限劳动合同",

        "第三次固定期限劳动合同自动转为无固定期限劳动合同",

        "连续签订三次固定期限劳动合同自动转为无固定期限劳动合同",

        "签三次固定期限劳动合同就自动转为无固定期限劳动合同",

        "签三次固定期限劳动合同，所以必须签订无固定期限劳动合同",

        "三次固定期限劳动合同，所以必须签订无固定期限劳动合同",

        "签订三次固定期限劳动合同后自动转为无固定期限劳动合同",

        "签三次就必须签无固定期限劳动合同",

        "三次就自动转为无固定期限",

    ]

    for expression in forbidden:

        if expression in answer:

            return False

    return True


# ============================================================
# 检查用户事实是否被修改
# ============================================================

def check_fact_consistency(
    answer: str,
) -> bool:

    """
    用户明确事实：

        公司连续签订三次固定期限劳动合同

    最终答案必须注意：

        三次

    不能把用户事实直接改写成：

        已经连续订立二次固定期限劳动合同

    正确方式：

        用户明确说明连续签订三次固定期限劳动合同。

        如果第三次合同属于前两次合同到期后的续订，
        则进一步判断第十四条。

    """

    if (
        "三次固定期限劳动合同"
        not in answer
    ):

        return False

    forbidden_rewrites = [

        "已经连续订立二次固定期限劳动合同",

        "已经连续订立两次固定期限劳动合同",

        "事实是连续订立二次固定期限劳动合同",

        "你已经连续订立二次固定期限劳动合同",

        "用户已经连续订立二次固定期限劳动合同",

    ]

    for expression in forbidden_rewrites:

        if expression in answer:

            return False

    return True


# ============================================================
# 检查第十四条条件
# ============================================================

def check_article_14_conditions(
    answer: str,
) -> bool:

    """
    第十四条是本问题核心。

    必须体现：

        连续订立二次固定期限劳动合同

        续订劳动合同

        劳动者提出或者同意续订、订立劳动合同

        第三十九条

        第四十条第一项、第二项

    同时：

        当前事实不足时必须进行条件化判断。
    """

    required = [

        "第十四条",

        "连续订立二次固定期限劳动合同",

        "续订劳动合同",

        "劳动者提出或者同意",

    ]

    for keyword in required:

        if keyword not in answer:

            return False

    conditional_words = [

        "如果",

        "不能直接",

        "根据现有事实",

        "无法确认",

        "需要进一步确认",

        "条件",

    ]

    has_conditional = any(

        keyword in answer

        for keyword
        in conditional_words

    )

    if not has_conditional:

        return False

    return True


# ============================================================
# 检查第三十九条、第四十条
# ============================================================

def check_exception_conditions(
    answer: str,
) -> bool:

    required = [

        "第三十九条",

        "第四十条",

    ]

    for keyword in required:

        if keyword not in answer:

            return False

    return True


# ============================================================
# 检查法律义务强度
# ============================================================

def check_legal_strength(
    answer: str,
) -> bool:

    """
    严格区分：

        应当
        可以
        不得

    特别禁止：

        三次合同 = 必然应当签无固定期限合同

    """

    forbidden = [

        "三次后必然应当签订",

        "三次合同必然应当签订",

        "只要签订三次就应当签订",

        "签订三次即可直接认定",

        "三次固定期限合同必然导致",

        "三次固定期限劳动合同必然导致",

    ]

    for expression in forbidden:

        if expression in answer:

            return False

    return True


# ============================================================
# 检查第八十二条
# ============================================================

def check_article_82(
    answer: str,
) -> bool:

    """
    第八十二条不能脱离第十四条条件。

    正确逻辑：

        如果已经达到应当订立无固定期限劳动合同的条件，
        用人单位仍不订立，
        才可能产生第八十二条规定的二倍工资责任。

    禁止：

        尚未确认第十四条条件成立，
        就直接认定已经产生二倍工资责任。
    """

    if "第八十二条" not in answer:

        return True

    if "二倍工资" not in answer:

        return False

    direct_liability = [

        "应当支付二倍工资",

        "必须支付二倍工资",

        "已经产生二倍工资责任",

        "已经产生二倍工资",

        "公司应当支付二倍工资",

        "用人单位应当支付二倍工资",

    ]

    conditional_words = [

        "如果",

        "若",

        "在符合",

        "在达到",

        "前提是",

        "符合第十四条",

        "达到应当订立无固定期限劳动合同",

        "已经达到应当订立无固定期限劳动合同",

    ]

    for expression in direct_liability:

        if expression in answer:

            has_condition = any(

                keyword in answer

                for keyword
                in conditional_words

            )

            if not has_condition:

                return False

    return True


# ============================================================
# 检查法律引用
# ============================================================

def check_article_references(
    answer: str,
) -> bool:

    """
    本问题最核心：

        第十四条

    第八十二条不是核心判断规则，
    只有涉及法律责任时才需要出现。
    """

    if "第十四条" not in answer:

        return False

    return True


# ============================================================
# 检查思考过程
# ============================================================

def check_thinking_process(
    answer: str,
) -> bool:

    forbidden = [

        "我的思考是",

        "我的分析过程",

        "让我分析",

        "思考过程如下",

        "推理过程如下",

        "模型思考",

        "模型推理",

        "<think>",

        "</think>",

    ]

    for expression in forbidden:

        if expression in answer:

            return False

    return True


# ============================================================
# 检查重复内容
# ============================================================

def check_duplicate_content(
    answer: str,
) -> bool:

    """
    检查明显的整段重复。

    只检查长度较长的段落，
    避免因为正常短句重复导致误判。
    """

    paragraphs = [

        paragraph.strip()

        for paragraph
        in answer.split("\n\n")

        if paragraph.strip()

    ]

    seen = set()

    for paragraph in paragraphs:

        normalized = (

            paragraph

            .replace(
                " ",
                "",
            )

            .replace(
                "\n",
                "",
            )

        )

        if len(normalized) < 30:

            continue

        if normalized in seen:

            return False

        seen.add(
            normalized
        )

    return True


# ============================================================
# 检查条件化结论
# ============================================================

def check_conditional_conclusion(
    answer: str,
) -> bool:

    """
    当前问题事实：

        公司连续签订三次固定期限劳动合同

    尚未明确：

        第三次是否属于续订
        劳动者是否提出或者同意续订
        是否存在第三十九条情形
        是否存在第四十条第一项、第二项情形
        是否存在劳动者提出订立固定期限劳动合同

    因此最终结论原则上应该采用：

        条件化判断

    """

    expressions = [

        "不能直接作出绝对结论",

        "不能直接认定",

        "需要进一步确认",

        "如果第三次",

        "如果第三次合同",

        "根据现有事实",

        "现有事实不足",

        "无法确认",

    ]

    return any(

        expression in answer

        for expression
        in expressions

    )


# ============================================================
# 检查最终结论是否错误绝对化
# ============================================================

def check_absolute_conclusion(
    answer: str,
) -> bool:

    """
    防止模型输出：

        三次固定期限劳动合同后，
        必须签订无固定期限劳动合同。

    当前测试问题事实并不足以直接支持这种绝对结论。
    """

    forbidden = [

        "三次固定期限劳动合同后，必须签订无固定期限劳动合同",

        "三次固定期限劳动合同后必须签订无固定期限劳动合同",

        "连续签订三次固定期限劳动合同后，必须签订无固定期限劳动合同",

        "连续签订三次固定期限劳动合同后必须签订无固定期限劳动合同",

        "因此必须签订无固定期限劳动合同",

    ]

    for expression in forbidden:

        if expression in answer:

            return False

    return True


# ============================================================
# 打印答案
# ============================================================

def print_answer(
    answer: str,
):

    print()
    print("=" * 70)
    print("TEST 2 - RAG V6 最终答案")
    print("=" * 70)
    print()

    print(answer)

    print()


# ============================================================
# 执行最终答案检查
# ============================================================

def run_answer_tests(
    answer: str,
):

    print_title = (
        lambda title:
        (
            print(),
            print("=" * 70),
            print(title),
            print("=" * 70),
        )
    )

    print_title(
        "TEST 3 - 最终答案质量检查"
    )

    record_test(
        "答案非空",
        check_answer_exists(answer),
    )

    record_test(
        "答案结构完整",
        check_structure(answer),
    )

    record_test(
        "章节没有重复",
        check_duplicate_sections(answer),
    )

    record_test(
        "没有禁止法律表达",
        check_forbidden_expressions(answer),
    )

    record_test(
        "用户事实保持一致",
        check_fact_consistency(answer),
    )

    record_test(
        "第十四条条件完整",
        check_article_14_conditions(answer),
    )

    record_test(
        "第三十九条、第四十条条件完整",
        check_exception_conditions(answer),
    )

    record_test(
        "法律义务强度正确",
        check_legal_strength(answer),
    )

    record_test(
        "第八十二条前提正确",
        check_article_82(answer),
    )

    record_test(
        "法律引用正确",
        check_article_references(answer),
    )

    record_test(
        "没有泄露思考过程",
        check_thinking_process(answer),
    )

    record_test(
        "没有重复内容",
        check_duplicate_content(answer),
    )

    record_test(
        "结论采用条件化判断",
        check_conditional_conclusion(answer),
    )

    record_test(
        "没有错误绝对化结论",
        check_absolute_conclusion(answer),
    )


# ============================================================
# 主测试
# ============================================================

def main():

    print()
    print("=" * 70)
    print("RAG V6.0-8 - End-to-End Test")
    print("=" * 70)

    print()
    print("测试问题：")
    print(QUESTION)

    print()
    print(
        "项目目录：",
        PROJECT_ROOT,
    )

    # --------------------------------------------------------
    # TEST 1
    # --------------------------------------------------------

    answer_question = load_rag()

    # --------------------------------------------------------
    # TEST 2
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("TEST 2 - 执行完整 RAG V6")
    print("=" * 70)

    try:

        answer = answer_question(
            question=QUESTION,
            top_k=5,
            score_threshold=0.55,
            model="qwen3:14b",
        )

        if not isinstance(
            answer,
            str,
        ):

            answer = str(
                answer
            )

        record_test(
            "RAG V6 完整流程执行",
            True,
        )

    except Exception as e:

        record_test(
            "RAG V6 完整流程执行",
            False,
            str(e),
        )

        raise

    # --------------------------------------------------------
    # 打印最终答案
    # --------------------------------------------------------

    print_answer(
        answer
    )

    # --------------------------------------------------------
    # TEST 3
    # --------------------------------------------------------

    run_answer_tests(
        answer
    )

    # --------------------------------------------------------
    # TEST SUMMARY
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("RAG V6.0-8 E2E 测试总结")
    print("=" * 70)

    print()
    print(
        f"总测试数：{TOTAL_TESTS}"
    )

    print(
        f"通过：{PASSED_TESTS}"
    )

    print(
        f"失败：{FAILED_TESTS}"
    )

    print()

    if FAILED_TESTS == 0:

        print(
            "🎉 RAG V6.0-8 End-to-End Test 全部通过"
        )

        print()
        print(
            "完整流程验证成功："
        )

        print(
            "用户问题"
        )

        print(
            "    ↓"
        )

        print(
            "Retriever"
        )

        print(
            "    ↓"
        )

        print(
            "Legal Rule Extractor"
        )

        print(
            "    ↓"
        )

        print(
            "Rule Normalizer"
        )

        print(
            "    ↓"
        )

        print(
            "Legal Decision Engine"
        )

        print(
            "    ↓"
        )

        print(
            "Legal Answer Builder"
        )

        print(
            "    ↓"
        )

        print(
            "Legal Answer Validator"
        )

        print(
            "    ↓"
        )

        print(
            "最终法律答案"
        )

        return 0

    else:

        print(
            "❌ RAG V6.0-8 End-to-End Test 存在失败项目"
        )

        return 1


# ============================================================
# Python 入口
# ============================================================

if __name__ == "__main__":

    sys.exit(
        main()
    )