"""
V6.1 Legal Context Builder

职责：
1. 将 Retriever / Structured Rules 转换为可展示的法律依据文本。
2. 构建 Structured Context。
3. 本模块只负责 Context 层，不负责 Legal Decision 判定。
4. 不重新推断法律条件，不修改 DecisionResult。
5. Canonical Rule 定义仍由 legal_rule_definition.py /
   legal_rule_registry.py 统一提供。

本文件中的核心函数从 legal_decision_adapter.py 原样迁移，
迁移目标是职责分层，不改变既有业务逻辑。
"""

from typing import Any, Dict, List

from src.retriever import build_context

from src.legal_common import (
    ensure_list,
    get_field,
    get_first_field,
    get_rule_value,
    normalize_text,
)

from src.legal_rule_builder import (
    build_rules_from_articles,
    prioritize_legal_rules,
)

def format_rules_for_display(
    rules: List[Dict[str, Any]],
) -> str:
    # 将 Rules 转换为可阅读法律依据。

    if not rules:
        return "当前没有结构化法律规则。"

    lines = []

    seen = set()

    index = 1

    for rule in rules:

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

        summary = normalize_text(
            rule.get(
                "rule_summary",
                "",
            )
        )

        if law_name and article_number:

            title = (
                f"《{law_name}》"
                f"{article_number}"
            )

        elif law_name:

            title = f"《{law_name}》"

        else:

            title = article_number

        if not title:
            continue

        priority = normalize_text(
            rule.get("rule_priority", "")
        )

        if summary:
            prefix = "[核心依据] " if priority == "CORE" else "[相关依据] "
            text = (
                f"{prefix}{title}："
                f"{summary}"
            )
        else:
            text = title

        if text in seen:
            continue

        seen.add(text)

        lines.append(
            f"{index}. {text}"
        )

        index += 1

    if not lines:
        return "当前没有结构化法律规则。"

    return "\n".join(lines)

def build_structured_context(
    question: str,
    top_k: int = 5,
    score_threshold: float = 0.55,
) -> Dict[str, Any]:

    print()
    print("=" * 70)
    print("Step 1 / Retriever")
    print("=" * 70)

    articles = build_context(
        question=question,
        top_k=top_k,
        score_threshold=score_threshold,
        return_articles=True,
    )

    if articles is None:
        articles = []

    if isinstance(articles, str):

        print()
        print(
            "⚠️ Retriever 返回的是字符串，"
            "无法构建 Structured Articles。"
        )

        return {
            "articles": [],
            "rules": [],
            "context": articles,
        }

    rules = build_rules_from_articles(
        articles
    )

    # V6.0-13：不删除 Retriever 结果，只按问题相关性排序。
    # 核心法条优先展示，相关法条继续保留供 Decision Engine 使用。
    rules = prioritize_legal_rules(
        question=question,
        rules=rules,
    )

    context = format_rules_for_display(
        rules
    )

    print()
    print("✅ Retriever 完成")

    print(
        f"Structured Articles：{len(articles)}"
    )

    print(
        f"Normalized Rules：{len(rules)}"
    )

    print(
        f"Context 字符数：{len(context)}"
    )

    return {
        "articles": articles,
        "rules": rules,
        "context": context,
    }
