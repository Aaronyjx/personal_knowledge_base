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

11. V6.2 的 ConditionResult 结构：

       ConditionResult 的数量、
       REQUIRED / EXCLUSION / EXCEPTION 分类数量，
       均由当前 Runtime Rule 决定。

       Builder 不固定假设 Article 14 有 8 个条件。

12. Builder 不允许通过“补条件”的方式修改 DecisionResult。

13. Builder 不允许通过“猜测”把 UNKNOWN 转换成 SATISFIED。

14. Builder 不允许把用户事实自动转换成法律结论。

15. Builder 输出必须适合后续 Ollama Prompt 使用。


============================================================
V6.2 ConditionResult 结构
============================================================

ConditionResult 的完整结构由当前 Runtime Rule 决定。

Runtime Rule 提供：

    conditions
        ↓
    REQUIRED 条件

    exclusion_conditions
        ↓
    EXCLUSION 条件

    exceptions
        ↓
    EXCEPTION 条件

Builder 必须：

    1. 原样读取 DecisionResult.condition_results。
    2. 按 Runtime Rule 验证 ConditionResult 结构。
    3. 保留所有 ConditionResult。
    4. 保留每个 ConditionResult 的原始状态。
    5. 不根据 Article 14 的固定条件数量推导结构。

Builder 不得：

    1. 固定假设 ConditionResult 数量。
    2. 自动补充缺失条件。
    3. 删除多余条件。
    4. 修改 ConditionResult 的状态。
    5. 将 UNKNOWN 转换为 SATISFIED 或 NOT_SATISFIED。


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

from copy import deepcopy
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Iterable, List, Optional



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

def _get_runtime_expected_conditions(
    decision: Any,
) -> Dict[str, Any]:
    """
    从当前 DecisionResult 的 Runtime Rule 获取期望条件结构。

    V6.2：
        Builder 不再固定使用 RULE_ID / Article 14
        作为 ConditionResult 的结构来源。

    数据流：

        DecisionResult
            ↓
        selected_rule
            ↓
        Runtime Rule
            ↓
        conditions
        exclusion_conditions
        exceptions

    Builder 只消费 Engine 已经选择的 Runtime Rule，
    不自行选择 Rule，不重新执行法律推理。
    """

    selected_rule = get_value(
        decision,
        "selected_rule",
        None,
    )

    if not isinstance(selected_rule, dict):
        raise ValueError(
            "DecisionResult.selected_rule 必须是 Runtime Rule dict。"
        )

    required_conditions = selected_rule.get(
        "conditions",
        [],
    )

    exclusion_conditions = selected_rule.get(
        "exclusion_conditions",
        [],
    )

    exception_conditions = selected_rule.get(
        "exceptions",
        [],
    )

    if not isinstance(
        required_conditions,
        list,
    ):
        raise ValueError(
            "Runtime Rule.conditions 必须是 list。"
        )

    if not isinstance(
        exclusion_conditions,
        list,
    ):
        raise ValueError(
            "Runtime Rule.exclusion_conditions 必须是 list。"
        )

    if not isinstance(
        exception_conditions,
        list,
    ):
        raise ValueError(
            "Runtime Rule.exceptions 必须是 list。"
        )

    return {
        "required": list(
            required_conditions
        ),
        "exclusion": list(
            exclusion_conditions
        ),
        "exception": list(
            exception_conditions
        ),
        "total": (
            len(required_conditions)
            + len(exclusion_conditions)
            + len(exception_conditions)
        ),
    }


