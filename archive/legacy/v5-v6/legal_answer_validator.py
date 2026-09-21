# -*- coding: utf-8 -*-

"""
RAG V6.0-7
Legal Answer Validator

功能：

1. 最终法律答案结构检查
2. 用户事实一致性检查
3. 法律条件完整性检查
4. 法律义务强度检查
5. 法条引用检查
6. 第十四条核心规则检查
7. 第八十二条二倍工资条件检查
8. 禁止把“如果”条件写成确定事实
9. 禁止把“可以”写成“应当”
10. 禁止把“应当”写成“可以”
11. 禁止最终答案重复
12. 输出验证结果
13. 必要时对明显结构问题进行自动修复

V6.0-7 核心目标：

    Retriever
        ↓
    Rule Extractor
        ↓
    Rule Normalizer
        ↓
    Decision Engine
        ↓
    Answer Builder
        ↓
    Ollama
        ↓
    Legal Answer Validator
        ↓
    最终法律答案

本模块不负责：

    1. 法律检索
    2. 向量搜索
    3. 法条生成
    4. 法律事实推断
    5. 修改用户事实

本模块只负责：

    “检查最终答案是否符合已经确定的法律规则。”

特别注意：

法律答案验证器不能代替法律判断。

它只能检查：

    答案是否违反已经建立的规则。

如果发现问题：

    返回 validation result

而不是：

    擅自修改法律结论。
"""


import re

from typing import (
    Dict,
    List,
    Optional,
)


# ============================================================
# 常量
# ============================================================

REQUIRED_SECTIONS = [
    "【结论】",
    "【法律依据】",
    "【法律分析】",
    "【需要注意】",
]


# ============================================================
# 第十四条核心条件
# ============================================================

ARTICLE_14_REQUIRED_CONDITIONS = [

    "连续订立二次固定期限劳动合同",

    "续订劳动合同",

    "劳动者提出或者同意续订、订立劳动合同",
]


# ============================================================
# 第十四条排除条件
# ============================================================

ARTICLE_14_EXCLUSION_CONDITIONS = [

    "劳动者存在《劳动合同法》第三十九条规定的情形",

    "劳动者存在《劳动合同法》第四十条第一项规定的情形",

    "劳动者存在《劳动合同法》第四十条第二项规定的情形",
]


# ============================================================
# 第十四条例外
# ============================================================

ARTICLE_14_EXCEPTIONS = [

    "劳动者提出订立固定期限劳动合同",
]


# ============================================================
# 核心法律义务
# ============================================================

ARTICLE_14_OBLIGATION = (
    "用人单位应当订立无固定期限劳动合同"
)


# ============================================================
# 第八十二条
# ============================================================

ARTICLE_82_KEYWORDS = [
    "二倍工资",
    "每月支付二倍的工资",
]


# ============================================================
# 禁止出现的错误表达
# ============================================================

FORBIDDEN_EXPRESSIONS = [

    # --------------------------------------------------------
    # 错误理解：
    #
    # 三次固定期限劳动合同
    # =
    # 自动必须签无固定期限劳动合同
    # --------------------------------------------------------

    "签三次固定期限劳动合同就必须签无固定期限劳动合同",

    "连续签订三次固定期限劳动合同就必须签无固定期限劳动合同",

    "签订三次固定期限劳动合同后自动转为无固定期限劳动合同",

    "三次固定期限劳动合同自动转为无固定期限劳动合同",

    "签三次就自动转为无固定期限劳动合同",

    # --------------------------------------------------------
    # 错误理解：
    #
    # 第十四条规定签三次
    # --------------------------------------------------------

    "第十四条规定签三次",

    "法律规定必须签三次固定期限劳动合同",

    "法律规定第三次必须签固定期限劳动合同",

    # --------------------------------------------------------
    # 错误理解：
    #
    # 第十四条只规定两次，
    # 所以第三次完全没有约束
    # --------------------------------------------------------

    "第十四条只规定两次所以第三次不受约束",

    "签第三次固定期限劳动合同不受第十四条约束",

    # --------------------------------------------------------
    # 错误理解：
    #
    # 连续三次
    # =
    # 法律规定的连续二次 + 第三次续订
    # --------------------------------------------------------

    "连续签订三次就是连续订立二次固定期限劳动合同并自动续订",

    "三次签订等同于连续订立二次固定期限劳动合同并续订",
]


