# -*- coding: utf-8 -*-

"""
RAG V6.0-8
End-to-End Regression Test

功能：

1. 测试 V6.0 完整法律 RAG 链路
2. 测试 Retriever
3. 测试 Relevance Ranker
4. 测试 Legal Rule Extractor
5. 测试 Rule Normalizer
6. 测试 Legal Decision Engine
7. 测试 Legal Answer Builder
8. 测试 Legal Answer Validator
9. 测试最终 RAG 输出
10. 测试多个法律问题回归案例

核心目标：

    用户问题
        ↓
    Retriever
        ↓
    Relevance Ranker
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

V6.0-8 不修改业务逻辑。

本文件主要用于：

    End-to-End
    Regression Test
    防止后续版本修改时破坏已经通过的法律推理能力。

特别测试：

    “连续签订三次固定期限劳动合同”

不得被系统错误改写为：

    “连续订立二次固定期限劳动合同”

同时测试：

    第十四条
    第三十九条
    第四十条
    第八十二条

之间的法律条件关系。
"""

import sys
import traceback
from pathlib import Path


# ============================================================
# 项目路径
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:

    sys.path.insert(
        0,
        str(PROJECT_ROOT),
    )


# ============================================================
# 导入 V6.0 模块
# ============================================================

from src.retriever import build_context

from src.relevance_ranker import rank_documents

from src.legal_rule_extractor import (
    extract_legal_rules,
)

from src.rule_normalizer import (
    normalize_rules,
)

from src.legal_decision_engine import (
    make_legal_decision,
)

from src.legal_answer_builder import (
    build_legal_answer,
)

from src.legal_answer_validator import (
    validate_legal_answer,
)


# ============================================================
# 测试问题
# ============================================================

MAIN_QUESTION = (
    "公司连续签订三次固定期限劳动合同后，"
    "是否必须签订无固定期限劳动合同？"
)


# ============================================================
# 回归测试案例
# ============================================================

REGRESSION_CASES = [

    {
        "name": "三次固定期限劳动合同",
        "question": (
            "公司连续签订三次固定期限劳动合同后，"
            "是否必须签订无固定期限劳动合同？"
        ),
        "expected": [
            "【结论】",
            "【法律依据】",
            "【法律分析】",
            "【需要注意】",
        ],
    },

    {
        "name": "两次固定期限后第三次续签",
        "question": (
            "我已经连续订立两次固定期限劳动合同，"
            "公司第三次续签时可以继续签固定期限劳动合同吗？"
        ),
        "expected": [
            "【结论】",
            "【法律依据】",
            "【法律分析】",
            "【需要注意】",
        ],
    },

    {
        "name": "第三次固定期限合同",
        "question": (
            "公司第三次与我签固定期限劳动合同，"
            "我没有提出签固定期限，公司是否违法？"
        ),
        "expected": [
            "【结论】",
            "【法律依据】",
            "【法律分析】",
            "【需要注意】",
        ],
    },

    {
        "name": "无固定期限合同二倍工资",
        "question": (
            "公司应当签无固定期限劳动合同但没有签，"
            "需要支付二倍工资吗？"
        ),
        "expected": [
            "【结论】",
            "【法律依据】",
            "【法律分析】",
            "【需要注意】",
        ],
    },

    {
        "name": "劳动者主动要求固定期限",
        "question": (
            "我主动要求第三次继续签固定期限劳动合同，"
            "还能要求无固定期限劳动合同吗？"
        ),
        "expected": [
            "【结论】",
            "【法律依据】",
            "【法律分析】",
            "【需要注意】",
        ],
    },
]


# ============================================================
# 测试工具
# ============================================================

def print_title(
    title: str,
):

    print()
    print("=" * 70)
    print(title)
    print("=" * 70)


def assert_true(
    condition: bool,
    message: str,
):

    if not condition:

        raise AssertionError(
            message
        )


# ============================================================
# TEST 1
# Retriever
# ============================================================

