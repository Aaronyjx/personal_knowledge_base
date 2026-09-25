# -*- coding: utf-8 -*-

"""
RAG V6.0-4
Legal Rule Normalizer

功能：

1. 法律规则结构化
2. 规则条件清洗
3. 条件重复去除
4. 法条原文噪声清理
5. 法律义务规范化
6. 法律后果规范化
7. 排除条件规范化
8. 例外条件规范化
9. 引用法条规范化
10. 针对《劳动合同法》第十四条进行专门规则归一化

V6.0-4 核心升级：

    V6.0-3 Legal Rule Extractor
                    ↓
             原始法律规则
                    ↓
          Legal Rule Normalizer
                    ↓
             规范化法律规则
                    ↓
             V6.0-5 Rule Engine

主要解决 V6.0-3 中出现的问题：

    例如第十四条原始提取结果：

    - 连续订立二次固定期限劳动合同
    - 属于续订劳动合同
    - 连续工作
    - 连续订立
    - 连续工作满十年
    - 第十四条无固定期限劳动合同，是指……
    - 距法定退休年龄不足十年的……
    - 劳动者没有第三十九条……
    - 除劳动者提出订立固定期限劳动合同外

这些内容不能全部作为同一级别的“条件”。

V6.0-4 将其规范化为：

    触发条件：
        1. 连续订立二次固定期限劳动合同
        2. 续订劳动合同
        3. 劳动者提出或者同意续订、订立劳动合同

    排除条件：
        1. 存在第三十九条规定的情形
        2. 存在第四十条第一项规定的情形
        3. 存在第四十条第二项规定的情形

    例外：
        1. 劳动者提出订立固定期限劳动合同

    法律义务：
        用人单位应当订立无固定期限劳动合同

    法律后果：
        应当订立无固定期限劳动合同

注意：

V6.0-4 不负责判断具体案件事实。

例如：

    “公司已经与员工签了三次合同”

不是由本模块直接判断：

    “已经满足第十四条。”

V6.0-4 只负责把法律规则整理成：

    条件
        ↓
    排除条件
        ↓
    例外
        ↓
    法律义务
        ↓
    法律后果

具体事实判断交给后续：

    V6.0-5 Rule Engine
"""


from dataclasses import dataclass, field
from typing import List, Dict, Optional
import re


# ============================================================
# 数据结构
# ============================================================

@dataclass
class NormalizedLegalRule:
    """
    V6.0-4 规范化法律规则。

    一个 LegalRule 对应一个核心法律规则。

    例如：

        《中华人民共和国劳动合同法》第十四条

    可以形成：

        rule_type = 义务规则

        conditions = [
            "连续订立二次固定期限劳动合同",
            "续订劳动合同",
            "劳动者提出或者同意续订、订立劳动合同",
        ]

        exclusions = [
            "存在第三十九条规定的情形",
            "存在第四十条第一项规定的情形",
            "存在第四十条第二项规定的情形",
        ]

        exceptions = [
            "劳动者提出订立固定期限劳动合同",
        ]
    """

    law_name: str

    article_number: str

    category: str = ""

    rule_type: str = ""

    summary: str = ""

    conditions: List[str] = field(
        default_factory=list
    )

    exclusions: List[str] = field(
        default_factory=list
    )

    exceptions: List[str] = field(
        default_factory=list
    )

    obligations: List[str] = field(
        default_factory=list
    )

    consequences: List[str] = field(
        default_factory=list
    )

    cited_articles: List[str] = field(
        default_factory=list
    )

    confidence: float = 0.0

    source_text: str = ""


# ============================================================
# 基础工具
# ============================================================

def clean_text(
    text: Optional[str],
) -> str:
    """
    清理普通文本。

    主要处理：

    1. None
    2. 多余空格
    3. 多余换行
    4. 中文标点前后的异常空格
    """

    if not text:
        return ""

    text = str(text)

    text = text.replace(
        "\r\n",
        "\n",
    )

    text = text.replace(
        "\r",
        "\n",
    )

    text = re.sub(
        r"[ \t]+",
        " ",
        text,
    )

    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text,
    )

    text = text.strip()

    return text