# ============================================================
# 用户事实识别
# ============================================================

def extract_user_facts(
    question: str,
) -> Dict[str, bool]:
    """
    从用户问题中提取当前已经明确提供的事实。

    注意：

    这里只做非常保守的事实识别。

    不进行法律推断。

    例如：

        用户说：

            公司连续签订三次固定期限劳动合同

        只能识别：

            连续签订三次固定期限劳动合同

        不能直接识别：

            第三次属于续订劳动合同

    因为：

        “三次签订”

    和：

        “第三次续订”

    在法律分析中不能直接等同。
    """

    question = (
        question or ""
    ).strip()

    facts = {

        "three_fixed_term_contracts":
            False,

        "two_fixed_term_contracts":
            False,

        "renewal":
            False,

        "employee_requested_or_agreed":
            False,

        "article_39_condition":
            False,

        "article_40_1_condition":
            False,

        "article_40_2_condition":
            False,

        "employee_requested_fixed_term":
            False,
    }

    # --------------------------------------------------------
    # 三次固定期限劳动合同
    # --------------------------------------------------------

    if (
        "三次"
        in question
        and "固定期限劳动合同"
        in question
    ):

        facts[
            "three_fixed_term_contracts"
        ] = True

        # 三次事实意味着至少存在两次，
        # 但不能因此确认第三次属于续订。
        facts[
            "two_fixed_term_contracts"
        ] = True

    # --------------------------------------------------------
    # 两次固定期限劳动合同
    # --------------------------------------------------------

    elif (
        "二次"
        in question
        and "固定期限劳动合同"
        in question
    ) or (
        "两次"
        in question
        and "固定期限劳动合同"
        in question
    ):

        facts[
            "two_fixed_term_contracts"
        ] = True

    # --------------------------------------------------------
    # 续订
    # --------------------------------------------------------

    if (
        "续订"
        in question
        or "续签"
        in question
    ):

        facts[
            "renewal"
        ] = True

    # --------------------------------------------------------
    # 劳动者提出或者同意
    # --------------------------------------------------------

    if (
        "劳动者提出"
        in question
        or "劳动者同意"
        in question
    ):

        facts[
            "employee_requested_or_agreed"
        ] = True

    # --------------------------------------------------------
    # 第三十九条
    # --------------------------------------------------------

    if (
        "第三十九条"
        in question
    ):

        facts[
            "article_39_condition"
        ] = True

    # --------------------------------------------------------
    # 第四十条第一项
    # --------------------------------------------------------

    if (
        "第四十条第一项"
        in question
        or "第四十条第一款"
        in question
    ):

        facts[
            "article_40_1_condition"
        ] = True

    # --------------------------------------------------------
    # 第四十条第二项
    # --------------------------------------------------------

    if (
        "第四十条第二项"
        in question
        or "第四十条第二款"
        in question
    ):

        facts[
            "article_40_2_condition"
        ] = True

    # --------------------------------------------------------
    # 劳动者提出订立固定期限劳动合同
    # --------------------------------------------------------

    if (
        "劳动者提出订立固定期限劳动合同"
        in question
    ):

        facts[
            "employee_requested_fixed_term"
        ] = True

    return facts


# ============================================================
# 结构检查
# ============================================================

def validate_structure(
    answer: str,
) -> List[str]:
    """
    检查最终答案是否包含规定结构。

    必须包含：

        【结论】
        【法律依据】
        【法律分析】
        【需要注意】

    返回：

        errors
    """

    errors = []

    if not answer:

        errors.append(
            "最终答案为空"
        )

        return errors

    for section in REQUIRED_SECTIONS:

        if section not in answer:

            errors.append(
                f"缺少必要结构：{section}"
            )

    return errors


# ============================================================
# 重复结构检查
# ============================================================

