from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


# ============================================================
# RAG V6.0-2
# relevance_ranker.py
#
# 功能：
#
# 1. 对 Retriever 返回的法律依据重新排序
#
# 2. 区分：
#
#       核心法条
#       强依赖法条
#       关联法条
#       补充法条
#       低相关法条
#
# 3. 根据用户问题中的关键词提升真正相关的法条
#
# 4. 对法律引用关系进行加权
#
# 5. 核心法条引用的“必要条件法条”强制保留
#
# 6. 避免仅依赖 BGE-M3 similarity score
#
# 7. 为后续 legal_rule_extractor.py
#    提供更加完整的法律依据
#
#
# ============================================================
# V6.0-2 核心修复
# ============================================================
#
# V6.0-1 出现的问题：
#
#     第十四条
#         ↓
#     第三十九条
#     第四十条
#
# Retriever 已经成功找到了：
#
#     第十四条
#     第三十九条
#     第四十条
#
# 但是经过 Ranker：
#
#     第十四条   核心法条
#     第十一条   关联法条
#     第二十条   关联法条
#     第八十二条 关联法条
#     第三十九条 关联法条
#     第四十条   关联法条
#     ...
#
# select_context_laws() 又按照：
#
#     max_core = 3
#     max_related = 4
#     max_support = 2
#
# 截断。
#
# 导致：
#
#     第十四条     ✅
#     第三十九条   ✅
#     第四十条     ❌
#
# 最终 Context 缺少第40条。
#
#
# V6.0-2 修复：
#
#     核心法条
#          ↓
#     核心法条直接引用
#          ↓
#     强依赖法条
#          ↓
#     必须优先保留
#
# 因此：
#
#     第十四条
#         ↓
#     第三十九条
#     第四十条
#
# 三者必须作为一个法律规则组进入 Context。
#
#
# 注意：
#
# “强制保留”指 Context 构建层面的法律依据完整性，
# 不代表直接认定案件事实已经满足这些法条的条件。
#
# ============================================================


# ============================================================
# 配置
# ============================================================

DEFAULT_MAX_RESULTS = 8

# 普通补充法条最低综合相关度
DEFAULT_MIN_SCORE = 0.30

# 核心法条最低分
CORE_THRESHOLD = 0.70

# 关联法条最低分
RELATED_THRESHOLD = 0.50

# 补充法条最低分
SUPPORT_THRESHOLD = 0.30


# ============================================================
# 法律引用关系
#
# 格式：
#
#     父法条
#         ↓
#     被引用法条
#
# 这里保存的是“法律引用关系”，
# 不代表当前案件一定适用被引用法条。
# ============================================================

LAW_REFERENCE_MAP = {

    "中华人民共和国劳动合同法": {

        "第十四条": [
            "第三十九条",
            "第四十条",
        ],

        "第八十二条": [
            "第十四条",
        ],
    }
}


# ============================================================
# 法律引用关系类型
#
# strong：
#
#     核心法条在判断法律条件时直接引用，
#     通常属于必须一起分析的条件法条。
#
# normal：
#
#     一般法律关联。
# ============================================================

LAW_REFERENCE_TYPE = {

    "中华人民共和国劳动合同法": {

        "第十四条": {

            "第三十九条": "strong",

            "第四十条": "strong",
        },

        "第八十二条": {

            "第十四条": "strong",
        },
    }
}


# ============================================================
# 问题关键词
# ============================================================

QUESTION_KEYWORDS = {

    "劳动合同": [

        "劳动合同",

        "固定期限",

        "无固定期限",

        "续订",

        "续签",

        "订立",

        "签订",

        "合同期限",
    ],

    "解除": [

        "解除",

        "辞退",

        "开除",

        "解雇",

        "终止",
    ],

    "经济补偿": [

        "经济补偿",

        "补偿金",

        "赔偿",

        "赔偿金",

        "N+1",

        "N＋1",
    ],

    "工资": [

        "工资",

        "薪资",

        "工资差额",

        "拖欠工资",

        "工资支付",
    ],

    "加班": [

        "加班",

        "加班费",

        "延时工作",

        "休息日",

        "法定节假日",
    ],

    "工伤": [

        "工伤",

        "工伤认定",

        "劳动能力鉴定",

        "伤残",

        "医疗期",
    ],

    "社会保险": [

        "社保",

        "社会保险",

        "养老保险",

        "医疗保险",

        "失业保险",

        "生育保险",

        "工伤保险",
    ],

    "竞业限制": [

        "竞业",

        "竞业限制",

        "保密",

        "竞业补偿",
    ],

    "劳动仲裁": [

        "劳动仲裁",

        "仲裁",

        "仲裁时效",

        "劳动争议",
    ],
}


# ============================================================
# 法条重要性配置
#
# 注意：
#
# 这里只表示排序优先级，
# 不代表当前案件一定适用。
# ============================================================

ARTICLE_PRIORITY = {

    "中华人民共和国劳动合同法": {

        "第十四条": 1.00,

        "第十三条": 0.60,

        "第三十九条": 0.75,

        "第四十条": 0.75,

        "第八十二条": 0.65,
    },

    "中华人民共和国劳动法": {

        "第二十条": 0.70,
    },

    "中华人民共和国劳动合同法实施条例": {

        "第十一条": 0.85,
    },
}