def _get_expected_condition_sets(
    decision: Any,
) -> Dict[str, Any]:
    """
    V6.2 兼容适配：

    将 Runtime Rule 的条件结构转换为
    Builder 当前验证逻辑所使用的 EXPECTED_* 语义。

    不产生任何法律条件。
    """

    expected = _get_runtime_expected_conditions(
        decision
    )

    return {
        "required": expected["required"],
        "exclusion": expected["exclusion"],
        "exception": expected["exception"],
        "total": expected["total"],
    }


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

    selected_rule: Dict[str, Any] = field(
        default_factory=dict
    )

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

            "selected_rule": deepcopy(self.selected_rule),

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

    # 原始身份字段必须严格校验，不允许 safe_text() 修复非法输入。
    raw_condition_id = get_value(
        condition_result,
        "condition_id",
        None,
    )

    if (
        not isinstance(raw_condition_id, str)
        or not raw_condition_id
        or raw_condition_id != raw_condition_id.strip()
    ):
        raise ValueError(
            f"ConditionResult.condition_id 非法："
            f"{raw_condition_id!r}"
        )

    condition_id = raw_condition_id

    # 条件文本必须是原始非空字符串，且不得有首尾空白。
    raw_condition = get_value(
        condition_result,
        "condition",
        None,
    )

    if (
        not isinstance(raw_condition, str)
        or not raw_condition
        or raw_condition != raw_condition.strip()
    ):
        raise ValueError(
            f"ConditionResult.condition 非法："
            f"{raw_condition!r}"
        )

    condition = raw_condition

    # 状态必须由 Decision Engine 明确提供。
    # 缺失状态不能被静默解释为 UNKNOWN。
    status_value = get_value(
        condition_result,
        "status",
        None,
    )

    if status_value is None:
        raise ValueError(
            "ConditionResult 缺少 status，"
            "不能将缺失状态默认转换为 UNKNOWN。"
        )

    # RAW_STATUS_EXACT_VALIDATION
    # 必须校验原始值，禁止 safe_text() 将非法状态清洗为合法状态。
    if (
        not isinstance(status_value, str)
        or status_value not in {
            SATISFIED,
            NOT_SATISFIED,
            UNKNOWN,
        }
    ):
        raise ValueError(
            f"ConditionResult.status 非法：{status_value!r}"
        )

    status = status_value

    reason = safe_text(
        get_value(
            condition_result,
            "reason",
            "",
        )
    )

    # 只在 condition_type 字段确实缺失时兼容旧字段 type。
    # 显式 None 或其他非法值均不得触发回退。
    raw_condition_type = _get_raw_condition_type(
        condition_result
    )

    allowed_condition_types = {
        REQUIRED,
        EXCLUSION,
        EXCEPTION,
    }

    if (
        not isinstance(raw_condition_type, str)
        or raw_condition_type not in allowed_condition_types
    ):
        raise ValueError(
            f"ConditionResult.condition_type 非法："
            f"{raw_condition_type!r}"
        )

    condition_type = raw_condition_type

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

    如果 Decision Engine 给出 Runtime Rule 定义数量的
    ConditionResult，Builder 就原样读取。

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

