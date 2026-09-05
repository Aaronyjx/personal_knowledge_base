# -*- coding: utf-8 -*-

"""
RAG V6.0-3
legal_rule_extractor.py

功能：

1. 从 Relevance Ranker 输出的法律依据中提取法律规则
2. 将完整法条转换为结构化法律规则
3. 自动识别：
       - 法律义务
       - 法律权利
       - 禁止性规则
       - 条件
       - 例外
       - 排除条件
       - 法律后果
       - 引用法条
4. 特别处理《中华人民共和国劳动合同法》第十四条
5. 不调用 LLM
6. 不修改用户事实
7. 为 V6.0-4「事实 × 法律规则匹配」提供结构化输入

核心架构：

    Retriever
        ↓
    Relevance Ranker
        ↓
    Legal Rule Extractor
        ↓
    Structured Legal Rules
        ↓
    V6.0-4 Fact Rule Matcher

特别注意：

法律规则提取 ≠ 法律结论。

本模块只负责：

    法条
      ↓
    规则结构

不负责：

    用户事实
      ↓
    最终法律结论

例如：

用户问题：

    公司连续签订三次固定期限劳动合同后，
    是否必须签订无固定期限劳动合同？

本模块应该提取：

    连续订立二次固定期限劳动合同
        +
    不存在第三十九条规定的情形
        +
    不存在第四十条第一项、第二项规定的情形
        +
    续订劳动合同
        +
    劳动者提出或者同意续订、订立劳动合同
        +
    劳动者没有提出订立固定期限劳动合同
        ↓
    应当订立无固定期限劳动合同

而不能直接输出：

    签订三次固定期限劳动合同
        ↓
    必须签订无固定期限劳动合同

因为：

    “连续订立二次固定期限劳动合同”

与：

    “连续签订三次固定期限劳动合同”

不是完全相同的法律事实。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ============================================================
# 配置
# ============================================================

MAX_RULES = 20

MAX_CONDITIONS = 20

MAX_EXCEPTIONS = 20

MAX_REFERENCES = 20


# ============================================================
# 法律规则类型
# ============================================================

RULE_TYPE_DUTY = "义务规则"

RULE_TYPE_RIGHT = "权利规则"

RULE_TYPE_PROHIBITION = "禁止规则"

RULE_TYPE_PERMISSION = "授权规则"

RULE_TYPE_DEFINITION = "定义规则"

RULE_TYPE_CONDITION = "条件规则"

RULE_TYPE_CONSEQUENCE = "法律后果规则"

RULE_TYPE_GENERAL = "一般规则"


# ============================================================
# 法律义务关键词
# ============================================================

DUTY_KEYWORDS = [
    "应当",
    "必须",
    "有义务",
    "应与",
    "应向",
    "应当与",
    "应当支付",
    "应当订立",
    "应当签订",
]


# ============================================================
# 权利关键词
# ============================================================

RIGHT_KEYWORDS = [
    "有权",
    "可以要求",
    "可以提出",
    "劳动者提出",
    "劳动者可以",
    "当事人可以",
]


# ============================================================
# 禁止关键词
# ============================================================

PROHIBITION_KEYWORDS = [
    "不得",
    "禁止",
    "不准",
    "不得以",
    "不得解除",
    "不得终止",
]


# ============================================================
# 授权关键词
# ============================================================

PERMISSION_KEYWORDS = [
    "可以",
    "有权",
    "可以解除",
    "可以终止",
    "可以订立",
]


# ============================================================
# 条件关键词
# ============================================================

CONDITION_KEYWORDS = [
    "有下列情形之一",
    "符合",
    "具备",
    "如果",
    "在",
    "当",
    "且",
    "并且",
    "同时",
    "连续",
    "满",
    "达到",
    "自",
    "经",
    "后",
]


# ============================================================
# 例外关键词
# ============================================================

EXCEPTION_KEYWORDS = [
    "除",
    "除外",
    "除非",
    "但",
    "但是",
    "除劳动者",
    "除劳动者提出",
    "不包括",
]


# ============================================================
# 法律后果关键词
# ============================================================

CONSEQUENCE_KEYWORDS = [
    "应当支付",
    "支付二倍工资",
    "承担责任",
    "承担法律责任",
    "无效",
    "视为",
    "可以解除",
    "可以终止",
    "应当订立",
    "应当签订",
]


# ============================================================
# 引用法条正则
# ============================================================

ARTICLE_REFERENCE_PATTERN = re.compile(
    r"(?:本法|本条例|劳动合同法|劳动法)?"
    r"(?:第[一二三四五六七八九十百千万零〇0-9]+条)"
    r"(?:第[一二三四五六七八九十百千万零〇0-9]+款)?"
    r"(?:第[一二三四五六七八九十百千万零〇0-9]+项)?"
)


# ============================================================
# 数据结构
# ============================================================

@dataclass
class LegalRule:

    law_name: str

    article_number: str

    article_text: str

    rule_type: str = RULE_TYPE_GENERAL

    rule_summary: str = ""

    conditions: List[str] = field(
        default_factory=list
    )

    exceptions: List[str] = field(
        default_factory=list
    )

    exclusions: List[str] = field(
        default_factory=list
    )

    obligations: List[str] = field(
        default_factory=list
    )

    rights: List[str] = field(
        default_factory=list
    )

    prohibitions: List[str] = field(
        default_factory=list
    )

    permissions: List[str] = field(
        default_factory=list
    )

    legal_consequences: List[str] = field(
        default_factory=list
    )

    referenced_articles: List[str] = field(
        default_factory=list
    )

    source: str = ""

    source_file: str = ""

    category: str = ""

    confidence: float = 0.0

    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:

        return {
            "law_name": self.law_name,
            "article_number": self.article_number,
            "article_text": self.article_text,
            "rule_type": self.rule_type,
            "rule_summary": self.rule_summary,
            "conditions": self.conditions,
            "exceptions": self.exceptions,
            "exclusions": self.exclusions,
            "obligations": self.obligations,
            "rights": self.rights,
            "prohibitions": self.prohibitions,
            "permissions": self.permissions,
            "legal_consequences": self.legal_consequences,
            "referenced_articles": self.referenced_articles,
            "source": self.source,
            "source_file": self.source_file,
            "category": self.category,
            "confidence": round(
                self.confidence,
                4,
            ),
            "metadata": self.metadata,
        }


# ============================================================
# 文本标准化
# ============================================================

def normalize_text(
    text: Any,
) -> str:

    if text is None:

        return ""

    text = str(text)

    text = text.replace(
        "\r",
        "",
    )

    text = text.replace(
        "\n",
        "",
    )

    text = text.replace(
        "　",
        "",
    )

    text = text.replace(
        " ",
        "",
    )

    return text.strip()


# ============================================================
# 获取字段
# ============================================================

def get_law_name(
    item: Dict[str, Any],
) -> str:

    return str(
        item.get("law_name")
        or item.get("法律名称")
        or ""
    ).strip()


def get_article_number(
    item: Dict[str, Any],
) -> str:

    return str(
        item.get("article_number")
        or item.get("法条")
        or item.get("article")
        or ""
    ).strip()


def get_article_text(
    item: Dict[str, Any],
) -> str:

    return str(
        item.get("article_text")
        or item.get("法条内容")
        or item.get("text")
        or ""
    ).strip()


def get_category(
    item: Dict[str, Any],
) -> str:

    return str(
        item.get("category")
        or ""
    ).strip()


def get_source(
    item: Dict[str, Any],
) -> str:

    return str(
        item.get("source")
        or ""
    ).strip()


def get_source_file(
    item: Dict[str, Any],
) -> str:

    return str(
        item.get("source_file")
        or ""
    ).strip()


# ============================================================
# 去除法条编号
# ============================================================

def remove_article_prefix(
    text: str,
) -> str:

    text = normalize_text(text)

    if not text:

        return ""

    text = re.sub(
        r"^第[一二三四五六七八九十百千万零〇0-9]+条",
        "",
        text,
        count=1,
    )

    return text.strip()


# ============================================================
# 分割法律条文
# ============================================================

def split_article_sentences(
    article_text: str,
) -> List[str]:

    article_text = normalize_text(
        article_text
    )

    if not article_text:

        return []

    article_text = remove_article_prefix(
        article_text
    )

    parts = re.split(
        r"(?<=[。；;])",
        article_text,
    )

    result = []

    for part in parts:

        part = part.strip(
            "。；;"
        )

        if part:

            result.append(
                part
            )

    return result


# ============================================================
# 提取引用法条
# ============================================================

def extract_referenced_articles(
    article_text: str,
) -> List[str]:

    article_text = normalize_text(
        article_text
    )

    if not article_text:

        return []

    matches = ARTICLE_REFERENCE_PATTERN.findall(
        article_text
    )

    result = []

    for match in matches:

        if not match:

            continue

        article_match = re.search(
            r"第[一二三四五六七八九十百千万零〇0-9]+条"
            r"(?:第[一二三四五六七八九十百千万零〇0-9]+款)?"
            r"(?:第[一二三四五六七八九十百千万零〇0-9]+项)?",
            match,
        )

        if article_match:

            value = article_match.group(
                0
            )

            if value not in result:

                result.append(
                    value
                )

    return result[:MAX_REFERENCES]


# ============================================================
# 提取“第十四条”特殊规则
# ============================================================

def extract_article_14_rule(
    article_text: str,
) -> Dict[str, Any]:

    text = normalize_text(
        article_text
    )

    result = {
        "conditions": [],
        "exceptions": [],
        "exclusions": [],
        "obligations": [],
        "rights": [],
        "permissions": [],
        "legal_consequences": [],
        "referenced_articles": [],
        "rule_summary": "",
        "rule_type": RULE_TYPE_DUTY,
    }

    # --------------------------------------------------------
    # 第十四条第三款核心规则
    # --------------------------------------------------------

    core_match = re.search(
        r"(连续订立二次固定期限劳动合同"
        r".*?"
        r"续订劳动合同的)"
        r"[，,]?"
        r"(?:则)?"
        r"应当订立无固定期限劳动合同",
        text,
    )

    if core_match:

        core_rule = core_match.group(
            1
        )

        result["rule_summary"] = (
            core_rule
            + "，应当订立无固定期限劳动合同"
        )

    else:

        if (
            "连续订立二次固定期限劳动合同"
            in text
        ):

            result["rule_summary"] = (
                "符合《劳动合同法》第十四条"
                "规定条件时，应当订立无固定期限劳动合同"
            )

    # --------------------------------------------------------
    # 条件一
    # --------------------------------------------------------

    if "连续订立二次固定期限劳动合同" in text:

        result["conditions"].append(
            "连续订立二次固定期限劳动合同"
        )

    # --------------------------------------------------------
    # 条件二
    # --------------------------------------------------------

    if "续订劳动合同" in text:

        result["conditions"].append(
            "属于续订劳动合同"
        )

    # --------------------------------------------------------
    # 条件三
    # --------------------------------------------------------

    if (
        "劳动者提出或者同意续订、订立劳动合同"
        in text
    ):

        result["conditions"].append(
            "劳动者提出或者同意续订、订立劳动合同"
        )

    # --------------------------------------------------------
    # 排除条件
    # --------------------------------------------------------

    if "没有本法第三十九条" in text:

        result["exclusions"].append(
            "劳动者不存在《劳动合同法》第三十九条规定的情形"
        )

    if "第四十条第一项、第二项" in text:

        result["exclusions"].append(
            "劳动者不存在《劳动合同法》第四十条第一项、第二项规定的情形"
        )

    # --------------------------------------------------------
    # 例外
    # --------------------------------------------------------

    if "除劳动者提出订立固定期限劳动合同外" in text:

        result["exceptions"].append(
            "劳动者提出订立固定期限劳动合同"
        )

    # --------------------------------------------------------
    # 法律义务
    # --------------------------------------------------------

    if "应当订立无固定期限劳动合同" in text:

        result["obligations"].append(
            "用人单位应当订立无固定期限劳动合同"
        )

    # --------------------------------------------------------
    # 引用法条
    # --------------------------------------------------------

    if "第三十九条" in text:

        result["referenced_articles"].append(
            "第三十九条"
        )

    if "第四十条" in text:

        result["referenced_articles"].append(
            "第四十条"
        )

    return result


# ============================================================
# 提取条件
# ============================================================

def extract_conditions(
    article_text: str,
) -> List[str]:

    text = normalize_text(
        article_text
    )

    conditions = []

    if not text:

        return conditions

    # --------------------------------------------------------
    # 常见“有下列情形之一”
    # --------------------------------------------------------

    if "有下列情形之一" in text:

        before, _, after = text.partition(
            "有下列情形之一"
        )

        if before:

            condition = before.strip(
                "，。；"
            )

            if condition:

                conditions.append(
                    condition
                )

    # --------------------------------------------------------
    # 连续订立
    # --------------------------------------------------------

    matches = re.findall(
        r"连续.{0,30}?(?:合同|工作|订立)",
        text,
    )

    for match in matches:

        if len(match) >= 4:

            conditions.append(
                match.strip(
                    "，。；"
                )
            )

    # --------------------------------------------------------
    # 满十年、满一年等
    # --------------------------------------------------------

    matches = re.findall(
        r"(?:连续工作|连续工作满|工作满)"
        r".{0,20}?(?:年|个月|日)",
        text,
    )

    for match in matches:

        conditions.append(
            match.strip(
                "，。；"
            )
        )

    # --------------------------------------------------------
    # “且”连接条件
    # --------------------------------------------------------

    parts = re.split(
        r"[，,]",
        text,
    )

    for part in parts:

        part = part.strip(
            "。；"
        )

        if "且" in part:

            sub_parts = re.split(
                r"且",
                part,
            )

            for sub_part in sub_parts:

                sub_part = sub_part.strip()

                if len(sub_part) >= 4:

                    conditions.append(
                        sub_part
                    )

    return unique_strings(
        conditions
    )[:MAX_CONDITIONS]


# ============================================================
# 提取例外
# ============================================================

def extract_exceptions(
    article_text: str,
) -> List[str]:

    text = normalize_text(
        article_text
    )

    exceptions = []

    if not text:

        return exceptions

    # --------------------------------------------------------
    # “除……外”
    # --------------------------------------------------------

    matches = re.findall(
        r"除.{1,80}?外",
        text,
    )

    for match in matches:

        match = match.strip(
            "，。；"
        )

        if match:

            exceptions.append(
                match
            )

    # --------------------------------------------------------
    # “但……”
    # --------------------------------------------------------

    matches = re.findall(
        r"但[^。；]{2,100}",
        text,
    )

    for match in matches:

        exceptions.append(
            match.strip(
                "，。；"
            )
        )

    # --------------------------------------------------------
    # “但是……”
    # --------------------------------------------------------

    matches = re.findall(
        r"但是[^。；]{2,100}",
        text,
    )

    for match in matches:

        exceptions.append(
            match.strip(
                "，。；"
            )
        )

    return unique_strings(
        exceptions
    )[:MAX_EXCEPTIONS]


# ============================================================
# 提取排除条件
# ============================================================

def extract_exclusions(
    article_text: str,
) -> List[str]:

    text = normalize_text(
        article_text
    )

    exclusions = []

    if not text:

        return exclusions

    # --------------------------------------------------------
    # “没有……情形”
    # --------------------------------------------------------

    matches = re.findall(
        r"没有[^。；]{2,100}?情形",
        text,
    )

    for match in matches:

        exclusions.append(
            match.strip(
                "，。；"
            )
        )

    # --------------------------------------------------------
    # “不存在……情形”
    # --------------------------------------------------------

    matches = re.findall(
        r"不存在[^。；]{2,100}?情形",
        text,
    )

    for match in matches:

        exclusions.append(
            match.strip(
                "，。；"
            )
        )

    return unique_strings(
        exclusions
    )[:MAX_EXCEPTIONS]


# ============================================================
# 提取义务
# ============================================================

def extract_obligations(
    article_text: str,
) -> List[str]:

    text = normalize_text(
        article_text
    )

    obligations = []

    if not text:

        return obligations

    sentences = split_article_sentences(
        text
    )

    for sentence in sentences:

        for keyword in DUTY_KEYWORDS:

            if keyword in sentence:

                obligations.append(
                    sentence
                )

                break

    return unique_strings(
        obligations
    )


# ============================================================
# 提取权利
# ============================================================

def extract_rights(
    article_text: str,
) -> List[str]:

    text = normalize_text(
        article_text
    )

    rights = []

    if not text:

        return rights

    sentences = split_article_sentences(
        text
    )

    for sentence in sentences:

        for keyword in RIGHT_KEYWORDS:

            if keyword in sentence:

                rights.append(
                    sentence
                )

                break

    return unique_strings(
        rights
    )


# ============================================================
# 提取禁止
# ============================================================

def extract_prohibitions(
    article_text: str,
) -> List[str]:

    text = normalize_text(
        article_text
    )

    prohibitions = []

    if not text:

        return prohibitions

    sentences = split_article_sentences(
        text
    )

    for sentence in sentences:

        for keyword in PROHIBITION_KEYWORDS:

            if keyword in sentence:

                prohibitions.append(
                    sentence
                )

                break

    return unique_strings(
        prohibitions
    )


# ============================================================
# 提取授权
# ============================================================

def extract_permissions(
    article_text: str,
) -> List[str]:

    text = normalize_text(
        article_text
    )

    permissions = []

    if not text:

        return permissions

    sentences = split_article_sentences(
        text
    )

    for sentence in sentences:

        if (
            "可以" in sentence
            and "应当" not in sentence
        ):

            permissions.append(
                sentence
            )

    return unique_strings(
        permissions
    )


# ============================================================
# 提取法律后果
# ============================================================

def extract_legal_consequences(
    article_text: str,
) -> List[str]:

    text = normalize_text(
        article_text
    )

    consequences = []

    if not text:

        return consequences

    sentences = split_article_sentences(
        text
    )

    for sentence in sentences:

        for keyword in CONSEQUENCE_KEYWORDS:

            if keyword in sentence:

                consequences.append(
                    sentence
                )

                break

    return unique_strings(
        consequences
    )


# ============================================================
# 判断规则类型
# ============================================================

def detect_rule_type(
    article_text: str,
) -> str:

    text = normalize_text(
        article_text
    )

    if not text:

        return RULE_TYPE_GENERAL

    # --------------------------------------------------------
    # 定义规则
    # --------------------------------------------------------

    if (
        "是指" in text
        or "是" in text
        and (
            "劳动合同" in text
            or "劳动者" in text
        )
    ):

        if (
            "应当" not in text
            and "可以" not in text
            and "不得" not in text
        ):

            return RULE_TYPE_DEFINITION

    # --------------------------------------------------------
    # 禁止规则
    # --------------------------------------------------------

    if "不得" in text:

        return RULE_TYPE_PROHIBITION

    # --------------------------------------------------------
    # 义务规则
    # --------------------------------------------------------

    if "应当" in text:

        return RULE_TYPE_DUTY

    # --------------------------------------------------------
    # 授权规则
    # --------------------------------------------------------

    if "可以" in text:

        return RULE_TYPE_PERMISSION

    # --------------------------------------------------------
    # 权利规则
    # --------------------------------------------------------

    if "有权" in text:

        return RULE_TYPE_RIGHT

    return RULE_TYPE_GENERAL


# ============================================================
# 生成规则摘要
# ============================================================

def build_rule_summary(
    article_text: str,
    rule_type: str,
    obligations: List[str],
    conditions: List[str],
    exceptions: List[str],
    exclusions: List[str],
    legal_consequences: List[str],
) -> str:

    text = normalize_text(
        article_text
    )

    # --------------------------------------------------------
    # 第十四条优先
    # --------------------------------------------------------

    if "连续订立二次固定期限劳动合同" in text:

        if "应当订立无固定期限劳动合同" in text:

            return (
                "连续订立二次固定期限劳动合同，"
                "并满足法定条件且属于续订劳动合同的，"
                "应当订立无固定期限劳动合同"
            )

    # --------------------------------------------------------
    # 一般规则
    # --------------------------------------------------------

    if obligations:

        return obligations[0]

    if legal_consequences:

        return legal_consequences[0]

    if exceptions:

        return exceptions[0]

    if conditions:

        return conditions[0]

    if text:

        if len(text) > 120:

            return text[:120] + "……"

        return text

    return ""


# ============================================================
# 计算规则置信度
# ============================================================

def calculate_confidence(
    article_text: str,
    rule_type: str,
    conditions: List[str],
    obligations: List[str],
    exceptions: List[str],
    referenced_articles: List[str],
) -> float:

    score = 0.50

    text = normalize_text(
        article_text
    )

    if not text:

        return 0.0

    if rule_type != RULE_TYPE_GENERAL:

        score += 0.10

    if obligations:

        score += 0.15

    if conditions:

        score += 0.10

    if exceptions:

        score += 0.05

    if referenced_articles:

        score += 0.05

    if len(text) > 50:

        score += 0.05

    return min(
        score,
        1.0,
    )


# ============================================================
# 唯一字符串
# ============================================================

def unique_strings(
    values: List[str],
) -> List[str]:

    result = []

    seen = set()

    for value in values:

        if value is None:

            continue

        value = str(
            value
        ).strip()

        if not value:

            continue

        if value in seen:

            continue

        seen.add(
            value
        )

        result.append(
            value
        )

    return result


# ============================================================
# 单条法条规则提取
# ============================================================

def extract_rule(
    item: Dict[str, Any],
) -> LegalRule:

    law_name = get_law_name(
        item
    )

    article_number = get_article_number(
        item
    )

    article_text = get_article_text(
        item
    )

    category = get_category(
        item
    )

    source = get_source(
        item
    )

    source_file = get_source_file(
        item
    )

    # --------------------------------------------------------
    # 特殊处理第十四条
    # --------------------------------------------------------

    is_article_14 = (
        law_name == "中华人民共和国劳动合同法"
        and article_number == "第十四条"
    )

    if is_article_14:

        special = extract_article_14_rule(
            article_text
        )

        conditions = unique_strings(
            special["conditions"]
            + extract_conditions(
                article_text
            )
        )

        exceptions = unique_strings(
            special["exceptions"]
            + extract_exceptions(
                article_text
            )
        )

        exclusions = unique_strings(
            special["exclusions"]
            + extract_exclusions(
                article_text
            )
        )

        obligations = unique_strings(
            special["obligations"]
            + extract_obligations(
                article_text
            )
        )

        rights = extract_rights(
            article_text
        )

        prohibitions = extract_prohibitions(
            article_text
        )

        permissions = extract_permissions(
            article_text
        )

        consequences = unique_strings(
            special["legal_consequences"]
            + extract_legal_consequences(
                article_text
            )
        )

        references = unique_strings(
            special["referenced_articles"]
            + extract_referenced_articles(
                article_text
            )
        )

        rule_type = special[
            "rule_type"
        ]

        rule_summary = (
            special[
                "rule_summary"
            ]
            or build_rule_summary(
                article_text,
                rule_type,
                obligations,
                conditions,
                exceptions,
                exclusions,
                consequences,
            )
        )

    else:

        conditions = extract_conditions(
            article_text
        )

        exceptions = extract_exceptions(
            article_text
        )

        exclusions = extract_exclusions(
            article_text
        )

        obligations = extract_obligations(
            article_text
        )

        rights = extract_rights(
            article_text
        )

        prohibitions = extract_prohibitions(
            article_text
        )

        permissions = extract_permissions(
            article_text
        )

        consequences = extract_legal_consequences(
            article_text
        )

        references = extract_referenced_articles(
            article_text
        )

        rule_type = detect_rule_type(
            article_text
        )

        rule_summary = build_rule_summary(
            article_text,
            rule_type,
            obligations,
            conditions,
            exceptions,
            exclusions,
            consequences,
        )

    confidence = calculate_confidence(
        article_text=article_text,
        rule_type=rule_type,
        conditions=conditions,
        obligations=obligations,
        exceptions=exceptions,
        referenced_articles=references,
    )

    metadata = dict(
        item
    )

    return LegalRule(
        law_name=law_name,
        article_number=article_number,
        article_text=article_text,
        rule_type=rule_type,
        rule_summary=rule_summary,
        conditions=conditions[
            :MAX_CONDITIONS
        ],
        exceptions=exceptions[
            :MAX_EXCEPTIONS
        ],
        exclusions=exclusions[
            :MAX_EXCEPTIONS
        ],
        obligations=obligations,
        rights=rights,
        prohibitions=prohibitions,
        permissions=permissions,
        legal_consequences=consequences,
        referenced_articles=references[
            :MAX_REFERENCES
        ],
        source=source,
        source_file=source_file,
        category=category,
        confidence=confidence,
        metadata=metadata,
    )


# ============================================================
# 多条法律规则提取
# ============================================================

def extract_rules(
    laws: List[Dict[str, Any]],
    max_rules: int = MAX_RULES,
) -> List[Dict[str, Any]]:

    if not laws:

        return []

    rules = []

    seen = set()

    for item in laws:

        if not isinstance(
            item,
            dict,
        ):

            continue

        law_name = get_law_name(
            item
        )

        article_number = get_article_number(
            item
        )

        key = (
            normalize_text(
                law_name
            ),
            normalize_text(
                article_number
            ),
        )

        if key in seen:

            continue

        seen.add(
            key
        )

        rule = extract_rule(
            item
        )

        rules.append(
            rule
        )

        if len(rules) >= max_rules:

            break

    return [
        rule.to_dict()
        for rule in rules
    ]


# ============================================================
# 按法律规则类型排序
# ============================================================

RULE_TYPE_ORDER = {
    RULE_TYPE_DUTY: 0,
    RULE_TYPE_PROHIBITION: 1,
    RULE_TYPE_RIGHT: 2,
    RULE_TYPE_PERMISSION: 3,
    RULE_TYPE_CONDITION: 4,
    RULE_TYPE_CONSEQUENCE: 5,
    RULE_TYPE_DEFINITION: 6,
    RULE_TYPE_GENERAL: 7,
}


def sort_rules(
    rules: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:

    return sorted(
        rules,
        key=lambda item: (
            RULE_TYPE_ORDER.get(
                item.get(
                    "rule_type",
                    RULE_TYPE_GENERAL,
                ),
                99,
            ),
            -float(
                item.get(
                    "confidence",
                    0.0,
                )
                or 0.0
            ),
        ),
    )


# ============================================================
# 获取核心法律规则
# ============================================================

def select_core_rules(
    rules: List[Dict[str, Any]],
    max_core: int = 5,
) -> List[Dict[str, Any]]:

    if not rules:

        return []

    core = []

    # --------------------------------------------------------
    # 第一优先级：
    # Ranker 已经判定为核心法条
    # --------------------------------------------------------

    for rule in rules:

        if rule.get(
            "category"
        ) == "核心法条":

            core.append(
                rule
            )

    # --------------------------------------------------------
    # 第二优先级：
    # 义务规则
    # --------------------------------------------------------

    if len(core) < max_core:

        for rule in rules:

            if rule in core:

                continue

            if rule.get(
                "rule_type"
            ) == RULE_TYPE_DUTY:

                core.append(
                    rule
                )

            if len(core) >= max_core:

                break

    return core[
        :max_core
    ]


# ============================================================
# 构建 V6.0-4 使用的规则 Context
# ============================================================

def build_rule_context(
    rules: List[Dict[str, Any]],
) -> str:

    if not rules:

        return ""

    lines = []

    lines.append(
        "===================="
    )

    lines.append(
        "结构化法律规则"
    )

    lines.append(
        "===================="
    )

    for index, rule in enumerate(
        rules,
        start=1,
    ):

        lines.append(
            f"【规则 {index}】"
        )

        lines.append(
            f"法律：{rule.get('law_name', '')}"
        )

        lines.append(
            f"法条：{rule.get('article_number', '')}"
        )

        lines.append(
            f"规则类型：{rule.get('rule_type', '')}"
        )

        lines.append(
            f"规则摘要：{rule.get('rule_summary', '')}"
        )

        conditions = rule.get(
            "conditions",
            [],
        )

        if conditions:

            lines.append(
                "条件："
            )

            for condition in conditions:

                lines.append(
                    f"- {condition}"
                )

        exclusions = rule.get(
            "exclusions",
            [],
        )

        if exclusions:

            lines.append(
                "排除条件："
            )

            for exclusion in exclusions:

                lines.append(
                    f"- {exclusion}"
                )

        exceptions = rule.get(
            "exceptions",
            [],
        )

        if exceptions:

            lines.append(
                "例外："
            )

            for exception in exceptions:

                lines.append(
                    f"- {exception}"
                )

        obligations = rule.get(
            "obligations",
            [],
        )

        if obligations:

            lines.append(
                "法律义务："
            )

            for obligation in obligations:

                lines.append(
                    f"- {obligation}"
                )

        consequences = rule.get(
            "legal_consequences",
            [],
        )

        if consequences:

            lines.append(
                "法律后果："
            )

            for consequence in consequences:

                lines.append(
                    f"- {consequence}"
                )

        references = rule.get(
            "referenced_articles",
            [],
        )

        if references:

            lines.append(
                "引用法条："
            )

            lines.append(
                "、".join(
                    references
                )
            )

        lines.append(
            ""
        )

    return "\n".join(
        lines
    )


# ============================================================
# 调试输出
# ============================================================

def print_rule(
    rule: Dict[str, Any],
    index: int,
) -> None:

    print()

    print(
        f"【法律规则 {index}】"
    )

    print(
        f"法律：{rule.get('law_name')}"
    )

    print(
        f"法条：{rule.get('article_number')}"
    )

    print(
        f"分类：{rule.get('category')}"
    )

    print(
        f"规则类型：{rule.get('rule_type')}"
    )

    print(
        f"规则摘要：{rule.get('rule_summary')}"
    )

    print(
        f"置信度：{rule.get('confidence')}"
    )

    print()

    print(
        "条件："
    )

    for item in rule.get(
        "conditions",
        [],
    ):

        print(
            f"  - {item}"
        )

    print()

    print(
        "排除条件："
    )

    for item in rule.get(
        "exclusions",
        [],
    ):

        print(
            f"  - {item}"
        )

    print()

    print(
        "例外："
    )

    for item in rule.get(
        "exceptions",
        [],
    ):

        print(
            f"  - {item}"
        )

    print()

    print(
        "法律义务："
    )

    for item in rule.get(
        "obligations",
        [],
    ):

        print(
            f"  - {item}"
        )

    print()

    print(
        "法律后果："
    )

    for item in rule.get(
        "legal_consequences",
        [],
    ):

        print(
            f"  - {item}"
        )

    print()

    print(
        "引用法条："
    )

    print(
        "、".join(
            rule.get(
                "referenced_articles",
                [],
            )
        )
    )


# ============================================================
# 测试数据
# ============================================================

def demo() -> None:

    question = (
        "公司连续签订三次固定期限劳动合同后，"
        "是否必须签订无固定期限劳动合同？"
    )

    print()
    print("=" * 70)
    print("RAG V6.0-3 - Legal Rule Extractor")
    print("=" * 70)

    print()
    print(
        "问题："
    )

    print(
        question
    )

    laws = [

        {
            "law_name": "中华人民共和国劳动合同法",
            "article_number": "第十四条",
            "article_text": (
                "第十四条 无固定期限劳动合同，是指用人单位与劳动者约定"
                "无确定终止时间的劳动合同。"
                "用人单位与劳动者协商一致，可以订立无固定期限劳动合同。"
                "有下列情形之一，劳动者提出或者同意续订、订立劳动合同的，"
                "除劳动者提出订立固定期限劳动合同外，应当订立无固定期限劳动合同："
                "（一）劳动者在该用人单位连续工作满十年的；"
                "（二）用人单位初次实行劳动合同制度或者国有企业改制重新订立劳动合同时，"
                "劳动者在该用人单位连续工作满十年且距法定退休年龄不足十年的；"
                "（三）连续订立二次固定期限劳动合同，且劳动者没有本法第三十九条"
                "和第四十条第一项、第二项规定的情形，续订劳动合同的。"
                "用人单位自用工之日起满一年不与劳动者订立书面劳动合同的，"
                "视为用人单位与劳动者已订立无固定期限劳动合同。"
            ),
            "category": "核心法条",
            "source": "V6.0-2 Relevance Ranker",
            "score": 0.6503,
        },

        {
            "law_name": "中华人民共和国劳动合同法",
            "article_number": "第三十九条",
            "article_text": (
                "第三十九条 劳动者有下列情形之一的，"
                "用人单位可以解除劳动合同："
                "（一）在试用期间被证明不符合录用条件的；"
                "（二）严重违反用人单位的规章制度的；"
                "（三）严重失职，营私舞弊，给用人单位造成重大损害的；"
                "（四）劳动者同时与其他用人单位建立劳动关系，"
                "对完成本单位的工作任务造成严重影响，"
                "或者经用人单位提出，拒不改正的；"
                "（五）因本法第二十六条第一款第一项规定的情形致使劳动合同无效的；"
                "（六）被依法追究刑事责任的。"
            ),
            "category": "关联法条",
            "source": "法律引用自动扩展",
            "score": 0.0,
        },

        {
            "law_name": "中华人民共和国劳动合同法",
            "article_number": "第四十条",
            "article_text": (
                "第四十条 有下列情形之一的，"
                "用人单位提前三十日以书面形式通知劳动者本人"
                "或者额外支付劳动者一个月工资后，可以解除劳动合同："
                "（一）劳动者患病或者非因工负伤，在规定的医疗期满后"
                "不能从事原工作，也不能从事由用人单位另行安排的工作的；"
                "（二）劳动者不能胜任工作，经过培训或者调整工作岗位，"
                "仍不能胜任工作的。"
            ),
            "category": "关联法条",
            "source": "法律引用自动扩展",
            "score": 0.0,
        },

        {
            "law_name": "中华人民共和国劳动合同法",
            "article_number": "第八十二条",
            "article_text": (
                "第八十二条 用人单位违反本法规定不与劳动者订立"
                "无固定期限劳动合同的，自应当订立无固定期限劳动合同之日起"
                "向劳动者每月支付二倍的工资。"
            ),
            "category": "关联法条",
            "source": "V6.0-2 Relevance Ranker",
            "score": 0.4685,
        },
    ]

    # ========================================================
    # 提取规则
    # ========================================================

    rules = extract_rules(
        laws
    )

    rules = sort_rules(
        rules
    )

    print()
    print("=" * 70)
    print("规则提取结果")
    print("=" * 70)

    for index, rule in enumerate(
        rules,
        start=1,
    ):

        print_rule(
            rule,
            index,
        )

    # ========================================================
    # 核心规则
    # ========================================================

    print()
    print("=" * 70)
    print("核心法律规则")
    print("=" * 70)

    core_rules = select_core_rules(
        rules
    )

    for index, rule in enumerate(
        core_rules,
        start=1,
    ):

        print_rule(
            rule,
            index,
        )

    # ========================================================
    # Rule Context
    # ========================================================

    print()
    print("=" * 70)
    print("V6.0-4 Rule Context")
    print("=" * 70)

    rule_context = build_rule_context(
        core_rules
    )

    print()
    print(
        rule_context
    )


# ============================================================
# 模块直接运行
# ============================================================

if __name__ == "__main__":

    demo()