# ============================================================
# V6.0-2
# 强依赖法条优先级
#
# 被核心法条直接引用的法条：
#
#     不应该因为 BGE-M3 score = 0
#     而被认为“不重要”。
#
# 例如：
#
#     第十四条
#         ↓
#     第三十九条
#     第四十条
#
# 第三十九条、第四十条属于第十四条判断条件的一部分。
# ============================================================

REFERENCE_PRIORITY = {

    "strong": 1.00,

    "normal": 0.70,
}


# ============================================================
# 数据结构
# ============================================================

@dataclass
class RankedLaw:

    law_name: str

    article_number: str

    article_text: str

    source: str = ""

    source_file: str = ""

    score: float = 0.0

    original_score: float = 0.0

    keyword_score: float = 0.0

    article_priority: float = 0.0

    reference_score: float = 0.0

    dependency_score: float = 0.0

    topic_score: float = 0.0

    category: str = "补充法条"

    reason: str = ""

    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:

        data = {

            "law_name": self.law_name,

            "article_number": self.article_number,

            "article_text": self.article_text,

            "source": self.source,

            "source_file": self.source_file,

            "score": round(
                self.score,
                4,
            ),

            "original_score": round(
                self.original_score,
                4,
            ),

            "keyword_score": round(
                self.keyword_score,
                4,
            ),

            "article_priority": round(
                self.article_priority,
                4,
            ),

            "reference_score": round(
                self.reference_score,
                4,
            ),

            "dependency_score": round(
                self.dependency_score,
                4,
            ),

            "topic_score": round(
                self.topic_score,
                4,
            ),

            "category": self.category,

            "reason": self.reason,
        }

        if self.metadata:

            data["metadata"] = self.metadata

        return data


# ============================================================
# 工具函数
# ============================================================

def normalize_text(
    text: Any,
) -> str:

    if text is None:

        return ""

    text = str(text)

    text = text.replace(
        "\n",
        "",
    )

    text = text.replace(
        "\r",
        "",
    )

    text = text.replace(
        " ",
        "",
    )

    text = text.replace(
        "　",
        "",
    )

    return text


def normalize_article_number(
    article_number: Any,
) -> str:

    if article_number is None:

        return ""

    text = str(
        article_number
    ).strip()

    text = text.replace(
        " ",
        "",
    )

    text = text.replace(
        "　",
        "",
    )

    return text


def get_law_name(
    item: Dict[str, Any],
) -> str:

    return (
        item.get("law_name")
        or item.get("法律名称")
        or ""
    )


def get_article_number(
    item: Dict[str, Any],
) -> str:

    return (
        item.get("article_number")
        or item.get("法条")
        or item.get("article")
        or ""
    )


def get_article_text(
    item: Dict[str, Any],
) -> str:

    return (
        item.get("article_text")
        or item.get("法条内容")
        or item.get("text")
        or ""
    )


def get_original_score(
    item: Dict[str, Any],
) -> float:

    # 注意：
    #
    # 不使用：
    #
    #     value = item.get("score") or ...
    #
    # 因为 score = 0.0 时，
    # Python 会继续寻找后面的字段。
    #
    # V6.0-2 使用明确的 None 判断，
    # 避免 0.0 被错误处理。

    value = item.get(
        "score",
        None,
    )

    if value is None:

        value = item.get(
            "similarity",
            None,
        )

    if value is None:

        value = item.get(
            "relevance_score",
            None,
        )

    if value is None:

        value = 0.0

    try:

        return float(value)

    except (
        TypeError,
        ValueError,
    ):

        return 0.0


# ============================================================
# 问题类型识别
# ============================================================

def detect_question_types(
    question: str,
) -> List[str]:

    question = normalize_text(
        question
    )

    matched_types = []

    for (
        question_type,
        keywords,
    ) in QUESTION_KEYWORDS.items():

        for keyword in keywords:

            if keyword in question:

                matched_types.append(
                    question_type
                )

                break

    return matched_types


# ============================================================
# 关键词提取
# ============================================================

def extract_question_keywords(
    question: str,
) -> List[str]:

    question = normalize_text(
        question
    )

    keywords = []

    for (
        _,
        type_keywords,
    ) in QUESTION_KEYWORDS.items():

        for keyword in type_keywords:

            if keyword in question:

                keywords.append(
                    keyword
                )

    # ========================================================
    # 法条编号
    # ========================================================

    article_matches = re.findall(

        r"第[一二三四五六七八九十百千万零〇0-9]+条",

        question,
    )

    keywords.extend(
        article_matches
    )

    # ========================================================
    # 特殊法律概念
    # ========================================================

    special_keywords = [

        "连续订立",

        "连续签订",

        "第三次",

        "第二次",

        "三次",

        "二次",

        "第一次",

        "第二次续订",

        "第三次续订",

        "应当",

        "必须",

        "可以",

        "不得",

        "除外",

        "例外",

        "条件",
    ]

    for keyword in special_keywords:

        if keyword in question:

            keywords.append(
                keyword
            )

    # ========================================================
    # 去重
    # ========================================================

    result = []

    for keyword in keywords:

        if keyword not in result:

            result.append(
                keyword
            )

    # ========================================================
    # V6.0-2
    #
    # 长关键词优先。
    #
    # 例如：
    #
    #     无固定期限劳动合同
    #     劳动合同
    #
    # 如果两个关键词同时命中，
    # 短关键词不应该重复造成过度加权。
    # ========================================================

    result.sort(
        key=len,
        reverse=True,
    )

    return result


