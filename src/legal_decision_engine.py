# -*- coding: utf-8 -*-

"""
RAG V7
Legal Decision Engine

============================================================
功能
============================================================

Legal Retriever
      ↓
Structured Articles
      ↓
Legal Fact Extractor
      ↓
LegalFacts
      ↓
Legal Decision Engine
      ↓
DecisionResult
      ↓
Legal Answer Builder
      ↓
Ollama
      ↓
Final Legal Answer

============================================================
V7 核心原则
============================================================

1. Decision Engine 只负责法律条件判断。

2. Decision Engine 不负责：
       - 生成最终法律答案
       - 调用 Ollama
       - 组织最终自然语言回复
       - 从用户问题中重新扫描事实

3. 用户自然语言事实由：

       legal_fact_extractor.py

   负责提取为：

       LegalFacts

4. Decision Engine 只消费 LegalFacts。

5. Article 14 的核心条件必须保持结构化。

6. 用户事实：

       公司连续签订三次固定期限劳动合同

   可以证明：

       - 连续订立二次固定期限劳动合同
       - 存在后续订立的劳动合同

   但不能自动证明：

       - 续订劳动合同
       - 劳动者提出或者同意续订、订立劳动合同
       - 不存在第39条情形
       - 不存在第40条第一项情形
       - 不存在第40条第二项情形
       - 劳动者没有提出订立固定期限劳动合同

7. “准备续订”“计划续订”“打算续订”
   不能等同于“已经续订”。

8. “劳动者同意续订”
   可以证明劳动者同意，
   但不能自动证明已经完成续订。

9. UNKNOWN 不能自动升级为 SATISFIED。

10. REQUIRED 条件存在 NOT_SATISFIED：
       → NOT_ESTABLISHED

11. EXCLUSION 条件存在 SATISFIED：
       → 表示排除条件已经触发
       → NOT_ESTABLISHED

12. EXCEPTION 条件存在 SATISFIED：
       → 表示例外已经触发
       → NOT_ESTABLISHED

13. 没有 NOT_SATISFIED，
    但存在 UNKNOWN：
       → CONDITIONAL

14. 全部条件 SATISFIED：
       → DEFINITE

15. 组合否定事实必须保持完整语义：

       不存在劳动合同法第三十九条和
       第四十条第一项、第二项规定的情形

   应同时证明：

       - 不存在第三十九条规定的情形
       - 不存在第四十条第一项规定的情形
       - 不存在第四十条第二项规定的情形

   不能因为三个法律条件在一句话中被合并表达，
   就将其中两个或者三个条件错误标记为 UNKNOWN。

============================================================
V7 Fact → Relationship → Condition 迁移
============================================================

事实层：

    用户问题
       ↓
    extract_legal_facts()
       ↓
    LegalFacts

判定层：

    LegalFacts
       ↓
    match_condition()
       ↓
    ConditionResult

其中：

    REQUIRED 1
        → facts.contract_sequence

    REQUIRED 2
        → facts.contract_sequence
        → facts.completed_renewal

    REQUIRED 3
        → facts.completed_renewal

    REQUIRED 4
        → facts.worker_agreement

    Article 39
        → facts.article_39

    Article 40(1)
        → facts.article_40_1

    Article 40(2)
        → facts.article_40_2

    EXCEPTION
        → facts.fixed_term_exception

注意：

    LegalFacts 中：

        True
            = 用户明确陈述事实存在

        False
            = 用户明确陈述事实不存在

        None
            = 用户没有明确陈述

    None 不得被 Engine 自动升级为 True。

============================================================
"""


from __future__ import annotations

from copy import deepcopy

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

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from src.legal_common import (
    normalize_text,
    unique_texts,
)


from src.legal_rule_selector import (
    select_rule_from_articles,
)

from src.legal_runtime_rule_adapter import (
    canonical_rule_to_runtime_rule,
)



from src.legal_fact_models import (
    ContractSequence,
    LegalFacts,
    validate_legal_facts_runtime,
)

from src.legal_fact_extractor import (
    extract_legal_facts,
    extract_explicit_facts,
    extract_contract_sequence,
)




# ============================================================
# Version
# ============================================================

ENGINE_VERSION = "V6.1"


# ============================================================
# Condition Status
# ============================================================





# ============================================================
# Condition Type
# ============================================================





# ============================================================
# Decision Status
# ============================================================





# ============================================================
# Legal Sources
# ============================================================



LABOR_CONTRACT_LAW_ARTICLE_39 = "第三十九条"

LABOR_CONTRACT_LAW_ARTICLE_40 = "第四十条"

IMPLEMENTING_REGULATIONS = (
    "中华人民共和国劳动合同法实施条例"
)


# ============================================================
# Article 14 Conditions
# ============================================================

# ============================================================
# Canonical Conditions
# ============================================================
#
# Article 14 的 Canonical Condition Identity 统一由
# legal_rule_registry.py 提供。
#
# 保留本模块原有的条件常量名称，避免修改后续 Decision
# Engine 判定逻辑；但条件的唯一来源改为 Rule Registry。
# ============================================================





# ============================================================
# Combined Negative Patterns
# ============================================================




# ============================================================
# Dataclass
# ============================================================

@dataclass
class ConditionResult:
    """
    单项法律条件判断结果。

    V6.2：

        condition_id：
            稳定的机器条件身份。

            用于：
                - 条件唯一识别
                - 条件级数据流追踪
                - 防止依赖位置判断
                - 后续 ConditionResult 跨模块传递

        condition：
            法律条件原文。

            用于：
                - 法律语义展示
                - 兼容 V6.1 既有调用
                - Answer Builder / Validator 等旧接口

        condition_type：
            REQUIRED / EXCLUSION / EXCEPTION

    重要原则：

        condition_id 是机器身份。
        condition 是法律文本。
        condition_type 是法律条件类别。

        三者职责不同，不互相替代。
    """

    condition_id: str

    condition: str

    status: str

    reason: str

    condition_type: str

    @property
    def type(self) -> str:
        """
        兼容旧调用。
        """

        return self.condition_type

    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典。

        V6.2：

            condition_id 必须随 ConditionResult
            一起向下游传播。

        同时保留 V6.1 原有字段，
        避免破坏现有消费者。
        """

        return {
            "condition_id": self.condition_id,
            "condition": self.condition,
            "status": self.status,
            "reason": self.reason,
            "condition_type": self.condition_type,
        }


@dataclass
class RuleDependency:
    """
    用户事实与法律规则之间的依赖关系。

    satisfied_by_fact：
        用户事实可以直接证明的法律条件。

    not_proven_by_fact：
        用户事实不能直接证明的法律条件。
    """

    rule_name: str

    satisfied_by_fact: List[str] = field(
        default_factory=list
    )

    not_proven_by_fact: List[str] = field(
        default_factory=list
    )

    explanation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典。
        """

        return {
            "rule_name": self.rule_name,
            "satisfied_by_fact": list(
                self.satisfied_by_fact
            ),
            "not_proven_by_fact": list(
                self.not_proven_by_fact
            ),
            "explanation": self.explanation,
        }


