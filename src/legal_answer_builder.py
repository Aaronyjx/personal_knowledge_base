# -*- coding: utf-8 -*-

"""
RAG V6.0-14
Legal Answer Builder
============================================================

功能
============================================================

本模块负责：

    Decision Engine
          ↓
    DecisionResult
          ↓
    Legal Answer Builder
          ↓
    Structured Answer
          ↓
    Ollama
          ↓
    Final Legal Answer


============================================================
V6.0-14 核心原则
============================================================

1. Decision Engine 是唯一法律决策来源。

2. Legal Answer Builder 不重新进行法律推理。

3. Legal Answer Builder 不创建新的 ConditionResult。

4. Legal Answer Builder 不修改 DecisionResult。

5. Builder 只负责：

       DecisionResult
            ↓
       Structured Answer

6. UNKNOWN 必须保持 UNKNOWN。

7. CONDITIONAL 必须保持 CONDITIONAL。

8. 用户明确陈述的事实与法律规则条件必须严格区分。

9. 用户事实：

       公司连续签订三次固定期限劳动合同

   不等于：

       连续订立二次固定期限劳动合同

   前者是用户事实，
   后者是法律规则条件。

10. ConditionResult 的完整结构必须保留。

11. V6.0-14 的 ConditionResult 固定结构：

       REQUIRED   = 4
       EXCLUSION  = 3
       EXCEPTION  = 1
       TOTAL      = 8

12. Builder 不允许通过“补条件”的方式修改 DecisionResult。

13. Builder 不允许通过“猜测”把 UNKNOWN 转换成 SATISFIED。

14. Builder 不允许把用户事实自动转换成法律结论。

15. Builder 输出必须适合后续 Ollama Prompt 使用。


============================================================
V6.0-14 ConditionResult 结构
============================================================

REQUIRED:

    1. 连续订立二次固定期限劳动合同
    2. 存在后续订立的劳动合同
    3. 续订劳动合同
    4. 劳动者提出或者同意续订、订立劳动合同

EXCLUSION:

    5. 劳动者存在《劳动合同法》第三十九条规定的情形
    6. 劳动者存在《劳动合同法》第四十条第一项规定的情形
    7. 劳动者存在《劳动合同法》第四十条第二项规定的情形

EXCEPTION:

    8. 劳动者提出订立固定期限劳动合同


============================================================
设计边界
============================================================

本模块不是：

    Decision Engine
    Rule Engine
    Legal Reasoning Engine
    Fact Extractor

本模块只是：

    Answer Builder

也就是说：

    Engine 决定“法律状态是什么”
    Builder 决定“如何结构化表达这个状态”


============================================================
"""

from __future__ import annotations

from src.legal_constants import (
    SATISFIED,
    NOT_SATISFIED,
    UNKNOWN,
    REQUIRED,
    EXCLUSION,
    EXCEPTION,
    DEFINITE,
    CONDITIONAL,
    NOT_ESTABLISHED,
)

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Iterable, List, Optional

from src.legal_rule_definition import RULE_ID
from src.legal_rule_registry import get_rule


# ============================================================
# Version
# ============================================================

BUILDER_VERSION = "V6.1"


# ============================================================
# Decision Constants
# ============================================================





# ============================================================
# Expected Condition Structure
# ============================================================

# ============================================================
# Canonical Rule Compatibility Structure
# ============================================================
#
# EXPECTED_* 保留为 Builder 的兼容接口。
#
# 它们不再自行定义 Article 14 条件，
# 而是统一从 Canonical Rule Registry 获取。
#
# 因此：
#
#     Rule Definition
#           ↓
#     Rule Registry
#           ↓
#     EXPECTED_*
#           ↓
#     Builder Validation
#
# Builder 仍然可以使用原有 EXPECTED_* 名称，
# 但不再形成第二套法律规则定义。
# ============================================================

_CANONICAL_RULE = get_rule(RULE_ID)

EXPECTED_REQUIRED_CONDITIONS = list(
    _CANONICAL_RULE["conditions"]
)

EXPECTED_EXCLUSION_CONDITIONS = list(
    _CANONICAL_RULE["exclusion_conditions"]
)

EXPECTED_EXCEPTION_CONDITIONS = list(
    _CANONICAL_RULE["exceptions"]
)