def find_duplicate_sections(
    answer: str,
) -> List[str]:
    """
    检查最终答案是否重复输出相同章节。

    例如：

        【结论】

        ...

        【法律依据】

        ...

        【结论】

        ...

    则认为存在重复。
    """

    errors = []

    if not answer:

        return errors

    for section in REQUIRED_SECTIONS:

        count = answer.count(
            section
        )

        if count > 1:

            errors.append(
                f"章节重复输出：{section} "
                f"（{count} 次）"
            )

    return errors


# ============================================================
# 禁止表达检查
# ============================================================

def validate_forbidden_expressions(
    answer: str,
) -> List[str]:
    """
    检查法律答案中是否出现明显错误表达。
    """

    errors = []

    if not answer:

        return errors

    normalized = re.sub(
        r"\s+",
        "",
        answer,
    )

    for expression in FORBIDDEN_EXPRESSIONS:

        expression_normalized = re.sub(
            r"\s+",
            "",
            expression,
        )

        if (
            expression_normalized
            in normalized
        ):

            errors.append(
                "发现禁止法律表达："
                f"{expression}"
            )

    return errors


# ============================================================
# 用户事实一致性检查
# ============================================================

def validate_fact_consistency(
    question: str,
    answer: str,
) -> List[str]:
    """
    检查最终答案是否修改用户明确事实。

    当前重点：

        用户说：

            三次固定期限劳动合同

        答案不能把事实改成：

            两次固定期限劳动合同

        或：

            第三次续订

    除非答案明确使用：

        “如果……”

        “若……”

        “在……情况下……”

    表示假设条件。
    """

    errors = []

    question = (
        question or ""
    ).strip()

    answer = (
        answer or ""
    ).strip()

    facts = extract_user_facts(
        question
    )

    # --------------------------------------------------------
    # 用户明确说三次
    # --------------------------------------------------------

    if facts[
        "three_fixed_term_contracts"
    ]:

        # ----------------------------------------------------
        # 检查是否把三次事实直接改成“两次”
        # ----------------------------------------------------

        dangerous_patterns = [

            "你签了两次固定期限劳动合同",

            "已经连续订立二次固定期限劳动合同",

            "事实为连续订立二次固定期限劳动合同",

            "用户签订了二次固定期限劳动合同",

        ]

        for pattern in dangerous_patterns:

            if pattern in answer:

                errors.append(
                    "用户明确提供的是“三次固定期限劳动合同”，"
                    f"答案却将其直接改写为：{pattern}"
                )

        # ----------------------------------------------------
        # 检查是否把第三次直接认定为续订
        # ----------------------------------------------------

        direct_renewal_patterns = [

            "第三次就是续订",

            "第三次属于续订劳动合同",

            "第三次合同属于续订",

            "第三次签订即为续订",

            "第三次签订就是续订",

        ]

        for pattern in direct_renewal_patterns:

            if pattern in answer:

                errors.append(
                    "用户仅提供“三次固定期限劳动合同”，"
                    f"答案却直接认定：{pattern}"
                )

    return errors


# ============================================================
# 条件完整性检查
# ============================================================