# ============================================================
# 关键词是否已经被更长关键词覆盖
# ============================================================

def is_keyword_covered(
    keyword: str,
    matched_keywords: List[str],
) -> bool:

    for other in matched_keywords:

        if other == keyword:

            continue

        if len(other) <= len(keyword):

            continue

        if keyword in other:

            return True

    return False


# ============================================================
# 计算关键词相关度
# ============================================================

def calculate_keyword_score(
    question: str,
    article_text: str,
    article_number: str,
) -> float:

    question = normalize_text(
        question
    )

    article_text = normalize_text(
        article_text
    )

    article_number = normalize_article_number(
        article_number
    )

    if not question:

        return 0.0

    if not article_text:

        return 0.0

    keywords = extract_question_keywords(
        question
    )

    if not keywords:

        return 0.0

    weighted = 0.0

    effective_keywords = []

    for keyword in keywords:

        # ====================================================
        # 长关键词覆盖短关键词
        # ====================================================

        if is_keyword_covered(
            keyword,
            keywords,
        ):

            continue

        effective_keywords.append(
            keyword
        )

        # ====================================================
        # 法条编号
        # ====================================================

        if (
            article_number
            and keyword == article_number
        ):

            if (
                article_number
                in question
            ):

                weighted += 1.0

                continue

        # ====================================================
        # 法律文本命中
        # ====================================================

        if keyword in article_text:

            if keyword in [

                "连续订立",

                "连续签订",

                "第三次",

                "第二次",

                "三次",

                "二次",

                "续订",

                "续签",

                "无固定期限",

                "固定期限",

                "应当",

                "必须",
            ]:

                weighted += 0.9

            elif keyword in [

                "劳动合同",

                "解除",

                "经济补偿",

                "补偿金",

                "工资",

                "加班",

                "工伤",

                "社保",

                "竞业",
            ]:

                weighted += 0.6

            else:

                weighted += 0.5

    if not effective_keywords:

        return 0.0

    score = (
        weighted
        / len(effective_keywords)
    )

    return min(
        score,
        1.0,
    )


# ============================================================
# 法条基础优先级
# ============================================================

def get_article_priority(
    law_name: str,
    article_number: str,
) -> float:

    law_map = ARTICLE_PRIORITY.get(
        law_name,
        {},
    )

    return float(
        law_map.get(
            article_number,
            0.50,
        )
    )


# ============================================================
# V6.0-2
# 判断法条是否属于核心法条
# ============================================================

def is_core_article(
    question: str,
    law_name: str,
    article_number: str,
    article_text: str,
    original_score: float,
) -> bool:

    question = normalize_text(
        question
    )

    article_text = normalize_text(
        article_text
    )

    # ========================================================
    # 1.
    # 用户直接指定法条
    # ========================================================

    if (
        article_number
        and article_number in question
    ):

        return True

    keyword_score = calculate_keyword_score(
        question,
        article_text,
        article_number,
    )

    priority = get_article_priority(
        law_name,
        article_number,
    )

    # ========================================================
    # 2.
    # BGE-M3 + 关键词
    # ========================================================

    if (
        original_score >= 0.70
        and keyword_score >= 0.25
    ):

        return True

    # ========================================================
    # 3.
    # 高优先级法律条款 + 高关键词相关性
    # ========================================================

    if (
        keyword_score >= 0.55
        and priority >= 0.75
    ):

        return True

    return False


# ============================================================
# 判断法条是否为核心法条直接引用的条款
# ============================================================

def get_reference_type(
    law_name: str,
    parent_article: str,
    article_number: str,
) -> str:

    law_map = LAW_REFERENCE_TYPE.get(
        law_name,
        {},
    )

    article_map = law_map.get(
        parent_article,
        {},
    )

    return article_map.get(
        article_number,
        "",
    )


# ============================================================
# V6.0-2
# 查找当前法条被哪些法条引用
#
# 返回：
#
# [
#     {
#         "parent_article": "第十四条",
#         "reference_type": "strong"
#     }
# ]
# ============================================================

def find_parent_references(
    law_name: str,
    article_number: str,
    all_items: List[Dict[str, Any]],
) -> List[Dict[str, str]]:

    results = []

    law_map = LAW_REFERENCE_MAP.get(
        law_name,
        {},
    )

    for (
        parent_article,
        related_articles,
    ) in law_map.items():

        if article_number not in related_articles:

            continue

        # ====================================================
        # 只有当父法条实际存在于当前候选集合时，
        # 才建立当前 Context 中的依赖关系。
        # ====================================================

        parent_exists = False

        for item in all_items:

            item_law = get_law_name(
                item
            )

            item_article = normalize_article_number(
                get_article_number(item)
            )

            if (
                item_law == law_name
                and item_article == parent_article
            ):

                parent_exists = True

                break

        if not parent_exists:

            continue

        reference_type = get_reference_type(
            law_name,
            parent_article,
            article_number,
        )

        if not reference_type:

            reference_type = "normal"

        results.append(
            {
                "parent_article": parent_article,
                "reference_type": reference_type,
            }
        )

    return results


# ============================================================
# V6.0-2
# 计算法律依赖分数
# ============================================================