EXPECTED_TOTAL_CONDITIONS = (
    len(EXPECTED_REQUIRED_CONDITIONS)
    + len(EXPECTED_EXCLUSION_CONDITIONS)
    + len(EXPECTED_EXCEPTION_CONDITIONS)
)


# ============================================================
# Utility Functions
# ============================================================

def safe_text(value: Any) -> str:
    """
    将任意对象安全转换为字符串。

    Builder 不应该因为上游某个字段为 None
    而导致整个 Answer Builder 崩溃。
    """

    if value is None:
        return ""

    if isinstance(value, str):
        return value.strip()

    try:
        return str(value).strip()
    except Exception:
        return ""


def get_value(
    obj: Any,
    key: str,
    default: Any = None,
) -> Any:
    """
    从 dict / object 中读取字段。

    支持：

        dict
        dataclass
        普通 object

    不进行任何法律推理。
    """

    if obj is None:
        return default

    if isinstance(obj, dict):
        return obj.get(key, default)

    try:
        return getattr(obj, key, default)
    except Exception:
        return default


def normalize_list(value: Any) -> List[Any]:
    """
    将输入安全转换成 List。

    不改变元素本身。
    """

    if value is None:
        return []

    if isinstance(value, list):
        return list(value)

    if isinstance(value, tuple):
        return list(value)

    if isinstance(value, set):
        return list(value)

    if isinstance(value, Iterable) and not isinstance(
        value,
        (str, bytes, dict),
    ):
        try:
            return list(value)
        except Exception:
            return [value]

    return [value]


def unique_strings(values: Iterable[Any]) -> List[str]:
    """
    去除重复字符串。

    这里只用于展示层结构化。
    不用于修改 DecisionResult。
    """

    result: List[str] = []
    seen = set()

    for value in values:
        text = safe_text(value)

        if not text:
            continue

        if text in seen:
            continue

        seen.add(text)
        result.append(text)

    return result


# ============================================================
# Condition View
# ============================================================

@dataclass
class ConditionView:
    """
    Builder 层条件展示对象。

    注意：

    ConditionView 不是 ConditionResult。

    它只是对 Engine 已经产生的 ConditionResult
    做只读结构化展示。

    Builder 不在这里产生法律判断。
    """

    condition_id: str
    condition: str
    status: str
    reason: str = ""
    condition_type: str = REQUIRED

    @property
    def type(self) -> str:
        """
        与 ConditionResult.type 保持兼容。
        """

        return self.condition_type

    def to_dict(self) -> Dict[str, Any]:
        """
        转换为普通 dict。
        """

        return {
            "condition_id": self.condition_id,
            "condition": self.condition,
            "status": self.status,
            "reason": self.reason,
            "condition_type": self.condition_type,
            "type": self.condition_type,
        }


# ============================================================
# Structured Answer
# ============================================================

@dataclass
class StructuredAnswer:
    """
    法律回答结构。

    这是 Decision Engine → Ollama 之间的中间结构。

    重要：

    StructuredAnswer 不是法律决策器。

    它只保存：

        用户事实
        Decision
        Conditions
        Rules
        Explanation

    所有法律状态均来自 DecisionResult。
    """

    decision: str = ""

    user_facts: List[str] = field(default_factory=list)

    satisfied_conditions: List[str] = field(
        default_factory=list
    )

    unknown_conditions: List[str] = field(
        default_factory=list
    )

    not_satisfied_conditions: List[str] = field(
        default_factory=list
    )

    required_conditions: List[str] = field(
        default_factory=list
    )

    exclusion_conditions: List[str] = field(
        default_factory=list
    )

    exception_conditions: List[str] = field(
        default_factory=list
    )

    condition_results: List[ConditionView] = field(
        default_factory=list
    )

    legal_rules: List[str] = field(
        default_factory=list
    )

    rule_dependencies: List[Any] = field(
        default_factory=list
    )

    contract_sequence: Dict[str, Any] = field(
        default_factory=dict
    )

    selected_rule: str = ""

    explanation: str = ""

    engine_version: str = ""

    builder_version: str = BUILDER_VERSION

    def to_dict(self) -> Dict[str, Any]:
        """
        转换为 JSON-friendly dict。
        """

        return {
            "decision": self.decision,

            "user_facts": list(
                self.user_facts
            ),

            "satisfied_conditions": list(
                self.satisfied_conditions
            ),

            "unknown_conditions": list(
                self.unknown_conditions
            ),

            "not_satisfied_conditions": list(
                self.not_satisfied_conditions
            ),

            "required_conditions": list(
                self.required_conditions
            ),

            "exclusion_conditions": list(
                self.exclusion_conditions
            ),

            "exception_conditions": list(
                self.exception_conditions
            ),

            "condition_results": [
                item.to_dict()
                if isinstance(
                    item,
                    ConditionView,
                )
                else item
                for item in self.condition_results
            ],

            "legal_rules": list(
                self.legal_rules
            ),

            "rule_dependencies": [
                _safe_to_dict(item)
                for item in self.rule_dependencies
            ],

            "contract_sequence": dict(
                self.contract_sequence
            ),

            "selected_rule": self.selected_rule,

            "explanation": self.explanation,

            "engine_version": self.engine_version,

            "builder_version": self.builder_version,
        }


