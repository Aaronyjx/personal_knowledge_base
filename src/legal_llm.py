# -*- coding: utf-8 -*-

"""
RAG V6.0-27
Legal LLM Layer

============================================================
功能
============================================================

Legal Decision Engine
      ↓
DecisionResult
      ↓
Legal Answer Builder
      ↓
Legal Prompt Builder
      ↓
Legal LLM
      ↓
Ollama
      ↓
LLM Output Cleaning
      ↓
Final Validation
      ↓
Final Legal Answer

============================================================
V6.0-27 模块化重构
============================================================

本文件从原 rag.py 中拆分出来。

本模块只负责：

    1. Ollama HTTP 调用
    2. Ollama Response 提取
    3. Ollama Runtime 统一入口
    4. LLM 输出基础结构检查

Answer Sanitization 已独立拆分至：

    src/legal_answer_sanitizer.py

该模块负责：

    1. Qwen Thinking 内容清理
    2. Markdown 标题清理
    3. 连续空行清理
    4. 正式 Section 清理
    5. 重复 Section 清理

Common Utils 已独立拆分至：

    src/legal_common_utils.py

本模块不负责：

    1. Legal Decision Engine
    2. 法律条件判断
    3. 用户事实提取
    4. 法律依据选择
    5. 法律依据验证
    6. 最终法律 Validation
    7. Deterministic Conclusion
    8. Deterministic Legal Basis
    9. Deterministic Notices
    10. Prompt 构建
    11. Answer Sanitization
    12. 通用文本规范化

============================================================
重要架构原则
============================================================

1. Legal Decision Engine 是唯一法律条件判定来源。

2. Ollama 只能解释 Engine 已经形成的 DecisionResult。

3. Ollama 不得重新进行法律条件判断。

4. Ollama 不得新增用户事实。

5. Ollama 不得把 UNKNOWN 推断为 SATISFIED。

6. Ollama 不得把 UNKNOWN 推断为 NOT_SATISFIED。

7. Ollama 不得把 SATISFIED 改写成 UNKNOWN。

8. Ollama 不得把 NOT_SATISFIED 改写成 UNKNOWN。

9. EXCLUSION / EXCEPTION 中的 NOT_SATISFIED
   表示该排除条件 / 例外条件已经触发。

10. 最终法律结论必须保持 Engine Decision 不变。

11. 法律 Prompt 不属于本模块。

12. 法律 Validation 不属于本模块。

13. Answer Sanitization 不属于本模块。

14. 通用文本工具函数不属于本模块。

============================================================
重构后的职责边界
============================================================

src/legal_llm.py
    ↓
    Ollama Runtime

src/legal_prompt.py
    ↓
    Ollama Prompt Builder

src/legal_answer_sanitizer.py
    ↓
    LLM Answer Sanitization

src/legal_validation.py
    ↓
    Final Validation

src/legal_citation_validator.py
    ↓
    Legal Citation Validation

src/legal_answer_builder.py
    ↓
    Deterministic Structured Answer

src/legal_decision_engine.py
    ↓
    Legal Decision

src/legal_common_utils.py
    ↓
    Common Text / Field Utilities

============================================================
V6.0-27 设计目标
============================================================

原来的 rag.py 中：

    build_ollama_prompt()
    call_ollama()
    clean_answer()
    remove_duplicate_sections()

全部混在一个巨大文件中。

现在拆分为：

    legal_prompt.py
        ↓
        负责 Prompt

    legal_llm.py
        ↓
        负责 Ollama Runtime

    legal_answer_sanitizer.py
        ↓
        负责 LLM Answer Sanitization

这样可以保证：

    Prompt 修改
        不需要修改 LLM Runtime

    Ollama 模型修改
        不需要修改 Prompt

    Sanitization 修改
        不需要修改 LLM Runtime

    Validation 修改
        不需要修改 LLM Runtime

============================================================
兼容原则
============================================================

call_ollama() 保留原来的公开接口。

因此原来的：

    answer = call_ollama(
        prompt=prompt,
        model=model,
    )

仍然可以继续使用。

============================================================
版本
============================================================

RAG V6.0-27
"""