def validate_article_14_conditions(
    question: str,
    answer: str,
) -> List[str]:
    """
    检查涉及劳动合同法第十四条时，
    是否正确处理关键条件。

    核心要求：

        连续订立二次固定期限劳动合同
        +
        续订劳动合同
        +
        劳动者提出或者同意
        +
        排除第三十九条
        +
        排除第四十条第一、二项
        +
        劳动者没有提出订立固定期限劳动合同

    注意：

    如果最终答案采用条件化表达：

        “如果第三次属于续订劳动合同……”
    
    则属于正确处理。

    不要求用户必须已经提供全部事实。
    """

    errors = []

    question = (
        question or ""
    ).strip()

    answer = (
        answer or ""
    ).strip()

    # --------------------------------------------------------
    # 如果不是劳动合同法第十四条问题，
    # 不强制执行本检查。
    # --------------------------------------------------------

    if (
        "劳动合同"
        not in question
        and "无固定期限"
        not in question
    ):

        return errors

    # --------------------------------------------------------
    # 判断是否讨论无固定期限劳动合同
    # --------------------------------------------------------

    if (
        "无固定期限"
        not in answer
    ):

        return errors

    # --------------------------------------------------------
    # 用户只说三次，
    # 重点检查第三次续订条件。
    # --------------------------------------------------------

    facts = extract_user_facts(
        question
    )

    if facts[
        "three_fixed_term_contracts"
    ]:

        # ----------------------------------------------------
        # 如果答案直接使用确定性语言：
        #
        # “因此必须签订”
        #
        # 但没有任何条件限制，
        # 则属于高风险表达。
        # ----------------------------------------------------

        unconditional_patterns = [

            "因此必须签订无固定期限劳动合同",

            "所以必须签订无固定期限劳动合同",

            "因此应当签订无固定期限劳动合同",

            "所以应当签订无固定期限劳动合同",

            "三次固定期限劳动合同后应当签订无固定期限劳动合同",

            "三次固定期限劳动合同后必须签订无固定期限劳动合同",

        ]

        has_condition_words = any(
            word in answer
            for word in [
                "如果",
                "若",
                "在……情况下",
                "在满足",
                "符合条件",
                "具体需要判断",
                "不能直接",
                "尚需确认",
                "取决于",
            ]
        )

        for pattern in unconditional_patterns:

            if (
                pattern in answer
                and not has_condition_words
            ):

                errors.append(
                    "答案可能将“三次固定期限劳动合同”"
                    "直接认定为必须订立无固定期限劳动合同，"
                    "缺少第十四条条件化判断。"
                )

                break

    # --------------------------------------------------------
    # 检查关键条件是否完全遗漏。
    #
    # 如果答案明确作出条件化结论，
    # 至少应该提到续订条件。
    # --------------------------------------------------------

    if facts[
        "three_fixed_term_contracts"
    ]:

        renewal_mentions = [
            "续订劳动合同",
            "第三次是否属于续订",
            "第三次属于法律意义上的续订",
            "第三次是否构成续订",
            "是否属于续订",
        ]

        if not any(
            item in answer
            for item in renewal_mentions
        ):

            errors.append(
                "用户明确提供“三次固定期限劳动合同”，"
                "但答案未说明第三次是否属于法律意义上的“续订劳动合同”。"
            )

    return errors


# ============================================================
# “应当 / 可以 / 不得”检查
# ============================================================

def validate_legal_strength(
    answer: str,
) -> List[str]:
    """
    检查法律义务强度是否出现明显错误。

    重点：

        应当
        可以
        不得

    不能互相替换。

    当前主要检查：

        第十四条：
            应当订立

        第三十九条：
            可以解除

        第四十条：
            可以解除

    """

    errors = []

    if not answer:

        return errors

    # --------------------------------------------------------
    # 第十四条：
    #
    # 如果答案引用第十四条，
    # 不应该把法律强制义务表达成“可以订立”。
    # --------------------------------------------------------

    if (
        "第十四条"
        in answer
        and "无固定期限劳动合同"
        in answer
    ):

        wrong_patterns = [

            "第十四条规定可以订立无固定期限劳动合同",

            "符合第十四条条件时可以订立无固定期限劳动合同",

            "用人单位可以订立无固定期限劳动合同",

        ]

        for pattern in wrong_patterns:

            if pattern in answer:

                errors.append(
                    "第十四条义务强度错误："
                    f"{pattern}"
                )

    # --------------------------------------------------------
    # 第三十九条：
    #
    # 法律使用“可以解除劳动合同”。
    #
    # 不应该被写成“应当解除”。
    # --------------------------------------------------------

    if (
        "第三十九条"
        in answer
    ):

        if (
            "第三十九条"
            in answer
            and "应当解除劳动合同"
            in answer
        ):

            errors.append(
                "第三十九条义务强度错误："
                "“可以解除”不能改写为“应当解除”。"
            )

    # --------------------------------------------------------
    # 第四十条：
    #
    # 同样使用“可以解除”。
    # --------------------------------------------------------

    if (
        "第四十条"
        in answer
        and "应当解除劳动合同"
        in answer
    ):

        errors.append(
            "第四十条义务强度错误："
            "“可以解除”不能改写为“应当解除”。"
        )

    return errors