def normalize_spaces(
    text: str,
) -> str:
    """
    统一文本中的空白字符。
    """

    if not text:
        return ""

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip()


def normalize_punctuation(
    text: str,
) -> str:
    """
    统一部分中文标点。

    注意：

    不进行激进的标点替换，
    避免改变法律原文含义。
    """

    if not text:
        return ""

    text = text.replace(
        "；；",
        "；",
    )

    text = text.replace(
        "，，",
        "，",
    )

    text = re.sub(
        r"\s+([，。；：、）】])",
        r"\1",
        text,
    )

    text = re.sub(
        r"([（【])\s+",
        r"\1",
        text,
    )

    return text.strip()


def normalize_text(
    text: str,
) -> str:
    """
    综合文本规范化。
    """

    text = clean_text(
        text
    )

    text = normalize_spaces(
        text
    )

    text = normalize_punctuation(
        text
    )

    return text


# ============================================================
# 条件去重
# ============================================================

def normalize_condition(
    condition: str,
) -> str:
    """
    对单个法律条件进行规范化。

    这里只做语言层面的清理。

    不改变法律规则。
    """

    condition = normalize_text(
        condition
    )

    if not condition:
        return ""

    # 去掉明显的列表编号
    condition = re.sub(
        r"^[（(]?[一二三四五六七八九十]+[）)]\s*",
        "",
        condition,
    )

    condition = re.sub(
        r"^\d+[.、．]\s*",
        "",
        condition,
    )

    # 去掉明显属于法条标题的前缀
    condition = re.sub(
        r"^第[一二三四五六七八九十百]+条\s*",
        "",
        condition,
    )

    condition = normalize_text(
        condition
    )

    return condition


def condition_key(
    condition: str,
) -> str:
    """
    生成条件去重 Key。

    用于：

        “连续订立”
        “连续订立”
        “连续订立。”

    视为相同条件。

    不进行语义推断。
    """

    condition = normalize_condition(
        condition
    )

    condition = re.sub(
        r"[，。；：、\s]",
        "",
        condition,
    )

    return condition


def deduplicate_conditions(
    conditions: List[str],
) -> List[str]:
    """
    条件去重。

    保留第一次出现的条件。
    """

    result = []

    seen = set()

    for condition in conditions:

        normalized = normalize_condition(
            condition
        )

        if not normalized:
            continue

        key = condition_key(
            normalized
        )

        if key in seen:
            continue

        seen.add(
            key
        )

        result.append(
            normalized
        )

    return result


# ============================================================
# 删除明显噪声
# ============================================================

def is_law_text_noise(
    text: str,
) -> bool:
    """
    判断某一条件是否明显属于法条原文噪声。

    例如：

        第十四条无固定期限劳动合同，是指……

    这种内容不是“连续订立二次固定期限劳动合同”的
    具体案件判断条件。

    注意：

    这里只删除明显噪声，
    不进行复杂法律推理。
    """

    if not text:
        return True

    text = normalize_text(
        text
    )

    noise_patterns = [

        r"^第[一二三四五六七八九十百]+条.*是指",

        r"^第[一二三四五六七八九十百]+条.*可以订立",

        r"^用人单位与劳动者协商一致，可以订立",

        r"^有下列情形之一.*应当订立",

        r"^有下列情形之一.*可以解除",

        r"^用人单位自用工之日起",

    ]

    for pattern in noise_patterns:

        if re.search(
            pattern,
            text,
        ):

            return True

    return False


def remove_noise_conditions(
    conditions: List[str],
) -> List[str]:
    """
    删除明显法条原文噪声。
    """

    result = []

    for condition in conditions:

        normalized = normalize_condition(
            condition
        )

        if not normalized:
            continue

        if is_law_text_noise(
            normalized
        ):
            continue

        result.append(
            normalized
        )

    return deduplicate_conditions(
        result
    )


