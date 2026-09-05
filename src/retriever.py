# -*- coding: utf-8 -*-

"""
RAG V6.0
Legal Retriever
Structured Rule Retriever

============================================================
版本
============================================================

RAG V6.0 Structured Retriever

============================================================
核心职责
============================================================

本模块负责：

    用户问题
        ↓
    Query Embedding
        ↓
    Qdrant Semantic Search
        ↓
    Qdrant Result Normalization
        ↓
    Article Deduplication
        ↓
    Legal Reference Expansion
        ↓
    Article Ranking
        ↓
    Relevant Article Filtering
        ↓
    Structured Rule Extraction
        ↓
    Structured Articles
        ↓
    Legal Decision Engine

============================================================
重要设计原则
============================================================

1. Retriever 负责“找法律依据”。

2. Retriever 不负责最终法律判断。

3. Legal Decision Engine 才负责：

       SATISFIED
       NOT_SATISFIED
       UNKNOWN
       CONDITIONAL
       DETERMINED

4. Retriever 可以从法律文本中提取结构化规则。

5. Retriever 不允许根据用户问题制造用户事实。

6. Retriever 不允许把 UNKNOWN 条件直接判断为满足。

7. 对于第十四条这种核心法律规则，
   使用确定性的结构化规则模板，
   避免纯文本解析导致条件丢失。

============================================================
本版本重点修复
============================================================

旧版本问题：

    embedding.py
        ↓
    实际函数：
        get_model()
        embed_text()
        embed_texts()

但是旧 retriever.py 错误调用：

    get_embedding_model()

导致：

    ImportError:
    cannot import name 'get_embedding_model'

本版本统一使用：

    from .embedding import get_model, embed_text

并通过：

    embed_text(question)

生成 Query Vector。

============================================================
V6.0 Structured Rule 修复
============================================================

针对：

    《中华人民共和国劳动合同法》第十四条

明确生成：

    conditions
    exclusion_conditions
    exceptions
    legal_obligations
    legal_consequences
    references

从而保证：

    Retriever
        ↓
    Structured Rule
        ↓
    Legal Decision Engine
        ↓
    Condition Results

而不是：

    Retriever
        ↓
    Raw Article
        ↓
    空 conditions
        ↓
    Condition Results = 0

============================================================
V6.0 Qdrant Interface 修复
============================================================

当前 vector_store.py 实际接口：

    search_vectors(vector, limit=20)

返回：

    Qdrant ScoredPoint

而不是：

    Dict

因此 Retriever 必须完成：

    ScoredPoint
        ↓
    payload + score
        ↓
    Article Dict

否则后续：

    article.get(...)
    article["law_name"]
    article["article_number"]

都会发生数据结构错误。

============================================================
"""

from __future__ import annotations

import re

from copy import deepcopy
from typing import Any, Dict, List, Optional


# ============================================================
# Version
# ============================================================

RETRIEVER_VERSION = "V6.0-STRUCTURED-FIXED"


# ============================================================
# Embedding
# ============================================================

"""
当前项目实际 embedding.py 接口：

    get_model()
    embed_text()
    embed_texts()

不能使用：

    get_embedding_model()

因为当前 embedding.py 并不存在这个函数。
"""

try:
    from .embedding import get_model, embed_text
except ImportError:
    from embedding import get_model, embed_text


# ============================================================
# Vector Store
# ============================================================

"""
当前 vector_store.py 实际接口：

    search_vectors(vector, limit=20)

注意：

不能使用：

    search_similar()

因为当前 vector_store.py 并没有这个函数。
"""

try:
    from .vector_store import search_vectors
except ImportError:
    from vector_store import search_vectors


# ============================================================
# 基础工具
# ============================================================


def normalize_text(value: Any) -> str:
    """
    将输入安全转换为字符串。

    用于：

    - article_number
    - article_title
    - law_name
    - rule_summary
    - conditions
    等字段。
    """

    if value is None:
        return ""

    if isinstance(value, str):
        return value.strip()

    return str(value).strip()


def normalize_rule_text(value: Any) -> str:
    """
    标准化法律规则文本。

    主要处理：

    - 多余空格
    - 换行
    - 全角空格
    """

    text = normalize_text(value)

    text = text.replace("\r", " ")
    text = text.replace("\n", " ")
    text = text.replace("\t", " ")
    text = text.replace("\u3000", " ")

    text = re.sub(r"\s+", " ", text)

    return text.strip()


def ensure_list(value: Any) -> List[Any]:
    """
    将任意值转换为 List。

    支持：

        None
        ""
        单字符串
        tuple
        set
        list
    """

    if value is None:
        return []

    if isinstance(value, list):
        return value

    if isinstance(value, tuple):
        return list(value)

    if isinstance(value, set):
        return list(value)

    if isinstance(value, str):

        text = value.strip()

        if not text:
            return []

        return [text]

    return [value]


def normalize_rule_list(value: Any) -> List[str]:
    """
    标准化法律规则列表。

    去重但保持原顺序。
    """

    result: List[str] = []

    for item in ensure_list(value):

        text = normalize_rule_text(item)

        if not text:
            continue

        if text not in result:
            result.append(text)

    return result


def get_field(
    article: Dict[str, Any],
    *names: str,
    default: Any = None,
) -> Any:
    """
    从 Article 中读取字段。

    兼容不同版本字段命名。
    """

    if not isinstance(article, dict):
        return default

    for name in names:

        if name in article:

            value = article.get(name)

            if value is not None:
                return value

    return default


