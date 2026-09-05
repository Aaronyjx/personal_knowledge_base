# -*- coding: utf-8 -*-

"""
Legal Evidence Engine
RAG V5.0
"""

import re
from typing import Dict


def normalize_article(
    article: str,
) -> str:

    if not article:
        return ""

    article = str(
        article
    ).strip()

    article = article.replace(
        "第",
        "",
    )

    article = article.replace(
        "条",
        "",
    )

    article = article.strip()

    mapping = {
        "一": "1",
        "二": "2",
        "三": "3",
        "四": "4",
        "五": "5",
        "六": "6",
        "七": "7",
        "八": "8",
        "九": "9",
        "十": "10",
        "十一": "11",
        "十二": "12",
        "十三": "13",
        "十四": "14",
        "十五": "15",
        "十六": "16",
        "十七": "17",
        "十八": "18",
        "十九": "19",
        "二十": "20",
        "二十一": "21",
    }

    return mapping.get(
        article,
        article,
    )


def get_law_name(
    payload: Dict,
) -> str:

    for key in [
        "law_name",
        "title",
        "document_name",
        "file_name",
    ]:

        value = payload.get(
            key
        )

        if value:

            return str(
                value
            )

    return "未知法律"


def get_article(
    payload: Dict,
) -> str:

    for key in [
        "article",
        "article_number",
        "clause",
    ]:

        value = payload.get(
            key
        )

        if value is not None:

            return normalize_article(
                str(value)
            )

    return ""


def classify_role(
    payload: Dict,
    query: str,
) -> str:

    law = get_law_name(
        payload
    )

    article = get_article(
        payload
    )

    text = payload.get(
        "text",
        "",
    )

    # ========================================================
    # 试用期最长
    # ========================================================

    if "试用期" in query:

        if any(
            key in query
            for key in [
                "最长",
                "最多",
                "上限",
                "多久",
                "多长",
            ]
        ):

            if (
                "劳动合同法"
                in law
                and article == "19"
            ):

                return "primary"

            if (
                "劳动法"
                in law
                and article == "21"
            ):

                return "supporting"

            if (
                "劳动合同法"
                in law
                and article in [
                    "20",
                    "21",
                ]
            ):

                return "supporting"

            if (
                "劳动合同法"
                in law
                and article == "83"
            ):

                return "penalty"

            if "试用期" in text:

                return "supporting"

    # ========================================================
    # General
    # ========================================================

    if "试用期" in text:

        return "supporting"

    return "irrelevant"


def role_score(
    role: str,
) -> float:

    return {
        "primary": 1.00,
        "direct": 0.90,
        "supporting": 0.70,
        "special": 0.40,
        "penalty": 0.10,
        "irrelevant": 0.00,
    }.get(
        role,
        0.0,
    )


def apply_evidence_engine(
    results,
    query: str,
):

    for item in results:

        payload = item[
            "payload"
        ]

        role = classify_role(
            payload,
            query,
        )

        item[
            "evidence_role"
        ] = role

        item[
            "evidence_score"
        ] = role_score(
            role
        )

    return results


def evidence_gate(
    results,
):

    valid = [
        x
        for x in results
        if x.get(
            "evidence_role"
        )
        in [
            "primary",
            "direct",
            "supporting",
        ]
    ]

    if valid:

        return valid

    # Safety fallback
    fallback = results[:2]

    for item in fallback:

        item[
            "evidence_role"
        ] = "fallback"

        item[
            "fallback_reason"
        ] = "no_valid_legal_evidence"

    return fallback