# ============================================================
# 条件分类
# ============================================================

def classify_condition(
    condition: str,
) -> str:
    """
    对条件进行初步分类。

    返回：

        trigger
        exclusion
        exception
        noise
        other

    这里只做规则模式匹配。

    不负责判断具体案件。
    """

    condition = normalize_condition(
        condition
    )

    if not condition:
        return "noise"

    if is_law_text_noise(
        condition
    ):
        return "noise"

    # --------------------------------------------------------
    # 例外
    # --------------------------------------------------------

    if (
        "除劳动者提出订立固定期限劳动合同外"
        in condition
    ):

        return "exception"

    if (
        "劳动者提出订立固定期限劳动合同"
        in condition
    ):

        return "exception"

    # --------------------------------------------------------
    # 排除条件
    # --------------------------------------------------------

    if (
        "没有本法第三十九条"
        in condition
    ):

        return "exclusion"

    if (
        "不存在《劳动合同法》第三十九条"
        in condition
    ):

        return "exclusion"

    if (
        "不存在《劳动合同法》第四十条"
        in condition
    ):

        return "exclusion"

    if (
        "没有本法第四十条"
        in condition
    ):

        return "exclusion"

    # --------------------------------------------------------
    # 第三十九条
    # --------------------------------------------------------

    if (
        "第三十九条规定的情形"
        in condition
    ):

        return "exclusion"

    # --------------------------------------------------------
    # 第四十条
    # --------------------------------------------------------

    if (
        "第四十条第一项"
        in condition
    ):

        return "exclusion"

    if (
        "第四十条第二项"
        in condition
    ):

        return "exclusion"

    # --------------------------------------------------------
    # 触发条件
    # --------------------------------------------------------

    if (
        "连续订立二次固定期限劳动合同"
        in condition
    ):

        return "trigger"

    if (
        "续订劳动合同"
        in condition
    ):

        return "trigger"

    if (
        "劳动者提出或者同意续订"
        in condition
    ):

        return "trigger"

    if (
        "劳动者提出或者同意续订、订立劳动合同"
        in condition
    ):

        return "trigger"

    return "other"


# ============================================================
# 第十四条专门规范化
# ============================================================

def normalize_article_14(
    rule: NormalizedLegalRule,
) -> NormalizedLegalRule:
    """
    专门规范化：

        《中华人民共和国劳动合同法》第十四条

    这是 V6.0-4 的核心升级。

    第十四条原始文本包含多个不同法律规则：

        1. 协商订立
        2. 连续工作十年
        3. 国企改制等特殊情形
        4. 连续订立二次固定期限劳动合同
        5. 一年未签书面合同

    对当前“连续固定期限劳动合同”的问题，
    我们只保留相关规则：

        连续订立二次固定期限劳动合同
        +
        续订
        +
        劳动者提出或者同意
        +
        排除第三十九条
        +
        排除第四十条第一、二项
        +
        固定期限合同例外

    注意：

    本函数不是修改法律。

    而是从已经提取的法律规则中，
    提取与当前规则类型直接相关的结构。
    """

    if (
        rule.law_name
        != "中华人民共和国劳动合同法"
    ):

        return rule

    if (
        normalize_article_number(
            rule.article_number
        )
        != "第十四条"
    ):

        return rule

    # --------------------------------------------------------
    # 固定规则类型
    # --------------------------------------------------------

    rule.rule_type = "义务规则"

    rule.category = "核心法条"

    rule.summary = (
        "符合《劳动合同法》第十四条规定条件时，"
        "应当订立无固定期限劳动合同"
    )

    # --------------------------------------------------------
    # 重新构建条件
    #
    # 不再直接相信 V6.0-3 提取出来的杂乱条件。
    # --------------------------------------------------------

    rule.conditions = [

        "连续订立二次固定期限劳动合同",

        "续订劳动合同",

        "劳动者提出或者同意续订、订立劳动合同",

    ]

    # --------------------------------------------------------
    # 排除条件
    # --------------------------------------------------------

    rule.exclusions = [

        "劳动者存在《劳动合同法》第三十九条规定的情形",

        "劳动者存在《劳动合同法》第四十条第一项规定的情形",

        "劳动者存在《劳动合同法》第四十条第二项规定的情形",

    ]

    # --------------------------------------------------------
    # 例外
    # --------------------------------------------------------

    rule.exceptions = [

        "劳动者提出订立固定期限劳动合同",

    ]

    # --------------------------------------------------------
    # 法律义务
    # --------------------------------------------------------

    rule.obligations = [

        "用人单位应当订立无固定期限劳动合同",

    ]

    # --------------------------------------------------------
    # 法律后果
    # --------------------------------------------------------

    rule.consequences = [

        "符合第十四条规定条件时，用人单位应当订立无固定期限劳动合同",

    ]

    # --------------------------------------------------------
    # 引用法条
    # --------------------------------------------------------

    rule.cited_articles = normalize_cited_articles(
        [
            "第十四条",
            "第三十九条",
            "第四十条",
            "第四十条第一项",
            "第四十条第二项",
        ]
    )

    return rule