from __future__ import annotations


# ============================================================
# 第三方库
# ============================================================

import requests


# ============================================================
# 本地模块
# ============================================================
#
# Answer Sanitization 已经独立拆分。
#
# legal_llm.py 不重新实现：
#
#     clean_answer()
#     remove_duplicate_sections()
#
# 只负责调用 Sanitizer。
# ============================================================

from src.legal_answer_sanitizer import (
    clean_answer,
)


# ============================================================
# Ollama Configuration
# ============================================================
#
# 当前项目使用本地 Ollama。
#
# 原 rag.py 中：
#
#     OLLAMA_URL
#     OLLAMA_MODEL
#
# 如果后续统一迁移到 config.py，
# 可以再将这里改为：
#
#     from src.config import OLLAMA_URL, OLLAMA_MODEL
#
# 当前阶段先保持模块独立，
# 避免第一次拆分同时修改过多依赖。
# ============================================================

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"

OLLAMA_MODEL = "qwen3:14b"


# ============================================================
# RAG Version
# ============================================================

RAG_VERSION = "V6.0-27"


# ============================================================
# Final Answer Sections
# ============================================================
#
# Ollama 最终回答使用统一的四段式结构：
#
#     【结论】
#     【法律依据】
#     【法律分析】
#     【需要注意】
#
# 注意：
#
# 本模块只负责识别这些 Section 是否按照要求出现。
#
# 本模块不负责判断 Section 内容是否正确。
#
# 内容正确性属于：
#
#     Legal Decision Engine
#     Answer Builder
#     Legal Validation
#     Citation Validator
#
# ============================================================

REQUIRED_SECTIONS = [
    "【结论】",
    "【法律依据】",
    "【法律分析】",
    "【需要注意】",
]


# ============================================================
# Ollama HTTP Runtime
# ============================================================

def call_ollama(
    prompt: str,
    model: str = OLLAMA_MODEL,
) -> str:
    """
    调用本地 Ollama API。

    ========================================================
    V6.0-13
    ========================================================

    Step 4 日志由 answer_question() 统一输出。

    call_ollama() 只负责 HTTP 调用，
    避免重复打印 Step 4。

    ========================================================
    调用流程
    ========================================================

        Prompt
          ↓
        requests.post()
          ↓
        Ollama
          ↓
        JSON Response
          ↓
        response
          ↓
        clean_answer()
          ↓
        Answer

    ========================================================
    参数
    ========================================================

    prompt:
        已经由 legal_prompt.py 构建完成的 Prompt。

    model:
        Ollama 模型名称。

        默认：

            qwen3:14b

    ========================================================
    返回
    ========================================================

    返回经过：

        legal_answer_sanitizer.clean_answer()

    清理后的字符串。

    ========================================================
    重要原则
    ========================================================

    本函数不负责：

        - 法律推理
        - Decision 判断
        - 条件判断
        - 用户事实判断
        - 法律依据判断
        - 法律结论生成
        - 法律 Validation

    这些内容均属于其他模块职责。
    """

    # ========================================================
    # 参数基础检查
    # ========================================================

    if not isinstance(
        prompt,
        str,
    ):
        raise TypeError(
            "prompt 必须是 str。"
        )

    if not prompt.strip():
        raise ValueError(
            "prompt 不能为空。"
        )

    if not isinstance(
        model,
        str,
    ):
        raise TypeError(
            "model 必须是 str。"
        )

    if not model.strip():
        raise ValueError(
            "model 不能为空。"
        )

    # ========================================================
    # Ollama Request Payload
    # ========================================================

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.05,
            "top_p": 0.8,
        },
    }

    # ========================================================
    # HTTP Request
    # ========================================================

    response = requests.post(
        OLLAMA_URL,
        json=payload,
        timeout=300,
    )

    # ========================================================
    # HTTP Error
    # ========================================================

    response.raise_for_status()

    # ========================================================
    # JSON Response
    # ========================================================

    data = response.json()

    if not isinstance(
        data,
        dict,
    ):
        raise ValueError(
            "Ollama 返回的数据不是 JSON object。"
        )

    # ========================================================
    # Extract Response
    # ========================================================

    answer = data.get(
        "response",
        "",
    )

    if answer is None:
        answer = ""

    if not isinstance(
        answer,
        str,
    ):
        answer = str(answer)

    # ========================================================
    # Answer Sanitization
    # ========================================================
    #
    # 注意：
    #
    # Sanitization 不属于 legal_llm.py。
    #
    # 这里仅调用：
    #
    #     legal_answer_sanitizer.clean_answer()
    #
    # ========================================================

    return clean_answer(
        answer
    )


