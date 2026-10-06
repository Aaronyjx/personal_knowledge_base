from __future__ import annotations

from typing import Any, Dict, Optional

from src.legal_rule_registry import find_rule_by_article


def select_rule_from_article(
    article: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """
    根据 Retriever Candidate Article 选择 Canonical Rule。

    Rule Selection 的唯一职责：

        Candidate Article
            ↓
        Article Identity
            ↓
        Canonical Rule Registry
            ↓
        Canonical Rule / None

    Article Identity：

        law_name + article_number

    本模块不负责：

    - Retriever Ranking
    - LegalFacts
    - Condition Matching
    - Decision
    - Ollama
    - 法律结论

    规则：

    1. 缺少 law_name → None
    2. 缺少 article_number → None
    3. Article Identity 未注册 → None
    4. 已注册 → 返回 Canonical Rule
    """

    if not isinstance(article, dict):
        return None

    law_name = article.get("law_name")
    article_number = article.get("article_number")

    if not law_name or not article_number:
        return None

    return find_rule_by_article(
        law_name=law_name,
        article_number=article_number,
    )


def select_rule_from_articles(
    articles: list[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """
    从 Retriever Candidate Articles 中选择第一个
    能映射到 Canonical Registry 的 Rule。

    注意：

    本函数不进行 Retriever Ranking。

    它只按照传入 Candidate Articles 的顺序，
    查找第一个存在于 Canonical Registry 的 Rule。

    Ranking 仍属于 Retriever 职责。
    """

    for article in articles:

        rule = select_rule_from_article(article)

        if rule is not None:
            return rule

    return None