def calculate_dependency_score(
    law_name: str,
    article_number: str,
    all_items: List[Dict[str, Any]],
) -> float:

    references = find_parent_references(
        law_name,
        article_number,
        all_items,
    )

    if not references:

        return 0.0

    score = 0.0

    for reference in references:

        reference_type = reference.get(
            "reference_type",
            "normal",
        )

        priority = REFERENCE_PRIORITY.get(
            reference_type,
            0.0,
        )

        score = max(
            score,
            priority,
        )

    return score


# ============================================================
# V6.0-2
# 计算法律引用关系分数
#
# 与 dependency_score 的区别：
#
# reference_score：
#     用于描述引用关系本身。
#
# dependency_score：
#     强调该法条对于核心法条法律条件判断的重要程度。
#
# ============================================================

def calculate_reference_score(
    law_name: str,
    article_number: str,
    all_items: List[Dict[str, Any]],
) -> float:

    references = find_parent_references(
        law_name,
        article_number,
        all_items,
    )

    if not references:

        return 0.0

    score = 0.0

    for reference in references:

        reference_type = reference.get(
            "reference_type",
            "normal",
        )

        if reference_type == "strong":

            score = max(
                score,
                0.85,
            )

        elif reference_type == "normal":

            score = max(
                score,
                0.70,
            )

    return score


# ============================================================
# V6.0-2
# 主题相关度
#
# 用于处理：
#
#     “劳动合同”
#     “解除”
#     “工资”
#     “工伤”
#
# 等问题主题。
#
# 与 keyword_score 不完全相同。
# ============================================================

def calculate_topic_score(
    question: str,
    article_text: str,
) -> float:

    question_types = detect_question_types(
        question
    )

    if not question_types:

        return 0.0

    article_text = normalize_text(
        article_text
    )

    if not article_text:

        return 0.0

    matched = 0

    for question_type in question_types:

        keywords = QUESTION_KEYWORDS.get(
            question_type,
            [],
        )

        for keyword in keywords:

            if keyword in article_text:

                matched += 1

                break

    if matched == 0:

        return 0.0

    return min(
        matched
        / len(question_types),
        1.0,
    )


# ============================================================
# V6.0-2
# 判断是否为强依赖法条
# ============================================================

def is_strong_dependency_article(
    law_name: str,
    article_number: str,
    all_items: List[Dict[str, Any]],
) -> bool:

    dependency_score = calculate_dependency_score(
        law_name,
        article_number,
        all_items,
    )

    return dependency_score >= 1.0


# ============================================================
# 判断是否为关联法条
# ============================================================

def is_related_article(
    question: str,
    law_name: str,
    article_number: str,
    article_text: str,
    all_items: Optional[List[Dict[str, Any]]] = None,
) -> bool:

    question = normalize_text(
        question
    )

    article_text = normalize_text(
        article_text
    )

    keyword_score = calculate_keyword_score(
        question,
        article_text,
        article_number,
    )

    if keyword_score >= 0.25:

        return True

    # ========================================================
    # V6.0-2
    # 核心法条直接引用的法条，
    # 即使 keyword_score 很低，
    # 也应该属于关联法条。
    # ========================================================

    if all_items is not None:

        dependency_score = calculate_dependency_score(
            law_name,
            article_number,
            all_items,
        )

        if dependency_score >= 0.70:

            return True

    return False


# ============================================================
# V6.0-2
# 计算综合相关度
# ============================================================

def calculate_final_score(
    original_score: float,
    keyword_score: float,
    article_priority: float,
    reference_score: float,
    dependency_score: float,
    topic_score: float,
) -> float:

    # ========================================================
    # V6.0-2 权重
    #
    # BGE-M3 原始语义相关度：35%
    # 问题关键词匹配：25%
    # 法条重要性：15%
    # 法律引用关系：10%
    # 法律依赖关系：10%
    # 问题主题相关度：5%
    #
    # 总计：
    #
    # 35 + 25 + 15 + 10 + 10 + 5 = 100%
    #
    # ========================================================

    final_score = (

        original_score * 0.35

        + keyword_score * 0.25

        + article_priority * 0.15

        + reference_score * 0.10

        + dependency_score * 0.10

        + topic_score * 0.05
    )

    return min(
        max(
            final_score,
            0.0,
        ),
        1.0,
    )


# ============================================================
# V6.0-2
# 法条分类
# ============================================================

def classify_article(
    final_score: float,
    keyword_score: float,
    article_priority: float,
    reference_score: float,
    dependency_score: float,
    is_core: bool,
    is_related: bool,
) -> str:

    # ========================================================
    # 第一优先级：
    # 核心法条
    # ========================================================

    if is_core:

        return "核心法条"

    # ========================================================
    # 第二优先级：
    # 强依赖法条
    #
    # 例如：
    #
    # 第十四条
    #     ↓
    # 第三十九条
    # 第四十条
    #
    # ========================================================

    if dependency_score >= 1.0:

        return "强依赖法条"

    # ========================================================
    # 第三优先级：
    # 普通关联法条
    # ========================================================

    if is_related:

        return "关联法条"

    if reference_score >= 0.70:

        return "关联法条"

    # ========================================================
    # 第四优先级：
    # 综合分数达到核心阈值
    # ========================================================

    if final_score >= CORE_THRESHOLD:

        return "核心法条"

    # ========================================================
    # 第五优先级：
    # 综合分数达到关联阈值
    # ========================================================

    if final_score >= RELATED_THRESHOLD:

        return "关联法条"

    # ========================================================
    # 第六优先级：
    # 补充法条
    # ========================================================

    if final_score >= SUPPORT_THRESHOLD:

        return "补充法条"

    return "低相关法条"


