# -*- coding: utf-8 -*-

"""
RAG V5.9 / V6.0-1 Debug Suite

测试：

1. config.py
2. embedding.py
3. vector_store.py
4. Qdrant
5. retriever.py
6. relevance_ranker.py
7. rag.py
8. Ollama

测试目标：

用户问题：

公司连续签订三次固定期限劳动合同后，
是否必须签订无固定期限劳动合同？

重点检查：

第十四条
第三十九条
第四十条
第八十二条

以及：

BGE-M3
Qdrant
法律引用扩展
Relevance Ranker
Ollama
"""

import sys
import traceback
from pathlib import Path


# ============================================================
# 项目路径
# ============================================================

ROOT_DIR = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT_DIR / "src"

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


# ============================================================
# 测试问题
# ============================================================

QUESTION = (
    "公司连续签订三次固定期限劳动合同后，"
    "是否必须签订无固定期限劳动合同？"
)


# ============================================================
# 测试结果
# ============================================================

TEST_RESULTS = []


def record_result(
    name,
    success,
    message="",
):
    TEST_RESULTS.append(
        {
            "name": name,
            "success": success,
            "message": message,
        }
    )


def print_header(title):

    print()
    print("=" * 70)
    print(title)
    print("=" * 70)


def print_success(message):

    print(f"✅ {message}")


def print_warning(message):

    print(f"⚠️ {message}")


def print_error(message):

    print(f"❌ {message}")


# ============================================================
# 1. 测试 config.py
# ============================================================

def test_config():

    print_header("TEST 1 - config.py")

    try:

        from src.config import (
            QDRANT_URL,
            COLLECTION_NAME,
            EMBEDDING_MODEL,
            VECTOR_SIZE,
        )

        print(
            f"QDRANT_URL：{QDRANT_URL}"
        )

        print(
            f"COLLECTION_NAME：{COLLECTION_NAME}"
        )

        print(
            f"EMBEDDING_MODEL：{EMBEDDING_MODEL}"
        )

        print(
            f"VECTOR_SIZE：{VECTOR_SIZE}"
        )

        if not QDRANT_URL:
            raise ValueError(
                "QDRANT_URL 为空"
            )

        if not COLLECTION_NAME:
            raise ValueError(
                "COLLECTION_NAME 为空"
            )

        if not EMBEDDING_MODEL:
            raise ValueError(
                "EMBEDDING_MODEL 为空"
            )

        if int(VECTOR_SIZE) != 1024:

            print_warning(
                "VECTOR_SIZE 不是 1024，"
                "请确认是否与 BGE-M3/Qdrant 一致"
            )

        print_success(
            "config.py 配置加载成功"
        )

        record_result(
            "config.py",
            True,
        )

        return True

    except Exception as exc:

        print_error(
            f"config.py 测试失败：{exc}"
        )

        traceback.print_exc()

        record_result(
            "config.py",
            False,
            str(exc),
        )

        return False


# ============================================================
# 2. 测试 embedding.py
# ============================================================

def test_embedding():

    print_header("TEST 2 - embedding.py / BGE-M3")

    try:

        from src.embedding import embed_text

        text = (
            "公司连续签订三次固定期限劳动合同后，"
            "是否必须签订无固定期限劳动合同？"
        )

        vector = embed_text(
            text
        )

        print(
            f"向量维度：{len(vector)}"
        )

        if not vector:
            raise ValueError(
                "Embedding 返回空向量"
            )

        if len(vector) != 1024:

            print_warning(
                f"Embedding 维度为 "
                f"{len(vector)}，"
                f"不是预期的 1024"
            )

        else:

            print_success(
                "BGE-M3 向量维度正确：1024"
            )

        print(
            f"前 5 个值："
            f"{vector[:5]}"
        )

        record_result(
            "embedding.py",
            True,
        )

        return True

    except Exception as exc:

        print_error(
            f"embedding.py 测试失败：{exc}"
        )

        traceback.print_exc()

        record_result(
            "embedding.py",
            False,
            str(exc),
        )

        return False


# ============================================================
# 3. 测试 Qdrant
# ============================================================