# ============================================================
# 法条编号规范化
# ============================================================

def normalize_article_number(
    article_number: str,
) -> str:
    """
    规范化法条编号。

    例如：

        第14条
        第十四条
        十四条

    最终尽量保持项目现有中文格式：

        第十四条
    """

    if not article_number:
        return ""

    article_number = normalize_text(
        article_number
    )

    if article_number == "十四条":
        return "第十四条"

    if article_number == "第三十九条":
        return "第三十九条"

    if article_number == "第四十条":
        return "第四十条"

    if article_number == "第八十二条":
        return "第八十二条"

    match = re.match(
        r"第?(\d+)条",
        article_number,
    )

    if match:

        number = int(
            match.group(1)
        )

        chinese = number_to_chinese(
            number
        )

        return f"第{chinese}条"

    return article_number


def number_to_chinese(
    number: int,
) -> str:
    """
    阿拉伯数字转中文数字。

    当前法律项目主要处理普通法条编号，
    实现 1～999 即可。
    """

    if number <= 0:
        return str(number)

    digits = [
        "零",
        "一",
        "二",
        "三",
        "四",
        "五",
        "六",
        "七",
        "八",
        "九",
    ]

    if number < 10:

        return digits[number]

    if number < 20:

        if number == 10:
            return "十"

        return "十" + digits[number % 10]

    if number < 100:

        tens = number // 10

        ones = number % 10

        result = (
            digits[tens]
            + "十"
        )

        if ones:

            result += digits[ones]

        return result

    if number < 1000:

        hundreds = number // 100

        remainder = number % 100

        result = (
            digits[hundreds]
            + "百"
        )

        if remainder == 0:

            return result

        if remainder < 10:

            result += "零"

            result += digits[remainder]

            return result

        tens = remainder // 10

        ones = remainder % 10

        result += digits[tens]

        result += "十"

        if ones:

            result += digits[ones]

        return result

    return str(number)


# ============================================================
# 引用法条规范化
# ============================================================

def normalize_cited_articles(
    articles: List[str],
) -> List[str]:
    """
    规范化引用法条。

    同时：

        去重
        排序

    但不改变引用关系。
    """

    if not articles:
        return []

    result = []

    seen = set()

    for article in articles:

        article = normalize_text(
            article
        )

        if not article:
            continue

        article = normalize_article_number(
            article
        )

        key = re.sub(
            r"\s+",
            "",
            article,
        )

        if key in seen:
            continue

        seen.add(
            key
        )

        result.append(
            article
        )

    return result


# ============================================================
# 法律义务规范化
# ============================================================

def normalize_obligations(
    obligations: List[str],
) -> List[str]:
    """
    规范化法律义务。

    特别保留：

        应当
        可以
        不得

    不改变法律义务强度。

    例如：

        应当订立

    不能转换成：

        可以订立
    """

    result = []

    for obligation in obligations:

        obligation = normalize_text(
            obligation
        )

        if not obligation:
            continue

        # 删除明显重复
        obligation = re.sub(
            r"^法律义务[:：]\s*",
            "",
            obligation,
        )

        result.append(
            obligation
        )

    return deduplicate_conditions(
        result
    )