# ============================================================
# V6.0-2
# 生成排序理由
# ============================================================

def build_reason(
    category: str,
    original_score: float,
    keyword_score: float,
    article_priority: float,
    reference_score: float,
    dependency_score: float,
    topic_score: float,
) -> str:

    reasons = []

    if original_score >= 0.65:

        reasons.append(
            "BGE-M3语义相关度较高"
        )

    if keyword_score >= 0.50:

        reasons.append(
            "与问题核心关键词高度匹配"
        )

    elif keyword_score >= 0.25:

        reasons.append(
            "与问题关键词存在关联"
        )

    if article_priority >= 0.75:

        reasons.append(
            "属于重要法律条款"
        )

    if reference_score >= 0.70:

        reasons.append(
            "存在法律引用关系"
        )

    if dependency_score >= 1.0:

        reasons.append(
            "属于核心法条直接引用的强依赖法条"
        )

    elif dependency_score >= 0.70:

        reasons.append(
            "属于法律引用关联法条"
        )

    if topic_score >= 0.70:

        reasons.append(
            "与问题法律主题高度相关"
        )

    elif topic_score >= 0.40:

        reasons.append(
            "与问题法律主题存在关联"
        )

    if not reasons:

        reasons.append(
            "综合相关度一般"
        )

    return (
        f"{category}："
        + "；".join(reasons)
    )


# ============================================================
# 单条法律依据评分
# ============================================================

def rank_one(
    question: str,
    item: Dict[str, Any],
    all_items: List[Dict[str, Any]],
) -> RankedLaw:

    law_name = get_law_name(
        item
    )

    article_number = normalize_article_number(
        get_article_number(item)
    )

    article_text = get_article_text(
        item
    )

    original_score = get_original_score(
        item
    )

    # ========================================================
    # 关键词相关度
    # ========================================================

    keyword_score = calculate_keyword_score(
        question,
        article_text,
        article_number,
    )

    # ========================================================
    # 法条重要性
    # ========================================================

    article_priority = get_article_priority(
        law_name,
        article_number,
    )

    # ========================================================
    # 法律引用关系
    # ========================================================

    reference_score = calculate_reference_score(
        law_name,
        article_number,
        all_items,
    )

    # ========================================================
    # 法律依赖关系
    # ========================================================

    dependency_score = calculate_dependency_score(
        law_name,
        article_number,
        all_items,
    )

    # ========================================================
    # 问题主题相关度
    # ========================================================

    topic_score = calculate_topic_score(
        question,
        article_text,
    )

    # ========================================================
    # 是否核心法条
    # ========================================================

    core = is_core_article(
        question,
        law_name,
        article_number,
        article_text,
        original_score,
    )

    # ========================================================
    # 是否关联法条
    # ========================================================

    related = is_related_article(
        question,
        law_name,
        article_number,
        article_text,
        all_items,
    )

    # ========================================================
    # 综合相关度
    # ========================================================

    final_score = calculate_final_score(

        original_score,

        keyword_score,

        article_priority,

        reference_score,

        dependency_score,

        topic_score,
    )

    # ========================================================
    # 分类
    # ========================================================

    category = classify_article(

        final_score,

        keyword_score,

        article_priority,

        reference_score,

        dependency_score,

        core,

        related,
    )

    # ========================================================
    # 理由
    # ========================================================

    reason = build_reason(

        category,

        original_score,

        keyword_score,

        article_priority,

        reference_score,

        dependency_score,

        topic_score,
    )

    metadata = dict(
        item
    )

    return RankedLaw(

        law_name=law_name,

        article_number=article_number,

        article_text=article_text,

        source=item.get(
            "source",
            "",
        ),

        source_file=item.get(
            "source_file",
            "",
        ),

        score=final_score,

        original_score=original_score,

        keyword_score=keyword_score,

        article_priority=article_priority,

        reference_score=reference_score,

        dependency_score=dependency_score,

        topic_score=topic_score,

        category=category,

        reason=reason,

        metadata=metadata,
    )


# ============================================================
# 去重
# ============================================================

def deduplicate_ranked(
    items: List[RankedLaw],
) -> List[RankedLaw]:

    result = []

    seen = set()

    for item in items:

        key = (

            normalize_text(
                item.law_name
            ),

            normalize_text(
                item.article_number
            ),
        )

        if key in seen:

            continue

        seen.add(
            key
        )

        result.append(
            item
        )

    return result


# ============================================================
# V6.0-2
# 分类排序
#
# 强依赖法条排在普通关联法条前面。
# ============================================================

CATEGORY_ORDER = {

    "核心法条": 0,

    "强依赖法条": 1,

    "关联法条": 2,

    "补充法条": 3,

    "低相关法条": 4,
}


def sort_ranked(
    items: List[RankedLaw],
) -> List[RankedLaw]:

    return sorted(

        items,

        key=lambda x: (

            CATEGORY_ORDER.get(
                x.category,
                9,
            ),

            # 强依赖法条首先按照 dependency_score 排序
            -x.dependency_score,

            # 再看综合相关度
            -x.score,

            # 再看关键词
            -x.keyword_score,

            # 最后看原始 BGE-M3
            -x.original_score,
        ),
    )


