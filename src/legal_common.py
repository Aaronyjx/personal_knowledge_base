# -*- coding: utf-8 -*-

"""
Legal Common Utilities

============================================================
功能
============================================================

RAG 公共基础工具层。

职责：

    1. 通用文本处理
    2. 通用列表处理
    3. 文本去重
    4. dict / object 字段读取
    5. 多字段兼容读取
    6. Rule 字段读取

============================================================
模块边界
============================================================

本模块只负责通用基础函数。

不负责：

    - Structured Article → Rule
    - Legal Decision Engine
    - Decision Adapter
    - Legal Answer Builder
    - Legal Prompt
    - Ollama
    - Legal Citation Validation

============================================================
拆分说明
============================================================

这些函数原本位于：

    src/rag.py

本次从 RAG V6.0-27 中独立出来，
为后续继续拆分：

    legal_rule_builder.py
    legal_citation_validator.py
    legal_decision_engine.py

提供公共基础依赖。

============================================================
"""


from typing import Any, Dict, List


# ============================================================
# 通用文本函数
# ============================================================

def normalize_text(value: Any) -> str:
    # 安全文本转换。
    #
    # None 返回空字符串。
    #
    # 其他类型转换为字符串。

    if value is None:
        return ""

    return str(value).strip()


# ============================================================
# 通用列表函数
# ============================================================

def ensure_list(value: Any) -> List[Any]:
    # 将对象转换为列表。

    if value is None:
        return []

    if isinstance(value, list):
        return value

    if isinstance(value, tuple):
        return list(value)

    if isinstance(value, set):
        return list(value)

    return [value]


# ============================================================
# 文本去重
# ============================================================

def unique_texts(values: List[Any]) -> List[str]:
    # 保持原始顺序进行文本去重。

    result = []

    seen = set()

    for value in values:
        text = normalize_text(value)

        if not text:
            continue

        if text in seen:
            continue

        seen.add(text)

        result.append(text)

    return result


# ============================================================
# 通用字段读取
# ============================================================

def get_field(value: Any, name: str, default: Any = None) -> Any:
    # 同时支持 dict 和 object.attribute。

    if value is None:
        return default

    if isinstance(value, dict):
        return value.get(name, default)

    if hasattr(value, name):
        return getattr(value, name)

    return default


# ============================================================
# 多字段读取
# ============================================================

def get_first_field(
    value: Any,
    names: List[str],
    default: Any = None,
) -> Any:
    # 按顺序读取第一个存在的字段。

    for name in names:
        result = get_field(value, name, None)

        if result is not None:
            return result

    return default


# ============================================================
# Rule 字段读取
# ============================================================

def get_rule_value(
    rule: Any,
    *names: str,
) -> Any:
    # 从 Rule 中读取字段。
    #
    # 同时兼容：
    #
    #     dict
    #
    #     object.attribute

    if rule is None:
        return None

    for name in names:
        result = get_field(rule, name, None)

        if result is not None:
            return result

    return None