def test_retriever():

    print_title(
        "TEST 1 - Retriever"
    )

    context = build_context(
        question=MAIN_QUESTION,
        top_k=5,
        score_threshold=0.55,
    )

    assert_true(
        context,
        "Retriever 没有返回 Context",
    )

    print(
        f"Context 字符数：{len(context)}"
    )

    assert_true(
        "第十四条" in context,
        "Context 缺少第十四条",
    )

    assert_true(
        "第三十九条" in context,
        "Context 缺少第三十九条",
    )

    assert_true(
        "第四十条" in context,
        "Context 缺少第四十条",
    )

    print(
        "✅ Retriever 测试通过"
    )

    return context


# ============================================================
# TEST 2
# Relevance Ranker
# ============================================================

def test_ranker(
    context: str,
):

    print_title(
        "TEST 2 - Relevance Ranker"
    )

    """
    注意：

    当前 ranker 的输入接口可能根据项目版本有所不同。

    如果 rank_documents() 接收的是 Retriever 返回的
    document list，而不是 Context 字符串，

    可以根据当前 relevance_ranker.py 的实际接口调整这里。

    本测试优先验证：

        ranker 模块可以正常工作
    """

    try:

        ranked = rank_documents(
            context
        )

    except TypeError:

        """
        某些版本的 ranker 可能要求：

            question
            documents

        因此尝试第二种调用方式。
        """

        ranked = rank_documents(
            question=MAIN_QUESTION,
            documents=context,
        )

    assert_true(
        ranked is not None,
        "Ranker 没有返回结果",
    )

    print(
        "Ranker 返回结果成功"
    )

    print(
        f"Ranker 返回数量："
        f"{len(ranked) if hasattr(ranked, '__len__') else '未知'}"
    )

    print(
        "✅ Relevance Ranker 测试通过"
    )

    return ranked


# ============================================================
# TEST 3
# Legal Rule Extractor
# ============================================================

def test_rule_extractor(
    context: str,
):

    print_title(
        "TEST 3 - Legal Rule Extractor"
    )

    try:

        rules = extract_legal_rules(
            question=MAIN_QUESTION,
            context=context,
        )

    except TypeError:

        rules = extract_legal_rules(
            context=context,
            question=MAIN_QUESTION,
        )

    assert_true(
        rules,
        "Legal Rule Extractor 没有提取法律规则",
    )

    print(
        f"法律规则数量：{len(rules)}"
    )

    law_names = []

    article_numbers = []

    for rule in rules:

        if not isinstance(
            rule,
            dict,
        ):

            continue

        law_name = rule.get(
            "law_name"
        )

        article_number = rule.get(
            "article_number"
        )

        if law_name:

            law_names.append(
                law_name
            )

        if article_number:

            article_numbers.append(
                str(article_number)
            )

    print(
        f"法律名称：{law_names}"
    )

    print(
        f"法条：{article_numbers}"
    )

    assert_true(
        any(
            "第十四条" in item
            for item in article_numbers
        ),
        "Legal Rule Extractor 未识别第十四条",
    )

    print(
        "✅ Legal Rule Extractor 测试通过"
    )

    return rules


# ============================================================
# TEST 4
# Rule Normalizer
# ============================================================

def test_rule_normalizer(
    rules,
):

    print_title(
        "TEST 4 - Rule Normalizer"
    )

    try:

        normalized = normalize_rules(
            rules
        )

    except TypeError:

        normalized = normalize_rules(
            rules=rules
        )

    assert_true(
        normalized,
        "Rule Normalizer 没有返回结果",
    )

    print(
        f"规范化后规则数量："
        f"{len(normalized)}"
    )

    for index, rule in enumerate(
        normalized,
        start=1,
    ):

        print()

        print(
            f"规则 {index}"
        )

        if not isinstance(
            rule,
            dict,
        ):

            continue

        print(
            "法律：",
            rule.get(
                "law_name",
                "",
            ),
        )

        print(
            "法条：",
            rule.get(
                "article_number",
                "",
            ),
        )

        print(
            "规则类型：",
            rule.get(
                "rule_type",
                "",
            ),
        )

    print(
        "✅ Rule Normalizer 测试通过"
    )

    return normalized


# ============================================================
# TEST 5
# Legal Decision Engine
# ============================================================