# ============================================================
# V6.0-2
# 找出核心法条
# ============================================================

def find_core_laws(
    ranked: List[RankedLaw],
) -> List[RankedLaw]:

    return [

        item

        for item in ranked

        if item.category == "核心法条"
    ]


# ============================================================
# V6.0-2
# 找出核心法条直接依赖
# ============================================================

def find_required_dependencies(
    ranked: List[RankedLaw],
) -> List[RankedLaw]:

    return [

        item

        for item in ranked

        if item.category == "强依赖法条"
    ]


# ============================================================
# V6.0-2
# 法律依据排序
# ============================================================

def rank_laws(
    question: str,
    laws: List[Dict[str, Any]],
    max_results: int = DEFAULT_MAX_RESULTS,
    min_score: float = DEFAULT_MIN_SCORE,
    keep_low_relevance: bool = False,
) -> List[Dict[str, Any]]:

    if not question:

        return []

    if not laws:

        return []

    ranked = []

    for item in laws:

        if not isinstance(
            item,
            dict,
        ):

            continue

        ranked_item = rank_one(

            question,

            item,

            laws,
        )

        ranked.append(
            ranked_item
        )

    # ========================================================
    # 去重
    # ========================================================

    ranked = deduplicate_ranked(
        ranked
    )

    # ========================================================
    # 排序
    # ========================================================

    ranked = sort_ranked(
        ranked
    )

    # ========================================================
    # V6.0-2
    #
    # 核心法条和强依赖法条必须优先。
    # ========================================================

    important = [

        item

        for item in ranked

        if item.category in [

            "核心法条",

            "强依赖法条",

        ]
    ]

    # ========================================================
    # 普通关联法条
    # ========================================================

    related = [

        item

        for item in ranked

        if item.category == "关联法条"
    ]

    # ========================================================
    # 补充法条
    # ========================================================

    supplementary = [

        item

        for item in ranked

        if (

            item.category
            == "补充法条"

            and item.score >= min_score
        )
    ]

    # ========================================================
    # 结果：
    #
    # 核心
    #     ↓
    # 强依赖
    #     ↓
    # 关联
    #     ↓
    # 补充
    # ========================================================

    result = (

        important

        + related

        + supplementary
    )

    if keep_low_relevance:

        low_relevance = [

            item

            for item in ranked

            if item.category
            == "低相关法条"
        ]

        result.extend(
            low_relevance
        )

    result = result[
        :max_results
    ]

    return [

        item.to_dict()

        for item in result
    ]


# ============================================================
# V6.0-2
# 专门用于法律问答的 Context 筛选
#
# 重要修复：
#
# 不能简单使用：
#
#     core[:max_core]
#     related[:max_related]
#
# 因为这样会导致：
#
#     第十四条
#     第三十九条
#     第四十条
#
# 被其他普通关联法条挤掉。
#
#
# V6.0-2 使用：
#
#     核心法条
#         ↓
#     强依赖法条
#         ↓
#     普通关联法条
#         ↓
#     补充法条
#
# 强依赖法条不受普通 related 数量限制。
# ============================================================

def select_context_laws(
    question: str,
    laws: List[Dict[str, Any]],
    max_core: int = 3,
    max_related: int = 4,
    max_support: int = 2,
) -> List[Dict[str, Any]]:

    ranked = rank_laws(

        question=question,

        laws=laws,

        max_results=50,

        min_score=0.25,

        keep_low_relevance=False,
    )

    # ========================================================
    # 核心法条
    # ========================================================

    core = [

        item

        for item in ranked

        if item.get("category")
        == "核心法条"
    ]

    # ========================================================
    # V6.0-2
    # 强依赖法条
    #
    # 例如：
    #
    # 第十四条
    #     ↓
    # 第三十九条
    # 第四十条
    #
    # 必须单独处理。
    # ========================================================

    dependencies = [

        item

        for item in ranked

        if item.get("category")
        == "强依赖法条"
    ]

    # ========================================================
    # 普通关联法条
    # ========================================================

    related = [

        item

        for item in ranked

        if item.get("category")
        == "关联法条"
    ]

    # ========================================================
    # 补充法条
    # ========================================================

    support = [

        item

        for item in ranked

        if item.get("category")
        == "补充法条"
    ]

    # ========================================================
    # 第一阶段：
    # 核心法条
    # ========================================================

    selected = []

    selected.extend(
        core[:max_core]
    )

    # ========================================================
    # 第二阶段：
    # 强依赖法条
    #
    # 注意：
    #
    # 不使用 max_related 限制。
    #
    # 因为它们是核心法律规则的组成部分。
    # ========================================================

    selected.extend(
        dependencies
    )

    # ========================================================
    # 第三阶段：
    # 普通关联法条
    #
    # 防止重复：
    #
    # 如果某条已经作为核心或强依赖加入，
    # 不再重复加入。
    # ========================================================

    selected_keys = {

        (
            normalize_text(
                item.get(
                    "law_name",
                    "",
                )
            ),

            normalize_text(
                item.get(
                    "article_number",
                    "",
                )
            ),
        )

        for item in selected
    }

    related_count = 0

    for item in related:

        key = (

            normalize_text(
                item.get(
                    "law_name",
                    "",
                )
            ),

            normalize_text(
                item.get(
                    "article_number",
                    "",
                )
            ),
        )

        if key in selected_keys:

            continue

        if related_count >= max_related:

            break

        selected.append(
            item
        )

        selected_keys.add(
            key
        )

        related_count += 1

    # ========================================================
    # 第四阶段：
    # 补充法条
    # ========================================================

    support_count = 0

    for item in support:

        key = (

            normalize_text(
                item.get(
                    "law_name",
                    "",
                )
            ),

            normalize_text(
                item.get(
                    "article_number",
                    "",
                )
            ),
        )

        if key in selected_keys:

            continue

        if support_count >= max_support:

            break

        selected.append(
            item
        )

        selected_keys.add(
            key
        )

        support_count += 1

    # ========================================================
    # V6.0-2
    # 最终安全去重
    # ========================================================

    final_result = []

    seen = set()

    for item in selected:

        key = (

            normalize_text(
                item.get(
                    "law_name",
                    "",
                )
            ),

            normalize_text(
                item.get(
                    "article_number",
                    "",
                )
            ),
        )

        if key in seen:

            continue

        seen.add(
            key
        )

        final_result.append(
            item
        )

    return final_result


