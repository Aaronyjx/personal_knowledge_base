# -*- coding: utf-8 -*-

"""
RAG V6.0-16
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
V6.0-16 / V6.1 第一阶段核心原则
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

11. EXCLUSION 条件存在 NOT_SATISFIED：
       → 表示排除条件已经触发
       → NOT_ESTABLISHED

12. EXCEPTION 条件存在 NOT_SATISFIED：
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
V6.1 第一阶段 Fact → Condition 迁移
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

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from src.legal_common import normalize_text

from src.legal_fact_models import (
    ContractSequence,
    LegalFacts,
)

from src.legal_fact_extractor import (
    unique_texts,
    extract_legal_facts,
)


# ============================================================
# Version
# ============================================================

ENGINE_VERSION = "V6.0-16"


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


# ============================================================
# Legal Sources
# ============================================================

LABOR_CONTRACT_LAW = "中华人民共和国劳动合同法"

LABOR_CONTRACT_LAW_ARTICLE_14 = "第十四条"

LABOR_CONTRACT_LAW_ARTICLE_39 = "第三十九条"

LABOR_CONTRACT_LAW_ARTICLE_40 = "第四十条"

IMPLEMENTING_REGULATIONS = (
    "中华人民共和国劳动合同法实施条例"
)


# ============================================================
# Article 14 Conditions
# ============================================================

REQUIRED_CONDITIONS = [
    "连续订立二次固定期限劳动合同",
    "存在后续订立的劳动合同",
    "续订劳动合同",
    "劳动者提出或者同意续订、订立劳动合同",
]


EXCLUSION_CONDITIONS = [
    "劳动者存在《劳动合同法》第三十九条规定的情形",
    "劳动者存在《劳动合同法》第四十条第一项规定的情形",
    "劳动者存在《劳动合同法》第四十条第二项规定的情形",
]


EXCEPTION_CONDITIONS = [
    "劳动者提出订立固定期限劳动合同",
]


ALL_CONDITIONS = (
    REQUIRED_CONDITIONS
    + EXCLUSION_CONDITIONS
    + EXCEPTION_CONDITIONS
)


# ============================================================
# Combined Negative Patterns
# ============================================================

COMBINED_ARTICLE_39_40_NEGATIVE_PATTERNS = [
    "不存在劳动合同法第三十九条和第四十条第一项、第二项规定的情形",
    "不存在《劳动合同法》第三十九条和第四十条第一项、第二项规定的情形",
    "不存在劳动合同法第三十九条和第四十条第一项及第二项规定的情形",
    "不存在《劳动合同法》第三十九条和第四十条第一项及第二项规定的情形",
    "不存在劳动合同法第三十九条、第四十条第一项、第二项规定的情形",
    "不存在《劳动合同法》第三十九条、第四十条第一项、第二项规定的情形",
    "没有劳动合同法第三十九条和第四十条第一项、第二项规定的情形",
    "没有《劳动合同法》第三十九条和第四十条第一项、第二项规定的情形",
    "没有劳动合同法第三十九条和第四十条第一项及第二项规定的情形",
    "没有《劳动合同法》第三十九条和第四十条第一项及第二项规定的情形",
    "不具有劳动合同法第三十九条和第四十条第一项、第二项规定的情形",
    "不具有《劳动合同法》第三十九条和第四十条第一项、第二项规定的情形",
    "不具有劳动合同法第三十九条和第四十条第一项及第二项规定的情形",
    "不具有《劳动合同法》第三十九条和第四十条第一项及第二项规定的情形",
]


# ============================================================
# Dataclass
# ============================================================

@dataclass
class ConditionResult:
    """
    单项法律条件判断结果。
    """

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
        """

        return {
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

        EXCLUSION 的 NOT_SATISFIED 并不是普通意义上的
        “条件不满足”，而是表示排除情形已经成立。
        """

        return [
            item.condition
            for item in self.condition_results
            if (
                item.condition_type == EXCLUSION
                and item.status == NOT_SATISFIED
            )
        ]

    @property
    def triggered_exception_conditions(
        self,
    ) -> List[str]:
        """
        获取已经触发的 EXCEPTION 条件。

        EXCEPTION 的 NOT_SATISFIED 表示例外情形成立，
        因而阻却通常规则的适用。
        """

        return [
            item.condition
            for item in self.condition_results
            if (
                item.condition_type == EXCEPTION
                and item.status == NOT_SATISFIED
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

            "selected_rule": self.selected_rule,

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

def build_core_rule() -> Dict[str, Any]:
    """
    构建《劳动合同法》第十四条核心规则。
    """

    return {
        "law_name": LABOR_CONTRACT_LAW,

        "article": LABOR_CONTRACT_LAW_ARTICLE_14,

        "rule_name": (
            "连续订立固定期限劳动合同后"
            "订立无固定期限劳动合同"
        ),

        "rule_text": (
            "连续订立二次固定期限劳动合同，"
            "且不存在法律规定的排除或者例外情形，"
            "在符合法定续订及劳动者意思表示等条件时，"
            "依法判断是否应当订立无固定期限劳动合同。"
        ),

        "conditions": list(
            REQUIRED_CONDITIONS
        ),

        "exclusion_conditions": list(
            EXCLUSION_CONDITIONS
        ),

        "exceptions": list(
            EXCEPTION_CONDITIONS
        ),

        "priority": "ARTICLE_14",
    }


# ============================================================
# Rule Dependency
# ============================================================

def build_rule_dependency(
    question: str,
    contract_sequence: Optional[
        ContractSequence
    ],
) -> RuleDependency:
    """
    建立用户事实与 Article 14 条件之间的依赖关系。

    重点：

        “三次固定期限合同”
        不能自动推导：

            “已经续订”

        也不能自动推导：

            “劳动者已经提出或者同意”

        更不能自动推导：

            “不存在第39条、第40条情形”
    """

    satisfied_by_fact: List[str] = []

    not_proven_by_fact: List[str] = []

    if (
        contract_sequence is not None
        and contract_sequence.count >= 3
        and contract_sequence.continuous
    ):

        satisfied_by_fact.extend(
            [
                "连续订立二次固定期限劳动合同",
                "存在后续订立的劳动合同",
            ]
        )

        not_proven_by_fact.extend(
            [
                "续订劳动合同",
                "劳动者提出或者同意续订、订立劳动合同",
                "劳动者不存在《劳动合同法》第三十九条规定的情形",
                "劳动者不存在《劳动合同法》第四十条第一项规定的情形",
                "劳动者不存在《劳动合同法》第四十条第二项规定的情形",
                "劳动者未提出订立固定期限劳动合同",
            ]
        )

        explanation = (
            "三次固定期限劳动合同这一事实，"
            "可以证明已经连续订立二次固定期限劳动合同，"
            "并且存在后续订立的劳动合同；"
            "但仅凭合同次数不能证明已经发生续订，"
            "也不能证明劳动者已经提出或者同意续订，"
            "同时不能推定不存在法定排除或者例外情形。"
        )

    elif (
        contract_sequence is not None
        and contract_sequence.count == 2
        and contract_sequence.continuous
    ):

        satisfied_by_fact.append(
            "连续订立二次固定期限劳动合同"
        )

        not_proven_by_fact.extend(
            [
                "存在后续订立的劳动合同",
                "续订劳动合同",
                "劳动者提出或者同意续订、订立劳动合同",
                "劳动者不存在《劳动合同法》第三十九条规定的情形",
                "劳动者不存在《劳动合同法》第四十条第一项规定的情形",
                "劳动者不存在《劳动合同法》第四十条第二项规定的情形",
                "劳动者未提出订立固定期限劳动合同",
            ]
        )

        explanation = (
            "两次固定期限劳动合同可以证明"
            "连续订立二次固定期限劳动合同，"
            "但仅凭两次合同事实，"
            "不能证明存在后续订立的劳动合同，"
            "也不能证明已经完成续订，"
            "同时不能推定劳动者已经同意续订，"
            "或者不存在法定排除、例外情形。"
        )

    else:

        not_proven_by_fact = list(
            ALL_CONDITIONS
        )

        explanation = (
            "当前用户事实不足以直接证明"
            "《劳动合同法》第十四条规定的核心条件。"
        )

    return RuleDependency(
        rule_name="劳动合同法第十四条",
        satisfied_by_fact=unique_texts(
            satisfied_by_fact
        ),
        not_proven_by_fact=unique_texts(
            not_proven_by_fact
        ),
        explanation=explanation,
    )


# ============================================================
# Condition Matching
# ============================================================

def match_condition(
    facts: LegalFacts,
    condition: str,
    condition_type: str,
) -> ConditionResult:
    """
    对单项法律条件进行判断。

    V6.1 第一阶段：

        本函数不再接收 question。

        本函数不再：
            - normalize_text(question)
            - contains_any(...)
            - has_completed_renewal(...)
            - 自己扫描自然语言模式

        本函数只消费 LegalFacts。

    Fact Layer：

        LegalFacts
            ↓
        Condition Mapping
            ↓
        ConditionResult

    注意：

        LegalFacts 中的 None 必须保持 UNKNOWN。

        Engine 不得因为上下文或者推测，
        将 None 自动升级为 SATISFIED。
    """

    # ========================================================
    # REQUIRED 1
    # ========================================================

    if condition == "连续订立二次固定期限劳动合同":

        contract_sequence = (
            facts.contract_sequence
        )

        if (
            contract_sequence is not None
            and contract_sequence.count >= 2
            and contract_sequence.term_type == "fixed"
            and contract_sequence.continuous
        ):

            return ConditionResult(
                condition=condition,
                status=SATISFIED,
                reason=(
                    "用户明确陈述连续订立"
                    "至少二次固定期限劳动合同。"
                ),
                condition_type=REQUIRED,
            )

        return ConditionResult(
            condition=condition,
            status=UNKNOWN,
            reason=(
                "当前事实不足以确认"
                "连续订立二次固定期限劳动合同。"
            ),
            condition_type=REQUIRED,
        )

    # ========================================================
    # REQUIRED 2
    # ========================================================

    if condition == "存在后续订立的劳动合同":

        contract_sequence = (
            facts.contract_sequence
        )

        if (
            contract_sequence is not None
            and contract_sequence.count >= 3
            and contract_sequence.term_type == "fixed"
        ):

            return ConditionResult(
                condition=condition,
                status=SATISFIED,
                reason=(
                    "用户明确陈述已经存在"
                    "第三次固定期限劳动合同，"
                    "因此可以确认存在后续订立的劳动合同。"
                ),
                condition_type=REQUIRED,
            )

        if facts.completed_renewal is True:

            return ConditionResult(
                condition=condition,
                status=SATISFIED,
                reason=(
                    "用户明确陈述已经完成续订/续签，"
                    "因此可以确认存在后续劳动合同。"
                ),
                condition_type=REQUIRED,
            )

        return ConditionResult(
            condition=condition,
            status=UNKNOWN,
            reason=(
                "当前事实不足以确认"
                "存在后续订立的劳动合同。"
            ),
            condition_type=REQUIRED,
        )

    # ========================================================
    # REQUIRED 3
    # ========================================================

    if condition == "续订劳动合同":

        if facts.completed_renewal is True:

            return ConditionResult(
                condition=condition,
                status=SATISFIED,
                reason=(
                    "用户明确使用“已经续订”“已经续签”"
                    "等完成性表述，"
                    "可以确认续订事实已经发生。"
                ),
                condition_type=REQUIRED,
            )

        contract_sequence = (
            facts.contract_sequence
        )

        if (
            contract_sequence is not None
            and contract_sequence.count >= 3
        ):

            return ConditionResult(
                condition=condition,
                status=UNKNOWN,
                reason=(
                    "虽然已经存在三次固定期限劳动合同，"
                    "但合同次数本身不能自动证明"
                    "第三次属于已经完成的续订。"
                ),
                condition_type=REQUIRED,
            )

        return ConditionResult(
            condition=condition,
            status=UNKNOWN,
            reason=(
                "当前事实不足以确认"
                "续订劳动合同已经完成。"
            ),
            condition_type=REQUIRED,
        )

    # ========================================================
    # REQUIRED 4
    # ========================================================

    if (
        condition
        == "劳动者提出或者同意续订、订立劳动合同"
    ):

        if facts.worker_agreement is True:

            return ConditionResult(
                condition=condition,
                status=SATISFIED,
                reason=(
                    "用户明确陈述劳动者"
                    "提出或者同意续订、订立劳动合同。"
                ),
                condition_type=REQUIRED,
            )

        contract_sequence = (
            facts.contract_sequence
        )

        if (
            contract_sequence is not None
            and contract_sequence.count >= 2
        ):

            return ConditionResult(
                condition=condition,
                status=UNKNOWN,
                reason=(
                    "已经存在两次或者三次固定期限劳动合同，"
                    "但合同次数本身不能证明劳动者"
                    "提出或者同意续订、订立劳动合同。"
                ),
                condition_type=REQUIRED,
            )

        return ConditionResult(
            condition=condition,
            status=UNKNOWN,
            reason=(
                "当前事实不足以确认劳动者"
                "提出或者同意续订、订立劳动合同。"
            ),
            condition_type=REQUIRED,
        )

    # ========================================================
    # EXCLUSION 1
    # Article 39
    # ========================================================

    if (
        condition
        == "劳动者存在《劳动合同法》第三十九条规定的情形"
    ):

        # ----------------------------------------------------
        # False：
        #
        # 用户明确陈述不存在 Article 39 情形。
        #
        # 对 EXCLUSION 而言：
        #
        # 不存在排除情形
        #     → 条件满足
        #     → SATISFIED
        # ----------------------------------------------------

        if facts.article_39 is False:

            return ConditionResult(
                condition=condition,
                status=SATISFIED,
                reason=(
                    "用户明确陈述不存在"
                    "《劳动合同法》第三十九条规定的情形，"
                    "因此该排除条件未被触发。"
                ),
                condition_type=EXCLUSION,
            )

        # ----------------------------------------------------
        # True：
        #
        # 用户明确陈述存在 Article 39 情形。
        #
        # 对 EXCLUSION 而言：
        #
        # 排除情形成立
        #     → NOT_SATISFIED
        #     → 触发 NOT_ESTABLISHED
        # ----------------------------------------------------

        if facts.article_39 is True:

            return ConditionResult(
                condition=condition,
                status=NOT_SATISFIED,
                reason=(
                    "用户明确陈述存在"
                    "《劳动合同法》第三十九条规定的情形，"
                    "因此该排除条件已经触发。"
                ),
                condition_type=EXCLUSION,
            )

        # ----------------------------------------------------
        # None：
        #
        # 用户没有明确说明。
        #
        # 不得推测。
        # ----------------------------------------------------

        return ConditionResult(
            condition=condition,
            status=UNKNOWN,
            reason=(
                "当前事实不足以确认劳动者"
                "是否存在《劳动合同法》第三十九条规定的情形。"
            ),
            condition_type=EXCLUSION,
        )

    # ========================================================
    # EXCLUSION 2
    # Article 40(1)
    # ========================================================

    if (
        condition
        == "劳动者存在《劳动合同法》第四十条第一项规定的情形"
    ):

        if facts.article_40_1 is False:

            return ConditionResult(
                condition=condition,
                status=SATISFIED,
                reason=(
                    "用户明确陈述不存在"
                    "《劳动合同法》第四十条第一项规定的情形，"
                    "因此该排除条件未被触发。"
                ),
                condition_type=EXCLUSION,
            )

        if facts.article_40_1 is True:

            return ConditionResult(
                condition=condition,
                status=NOT_SATISFIED,
                reason=(
                    "用户明确陈述存在"
                    "《劳动合同法》第四十条第一项规定的情形，"
                    "因此该排除条件已经触发。"
                ),
                condition_type=EXCLUSION,
            )

        return ConditionResult(
            condition=condition,
            status=UNKNOWN,
            reason=(
                "当前事实不足以确认劳动者"
                "是否存在《劳动合同法》第四十条第一项规定的情形。"
            ),
            condition_type=EXCLUSION,
        )

    # ========================================================
    # EXCLUSION 3
    # Article 40(2)
    # ========================================================

    if (
        condition
        == "劳动者存在《劳动合同法》第四十条第二项规定的情形"
    ):

        if facts.article_40_2 is False:

            return ConditionResult(
                condition=condition,
                status=SATISFIED,
                reason=(
                    "用户明确陈述不存在"
                    "《劳动合同法》第四十条第二项规定的情形，"
                    "因此该排除条件未被触发。"
                ),
                condition_type=EXCLUSION,
            )

        if facts.article_40_2 is True:

            return ConditionResult(
                condition=condition,
                status=NOT_SATISFIED,
                reason=(
                    "用户明确陈述存在"
                    "《劳动合同法》第四十条第二项规定的情形，"
                    "因此该排除条件已经触发。"
                ),
                condition_type=EXCLUSION,
            )

        return ConditionResult(
            condition=condition,
            status=UNKNOWN,
            reason=(
                "当前事实不足以确认劳动者"
                "是否存在《劳动合同法》第四十条第二项规定的情形。"
            ),
            condition_type=EXCLUSION,
        )

    # ========================================================
    # EXCEPTION
    # ========================================================

    if (
        condition
        == "劳动者提出订立固定期限劳动合同"
    ):

        # ----------------------------------------------------
        # False：
        #
        # 用户明确陈述劳动者没有提出订立固定期限劳动合同。
        #
        # 因此例外没有触发。
        # ----------------------------------------------------

        if facts.fixed_term_exception is False:

            return ConditionResult(
                condition=condition,
                status=SATISFIED,
                reason=(
                    "用户明确陈述劳动者没有提出"
                    "订立固定期限劳动合同，"
                    "因此该例外条件未被触发。"
                ),
                condition_type=EXCEPTION,
            )

        # ----------------------------------------------------
        # True：
        #
        # 用户明确陈述劳动者提出订立固定期限劳动合同。
        #
        # 例外条件触发。
        # ----------------------------------------------------

        if facts.fixed_term_exception is True:

            return ConditionResult(
                condition=condition,
                status=NOT_SATISFIED,
                reason=(
                    "用户明确陈述劳动者提出"
                    "订立固定期限劳动合同，"
                    "因此该例外条件已经触发。"
                ),
                condition_type=EXCEPTION,
            )

        # ----------------------------------------------------
        # None：
        #
        # 用户没有明确说明。
        # ----------------------------------------------------

        return ConditionResult(
            condition=condition,
            status=UNKNOWN,
            reason=(
                "当前事实不足以确认劳动者"
                "是否提出订立固定期限劳动合同。"
            ),
            condition_type=EXCEPTION,
        )

    # ========================================================
    # Default
    # ========================================================

    return ConditionResult(
        condition=condition,
        status=UNKNOWN,
        reason="当前条件没有匹配到明确事实。",
        condition_type=condition_type,
    )


# ============================================================
# Condition Structure Validation
# ============================================================

def validate_condition_structure(
    condition_results: List[ConditionResult],
) -> None:
    """
    验证 Article 14 条件结构。

    强约束：

        ConditionResult = 8

        REQUIRED   = 4
        EXCLUSION  = 3
        EXCEPTION  = 1
    """

    if len(condition_results) != 8:

        raise ValueError(
            "Legal Decision Engine "
            f"必须生成 8 个 ConditionResult，"
            f"实际为 {len(condition_results)}。"
        )

    required_results = [
        item
        for item in condition_results
        if item.condition_type == REQUIRED
    ]

    exclusion_results = [
        item
        for item in condition_results
        if item.condition_type == EXCLUSION
    ]

    exception_results = [
        item
        for item in condition_results
        if item.condition_type == EXCEPTION
    ]

    if len(required_results) != 4:

        raise ValueError(
            "REQUIRED 条件必须为 4 个，"
            f"实际为 {len(required_results)}。"
        )

    if len(exclusion_results) != 3:

        raise ValueError(
            "EXCLUSION 条件必须为 3 个，"
            f"实际为 {len(exclusion_results)}。"
        )

    if len(exception_results) != 1:

        raise ValueError(
            "EXCEPTION 条件必须为 1 个，"
            f"实际为 {len(exception_results)}。"
        )

    names = [
        item.condition
        for item in condition_results
    ]

    if len(set(names)) != 8:

        raise ValueError(
            "ConditionResult 存在重复条件。"
        )

    if set(names) != set(
        ALL_CONDITIONS
    ):

        raise ValueError(
            "ConditionResult 条件集合与"
            "Article 14 固定条件集合不一致。"
        )


# ============================================================
# Evaluate Rule
# ============================================================

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

        1. 任意 NOT_SATISFIED
           → NOT_ESTABLISHED

        2. 没有 NOT_SATISFIED，
           但存在 UNKNOWN
           → CONDITIONAL

        3. 全部 SATISFIED
           → DEFINITE
    """

    condition_results: List[
        ConditionResult
    ] = []

    # --------------------------------------------------------
    # REQUIRED
    # --------------------------------------------------------

    for condition in REQUIRED_CONDITIONS:

        result = match_condition(
            facts=facts,
            condition=condition,
            condition_type=REQUIRED,
        )

        condition_results.append(
            result
        )

    # --------------------------------------------------------
    # EXCLUSION
    # --------------------------------------------------------

    for condition in EXCLUSION_CONDITIONS:

        result = match_condition(
            facts=facts,
            condition=condition,
            condition_type=EXCLUSION,
        )

        condition_results.append(
            result
        )

    # --------------------------------------------------------
    # EXCEPTION
    # --------------------------------------------------------

    for condition in EXCEPTION_CONDITIONS:

        result = match_condition(
            facts=facts,
            condition=condition,
            condition_type=EXCEPTION,
        )

        condition_results.append(
            result
        )

    # --------------------------------------------------------
    # Structure Validation
    # --------------------------------------------------------

    validate_condition_structure(
        condition_results
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
            and item.status == NOT_SATISFIED
        )
    ]

    triggered_exceptions = [
        item
        for item in condition_results
        if (
            item.condition_type == EXCEPTION
            and item.status == NOT_SATISFIED
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
    选择 Article 14 核心规则。

    V6.0-16：

        即使 Retriever 提供了结构化规则，
        Decision Engine 仍然强制使用固定的
        Article 14 条件结构。

    目的：

        防止 Retriever 输出的条件结构漂移。
    """

    rule = build_core_rule()

    if retrieved_articles:

        for article in retrieved_articles:

            if not isinstance(
                article,
                dict,
            ):
                continue

            article_text = normalize_text(
                article.get(
                    "article",
                    ""
                )
            )

            law_name = normalize_text(
                article.get(
                    "law_name",
                    ""
                )
            )

            if (
                "第十四条"
                in article_text
                or "第十四条"
                in normalize_text(
                    article.get(
                        "title",
                        ""
                    )
                )
                or (
                    law_name
                    == LABOR_CONTRACT_LAW
                    and "14"
                    in article_text
                )
            ):

                rule = dict(rule)

                if article.get(
                    "rule_text"
                ):

                    rule["rule_text"] = (
                        article[
                            "rule_text"
                        ]
                    )

                break

    # --------------------------------------------------------
    # 强制固定条件
    # --------------------------------------------------------

    rule["conditions"] = list(
        REQUIRED_CONDITIONS
    )

    rule["exclusion_conditions"] = list(
        EXCLUSION_CONDITIONS
    )

    rule["exceptions"] = list(
        EXCEPTION_CONDITIONS
    )

    return rule


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
            and item.status == NOT_SATISFIED
        )
    ]

    triggered_exceptions = [
        item.condition
        for item in condition_results
        if (
            item.condition_type == EXCEPTION
            and item.status == NOT_SATISFIED
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

    core_rule = select_core_rule(
        retrieved_articles
    )

    # --------------------------------------------------------
    # Rule Dependency
    # --------------------------------------------------------

    dependency = build_rule_dependency(
        normalized_question,
        contract_sequence,
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
        rule=core_rule,
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
        selected_rule=core_rule,
        explanation=explanation,
        engine_version=ENGINE_VERSION,
    )

    # --------------------------------------------------------
    # Final Engine Validation
    # --------------------------------------------------------

    validate_decision_result(
        result
    )

    return result


# ============================================================
# Validate DecisionResult
# ============================================================

def validate_decision_result(
    decision: DecisionResult,
) -> None:
    """
    对最终 DecisionResult 进行结构验证。

    强约束：

        ConditionResult = 8

        REQUIRED   = 4
        EXCLUSION  = 3
        EXCEPTION  = 1
    """

    if not isinstance(
        decision,
        DecisionResult,
    ):

        raise TypeError(
            "Decision Engine 输出必须为 DecisionResult。"
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
        decision.condition_results
    )

    unknown_count = sum(
        1
        for item in decision.condition_results
        if item.status == UNKNOWN
    )

    not_satisfied_count = sum(
        1
        for item in decision.condition_results
        if item.status == NOT_SATISFIED
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
            and item.status == NOT_SATISFIED
        )
    )

    triggered_exception_count = sum(
        1
        for item in decision.condition_results
        if (
            item.condition_type == EXCEPTION
            and item.status == NOT_SATISFIED
        )
    )

    categorized_not_satisfied_count = (
        required_not_satisfied_count
        + triggered_exclusion_count
        + triggered_exception_count
    )

    if (
        categorized_not_satisfied_count
        != not_satisfied_count
    ):

        raise ValueError(
            "Legal Decision Engine "
            "NOT_SATISFIED 条件存在未正确分类的情况。"
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
        and not_satisfied_count == 0
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
        and not_satisfied_count == 0
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