# ============================================================
# Generic Object Conversion
# ============================================================

def _safe_to_dict(value: Any) -> Any:
    """
    将对象转换成可序列化结构。

    不执行任何推理。
    """

    if value is None:
        return None

    if isinstance(value, dict):
        return {
            str(k): _safe_to_dict(v)
            for k, v in value.items()
        }

    if isinstance(value, list):
        return [
            _safe_to_dict(item)
            for item in value
        ]

    if isinstance(value, tuple):
        return [
            _safe_to_dict(item)
            for item in value
        ]

    if hasattr(value, "to_dict"):
        try:
            return _safe_to_dict(
                value.to_dict()
            )
        except Exception:
            pass

    if hasattr(value, "__dataclass_fields__"):
        try:
            return _safe_to_dict(
                asdict(value)
            )
        except Exception:
            pass

    if hasattr(value, "__dict__"):
        try:
            return {
                str(k): _safe_to_dict(v)
                for k, v in vars(value).items()
                if not str(k).startswith("_")
            }
        except Exception:
            pass

    return value


# ============================================================
# ConditionResult Adapter
# ============================================================

def _condition_to_view(
    condition_result: Any,
) -> ConditionView:
    """
    将 Engine ConditionResult 转换为 Builder ConditionView。

    关键原则：

        不改变 condition
        不改变 status
        不改变 reason
        不改变 condition_type

    Builder 只做展示层适配。
    """

    condition_id = safe_text(
        get_value(
            condition_result,
            "condition_id",
            "",
        )
    )

    if not condition_id:
        raise ValueError(
            "ConditionResult 缺少 condition_id，"
            "无法构造 V6.2 ConditionView。"
        )

    condition = safe_text(
        get_value(
            condition_result,
            "condition",
            "",
        )
    )

    status = safe_text(
        get_value(
            condition_result,
            "status",
            UNKNOWN,
        )
    )

    reason = safe_text(
        get_value(
            condition_result,
            "reason",
            "",
        )
    )

    condition_type = safe_text(
        get_value(
            condition_result,
            "condition_type",
            "",
        )
    )

    if not condition_type:
        condition_type = safe_text(
            get_value(
                condition_result,
                "type",
                "",
            )
        )

    return ConditionView(
        condition_id=condition_id,
        condition=condition,
        status=status,
        reason=reason,
        condition_type=condition_type,
    )


# ============================================================
# Decision Result Access
# ============================================================

def _get_condition_results(
    decision: Any,
) -> List[Any]:
    """
    从 DecisionResult 中读取原始 ConditionResult。

    注意：

    这里绝不追加、删除或者修改 ConditionResult。

    如果 Decision Engine 给出 8 个，
    Builder 就读取 8 个。

    如果数量不正确，
    应该报告结构错误，而不是偷偷修复。
    """

    value = get_value(
        decision,
        "condition_results",
        [],
    )

    return normalize_list(value)


# ============================================================
# Condition Classification
# ============================================================