# ============================================================
# 第八十二条责任检查
# ============================================================

def validate_article_82(
    answer: str,
) -> List[str]:
    """
    检查第八十二条二倍工资责任是否被提前确定。

    正确逻辑：

        先判断：

            是否已经达到应当订立无固定期限劳动合同的条件？

        再判断：

            用人单位是否违反该义务？

        最后：

            才能讨论第八十二条二倍工资责任。

    禁止：

        仅因为用户说“三次固定期限劳动合同”，
        就直接认定必须支付二倍工资。
    """

    errors = []

    if not answer:

        return errors

    # --------------------------------------------------------
    # 如果答案没有引用第八十二条，
    # 则不需要执行本检查。
    # --------------------------------------------------------

    if (
        "第八十二条"
        not in answer
    ):

        return errors

    # --------------------------------------------------------
    # 检查是否直接确定二倍工资责任。
    # --------------------------------------------------------

    unconditional_patterns = [

        "必须支付二倍工资",

        "应当支付二倍工资",

        "公司必须支付二倍工资",

        "用人单位应当支付二倍工资",

        "公司需要支付二倍工资",

    ]

    # --------------------------------------------------------
    # 检查是否同时存在条件判断。
    # --------------------------------------------------------

    has_condition_words = any(
        word in answer
        for word in [
            "如果",
            "若",
            "在……情况下",
            "符合条件",
            "达到",
            "应当订立无固定期限劳动合同",
            "违反",
            "尚需确认",
        ]
    )

    for pattern in unconditional_patterns:

        if (
            pattern in answer
            and not has_condition_words
        ):

            errors.append(
                "第八十二条责任判断缺少前提条件："
                "不能在尚未确认应当订立无固定期限劳动合同的情况下，"
                "直接认定二倍工资责任。"
            )

            break

    return errors


# ============================================================
# 法条引用检查
# ============================================================

def validate_article_references(
    answer: str,
    context: Optional[str] = None,
) -> List[str]:
    """
    检查答案引用的法条是否能够在 Context 中找到。

    如果提供：

        context

    则检查：

        答案中的“第十四条”
        是否存在于 Context。

    注意：

    这里只检查引用存在性。

    不判断：

        法条内容是否真的适用于案件。

    法律适用由：

        legal_decision_engine

    负责。
    """

    errors = []

    if not answer:

        return errors

    if not context:

        return errors

    # --------------------------------------------------------
    # 提取答案中的法条编号
    # --------------------------------------------------------

    article_pattern = (
        r"第[一二三四五六七八九十百千万零〇\d]+条"
    )

    answer_articles = set(
        re.findall(
            article_pattern,
            answer,
        )
    )

    if not answer_articles:

        return errors

    for article in sorted(
        answer_articles
    ):

        if article not in context:

            errors.append(
                f"答案引用了 Context 中不存在的法条：{article}"
            )

    return errors


# ============================================================
# 思考过程检查
# ============================================================

def validate_no_thinking_process(
    answer: str,
) -> List[str]:
    """
    检查最终答案是否泄露模型思考过程。
    """

    errors = []

    if not answer:

        return errors

    forbidden = [

        "我的思考是",

        "让我分析",

        "分析过程如下",

        "我的推理",

        "根据我的推理",

        "首先让我",

        "我认为我们需要分析",

        "<think>",

        "</think>",
    ]

    for expression in forbidden:

        if expression in answer:

            errors.append(
                "发现不应输出的思考过程表达："
                f"{expression}"
            )

    return errors


# ============================================================
# 重复文本检查
# ============================================================

def validate_duplicate_content(
    answer: str,
) -> List[str]:
    """
    检查最终答案是否存在明显重复。

    当前主要用于：

        Ollama 偶尔重复整段答案。

    方法：

        将文本按照段落拆分，
        检查完全相同的段落。
    """

    errors = []

    if not answer:

        return errors

    paragraphs = [
        paragraph.strip()
        for paragraph in re.split(
            r"\n\s*\n",
            answer,
        )
        if paragraph.strip()
    ]

    seen = set()

    duplicates = set()

    for paragraph in paragraphs:

        normalized = re.sub(
            r"\s+",
            "",
            paragraph,
        )

        if (
            normalized
            in seen
        ):

            duplicates.add(
                normalized
            )

        seen.add(
            normalized
        )

    if duplicates:

        errors.append(
            f"发现重复段落：{len(duplicates)} 个"
        )

    return errors