# ============================================================
# 法律后果规范化
# ============================================================

def normalize_consequences(
    consequences: List[str],
) -> List[str]:
    """
    规范化法律后果。

    注意：

    法律后果与法律义务不是完全相同的概念。

    例如：

        法律义务：
            应当订立无固定期限劳动合同

        法律后果：
            不履行该义务可能产生二倍工资责任

    V6.0-4 不自行创造法律后果。

    只有原始规则明确提供时才保留。
    """

    result = []

    for consequence in consequences:

        consequence = normalize_text(
            consequence
        )

        if not consequence:
            continue

        result.append(
            consequence
        )

    return deduplicate_conditions(
        result
    )


# ============================================================
# 规则整体规范化
# ============================================================

def normalize_rule(
    rule: NormalizedLegalRule,
) -> NormalizedLegalRule:
    """
    对单条 LegalRule 进行整体规范化。

    流程：

        1. 清理基本字段
        2. 规范法条编号
        3. 清洗条件
        4. 去除噪声
        5. 条件分类
        6. 规范法律义务
        7. 规范法律后果
        8. 规范引用法条
        9. 特殊规则处理
    """

    rule.law_name = normalize_text(
        rule.law_name
    )

    rule.article_number = normalize_article_number(
        rule.article_number
    )

    rule.category = normalize_text(
        rule.category
    )

    rule.rule_type = normalize_text(
        rule.rule_type
    )

    rule.summary = normalize_text(
        rule.summary
    )

    rule.source_text = clean_text(
        rule.source_text
    )

    # --------------------------------------------------------
    # 原始条件
    # --------------------------------------------------------

    raw_conditions = (
        rule.conditions
        or []
    )

    raw_conditions = (
        remove_noise_conditions(
            raw_conditions
        )
    )

    trigger_conditions = []

    exclusion_conditions = []

    exception_conditions = []

    other_conditions = []

    for condition in raw_conditions:

        condition_type = classify_condition(
            condition
        )

        if condition_type == "trigger":

            trigger_conditions.append(
                condition
            )

        elif condition_type == "exclusion":

            exclusion_conditions.append(
                condition
            )

        elif condition_type == "exception":

            exception_conditions.append(
                condition
            )

        elif condition_type == "other":

            other_conditions.append(
                condition
            )

    # --------------------------------------------------------
    # 保留普通条件
    #
    # 对非专门规则，
    # 不贸然删除未知条件。
    # --------------------------------------------------------

    rule.conditions = deduplicate_conditions(
        trigger_conditions
        + other_conditions
    )

    rule.exclusions = deduplicate_conditions(
        (
            rule.exclusions
            or []
        )
        + exclusion_conditions
    )

    rule.exceptions = deduplicate_conditions(
        (
            rule.exceptions
            or []
        )
        + exception_conditions
    )

    rule.obligations = normalize_obligations(
        rule.obligations
        or []
    )

    rule.consequences = normalize_consequences(
        rule.consequences
        or []
    )

    rule.cited_articles = normalize_cited_articles(
        rule.cited_articles
        or []
    )

    # --------------------------------------------------------
    # 第十四条特殊规范化
    # --------------------------------------------------------

    if (
        rule.law_name
        == "中华人民共和国劳动合同法"
        and rule.article_number
        == "第十四条"
    ):

        rule = normalize_article_14(
            rule
        )

    return rule


# ============================================================
# 从 V6.0-3 Dict 创建规则
# ============================================================