def get_first_field(
    article: Dict[str, Any],
    *names: str,
) -> str:
    """
    获取第一个非空字段。
    """

    for name in names:

        value = get_field(
            article,
            name,
        )

        text = normalize_text(value)

        if text:
            return text

    return ""


def copy_article(
    article: Dict[str, Any],
) -> Dict[str, Any]:
    """
    深复制 Article。

    避免修改 Retriever 上游返回的数据。
    """

    if not isinstance(article, dict):
        return {}

    return deepcopy(article)


# ============================================================
# Qdrant Result Normalization
# ============================================================


def qdrant_point_to_article(
    point: Any,
) -> Dict[str, Any]:
    """
    将 Qdrant ScoredPoint 转换成 Retriever 使用的 Article Dict。

    当前 vector_store.search_vectors() 返回：

        List[ScoredPoint]

    ScoredPoint 通常包含：

        id
        score
        payload
        vector

    Retriever 后续统一使用：

        Dict[str, Any]

    因此在这里进行边界转换。

    ========================================================
    设计原则
    ========================================================

    Vector Store：

        负责 Qdrant

    Retriever：

        负责 Article

    不让 Qdrant 对象进入后面的法律规则处理流程。
    """

    if point is None:
        return {}

    # --------------------------------------------------------
    # 已经是 Dict
    # --------------------------------------------------------

    if isinstance(point, dict):

        result = deepcopy(point)

        if "score" not in result:

            if "_score" in result:
                result["score"] = result["_score"]

        return result

    # --------------------------------------------------------
    # Qdrant ScoredPoint
    # --------------------------------------------------------

    payload = getattr(
        point,
        "payload",
        None,
    )

    if not isinstance(payload, dict):
        payload = {}

    result = deepcopy(payload)

    point_id = getattr(
        point,
        "id",
        None,
    )

    score = getattr(
        point,
        "score",
        None,
    )

    if point_id is not None:

        result.setdefault(
            "id",
            point_id,
        )

    if score is not None:

        result["score"] = score

    return result


def normalize_qdrant_results(
    results: Any,
) -> List[Dict[str, Any]]:
    """
    将 Qdrant 查询结果统一转换成：

        List[Dict[str, Any]]
    """

    if results is None:
        return []

    if isinstance(results, dict):

        return [
            qdrant_point_to_article(results)
        ]

    try:

        items = list(results)

    except TypeError:

        return []

    normalized: List[Dict[str, Any]] = []

    for item in items:

        article = qdrant_point_to_article(
            item
        )

        if article:
            normalized.append(article)

    return normalized


# ============================================================
# Article Number Normalization
# ============================================================