def _get_raw_condition_type(item: Any) -> Any:
    """
    读取原始 condition_type。

    只有 condition_type 字段确实不存在时，才兼容旧字段 type。
    显式 None、空字符串、非法字符串和非字符串值均原样返回。
    不执行 strip 或字符串转换。
    """

    if isinstance(item, dict):
        if "condition_type" in item:
            return item["condition_type"]
        return item.get("type", None)

    try:
        instance_values = vars(item)
    except (TypeError, AttributeError):
        instance_values = {}

    if "condition_type" in instance_values:
        return instance_values["condition_type"]

    # 支持 property、slot 等未存储在实例字典中的属性。
    try:
        value = getattr(item, "condition_type")
    except AttributeError:
        return get_value(item, "type", None)
    except Exception:
        # 属性读取异常时，不允许用旧字段掩盖问题。
        return None

    return value


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
        condition_type = _get_raw_condition_type(item)

        # 非字符串值和非规范枚举值不得参与合法分类计数。
        if (
            not isinstance(condition_type, str)
            or condition_type not in classified
        ):
            continue

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
    读取并校验 ContractSequence。

    不重新分析合同次数，不把非法字段转换成合法值。

    兼容行为：
        contract_sequence=None -> {}

    字段类型必须严格符合：
        count      -> int，但不允许 bool
        term_type  -> str
        continuous -> bool
    """

    sequence = get_value(
        decision,
        "contract_sequence",
        None,
    )

    if sequence is None:
        return {}

    # 保留原有 dict / 对象读取能力，但两种输入共用相同校验。
    if isinstance(sequence, dict):
        count = sequence.get("count", 0)
        term_type = sequence.get("term_type", "")
        continuous = sequence.get("continuous", False)
    else:
        count = get_value(
            sequence,
            "count",
            0,
        )
        term_type = get_value(
            sequence,
            "term_type",
            "",
        )
        continuous = get_value(
            sequence,
            "continuous",
            False,
        )

    # 必须使用 type(...) is ...，避免 bool 被当作 int 接受。
    if type(count) is not int:
        raise ValueError(
            "DecisionResult.contract_sequence.count 必须是 int，"
            "且不能是 bool。"
        )

    if type(term_type) is not str:
        raise ValueError(
            "DecisionResult.contract_sequence.term_type 必须是 str。"
        )

    if type(continuous) is not bool:
        raise ValueError(
            "DecisionResult.contract_sequence.continuous 必须是 bool。"
        )

    # 返回新字典。字段均为已校验的标量，避免嵌套可变对象引用泄漏。
    return {
        "count": count,
        "term_type": term_type,
        "continuous": continuous,
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

    selected_rule = get_value(
        decision,
        "selected_rule",
        {},
    )

    if isinstance(selected_rule, dict):
        rule_name = safe_text(
            selected_rule.get(
                "rule_name",
                "",
            )
        )

        if rule_name:
            result.append(
                rule_name
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

def _validate_condition_structure_impl(
    decision: Any,
    strict: bool = True,
) -> Dict[str, Any]:
    """
    验证 ConditionResult 结构。

    V6.2 正常情况下必须：

        ConditionResult 结构与当前 Runtime Rule 完全一致。

        REQUIRED / EXCLUSION / EXCEPTION
        的数量由 Runtime Rule 动态决定。

    strict=True：

        不符合结构直接抛出 ValueError。

    strict=False：

        返回检查结果，
        供调试使用。

    注意：

    Builder 不会通过补条件的方式修复结构。
    """

    expected = _get_expected_condition_sets(
        decision
    )

    expected_required_conditions = expected[
        "required"
    ]

    expected_exclusion_conditions = expected[
        "exclusion"
    ]

    expected_exception_conditions = expected[
        "exception"
    ]

    expected_total_conditions = expected[
        "total"
    ]

    # --------------------------------------------------------
    # Condition ID Integrity
    # 以 Runtime Rule.condition_definitions 作为唯一映射来源。
    # --------------------------------------------------------

    selected_rule = get_value(
        decision,
        "selected_rule",
        None,
    )

    if not isinstance(selected_rule, dict):
        raise ValueError(
            "DecisionResult.selected_rule 必须是 Runtime Rule dict。"
        )

    condition_definitions = selected_rule.get(
        "condition_definitions"
    )

    if not isinstance(condition_definitions, list):
        raise ValueError(
            "Runtime Rule.condition_definitions 必须是 list。"
        )

    if not condition_definitions:
        raise ValueError(
            "Runtime Rule.condition_definitions 不能为空。"
        )

    expected_by_id = {}
    expected_definition_names = set()

    for definition in condition_definitions:
        if not isinstance(definition, dict):
            raise ValueError(
                "Runtime Rule.condition_definitions 元素必须是 dict。"
            )

        definition_id = definition.get("condition_id")
        definition_name = definition.get("condition")
        definition_type = definition.get("condition_type")

        if (
            not isinstance(definition_id, str)
            or not definition_id.strip()
        ):
            raise ValueError(
                "Runtime Rule 存在空或非法 condition_id。"
            )

        if (
            not isinstance(definition_name, str)
            or not definition_name.strip()
        ):
            raise ValueError(
                "Runtime Rule 存在空或非法 condition。"
            )

        if (
            not isinstance(definition_type, str)
            or definition_type not in {
                REQUIRED,
                EXCLUSION,
                EXCEPTION,
            }
        ):
            raise ValueError(
                "Runtime Rule 存在非法 condition_type："
                f"{definition_type!r}"
            )

        # condition_id 是机器身份，禁止通过 strip() 静默修复。
        if definition_id != definition_id.strip():
            raise ValueError(
                "Runtime Rule.condition_definitions 的 condition_id "
                "不能包含首尾空格。"
            )

        # condition 是规则定义中的法律文本，必须精确匹配规范值。
        if definition_name != definition_name.strip():
            raise ValueError(
                "Runtime Rule.condition_definitions 的 condition "
                "不能包含首尾空格。"
            )

        definition_id = definition_id.strip()
        definition_name = definition_name.strip()

        if definition_id in expected_by_id:
            raise ValueError(
                "Runtime Rule 存在重复 condition_id："
                f"{definition_id}"
            )

        if definition_name in expected_definition_names:
            raise ValueError(
                "Runtime Rule 存在重复 condition："
                f"{definition_name}"
            )

        expected_by_id[definition_id] = {
            "condition": definition_name,
            "condition_type": definition_type,
        }
        expected_definition_names.add(definition_name)

    expected_names_by_type = {
        REQUIRED: expected_required_conditions,
        EXCLUSION: expected_exclusion_conditions,
        EXCEPTION: expected_exception_conditions,
    }

    for definition_type, expected_names in expected_names_by_type.items():
        definition_names = {
            item["condition"]
            for item in expected_by_id.values()
            if item["condition_type"] == definition_type
        }

        if (
            len(definition_names) != len(expected_names)
            or definition_names != set(expected_names)
        ):
            raise ValueError(
                "Runtime Rule.condition_definitions 与条件列表不一致："
                f"{definition_type}"
            )

    if len(expected_by_id) != expected_total_conditions:
        raise ValueError(
            "Runtime Rule.condition_definitions 数量错误："
            f"{len(expected_by_id)} != {expected_total_conditions}"
        )

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
    invalid_condition_types = []

    allowed_condition_types = {
        REQUIRED,
        EXCLUSION,
        EXCEPTION,
    }

    for index, item in enumerate(condition_results):
        raw_condition_type = _get_raw_condition_type(item)

        if (
            not isinstance(raw_condition_type, str)
            or raw_condition_type not in allowed_condition_types
        ):
            invalid_condition_types.append(
                f"第 {index + 1} 条条件的原始 condition_type 非法："
                f"{raw_condition_type!r}"
            )

            if isinstance(raw_condition_type, str):
                unknown_types.append(raw_condition_type)


    # 状态必须使用原始值精确校验，不允许 safe_text() 静默修复。
    invalid_statuses = []

    allowed_statuses = {
        SATISFIED,
        NOT_SATISFIED,
        UNKNOWN,
    }

    for index, item in enumerate(condition_results):
        raw_status = get_value(
            item,
            "status",
            None,
        )

        if (
            not isinstance(raw_status, str)
            or raw_status not in allowed_statuses
        ):
            invalid_statuses.append(
                f"第 {index + 1} 条条件的原始 status 非法："
                f"{raw_status!r}"
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

    actual_ids = []
    duplicate_ids = []
    condition_id_mismatches = []
    seen_ids = set()

    for index, item in enumerate(condition_results):
        # condition_id 是机器身份：先检查原始值，不做文本规范化。
        raw_condition_id = get_value(
            item,
            "condition_id",
            "",
        )

        condition_id = (
            raw_condition_id
            if isinstance(raw_condition_id, str)
            else ""
        )

        # 结构校验使用原始字符串，禁止静默清理身份关联字段。
        raw_condition_name = get_value(
            item,
            "condition",
            "",
        )
        condition_name = (
            raw_condition_name
            if isinstance(raw_condition_name, str)
            else safe_text(raw_condition_name)
        )

        raw_condition_type = _get_raw_condition_type(item)
        condition_type = (
            raw_condition_type
            if isinstance(raw_condition_type, str)
            else None
        )

        actual_ids.append(condition_id)

        if not condition_id:
            condition_id_mismatches.append(
                f"第 {index + 1} 条条件缺少 condition_id"
            )
            continue

        if condition_id in seen_ids:
            duplicate_ids.append(condition_id)
        else:
            seen_ids.add(condition_id)

        expected_definition = expected_by_id.get(
            condition_id
        )

        if expected_definition is None:
            condition_id_mismatches.append(
                f"未知 condition_id：{condition_id}"
            )
            continue

        if condition_name != expected_definition["condition"]:
            condition_id_mismatches.append(
                f"{condition_id} 的 condition 不匹配："
                f"{condition_name!r} != "
                f"{expected_definition['condition']!r}"
            )

        if condition_type != expected_definition["condition_type"]:
            condition_id_mismatches.append(
                f"{condition_id} 的 condition_type 不匹配："
                f"{condition_type!r} != "
                f"{expected_definition['condition_type']!r}"
            )

    expected_ids = set(expected_by_id)
    actual_id_set = set(actual_ids)

    for missing_id in sorted(expected_ids - actual_id_set):
        condition_id_mismatches.append(
            f"缺少 Runtime Rule 定义的 condition_id：{missing_id}"
        )

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
        for item in expected_required_conditions
        if item not in actual_required_names
    ]

    missing_exclusion = [
        item
        for item in expected_exclusion_conditions
        if item not in actual_exclusion_names
    ]

    missing_exception = [
        item
        for item in expected_exception_conditions
        if item not in actual_exception_names
    ]

    extra_conditions = [
        name
        for name in all_names
        if name
        and name not in (
            expected_required_conditions
            + expected_exclusion_conditions
            + expected_exception_conditions
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
            expected_total_conditions,

        "expected_required":
            len(
                expected_required_conditions
            ),

        "expected_exclusion":
            len(
                expected_exclusion_conditions
            ),

        "expected_exception":
            len(
                expected_exception_conditions
            ),

        "unknown_types":
            unique_strings(
                unknown_types
            ),

        "invalid_condition_types":
            invalid_condition_types,

        "invalid_statuses":
            invalid_statuses,

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

        "duplicate_condition_ids":
            unique_strings(
                duplicate_ids
            ),

        "condition_id_mismatches":
            unique_strings(
                condition_id_mismatches
            ),
    }

    errors: List[str] = []

    if (
        result["total"]
        != expected_total_conditions
    ):
        errors.append(
            "ConditionResult 总数错误："
            f"{result['total']} != "
            f"{expected_total_conditions}"
        )

    if (
        result["required"]
        != len(
            expected_required_conditions
        )
    ):
        errors.append(
            "REQUIRED 数量错误："
            f"{result['required']} != {len(expected_required_conditions)}"
        )

    if (
        result["exclusion"]
        != len(
            expected_exclusion_conditions
        )
    ):
        errors.append(
            "EXCLUSION 数量错误："
            f"{result['exclusion']} != {len(expected_exclusion_conditions)}"
        )

    if (
        result["exception"]
        != len(
            expected_exception_conditions
        )
    ):
        errors.append(
            "EXCEPTION 数量错误："
            f"{result['exception']} != {len(expected_exception_conditions)}"
        )

    if result["invalid_condition_types"]:
        errors.append(
            "存在非法原始 ConditionResult.condition_type："
            + "; ".join(result["invalid_condition_types"])
        )

    if result["unknown_types"]:
        errors.append(
            "存在未知 condition_type："
            + ", ".join(
                result["unknown_types"]
            )
        )

    if result["invalid_statuses"]:
        errors.append(
            "存在非法 ConditionResult.status："
            + "; ".join(
                result["invalid_statuses"]
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

    if result["duplicate_condition_ids"]:
        errors.append(
            "存在重复 condition_id："
            + ", ".join(
                result["duplicate_condition_ids"]
            )
        )

    if result["condition_id_mismatches"]:
        errors.append(
            "Condition ID 身份映射错误："
            + "; ".join(
                result["condition_id_mismatches"]
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


def validate_condition_structure(
    decision: Any,
    strict: bool = True,
) -> Dict[str, Any]:
    """
    校验当前 Runtime Rule 与 ConditionResult 的结构完整性。

    strict=True：
        保留原有行为，发现无效结构时抛出 ValueError。

    strict=False：
        返回 valid / errors；包括 Runtime Rule 前置结构
        无法解析的情况，不将异常误报为校验通过。
    """

    if strict:
        return _validate_condition_structure_impl(
            decision,
            strict=True,
        )

    try:
        return _validate_condition_structure_impl(
            decision,
            strict=False,
        )
    except (ValueError, TypeError, KeyError, AttributeError) as exc:
        return {
            "valid": False,
            "errors": [
                f"Runtime Rule / ConditionResult 结构无法完成校验：{exc}"
            ],
            "total": 0,
            "required": 0,
            "exclusion": 0,
            "exception": 0,
            "expected_total": None,
            "expected_required": None,
            "expected_exclusion": None,
            "expected_exception": None,
            "unknown_types": [],
            "invalid_condition_types": [],
            "invalid_statuses": [],
            "duplicate_conditions": [],
            "missing_required": [],
            "missing_exclusion": [],
            "missing_exception": [],
            "extra_conditions": [],
            "duplicate_condition_ids": [],
            "condition_id_mismatches": [],
        }


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

    validation_result = validate_condition_structure(
        decision,
        strict=strict,
    )

    if not validation_result["valid"]:
        errors = validation_result.get("errors", [])
        error_text = "\n".join(
            f"  - {error}"
            for error in errors
        )

        raise ValueError(
            "Builder 拒绝构建无效的 ConditionResult 结构：\n"
            + error_text
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

    selected_rule = get_value(
        decision,
        "selected_rule",
        {},
    )

    if not isinstance(selected_rule, dict):
        raise ValueError(
            "DecisionResult.selected_rule 必须是 Runtime Rule dict。"
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

        selected_rule=deepcopy(selected_rule),

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

