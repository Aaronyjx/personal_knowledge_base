# -*- coding: utf-8 -*-

"""
RAG V5.1
BGE Reranker
"""

from typing import List, Dict

from sentence_transformers import CrossEncoder

from .config import RERANKER_MODEL


_model = None


def get_reranker():

    global _model

    if _model is None:

        print()
        print(
            "加载 Reranker："
            f"{RERANKER_MODEL}"
        )

        _model = CrossEncoder(
            RERANKER_MODEL
        )

        print(
            "Reranker 加载完成"
        )

    return _model


def rerank(
    query: str,
    results: List[Dict],
    top_k: int = 5,
):

    if not results:

        return []

    model = get_reranker()

    pairs = []

    for item in results:

        text = item.get(
            "text",
            "",
        )

        pairs.append(
            [
                query,
                text,
            ]
        )

    scores = model.predict(
        pairs
    )

    reranked = []

    for item, score in zip(
        results,
        scores,
    ):

        item = dict(item)

        item["rerank_score"] = float(
            score
        )

        reranked.append(
            item
        )

    reranked.sort(
        key=lambda x:
            x["rerank_score"],
        reverse=True,
    )

    for rank, item in enumerate(
        reranked[:top_k],
        start=1,
    ):

        item["rerank_rank"] = rank

    return reranked[:top_k]


def rerank_with_diagnostics(
    query: str,
    results: List[Dict],
    top_k: int = 5,
):

    reranked = rerank(
        query,
        results,
        top_k,
    )

    print()
    print("=" * 70)

    print(
        "RAG V5.1 - Reranker"
    )

    print(
        f"最终证据：{len(reranked)} 条"
    )

    print("=" * 70)

    for i, item in enumerate(
        reranked,
        start=1,
    ):

        payload = item.get(
            "payload",
            {},
        )

        print()
        print(
            f"[{i}] "
            f"{payload.get('law_name')} "
            f"{payload.get('article')}"
        )

        print(
            "BGE Score:",
            round(
                item.get(
                    "bge_score",
                    0,
                ),
                6,
            )
        )

        print(
            "Rerank Score:",
            round(
                item.get(
                    "rerank_score",
                    0,
                ),
                6,
            )
        )

        print(
            "Text:",
            item.get(
                "text",
                "",
            )[:180],
        )

    return reranked