# ============================================================
# 自动清理重复章节
# ============================================================

def remove_duplicate_sections(
    answer: str,
) -> str:
    """
    删除重复章节。

    注意：

    这是结构性清理。

    不修改法律内容。
    """

    if not answer:

        return ""

    parts = re.split(
        r"(【(?:结论|法律依据|法律分析|需要注意)】)",
        answer,
    )

    if len(parts) < 3:

        return answer

    result = []

    seen = set()

    i = 0

    while i < len(parts):

        part = parts[i]

        if part in REQUIRED_SECTIONS:

            section = part

            body = ""

            if i + 1 < len(parts):

                body = parts[i + 1]

            if section not in seen:

                result.append(
                    section
                )

                result.append(
                    body
                )

                seen.add(
                    section
                )

            i += 2

        else:

            if part.strip():

                result.append(
                    part
                )

            i += 1

    return "".join(
        result
    ).strip()


# ============================================================
# 清理 <think>
# ============================================================

def remove_thinking_process(
    answer: str,
) -> str:
    """
    删除 Ollama/Qwen 输出中的 <think>...</think>。
    """

    if not answer:

        return ""

    answer = re.sub(
        r"<think>.*?</think>",
        "",
        answer,
        flags=re.DOTALL,
    )

    return answer.strip()


# ============================================================
# 自动清理
# ============================================================

def clean_answer(
    answer: str,
) -> str:
    """
    对最终答案进行安全清理。

    只处理：

        1. think 标签
        2. 重复章节
        3. 多余空行
        4. 首尾空格

    不修改：

        法律结论
        用户事实
        法律条件
        法条内容
    """

    if not answer:

        return ""

    answer = remove_thinking_process(
        answer
    )

    answer = remove_duplicate_sections(
        answer
    )

    answer = re.sub(
        r"\n{3,}",
        "\n\n",
        answer,
    )

    return answer.strip()


# ============================================================
# 综合验证
# ============================================================

def validate_answer(
    question: str,
    answer: str,
    context: Optional[str] = None,
) -> Dict:
    """
    V6.0-7 核心验证函数。

    返回：

        {
            "valid": True / False,

            "errors": [],

            "warnings": [],

            "checks": {
                ...
            }
        }

    注意：

    valid=False

    并不意味着法律结论一定错误。

    只表示：

        当前答案存在需要人工或者程序进一步处理的问题。
    """

    answer = (
        answer or ""
    ).strip()

    errors = []

    warnings = []

    # --------------------------------------------------------
    # 1. 结构
    # --------------------------------------------------------

    structure_errors = (
        validate_structure(
            answer
        )
    )

    errors.extend(
        structure_errors
    )

    # --------------------------------------------------------
    # 2. 重复章节
    # --------------------------------------------------------

    duplicate_section_errors = (
        find_duplicate_sections(
            answer
        )
    )

    errors.extend(
        duplicate_section_errors
    )

    # --------------------------------------------------------
    # 3. 禁止表达
    # --------------------------------------------------------

    forbidden_errors = (
        validate_forbidden_expressions(
            answer
        )
    )

    errors.extend(
        forbidden_errors
    )

    # --------------------------------------------------------
    # 4. 用户事实一致性
    # --------------------------------------------------------

    fact_errors = (
        validate_fact_consistency(
            question=question,
            answer=answer,
        )
    )

    errors.extend(
        fact_errors
    )

    # --------------------------------------------------------
    # 5. 第十四条条件
    # --------------------------------------------------------

    article_14_errors = (
        validate_article_14_conditions(
            question=question,
            answer=answer,
        )
    )

    errors.extend(
        article_14_errors
    )

    # --------------------------------------------------------
    # 6. 法律义务强度
    # --------------------------------------------------------

    legal_strength_errors = (
        validate_legal_strength(
            answer
        )
    )

    errors.extend(
        legal_strength_errors
    )

    # --------------------------------------------------------
    # 7. 第八十二条
    # --------------------------------------------------------

    article_82_errors = (
        validate_article_82(
            answer
        )
    )

    errors.extend(
        article_82_errors
    )

    # --------------------------------------------------------
    # 8. 法条引用
    # --------------------------------------------------------

    reference_errors = (
        validate_article_references(
            answer=answer,
            context=context,
        )
    )

    errors.extend(
        reference_errors
    )

    # --------------------------------------------------------
    # 9. 思考过程
    # --------------------------------------------------------

    thinking_errors = (
        validate_no_thinking_process(
            answer
        )
    )

    errors.extend(
        thinking_errors
    )

    # --------------------------------------------------------
    # 10. 重复内容
    # --------------------------------------------------------

    duplicate_content_errors = (
        validate_duplicate_content(
            answer
        )
    )

    errors.extend(
        duplicate_content_errors
    )

    # --------------------------------------------------------
    # 如果答案没有明显错误，
    # 则认为验证通过。
    # --------------------------------------------------------

    valid = (
        len(errors) == 0
    )

    return {

        "valid": valid,

        "errors": errors,

        "warnings": warnings,

        "checks": {

            "structure":
                len(structure_errors) == 0,

            "duplicate_sections":
                len(duplicate_section_errors) == 0,

            "forbidden_expressions":
                len(forbidden_errors) == 0,

            "fact_consistency":
                len(fact_errors) == 0,

            "article_14_conditions":
                len(article_14_errors) == 0,

            "legal_strength":
                len(legal_strength_errors) == 0,

            "article_82":
                len(article_82_errors) == 0,

            "article_references":
                len(reference_errors) == 0,

            "thinking_process":
                len(thinking_errors) == 0,

            "duplicate_content":
                len(duplicate_content_errors) == 0,
        },
    }