def test_decision_engine(
    normalized_rules,
):

    print_title(
        "TEST 5 - Legal Decision Engine"
    )

    try:

        decision = make_legal_decision(
            question=MAIN_QUESTION,
            rules=normalized_rules,
        )

    except TypeError:

        decision = make_legal_decision(
            MAIN_QUESTION,
            normalized_rules,
        )

    assert_true(
        decision,
        "Legal Decision Engine 没有返回结果",
    )

    """
    V6.0 核心测试：

    对于：

        公司连续签订三次固定期限劳动合同

    不能直接得出：

        必须签无固定期限劳动合同

    因为：

        第三次是否属于法律意义上的“续订劳动合同”
        尚未得到确认。

    因此当前问题应该保持：

        CONDITIONAL
    """

    if isinstance(
        decision,
        dict,
    ):

        status = (
            decision.get(
                "decision"
            )
            or decision.get(
                "status"
            )
            or decision.get(
                "decision_status"
            )
        )

        print(
            "Decision：",
            status,
        )

        conclusion = (
            decision.get(
                "conclusion"
            )
            or decision.get(
                "preliminary_conclusion"
            )
            or ""
        )

        print(
            "Conclusion：",
            conclusion,
        )

        if status:

            assert_true(
                str(status).upper()
                == "CONDITIONAL",
                (
                    "当前事实不完整，"
                    "Decision 应为 CONDITIONAL，"
                    f"实际为：{status}"
                ),
            )

    else:

        print(
            "Decision 返回对象：",
            type(decision),
        )

    print(
        "✅ Legal Decision Engine 测试通过"
    )

    return decision


# ============================================================
# TEST 6
# Legal Answer Builder
# ============================================================

def test_answer_builder(
    decision,
    normalized_rules,
):

    print_title(
        "TEST 6 - Legal Answer Builder"
    )

    try:

        answer = build_legal_answer(
            question=MAIN_QUESTION,
            decision=decision,
            rules=normalized_rules,
        )

    except TypeError:

        try:

            answer = build_legal_answer(
                MAIN_QUESTION,
                decision,
                normalized_rules,
            )

        except TypeError:

            answer = build_legal_answer(
                question=MAIN_QUESTION,
                decision=decision,
            )

    assert_true(
        answer,
        "Legal Answer Builder 没有生成答案",
    )

    answer = str(
        answer
    )

    print(
        "答案字符数：",
        len(answer),
    )

    required_sections = [
        "【结论】",
        "【法律依据】",
        "【法律分析】",
        "【需要注意】",
    ]

    for section in required_sections:

        assert_true(
            section in answer,
            f"答案缺少章节：{section}",
        )

    print(
        "四个法律答案章节全部存在"
    )

    print()
    print(
        "生成答案："
    )
    print(
        answer
    )

    print(
        "✅ Legal Answer Builder 测试通过"
    )

    return answer


# ============================================================
# TEST 7
# Legal Answer Validator
# ============================================================

def test_answer_validator(
    answer: str,
):

    print_title(
        "TEST 7 - Legal Answer Validator"
    )

    try:

        validation = validate_legal_answer(
            answer=answer,
            question=MAIN_QUESTION,
        )

    except TypeError:

        validation = validate_legal_answer(
            answer,
            MAIN_QUESTION,
        )

    assert_true(
        validation is not None,
        "Validator 没有返回结果",
    )

    """
    Validator 的不同版本可能返回：

        bool

    或：

        {
            "status": "PASS",
            "errors": []
        }

    或：

        {
            "valid": True,
            ...
        }
    """

    if isinstance(
        validation,
        bool,
    ):

        valid = validation

    elif isinstance(
        validation,
        dict,
    ):

        status = validation.get(
            "status"
        )

        valid_value = validation.get(
            "valid"
        )

        if status is not None:

            valid = (
                str(status).upper()
                == "PASS"
            )

        elif valid_value is not None:

            valid = bool(
                valid_value
            )

        else:

            valid = True

    else:

        valid = True

    assert_true(
        valid,
        "最终法律答案未通过 Validator",
    )

    print(
        "Validator：PASS"
    )

    print(
        "✅ Legal Answer Validator 测试通过"
    )

    return validation


# ============================================================
# TEST 8
# 事实一致性
# ============================================================