def test_qdrant():

    print_header("TEST 3 - Qdrant")

    try:

        from src.vector_store import (
            get_client,
            collection_exists,
            get_collection_info,
            count_points,
        )

        client = get_client()

        print(
            "Qdrant Client 创建成功"
        )

        collections = (
            client.get_collections()
        )

        print(
            "Qdrant Collections："
        )

        for collection in (
            collections.collections
        ):

            print(
                f"  - {collection.name}"
            )

        exists = collection_exists()

        if not exists:

            raise RuntimeError(
                "目标 Collection 不存在"
            )

        print_success(
            "目标 Collection 存在"
        )

        info = get_collection_info()

        count = count_points()

        print(
            f"Collection："
            f"{info}"
        )

        print(
            f"向量数量：{count}"
        )

        if count == 0:

            print_error(
                "Qdrant Collection 当前没有向量"
            )

            print(
                "请先执行法律文档入库。"
            )

            record_result(
                "Qdrant",
                False,
                "Collection 为空",
            )

            return False

        print_success(
            f"Qdrant 中存在 {count} 个向量"
        )

        record_result(
            "Qdrant",
            True,
        )

        return True

    except Exception as exc:

        print_error(
            f"Qdrant 测试失败：{exc}"
        )

        traceback.print_exc()

        record_result(
            "Qdrant",
            False,
            str(exc),
        )

        return False


# ============================================================
# 4. 测试 vector_store 精确查询
# ============================================================

def test_exact_article():

    print_header(
        "TEST 4 - Qdrant 法律条文精确查询"
    )

    try:

        from src.vector_store import (
            get_article_exact,
        )

        test_articles = [
            (
                "中华人民共和国劳动合同法",
                "第十四条",
            ),
            (
                "中华人民共和国劳动合同法",
                "第三十九条",
            ),
            (
                "中华人民共和国劳动合同法",
                "第四十条",
            ),
            (
                "中华人民共和国劳动合同法",
                "第八十二条",
            ),
        ]

        success_count = 0

        for law_name, article_number in (
            test_articles
        ):

            print()
            print(
                f"查询："
                f"{law_name} "
                f"{article_number}"
            )

            result = get_article_exact(
                law_name,
                article_number,
            )

            if result is None:

                print_error(
                    f"找不到：{article_number}"
                )

                continue

            payload = (
                result.get(
                    "payload",
                    {},
                )
                or {}
            )

            article_text = (
                payload.get(
                    "article_text",
                    payload.get(
                        "text",
                        "",
                    ),
                )
            )

            print_success(
                f"找到：{article_number}"
            )

            print(
                f"文本长度："
                f"{len(article_text)}"
            )

            success_count += 1

        print()
        print(
            f"精确查询成功："
            f"{success_count}/"
            f"{len(test_articles)}"
        )

        if success_count != len(
            test_articles
        ):

            record_result(
                "Qdrant 精确查询",
                False,
                (
                    f"{success_count}/"
                    f"{len(test_articles)}"
                ),
            )

            return False

        record_result(
            "Qdrant 精确查询",
            True,
        )

        return True

    except Exception as exc:

        print_error(
            f"精确查询测试失败：{exc}"
        )

        traceback.print_exc()

        record_result(
            "Qdrant 精确查询",
            False,
            str(exc),
        )

        return False


# ============================================================
# 5. 测试 Retriever
# ============================================================

def test_retriever():

    print_header(
        "TEST 5 - V5.9 Retriever"
    )

    try:

        from src.retriever import (
            semantic_recall,
            expand_legal_references,
            retrieve,
        )

        print()
        print(
            "执行 semantic_recall..."
        )

        semantic_results = (
            semantic_recall(
                QUESTION,
                top_k=5,
            )
        )

        print()
        print(
            f"语义召回数量："
            f"{len(semantic_results)}"
        )

        if not semantic_results:

            raise RuntimeError(
                "Retriever 没有召回任何结果"
            )

        for index, item in enumerate(
            semantic_results,
            start=1,
        ):

            print()
            print(
                f"【召回 {index}】"
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
                f"Score："
                f"{item.get('score')}"
            )

        expanded = (
            expand_legal_references(
                semantic_results
            )
        )

        print()
        print(
            f"引用扩展后数量："
            f"{len(expanded)}"
        )

        article_numbers = {
            (
                item.get(
                    "article_number"
                )
            )
            for item in expanded
        }

        print()
        print(
            "扩展后的法条："
        )

        for article_number in sorted(
            article_numbers
        ):

            print(
                f"  - {article_number}"
            )

        expected = {
            "第十四条",
            "第三十九条",
            "第四十条",
        }

        missing = (
            expected
            - article_numbers
        )

        if missing:

            print_warning(
                "以下关键法条没有进入引用扩展："
            )

            for item in missing:
                print(
                    f"  - {item}"
                )

        else:

            print_success(
                "第十四条、第三十九条、"
                "第四十条均存在"
            )

        print()
        print(
            "执行完整 retrieve..."
        )

        final_results = retrieve(
            query=QUESTION,
            top_k=5,
            score_threshold=0.55,
        )

        print()
        print(
            f"Retriever 最终返回："
            f"{len(final_results)} 条"
        )

        if not final_results:

            raise RuntimeError(
                "retrieve() 最终没有返回法律依据"
            )

        print()
        print(
            "Retriever 最终结果："
        )

        for index, item in enumerate(
            final_results,
            start=1,
        ):

            print(
                f"{index}. "
                f"{item.get('law_name')} "
                f"{item.get('article_number')} "
                f""
                f"score="
                f"{item.get('score')}"
            )

        record_result(
            "Retriever",
            True,
        )

        return final_results

    except Exception as exc:

        print_error(
            f"Retriever 测试失败：{exc}"
        )

        traceback.print_exc()

        record_result(
            "Retriever",
            False,
            str(exc),
        )

        return None


