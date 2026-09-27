"""
法律 RAG 全局语义常量。

V6.1：
统一维护 Condition Status、Condition Type、Decision Status，
避免 Decision Engine、Answer Builder 等模块重复定义相同字符串。

本文件只保存语义常量，不保存具体法律规则或条件列表。
"""

# ============================================================
# Condition Status
# ============================================================

SATISFIED = "SATISFIED"
NOT_SATISFIED = "NOT_SATISFIED"
UNKNOWN = "UNKNOWN"


# ============================================================
# Condition Type
# ============================================================

REQUIRED = "REQUIRED"
EXCLUSION = "EXCLUSION"
EXCEPTION = "EXCEPTION"


# ============================================================
# Decision Status
# ============================================================

DEFINITE = "DEFINITE"
CONDITIONAL = "CONDITIONAL"
NOT_ESTABLISHED = "NOT_ESTABLISHED"
