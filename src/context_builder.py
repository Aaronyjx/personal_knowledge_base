# -*- coding: utf-8 -*-

"""
RAG V5.7 Context Builder
========================

负责：

1. 调用 Retriever
2. 构建法律 Context
3. 区分：
   - BGE-M3 语义召回
   - 法律引用自动补充
4. 不再对引用补充结果进行 Score 过滤
5. 为 LLM 提供结构化法律依据
"""

from typing import List, Dict

from .retriever import retrieve


def build_context(
    question: str,
    top_k: int = 5,
    score_threshold: float = 0.55,
) -> str:

    print()
    print("=" * 70)

    print(
        "RAG V5.7 - 构建法律 Context"
    )

    print()
    print(
        f"问题：{question}"
    )

    print(
        f"Top K：{top_k}"
    )

    print(
        f"Score Threshold：{score_threshold}"
    )

    print("=" * 70)

    results = retrieve(
        question,
        top_k=top_k,
        score_threshold=score_threshold,
    )

    print()
    print("=" * 70)
    print("V5.7 Context 构建完成")
    print("=" * 70)

    print(
        f"法律依据数量：{len(results)}"
    )

    # ========================================================
    # 没有结果
    # ========================================================

    if not results:

        context = (
            "知识库中没有找到与问题直接相关的法律依据。"
        )

        print(
            f"Context 字符数：{len(context)}"
        )

        return context

    blocks = []

    for index, result in enumerate(
        results,
        start=1,
    ):

        law_name = result.get(
            "law_name",
            "",
        )

        article_number = result.get(
            "article_number",
            "",
        )

        article_text = result.get(
            "article_text",
            "",
        )

        source = result.get(
            "source",
            "",
        )

        score = result.get(
            "bge_score",
            0.0,
        )

        source_type = result.get(
            "source_type",
            "BGE-M3语义召回",
        )

        referenced_from = result.get(
            "referenced_from",
            None,
        )

        # ====================================================
        # 来源描述
        # ====================================================

        if source_type == "法律引用自动补充":

            source_desc = (
                "法律引用自动补充"
            )

            reference_desc = ""

            if referenced_from:

                reference_desc = (
                    f"引用自：{referenced_from}"
                )

        else:

            source_desc = (
                "BGE-M3语义召回"
            )

            reference_desc = (
                f"相关度：{score:.4f}"
            )

        # ====================================================
        # Context Block
        # ====================================================

        block = []

        block.append(
            f"【法律依据 {index}】"
        )

        block.append(
            f"法律名称：《{law_name}》"
        )

        block.append(
            f"法条：{article_number}"
        )

        block.append(
            f"来源：{source_desc}"
        )

        if reference_desc:

            block.append(
                reference_desc
            )

        if source:

            block.append(
                f"原始文件：{source}"
            )

        block.append(
            "法条内容："
        )

        block.append(
            article_text.strip()
        )

        blocks.append(
            "\n".join(block)
        )

    context = "\n\n".join(
        blocks
    )

    print(
        f"Context 字符数：{len(context)}"
    )

    return context