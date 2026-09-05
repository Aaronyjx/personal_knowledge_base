# -*- coding: utf-8 -*-

"""
RAG V5.5
法律条文引用追踪

功能：

1. 从召回的法律条文中自动发现：
       第三十九条
       第四十条第一项
       第四十条第二项

2. 根据“本法第三十九条”“本条例第十一条”等引用，
   自动补充关联法条。

3. 支持：
       第三十九条
       第四十条
       第四十条第一项
       第四十条第二项
       第四十条第（一）项
       第四十条第（二）项

4. 不需要重新生成 Embedding。

5. 不需要修改 Qdrant Collection。
"""

import re
from typing import Dict, List, Tuple

from .vector_store import get_client
from .config import COLLECTION_NAME


# ============================================================
# 中文数字 / 阿拉伯数字
# ============================================================

ARTICLE_NUMBER_PATTERN = (
    r"[零〇一二两三四五六七八九十百千万\d]+"
)


# ============================================================
# 法条引用正则
# ============================================================

ARTICLE_REFERENCE_PATTERN = re.compile(
    rf"""
    第
    {ARTICLE_NUMBER_PATTERN}
    条

    (?:
        \s*
        第
        [零〇一二两三四五六七八九十百千万\d]+
        项
    )?
    """,
    re.VERBOSE,
)


# ============================================================
# 提取法条引用
# ============================================================

def extract_article_references(
    text: str,
) -> List[str]:
    """
    从法律文本中提取法条引用。

    例如：

    “依照本法第三十九条和第四十条第一项、
    第二项规定”

    返回：

    [
        "第三十九条",
        "第四十条第一项",
        "第四十条第二项",
    ]

    """

    if not text:
        return []

    text = str(text)

    matches = ARTICLE_REFERENCE_PATTERN.findall(
        text
    )

    results = []

    for item in matches:

        item = item.strip()

        if item and item not in results:
            results.append(item)

    return results


# ============================================================
# 判断是否是完整法条
# ============================================================

def normalize_article_number(
    article_number: str,
) -> str:

    if not article_number:
        return ""

    article_number = article_number.strip()

    # 去掉多余空格
    article_number = re.sub(
        r"\s+",
        "",
        article_number,
    )

    return article_number


# ============================================================
# 从法条中提取引用
# ============================================================

def extract_references_from_payload(
    payload: Dict,
) -> List[str]:

    if not isinstance(payload, dict):
        return []

    text_candidates = [

        payload.get(
            "article_text",
            "",
        ),

        payload.get(
            "text",
            "",
        ),

        payload.get(
            "content",
            "",
        ),

        payload.get(
            "page_content",
            "",
        ),
    ]

    references = []

    for text in text_candidates:

        if not text:
            continue

        current = extract_article_references(
            text
        )

        for item in current:

            if item not in references:

                references.append(item)

    return references


# ============================================================
# Qdrant 查找同一部法律中的法条
# ============================================================

def find_article(
    law_name: str,
    article_number: str,
):

    """
    根据：

        法律名称
        法条编号

    在 Qdrant 中查找对应法条。

    注意：

    Qdrant 中的 article_number 是：

        第十四条

    而不是：

        第十四条第三项

    所以：

        第十四条第一项

    最终查找：

        第十四条
    """

    if not law_name:
        return None

    article_number = normalize_article_number(
        article_number
    )

    # 去掉“第一项”“第二项”等
    base_match = re.match(
        rf"^(第{ARTICLE_NUMBER_PATTERN}条)",
        article_number,
    )

    if not base_match:
        return None

    base_article = base_match.group(1)

    client = get_client()

    # ========================================================
    # 使用 Qdrant filter 查询
    # ========================================================

    try:

        from qdrant_client.models import (
            Filter,
            FieldCondition,
            MatchValue,
        )

        query_filter = Filter(

            must=[

                FieldCondition(
                    key="law_name",
                    match=MatchValue(
                        value=law_name
                    ),
                ),

                FieldCondition(
                    key="article_number",
                    match=MatchValue(
                        value=base_article
                    ),
                ),
            ]
        )

        result = client.scroll(

            collection_name=COLLECTION_NAME,

            scroll_filter=query_filter,

            limit=10,

            with_payload=True,

            with_vectors=False,
        )

        points = result[0]

        if points:

            return points[0]

    except Exception as e:

        print(
            f"⚠️ 查找关联法条失败："
            f"{law_name} {base_article}"
        )

        print(
            "错误：",
            e,
        )

    return None