def rule_from_dict(
    data: Dict,
) -> NormalizedLegalRule:
    """
    将 V6.0-3 Legal Rule Dictionary
    转换成 NormalizedLegalRule。

    支持字段：

        law_name
        article_number
        category
        rule_type
        summary
        conditions
        exclusions
        exceptions
        obligations
        consequences
        cited_articles
        confidence
        source_text
    """

    if not data:

        raise ValueError(
            "rule_from_dict() 收到空数据"
        )

    return NormalizedLegalRule(

        law_name=str(
            data.get(
                "law_name",
                "",
            )
        ),

        article_number=str(
            data.get(
                "article_number",
                "",
            )
        ),

        category=str(
            data.get(
                "category",
                "",
            )
        ),

        rule_type=str(
            data.get(
                "rule_type",
                "",
            )
        ),

        summary=str(
            data.get(
                "summary",
                "",
            )
        ),

        conditions=list(
            data.get(
                "conditions",
                [],
            )
            or []
        ),

        exclusions=list(
            data.get(
                "exclusions",
                [],
            )
            or []
        ),

        exceptions=list(
            data.get(
                "exceptions",
                [],
            )
            or []
        ),

        obligations=list(
            data.get(
                "obligations",
                [],
            )
            or []
        ),

        consequences=list(
            data.get(
                "consequences",
                [],
            )
            or []
        ),

        cited_articles=list(
            data.get(
                "cited_articles",
                [],
            )
            or []
        ),

        confidence=float(
            data.get(
                "confidence",
                0.0,
            )
            or 0.0
        ),

        source_text=str(
            data.get(
                "source_text",
                "",
            )
            or ""
        ),
    )


# ============================================================
# 转换成 Dictionary
# ============================================================

def rule_to_dict(
    rule: NormalizedLegalRule,
) -> Dict:
    """
    将规范化规则转换成普通 Dictionary。

    方便：

        JSON
        RAG Context
        Rule Engine
        Debug
    """

    return {

        "law_name":
            rule.law_name,

        "article_number":
            rule.article_number,

        "category":
            rule.category,

        "rule_type":
            rule.rule_type,

        "summary":
            rule.summary,

        "conditions":
            list(
                rule.conditions
            ),

        "exclusions":
            list(
                rule.exclusions
            ),

        "exceptions":
            list(
                rule.exceptions
            ),

        "obligations":
            list(
                rule.obligations
            ),

        "consequences":
            list(
                rule.consequences
            ),

        "cited_articles":
            list(
                rule.cited_articles
            ),

        "confidence":
            rule.confidence,

        "source_text":
            rule.source_text,

    }


# ============================================================
# 批量规则规范化
# ============================================================

def normalize_rules(
    rules: List,
) -> List[NormalizedLegalRule]:
    """
    批量规范化法律规则。

    输入可以是：

        NormalizedLegalRule

    或：

        Dict

    输出统一为：

        List[NormalizedLegalRule]
    """

    if not rules:

        return []

    result = []

    for item in rules:

        if isinstance(
            item,
            NormalizedLegalRule,
        ):

            rule = item

        elif isinstance(
            item,
            dict,
        ):

            rule = rule_from_dict(
                item
            )

        else:

            continue

        normalized = normalize_rule(
            rule
        )

        result.append(
            normalized
        )

    return result


# ============================================================
# 查找核心规则
# ============================================================

def get_core_rules(
    rules: List[NormalizedLegalRule],
) -> List[NormalizedLegalRule]:
    """
    获取核心法律规则。

    优先：

        category == 核心法条

    """

    if not rules:

        return []

    result = []

    for rule in rules:

        if rule.category == "核心法条":

            result.append(
                rule
            )

    return result


# ============================================================
# 按法律 + 法条查找
# ============================================================

def find_rule(
    rules: List[NormalizedLegalRule],
    law_name: str,
    article_number: str,
) -> Optional[NormalizedLegalRule]:
    """
    精确查找法律规则。
    """

    law_name = normalize_text(
        law_name
    )

    article_number = normalize_article_number(
        article_number
    )

    for rule in rules:

        if (
            rule.law_name == law_name
            and
            rule.article_number
            == article_number
        ):

            return rule

    return None


# ============================================================
# V6.0-4 Rule Context
# ============================================================