# ============================================================
# V6.0-2
# 检查核心法条依赖是否完整
#
# 用于 Debug。
#
# 例如：
#
# 第十四条
#     ↓
# 第三十九条
# 第四十条
#
# 如果 Context 缺少第四十条，
# 返回：
#
# [
#     "第四十条"
# ]
# ============================================================

def find_missing_dependencies(
    selected: List[Dict[str, Any]],
    all_laws: List[Dict[str, Any]],
) -> List[str]:

    selected_keys = set()

    for item in selected:

        selected_keys.add(

            (

                normalize_text(
                    get_law_name(item)
                ),

                normalize_text(
                    get_article_number(item)
                ),
            )
        )

    missing = []

    for item in all_laws:

        law_name = get_law_name(
            item
        )

        article_number = normalize_article_number(
            get_article_number(item)
        )

        dependency_score = calculate_dependency_score(

            law_name,

            article_number,

            all_laws,
        )

        if dependency_score < 1.0:

            continue

        key = (

            normalize_text(
                law_name
            ),

            normalize_text(
                article_number
            ),
        )

        if key not in selected_keys:

            if article_number not in missing:

                missing.append(
                    article_number
                )

    return missing


# ============================================================
# V6.0-2
# 打印排序 Debug
# ============================================================

def print_ranked_results(
    question: str,
    laws: List[Dict[str, Any]],
) -> None:

    print()

    print("=" * 70)

    print(
        "RAG V6.0-2 - Legal Relevance Ranking"
    )

    print("=" * 70)

    print()

    print("问题：")

    print(
        question
    )

    # ========================================================
    # 问题类型
    # ========================================================

    question_types = detect_question_types(
        question
    )

    print()

    print("问题类型：")

    if question_types:

        print(
            "、".join(
                question_types
            )
        )

    else:

        print("未识别")

    # ========================================================
    # 关键词
    # ========================================================

    keywords = extract_question_keywords(
        question
    )

    print()

    print("核心关键词：")

    if keywords:

        print(
            "、".join(
                keywords
            )
        )

    else:

        print("无")

    print()

    print("-" * 70)

    print("法律依据重新排序")

    print("-" * 70)

    ranked = rank_laws(

        question=question,

        laws=laws,

        max_results=50,

        min_score=0.25,

        keep_low_relevance=True,
    )

    for index, item in enumerate(
        ranked,
        start=1,
    ):

        print()

        print(
            f"【{index}】"
        )

        print(
            f"法律：{item.get('law_name')}"
        )

        print(
            f"法条：{item.get('article_number')}"
        )

        print(
            f"分类：{item.get('category')}"
        )

        print(
            f"综合相关度：{item.get('score')}"
        )

        print(
            f"BGE-M3：{item.get('original_score')}"
        )

        print(
            f"关键词：{item.get('keyword_score')}"
        )

        print(
            f"法条优先级：{item.get('article_priority')}"
        )

        print(
            f"引用关系：{item.get('reference_score')}"
        )

        print(
            f"依赖关系：{item.get('dependency_score')}"
        )

        print(
            f"主题相关度：{item.get('topic_score')}"
        )

        print(
            f"理由：{item.get('reason')}"
        )


# ============================================================
# V6.0-2
# Context Debug
# ============================================================

def print_context_results(
    question: str,
    laws: List[Dict[str, Any]],
) -> None:

    print()

    print("=" * 70)

    print(
        "RAG V6.0-2 - Context Selection"
    )

    print("=" * 70)

    selected = select_context_laws(

        question=question,

        laws=laws,

        max_core=3,

        max_related=4,

        max_support=2,
    )

    print()

    print(
        f"Context 法律依据数量："
        f"{len(selected)}"
    )

    for index, item in enumerate(
        selected,
        start=1,
    ):

        print()

        print(
            f"【Context {index}】"
        )

        print(
            f"法律："
            f"{item.get('law_name')}"
        )

        print(
            f"法条："
            f"{item.get('article_number')}"
        )

        print(
            f"分类："
            f"{item.get('category')}"
        )

        print(
            f"综合相关度："
            f"{item.get('score')}"
        )

        print(
            f"依赖关系："
            f"{item.get('dependency_score')}"
        )

        print(
            f"理由："
            f"{item.get('reason')}"
        )

    # ========================================================
    # 检查依赖完整性
    # ========================================================

    missing = find_missing_dependencies(

        selected,

        laws,
    )

    print()

    if missing:

        print(
            "⚠️ Context 缺少强依赖法条："
        )

        for article in missing:

            print(
                f"  - {article}"
            )

    else:

        print(
            "✅ Context 核心法律依赖完整"
        )