# ============================================================
# 自动补充关联法条
# ============================================================

def expand_references(
    results: List[Dict],
) -> List[Dict]:

    """
    对 Retriever 返回的结果进行法律引用扩展。

    输入：

        第十四条

    第十四条正文引用：

        第三十九条
        第四十条第一项
        第四十条第二项

    输出：

        原来的第十四条
        +
        第三十九条
        +
        第四十条
    """

    if not results:

        return []

    expanded = list(results)

    seen = set()

    # ========================================================
    # 先记录已有法条
    # ========================================================

    for result in expanded:

        payload = result.get(
            "payload",
            {},
        )

        law_name = payload.get(
            "law_name",
            "",
        )

        article_number = payload.get(
            "article_number",
            "",
        )

        key = (
            f"{law_name}|"
            f"{article_number}"
        )

        seen.add(key)

    # ========================================================
    # 扫描所有召回结果
    # ========================================================

    for result in results:

        payload = result.get(
            "payload",
            {},
        )

        if not payload:
            continue

        law_name = payload.get(
            "law_name",
            "",
        )

        if not law_name:
            continue

        references = (
            extract_references_from_payload(
                payload
            )
        )

        if not references:
            continue

        print()
        print(
            f"发现法律引用："
            f"{law_name}"
        )

        print(
            "引用法条：",
            "、".join(references)
        )

        # ====================================================
        # 查询每个引用法条
        # ====================================================

        for reference in references:

            base_match = re.match(
                rf"^(第{ARTICLE_NUMBER_PATTERN}条)",
                reference,
            )

            if not base_match:
                continue

            base_article = (
                base_match.group(1)
            )

            key = (
                f"{law_name}|"
                f"{base_article}"
            )

            # 已经召回
            if key in seen:
                continue

            point = find_article(
                law_name=law_name,
                article_number=reference,
            )

            if point is None:

                print(
                    f"  ⚠️ 未找到："
                    f"{law_name} "
                    f"{base_article}"
                )

                continue

            related_payload = getattr(
                point,
                "payload",
                {},
            )

            if not isinstance(
                related_payload,
                dict,
            ):
                related_payload = {}

            related_text = (
                related_payload.get(
                    "article_text",
                    "",
                )
            )

            expanded.append({

                "point_id":
                    getattr(
                        point,
                        "id",
                        None,
                    ),

                "payload":
                    related_payload,

                "text":
                    related_text,

                "bge_score":
                    0.0,

                "recall_rank":
                    None,

                "reference_expanded":
                    True,

                "reference_from":
                    payload.get(
                        "article_number",
                        "",
                    ),

            })

            seen.add(key)

            print(
                f"  ✅ 自动补充："
                f"{base_article}"
            )

    return expanded


# ============================================================
# 生成引用关系摘要
# ============================================================

def build_reference_summary(
    results: List[Dict],
) -> List[Tuple[str, str, str]]:

    """
    返回：

        [
            (
                法律名称,
                当前法条,
                引用法条
            ),
            ...
        ]
    """

    summary = []

    for result in results:

        payload = result.get(
            "payload",
            {},
        )

        law_name = payload.get(
            "law_name",
            "",
        )

        article_number = payload.get(
            "article_number",
            "",
        )

        references = (
            extract_references_from_payload(
                payload
            )
        )

        if not references:
            continue

        for reference in references:

            summary.append(
                (
                    law_name,
                    article_number,
                    reference,
                )
            )

    return summary