# ============================================================
# 自动验证并清理
# ============================================================

def validate_and_clean_answer(
    question: str,
    answer: str,
    context: Optional[str] = None,
) -> Dict:
    """
    V6.0-7 最推荐的入口函数。

    执行：

        原始答案
            ↓
        自动清理
            ↓
        法律验证
            ↓
        返回最终结果

    注意：

    如果验证失败：

        不自动修改法律结论。

    这样可以避免：

        Validator 擅自改变法律判断。
    """

    cleaned_answer = clean_answer(
        answer
    )

    validation = validate_answer(
        question=question,
        answer=cleaned_answer,
        context=context,
    )

    return {

        "answer":
            cleaned_answer,

        "valid":
            validation["valid"],

        "errors":
            validation["errors"],

        "warnings":
            validation["warnings"],

        "checks":
            validation["checks"],
    }


# ============================================================
# 打印验证结果
# ============================================================

def print_validation_result(
    result: Dict,
):
    """
    输出 V6.0-7 验证结果。
    """

    print()
    print("=" * 70)
    print("RAG V6.0-7 - Legal Answer Validator")
    print("=" * 70)

    print()

    if result.get(
        "valid",
        False,
    ):

        print(
            "✅ 法律答案验证通过"
        )

    else:

        print(
            "❌ 法律答案验证失败"
        )

    print()

    print(
        "验证状态：",
        "PASS"
        if result.get(
            "valid",
            False,
        )
        else "FAIL",
    )

    errors = result.get(
        "errors",
        [],
    )

    if errors:

        print()

        print(
            "发现问题："
        )

        for index, error in enumerate(
            errors,
            start=1,
        ):

            print(
                f"  {index}. {error}"
            )

    print()

    print(
        "检查项目："
    )

    checks = result.get(
        "checks",
        {},
    )

    for name, passed in checks.items():

        status = (
            "✅"
            if passed
            else "❌"
        )

        print(
            f"  {status} {name}"
        )


# ============================================================
# V6.0-7 测试
# ============================================================