def _classify_conditions(
    condition_results: List[Any],
) -> Dict[str, List[Any]]:
    """
    按 condition_type 分类。

    只读取 Engine 的 condition_type。

    不根据 condition 名称猜测类型。
    """

    classified = {
        REQUIRED: [],
        EXCLUSION: [],
        EXCEPTION: [],
    }

    for item in condition_results:
        condition_type = safe_text(
            get_value(
                item,
                "condition_type",
                "",
            )
        )

        if not condition_type:
            condition_type = safe_text(
                get_value(
                    item,
                    "type",
                    "",
                )
            )

        if condition_type in classified:
            classified[
                condition_type
            ].append(item)

    return classified


def _condition_names(
    values: Iterable[Any],
) -> List[str]:
    """
    提取条件名称。
    """

    return unique_strings(
        get_value(
            item,
            "condition",
            "",
        )
        for item in values
    )


def _status_names(
    values: Iterable[Any],
    status: str,
) -> List[str]:
    """
    提取指定状态的条件名称。

    状态完全来自 Engine。
    """

    result = []

    for item in values:
        item_status = safe_text(
            get_value(
                item,
                "status",
                "",
            )
        )

        if item_status != status:
            continue

        condition = safe_text(
            get_value(
                item,
                "condition",
                "",
            )
        )

        if condition:
            result.append(condition)

    return unique_strings(result)


# ============================================================
# Contract Sequence
# ============================================================

def _build_contract_sequence(
    decision: Any,
) -> Dict[str, Any]:
    """
    读取 ContractSequence。

    不重新分析合同次数。
    """

    sequence = get_value(
        decision,
        "contract_sequence",
        None,
    )

    if sequence is None:
        return {}

    if isinstance(sequence, dict):
        return {
            "count": sequence.get(
                "count",
                0,
            ),
            "term_type": sequence.get(
                "term_type",
                "",
            ),
            "continuous": sequence.get(
                "continuous",
                False,
            ),
        }

    return {
        "count": get_value(
            sequence,
            "count",
            0,
        ),
        "term_type": safe_text(
            get_value(
                sequence,
                "term_type",
                "",
            )
        ),
        "continuous": bool(
            get_value(
                sequence,
                "continuous",
                False,
            )
        ),
    }


# ============================================================
# Explicit Facts
# ============================================================

def _build_user_facts(
    decision: Any,
) -> List[str]:
    """
    从 DecisionResult 读取 explicit_facts。

    不把 ConditionResult 转换成 user fact。

    例如：

        用户事实：
        公司连续签订三次固定期限劳动合同

    必须保持为用户事实。

    不能因为存在：

        连续订立二次固定期限劳动合同

    就把它替换掉。
    """

    explicit_facts = get_value(
        decision,
        "explicit_facts",
        [],
    )

    result: List[str] = []

    for fact in normalize_list(
        explicit_facts
    ):
        if isinstance(fact, str):
            text = safe_text(fact)

        elif isinstance(fact, dict):
            text = safe_text(
                fact.get(
                    "fact",
                    fact.get(
                        "text",
                        "",
                    ),
                )
            )

        else:
            text = safe_text(
                get_value(
                    fact,
                    "fact",
                    get_value(
                        fact,
                        "text",
                        "",
                    ),
                )
            )

        if text:
            result.append(text)

    return unique_strings(result)


# ============================================================
# Legal Rules
# ============================================================

def _build_legal_rules(
    decision: Any,
) -> List[str]:
    """
    读取法律规则。

    支持：

        selected_rule
        rule_dependencies

    不自行产生新的法律规则。
    """

    result: List[str] = []

    selected_rule = safe_text(
        get_value(
            decision,
            "selected_rule",
            "",
        )
    )

    if selected_rule:
        result.append(
            selected_rule
        )

    dependencies = normalize_list(
        get_value(
            decision,
            "rule_dependencies",
            [],
        )
    )

    for dependency in dependencies:
        rule_name = safe_text(
            get_value(
                dependency,
                "rule_name",
                "",
            )
        )

        if rule_name:
            result.append(
                rule_name
            )

    return unique_strings(result)


# ============================================================
# Decision Validation
# ============================================================