def build_rule_context(
    rules: List[NormalizedLegalRule],
) -> str:
    """
    构建结构化法律规则 Context。

    该 Context 与普通法律原文 Context 不同。

    普通 Context：

        法律依据
        法条全文

    Rule Context：

        法律规则
        条件
        排除条件
        例外
        法律义务
        法律后果

    为下一阶段：

        V6.0-5 Rule Engine

    提供输入。
    """

    if not rules:

        return ""

    blocks = []

    for index, rule in enumerate(
        rules,
        start=1,
    ):

        lines = []

        lines.append(
            f"【规则 {index}】"
        )

        lines.append(
            f"法律：{rule.law_name}"
        )

        lines.append(
            f"法条：{rule.article_number}"
        )

        lines.append(
            f"规则类型：{rule.rule_type}"
        )

        if rule.summary:

            lines.append(
                f"规则摘要：{rule.summary}"
            )

        # ----------------------------------------------------
        # 条件
        # ----------------------------------------------------

        if rule.conditions:

            lines.append(
                "条件："
            )

            for condition in rule.conditions:

                lines.append(
                    f"- {condition}"
                )

        # ----------------------------------------------------
        # 排除条件
        # ----------------------------------------------------

        if rule.exclusions:

            lines.append(
                "排除条件："
            )

            for condition in rule.exclusions:

                lines.append(
                    f"- {condition}"
                )

        # ----------------------------------------------------
        # 例外
        # ----------------------------------------------------

        if rule.exceptions:

            lines.append(
                "例外："
            )

            for exception in rule.exceptions:

                lines.append(
                    f"- {exception}"
                )

        # ----------------------------------------------------
        # 法律义务
        # ----------------------------------------------------

        if rule.obligations:

            lines.append(
                "法律义务："
            )

            for obligation in rule.obligations:

                lines.append(
                    f"- {obligation}"
                )

        # ----------------------------------------------------
        # 法律后果
        # ----------------------------------------------------

        if rule.consequences:

            lines.append(
                "法律后果："
            )

            for consequence in rule.consequences:

                lines.append(
                    f"- {consequence}"
                )

        # ----------------------------------------------------
        # 引用法条
        # ----------------------------------------------------

        if rule.cited_articles:

            lines.append(
                "引用法条："
                + "、".join(
                    rule.cited_articles
                )
            )

        blocks.append(
            "\n".join(
                lines
            )
        )

    return "\n\n".join(
        blocks
    )


# ============================================================
# Debug 输出
# ============================================================

def print_rule(
    rule: NormalizedLegalRule,
    index: int = 1,
):
    """
    打印单条规范化规则。

    用于：

        python -m src.rule_normalizer
    """

    print()
    print(
        f"【规范化规则 {index}】"
    )

    print(
        f"法律：{rule.law_name}"
    )

    print(
        f"法条：{rule.article_number}"
    )

    print(
        f"分类：{rule.category}"
    )

    print(
        f"规则类型：{rule.rule_type}"
    )

    print(
        f"规则摘要：{rule.summary}"
    )

    print(
        f"置信度：{rule.confidence}"
    )

    print()

    print(
        "条件："
    )

    if rule.conditions:

        for item in rule.conditions:

            print(
                f"  - {item}"
            )

    else:

        print(
            "  - 无"
        )

    print()

    print(
        "排除条件："
    )

    if rule.exclusions:

        for item in rule.exclusions:

            print(
                f"  - {item}"
            )

    else:

        print(
            "  - 无"
        )

    print()

    print(
        "例外："
    )

    if rule.exceptions:

        for item in rule.exceptions:

            print(
                f"  - {item}"
            )

    else:

        print(
            "  - 无"
        )

    print()

    print(
        "法律义务："
    )

    if rule.obligations:

        for item in rule.obligations:

            print(
                f"  - {item}"
            )

    else:

        print(
            "  - 无"
        )

    print()

    print(
        "法律后果："
    )

    if rule.consequences:

        for item in rule.consequences:

            print(
                f"  - {item}"
            )

    else:

        print(
            "  - 无"
        )

    print()

    print(
        "引用法条："
    )

    if rule.cited_articles:

        print(
            "  "
            + "、".join(
                rule.cited_articles
            )
        )

    else:

        print(
            "  - 无"
        )