def test_fact_consistency(
    answer: str,
):

    print_title(
        "TEST 8 - Fact Consistency"
    )

    """
    用户事实：

        公司连续签订三次固定期限劳动合同

    最终答案不得把事实直接改写成：

        连续订立二次固定期限劳动合同

    注意：

    法律规则本身当然可以出现：

        “连续订立二次固定期限劳动合同”

    因为这是第十四条的法律规则。

    因此这里不能简单判断：

        “答案中出现二次” = 错误。

    真正需要防止的是：

        “用户连续签订三次”
        被直接认定为
        “法律上的连续订立二次并且第三次必然属于续订”。

    因此主要检查危险表达。
    """

    forbidden_patterns = [

        "三次固定期限劳动合同自动转为无固定期限劳动合同",

        "签订三次固定期限劳动合同后自动转为无固定期限劳动合同",

        "连续签订三次固定期限劳动合同必然签订无固定期限劳动合同",

        "连续签订三次固定期限劳动合同一定必须签订无固定期限劳动合同",

    ]

    for pattern in forbidden_patterns:

        assert_true(
            pattern not in answer,
            f"发现危险法律表达：{pattern}",
        )

    print(
        "未发现“三次自动转无固定期限”等危险表达"
    )

    print(
        "✅ Fact Consistency 测试通过"
    )


# ============================================================
# TEST 9
# 第十四条条件化判断
# ============================================================

def test_article_14_conditions(
    answer: str,
):

    print_title(
        "TEST 9 - Article 14 Conditions"
    )

    """
    对当前问题：

        公司连续签订三次固定期限劳动合同后，
        是否必须签订无固定期限劳动合同？

    最终答案必须体现：

        第三次是否属于法律意义上的续订劳动合同
        仍然需要确认。

    因此检查：

        “续订劳动合同”
    """

    assert_true(
        "续订劳动合同" in answer,
        (
            "最终答案没有体现第十四条"
            "“续订劳动合同”的条件。"
        ),
    )

    print(
        "答案包含“续订劳动合同”条件"
    )

    print(
        "✅ Article 14 Conditions 测试通过"
    )


# ============================================================
# TEST 10
# 第八十二条条件
# ============================================================

def test_article_82_condition(
    answer: str,
):

    print_title(
        "TEST 10 - Article 82 Condition"
    )

    """
    如果答案引用第八十二条：

        必须先判断是否已经达到
        “应当订立无固定期限劳动合同”的条件。

    当前事实并不完整。

    因此不能直接写成：

        公司应当支付二倍工资。

    应该采用条件化表达。
    """

    if "第八十二条" not in answer:

        print(
            "答案未引用第八十二条"
        )

        print(
            "本测试跳过"
        )

        return

    dangerous_patterns = [

        "公司应当支付二倍工资",

        "公司必须支付二倍工资",

        "应直接支付二倍工资",

        "一定要支付二倍工资",

    ]

    for pattern in dangerous_patterns:

        assert_true(
            pattern not in answer,
            (
                "第八十二条责任判断"
                "缺少前提条件："
                f"{pattern}"
            ),
        )

    print(
        "第八十二条责任未被无条件认定"
    )

    print(
        "✅ Article 82 Condition 测试通过"
    )


# ============================================================
# TEST 11
# 重复章节
# ============================================================

def test_duplicate_sections(
    answer: str,
):

    print_title(
        "TEST 11 - Duplicate Sections"
    )

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

        print(
            f"{section}：{count} 次"
        )

        assert_true(
            count == 1,
            f"章节重复：{section}",
        )

    print(
        "未发现重复章节"
    )

    print(
        "✅ Duplicate Sections 测试通过"
    )


# ============================================================
# TEST 12
# 思考过程
# ============================================================

def test_thinking_process(
    answer: str,
):

    print_title(
        "TEST 12 - Thinking Process"
    )

    forbidden = [

        "我的思考是",

        "让我分析",

        "分析过程",

        "我的推理",

        "思考过程",

        "我认为",

    ]

    for item in forbidden:

        assert_true(
            item not in answer,
            f"发现思考过程表达：{item}",
        )

    print(
        "未发现明显思考过程"
    )

    print(
        "✅ Thinking Process 测试通过"
    )


# ============================================================
# TEST 13
# 最终法律答案综合测试
# ============================================================