# ============================================================
# LLM 输出基础结构检查
# ============================================================

def validate_answer_structure(
    answer: str,
) -> bool:
    """
    对 Ollama 输出进行最基础的结构检查。

    ========================================================
    要求
    ========================================================

    每个正式 Section 恰好出现一次：

        【结论】
        【法律依据】
        【法律分析】
        【需要注意】

    并且顺序正确。

    ========================================================
    注意
    ========================================================

    这不是最终法律 Validation。

    真正的最终验证属于：

        src/legal_validation.py

    法律依据验证属于：

        src/legal_citation_validator.py

    本函数只检查：

        1. answer 是否存在
        2. 四个 Section 是否全部存在
        3. 每个 Section 是否恰好出现一次
        4. Section 顺序是否正确

    不检查：

        - 结论是否正确
        - 法律依据是否正确
        - 法律分析是否正确
        - 用户事实是否正确
        - Decision 是否正确
        - Citation 是否正确
        - UNKNOWN 是否被错误升级
        - SATISFIED 是否被错误修改
        - NOT_SATISFIED 是否被错误修改

    ========================================================
    """

    # ========================================================
    # 基础检查
    # ========================================================

    if not isinstance(
        answer,
        str,
    ):
        return False

    if not answer.strip():
        return False

    # ========================================================
    # Section 数量检查
    # ========================================================

    for section in REQUIRED_SECTIONS:

        if answer.count(section) != 1:

            return False

    # ========================================================
    # Section 顺序检查
    # ========================================================

    positions = [
        answer.find(section)
        for section in REQUIRED_SECTIONS
    ]

    if positions != sorted(
        positions
    ):

        return False

    # ========================================================
    # 防御性检查
    # ========================================================
    #
    # find() 返回 -1 表示 Section 不存在。
    #
    # 理论上前面的 count() 已经保证全部存在，
    # 这里保留防御性检查。
    # ========================================================

    if any(
        position < 0
        for position in positions
    ):
        return False

    return True


# ============================================================
# Ollama Runtime
# ============================================================

def generate_answer(
    prompt: str,
    model: str = OLLAMA_MODEL,
) -> str:
    """
    Legal LLM Runtime 统一入口。

    ========================================================
    Pipeline
    ========================================================

        Prompt
          ↓
        call_ollama()
          ↓
        clean_answer()
          ↓
        Answer

    ========================================================
    注意
    ========================================================

    Prompt 的构建不在本模块。

    应由：

        src/legal_prompt.py

    完成。

    Answer Sanitization 不在本模块。

    应由：

        src/legal_answer_sanitizer.py

    完成。

    Final Validation 不在本模块。

    应由：

        src/legal_validation.py

    完成。

    ========================================================
    """

    return call_ollama(
        prompt=prompt,
        model=model,
    )


# ============================================================
# 模块导出
# ============================================================
#
# 只导出本模块真正负责的公开接口。
#
# 不再错误导出：
#
#     normalize_text
#     clean_answer
#     remove_duplicate_sections
#
# 其中：
#
#     normalize_text
#         属于 legal_common_utils.py
#
#     clean_answer
#         属于 legal_answer_sanitizer.py
#
#     remove_duplicate_sections
#         属于 legal_answer_sanitizer.py
#
# ============================================================

__all__ = [
    "RAG_VERSION",
    "OLLAMA_URL",
    "OLLAMA_MODEL",
    "REQUIRED_SECTIONS",
    "call_ollama",
    "validate_answer_structure",
    "generate_answer",
]