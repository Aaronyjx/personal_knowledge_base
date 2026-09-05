# -*- coding: utf-8 -*-

"""
RAG V5.7
Qdrant Vector Store

功能：

1. Qdrant 连接
2. Collection 管理
3. 法条唯一 ID
4. 增量 Upsert
5. BGE-M3 向量搜索
6. 按法律名称 + 法条编号精确查询
7. 法律引用链补全

V5.7 核心升级：

    law_name + article_number
                    ↓
             Qdrant 精确查询
                    ↓
             返回完整法条

用于解决：

    第十四条
       ↓
    引用第三十九条
       ↓
    第三十九条不在 Top K
       ↓
    V5.7 直接从 Qdrant 精确补回
"""

from typing import List, Dict, Optional
from uuid import uuid5, NAMESPACE_URL

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
)


from .config import (
    QDRANT_URL,
    COLLECTION_NAME,
    VECTOR_SIZE,
)


# ============================================================
# Qdrant Client
# ============================================================

_client = None


def get_client():

    global _client

    if _client is None:

        _client = QdrantClient(
            url=QDRANT_URL,
            trust_env=False,
        )

    return _client


# ============================================================
# Collection
# ============================================================

def collection_exists() -> bool:

    client = get_client()

    try:

        return client.collection_exists(
            COLLECTION_NAME
        )

    except Exception:

        collections = client.get_collections()

        names = [
            item.name
            for item in collections.collections
        ]

        return COLLECTION_NAME in names


def ensure_collection():

    client = get_client()

    if collection_exists():

        print(
            f"Collection 已存在："
            f"{COLLECTION_NAME}"
        )

        return

    client.create_collection(

        collection_name=COLLECTION_NAME,

        vectors_config=VectorParams(
            size=VECTOR_SIZE,
            distance=Distance.COSINE,
        ),
    )

    print(
        f"创建 Qdrant Collection："
        f"{COLLECTION_NAME}"
    )


# ============================================================
# Point ID
# ============================================================

def make_point_id(
    law_name: str,
    article_number,
) -> str:

    """
    同一部法律 + 同一条款
    永远生成相同 UUID。

    例如：

    中华人民共和国劳动合同法
    第十四条

    → 固定 UUID

    从根本上避免重复入库。
    """

    law_name = str(
        law_name
    ).strip()

    article_number = str(
        article_number
    ).strip()

    key = (
        f"{law_name}|"
        f"{article_number}"
    )

    return str(
        uuid5(
            NAMESPACE_URL,
            key,
        )
    )


# ============================================================
# Upsert
# ============================================================

def upsert_points(
    points: List[PointStruct],
):

    if not points:

        return 0

    client = get_client()

    client.upsert(
        collection_name=COLLECTION_NAME,
        points=points,
    )

    return len(points)


# ============================================================
# Semantic Search
# ============================================================

def search_vectors(
    vector,
    limit: int = 20,
):

    client = get_client()

    result = client.query_points(

        collection_name=COLLECTION_NAME,

        query=vector,

        limit=limit,

        with_payload=True,

    )

    return result.points


# ============================================================
# V5.7
# 精确查询单个法律条款
# ============================================================

def get_article(
    law_name: str,
    article_number: str,
) -> Optional[Dict]:

    """
    根据：

        法律名称
        +
        法条编号

    精确查询 Qdrant。

    例如：

        get_article(
            "中华人民共和国劳动合同法",
            "第三十九条",
        )

    返回：

        {
            "id": ...,
            "payload": ...
        }

    找不到：

        None

    注意：

    这里不进行向量搜索。

    这是精确查询。

    用于法律引用链补全。
    """

    law_name = str(
        law_name
    ).strip()

    article_number = str(
        article_number
    ).strip()

    point_id = make_point_id(
        law_name,
        article_number,
    )

    client = get_client()

    try:

        points = client.retrieve(
            collection_name=COLLECTION_NAME,
            ids=[point_id],
            with_payload=True,
            with_vectors=False,
        )

    except Exception as e:

        print(
            f"⚠️ Qdrant 精确查询失败："
            f"{e}"
        )

        return None

    if not points:

        return None

    point = points[0]

    return {
        "id": getattr(
            point,
            "id",
            point_id,
        ),
        "payload": getattr(
            point,
            "payload",
            {},
        ),
    }


# ============================================================
# V5.7
# 精确查询多个法律条款
# ============================================================

def get_articles(
    law_name: str,
    article_numbers: List[str],
) -> List[Dict]:

    """
    批量精确查询。

    例如：

        get_articles(
            "中华人民共和国劳动合同法",
            [
                "第三十九条",
                "第四十条",
            ],
        )

    返回所有能够找到的法条。
    """

    results = []

    if not article_numbers:

        return results

    for article_number in article_numbers:

        result = get_article(
            law_name,
            article_number,
        )

        if result is not None:

            results.append(
                result
            )

    return results


# ============================================================
# V5.7
# 根据 payload 查询
# ============================================================

def search_article_by_payload(
    law_name: str,
    article_number: str,
) -> Optional[Dict]:

    """
    备用精确查询。

    如果 UUID 查询失败，
    使用 Qdrant payload Filter 查询。

    这样可以提高 V5.7 的兼容性。

    要求 payload 中存在：

        law_name
        article_number
    """

    client = get_client()

    try:

        result = client.scroll(

            collection_name=COLLECTION_NAME,

            scroll_filter=Filter(

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
                            value=article_number
                        ),
                    ),
                ]
            ),

            limit=1,

            with_payload=True,

            with_vectors=False,
        )

    except Exception:

        return None

    points = result[0]

    if not points:

        return None

    point = points[0]

    return {
        "id": getattr(
            point,
            "id",
            None,
        ),
        "payload": getattr(
            point,
            "payload",
            {},
        ),
    }


# ============================================================
# V5.7
# 强化版精确查询
# ============================================================

def get_article_exact(
    law_name: str,
    article_number: str,
) -> Optional[Dict]:

    """
    强化版精确查询。

    第一层：

        UUID retrieve

    第二层：

        Payload Filter

    目的：

    即使历史数据的 UUID 生成方式存在差异，
    也可以通过 payload 找到法条。
    """

    result = get_article(
        law_name,
        article_number,
    )

    if result is not None:

        return result

    return search_article_by_payload(
        law_name,
        article_number,
    )


# ============================================================
# Collection Info
# ============================================================

def get_collection_info():

    client = get_client()

    return client.get_collection(
        COLLECTION_NAME
    )


# ============================================================
# Count
# ============================================================

def count_points() -> int:

    info = get_collection_info()

    return info.points_count


# ============================================================
# Delete Collection
# ============================================================

def delete_collection():

    client = get_client()

    if collection_exists():

        client.delete_collection(
            COLLECTION_NAME
        )

        print(
            f"✅ 已删除 Collection："
            f"{COLLECTION_NAME}"
        )


# ============================================================
# Clear Collection
# ============================================================

def clear_collection():

    client = get_client()

    if not collection_exists():

        print(
            f"Collection 不存在："
            f"{COLLECTION_NAME}"
        )

        ensure_collection()

        return

    info = get_collection_info()

    print("=" * 70)
    print("清空 Qdrant Collection")
    print("=" * 70)

    print(
        "Collection：",
        COLLECTION_NAME,
    )

    print(
        "清空前向量数量：",
        info.points_count,
    )

    client.delete_collection(
        COLLECTION_NAME
    )

    ensure_collection()

    info = get_collection_info()

    print(
        "清空后向量数量：",
        info.points_count,
    )