def test_final_answer(
    answer: str,
):

    print_title(
        "TEST 13 - Final Legal Answer"
    )

    assert_true(
        answer,
        "最终答案为空",
    )

    required_sections = [
        "【结论】",
        "【法律依据】",
        "【法律分析】",
        "【需要注意】",
    ]

    for section in required_sections:

        assert_true(
            section in answer,
            f"最终答案缺少：{section}",
        )

    """
    当前问题事实不足。

    因此最终答案不能简单给：

        “必须签订无固定期限劳动合同。”

    应该体现：

        根据现有事实，不能直接作出绝对结论。

    或者等价的条件化表达。
    """

    conditional_expressions = [

        "不能直接作出绝对结论",

        "如果",

        "需要进一步确认",

        "无法确认",

        "尚不能确定",

    ]

    has_conditional_expression = any(
        item in answer
        for item in conditional_expressions
    )

    assert_true(
        has_conditional_expression,
        (
            "当前事实不完整，"
            "但最终答案没有体现条件化判断。"
        ),
    )

    print(
        "最终答案体现条件化法律判断"
    )

    print(
        "✅ Final Legal Answer 测试通过"
    )


# ============================================================
# 单案例完整测试
# ============================================================

def run_main_case():

    print_title(
        "V6.0-8 - Main End-to-End Case"
    )

    print()
    print(
        "问题："
    )

    print(
        MAIN_QUESTION
    )

    # --------------------------------------------------------
    # 1. Retriever
    # --------------------------------------------------------

    context = test_retriever()

    # --------------------------------------------------------
    # 2. Ranker
    # --------------------------------------------------------

    test_ranker(
        context
    )

    # --------------------------------------------------------
    # 3. Rule Extractor
    # --------------------------------------------------------

    rules = test_rule_extractor(
        context
    )

    # --------------------------------------------------------
    # 4. Rule Normalizer
    # --------------------------------------------------------

    normalized_rules = test_rule_normalizer(
        rules
    )

    # --------------------------------------------------------
    # 5. Decision Engine
    # --------------------------------------------------------

    decision = test_decision_engine(
        normalized_rules
    )

    # --------------------------------------------------------
    # 6. Answer Builder
    # --------------------------------------------------------

    answer = test_answer_builder(
        decision,
        normalized_rules,
    )

    # --------------------------------------------------------
    # 7. Validator
    # --------------------------------------------------------

    test_answer_validator(
        answer
    )

    # --------------------------------------------------------
    # 8. Fact Consistency
    # --------------------------------------------------------

    test_fact_consistency(
        answer
    )

    # --------------------------------------------------------
    # 9. Article 14
    # --------------------------------------------------------

    test_article_14_conditions(
        answer
    )

    # --------------------------------------------------------
    # 10. Article 82
    # --------------------------------------------------------

    test_article_82_condition(
        answer
    )

    # --------------------------------------------------------
    # 11. Duplicate Sections
    # --------------------------------------------------------

    test_duplicate_sections(
        answer
    )

    # --------------------------------------------------------
    # 12. Thinking Process
    # --------------------------------------------------------

    test_thinking_process(
        answer
    )

    # --------------------------------------------------------
    # 13. Final Answer
    # --------------------------------------------------------

    test_final_answer(
        answer
    )

    return answer


# ============================================================
# 回归测试
# ============================================================

