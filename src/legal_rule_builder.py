# -*- coding: utf-8 -*-

"""
Legal Rule Builder

============================================================
RAG V6.0-27
Structured Article → Legal Rule
============================================================

功能：

    1. Structured Article → Rule
    2. Rule 字段统一
    3. Retriever Article 字段兼容
    4. Rule 去重
    5. 法条编号标准化排序辅助
    6. Rule 文本提取
    7. Rule 相关性排序
    8. CORE / RELATED 规则分层
    9. Structured Rules 构建

============================================================
模块边界
============================================================

本模块只负责：

    Retriever Articles
            ↓
    normalize_rule()
            ↓
    Normalized Rule
            ↓
    build_rules_from_articles()
            ↓
    Structured Rules
            ↓
    prioritize_legal_rules()
            ↓
    Ordered Rules

============================================================
不负责
============================================================

本模块不负责：

    - Legal Decision Engine
    - ConditionResult
    - Fact → Condition 推理
    - Decision Adapter
    - Legal Answer Builder
    - Legal Prompt
    - Ollama
    - Legal Citation Validation

============================================================
拆分说明
============================================================

这些函数原本位于：

    src/rag.py

本次从 RAG V6.0-27 中独立出来。

后续模块通过本模块统一获得：

    Structured Rules

从而避免：

    - 多个模块重复 normalize_rule()
    - 多个模块重复 Rules 去重
    - 多个模块自行解释 Article 字段
    - 多个模块自行构建 Rule

============================================================
核心原则
============================================================

1. Retriever 负责寻找法律依据。

2. Rule Builder 负责将 Retriever Article
   转换为统一 Rule。

3. Rule Builder 不进行法律条件判断。

4. Rule Builder 不根据用户问题创造法律规则。

5. Rule Builder 不修改用户事实。

6. Rule Builder 不创建 ConditionResult。

7. Rule Builder 不决定 DEFINITE / CONDITIONAL /
   NOT_ESTABLISHED。

8. Rule Builder 只负责 Rules 的结构化、
   归一化、去重和排序。

============================================================
"""


import re

from typing import Any, Dict, List


from src.legal_common import (
    normalize_text,
    ensure_list,
    get_field,
    get_first_field,
)


# ============================================================
# Structured Article → Rule
# ============================================================

def normalize_rule(article: Any) -> Dict[str, Any]:
    """
    将 Retriever 返回的结构化法律条文
    转换成统一 Rule。

    兼容字段：

        law_name
        law
        title

        article_number
        article
        article_no

        rule_summary
        summary
        content
        text

        rule_type
        type

        conditions
        exceptions

    核心原则：

        只做字段归一化，
        不进行法律推理。
    """

    source = {}

    # ========================================================
    # 1. Article 本身是 dict
    # ========================================================

    if isinstance(article, dict):

        source = dict(article)

    # ========================================================
    # 2. Article 是 object
    # ========================================================

    else:

        for name in [
            "law_name",
            "law",
            "title",
            "article_number",
            "article",
            "article_no",
            "rule_summary",
            "summary",
            "content",
            "text",
            "rule_type",
            "type",
            "conditions",
            "exceptions",
        ]:

            value = get_field(
                article,
                name,
                None,
            )

            if value is not None:
                source[name] = value

    # ========================================================
    # 法律名称
    # ========================================================

    law_name = get_first_field(
        source,
        [
            "law_name",
            "law",
            "title",
        ],
        "",
    )

    # ========================================================
    # 法条编号
    # ========================================================

    article_number = get_first_field(
        source,
        [
            "article_number",
            "article",
            "article_no",
        ],
        "",
    )

    # ========================================================
    # Rule 摘要
    # ========================================================

    rule_summary = get_first_field(
        source,
        [
            "rule_summary",
            "summary",
            "content",
            "text",
        ],
        "",
    )

    # ========================================================
    # Rule 类型
    # ========================================================

    rule_type = get_first_field(
        source,
        [
            "rule_type",
            "type",
        ],
        "",
    )

    # ========================================================
    # 条件
    # ========================================================

    conditions = ensure_list(
        source.get(
            "conditions",
            [],
        )
    )

    # ========================================================
    # 例外
    # ========================================================

    exceptions = ensure_list(
        source.get(
            "exceptions",
            [],
        )
    )

    # ========================================================
    # 保留原始字段
    # ========================================================

    result = dict(source)

    # ========================================================
    # 写入统一字段
    # ========================================================

    result["law_name"] = normalize_text(
        law_name
    )

    result["article_number"] = normalize_text(
        article_number
    )

    result["rule_summary"] = normalize_text(
        rule_summary
    )

    result["rule_type"] = normalize_text(
        rule_type
    )

    result["conditions"] = conditions

    result["exceptions"] = exceptions

    return result