def validate_decision_result(
    decision: Any,
) -> None:
    """
    验证 DecisionResult 是否具有 Builder 所需要的基本结构。

    这里只做结构检查。

    不修改对象。
    """

    if decision is None:
        raise ValueError(
            "DecisionResult 不能为空"
        )

    decision_value = safe_text(
        get_value(
            decision,
            "decision",
            "",
        )
    )

    if not decision_value:
        raise ValueError(
            "DecisionResult.decision 不能为空"
        )

    condition_results = _get_condition_results(
        decision
    )

    if not condition_results:
        raise ValueError(
            "DecisionResult.condition_results 不能为空"
        )


# ============================================================
# Condition Structure Validation
# ============================================================

def validate_condition_structure(
    decision: Any,
    strict: bool = True,
) -> Dict[str, Any]:
    """
    验证 ConditionResult 结构。

    V6.0-14 正常情况下必须：

        REQUIRED   = 4
        EXCLUSION  = 3
        EXCEPTION  = 1
        TOTAL      = 8

    strict=True：

        不符合结构直接抛出 ValueError。

    strict=False：

        返回检查结果，
        供调试使用。

    注意：

    Builder 不会通过补条件的方式修复结构。
    """

    condition_results = _get_condition_results(
        decision
    )

    classified = _classify_conditions(
        condition_results
    )

    required = classified[
        REQUIRED
    ]

    exclusion = classified[
        EXCLUSION
    ]

    exception = classified[
        EXCEPTION
    ]

    unknown_types = []

    for item in condition_results:
        condition_type = safe_text(
            get_value(
                item,
                "condition_type",
                get_value(
                    item,
                    "type",
                    "",
                ),
            )
        )

        if condition_type not in {
            REQUIRED,
            EXCLUSION,
            EXCEPTION,
        }:
            unknown_types.append(
                condition_type
            )

    all_names = [
        safe_text(
            get_value(
                item,
                "condition",
                "",
            )
        )
        for item in condition_results
    ]

    duplicate_names = []

    seen = set()

    for name in all_names:
        if not name:
            continue

        if name in seen:
            duplicate_names.append(
                name
            )
        else:
            seen.add(name)

    actual_required_names = _condition_names(
        required
    )

    actual_exclusion_names = _condition_names(
        exclusion
    )

    actual_exception_names = _condition_names(
        exception
    )

    missing_required = [
        item
        for item in EXPECTED_REQUIRED_CONDITIONS
        if item not in actual_required_names
    ]

    missing_exclusion = [
        item
        for item in EXPECTED_EXCLUSION_CONDITIONS
        if item not in actual_exclusion_names
    ]

    missing_exception = [
        item
        for item in EXPECTED_EXCEPTION_CONDITIONS
        if item not in actual_exception_names
    ]

    extra_conditions = [
        name
        for name in all_names
        if name
        and name not in (
            EXPECTED_REQUIRED_CONDITIONS
            + EXPECTED_EXCLUSION_CONDITIONS
            + EXPECTED_EXCEPTION_CONDITIONS
        )
    ]

    result = {
        "valid": True,

        "total": len(
            condition_results
        ),

        "required": len(
            required
        ),

        "exclusion": len(
            exclusion
        ),

        "exception": len(
            exception
        ),

        "expected_total":
            EXPECTED_TOTAL_CONDITIONS,

        "expected_required":
            len(
                EXPECTED_REQUIRED_CONDITIONS
            ),

        "expected_exclusion":
            len(
                EXPECTED_EXCLUSION_CONDITIONS
            ),

        "expected_exception":
            len(
                EXPECTED_EXCEPTION_CONDITIONS
            ),

        "unknown_types":
            unique_strings(
                unknown_types
            ),

        "duplicate_conditions":
            unique_strings(
                duplicate_names
            ),

        "missing_required":
            missing_required,

        "missing_exclusion":
            missing_exclusion,

        "missing_exception":
            missing_exception,

        "extra_conditions":
            unique_strings(
                extra_conditions
            ),
    }

    errors: List[str] = []

    if (
        result["total"]
        != EXPECTED_TOTAL_CONDITIONS
    ):
        errors.append(
            "ConditionResult 总数错误："
            f"{result['total']} != "
            f"{EXPECTED_TOTAL_CONDITIONS}"
        )

    if (
        result["required"]
        != len(
            EXPECTED_REQUIRED_CONDITIONS
        )
    ):
        errors.append(
            "REQUIRED 数量错误："
            f"{result['required']} != {len(EXPECTED_REQUIRED_CONDITIONS)}"
        )

    if (
        result["exclusion"]
        != len(
            EXPECTED_EXCLUSION_CONDITIONS
        )
    ):
        errors.append(
            "EXCLUSION 数量错误："
            f"{result['exclusion']} != {len(EXPECTED_EXCLUSION_CONDITIONS)}"
        )

    if (
        result["exception"]
        != len(
            EXPECTED_EXCEPTION_CONDITIONS
        )
    ):
        errors.append(
            "EXCEPTION 数量错误："
            f"{result['exception']} != {len(EXPECTED_EXCEPTION_CONDITIONS)}"
        )

    if result["unknown_types"]:
        errors.append(
            "存在未知 condition_type："
            + ", ".join(
                result["unknown_types"]
            )
        )

    if result["duplicate_conditions"]:
        errors.append(
            "存在重复 Condition："
            + ", ".join(
                result["duplicate_conditions"]
            )
        )

    if result["missing_required"]:
        errors.append(
            "缺少 REQUIRED Condition："
            + ", ".join(
                result["missing_required"]
            )
        )

    if result["missing_exclusion"]:
        errors.append(
            "缺少 EXCLUSION Condition："
            + ", ".join(
                result["missing_exclusion"]
            )
        )

    if result["missing_exception"]:
        errors.append(
            "缺少 EXCEPTION Condition："
            + ", ".join(
                result["missing_exception"]
            )
        )

    if result["extra_conditions"]:
        errors.append(
            "存在额外 Condition："
            + ", ".join(
                result["extra_conditions"]
            )
        )

    if errors:
        result["valid"] = False
        result["errors"] = errors

        if strict:
            raise ValueError(
                "ConditionResult 结构验证失败：\n"
                + "\n".join(
                    f"  - {error}"
                    for error in errors
                )
            )

    else:
        result["errors"] = []

    return result