# ============================================================
# 6. 测试 Relevance Ranker
# ============================================================

def test_ranker(laws):

    print_header(
        "TEST 6 - V6.0-1 Relevance Ranker"
    )

    if not laws:

        print_error(
            "没有 Retriever 数据，"
            "跳过 Ranker"
        )

        record_result(
            "Relevance Ranker",
            False,
            "没有输入数据",
        )

        return None

    try:

        from src.relevance_ranker import (
            rank_laws,
            select_context_laws,
        )

        ranked = rank_laws(
            question=QUESTION,
            laws=laws,
            max_results=20,
            min_score=0.25,
            keep_low_relevance=True,
        )

        print()
        print(
            f"Ranker 返回："
            f"{len(ranked)} 条"
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
                f"BGE-M3："
                f"{item.get('original_score')}"
            )

            print(
                f"关键词："
                f"{item.get('keyword_score')}"
            )

            print(
                f"法条优先级："
                f"{item.get('article_priority')}"
            )

            print(
                f"引用关系："
                f"{item.get('reference_score')}"
            )

            print(
                f"理由："
                f"{item.get('reason')}"
            )

        print()
        print(
            "=" * 70
        )

        selected = select_context_laws(
            question=QUESTION,
            laws=laws,
        )

        print(
            "Context 选取结果："
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

        required_articles = {
            "第十四条",
            "第三十九条",
            "第四十条",
        }

        selected_articles = {
            item.get(
                "article_number"
            )
            for item in selected
        }

        missing = (
            required_articles
            - selected_articles
        )

        if missing:

            print_warning(
                "Context 中缺少关键法条："
            )

            for item in missing:
                print(
                    f"  - {item}"
                )

        else:

            print_success(
                "核心法律条件法条全部进入 Context"
            )

        record_result(
            "Relevance Ranker",
            True,
        )

        return selected

    except Exception as exc:

        print_error(
            f"Ranker 测试失败：{exc}"
        )

        traceback.print_exc()

        record_result(
            "Relevance Ranker",
            False,
            str(exc),
        )

        return None


# ============================================================
# 7. 测试 Context
# ============================================================

def test_context(laws):

    print_header(
        "TEST 7 - Context 内容检查"
    )

    if not laws:

        print_error(
            "没有法律依据"
        )

        record_result(
            "Context",
            False,
            "没有法律依据",
        )

        return False

    try:

        from src.relevance_ranker import (
            select_context_laws,
        )

        selected = (
            select_context_laws(
                QUESTION,
                laws,
            )
        )

        if not selected:

            raise RuntimeError(
                "Context 为空"
            )

        print(
            f"Context 法条数量："
            f"{len(selected)}"
        )

        required_articles = [
            "第十四条",
            "第三十九条",
            "第四十条",
        ]

        for article_number in (
            required_articles
        ):

            found = any(
                item.get(
                    "article_number"
                ) == article_number
                for item in selected
            )

            if found:

                print_success(
                    f"Context 包含："
                    f"{article_number}"
                )

            else:

                print_warning(
                    f"Context 缺少："
                    f"{article_number}"
                )

        context_parts = []

        for index, item in enumerate(
            selected,
            start=1,
        ):

            context_parts.append(
                (
                    f"【法律依据 {index}】\n"
                    f"法律名称："
                    f"{item.get('law_name')}\n"
                    f"法条："
                    f"{item.get('article_number')}\n"
                    f"分类："
                    f"{item.get('category')}\n"
                    f"法条内容：\n"
                    f"{item.get('article_text')}"
                )
            )

        context = "\n\n".join(
            context_parts
        )

        print()
        print(
            "=" * 70
        )

        print(
            f"Context 字符数："
            f"{len(context)}"
        )

        print()
        print(
            context
        )

        record_result(
            "Context",
            True,
        )

        return context

    except Exception as exc:

        print_error(
            f"Context 测试失败：{exc}"
        )

        traceback.print_exc()

        record_result(
            "Context",
            False,
            str(exc),
        )

        return False


# ============================================================
# 8. 测试 Ollama
# ============================================================

def test_ollama():

    print_header(
        "TEST 8 - Ollama"
    )

    try:

        import requests

        url = (
            "http://127.0.0.1:11434/api/tags"
        )

        response = requests.get(
            url,
            timeout=10,
        )

        response.raise_for_status()

        data = response.json()

        models = data.get(
            "models",
            [],
        )

        print(
            f"Ollama 模型数量："
            f"{len(models)}"
        )

        found_qwen = False

        for model in models:

            name = model.get(
                "name",
                "",
            )

            print(
                f"  - {name}"
            )

            if name == "qwen3:14b":

                found_qwen = True

        if found_qwen:

            print_success(
                "找到 qwen3:14b"
            )

        else:

            print_warning(
                "没有找到 qwen3:14b"
            )

            print(
                "请执行："
            )

            print(
                "ollama list"
            )

        record_result(
            "Ollama",
            True,
        )

        return True

    except Exception as exc:

        print_error(
            f"Ollama 测试失败：{exc}"
        )

        traceback.print_exc()

        record_result(
            "Ollama",
            False,
            str(exc),
        )

        return False


# ============================================================
# 9. 测试 RAG Context 构建
# ============================================================

def test_rag_context():

    print_header(
        "TEST 9 - RAG Context Integration"
    )

    try:

        from src.retriever import (
            build_context,
        )

        context = build_context(
            question=QUESTION,
            top_k=5,
            score_threshold=0.55,
        )

        if not context:

            raise RuntimeError(
                "build_context() 返回空"
            )

        print()
        print(
            f"Retriever build_context "
            f"字符数：{len(context)}"
        )

        if (
            "第十四条"
            not in context
        ):

            print_warning(
                "Context 中没有第十四条"
            )

        else:

            print_success(
                "Context 中存在第十四条"
            )

        record_result(
            "RAG Context",
            True,
        )

        return context

    except Exception as exc:

        print_error(
            f"RAG Context 测试失败：{exc}"
        )

        traceback.print_exc()

        record_result(
            "RAG Context",
            False,
            str(exc),
        )

        return None


# ============================================================
# 10. 最终测试总结
# ============================================================

def print_summary():

    print_header(
        "V5.9 / V6.0-1 Debug Suite - 测试总结"
    )

    total = len(
        TEST_RESULTS
    )

    passed = sum(
        1
        for item in TEST_RESULTS
        if item["success"]
    )

    failed = total - passed

    print()
    print(
        f"总测试数：{total}"
    )

    print(
        f"通过：{passed}"
    )

    print(
        f"失败：{failed}"
    )

    print()

    for item in TEST_RESULTS:

        if item["success"]:

            print(
                f"✅ {item['name']}"
            )

        else:

            print(
                f"❌ {item['name']}"
                f"：{item['message']}"
            )

    print()

    print(
        "=" * 70
    )

    if failed == 0:

        print(
            "🎉 V5.9 / V6.0-1 基础 Debug 全部通过"
        )

    else:

        print(
            "⚠️ Debug 存在问题，"
            "暂时不要进入 V6.0-2"
        )

    print(
        "=" * 70
    )


# ============================================================
# Main
# ============================================================

def main():

    print()
    print("=" * 70)
    print(
        "RAG V5.9 / V6.0-1 Debug Suite"
    )
    print("=" * 70)

    print()
    print(
        "测试问题："
    )

    print(
        QUESTION
    )

    print()
    print(
        f"项目目录："
        f"{ROOT_DIR}"
    )

    print()
    print(
        "=" * 70
    )

    # --------------------------------------------------------
    # 基础环境
    # --------------------------------------------------------

    test_config()

    test_embedding()

    qdrant_ok = test_qdrant()

    if not qdrant_ok:

        print()
        print_error(
            "Qdrant 测试失败。"
        )

        print(
            "后续 Retriever / Ranker 测试可能没有意义。"
        )

        print_summary()

        return

    # --------------------------------------------------------
    # 精确查询
    # --------------------------------------------------------

    test_exact_article()

    # --------------------------------------------------------
    # Retriever
    # --------------------------------------------------------

    laws = test_retriever()

    if not laws:

        print()
        print_error(
            "Retriever 测试失败。"
        )

        print_summary()

        return

    # --------------------------------------------------------
    # Ranker
    # --------------------------------------------------------

    selected = test_ranker(
        laws
    )

    # --------------------------------------------------------
    # Context
    # --------------------------------------------------------

    test_context(
        laws
    )

    # --------------------------------------------------------
    # Ollama
    # --------------------------------------------------------

    test_ollama()

    # --------------------------------------------------------
    # RAG Context
    # --------------------------------------------------------

    test_rag_context()

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    print_summary()


if __name__ == "__main__":

    main()