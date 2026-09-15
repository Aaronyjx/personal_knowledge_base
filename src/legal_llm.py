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
    3. Qwen Thinking 内容清理
    4. Markdown 标题清理
    5. 重复 Section 清理

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

============================================================
重构后的职责边界
============================================================

src/legal_llm.py
    ↓
    Ollama Runtime

src/legal_prompt.py
    ↓
    Ollama Prompt Builder

src/legal_validation.py
    ↓
    Final Validation

src/legal_citation_validator.py
    ↓
    Legal Citation Validation

src/legal_answer_builder.py
    ↓
    Deterministic Structured Answer

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

这样可以保证：

    Prompt 修改
        不需要修改 LLM Runtime

    Ollama 模型修改
        不需要修改 Prompt

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
# 标准库
# ============================================================

import re
from typing import Any


# ============================================================
# 第三方库
# ============================================================

import requests


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
# 本模块只负责识别和清理这些 Section。
#
# 不负责判断 Section 内容是否正确。
# ============================================================

REQUIRED_SECTIONS = [
    "【结论】",
    "【法律依据】",
    "【法律分析】",
    "【需要注意】",
]


# ============================================================
# 基础文本规范化
# ============================================================

def normalize_text(
    text: Any,
) -> str:
    """
    基础文本规范化。

    这里只处理：

        1. None
        2. 非字符串对象
        3. Windows 换行
        4. Mac 旧式换行
        5. 首尾空白

    不进行任何法律语义处理。
    """

    if text is None:
        return ""

    text = str(text)

    text = text.replace(
        "\r\n",
        "\n",
    )

    text = text.replace(
        "\r",
        "\n",
    )

    return text.strip()


# ============================================================
# Ollama
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

    ========================================================
    重要原则
    ========================================================

    本函数不负责：

        - 法律推理
        - Decision 判断
        - 条件判断
        - 用户事实判断
        - 法律依据判断

    这些内容均属于其他模块职责。
    """

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.05,
            "top_p": 0.8,
        },
    }

    response = requests.post(
        OLLAMA_URL,
        json=payload,
        timeout=300,
    )

    response.raise_for_status()

    data = response.json()

    answer = data.get(
        "response",
        "",
    )

    return clean_answer(
        answer
    )


# ============================================================
# 清理 Ollama 输出
# ============================================================

def clean_answer(
    answer: str,
) -> str:
    """
    清理 Ollama 输出。

    ========================================================
    清理内容
    ========================================================

    1. 空结果处理。

    2. 基础文本规范化。

    3. 删除 Qwen Thinking 内容。

    4. 删除 Markdown 标题符号。

    5. 压缩连续空行。

    6. 如果已经生成正式 Section，
       从第一个正式 Section 开始保留。

    7. 删除重复 Section。

    ========================================================
    注意
    ========================================================

    本函数不进行法律判断。

    例如：

        UNKNOWN
        SATISFIED
        NOT_SATISFIED
        DEFINITE
        CONDITIONAL
        NOT_ESTABLISHED

    都不会在这里重新计算。

    ========================================================
    """

    if not answer:
        return ""

    answer = normalize_text(
        answer
    )

    # ========================================================
    # 删除 Qwen Thinking 内容
    # ========================================================

    answer = re.sub(
        r"<think>.*?</think>",
        "",
        answer,
        flags=re.DOTALL,
    )

    answer = re.sub(
        r"<think>.*",
        "",
        answer,
        flags=re.DOTALL,
    )

    answer = answer.strip()

    # ========================================================
    # 删除 Markdown 标题符号
    #
    # 例如：
    #
    #     # 【结论】
    #
    # 转换为：
    #
    #     【结论】
    #
    # ========================================================

    answer = re.sub(
        r"(?m)^\s*#+\s*【",
        "【",
        answer,
    )

    # ========================================================
    # 多个空行压缩
    # ========================================================

    answer = re.sub(
        r"\n{3,}",
        "\n\n",
        answer,
    )

    # ========================================================
    # 如果四段标题存在，
    # 从第一个正式 Section 开始保留。
    # ========================================================

    positions = []

    for section in REQUIRED_SECTIONS:

        position = answer.find(
            section
        )

        if position >= 0:

            positions.append(
                position
            )

    if positions:

        start = min(
            positions
        )

        answer = answer[
            start:
        ]

    # ========================================================
    # 删除重复标题
    # ========================================================

    answer = remove_duplicate_sections(
        answer
    )

    return answer.strip()


# ============================================================
# 删除重复 Section
# ============================================================

def remove_duplicate_sections(
    text: str,
) -> str:
    """
    删除重复的最终回答 Section。

    例如 Ollama 可能生成：

        【结论】
        ...

        【法律依据】
        ...

        【法律分析】
        ...

        【结论】
        ...

    最终只保留第一次出现的：

        【结论】

    ========================================================
    注意
    ========================================================

    这里仅进行文本结构清理。

    不判断：

        - 哪一个结论正确
        - 哪一个法律依据正确
        - 哪一个条件正确

    ========================================================
    """

    if not text:
        return ""

    pattern = (
        r"(【结论】|【法律依据】|【法律分析】|【需要注意】)"
    )

    parts = re.split(
        pattern,
        text,
    )

    if len(parts) < 3:
        return text

    result = []

    seen = set()

    i = 0

    while i < len(parts):

        part = parts[i]

        if part in REQUIRED_SECTIONS:

            section_name = part

            body = ""

            if i + 1 < len(parts):

                body = parts[
                    i + 1
                ]

            if section_name not in seen:

                result.append(
                    section_name
                )

                result.append(
                    body
                )

                seen.add(
                    section_name
                )

            i += 2

        else:

            # ------------------------------------------------
            # 正式 Section 之前的普通文本，
            # 只保留第一次出现的前置文本。
            # ------------------------------------------------

            if (
                part.strip()
                and not result
            ):

                result.append(
                    part
                )

            i += 1

    return "".join(
        result
    ).strip()


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

    ========================================================
    """

    if not answer:
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

    ========================================================
    """

    return call_ollama(
        prompt=prompt,
        model=model,
    )


# ============================================================
# 模块导出
# ============================================================

__all__ = [
    "RAG_VERSION",
    "OLLAMA_URL",
    "OLLAMA_MODEL",
    "REQUIRED_SECTIONS",
    "normalize_text",
    "call_ollama",
    "clean_answer",
    "remove_duplicate_sections",
    "validate_answer_structure",
    "generate_answer",
]