def run_tests():
    """
    V6.0-7 单元测试。

    测试重点：

        1. 正确条件化答案
        2. 错误“三次自动转无固定期限”
        3. 用户事实被修改
        4. 第八十二条责任提前确定
        5. 重复章节
    """

    question = (
        "公司连续签订三次固定期限劳动合同后，"
        "是否必须签订无固定期限劳动合同？"
    )

    # ========================================================
    # 测试 1
    # 正确答案
    # ========================================================

    answer_1 = """
【结论】

根据现有事实，不能直接作出绝对结论。

如果所谓第三次合同是在前两次固定期限劳动合同之后的续订，
并且满足《劳动合同法》第十四条规定的其他条件，
则可能需要订立无固定期限劳动合同。

【法律依据】

《中华人民共和国劳动合同法》第十四条规定，
连续订立二次固定期限劳动合同，
且符合其他法定条件，续订劳动合同的，
应当订立无固定期限劳动合同。

【法律分析】

用户明确提供的事实是连续签订三次固定期限劳动合同。

这一事实至少可以说明存在两次固定期限劳动合同，
但不能仅凭“三次”直接认定第三次属于法律意义上的续订劳动合同。

还需要确认劳动者是否提出或者同意续订、订立劳动合同，
以及是否存在第三十九条、第四十条第一项、第二项规定的情形。

【需要注意】

如果第三次合同并非法律意义上的续订，
或者其他法定条件不成立，
则不能仅依据“三次固定期限劳动合同”直接作出必须订立无固定期限劳动合同的结论。
"""

    result_1 = validate_answer(
        question=question,
        answer=answer_1,
    )

    print_validation_result(
        result_1
    )

    assert result_1["valid"] is True

    # ========================================================
    # 测试 2
    # 错误：
    #
    # 三次自动转无固定期限
    # ========================================================

    answer_2 = """
【结论】

公司连续签订三次固定期限劳动合同后，
因此必须签订无固定期限劳动合同。

【法律依据】

《劳动合同法》第十四条。

【法律分析】

三次固定期限劳动合同自动转为无固定期限劳动合同。

【需要注意】

没有其他需要注意的事项。
"""

    result_2 = validate_answer(
        question=question,
        answer=answer_2,
    )

    print_validation_result(
        result_2
    )

    assert result_2["valid"] is False

    # ========================================================
    # 测试 3
    # 错误：
    #
    # 把三次事实改成两次
    # ========================================================

    answer_3 = """
【结论】

根据现有事实，劳动者已经连续订立二次固定期限劳动合同，
因此第三次应当订立无固定期限劳动合同。

【法律依据】

《劳动合同法》第十四条。

【法律分析】

用户已经签订二次固定期限劳动合同。

【需要注意】

需要进一步确认其他条件。
"""

    result_3 = validate_answer(
        question=question,
        answer=answer_3,
    )

    print_validation_result(
        result_3
    )

    assert result_3["valid"] is False

    # ========================================================
    # 测试 4
    # 第八十二条责任提前确定
    # ========================================================

    answer_4 = """
【结论】

公司必须支付二倍工资。

【法律依据】

《劳动合同法》第十四条、第八十二条。

【法律分析】

公司连续签订三次固定期限劳动合同，
所以必须支付二倍工资。

【需要注意】

无。
"""

    result_4 = validate_answer(
        question=question,
        answer=answer_4,
    )

    print_validation_result(
        result_4
    )

    assert result_4["valid"] is False

    # ========================================================
    # 测试 5
    # 重复章节
    # ========================================================

    answer_5 = """
【结论】

根据现有事实，不能直接作出绝对结论。

【法律依据】

《劳动合同法》第十四条。

【法律分析】

需要进一步确认第三次合同是否属于续订。

【需要注意】

需要进一步确认其他事实。

【结论】

根据现有事实，不能直接作出绝对结论。
"""

    result_5 = validate_answer(
        question=question,
        answer=answer_5,
    )

    print_validation_result(
        result_5
    )

    assert result_5["valid"] is False

    # ========================================================
    # 测试完成
    # ========================================================

    print()
    print("=" * 70)
    print("V6.0-7 Legal Answer Validator 测试完成")
    print("=" * 70)
    print()
    print(
        "✅ 所有测试通过"
    )


# ============================================================
# Module Test
# ============================================================

if __name__ == "__main__":

    run_tests()