# ============================================================
# Build Condition Views
# ============================================================

def _build_condition_views(
    condition_results: List[Any],
) -> List[ConditionView]:
    """
    把 Engine ConditionResult 转换为 Builder View。

    数量一一对应。

    不添加任何 ConditionResult。
    """

    return [
        _condition_to_view(item)
        for item in condition_results
    ]


# ============================================================
# Build Structured Answer
# ============================================================

def build_structured_answer(
    decision: Any,
    strict: bool = True,
) -> StructuredAnswer:
    """
    构建 StructuredAnswer。

    核心流程：

        DecisionResult
             ↓
        读取 decision
             ↓
        读取 explicit_facts
             ↓
        读取 ConditionResults
             ↓
        按 status 分类
             ↓
        按 condition_type 分类
             ↓
        StructuredAnswer

    没有法律推理。
    """

    validate_decision_result(
        decision
    )

    if strict:
        validate_condition_structure(
            decision,
            strict=True,
        )

    condition_results = _get_condition_results(
        decision
    )

    classified = _classify_conditions(
        condition_results
    )

    decision_value = safe_text(
        get_value(
            decision,
            "decision",
            "",
        )
    )

    explicit_facts = _build_user_facts(
        decision
    )

    satisfied_conditions = _status_names(
        condition_results,
        SATISFIED,
    )

    unknown_conditions = _status_names(
        classified[REQUIRED],
        UNKNOWN,
    )

    not_satisfied_conditions = _status_names(
        condition_results,
        NOT_SATISFIED,
    )

    required_conditions = _condition_names(
        classified[REQUIRED]
    )

    exclusion_conditions = _condition_names(
        classified[EXCLUSION]
    )

    exception_conditions = _condition_names(
        classified[EXCEPTION]
    )

    condition_views = _build_condition_views(
        condition_results
    )

    legal_rules = _build_legal_rules(
        decision
    )

    dependencies = normalize_list(
        get_value(
            decision,
            "rule_dependencies",
            [],
        )
    )

    selected_rule = safe_text(
        get_value(
            decision,
            "selected_rule",
            "",
        )
    )

    explanation = safe_text(
        get_value(
            decision,
            "explanation",
            "",
        )
    )

    engine_version = safe_text(
        get_value(
            decision,
            "engine_version",
            "",
        )
    )

    contract_sequence = (
        _build_contract_sequence(
            decision
        )
    )

    return StructuredAnswer(
        decision=decision_value,

        user_facts=explicit_facts,

        satisfied_conditions=(
            satisfied_conditions
        ),

        unknown_conditions=(
            unknown_conditions
        ),

        not_satisfied_conditions=(
            not_satisfied_conditions
        ),

        required_conditions=(
            required_conditions
        ),

        exclusion_conditions=(
            exclusion_conditions
        ),

        exception_conditions=(
            exception_conditions
        ),

        condition_results=condition_views,

        legal_rules=legal_rules,

        rule_dependencies=dependencies,

        contract_sequence=contract_sequence,

        selected_rule=selected_rule,

        explanation=explanation,

        engine_version=engine_version,

        builder_version=BUILDER_VERSION,
    )


