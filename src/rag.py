# -*- coding: utf-8 -*-

# ============================================================
# RAG V6.1
# Legal RAG Pipeline Entry Point
#
# ============================================================
#
# 本文件职责
# ============================================================
#
# 本文件仅负责：
#
# 1. Legal RAG Pipeline CLI 入口
# 2. Demo Question
# 3. 完整 Pipeline 测试入口
# 4. Component Test 入口
# 5. 自定义法律问题交互入口
#
# 核心业务逻辑已经拆分到独立模块：
#
#     Retriever
#         ↓
#     Structured Context
#         ↓
#     Legal Decision Engine
#         ↓
#     DecisionResult
#         ↓
#     Decision Adapter
#         ↓
#     Legal Answer Builder
#         ↓
#     Legal Prompt
#         ↓
#     Legal LLM / Ollama
#         ↓
#     Answer Sanitizer
#         ↓
#     Final Validation
#         ↓
#     Final Legal Answer
#
# ============================================================
#
# V6.1 第一阶段
# ============================================================
#
# 事实提取层已经完成模块化拆分：
#
#     legal_fact_models.py
#         ↓
#     legal_fact_extractor.py
#         ├── legal_fact_contract.py
#         ├── legal_fact_renewal.py
#         └── legal_fact_exclusion.py
#
# 同时：
#
#     legal_common.py
#
# 提供公共文本处理工具。
#
# ============================================================
#
# 核心架构原则
# ============================================================
#
# 1. Retriever 负责寻找法律依据。
#
# 2. Legal Decision Engine 负责结构化法律判断。
#
# 3. Decision Adapter 负责接口适配。
#
# 4. Legal Answer Builder 负责构建结构化回答。
#
# 5. Legal Prompt 负责组织 LLM 输入。
#
# 6. Ollama / Legal LLM 只负责自然语言表达。
#
# 7. Ollama 不允许重新判断法律。
#
# 8. 用户事实必须保持原意。
#
# 9. 法律规则和用户事实必须严格区分。
#
# 10. CONDITIONAL 必须保持条件性。
#
# 11. UNKNOWN 条件不得自行补充。
#
# 12. Final Answer 必须经过 Validation。
#
# 13. Legal Decision Engine 是 ConditionResult 的唯一判断来源。
#
# 14. RAG 入口层不得重新生成、修改或补充法律条件。
#
# ============================================================
#
# V6.0-27 Decision Engine Boundary
# ============================================================
#
# Legal Decision Engine 已经负责完整生成 ConditionResult。
#
# RAG 入口层不得：
#
#     - 补充 ConditionResult
#     - 删除 ConditionResult
#     - 修改 ConditionResult
#     - 根据自然语言答案重新判断 ConditionResult
#
# 特别是：
#
#     "存在后续订立的劳动合同"
#
# 已经由 Legal Decision Engine 正式产生。
#
# RAG 入口层不再使用旧版兼容函数追加该条件。
#
# ============================================================
#
# V6.1 第二阶段
# ============================================================
#
# 本阶段将 rag.py 保持为纯入口层。
#
# 已经迁移到独立模块的业务逻辑不再在本文件保留
# 空壳函数或重复实现。
#
# ============================================================
#
# 运行方式：
#
#     cd ~/Projects/Jupyter/personal_knowledge_base
#
#     python -m src.rag
#
# ============================================================


from src.legal_llm import (
    OLLAMA_MODEL,
)

from src.legal_pipeline import (
    answer_question,
)

from src.legal_component_test import (
    component_test,
)


# ============================================================
# 常量
# ============================================================

RAG_VERSION = "V6.1"


# ============================================================
# Demo Question
# ============================================================

def create_demo_question() -> str:
    """
    创建默认法律问题。

    本函数只负责提供 CLI / Pipeline 测试问题，
    不参与任何法律事实提取或法律判断。
    """

    return (
        "公司连续签订三次固定期限劳动合同后，"
        "是否必须签订无固定期限劳动合同？"
    )


# ============================================================
# Pipeline Test
# ============================================================

def run_pipeline_test():
    """
    执行完整 Legal RAG Pipeline。

    本函数只负责调用 Pipeline 入口，
    不在 CLI 层执行法律判断。
    """

    question = create_demo_question()

    return answer_question(
        question=question,
        top_k=5,
        score_threshold=0.55,
        model=OLLAMA_MODEL,
    )


# ============================================================
# Interactive Question
# ============================================================

def interactive_question():
    """
    接收用户自定义法律问题并执行完整 Pipeline。
    """

    print()
    print("=" * 70)
    print(
        f"RAG {RAG_VERSION} Interactive Question"
    )
    print("=" * 70)

    print()
    print(
        "请输入法律问题："
    )

    try:

        question = input(
            "> "
        ).strip()

    except EOFError:

        question = ""

    if not question:

        print()
        print(
            "⚠️ 未输入问题。"
        )

        return ""

    return answer_question(
        question=question,
        top_k=5,
        score_threshold=0.55,
        model=OLLAMA_MODEL,
    )


# ============================================================
# Main Menu
# ============================================================

def main():
    """
    Legal RAG CLI 主入口。

    这里只负责选择测试入口，
    不负责任何法律业务逻辑。
    """

    print()
    print("=" * 70)
    print(
        f"RAG {RAG_VERSION}"
    )
    print("=" * 70)

    print()
    print(
        "Legal RAG Pipeline"
    )

    print()
    print(
        "请选择测试："
    )

    print()
    print(
        "1. 完整 Pipeline 测试"
    )

    print(
        "2. Component Test"
    )

    print(
        "3. 输入自定义法律问题"
    )

    print()

    try:

        choice = input(
            "请输入 1、2 或 3："
        ).strip()

    except EOFError:

        choice = "1"

    # --------------------------------------------------------
    # 完整 Pipeline
    # --------------------------------------------------------

    if choice == "1":

        run_pipeline_test()

        return

    # --------------------------------------------------------
    # Component Test
    # --------------------------------------------------------

    if choice == "2":

        component_test()

        return

    # --------------------------------------------------------
    # 自定义问题
    # --------------------------------------------------------

    if choice == "3":

        interactive_question()

        return

    # --------------------------------------------------------
    # 无效输入
    # --------------------------------------------------------

    print()
    print(
        "⚠️ 无效选择。"
    )

    print(
        "默认执行完整 Pipeline 测试。"
    )

    run_pipeline_test()


# ============================================================
# Module Entry
# ============================================================

if __name__ == "__main__":

    main()