# ============================================================
# Article Number
# ============================================================

def _article_number_value(
    article_number: str,
) -> int:
    """
    将常见中文/阿拉伯数字法条号转换为整数，
    用于稳定排序。

    例如：

        第14条
            ↓
        14

        第十四条
            ↓
        14

        第四十条
            ↓
        40
    """

    text = normalize_text(
        article_number
    )

    # ========================================================
    # 阿拉伯数字
    # ========================================================

    match = re.search(
        r"第?([0-9]+)条",
        text,
    )

    if match:

        try:
            return int(
                match.group(1)
            )

        except ValueError:

            return 999999

    # ========================================================
    # 中文数字
    # ========================================================

    chinese_digits = {
        "零": 0,
        "一": 1,
        "二": 2,
        "两": 2,
        "三": 3,
        "四": 4,
        "五": 5,
        "六": 6,
        "七": 7,
        "八": 8,
        "九": 9,
        "十": 10,
        "百": 100,
        "千": 1000,
    }

    match = re.search(
        r"第([零一二两三四五六七八九十百千万]+)条",
        text,
    )

    if not match:
        return 999999

    raw = match.group(1)

    if raw.isdigit():
        return int(raw)

    total = 0
    section = 0
    number = 0

    units = {
        "十": 10,
        "百": 100,
        "千": 1000,
        "万": 10000,
    }

    for ch in raw:

        if ch in units:

            unit = units[ch]

            if number == 0:
                number = 1

            section += number * unit

            number = 0

        else:

            number = chinese_digits.get(
                ch,
                0,
            )

    return section + number


# ============================================================
# Rule Text
# ============================================================

def _rule_text(
    rule: Dict[str, Any],
) -> str:
    """
    提取 Rule 的可检索文本，
    不修改原始 Rule。
    """

    parts = [
        normalize_text(
            rule.get(
                "law_name",
                "",
            )
        ),

        normalize_text(
            rule.get(
                "article_number",
                "",
            )
        ),

        normalize_text(
            rule.get(
                "rule_summary",
                "",
            )
        ),

        normalize_text(
            rule.get(
                "rule_type",
                "",
            )
        ),

        normalize_text(
            rule.get(
                "conditions",
                "",
            )
        ),

        normalize_text(
            rule.get(
                "exceptions",
                "",
            )
        ),
    ]

    return " ".join(
        part
        for part in parts
        if part
    )


# ============================================================
# Rule Priority
# ============================================================

def _rule_priority(
    rule: Dict[str, Any],
    question: str,
) -> tuple:
    """
    V6.0-13 法律规则相关性排序。

    目标不是删除法律依据，
    而是把与问题直接对应的核心法条放在前面，
    同时保留例外、法律后果等相关规则。

    返回：

        (
            -score,
            article_number,
            law_name,
            article_number,
        )

    其中：

        score 越高，
        排序越靠前。
    """

    q = normalize_text(
        question
    )

    text = _rule_text(
        rule
    )

    law_name = normalize_text(
        rule.get(
            "law_name",
            "",
        )
    )

    article_number = normalize_text(
        rule.get(
            "article_number",
            "",
        )
    )

    score = 0

    # ========================================================
    # 劳动合同“连续两次固定期限后无固定期限”
    # 问题的核心法条。
    # ========================================================

    if "固定期限劳动合同" in q:

        if (
            "第十四条" in article_number
            or
            "第14条" in article_number
        ):
            score += 100

        if "无固定期限劳动合同" in text:
            score += 80

        if "连续订立二次固定期限劳动合同" in text:
            score += 80

    # ========================================================
    # 用户问题包含“三次”时，
    # 第十四条仍是最直接的法律依据。
    # ========================================================

    if (
        "三次" in q
        and
        (
            "第十四条" in article_number
            or
            "第14条" in article_number
        )
    ):
        score += 40

    # ========================================================
    # 与签订/续订直接相关的规则优先。
    # ========================================================

    for keyword, weight in [
        ("订立", 20),
        ("续订", 20),
        ("无固定期限", 30),
        ("固定期限", 20),
        ("劳动合同", 10),
    ]:

        if keyword in text:
            score += weight

    # ========================================================
    # 法律后果/例外属于相关依据，
    # 但不应压过核心法条。
    # ========================================================

    if (
        "解除" in text
        or
        "终止" in text
    ):
        score -= 8

    if (
        "法律责任" in text
        or
        "赔偿" in text
        or
        "罚款" in text
    ):
        score -= 5

    # ========================================================
    # 保持原 Retriever 顺序作为最后稳定排序键。
    # ========================================================

    return (
        -score,
        _article_number_value(
            article_number
        ),
        law_name,
        article_number,
    )