def normalize_article_number(
    value: Any,
) -> str:
    """
    将法律条文编号标准化。

    示例：

        第14条
            ↓
        第十四条

        第１４条
            ↓
        第十四条

        第十四条
            ↓
        第十四条

    注意：

    当前项目 CORE_ARTICLES 使用中文数字形式。
    """

    text = normalize_text(value)

    if not text:
        return ""

    text = text.replace(
        " ",
        "",
    )

    match = re.fullmatch(
        r"第([0-9０-９]+)条",
        text,
    )

    if not match:
        return text

    number_text = match.group(1)

    number_text = number_text.translate(
        str.maketrans(
            "０１２３４５６７８９",
            "0123456789",
        )
    )

    try:

        number = int(number_text)

    except ValueError:

        return text

    digits = "零一二三四五六七八九"

    if number < 10:

        chinese = digits[number]

    elif number < 20:

        chinese = "十"

        if number > 10:

            chinese += digits[
                number - 10
            ]

    elif number < 100:

        chinese = (
            digits[number // 10]
            + "十"
        )

        if number % 10:

            chinese += digits[
                number % 10
            ]

    else:

        return text

    return f"第{chinese}条"


# ============================================================
# Law Detection
# ============================================================


def is_labor_contract_law(
    article: Dict[str, Any],
) -> bool:
    """
    判断 Article 是否属于《中华人民共和国劳动合同法》。
    """

    law_name = get_first_field(
        article,
        "law_name",
        "law",
        "source",
        "document_name",
        "title",
    )

    normalized = normalize_text(
        law_name
    )

    return (
        "劳动合同法" in normalized
        and "实施条例" not in normalized
    )


def is_article_14(
    article: Dict[str, Any],
) -> bool:
    """
    判断是否为《劳动合同法》第十四条。
    """

    if not is_labor_contract_law(
        article
    ):
        return False

    article_number = get_first_field(
        article,
        "article_number",
        "article_no",
        "article",
        "number",
    )

    article_number = normalize_article_number(
        article_number
    )

    return article_number == "第十四条"


# ============================================================
# Article 14 Deterministic Structured Rule
# ============================================================


def build_article_14_rule(
    article: Dict[str, Any],
) -> Dict[str, Any]:
    """
    构造《劳动合同法》第十四条结构化法律规则。

    ========================================================
    法律规则结构
    ========================================================

    conditions：

        1. 连续订立二次固定期限劳动合同
        2. 续订劳动合同
        3. 劳动者提出或者同意续订、订立劳动合同

    exclusion_conditions：

        1. 劳动者存在第三十九条规定的情形
        2. 劳动者存在第四十条第一项规定的情形
        3. 劳动者存在第四十条第二项规定的情形

    exceptions：

        劳动者提出订立固定期限劳动合同

    legal_obligations：

        用人单位应当订立无固定期限劳动合同

    ========================================================
    重要
    ========================================================

    这里只建立法律规则。

    不判断用户是否满足这些条件。

    用户事实由 Legal Decision Engine 处理。
    """

    result = copy_article(
        article
    )

    result["law_name"] = (
        get_first_field(
            result,
            "law_name",
            "law",
            "source",
            "document_name",
        )
        or "中华人民共和国劳动合同法"
    )

    result["article_number"] = "第十四条"

    result["classification"] = (
        get_first_field(
            result,
            "classification",
        )
        or "核心法条"
    )

    result["rule_type"] = (
        get_first_field(
            result,
            "rule_type",
        )
        or "DUTY"
    )

    result["rule_summary"] = (
        "符合《劳动合同法》第十四条规定条件时，"
        "应当订立无固定期限劳动合同"
    )

    result["conditions"] = [
        "连续订立二次固定期限劳动合同",
        "续订劳动合同",
        "劳动者提出或者同意续订、订立劳动合同",
    ]

    result["exclusion_conditions"] = [
        "劳动者存在《劳动合同法》第三十九条规定的情形",
        "劳动者存在《劳动合同法》第四十条第一项规定的情形",
        "劳动者存在《劳动合同法》第四十条第二项规定的情形",
    ]

    result["exceptions"] = [
        "劳动者提出订立固定期限劳动合同",
    ]

    result["legal_obligations"] = [
        "用人单位应当订立无固定期限劳动合同",
    ]

    result["legal_consequences"] = [
        "符合第十四条规定条件时，用人单位应当订立无固定期限劳动合同",
    ]

    result["references"] = [
        "第十四条",
        "第三十九条",
        "第四十条",
        "第四十条第一项",
        "第四十条第二项",
    ]

    result["structured_rule"] = True

    result["rule_extractor"] = (
        RETRIEVER_VERSION
    )

    result["structured_rule_source"] = (
        "deterministic_article_14_template"
    )

    return result


# ============================================================
# Generic Structured Rule
# ============================================================


def build_generic_structured_rule(
    article: Dict[str, Any],
) -> Dict[str, Any]:
    """
    构造通用结构化规则。

    ========================================================
    重要设计原则
    ========================================================

    对于非核心法条：

        不允许 Retriever 根据用户问题
        自己“猜”法律条件。

    只读取 Article 中已经存在的结构化字段。

    例如 Article 本身已经包含：

        conditions

    才进行标准化。

    如果 Article 没有：

        conditions

    则保持：

        []

    而不是根据文本自行制造条件。
    """

    result = copy_article(
        article
    )

    result["conditions"] = (
        normalize_rule_list(
            result.get(
                "conditions",
                [],
            )
        )
    )

    result["exclusion_conditions"] = (
        normalize_rule_list(
            result.get(
                "exclusion_conditions",
                [],
            )
        )
    )

    result["exceptions"] = (
        normalize_rule_list(
            result.get(
                "exceptions",
                [],
            )
        )
    )

    result["legal_obligations"] = (
        normalize_rule_list(
            result.get(
                "legal_obligations",
                [],
            )
        )
    )

    result["legal_consequences"] = (
        normalize_rule_list(
            result.get(
                "legal_consequences",
                [],
            )
        )
    )

    result["references"] = (
        normalize_rule_list(
            result.get(
                "references",
                [],
            )
        )
    )

    result["structured_rule"] = bool(
        result["conditions"]
        or result["exclusion_conditions"]
        or result["exceptions"]
        or result["legal_obligations"]
        or result["legal_consequences"]
    )

    result["rule_extractor"] = (
        RETRIEVER_VERSION
    )

    if result["structured_rule"]:

        result["structured_rule_source"] = (
            "article_existing_structured_fields"
        )

    return result


# ============================================================
# Structured Rule Extraction
# ============================================================


def extract_structured_rule(
    article: Dict[str, Any],
) -> Dict[str, Any]:
    """
    从 Article 提取结构化法律规则。

    当前采用：

        核心法条确定性模板
        +
        通用已有字段读取
    """

    if not isinstance(
        article,
        dict,
    ):
        return {}

    if is_article_14(
        article
    ):

        return build_article_14_rule(
            article
        )

    return build_generic_structured_rule(
        article
    )


def normalize_structured_rule(
    article: Dict[str, Any],
) -> Dict[str, Any]:
    """
    对结构化法律规则进行最终标准化。
    """

    result = copy_article(
        article
    )

    result["law_name"] = get_first_field(
        result,
        "law_name",
        "law",
        "source",
        "document_name",
    )

    article_number = get_first_field(
        result,
        "article_number",
        "article_no",
        "article",
        "number",
    )

    result["article_number"] = (
        normalize_article_number(
            article_number
        )
    )

    result["conditions"] = (
        normalize_rule_list(
            result.get(
                "conditions",
                [],
            )
        )
    )

    result["exclusion_conditions"] = (
        normalize_rule_list(
            result.get(
                "exclusion_conditions",
                [],
            )
        )
    )

    result["exceptions"] = (
        normalize_rule_list(
            result.get(
                "exceptions",
                [],
            )
        )
    )

    result["legal_obligations"] = (
        normalize_rule_list(
            result.get(
                "legal_obligations",
                [],
            )
        )
    )

    result["legal_consequences"] = (
        normalize_rule_list(
            result.get(
                "legal_consequences",
                [],
            )
        )
    )

    result["references"] = (
        normalize_rule_list(
            result.get(
                "references",
                [],
            )
        )
    )

    return result


def build_structured_rules(
    articles: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    将 Retriever Articles 转换为 Structured Articles。
    """

    result: List[Dict[str, Any]] = []

    for article in articles:

        if not isinstance(
            article,
            dict,
        ):
            continue

        structured = extract_structured_rule(
            article
        )

        structured = normalize_structured_rule(
            structured
        )

        result.append(
            structured
        )

    return result


# ============================================================
# Query Embedding
# ============================================================


def embed_query(
    question: str,
) -> List[float]:
    """
    将用户问题转换为 Query Vector。

    使用当前项目 embedding.py：

        embed_text(question)

    不直接调用 SentenceTransformer。
    """

    question = normalize_text(
        question
    )

    if not question:

        raise ValueError(
            "embed_query() 收到空问题"
        )

    vector = embed_text(
        question
    )

    return vector


# ============================================================
# Semantic Search
# ============================================================


def semantic_search(
    question: str,
    top_k: int = 10,
) -> List[Dict[str, Any]]:
    """
    执行 Qdrant 语义检索。

    ========================================================
    流程
    ========================================================

        question
            ↓
        embed_text()
            ↓
        query vector
            ↓
        search_vectors()
            ↓
        Qdrant ScoredPoint
            ↓
        Article Dict
    """

    question = normalize_text(
        question
    )

    if not question:
        return []

    query_vector = embed_query(
        question
    )

    try:

        results = search_vectors(
            query_vector,
            limit=top_k,
        )

    except TypeError:

        try:

            results = search_vectors(
                vector=query_vector,
                limit=top_k,
            )

        except TypeError:

            results = search_vectors(
                query=query_vector,
                limit=top_k,
            )

    return normalize_qdrant_results(
        results
    )


# ============================================================
# Article Identity
# ============================================================


def article_identity(
    article: Dict[str, Any],
) -> str:
    """
    构造 Article 唯一标识。

    优先：

        law_name + article_number

    如果没有，则使用：

        document + article_number

    最后退化到：

        text
    """

    law_name = get_first_field(
        article,
        "law_name",
        "law",
        "source",
        "document_name",
    )

    article_number = normalize_article_number(
        get_first_field(
            article,
            "article_number",
            "article_no",
            "article",
            "number",
        )
    )

    if law_name or article_number:

        return (
            f"{normalize_text(law_name)}"
            f"|"
            f"{article_number}"
        )

    text = get_first_field(
        article,
        "text",
        "content",
        "page_content",
        "chunk_text",
    )

    return normalize_rule_text(
        text
    )


# ============================================================
# Deduplication
# ============================================================


def deduplicate_articles(
    articles: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Article 去重。

    同一法律 + 同一条文只保留一个。

    如果重复 Article：

        优先保留 score 更高的。
    """

    best: Dict[
        str,
        Dict[str, Any]
    ] = {}

    for article in articles:

        if not isinstance(
            article,
            dict,
        ):
            continue

        key = article_identity(
            article
        )

        if not key:
            continue

        score = article.get(
            "score",
            article.get(
                "_score",
                0.0,
            ),
        )

        try:

            score = float(
                score
            )

        except (
            TypeError,
            ValueError,
        ):

            score = 0.0

        if key not in best:

            best[key] = copy_article(
                article
            )

        else:

            old = best[key]

            old_score = old.get(
                "score",
                old.get(
                    "_score",
                    0.0,
                ),
            )

            try:

                old_score = float(
                    old_score
                )

            except (
                TypeError,
                ValueError,
            ):

                old_score = 0.0

            if score > old_score:

                best[key] = copy_article(
                    article
                )

    return list(
        best.values()
    )


# ============================================================
# Legal Article Reference Parsing
# ============================================================


ARTICLE_PATTERN = re.compile(
    r"第\s*([0-9０-９一二三四五六七八九十百零〇]+)\s*条"
)


def parse_article_references(
    text: str,
) -> List[str]:
    """
    从法律文本中解析：

        第十四条
        第39条
        第３９条

    等法律条文引用。
    """

    text = normalize_text(
        text
    )

    if not text:
        return []

    result: List[str] = []

    for match in ARTICLE_PATTERN.finditer(
        text
    ):

        raw = match.group(0)

        normalized = normalize_article_number(
            raw
        )

        if (
            normalized
            and normalized not in result
        ):

            result.append(
                normalized
            )

    return result


def extract_article_references(
    article: Dict[str, Any],
) -> List[str]:
    """
    从 Article 的多个字段中提取法律引用。
    """

    fields = [
        "text",
        "content",
        "page_content",
        "chunk_text",
        "article_text",
        "rule_summary",
        "legal_consequences",
        "references",
    ]

    result: List[str] = []

    for field in fields:

        value = article.get(
            field
        )

        for item in ensure_list(
            value
        ):

            text = normalize_text(
                item
            )

            for reference in parse_article_references(
                text
            ):

                if reference not in result:

                    result.append(
                        reference
                    )

    return result


# ============================================================
# Find Article
# ============================================================


def find_article(
    articles: List[Dict[str, Any]],
    law_name: str,
    article_number: str,
) -> Optional[Dict[str, Any]]:
    """
    在当前 Articles 中寻找指定法条。
    """

    target_law = normalize_text(
        law_name
    )

    target_article = normalize_article_number(
        article_number
    )

    for article in articles:

        current_law = normalize_text(
            get_first_field(
                article,
                "law_name",
                "law",
                "source",
                "document_name",
            )
        )

        current_article = normalize_article_number(
            get_first_field(
                article,
                "article_number",
                "article_no",
                "article",
                "number",
            )
        )

        if (
            current_law == target_law
            and current_article
            == target_article
        ):

            return article

    return None


# ============================================================
# Legal Reference Expansion
# ============================================================


def expand_legal_references(
    articles: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    扩展法律引用。

    ========================================================
    设计原则
    ========================================================

    如果 Article A 明确引用：

        第三十九条
        第四十条

    Retriever 可以尝试从已经召回的 Articles 中寻找对应条文。

    这里不制造法律文本。

    这里只进行：

        已召回 Article
        ↓
        引用关系整理
    """

    if not articles:
        return []

    result = [
        copy_article(article)
        for article in articles
        if isinstance(
            article,
            dict,
        )
    ]

    existing = set()

    for article in result:

        identity = article_identity(
            article
        )

        if identity:

            existing.add(
                identity
            )

    expanded: List[
        Dict[str, Any]
    ] = []

    for article in result:

        references = extract_article_references(
            article
        )

        article[
            "_legal_references"
        ] = references

        expanded.append(
            article
        )

    return expanded


# ============================================================
# Question Type
# ============================================================


def detect_question_type(
    question: str,
) -> str:
    """
    简单识别问题类型。

    该函数只用于 Retriever 排序。

    不参与最终法律判断。
    """

    question = normalize_text(
        question
    )

    if any(
        keyword in question
        for keyword in [
            "是否必须",
            "是不是必须",
            "是否应当",
            "要不要",
            "能否",
            "可以吗",
        ]
    ):

        return "LEGAL_DUTY"

    if any(
        keyword in question
        for keyword in [
            "什么条件",
            "哪些条件",
            "条件是什么",
            "需要满足什么",
        ]
    ):

        return "LEGAL_CONDITION"

    if any(
        keyword in question
        for keyword in [
            "后果",
            "赔偿",
            "补偿",
            "责任",
        ]
    ):

        return "LEGAL_CONSEQUENCE"

    if any(
        keyword in question
        for keyword in [
            "是否合法",
            "违法吗",
            "违法",
            "有效吗",
        ]
    ):

        return "LEGAL_VALIDITY"

    return "GENERAL_LEGAL"


# ============================================================
# Keyword Extraction
# ============================================================


def extract_keywords(
    question: str,
) -> List[str]:
    """
    提取法律问题关键词。

    当前使用轻量级规则。

    不使用 LLM。
    """

    question = normalize_text(
        question
    )

    keywords = [
        "劳动合同",
        "固定期限",
        "无固定期限",
        "连续订立",
        "续订",
        "劳动者",
        "用人单位",
        "第三十九条",
        "第四十条",
        "第十四条",
        "第八十二条",
        "解除",
        "终止",
        "赔偿",
        "补偿",
        "试用期",
        "工资",
        "加班",
        "竞业限制",
    ]

    result: List[str] = []

    for keyword in keywords:

        if keyword in question:

            result.append(
                keyword
            )

    return result


# ============================================================
# Core Articles
# ============================================================


CORE_ARTICLES = {
    "第十四条",
    "第三十九条",
    "第四十条",
    "第八十二条",
    "第二十条",
}


def is_core_article(
    article: Dict[str, Any],
) -> bool:
    """
    判断是否为核心法条。
    """

    article_number = normalize_article_number(
        get_first_field(
            article,
            "article_number",
            "article_no",
            "article",
            "number",
        )
    )

    return article_number in CORE_ARTICLES


# ============================================================
# Rule Score
# ============================================================


def calculate_rule_score(
    article: Dict[str, Any],
    question: str,
) -> float:
    """
    计算法律规则相关性分数。

    注意：

    该分数只用于 Retriever 排序。

    不代表法律结论。
    """

    question = normalize_text(
        question
    )

    score = 0.0

    keywords = extract_keywords(
        question
    )

    text_parts = [
        get_first_field(
            article,
            "law_name",
            "law",
            "source",
            "document_name",
        ),
        get_first_field(
            article,
            "article_number",
            "article_no",
            "article",
            "number",
        ),
        get_first_field(
            article,
            "text",
            "content",
            "page_content",
            "chunk_text",
        ),
        get_first_field(
            article,
            "rule_summary",
        ),
    ]

    text = " ".join(
        text_parts
    )

    text = normalize_text(
        text
    )

    for keyword in keywords:

        if keyword in text:

            score += 1.0

    if is_core_article(
        article
    ):

        score += 1.5

    if is_article_14(
        article
    ):

        score += 3.0

    return score


# ============================================================
# Ranking
# ============================================================


def rank_articles(
    articles: List[Dict[str, Any]],
    question: str,
) -> List[Dict[str, Any]]:
    """
    对法律 Articles 排序。

    排序因素：

        1. Qdrant semantic score
        2. rule relevance score
        3. core article bonus
    """

    ranked: List[
        Dict[str, Any]
    ] = []

    for article in articles:

        item = copy_article(
            article
        )

        semantic_score = item.get(
            "score",
            item.get(
                "_score",
                0.0,
            ),
        )

        try:

            semantic_score = float(
                semantic_score
            )

        except (
            TypeError,
            ValueError,
        ):

            semantic_score = 0.0

        rule_score = calculate_rule_score(
            item,
            question,
        )

        item[
            "_semantic_score"
        ] = semantic_score

        item[
            "_rule_score"
        ] = rule_score

        item[
            "_ranking_score"
        ] = (
            semantic_score
            + rule_score * 0.05
        )

        ranked.append(
            item
        )

    ranked.sort(
        key=lambda x: x.get(
            "_ranking_score",
            0.0,
        ),
        reverse=True,
    )

    return ranked


# ============================================================
# Irrelevant Article Filtering
# ============================================================


def filter_irrelevant_articles(
    articles: List[Dict[str, Any]],
    question: str,
    score_threshold: float = 0.0,
) -> List[Dict[str, Any]]:
    """
    过滤明显无关 Article。

    注意：

    Retriever 不应过度过滤法律依据。

    因此默认仅过滤：

        明确 semantic score 无效
        且没有任何文本相关性的 Article
    """

    if not articles:
        return []

    keywords = extract_keywords(
        question
    )

    result: List[
        Dict[str, Any]
    ] = []

    for article in articles:

        semantic_score = article.get(
            "score",
            article.get(
                "_score",
                0.0,
            ),
        )

        try:

            semantic_score = float(
                semantic_score
            )

        except (
            TypeError,
            ValueError,
        ):

            semantic_score = 0.0

        text = " ".join(
            [
                get_first_field(
                    article,
                    "law_name",
                    "law",
                    "source",
                    "document_name",
                ),
                get_first_field(
                    article,
                    "article_number",
                    "article_no",
                    "article",
                    "number",
                ),
                get_first_field(
                    article,
                    "text",
                    "content",
                    "page_content",
                    "chunk_text",
                ),
                get_first_field(
                    article,
                    "rule_summary",
                ),
            ]
        )

        keyword_hit = any(
            keyword in text
            for keyword in keywords
        )

        if (
            semantic_score
            >= score_threshold
        ):

            result.append(
                article
            )

        elif keyword_hit:

            result.append(
                article
            )

        elif is_core_article(
            article
        ):

            result.append(
                article
            )

    return result


# ============================================================
# Importance
# ============================================================


def assign_importance(
    articles: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    给 Article 分配重要性。

    重要性只用于：

        Context 展示
        排序
        Answer Builder

    不参与最终法律判断。
    """

    result: List[
        Dict[str, Any]
    ] = []

    for article in articles:

        item = copy_article(
            article
        )

        if is_article_14(
            item
        ):

            importance = "CRITICAL"

        elif is_core_article(
            item
        ):

            importance = "HIGH"

        else:

            importance = "NORMAL"

        item[
            "importance"
        ] = importance

        result.append(
            item
        )

    return result


# ============================================================
# Prepare Articles
# ============================================================


def prepare_articles(
    articles: List[Dict[str, Any]],
    question: str,
) -> List[Dict[str, Any]]:
    """
    Retriever 最终 Article 处理入口。

    ========================================================
    V6.0 修复
    ========================================================

    旧版本：

        deduplicate
        ↓
        rank
        ↓
        filter
        ↓
        importance
        ↓
        return

    导致：

        Structured Rule = 空

    新版本：

        deduplicate
        ↓
        rank
        ↓
        filter
        ↓
        importance
        ↓
        Structured Rule Extraction
        ↓
        return
    """

    result = deduplicate_articles(
        articles
    )

    result = rank_articles(
        result,
        question,
    )

    result = filter_irrelevant_articles(
        result,
        question,
    )

    result = assign_importance(
        result
    )

    # ========================================================
    # V6.0 核心修复
    # ========================================================

    result = build_structured_rules(
        result
    )

    return result


# ============================================================
# Retrieve
# ============================================================


def retrieve(
    question: str,
    top_k: int = 10,
    score_threshold: float = 0.55,
) -> List[Dict[str, Any]]:
    """
    完整法律 Retriever。

    ========================================================
    流程
    ========================================================

        用户问题
            ↓
        Query Embedding
            ↓
        Qdrant
            ↓
        Semantic Articles
            ↓
        去重
            ↓
        法律引用
            ↓
        排序
            ↓
        过滤
            ↓
        Structured Rule
            ↓
        返回
    """

    question = normalize_text(
        question
    )

    if not question:
        return []

    # ========================================================
    # Step 1
    # Semantic Search
    # ========================================================

    articles = semantic_search(
        question=question,
        top_k=top_k,
    )

    # ========================================================
    # Step 2
    # Score Threshold
    # ========================================================

    filtered: List[
        Dict[str, Any]
    ] = []

    for article in articles:

        if not isinstance(
            article,
            dict,
        ):
            continue

        score = article.get(
            "score",
            article.get(
                "_score",
                0.0,
            ),
        )

        try:

            score = float(
                score
            )

        except (
            TypeError,
            ValueError,
        ):

            score = 0.0

        if score >= score_threshold:

            filtered.append(
                article
            )

    # 如果阈值过滤后没有结果，
    # 保留原始结果，避免法律问题完全无依据。

    if filtered:

        articles = filtered

    # ========================================================
    # Step 3
    # Deduplicate
    # ========================================================

    articles = deduplicate_articles(
        articles
    )

    # ========================================================
    # Step 4
    # Legal Reference Expansion
    # ========================================================

    articles = expand_legal_references(
        articles
    )

    # ========================================================
    # Step 5
    # Prepare Structured Articles
    # ========================================================

    articles = prepare_articles(
        articles,
        question,
    )

    return articles


# ============================================================
# Context Formatting
# ============================================================


def format_context(
    articles: List[Dict[str, Any]],
) -> str:
    """
    将 Structured Articles 转换成 Context 文本。

    ========================================================
    注意
    ========================================================

    Context 是给：

        Answer Builder
        Ollama

    使用的。

    Ollama 只负责自然语言表达，
    不负责重新判断法律条件。
    """

    if not articles:
        return ""

    blocks: List[str] = []

    for index, article in enumerate(
        articles,
        start=1,
    ):

        law_name = get_first_field(
            article,
            "law_name",
            "law",
            "source",
            "document_name",
        )

        article_number = (
            normalize_article_number(
                get_first_field(
                    article,
                    "article_number",
                    "article_no",
                    "article",
                    "number",
                )
            )
        )

        rule_summary = get_first_field(
            article,
            "rule_summary",
        )

        text = get_first_field(
            article,
            "text",
            "content",
            "page_content",
            "chunk_text",
        )

        conditions = normalize_rule_list(
            article.get(
                "conditions",
                [],
            )
        )

        exclusions = normalize_rule_list(
            article.get(
                "exclusion_conditions",
                [],
            )
        )

        exceptions = normalize_rule_list(
            article.get(
                "exceptions",
                [],
            )
        )

        obligations = normalize_rule_list(
            article.get(
                "legal_obligations",
                [],
            )
        )

        consequences = normalize_rule_list(
            article.get(
                "legal_consequences",
                [],
            )
        )

        references = normalize_rule_list(
            article.get(
                "references",
                [],
            )
        )

        lines: List[str] = []

        lines.append(
            f"[法律依据 {index}]"
        )

        if law_name:

            lines.append(
                f"法律：{law_name}"
            )

        if article_number:

            lines.append(
                f"条文：{article_number}"
            )

        if rule_summary:

            lines.append(
                f"规则摘要：{rule_summary}"
            )

        if conditions:

            lines.append(
                "成立条件："
                + "；".join(
                    conditions
                )
            )

        if exclusions:

            lines.append(
                "排除条件："
                + "；".join(
                    exclusions
                )
            )

        if exceptions:

            lines.append(
                "例外："
                + "；".join(
                    exceptions
                )
            )

        if obligations:

            lines.append(
                "法律义务："
                + "；".join(
                    obligations
                )
            )

        if consequences:

            lines.append(
                "法律后果："
                + "；".join(
                    consequences
                )
            )

        if references:

            lines.append(
                "法律引用："
                + "；".join(
                    references
                )
            )

        if text:

            lines.append(
                f"原文：{text}"
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
# Build Context
# ============================================================


def build_context(
    question: str,
    top_k: int = 10,
    score_threshold: float = 0.55,
    return_articles: bool = False,
):
    """
    构建法律 Context。

    ========================================================
    返回
    ========================================================

    return_articles=False：

        返回 Context 字符串。

    return_articles=True：

        返回 Structured Articles。

    这样可以兼容：

        RAG V5.x
        RAG V6.x
    """

    articles = retrieve(
        question=question,
        top_k=top_k,
        score_threshold=score_threshold,
    )

    context = format_context(
        articles
    )

    if return_articles:

        return articles

    return context


# ============================================================
# Compatibility API
# ============================================================


def retrieve_articles(
    question: str,
    top_k: int = 10,
    score_threshold: float = 0.55,
) -> List[Dict[str, Any]]:
    """
    兼容旧版调用接口。
    """

    return retrieve(
        question=question,
        top_k=top_k,
        score_threshold=score_threshold,
    )


# ============================================================
# Local Tests
# ============================================================


def test_article_number_normalization():
    """
    测试条文编号标准化。
    """

    assert (
        normalize_article_number(
            "第14条"
        )
        == "第十四条"
    )

    assert (
        normalize_article_number(
            "第１４条"
        )
        == "第十四条"
    )

    assert (
        normalize_article_number(
            "第十四条"
        )
        == "第十四条"
    )

    assert (
        normalize_article_number(
            "第39条"
        )
        == "第三十九条"
    )

    assert (
        normalize_article_number(
            "第40条"
        )
        == "第四十条"
    )

    print(
        "Article Number Normalization Test：通过"
    )


def test_qdrant_point_normalization():
    """
    测试 Qdrant ScoredPoint → Article Dict。

    该测试不需要连接 Qdrant。
    """

    class FakePoint:

        id = "test-id"

        score = 0.95

        payload = {
            "law_name":
                "中华人民共和国劳动合同法",

            "article_number":
                "第14条",

            "text":
                "测试法律文本",
        }

    result = qdrant_point_to_article(
        FakePoint()
    )

    assert isinstance(
        result,
        dict,
    )

    assert result["id"] == "test-id"

    assert result["score"] == 0.95

    assert (
        result["law_name"]
        == "中华人民共和国劳动合同法"
    )

    assert (
        result["article_number"]
        == "第14条"
    )

    print(
        "Qdrant Point Normalization Test：通过"
    )


def test_article_14_structured_rule():
    """
    测试第十四条结构化规则。

    这是本版本最重要的单元测试之一。
    """

    article = {
        "law_name":
            "中华人民共和国劳动合同法",

        "article_number":
            "第14条",

        "text":
            (
                "用人单位与劳动者协商一致，"
                "可以订立无固定期限劳动合同。"
            ),
    }

    result = extract_structured_rule(
        article
    )

    assert (
        result["article_number"]
        == "第十四条"
    )

    assert len(
        result["conditions"]
    ) == 3

    assert len(
        result[
            "exclusion_conditions"
        ]
    ) == 3

    assert len(
        result["exceptions"]
    ) == 1

    assert len(
        result["legal_obligations"]
    ) == 1

    assert len(
        result["legal_consequences"]
    ) == 1

    assert (
        result["structured_rule"]
        is True
    )

    print(
        "Article 14 Structured Rule Test：通过"
    )

    print(
        "conditions：",
        len(
            result["conditions"]
        ),
    )

    print(
        "exclusion_conditions：",
        len(
            result[
                "exclusion_conditions"
            ]
        ),
    )

    print(
        "exceptions：",
        len(
            result["exceptions"]
        ),
    )

    print(
        "legal_obligations：",
        len(
            result[
                "legal_obligations"
            ]
        ),
    )


def test_generic_rule_does_not_invent_conditions():
    """
    测试通用规则不会凭空制造条件。

    例如：

        Article 13

    如果原 Article 没有：

        conditions

    Retriever 不应该根据用户问题自行创建条件。
    """

    article = {
        "law_name":
            "中华人民共和国劳动合同法",

        "article_number":
            "第十三条",

        "text":
            "固定期限劳动合同，是指用人单位与劳动者约定合同终止时间的劳动合同。",
    }

    result = extract_structured_rule(
        article
    )

    assert result.get(
        "conditions",
        [],
    ) == []

    assert result.get(
        "exclusion_conditions",
        [],
    ) == []

    assert result.get(
        "exceptions",
        [],
    ) == []

    print(
        "Generic Rule No-Invention Test：通过"
    )


def test_prepare_articles():
    """
    测试 prepare_articles() 是否真正产生 Structured Rule。
    """

    articles = [
        {
            "law_name":
                "中华人民共和国劳动合同法",

            "article_number":
                "第14条",

            "score":
                0.95,

            "text":
                "相关法律文本",
        }
    ]

    result = prepare_articles(
        articles,
        "公司连续签订三次固定期限劳动合同后，是否必须签订无固定期限劳动合同？",
    )

    assert len(
        result
    ) == 1

    article = result[0]

    assert (
        article[
            "article_number"
        ]
        == "第十四条"
    )

    assert len(
        article["conditions"]
    ) == 3

    assert len(
        article[
            "exclusion_conditions"
        ]
    ) == 3

    assert len(
        article["exceptions"]
    ) == 1

    assert len(
        article[
            "legal_obligations"
        ]
    ) == 1

    assert len(
        article[
            "legal_consequences"
        ]
    ) == 1

    assert (
        article["structured_rule"]
        is True
    )

    print(
        "prepare_articles Structured Rule Test：通过"
    )


def test_three_contract_rule_structure():
    """
    专门测试用户当前核心问题：

        公司连续签订三次固定期限劳动合同后，
        是否必须签订无固定期限劳动合同？

    注意：

    Retriever 这里只建立法律规则。

    不直接判断用户事实。
    """

    article = {
        "law_name":
            "中华人民共和国劳动合同法",

        "article_number":
            "第十四条",

        "score":
            0.99,

        "text":
            "相关法律文本",
    }

    result = extract_structured_rule(
        article
    )

    expected_conditions = [
        "连续订立二次固定期限劳动合同",
        "续订劳动合同",
        "劳动者提出或者同意续订、订立劳动合同",
    ]

    expected_exclusions = [
        "劳动者存在《劳动合同法》第三十九条规定的情形",
        "劳动者存在《劳动合同法》第四十条第一项规定的情形",
        "劳动者存在《劳动合同法》第四十条第二项规定的情形",
    ]

    expected_exceptions = [
        "劳动者提出订立固定期限劳动合同",
    ]

    assert (
        result["conditions"]
        == expected_conditions
    )

    assert (
        result[
            "exclusion_conditions"
        ]
        == expected_exclusions
    )

    assert (
        result["exceptions"]
        == expected_exceptions
    )

    assert (
        result["legal_obligations"]
        == [
            "用人单位应当订立无固定期限劳动合同"
        ]
    )

    assert (
        result[
            "legal_consequences"
        ]
        == [
            "符合第十四条规定条件时，用人单位应当订立无固定期限劳动合同"
        ]
    )

    print(
        "Three-Contract Rule Structure Test：通过"
    )


# ============================================================
# Local Test Runner
# ============================================================


def run_local_tests():
    """
    执行 Retriever V6.0 本地测试。
    """

    print()

    print(
        "=" * 70
    )

    print(
        "RAG V6.0 Structured Retriever Tests"
    )

    print(
        "=" * 70
    )

    test_article_number_normalization()

    test_qdrant_point_normalization()

    test_article_14_structured_rule()

    test_generic_rule_does_not_invent_conditions()

    test_prepare_articles()

    test_three_contract_rule_structure()

    print()

    print(
        "全部 Retriever V6.0 测试通过"
    )

    print(
        "=" * 70
    )


# ============================================================
# Main
# ============================================================


if __name__ == "__main__":

    run_local_tests()