@dataclass
class DecisionResult:
    """
    Legal Decision Engine 最终结构化输出。

    注意：

        DecisionResult 只表达法律条件判断结果，
        不负责生成最终法律答案。
    """

    decision: str

    condition_results: List[ConditionResult]

    explicit_facts: List[str]

    contract_sequence: Optional[ContractSequence]

    rule_dependencies: List[RuleDependency]

    selected_rule: Dict[str, Any]

    explanation: str

    engine_version: str = ENGINE_VERSION

    # 决策创建时记录的规则身份；不加入 to_dict() 输出。
    selected_rule_id: Optional[str] = None

    @property
    def satisfied_conditions(self) -> List[str]:
        """
        获取已经满足的条件。
        """

        return [
            item.condition
            for item in self.condition_results
            if item.status == SATISFIED
        ]

    @property
    def unknown_conditions(self) -> List[str]:
        """
        获取尚不确定的条件。
        """

        return [
            item.condition
            for item in self.condition_results
            if item.status == UNKNOWN
        ]

    @property
    def not_satisfied_conditions(self) -> List[str]:
        """
        获取所有未满足条件。

        保留 V6.0-16 原有接口。

        如需区分语义，应使用：

            required_not_satisfied_conditions
            triggered_exclusion_conditions
            triggered_exception_conditions
        """

        return [
            item.condition
            for item in self.condition_results
            if item.status == NOT_SATISFIED
        ]

    @property
    def required_not_satisfied_conditions(
        self,
    ) -> List[str]:
        """
        获取未满足的 REQUIRED 条件。

        注意：
        REQUIRED 的 NOT_SATISFIED 表示必备条件没有满足，
        与 EXCLUSION / EXCEPTION 的 NOT_SATISFIED 语义不同。
        """

        return [
            item.condition
            for item in self.condition_results
            if (
                item.condition_type == REQUIRED
                and item.status == NOT_SATISFIED
            )
        ]

    @property
    def triggered_exclusion_conditions(
        self,
    ) -> List[str]:
        """
        获取已经触发的 EXCLUSION 条件。

        EXCLUSION 的 SATISFIED 表示排除情形已经成立，
        因此该条件已经触发。

        EXCLUSION 的 NOT_SATISFIED 表示排除情形不存在，
        因此该条件没有触发。
        """

        return [
            item.condition
            for item in self.condition_results
            if (
                item.condition_type == EXCLUSION
                and item.status == SATISFIED
            )
        ]

    @property
    def triggered_exception_conditions(
        self,
    ) -> List[str]:
        """
        获取已经触发的 EXCEPTION 条件。

        EXCEPTION 的 SATISFIED 表示例外情形已经成立，
        因此该例外条件已经触发。

        EXCEPTION 的 NOT_SATISFIED 表示例外情形不存在，
        因此该例外条件没有触发。
        """

        return [
            item.condition
            for item in self.condition_results
            if (
                item.condition_type == EXCEPTION
                and item.status == SATISFIED
            )
        ]

    @property
    def required_results(
        self,
    ) -> List[ConditionResult]:
        """
        获取 REQUIRED 条件。
        """

        return [
            item
            for item in self.condition_results
            if item.condition_type == REQUIRED
        ]

    @property
    def exclusion_results(
        self,
    ) -> List[ConditionResult]:
        """
        获取 EXCLUSION 条件。
        """

        return [
            item
            for item in self.condition_results
            if item.condition_type == EXCLUSION
        ]

    @property
    def exception_results(
        self,
    ) -> List[ConditionResult]:
        """
        获取 EXCEPTION 条件。
        """

        return [
            item
            for item in self.condition_results
            if item.condition_type == EXCEPTION
        ]

    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典。
        """

        return {
            "decision": self.decision,

            "condition_results": [
                item.to_dict()
                for item in self.condition_results
            ],

            "explicit_facts": list(
                self.explicit_facts
            ),

            "contract_sequence": (
                self.contract_sequence.to_dict()
                if self.contract_sequence
                else None
            ),

            "rule_dependencies": [
                item.to_dict()
                for item in self.rule_dependencies
            ],

            "selected_rule": deepcopy(self.selected_rule),

            "explanation": self.explanation,

            "engine_version": self.engine_version,

            "satisfied_conditions":
                self.satisfied_conditions,

            "unknown_conditions":
                self.unknown_conditions,

            "not_satisfied_conditions":
                self.not_satisfied_conditions,

            "required_not_satisfied_conditions":
                self.required_not_satisfied_conditions,

            "triggered_exclusion_conditions":
                self.triggered_exclusion_conditions,

            "triggered_exception_conditions":
                self.triggered_exception_conditions,
        }


# ============================================================
# Text Helpers
# ============================================================




# ============================================================
# Rule Dependency
# ============================================================

def build_rule_dependency(
    condition_results: List[ConditionResult],
    rule: Dict[str, Any],
) -> RuleDependency:
    """
    根据 Decision Engine 已经产生的 ConditionResult
    建立 RuleDependency。

    V7 原则：

        build_rule_dependency() 只负责结果汇总。

        不负责：
            - 重新读取 LegalFacts
            - 重新判断 ContractSequence
            - 重新推导 Article 14 条件
            - 根据合同次数推导法律关系
            - 生成第二套 ConditionResult

    唯一法律条件判断来源：

        Canonical Relationship
            ↓
        match_condition()
            ↓
        ConditionResult
            ↓
        build_rule_dependency()
    """

    if not isinstance(
        condition_results,
        list,
    ):
        raise ValueError(
            "condition_results 必须是 list。"
        )

    if not isinstance(
        rule,
        dict,
    ):
        raise ValueError(
            "rule 必须是 dict。"
        )

    satisfied_by_fact: List[str] = []
    not_proven_by_fact: List[str] = []

    for result in condition_results:

        if not isinstance(
            result,
            ConditionResult,
        ):
            raise ValueError(
                "condition_results 中的每一项 "
                "必须是 ConditionResult。"
            )

        condition = str(
            result.condition
        ).strip()

        if not condition:
            continue

        if result.status == SATISFIED:
            satisfied_by_fact.append(
                condition
            )
        else:
            not_proven_by_fact.append(
                condition
            )

    rule_name = str(
        rule.get(
            "rule_name",
            rule.get(
                "rule_id",
                "",
            ),
        )
    ).strip()

    if not rule_name:
        rule_name = "未命名法律规则"

    if not_proven_by_fact:
        explanation = (
            "RuleDependency 由 Decision Engine "
            "已经产生的 ConditionResult 汇总生成；"
            "当前仍存在未被事实充分证明的法律条件。"
        )
    else:
        explanation = (
            "RuleDependency 由 Decision Engine "
            "已经产生的 ConditionResult 汇总生成；"
            "当前条件均已获得明确状态。"
        )

    return RuleDependency(
        rule_name=rule_name,
        satisfied_by_fact=unique_texts(
            satisfied_by_fact
        ),
        not_proven_by_fact=unique_texts(
            not_proven_by_fact
        ),
        explanation=explanation,
    )


# ============================================================
# V7 Generic Predicate Evaluation
# ============================================================

def _get_fact_value(
    facts: LegalFacts,
    fact_key: str,
):
    """
    根据 Canonical Predicate 的 fact_key
    从 LegalFacts 中读取事实。

    支持：

        普通字段：
            article_39
            article_40_1
            article_40_2
            completed_renewal
            worker_agreement
            fixed_term_exception

        嵌套字段：
            contract_sequence.count
            contract_sequence.term_type
            contract_sequence.continuous

    None 必须原样返回。
    """

    current = facts

    for part in str(
        fact_key
    ).split("."):

        if current is None:
            return None

        if isinstance(
            current,
            dict,
        ):
            current = current.get(
                part
            )
            continue

        if not hasattr(
            current,
            part,
        ):
            return None

        current = getattr(
            current,
            part,
        )

    return current


def _evaluate_predicate(
    facts: LegalFacts,
    predicate: Dict[str, Any],
) -> bool:
    """
    执行单个 Canonical Predicate。

    V7 当前只允许：

        ==
        >=

    注意：

        fact == None

    不会被自动解释为 True。

    对 >=：

        None
            → False

    """

    fact_key = str(
        predicate.get(
            "fact_key",
            "",
        )
    ).strip()

    operator = str(
        predicate.get(
            "operator",
            "",
        )
    ).strip()

    expected_value = predicate.get(
        "value"
    )

    if not fact_key:
        raise ValueError(
            "Canonical Predicate 缺少 fact_key。"
        )

    if operator not in {
        "==",
        ">=",
    }:
        raise ValueError(
            "Canonical Predicate 使用非法 operator："
            f"{operator}"
        )

    actual_value = _get_fact_value(
        facts,
        fact_key,
    )

    if operator == "==":
        return actual_value == expected_value

    if actual_value is None:
        return False

    return actual_value >= expected_value


def _evaluate_predicate_group(
    facts: LegalFacts,
    predicate_group: Dict[str, Any],
) -> bool:
    """
    执行一个 Predicate Group。

    当前 Canonical Schema：

        match = ALL

    因此 Group 内：

        predicate1 AND predicate2 AND ...

    """

    match_mode = str(
        predicate_group.get(
            "match",
            "",
        )
    ).strip()

    if match_mode != "ALL":
        raise ValueError(
            "当前 V7 Predicate Group 只允许 "
            "match='ALL'。"
        )

    predicates = predicate_group.get(
        "predicates",
        [],
    )

    if not isinstance(
        predicates,
        list,
    ):
        raise ValueError(
            "predicate_group.predicates 必须是 list。"
        )

    if not predicates:
        raise ValueError(
            "Predicate Group 不允许为空。"
        )

    return all(
        _evaluate_predicate(
            facts,
            predicate,
        )
        for predicate in predicates
    )


def _evaluate_relationship(
    facts: LegalFacts,
    relationship: Dict[str, Any],
) -> bool:
    """
    判断一个 Canonical Relationship 是否被当前事实组满足。

    Predicate Groups 之间为 OR：

        Group 1 OR Group 2 OR ...

    注意：

        这里的 True 只表示：
        “该 Predicate Group 被事实满足”。

        最终 ConditionResult.status
        仍由 relationship_type 决定。
    """

    predicate_groups = relationship.get(
        "predicate_groups",
        [],
    )

    if not isinstance(
        predicate_groups,
        list,
    ):
        raise ValueError(
            "Relationship predicate_groups 必须是 list。"
        )

    if not predicate_groups:
        raise ValueError(
            "Relationship 不允许没有 predicate_groups。"
        )

    return any(
        _evaluate_predicate_group(
            facts,
            group,
        )
        for group in predicate_groups
    )


def _get_condition_relationships(
    relationships: List[Dict[str, Any]],
    condition_id: str,
) -> List[Dict[str, Any]]:
    """
    从 Canonical Relationship 集合中取得
    当前 Condition 的全部 Relationship。
    """

    matched = [
        relationship
        for relationship in relationships
        if relationship.get(
            "condition_id"
        ) == condition_id
    ]

    if not matched:
        raise ValueError(
            "Runtime Rule 缺少当前 Condition 的 "
            "Canonical Relationship："
            f"{condition_id}"
        )

    return matched


def _evaluate_condition_from_relationships(
    facts: LegalFacts,
    condition_id: str,
    relationships: List[Dict[str, Any]],
) -> Tuple[str, str]:
    """
    根据当前条件的全部命中 Relationship 计算结果。

    语义：
        PROVES_TRUE     -> SATISFIED
        PROVES_FALSE    -> NOT_SATISFIED
        DOES_NOT_PROVE  -> UNKNOWN

    多条关系命中时：
        - 结果状态一致：允许，使用第一条命中的解释。
        - 结果状态冲突：抛出 ValueError。
        - 没有关系命中：返回 UNKNOWN。
    """

    matched_relationships = _get_condition_relationships(
        relationships,
        condition_id,
    )

    status_by_type = {
        "PROVES_TRUE": SATISFIED,
        "PROVES_FALSE": NOT_SATISFIED,
        "DOES_NOT_PROVE": UNKNOWN,
    }

    matched_results = []

    for relationship in matched_relationships:
        relationship_type = relationship.get("relationship_type")
        result_status = relationship.get("result_status")

        if relationship_type not in status_by_type:
            raise ValueError(
                "Canonical Relationship 使用非法 "
                f"relationship_type：{relationship_type}"
            )

        expected_status = status_by_type[relationship_type]

        if result_status != expected_status:
            raise ValueError(
                "Canonical Relationship 语义不一致："
                f"relationship_id={relationship.get('relationship_id')}"
                f"\nrelationship_type={relationship_type}"
                f"\nresult_status={result_status}"
                f"\nexpected_status={expected_status}"
            )

        if _evaluate_relationship(facts, relationship):
            matched_results.append(
                (
                    result_status,
                    str(relationship.get("reason", "")),
                    str(relationship.get("relationship_id", "")),
                )
            )

    if not matched_results:
        return (
            UNKNOWN,
            "当前事实不足以证明该法律条件。",
        )

    # UNKNOWN 表示证据不足，不构成反向证据。
    # 只有命中的确定结论同时包含 SATISFIED 和 NOT_SATISFIED，
    # 才属于真正的状态冲突。
    definitive_statuses = {
        result[0]
        for result in matched_results
        if result[0] in {SATISFIED, NOT_SATISFIED}
    }

    if len(definitive_statuses) > 1:
        details = "; ".join(
            f"{relationship_id} -> {status}"
            for status, _, relationship_id in matched_results
        )
        raise ValueError(
            "Canonical Relationship 命中结果冲突："
            f"condition_id={condition_id}；{details}"
        )

    # 优先返回确定结论，避免 UNKNOWN 因 Relationship 顺序而覆盖它。
    for status, reason, _ in matched_results:
        if status in {SATISFIED, NOT_SATISFIED}:
            return status, reason

    # 所有命中结果均为 UNKNOWN。
    return UNKNOWN, matched_results[0][1]



# ============================================================
# Condition Matching
# ============================================================

def match_condition(
    facts: LegalFacts,
    condition_id: str,
    condition: str,
    condition_type: str,
    relationships: List[
        Dict[str, Any]
    ],
) -> ConditionResult:
    """
    对单项法律条件进行判断。

    V7：

        LegalFacts
            ↓
        Canonical Relationship
            ↓
        Generic Predicate Evaluator
            ↓
        ConditionResult

    本函数不再保存 Article 14 的法律条件判断逻辑。

    Article 14 的具体法律关系由：

        Runtime Rule
            ↓
        fact_condition_relationships

    提供。

    relationships 必须由上游 Runtime Rule
    显式传入。

    本函数不负责 Rule Selection，
    也不负责从 Canonical Registry
    获取法律关系。

    注意：

        None 必须保持 UNKNOWN。

        不允许根据合同次数、
        上下文或者自然语言推测，
        自动升级为 SATISFIED。
    """

    if not isinstance(
        relationships,
        list,
    ):
        raise ValueError(
            "fact_condition_relationships 必须是 list。"
        )

    status, relationship_reason = (
        _evaluate_condition_from_relationships(
            facts=facts,
            condition_id=condition_id,
            relationships=relationships,
        )
    )

    if status == SATISFIED:

        reason = (
            relationship_reason
            or
            "Canonical Relationship 已被当前事实满足。"
        )

    elif status == NOT_SATISFIED:

        reason = (
            relationship_reason
            or
            "Canonical Relationship 已被当前事实证明不成立。"
        )

    else:

        reason = (
            relationship_reason
            or
            "当前事实不足以证明该法律条件。"
        )

    return ConditionResult(
        condition_id=condition_id,
        condition=condition,
        status=status,
        reason=reason,
        condition_type=condition_type,
    )



# ============================================================
# Condition Structure Validation
# ============================================================

def validate_condition_structure(
    condition_results: List[ConditionResult],
    rule: Dict[str, Any],
) -> None:
    """
    验证 Runtime Rule 对应的 ConditionResult 结构。

    V6.2：
    当前验证完全依据传入的 Runtime Rule，
    不再固定假设 Article 14 有 8 个条件。

    验证来源：
        rule["condition_definitions"]

    核心原则：
        1. Rule 是当前条件结构的唯一来源。
        2. ConditionResult 必须与 Rule 的
           condition_definitions 完全一致。
        3. REQUIRED / EXCLUSION / EXCEPTION
           的数量由 Runtime Rule 动态计算。
    """

    # ========================================================
    # ConditionResult Runtime Type Contract
    # 必须先校验结果对象和字段类型，再访问字段或进行结构比较。
    # ========================================================

    if not isinstance(condition_results, list):
        raise TypeError(
            "condition_results 必须是 list。"
        )

    for index, item in enumerate(condition_results):
        if not isinstance(item, ConditionResult):
            raise TypeError(
                "condition_results "
                f"第 {index + 1} 项必须是 ConditionResult，"
                f"实际类型为 {type(item).__name__}。"
            )

        field_types = {
            "condition_id": item.condition_id,
            "condition": item.condition,
            "status": item.status,
            "reason": item.reason,
            "condition_type": item.condition_type,
        }

        for field_name, field_value in field_types.items():
            if not isinstance(field_value, str):
                raise TypeError(
                    f"ConditionResult.{field_name} 必须是字符串："
                    f"index={index}, "
                    f"actual_type={type(field_value).__name__}"
                )

        if not item.condition_id.strip():
            raise ValueError(
                "ConditionResult.condition_id 不能为空字符串："
                f"index={index}"
            )

        if not item.condition.strip():
            raise ValueError(
                "ConditionResult.condition 不能为空字符串："
                f"condition_id={item.condition_id}"
            )

        if item.status not in {
            SATISFIED,
            NOT_SATISFIED,
            UNKNOWN,
        }:
            raise ValueError(
                "ConditionResult 存在非法 status："
                f"condition_id={item.condition_id}, "
                f"status={item.status!r}"
            )

        if item.condition_type not in {
            REQUIRED,
            EXCLUSION,
            EXCEPTION,
        }:
            raise ValueError(
                "ConditionResult 存在非法 condition_type："
                f"condition_id={item.condition_id}, "
                f"condition_type={item.condition_type!r}"
            )

    if not isinstance(rule, dict):
        raise ValueError(
            "Runtime Rule 必须是 dict。"
        )

    canonical_condition_definitions = rule.get(
        "condition_definitions",
        [],
    )

    if not isinstance(canonical_condition_definitions, list):
        raise ValueError(
            "Runtime Rule 的 condition_definitions 必须是 list。"
        )

    if not canonical_condition_definitions:
        raise ValueError(
            "Runtime Rule 缺少 condition_definitions。"
        )

    # ========================================================
    # Runtime Rule → Expected Condition Structure
    # ========================================================

    expected_condition_ids = []
    expected_conditions = []
    expected_condition_types = []

    for index, definition in enumerate(
        canonical_condition_definitions
    ):
        if not isinstance(definition, dict):
            raise ValueError(
                "Runtime Rule 的 condition_definitions "
                f"第 {index + 1} 项必须是 dict。"
            )

        condition_id = str(
            definition.get("condition_id", "")
        ).strip()

        condition = str(
            definition.get("condition", "")
        ).strip()

        condition_type = str(
            definition.get("condition_type", "")
        ).strip()

        if not condition_id:
            raise ValueError(
                "Runtime Rule 存在缺少 condition_id 的条件定义。"
            )

        if not condition:
            raise ValueError(
                f"Runtime Rule 条件 {condition_id} 缺少 condition。"
            )

        if condition_type not in {
            "REQUIRED",
            "EXCLUSION",
            "EXCEPTION",
        }:
            raise ValueError(
                f"Runtime Rule 条件 {condition_id} "
                f"存在非法 condition_type：{condition_type}"
            )

        expected_condition_ids.append(condition_id)
        expected_conditions.append(condition)
        expected_condition_types.append(condition_type)

    expected_count = len(canonical_condition_definitions)

    # ========================================================
    # Expected Condition ID 必须唯一
    # ========================================================

    if len(set(expected_condition_ids)) != expected_count:
        raise ValueError(
            "Runtime Rule 的 condition_id 存在重复。"
        )

    # ========================================================
    # ConditionResult 数量
    # ========================================================

    if len(condition_results) != expected_count:
        raise ValueError(
            "ConditionResult 数量与 Runtime Rule "
            f"condition_definitions 数量不一致："
            f"expected={expected_count}, "
            f"actual={len(condition_results)}"
        )

    # ========================================================
    # Condition Type 数量
    # ========================================================

    expected_required_count = expected_condition_types.count(
        "REQUIRED"
    )
    expected_exclusion_count = expected_condition_types.count(
        "EXCLUSION"
    )
    expected_exception_count = expected_condition_types.count(
        "EXCEPTION"
    )

    required_results = [
        item
        for item in condition_results
        if item.condition_type == "REQUIRED"
    ]

    exclusion_results = [
        item
        for item in condition_results
        if item.condition_type == "EXCLUSION"
    ]

    exception_results = [
        item
        for item in condition_results
        if item.condition_type == "EXCEPTION"
    ]

    if len(required_results) != expected_required_count:
        raise ValueError(
            "REQUIRED ConditionResult 数量与 Runtime Rule 不一致："
            f"expected={expected_required_count}, "
            f"actual={len(required_results)}"
        )

    if len(exclusion_results) != expected_exclusion_count:
        raise ValueError(
            "EXCLUSION ConditionResult 数量与 Runtime Rule 不一致："
            f"expected={expected_exclusion_count}, "
            f"actual={len(exclusion_results)}"
        )

    if len(exception_results) != expected_exception_count:
        raise ValueError(
            "EXCEPTION ConditionResult 数量与 Runtime Rule 不一致："
            f"expected={expected_exception_count}, "
            f"actual={len(exception_results)}"
        )

    # ========================================================
    # ConditionResult ID 必须完整且顺序一致
    # ========================================================

    actual_condition_ids = [
        str(item.condition_id).strip()
        for item in condition_results
    ]

    if any(
        not condition_id
        for condition_id in actual_condition_ids
    ):
        raise ValueError(
            "ConditionResult 存在缺少 condition_id 的结果。"
        )

    if len(set(actual_condition_ids)) != expected_count:
        raise ValueError(
            "ConditionResult 的 condition_id 存在重复。"
        )

    if actual_condition_ids != expected_condition_ids:
        raise ValueError(
            "ConditionResult condition_id 顺序或集合 "
            "与 Runtime Rule 不一致。"
            f"\nexpected={expected_condition_ids}"
            f"\nactual={actual_condition_ids}"
        )

    # ========================================================
    # condition / condition_type 必须与 Rule 完全一致
    # ========================================================

    expected_by_id = {
        condition_id: (
            condition,
            condition_type,
        )
        for condition_id, condition, condition_type in zip(
            expected_condition_ids,
            expected_conditions,
            expected_condition_types,
        )
    }

    for item in condition_results:
        condition_id = str(
            item.condition_id
        ).strip()

        expected_condition, expected_type = (
            expected_by_id[condition_id]
        )

        actual_condition = str(
            item.condition
        ).strip()

        actual_type = str(
            item.condition_type
        ).strip()

        if actual_condition != expected_condition:
            raise ValueError(
                "ConditionResult condition 与 Runtime Rule 不一致："
                f"condition_id={condition_id}"
                f"\nexpected={expected_condition}"
                f"\nactual={actual_condition}"
            )

        if actual_type != expected_type:
            raise ValueError(
                "ConditionResult condition_type 与 Runtime Rule 不一致："
                f"condition_id={condition_id}"
                f"\nexpected={expected_type}"
                f"\nactual={actual_type}"
            )

    # ========================================================
    # 条件名称完整性
    # ========================================================

    names = [
        str(item.condition).strip()
        for item in condition_results
    ]

    if len(set(names)) != expected_count:
        raise ValueError(
            "ConditionResult 存在重复条件。"
        )

    if set(names) != set(expected_conditions):
        raise ValueError(
            "ConditionResult 条件集合与 Runtime Rule "
            "condition_definitions 不一致。"
        )

def validate_runtime_rule_relationships(
    rule: Dict[str, Any],
) -> None:
    """
    验证 Runtime Rule 的通用结构。

    不依赖 Article 14 的固定条件数量或特定条件 ID。
    """

    if not isinstance(rule, dict):
        raise ValueError("Runtime Rule 必须是 dict。")

    if "condition_definitions" not in rule:
        raise ValueError(
            "Runtime Rule 缺少 condition_definitions。"
        )

    condition_definitions = rule["condition_definitions"]

    if not isinstance(condition_definitions, list):
        raise ValueError(
            "Runtime Rule 的 condition_definitions 必须是 list。"
        )

    if not condition_definitions:
        raise ValueError(
            "Runtime Rule 的 condition_definitions 不能为空。"
        )

    condition_ids = set()

    valid_condition_types = {
        "REQUIRED",
        "EXCLUSION",
        "EXCEPTION",
    }

    for definition_index, definition in enumerate(condition_definitions):
        if not isinstance(definition, dict):
            raise ValueError(
                "condition_definitions 中的每一项必须是 dict。"
            )

        condition_id = definition.get("condition_id")
        condition = definition.get("condition")
        condition_type = definition.get("condition_type")

        if not isinstance(condition_id, str) or not condition_id.strip():
            raise ValueError(
                "condition_definitions 中存在非法 condition_id。"
            )

        if not isinstance(condition, str) or not condition.strip():
            raise ValueError(
                "condition_definitions 中存在非法 condition："
                f"index={definition_index}"
            )

        if (
            not isinstance(condition_type, str)
            or condition_type not in valid_condition_types
        ):
            raise ValueError(
                "condition_definitions 中存在非法 condition_type："
                f"condition_id={condition_id}, "
                f"condition_type={condition_type!r}"
            )

        condition_id = condition_id.strip()

        if condition_id in condition_ids:
            raise ValueError(
                "Runtime Rule 存在重复 condition_id："
                f"{condition_id}"
            )

        condition_ids.add(condition_id)

    if "fact_condition_relationships" not in rule:
        raise ValueError(
            "Runtime Rule 缺少 fact_condition_relationships。"
        )

    relationships = rule["fact_condition_relationships"]

    if not isinstance(relationships, list):
        raise ValueError(
            "fact_condition_relationships 必须是 list。"
        )

    if not relationships:
        raise ValueError(
            "fact_condition_relationships 不能为空。"
        )

    valid_semantics = {
        "PROVES_TRUE": "SATISFIED",
        "PROVES_FALSE": "NOT_SATISFIED",
        "DOES_NOT_PROVE": "UNKNOWN",
    }
    valid_operators = {"==", ">="}

    relationship_ids = set()
    covered_condition_ids = set()

    for relationship in relationships:
        if not isinstance(relationship, dict):
            raise ValueError(
                "fact_condition_relationships 中的每一项必须是 dict。"
            )

        relationship_id = relationship.get("relationship_id")

        if not isinstance(relationship_id, str) or not relationship_id.strip():
            raise ValueError(
                "Relationship 存在非法 relationship_id。"
            )

        relationship_id = relationship_id.strip()

        if relationship_id in relationship_ids:
            raise ValueError(
                "Runtime Rule 存在重复 relationship_id："
                f"{relationship_id}"
            )

        relationship_ids.add(relationship_id)

        reason = relationship.get("reason")

        if not isinstance(reason, str) or not reason.strip():
            raise ValueError(
                "Runtime Relationship 的 reason 必须是非空字符串："
                f"relationship_id={relationship_id}"
            )

        condition_id = relationship.get("condition_id")

        if not isinstance(condition_id, str) or not condition_id.strip():
            raise ValueError(
                "Relationship 存在非法 condition_id："
                f"{relationship_id}"
            )

        condition_id = condition_id.strip()

        if condition_id not in condition_ids:
            raise ValueError(
                "Relationship 引用了 Runtime Rule 中不存在的 "
                f"condition_id：{condition_id}"
            )

        covered_condition_ids.add(condition_id)

        relationship_type = relationship.get("relationship_type")
        result_status = relationship.get("result_status")
        expected_status = valid_semantics.get(relationship_type)

        if expected_status is None:
            raise ValueError(
                "Relationship 使用非法 relationship_type："
                f"{relationship_type}"
            )

        if result_status != expected_status:
            raise ValueError(
                "Relationship 类型与结果状态不一致："
                f"relationship_id={relationship_id}"
                f"\nrelationship_type={relationship_type}"
                f"\nresult_status={result_status}"
                f"\nexpected_status={expected_status}"
            )

        predicate_groups = relationship.get("predicate_groups")

        if not isinstance(predicate_groups, list) or not predicate_groups:
            raise ValueError(
                "Relationship predicate_groups 必须是非空 list："
                f"{relationship_id}"
            )

        for group_index, group in enumerate(predicate_groups):
            if not isinstance(group, dict):
                raise ValueError(
                    "Predicate Group 必须是 dict："
                    f"{relationship_id}[{group_index}]"
                )

            if group.get("match") != "ALL":
                raise ValueError(
                    "Predicate Group 只允许 match='ALL'："
                    f"{relationship_id}[{group_index}]"
                )

            predicates = group.get("predicates")

            if not isinstance(predicates, list) or not predicates:
                raise ValueError(
                    "Predicate Group 的 predicates 必须是非空 list："
                    f"{relationship_id}[{group_index}]"
                )

            for predicate_index, predicate in enumerate(predicates):
                location = (
                    f"{relationship_id}"
                    f"[{group_index}][{predicate_index}]"
                )

                if not isinstance(predicate, dict):
                    raise ValueError(
                        f"Predicate 必须是 dict：{location}"
                    )

                required_predicate_keys = {
                    "fact_key",
                    "operator",
                    "value",
                }

                if not required_predicate_keys.issubset(predicate):
                    raise ValueError(
                        f"Predicate 缺少必需字段：{location}"
                    )

                fact_key = predicate.get("fact_key")
                operator = predicate.get("operator")
                value = predicate.get("value")

                if not isinstance(fact_key, str) or not fact_key.strip():
                    raise ValueError(
                        f"Predicate fact_key 必须是非空字符串：{location}"
                    )

                if not isinstance(operator, str) or operator not in valid_operators:
                    raise ValueError(
                        f"Predicate 使用非法 operator：{location}"
                    )

                if operator == "==":
                    value_is_valid = (
                        type(value) is bool
                        or (
                            isinstance(value, str)
                            and bool(value.strip())
                        )
                    )
                else:
                    # bool 是 int 的子类，必须排除 True / False。
                    value_is_valid = type(value) is int

                if not value_is_valid:
                    raise ValueError(
                        "Predicate value 与 operator 不匹配："
                        f"{location}, operator={operator}, "
                        f"value_type={type(value).__name__}"
                    )

    missing_condition_ids = condition_ids - covered_condition_ids

    if missing_condition_ids:
        raise ValueError(
            "Runtime Rule 存在缺少 Relationship 的条件："
            + ", ".join(sorted(missing_condition_ids))
        )


def _validate_runtime_fact_paths(
    facts: LegalFacts,
    rule: Dict[str, Any],
) -> None:
    """
    根据事实模型的 dataclass 字段声明校验所有 Predicate 路径。

    本函数只验证路径是否存在，不检查事实值是否为 None。

    因此：
        contract_sequence.count
            是合法路径。

        contract_sequence=None
            只表示当前嵌套事实未知，不代表路径无效。

    本函数不依赖 Article 14 的固定字段白名单。
    """

    from dataclasses import fields, is_dataclass
    from types import UnionType
    from typing import Union, get_args, get_origin, get_type_hints

    # 仅接受正式的 LegalFacts 事实模型及其子类。
    # 不能仅凭输入对象是 dataclass，就允许其进入法律事实判定流程。
    if not isinstance(facts, LegalFacts):
        raise ValueError(
            "Runtime Rule 的 fact_key 路径校验要求事实输入使用 "
            "LegalFacts 事实模型；"
            f"actual_type={type(facts).__name__}"
        )

    model_type = type(facts)

    if not is_dataclass(model_type):
        raise ValueError(
            "Runtime Rule 的 fact_key 路径校验要求事实输入使用 "
            "dataclass 事实模型；"
            f"actual_type={model_type.__name__}"
        )

    def unwrap_optional(annotation):
        """去除 Optional / 单一非 None 联合类型的包装。"""
        origin = get_origin(annotation)

        if origin in (Union, UnionType):
            non_none_types = [
                item
                for item in get_args(annotation)
                if item is not type(None)
            ]

            if len(non_none_types) == 1:
                return non_none_types[0]

        return annotation

    def validate_path(fact_key, relationship_id, location):
        """按模型声明逐层校验字段路径。"""
        parts = fact_key.split(".")
        current_type = model_type

        for index, part in enumerate(parts):
            if not is_dataclass(current_type):
                raise ValueError(
                    "Runtime Rule 的 fact_key 路径包含无法继续解析的"
                    "非 dataclass 中间字段："
                    f"fact_key={fact_key!r}, "
                    f"relationship_id={relationship_id!r}, "
                    f"location={location}, "
                    f"model_type={current_type!r}"
                )

            declared_fields = {
                item.name
                for item in fields(current_type)
            }

            if part not in declared_fields:
                raise ValueError(
                    "Runtime Rule 存在无效 fact_key 字段路径："
                    f"fact_key={fact_key!r}, "
                    f"relationship_id={relationship_id!r}, "
                    f"location={location}, "
                    f"model_type={current_type.__name__}, "
                    f"invalid_field={part!r}"
                )

            if index == len(parts) - 1:
                return

            type_hints = get_type_hints(current_type)
            annotation = type_hints.get(part)

            if annotation is None:
                raise ValueError(
                    "Runtime Rule 的 fact_key 中间字段缺少类型声明："
                    f"fact_key={fact_key!r}, "
                    f"relationship_id={relationship_id!r}, "
                    f"field={part!r}"
                )

            current_type = unwrap_optional(annotation)

            if not isinstance(current_type, type):
                raise ValueError(
                    "Runtime Rule 的 fact_key 中间字段类型"
                    "无法用于路径解析："
                    f"fact_key={fact_key!r}, "
                    f"relationship_id={relationship_id!r}, "
                    f"field={part!r}, "
                    f"annotation={annotation!r}"
                )

            if not is_dataclass(current_type):
                raise ValueError(
                    "Runtime Rule 的 fact_key 中间字段不是"
                    "可继续解析的 dataclass 模型："
                    f"fact_key={fact_key!r}, "
                    f"relationship_id={relationship_id!r}, "
                    f"field={part!r}, "
                    f"field_type={current_type.__name__}"
                )

    relationships = rule["fact_condition_relationships"]

    for relationship in relationships:
        relationship_id = relationship["relationship_id"]

        for group_index, group in enumerate(
            relationship["predicate_groups"]
        ):
            for predicate_index, predicate in enumerate(
                group["predicates"]
            ):
                raw_fact_key = predicate["fact_key"]

                location = (
                    f"group_index={group_index}, "
                    f"predicate_index={predicate_index}"
                )

                # 严格拒绝前后空格，避免校验路径与执行路径不一致。
                if raw_fact_key != raw_fact_key.strip():
                    raise ValueError(
                        "Runtime Rule 的 fact_key 不允许包含前后空格："
                        f"fact_key={raw_fact_key!r}, "
                        f"relationship_id={relationship_id!r}, "
                        f"location={location}"
                    )

                fact_key = raw_fact_key

                validate_path(
                    fact_key=fact_key,
                    relationship_id=relationship_id,
                    location=location,
                )


def evaluate_rule(
    facts: LegalFacts,
    rule: Dict[str, Any],
) -> Tuple[
    str,
    List[ConditionResult],
]:
    """
    评估核心法律规则。

    V6.1 第一阶段：

        evaluate_rule() 不再接收 question。

        evaluate_rule() 不再向 match_condition()
        传递原始用户问题。

        唯一事实输入：

            LegalFacts

    V6.0-16：

        REQUIRED / EXCLUSION / EXCEPTION
        的 NOT_SATISFIED 必须保留原始语义。

    决策原则：

        1. REQUIRED 条件存在 NOT_SATISFIED
           → NOT_ESTABLISHED

        2. EXCLUSION 条件存在 SATISFIED
           → NOT_ESTABLISHED

        3. EXCEPTION 条件存在 SATISFIED
           → NOT_ESTABLISHED

        4. 没有上述阻断条件，
           但存在 UNKNOWN
           → CONDITIONAL

        5. 没有阻断条件，
           且不存在 UNKNOWN
           → DEFINITE
    """

    # Engine 接口先拒绝不属于正式事实模型的输入。
    if not isinstance(facts, LegalFacts):
        raise ValueError(
            "事实输入必须是 LegalFacts 事实模型。"
        )

    # 对正式事实模型继续执行完整的运行时字段类型校验。
    validate_legal_facts_runtime(facts)
    validate_runtime_rule_relationships(rule)
    _validate_runtime_fact_paths(facts, rule)

    condition_results: List[
        ConditionResult
    ] = []

    # --------------------------------------------------------
    # V6.2 Stable Condition Identity
    # --------------------------------------------------------
    #
    # Runtime Rule 已经由：
    #
    #     Canonical Definition
    #         ↓
    #     Rule Registry
    #         ↓
    #     Runtime Rule
    #
    # 提供 condition_definitions。
    #
    # 每个 definition 同时包含：
    #
    #     condition_id
    #     condition
    #     condition_type
    #
    # 因此 evaluate_rule() 不再通过：
    #
    #     条件列表中的固定位置
    #
    # 推导条件身份。
    #
    # evaluate_rule() 不负责定义或生成 Stable Condition ID。
    #
    # Stable Condition ID 由 Runtime Rule 提供。
    #
    # match_condition() 仅将 Stable Condition ID
    # 作为已有法律事实判断分支的 dispatch key。
    # --------------------------------------------------------

    condition_definitions = rule.get(
        "condition_definitions",
        [],
    )

    if not isinstance(
        condition_definitions,
        list,
    ):
        raise ValueError(
            "Runtime Rule 的 condition_definitions "
            "必须是 list。"
        )

    if not condition_definitions:
        raise ValueError(
            "Runtime Rule 缺少 condition_definitions，"
            "无法执行 V6.2 Stable Condition Identity。"
        )

    for definition in condition_definitions:

        if not isinstance(
            definition,
            dict,
        ):
            raise ValueError(
                "condition_definitions 中的每一项 "
                "必须是 dict。"
            )

        # Runtime Rule 已在 evaluate_rule() 入口完成严格类型校验。
        # 这里仅保留原有的字符串规范化，不再通过 str() 转换非法类型。
        condition_id = definition["condition_id"].strip()
        condition = definition["condition"].strip()
        condition_type = definition["condition_type"].strip()

        if not condition_id:
            raise ValueError(
                "condition_definitions 中存在空 condition_id。"
            )

        if not condition:
            raise ValueError(
                "condition_definitions 中存在空 condition。"
            )

        if condition_type not in {
            REQUIRED,
            EXCLUSION,
            EXCEPTION,
        }:
            raise ValueError(
                "condition_definitions 中存在非法 "
                f"condition_type: {condition_type}"
            )

        result = match_condition(
            facts=facts,
            condition_id=condition_id,
            condition=condition,
            condition_type=condition_type,
            relationships=rule.get(
                "fact_condition_relationships",
                [],
            ),
        )

        condition_results.append(
            result
        )

    # --------------------------------------------------------
    # Structure Validation
    # --------------------------------------------------------

    validate_condition_structure(
        condition_results,
        rule,
    )

    # --------------------------------------------------------
    # Semantic Decision
    # --------------------------------------------------------

    required_not_satisfied = [
        item
        for item in condition_results
        if (
            item.condition_type == REQUIRED
            and item.status == NOT_SATISFIED
        )
    ]

    triggered_exclusions = [
        item
        for item in condition_results
        if (
            item.condition_type == EXCLUSION
            and item.status == SATISFIED
        )
    ]

    triggered_exceptions = [
        item
        for item in condition_results
        if (
            item.condition_type == EXCEPTION
            and item.status == SATISFIED
        )
    ]

    unknown_results = [
        item
        for item in condition_results
        if item.status == UNKNOWN
    ]

    # --------------------------------------------------------
    # REQUIRED 阻断
    # --------------------------------------------------------

    if required_not_satisfied:

        decision = NOT_ESTABLISHED

    # --------------------------------------------------------
    # EXCLUSION 已触发
    # --------------------------------------------------------

    elif triggered_exclusions:

        decision = NOT_ESTABLISHED

    # --------------------------------------------------------
    # EXCEPTION 已触发
    # --------------------------------------------------------

    elif triggered_exceptions:

        decision = NOT_ESTABLISHED

    # --------------------------------------------------------
    # 仍有 UNKNOWN
    # --------------------------------------------------------

    elif unknown_results:

        decision = CONDITIONAL

    # --------------------------------------------------------
    # 所有条件满足
    # --------------------------------------------------------

    else:

        decision = DEFINITE

    return (
        decision,
        condition_results,
    )


# ============================================================
# Select Core Rule
# ============================================================

def select_core_rule(
    retrieved_articles: Optional[
        List[Dict[str, Any]]
    ] = None,
) -> Dict[str, Any]:
    """
    选择当前请求对应的 Runtime Rule。

    V6.2：

        Retriever Rules
                ↓
        Rule Selector
                ↓
        Canonical Rule
                ↓
        Runtime Rule Adapter
                ↓
        Runtime Rule

    职责边界：

        1. Rule Selector 决定使用哪个 Canonical Rule。
        2. Runtime Adapter 将 Canonical Rule 转换为
           Decision Engine 使用的 Runtime Rule。
        3. 本函数不根据 Article Number 编写法律规则判断。
        4. 本函数不从 Retriever 条件直接构造 Decision Rule。

    V7 Compatibility Boundary：

        本函数保留为 Legacy Compatibility API。

        如果 Retriever 没有匹配到 Canonical Rule，
        必须显式抛出 ValueError。

        不允许在规则选择失败时，
        静默回退到 Article 14。

        V7 Production Pipeline 使用独立的
        build_runtime_rule_from_retrieved_articles()
        完成规则选择与 Runtime Rule 构建。

    注意：

        本函数不再调用 build_core_rule()。
    """

    # ========================================================
    # V7 Legacy Rule Selection Compatibility
    # ========================================================

    canonical_rule = select_rule_from_articles(
        retrieved_articles or []
    )

    if canonical_rule is not None:

        # ----------------------------------------------------
        # Canonical Rule → Runtime Rule
        # ----------------------------------------------------

        return canonical_rule_to_runtime_rule(
            canonical_rule
        )

    # ========================================================
    # V7：显式处理规则选择失败
    # ========================================================

    raise ValueError(
        "Retriever Rules 中没有找到对应的 Canonical Rule"
    )

# ============================================================
# Decision Explanation
# ============================================================

def build_decision_explanation(
    decision: str,
    condition_results: List[ConditionResult],
    contract_sequence: Optional[
        ContractSequence
    ],
) -> str:
    """
    构建结构化 Decision Explanation。

    注意：

        不再把所有 NOT_SATISFIED
        简单合并成“不满足条件”。

    而是区分：

        不满足必备条件=
        已触发排除条件=
        已触发例外条件=
    """

    satisfied = [
        item.condition
        for item in condition_results
        if item.status == SATISFIED
    ]

    unknown = [
        item.condition
        for item in condition_results
        if item.status == UNKNOWN
    ]

    required_not_satisfied = [
        item.condition
        for item in condition_results
        if (
            item.condition_type == REQUIRED
            and item.status == NOT_SATISFIED
        )
    ]

    triggered_exclusions = [
        item.condition
        for item in condition_results
        if (
            item.condition_type == EXCLUSION
            and item.status == SATISFIED
        )
    ]

    triggered_exceptions = [
        item.condition
        for item in condition_results
        if (
            item.condition_type == EXCEPTION
            and item.status == SATISFIED
        )
    ]

    parts: List[str] = []

    parts.append(
        f"Decision={decision}"
    )

    # --------------------------------------------------------
    # Contract Sequence
    # --------------------------------------------------------

    if contract_sequence is not None:

        parts.append(
            "合同序列="
            f"{contract_sequence.count}次"
            f"{contract_sequence.term_type}"
            f"期限，"
            f"连续={contract_sequence.continuous}"
        )

    # --------------------------------------------------------
    # Satisfied
    # --------------------------------------------------------

    if satisfied:

        parts.append(
            "已满足条件="
            + "、".join(satisfied)
        )

    # --------------------------------------------------------
    # Unknown
    # --------------------------------------------------------

    if unknown:

        parts.append(
            "尚不确定条件="
            + "、".join(unknown)
        )

    # --------------------------------------------------------
    # Required Not Satisfied
    # --------------------------------------------------------

    if required_not_satisfied:

        parts.append(
            "不满足必备条件="
            + "、".join(
                required_not_satisfied
            )
        )

    # --------------------------------------------------------
    # Triggered Exclusion
    # --------------------------------------------------------

    if triggered_exclusions:

        parts.append(
            "已触发排除条件="
            + "、".join(
                triggered_exclusions
            )
        )

    # --------------------------------------------------------
    # Triggered Exception
    # --------------------------------------------------------

    if triggered_exceptions:

        parts.append(
            "已触发例外条件="
            + "、".join(
                triggered_exceptions
            )
        )

    return "；".join(parts)


# ============================================================
# Make Decision
# ============================================================

def make_decision(
    question: str,
    rule: Optional[Dict[str, Any]] = None,
    retrieved_articles: Optional[
        List[Dict[str, Any]]
    ] = None,
) -> DecisionResult:
    """
    对法律问题进行结构化判断。

    V6.1 第一阶段：

        用户问题
            ↓
        extract_legal_facts()
            ↓
        LegalFacts
            ↓
        evaluate_rule()
            ↓
        DecisionResult

    V7 Production Boundary：

        Production Pipeline 应通过：

            Retriever
                ↓
            Rule Selector
                ↓
            Canonical Rule
                ↓
            Runtime Rule Adapter
                ↓
            make_decision(rule=runtime_rule)

        因此：

            rule
                是 V7 Production Runtime Rule 入口。

            retrieved_articles
                仅作为 Legacy Compatibility 参数保留，
                用于兼容旧调用方和回归测试。

        Production Pipeline 不应通过
        retrieved_articles 进行 Rule Selection。

    注意：

        本函数只进行一次事实抽取。

        Decision Engine 后续所有条件判断，
        均从同一个 LegalFacts 对象读取。

        不再让 match_condition()
        重新扫描 question。
    """

    normalized_question = normalize_text(
        question
    )

    # --------------------------------------------------------
    # Fact Layer
    # --------------------------------------------------------
    #
    # 唯一事实抽取入口。
    #
    # 后续 Engine 不再重新扫描 question。
    # --------------------------------------------------------

    facts = extract_legal_facts(
        normalized_question
    )

    # 在读取事实字段前检查当前 LegalFacts 的运行时类型。
    validate_legal_facts_runtime(facts)

    # --------------------------------------------------------
    # 从 LegalFacts 获取兼容旧 DecisionResult
    # 字段。
    # --------------------------------------------------------

    explicit_facts = list(
        facts.explicit_facts
    )

    contract_sequence = (
        facts.contract_sequence
    )

    # --------------------------------------------------------
    # Core Rule
    # --------------------------------------------------------

    if rule is not None:
        runtime_rule = rule
    else:
        runtime_rule = select_core_rule(
            retrieved_articles
        )

    # --------------------------------------------------------
    # Decision Engine
    # --------------------------------------------------------
    #
    # 注意：
    #
    # evaluate_rule() 不再接收 question。
    #
    # 所有条件判断统一消费 LegalFacts。
    # --------------------------------------------------------

    (
        decision,
        condition_results,
    ) = evaluate_rule(
        facts=facts,
        rule=runtime_rule,
    )

    # --------------------------------------------------------
    # Rule Dependency
    # --------------------------------------------------------
    #
    # V7：
    #
    # Dependency 只能消费 Decision Engine 已经产生的
    # ConditionResult。
    #
    # 不再重新读取 LegalFacts，
    # 不再重新推导 Article 14 法律条件。
    # --------------------------------------------------------

    dependency = build_rule_dependency(
        condition_results,
        runtime_rule,
    )

    # --------------------------------------------------------
    # Explanation
    # --------------------------------------------------------

    explanation = (
        build_decision_explanation(
            decision,
            condition_results,
            contract_sequence,
        )
    )

    # --------------------------------------------------------
    # DecisionResult
    # --------------------------------------------------------

    result = DecisionResult(
        decision=decision,
        condition_results=condition_results,
        explicit_facts=explicit_facts,
        contract_sequence=contract_sequence,
        rule_dependencies=[
            dependency
        ],
        selected_rule=runtime_rule,
        explanation=explanation,
        engine_version=ENGINE_VERSION,
        selected_rule_id=runtime_rule.get("rule_id"),
    )

    # --------------------------------------------------------
    # Final Engine Validation
    # --------------------------------------------------------

    validate_decision_result(
        result,
        runtime_rule,
    )

    return result


# ============================================================
# Validate DecisionResult
# ============================================================

def validate_decision_result(
    decision: DecisionResult,
    rule: Dict[str, Any],
) -> None:
    """
    对最终 DecisionResult 进行结构验证。

    V6.2：
        ConditionResult 结构由 Runtime Rule 决定。

        Validator 不再固定假设 Article 14
        具有固定数量的条件。
    """

    if not isinstance(
        decision,
        DecisionResult,
    ):

        raise TypeError(
            "Decision Engine 输出必须为 DecisionResult。"
        )

    # --------------------------------------------------------
    # Rule Identity Binding
    # --------------------------------------------------------

    if not isinstance(rule, dict):
        raise TypeError(
            "Decision Engine 校验器的 rule 必须为字典。"
        )

    if not isinstance(decision.selected_rule, dict):
        raise TypeError(
            "DecisionResult.selected_rule 必须为字典。"
        )

    rule_id = rule.get("rule_id")
    selected_rule_id = decision.selected_rule.get("rule_id")
    identity_snapshot = decision.selected_rule_id

    if not isinstance(rule_id, str) or not rule_id.strip():
        raise ValueError("Runtime Rule 缺少合法的 rule_id。")

    if (
        not isinstance(selected_rule_id, str)
        or not selected_rule_id.strip()
    ):
        raise ValueError(
            "DecisionResult.selected_rule 缺少合法的 rule_id。"
        )

    if (
        not isinstance(identity_snapshot, str)
        or not identity_snapshot.strip()
    ):
        raise ValueError(
            "DecisionResult 缺少独立的规则身份快照。"
        )

    if not (
        identity_snapshot == rule_id
        and selected_rule_id == rule_id
    ):
        raise ValueError(
            "DecisionResult.selected_rule、规则身份快照与传入 "
            "Runtime Rule 的 rule_id 必须完全一致。"
        )


    if decision.decision not in {
        DEFINITE,
        CONDITIONAL,
        NOT_ESTABLISHED,
    }:

        raise ValueError(
            "非法 Decision 状态："
            f"{decision.decision}"
        )

    validate_condition_structure(
        decision.condition_results,
        rule,
    )

    unknown_count = sum(
        1
        for item in decision.condition_results
        if item.status == UNKNOWN
    )

    required_not_satisfied_count = sum(
        1
        for item in decision.condition_results
        if (
            item.condition_type == REQUIRED
            and item.status == NOT_SATISFIED
        )
    )

    triggered_exclusion_count = sum(
        1
        for item in decision.condition_results
        if (
            item.condition_type == EXCLUSION
            and item.status == SATISFIED
        )
    )

    triggered_exception_count = sum(
        1
        for item in decision.condition_results
        if (
            item.condition_type == EXCEPTION
            and item.status == SATISFIED
        )
    )

    # --------------------------------------------------------
    # UNKNOWN → 不能 DEFINITE
    # --------------------------------------------------------

    if (
        unknown_count > 0
        and decision.decision == DEFINITE
    ):

        raise ValueError(
            "Legal Decision Engine "
            "存在 UNKNOWN 条件时不能输出 DEFINITE。"
        )

    # --------------------------------------------------------
    # REQUIRED NOT_SATISFIED
    # → 必须 NOT_ESTABLISHED
    # --------------------------------------------------------

    if (
        required_not_satisfied_count > 0
        and decision.decision != NOT_ESTABLISHED
    ):

        raise ValueError(
            "Legal Decision Engine "
            "存在未满足的 REQUIRED 条件时"
            "必须输出 NOT_ESTABLISHED。"
        )

    # --------------------------------------------------------
    # EXCLUSION 已触发
    # → 必须 NOT_ESTABLISHED
    # --------------------------------------------------------

    if (
        triggered_exclusion_count > 0
        and decision.decision != NOT_ESTABLISHED
    ):

        raise ValueError(
            "Legal Decision Engine "
            "存在已经触发的 EXCLUSION 条件时"
            "必须输出 NOT_ESTABLISHED。"
        )

    # --------------------------------------------------------
    # EXCEPTION 已触发
    # → 必须 NOT_ESTABLISHED
    # --------------------------------------------------------

    if (
        triggered_exception_count > 0
        and decision.decision != NOT_ESTABLISHED
    ):

        raise ValueError(
            "Legal Decision Engine "
            "存在已经触发的 EXCEPTION 条件时"
            "必须输出 NOT_ESTABLISHED。"
        )

    # --------------------------------------------------------
    # UNKNOWN → CONDITIONAL
    # --------------------------------------------------------

    if (
        unknown_count > 0
        and required_not_satisfied_count == 0
        and triggered_exclusion_count == 0
        and triggered_exception_count == 0
        and decision.decision != CONDITIONAL
    ):

        raise ValueError(
            "Legal Decision Engine "
            "存在 UNKNOWN 且不存在阻断性 NOT_SATISFIED "
            "时必须输出 CONDITIONAL。"
        )

    # --------------------------------------------------------
    # 没有 UNKNOWN / NOT_SATISFIED
    # → 必须 DEFINITE
    # --------------------------------------------------------

    if (
        unknown_count == 0
        and required_not_satisfied_count == 0
        and triggered_exclusion_count == 0
        and triggered_exception_count == 0
        and decision.decision != DEFINITE
    ):

        raise ValueError(
            "Legal Decision Engine "
            "全部条件满足时必须输出 DEFINITE。"
        )


# ============================================================
# Public Helper Functions
# ============================================================

def get_condition_results(
    decision: DecisionResult,
) -> List[ConditionResult]:
    """
    获取全部 ConditionResult。
    """

    if not isinstance(
        decision,
        DecisionResult,
    ):

        return []

    return list(
        decision.condition_results
    )


def get_required_results(
    decision: DecisionResult,
) -> List[ConditionResult]:
    """
    获取 REQUIRED 条件。
    """

    return [
        item
        for item in decision.condition_results
        if item.condition_type == REQUIRED
    ]


def get_exclusion_results(
    decision: DecisionResult,
) -> List[ConditionResult]:
    """
    获取 EXCLUSION 条件。
    """

    return [
        item
        for item in decision.condition_results
        if item.condition_type == EXCLUSION
    ]


def get_exception_results(
    decision: DecisionResult,
) -> List[ConditionResult]:
    """
    获取 EXCEPTION 条件。
    """

    return [
        item
        for item in decision.condition_results
        if item.condition_type == EXCEPTION
    ]


# ============================================================
# Debug Print
# ============================================================

def print_decision_result(
    decision: DecisionResult,
) -> None:
    """
    打印 DecisionResult。

    仅用于人工调试和 Component Test。
    """

    print()
    print("=" * 70)

    print(
        f"Legal Decision Engine {ENGINE_VERSION}"
    )

    print("=" * 70)

    print()

    print(
        f"Decision: {decision.decision}"
    )

    print()

    print(
        "Explicit Facts:"
    )

    for fact in decision.explicit_facts:

        print(
            f"  - {fact}"
        )

    print()

    if decision.contract_sequence:

        sequence = decision.contract_sequence

        print(
            "Contract Sequence:"
        )

        print(
            f"  Count: {sequence.count}"
        )

        print(
            f"  Term Type: {sequence.term_type}"
        )

        print(
            f"  Continuous: {sequence.continuous}"
        )

    print()

    print(
        "Condition Results:"
    )

    for index, result in enumerate(
        decision.condition_results,
        start=1,
    ):

        print(
            f"  {index}. "
            f"[{result.condition_type}] "
            f"{result.status}"
        )

        print(
            f"     {result.condition}"
        )

        print(
            f"     Reason: {result.reason}"
        )

    print()

    print(
        f"Total Condition Results: "
        f"{len(decision.condition_results)}"
    )

    print(
        f"REQUIRED: "
        f"{len(decision.required_results)}"
    )

    print(
        f"EXCLUSION: "
        f"{len(decision.exclusion_results)}"
    )

    print(
        f"EXCEPTION: "
        f"{len(decision.exception_results)}"
    )

    print()

    print(
        "Satisfied Conditions:"
    )

    for item in decision.satisfied_conditions:

        print(
            f"  - {item}"
        )

    print()

    print(
        "Unknown Conditions:"
    )

    for item in decision.unknown_conditions:

        print(
            f"  - {item}"
        )

    print()

    print(
        "Not Satisfied Conditions:"
    )

    for item in decision.not_satisfied_conditions:

        print(
            f"  - {item}"
        )

    print()

    print(
        "Required Not Satisfied Conditions:"
    )

    for item in (
        decision.required_not_satisfied_conditions
    ):

        print(
            f"  - {item}"
        )

    print()

    print(
        "Triggered Exclusion Conditions:"
    )

    for item in (
        decision.triggered_exclusion_conditions
    ):

        print(
            f"  - {item}"
        )

    print()

    print(
        "Triggered Exception Conditions:"
    )

    for item in (
        decision.triggered_exception_conditions
    ):

        print(
            f"  - {item}"
        )

    print()

    print(
        "Explanation:"
    )

    print(
        f"  {decision.explanation}"
    )

    print("=" * 70)