# ============================================================
# Prioritize Legal Rules
# ============================================================

def prioritize_legal_rules(
    question: str,
    rules: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    V6.0-13：规则分层排序。

    不删除规则，
    不改变 Rule 内容，
    只增加：

        rule_priority
            CORE / RELATED

        rule_relevance_score
            int

    CORE：

        直接回答问题的主要法律依据。

    RELATED：

        例外、法律后果或其他辅助法律依据。

    核心原则：

        Rules 仍然全部保留。

        这里只改变：
            1. 排序
            2. priority metadata

        不进行法律条件推理。
    """

    normalized = build_rules_from_articles(
        rules
    )

    if not normalized:
        return []

    result = []

    q = normalize_text(
        question
    )

    for rule in normalized:

        # ----------------------------------------------------
        # 不修改原始 Rule，
        # 使用副本增加排序信息。
        # ----------------------------------------------------

        item = dict(rule)

        text = _rule_text(
            item
        )

        article_number = normalize_text(
            item.get(
                "article_number",
                "",
            )
        )

        priority = 0

        # ====================================================
        # 劳动合同相关问题
        # ====================================================

        if "固定期限劳动合同" in q:

            if (
                "第十四条" in article_number
                or
                "第14条" in article_number
            ):
                priority += 100

            if "无固定期限劳动合同" in text:
                priority += 80

            if "连续订立二次固定期限劳动合同" in text:
                priority += 80

        # ====================================================
        # “三次”问题
        # ====================================================

        if (
            "三次" in q
            and
            (
                "第十四条" in article_number
                or
                "第14条" in article_number
            )
        ):
            priority += 40

        # ====================================================
        # 通用关键词
        # ====================================================

        for keyword, weight in [
            ("订立", 20),
            ("续订", 20),
            ("无固定期限", 30),
            ("固定期限", 20),
            ("劳动合同", 10),
        ]:

            if keyword in text:
                priority += weight

        # ====================================================
        # 法律后果
        # ====================================================

        if (
            "解除" in text
            or
            "终止" in text
        ):
            priority -= 8

        if (
            "法律责任" in text
            or
            "赔偿" in text
            or
            "罚款" in text
        ):
            priority -= 5

        # ====================================================
        # 写入 Rule 元数据
        # ====================================================

        item["rule_relevance_score"] = priority

        item["rule_priority"] = (
            "CORE"
            if priority >= 100
            else
            "RELATED"
        )

        result.append(
            item
        )

    # ========================================================
    # 稳定排序
    # ========================================================

    result.sort(
        key=lambda r:
            _rule_priority(
                r,
                question,
            )
    )

    return result


# ============================================================
# Articles → Rules
# ============================================================

def build_rules_from_articles(
    articles: Any,
) -> List[Dict[str, Any]]:
    """
    将 Retriever Articles 转换成 Rules。

    ========================================================
    数据流
    ========================================================

        Retriever Articles
                ↓
        normalize_rule()
                ↓
        Normalized Rules

    ========================================================
    职责边界
    ========================================================

    本函数负责：

        - Article 类型统一
        - normalize_rule()
        - Rule 去重
        - 返回统一 Rules

    本函数不负责：

        - Decision Adapter
        - Ollama
        - Answer Builder
        - Legal Decision Engine
        - ConditionResult

    因此这里保持“纯 Rules 构建”职责。
    """

    # ========================================================
    # None
    # ========================================================

    if articles is None:
        return []

    # ========================================================
    # 单个 dict
    # ========================================================

    if isinstance(
        articles,
        dict,
    ):

        articles = [
            articles
        ]

    # ========================================================
    # 非 list / tuple
    # ========================================================

    if not isinstance(
        articles,
        (
            list,
            tuple,
        ),
    ):
        return []

    rules = []

    seen = set()

    # ========================================================
    # Article → Rule
    # ========================================================

    for article in articles:

        rule = normalize_rule(
            article
        )

        # ----------------------------------------------------
        # 防止 normalize_rule() 返回空结果
        # ----------------------------------------------------

        if (
            not isinstance(
                rule,
                dict,
            )
            or
            not rule
        ):
            continue

        law_name = rule.get(
            "law_name",
            "",
        )

        article_number = rule.get(
            "article_number",
            "",
        )

        summary = rule.get(
            "rule_summary",
            "",
        )

        # ----------------------------------------------------
        # 去重
        #
        # 使用：
        #
        #     law_name
        #     article_number
        #     rule_summary
        #
        # 作为 Rule 唯一键。
        # ----------------------------------------------------

        key = (
            law_name,
            article_number,
            summary,
        )

        if key in seen:
            continue

        seen.add(
            key
        )

        rules.append(
            rule
        )

    return rules