# ============================================================
# 测试数据
# ============================================================

def demo() -> None:

    question = (

        "公司连续签订三次固定期限劳动合同后，"

        "是否必须签订无固定期限劳动合同？"
    )

    laws = [

        {

            "law_name":
                "中华人民共和国劳动合同法",

            "article_number":
                "第十四条",

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
            ),

            "source":
                "BGE-M3语义召回",

            "score":
                0.7312,
        },

        {

            "law_name":
                "中华人民共和国劳动法",

            "article_number":
                "第二十条",

            "article_text": (

                "第二十条 劳动合同的期限分为有固定期限、无固定期限和"
                "以完成一定的工作为期限。"
                "劳动者在同一用人单位连续工作满十年以上，"
                "当事人双方同意续延劳动合同的，"
                "如果劳动者提出订立无固定期限的劳动合同，"
                "应当订立无固定期限的劳动合同。"
            ),

            "source":
                "BGE-M3语义召回",

            "score":
                0.7000,
        },

        {

            "law_name":
                "中华人民共和国劳动合同法实施条例",

            "article_number":
                "第十一条",

            "article_text": (

                "第十一条 除劳动者与用人单位协商一致的情形外，"
                "劳动者依照劳动合同法第十四条第二款的规定，"
                "提出订立无固定期限劳动合同的，"
                "用人单位应当与其订立无固定期限劳动合同。"
            ),

            "source":
                "BGE-M3语义召回",

            "score":
                0.6748,
        },

        {

            "law_name":
                "中华人民共和国劳动合同法",

            "article_number":
                "第十三条",

            "article_text": (

                "第十三条 固定期限劳动合同，是指用人单位与劳动者"
                "约定合同终止时间的劳动合同。"
            ),

            "source":
                "BGE-M3语义召回",

            "score":
                0.6639,
        },

        {

            "law_name":
                "中华人民共和国劳动合同法",

            "article_number":
                "第八十二条",

            "article_text": (

                "第八十二条 用人单位违反本法规定不与劳动者订立"
                "无固定期限劳动合同的，自应当订立无固定期限劳动合同之日起"
                "向劳动者每月支付二倍的工资。"
            ),

            "source":
                "BGE-M3语义召回",

            "score":
                0.6327,
        },

        {

            "law_name":
                "中华人民共和国劳动合同法",

            "article_number":
                "第三十九条",

            "article_text": (

                "第三十九条 劳动者有下列情形之一的，"
                "用人单位可以解除劳动合同："
                "（一）在试用期间被证明不符合录用条件的；"
                "（二）严重违反用人单位的规章制度的；"
                "（三）严重失职，营私舞弊，给用人单位造成重大损害的。"
            ),

            "source":
                "法律引用自动扩展",

            "score":
                0.0,
        },

        {

            "law_name":
                "中华人民共和国劳动合同法",

            "article_number":
                "第四十条",

            "article_text": (

                "第四十条 有下列情形之一的，"
                "用人单位提前三十日以书面形式通知劳动者本人"
                "或者额外支付劳动者一个月工资后，可以解除劳动合同："
                "（一）劳动者患病或者非因工负伤，在规定的医疗期满后"
                "不能从事原工作，也不能从事由用人单位另行安排的工作的；"
                "（二）劳动者不能胜任工作，经过培训或者调整工作岗位，"
                "仍不能胜任工作的。"
            ),

            "source":
                "法律引用自动扩展",

            "score":
                0.0,
        },

        {

            "law_name":
                "中华人民共和国劳动合同法实施条例",

            "article_number":
                "第十四条",

            "article_text": (

                "第十四条 劳动合同履行地与用人单位注册地不一致的，"
                "有关劳动者的最低工资标准、劳动保护、劳动条件、"
                "职业危害防护和本地区上年度职工月平均工资标准等事项，"
                "按照劳动合同履行地的有关规定执行。"
            ),

            "source":
                "法律引用自动扩展",

            "score":
                0.0,
        },

        {

            "law_name":
                "中华人民共和国劳动合同法实施条例",

            "article_number":
                "第十八条",

            "article_text": (

                "第十八条 有下列情形之一的，劳动者可以与用人单位解除"
                "固定期限劳动合同、无固定期限劳动合同或者以完成一定工作任务"
                "为期限的劳动合同："
            ),

            "source":
                "法律引用自动扩展",

            "score":
                0.0,
        },
    ]

    # ========================================================
    # Debug 1
    # ========================================================

    print_ranked_results(
        question,
        laws,
    )

    # ========================================================
    # Debug 2
    # Context
    # ========================================================

    print_context_results(
        question,
        laws,
    )


# ============================================================
# 模块直接运行
# ============================================================

if __name__ == "__main__":

    demo()