def run_regression_tests():

    print_title(
        "V6.0-8 - Regression Test Suite"
    )

    print(
        f"回归案例数量："
        f"{len(REGRESSION_CASES)}"
    )

    passed = 0
    failed = 0

    for index, case in enumerate(
        REGRESSION_CASES,
        start=1,
    ):

        print()
        print(
            "-" * 70
        )

        print(
            f"CASE {index}："
            f"{case['name']}"
        )

        print(
            f"问题：{case['question']}"
        )

        try:

            context = build_context(
                question=case[
                    "question"
                ],
                top_k=5,
                score_threshold=0.55,
            )

            assert_true(
                context,
                "Retriever 未返回 Context",
            )

            print(
                "  ✅ Retriever"
            )

            rules = extract_legal_rules(
                question=case[
                    "question"
                ],
                context=context,
            )

            assert_true(
                rules,
                "Rule Extractor 未返回规则",
            )

            print(
                "  ✅ Rule Extractor"
            )

            normalized = normalize_rules(
                rules
            )

            assert_true(
                normalized,
                "Rule Normalizer 未返回规则",
            )

            print(
                "  ✅ Rule Normalizer"
            )

            decision = make_legal_decision(
                question=case[
                    "question"
                ],
                rules=normalized,
            )

            assert_true(
                decision,
                "Decision Engine 未返回结果",
            )

            print(
                "  ✅ Decision Engine"
            )

            answer = build_legal_answer(
                question=case[
                    "question"
                ],
                decision=decision,
                rules=normalized,
            )

            assert_true(
                answer,
                "Answer Builder 未生成答案",
            )

            answer = str(
                answer
            )

            print(
                "  ✅ Answer Builder"
            )

            validation = validate_legal_answer(
                answer=answer,
                question=case[
                    "question"
                ],
            )

            if isinstance(
                validation,
                bool,
            ):

                valid = validation

            elif isinstance(
                validation,
                dict,
            ):

                status = validation.get(
                    "status"
                )

                valid_value = validation.get(
                    "valid"
                )

                if status is not None:

                    valid = (
                        str(status).upper()
                        == "PASS"
                    )

                elif valid_value is not None:

                    valid = bool(
                        valid_value
                    )

                else:

                    valid = True

            else:

                valid = True

            assert_true(
                valid,
                "Validator FAIL",
            )

            print(
                "  ✅ Answer Validator"
            )

            for section in case[
                "expected"
            ]:

                assert_true(
                    section in answer,
                    f"缺少章节：{section}",
                )

            print(
                "  ✅ Answer Structure"
            )

            passed += 1

            print(
                f"  🎉 CASE {index} PASS"
            )

        except Exception as e:

            failed += 1

            print(
                f"  ❌ CASE {index} FAIL"
            )

            print(
                f"  原因：{e}"
            )

            traceback.print_exc()

    print()
    print(
        "=" * 70
    )

    print(
        "Regression Test Summary"
    )

    print(
        "=" * 70
    )

    print(
        f"总案例：{len(REGRESSION_CASES)}"
    )

    print(
        f"通过：{passed}"
    )

    print(
        f"失败：{failed}"
    )

    if failed == 0:

        print()
        print(
            "🎉 V6.0-8 Regression Test 全部通过"
        )

    else:

        print()
        print(
            "⚠️ V6.0-8 存在失败案例"
        )

    return (
        passed,
        failed,
    )


# ============================================================
# 主测试
# ============================================================

def main():

    print()
    print(
        "=" * 70
    )

    print(
        "RAG V6.0-8"
    )

    print(
        "End-to-End Regression Test"
    )

    print(
        "=" * 70
    )

    print()
    print(
        f"项目目录：{PROJECT_ROOT}"
    )

    print()
    print(
        "核心测试问题："
    )

    print(
        MAIN_QUESTION
    )

    # ========================================================
    # 主链路测试
    # ========================================================

    try:

        run_main_case()

        print()
        print(
            "=" * 70
        )

        print(
            "主链路测试：PASS"
        )

        print(
            "=" * 70
        )

    except Exception as e:

        print()
        print(
            "=" * 70
        )

        print(
            "主链路测试：FAIL"
        )

        print(
            "=" * 70
        )

        print(
            f"错误：{e}"
        )

        traceback.print_exc()

        return 1

    # ========================================================
    # 回归测试
    # ========================================================

    passed, failed = (
        run_regression_tests()
    )

    # ========================================================
    # 最终结果
    # ========================================================

    print()
    print(
        "=" * 70
    )

    print(
        "RAG V6.0-8 最终测试结果"
    )

    print(
        "=" * 70
    )

    if failed == 0:

        print()
        print(
            "🎉 V6.0-8 全部测试通过"
        )

        print()
        print(
            "V6.0 当前完整链路："
        )

        print(
            "Retriever"
        )

        print(
            "    ↓"
        )

        print(
            "Relevance Ranker"
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

        print()
        print(
            "V6.0-8：PASS"
        )

        return 0

    print()
    print(
        "❌ V6.0-8 测试失败"
    )

    print(
        f"通过：{passed}"
    )

    print(
        f"失败：{failed}"
    )

    return 1


# ============================================================
# Python Module Entry
# ============================================================

if __name__ == "__main__":

    exit_code = main()

    sys.exit(
        exit_code
    )