# ============================================================
# 构造测试规则
# ============================================================

def build_test_rule() -> NormalizedLegalRule:
    """
    构造 V6.0-3 当前测试结果。

    用于测试：

        V6.0-4 Rule Normalizer

    特意保留 V6.0-3 中出现的“脏数据”，
    用来验证清洗效果。
    """

    return NormalizedLegalRule(

        law_name=
            "中华人民共和国劳动合同法",

        article_number=
            "第十四条",

        category=
            "核心法条",

        rule_type=
            "义务规则",

        summary=
            "符合《劳动合同法》第十四条规定条件时，"
            "应当订立无固定期限劳动合同",

        conditions=[

            "连续订立二次固定期限劳动合同",

            "属于续订劳动合同",

            "劳动者提出或者同意续订、订立劳动合同",

            "第十四条无固定期限劳动合同，是指用人单位与劳动者约定无确定终止时间的劳动合同。",

            "连续工作",

            "连续订立",

            "连续工作满十年",

            "劳动者在该用人单位连续工作满十年",

            "距法定退休年龄不足十年的；（三）连续订立二次固定期限劳动合同",

            "劳动者没有本法第三十九条和第四十条第一项、第二项规定的情形",

        ],

        exclusions=[

            "劳动者不存在《劳动合同法》第三十九条规定的情形",

            "劳动者不存在《劳动合同法》第四十条第一项、第二项规定的情形",

            "没有本法第三十九条和第四十条第一项、第二项规定的情形",

        ],

        exceptions=[

            "劳动者提出订立固定期限劳动合同",

            "除劳动者提出订立固定期限劳动合同外",

        ],

        obligations=[

            "用人单位应当订立无固定期限劳动合同",

            "有下列情形之一，劳动者提出或者同意续订、订立劳动合同的，"
            "除劳动者提出订立固定期限劳动合同外，"
            "应当订立无固定期限劳动合同",

        ],

        consequences=[

            "有下列情形之一，劳动者提出或者同意续订、订立劳动合同的，"
            "除劳动者提出订立固定期限劳动合同外，"
            "应当订立无固定期限劳动合同",

            "用人单位自用工之日起满一年不与劳动者订立书面劳动合同的，"
            "视为用人单位与劳动者已订立无固定期限劳动合同",

        ],

        cited_articles=[

            "第三十九条",

            "第四十条",

            "第十四条",

            "第四十条第一项",

        ],

        confidence=1.0,
    )


# ============================================================
# Module Test
# ============================================================

def main():
    """
    V6.0-4 Rule Normalizer 测试。

    执行：

        python -m src.rule_normalizer
    """

    print()
    print("=" * 70)
    print(
        "RAG V6.0-4 - Legal Rule Normalizer"
    )
    print("=" * 70)

    print()

    print(
        "输入：V6.0-3 原始法律规则"
    )

    print(
        "目标：清洗、去重、归一化"
    )

    print()

    rule = build_test_rule()

    print(
        "=============================="
    )

    print(
        "规范化前"
    )

    print_rule(
        rule
    )

    print()

    normalized = normalize_rule(
        rule
    )

    print()

    print(
        "=============================="
    )

    print(
        "规范化后"
    )

    print_rule(
        normalized
    )

    print()

    print(
        "=============================="
    )

    print(
        "V6.0-4 Rule Context"
    )

    print(
        "=============================="
    )

    context = build_rule_context(
        [normalized]
    )

    print(
        context
    )

    print()

    print(
        "=" * 70
    )

    print(
        "V6.0-4 Rule Normalizer 测试完成"
    )

    print(
        "=" * 70
    )


# ============================================================
# Entry Point
# ============================================================

if __name__ == "__main__":

    main()