# ============================================================
# Compatibility Adapter
# ============================================================

def adapt_decision_for_answer_builder(
    decision: Any,
    strict: bool = True,
) -> StructuredAnswer:
    """
    兼容 RAG Pipeline 的调用接口。

    当前 rag.py 可以使用：

        structured_answer = (
            adapt_decision_for_answer_builder(
                decision
            )
        )

    这个函数不修改 DecisionResult。

    只是：

        DecisionResult
            ↓
        StructuredAnswer
    """

    return build_structured_answer(
        decision,
        strict=strict,
    )


# ============================================================
# Compatibility View Adapters
# ============================================================

def _format_contract_sequence(
    sequence: Dict[str, Any],
) -> str:
    """
    Builder 兼容接口。

    实际展示逻辑已经移动到：

        src/legal_answer_views.py
    """

    from src.legal_answer_views import (
        format_contract_sequence,
    )

    return format_contract_sequence(
        sequence
    )


def _format_condition_group(
    title: str,
    conditions: List[str],
) -> List[str]:
    """
    Builder 兼容接口。

    实际展示逻辑已经移动到：

        src/legal_answer_views.py
    """

    from src.legal_answer_views import (
        format_condition_group,
    )

    return format_condition_group(
        title,
        conditions,
    )


def build_plain_answer(
    structured_answer: Any,
) -> str:
    """
    Builder 兼容接口。

    保留原有：

        legal_answer_builder.build_plain_answer()

    调用方式不变。

    如果传入的是 DecisionResult，
    仍然由 Builder Core 完成：

        DecisionResult
            ↓
        StructuredAnswer

    然后交给 Views 层进行展示。

    Views 层本身不进行法律转换。
    """

    if not isinstance(
        structured_answer,
        StructuredAnswer,
    ):
        structured_answer = build_structured_answer(
            structured_answer
        )

    from src.legal_answer_views import (
        build_plain_answer as _build_plain_answer_view,
    )

    return _build_plain_answer_view(
        structured_answer
    )


def build_answer_context(
    structured_answer: Any,
) -> Dict[str, Any]:
    """
    Builder 兼容接口。

    保留原有外部调用方式。
    """

    if not isinstance(
        structured_answer,
        StructuredAnswer,
    ):
        structured_answer = build_structured_answer(
            structured_answer
        )

    from src.legal_answer_views import (
        build_answer_context as _build_answer_context_view,
    )

    return _build_answer_context_view(
        structured_answer
    )


def build_prompt_context(
    structured_answer: Any,
) -> str:
    """
    Builder 兼容接口。

    保留原有外部调用方式。
    """

    if not isinstance(
        structured_answer,
        StructuredAnswer,
    ):
        structured_answer = build_structured_answer(
            structured_answer
        )

    from src.legal_answer_views import (
        build_prompt_context as _build_prompt_context_view,
    )

    return _build_prompt_context_view(
        structured_answer
    )


def summarize_structured_answer(
    structured_answer: Any,
) -> str:
    """
    Builder 兼容接口。

    保留原有外部调用方式。
    """

    if not isinstance(
        structured_answer,
        StructuredAnswer,
    ):
        structured_answer = build_structured_answer(
            structured_answer
        )

    from src.legal_answer_views import (
        summarize_structured_answer
        as _summarize_structured_answer_view,
    )

    return _summarize_structured_answer_view(
        structured_answer
    )


# ============================================================
# Component Test Helpers
# ============================================================

