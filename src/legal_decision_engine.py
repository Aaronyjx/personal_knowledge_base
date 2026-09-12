# -*- coding: utf-8 -*-

"""
RAG V6.0-15
Legal Decision Engine

============================================================
功能
============================================================

本模块负责：

    用户问题
        ↓
    显式事实提取
        ↓
    合同序列提取
        ↓
    法律规则条件匹配
        ↓
    条件状态判断
        ↓
    综合法律决策
        ↓
    DecisionResult

============================================================
V6.0-15 核心原则
============================================================

1. Decision Engine 是唯一法律条件判断来源。

2. ConditionResult 只能在本模块创建。

3. 固定 8 条法律条件：

    REQUIRED
        1. 连续订立二次固定期限劳动合同
        2. 存在后续订立的劳动合同
        3. 续订劳动合同
        4. 劳动者提出或者同意续订、订立劳动合同

    EXCLUSION
        5. 劳动者存在《劳动合同法》第三十九条规定的情形
        6. 劳动者存在《劳动合同法》第四十条第一项规定的情形
        7. 劳动者存在《劳动合同法》第四十条第二项规定的情形

    EXCEPTION
        8. 劳动者提出订立固定期限劳动合同

    总数：

        REQUIRED   = 4
        EXCLUSION  = 3
        EXCEPTION  = 1
        TOTAL      = 8

4. “连续签订三次固定期限劳动合同”属于用户事实。

5. 三次固定期限合同可以证明：

        连续订立二次固定期限劳动合同
            → SATISFIED

        存在后续订立的劳动合同
            → SATISFIED

   但不能仅凭合同次数证明：

        续订劳动合同
            → UNKNOWN

        劳动者提出或者同意续订、订立劳动合同
            → UNKNOWN

6. “准备续订”“计划续订”“打算续订”“拟续订”
   不属于已经完成的续订。

7. “已经续订”“已经续签”“已续订”“已续签”
   可以证明已经发生续订。

8. 劳动者“同意续订”可以证明劳动者同意，
   但不能反向证明续订已经完成。

9. UNKNOWN 不得自动升级为 SATISFIED。

10. 任一 NOT_SATISFIED：
        Decision = NOT_ESTABLISHED

11. 没有 NOT_SATISFIED，但存在 UNKNOWN：
        Decision = CONDITIONAL

12. 全部条件 SATISFIED：
        Decision = DEFINITE

13. Decision Engine 不生成最终自然语言法律答案。

14. Decision Engine 不调用 Ollama。

15. Answer Builder 只消费 DecisionResult，
    不重新判断法律条件。

============================================================
"""


from __future__ import annotations


from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# Version
# ============================================================

ENGINE_VERSION = "V6.0-15"


# ============================================================
# Status Constants
# ============================================================

SATISFIED = "SATISFIED"

NOT_SATISFIED = "NOT_SATISFIED"

UNKNOWN = "UNKNOWN"


# ============================================================
# Condition Category
# ============================================================

REQUIRED = "REQUIRED"

EXCLUSION = "EXCLUSION"

EXCEPTION = "EXCEPTION"


# ============================================================
# Decision Constants
# ============================================================

DEFINITE = "DEFINITE"

CONDITIONAL = "CONDITIONAL"

NOT_ESTABLISHED = "NOT_ESTABLISHED"


# ============================================================
# Legal Rule Constants
# ============================================================

LABOR_CONTRACT_LAW = "中华人民共和国劳动合同法"

LABOR_CONTRACT_LAW_ARTICLE_14 = "第十四条"

LABOR_CONTRACT_LAW_ARTICLE_39 = "第三十九条"

LABOR_CONTRACT_LAW_ARTICLE_40 = "第四十条"

IMPLEMENTING_REGULATIONS = "中华人民共和国劳动合同法实施条例"


# ============================================================
# Fixed Conditions
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


# ============================================================
# ConditionResult
# ============================================================

@dataclass
class ConditionResult:
    """
    单个法律条件的判断结果。

    ========================================================
    字段
    ========================================================

    condition:
        法律条件文本。

    status:
        SATISFIED
        NOT_SATISFIED
        UNKNOWN

    reason:
        判断理由。

    condition_type:
        REQUIRED
        EXCLUSION
        EXCEPTION

    ========================================================
    兼容旧版本
    ========================================================

    result.type

    等价于：

    result.condition_type
    """

    condition: str

    status: str

    reason: str = ""

    condition_type: str = REQUIRED

    @property
    def type(self) -> str:
        """
        兼容旧版本字段。
        """

        return self.condition_type

    def to_dict(self) -> Dict[str, Any]:
        """
        转换为普通 dict。
        """

        return {
            "condition": self.condition,
            "status": self.status,
            "reason": self.reason,
            "condition_type": self.condition_type,
            "type": self.condition_type,
        }


# ============================================================
# ContractSequence
# ============================================================

@dataclass
class ContractSequence:
    """
    用户问题中识别出的劳动合同序列。

    例如：

        公司连续签订三次固定期限劳动合同

    对应：

        count = 3
        term_type = fixed
        continuous = True
    """

    count: int = 0

    term_type: str = ""

    continuous: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """
        转换为 dict。
        """

        return {
            "count": self.count,
            "term_type": self.term_type,
            "continuous": self.continuous,
        }


# ============================================================
# RuleDependency
# ============================================================

@dataclass
class RuleDependency:
    """
    法律规则之间的事实依赖关系。

    表达：

        用户事实
            ↓
        可以证明什么
            ↓
        不能证明什么

    重要原则：

        不允许：

            用户事实
                ↓
            自动扩张
                ↓
            未明确事实
                ↓
            SATISFIED
    """

    rule_name: str = ""

    satisfied_by_fact: List[str] = field(
        default_factory=list
    )

    not_proven_by_fact: List[str] = field(
        default_factory=list
    )

    explanation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """
        转换为 dict。
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


# ============================================================
# DecisionResult
# ============================================================

@dataclass
class DecisionResult:
    """
    法律决策最终结果。

    Decision Engine 对外输出的唯一标准数据结构。
    """

    decision: str

    condition_results: List[ConditionResult] = field(
        default_factory=list
    )

    explicit_facts: List[str] = field(
        default_factory=list
    )

    contract_sequence: Optional[
        ContractSequence
    ] = None

    rule_dependencies: List[RuleDependency] = field(
        default_factory=list
    )

    selected_rule: Dict[str, Any] = field(
        default_factory=dict
    )

    explanation: str = ""

    engine_version: str = ENGINE_VERSION

    @property
    def satisfied_conditions(self) -> List[str]:
        """
        返回 SATISFIED 条件。

        这里只读取数据，不重新进行法律判断。
        """

        return [
            item.condition
            for item in self.condition_results
            if item.status == SATISFIED
        ]

    @property
    def unknown_conditions(self) -> List[str]:
        """
        返回 UNKNOWN 条件。
        """

        return [
            item.condition
            for item in self.condition_results
            if item.status == UNKNOWN
        ]

    @property
    def not_satisfied_conditions(self) -> List[str]:
        """
        返回 NOT_SATISFIED 条件。
        """

        return [
            item.condition
            for item in self.condition_results
            if item.status == NOT_SATISFIED
        ]

    @property
    def required_results(
        self,
    ) -> List[ConditionResult]:
        """
        获取 REQUIRED 条件结果。
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
        获取 EXCLUSION 条件结果。
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
        获取 EXCEPTION 条件结果。
        """

        return [
            item
            for item in self.condition_results
            if item.condition_type == EXCEPTION
        ]

    def to_dict(self) -> Dict[str, Any]:
        """
        转换为完整 dict。
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
        }


# ============================================================
# Text Helpers
# ============================================================

def normalize_text(
    value: Any,
) -> str:
    """
    文本标准化。
    """

    if value is None:
        return ""

    return str(value).strip()


def contains_any(
    text: str,
    patterns: List[str],
) -> bool:
    """
    判断文本是否包含任意关键词。
    """

    text = normalize_text(text)

    return any(
        pattern in text
        for pattern in patterns
    )


def unique_texts(
    values: List[str],
) -> List[str]:
    """
    去重并保持原顺序。
    """

    result: List[str] = []

    seen = set()

    for value in values:

        value = normalize_text(
            value
        )

        if not value:
            continue

        if value in seen:
            continue

        seen.add(value)

        result.append(value)

    return result


# ============================================================
# Completed Renewal Helper
# ============================================================

def has_completed_renewal(
    question: str,
) -> bool:
    """
    判断用户是否明确陈述：

        已经完成续订 / 续签。

    重要：

        准备续订
        计划续订
        打算续订
        拟续订

    均不属于已经完成的续订。

    ========================================================
    允许识别
    ========================================================

        已经续订劳动合同
        已经续签劳动合同
        已续订劳动合同
        已续签劳动合同
        已经续订
        已经续签
        已续订
        已续签
        后来已经续订劳动合同
        后来已经续签劳动合同
        之后已经续订劳动合同
        之后已经续签劳动合同
        后来又续订劳动合同
        后来又续签劳动合同

    ========================================================
    不允许识别
    ========================================================

        准备续订
        准备续签
        计划续订
        计划续签
        打算续订
        打算续签
        拟续订
        拟续签
    """

    question = normalize_text(
        question
    )

    completed_patterns = [

        "已经续订劳动合同",
        "已经续签劳动合同",

        "已经续订了劳动合同",
        "已经续签了劳动合同",

        "已续订劳动合同",
        "已续签劳动合同",

        "已经续订",
        "已经续签",

        "已续订",
        "已续签",

        "后来已经续订劳动合同",
        "后来已经续签劳动合同",

        "后来已经续订了劳动合同",
        "后来已经续签了劳动合同",

        "之后已经续订劳动合同",
        "之后已经续签劳动合同",

        "之后已经续订了劳动合同",
        "之后已经续签了劳动合同",

        "后来又续订劳动合同",
        "后来又续签劳动合同",

        "后来又续订了劳动合同",
        "后来又续签了劳动合同",

        "之后又已经续订劳动合同",
        "之后又已经续签劳动合同",

        "第三次已经续订",
        "第三次已经续签",

        "第三次已续订",
        "第三次已续签",

        "第三次已经续订劳动合同",
        "第三次已经续签劳动合同",

        "第三次已续订劳动合同",
        "第三次已续签劳动合同",
    ]

    return contains_any(
        question,
        completed_patterns,
    )


# ============================================================
# Explicit Fact Extraction
# ============================================================

def extract_explicit_facts(
    question: str,
) -> List[str]:
    """
    从用户问题中提取明确事实。

    这里只提取用户明确说出的事实。

    不进行法律推理。

    例如：

        公司连续签订三次固定期限劳动合同

    可以提取：

        公司连续签订三次固定期限劳动合同

    但不能直接因为“三次合同”而提取：

        劳动者同意续订
        第三次合同属于续订
        不存在第39条情形
    """

    question = normalize_text(
        question
    )

    facts: List[str] = []

    # --------------------------------------------------------
    # 三次固定期限劳动合同
    # --------------------------------------------------------

    three_fixed_patterns = [

        "连续签订三次固定期限劳动合同",
        "连续签了三次固定期限劳动合同",
        "连续签署三次固定期限劳动合同",
        "连续订立三次固定期限劳动合同",
        "连续订了三次固定期限劳动合同",

        "三次固定期限劳动合同",
        "三份固定期限劳动合同",
    ]

    if contains_any(
        question,
        three_fixed_patterns,
    ):

        facts.append(
            "公司连续签订三次固定期限劳动合同"
        )

    # --------------------------------------------------------
    # 两次固定期限劳动合同
    # --------------------------------------------------------

    two_fixed_patterns = [

        "连续签订两次固定期限劳动合同",
        "连续签了两次固定期限劳动合同",
        "连续签署两次固定期限劳动合同",
        "连续订立两次固定期限劳动合同",
        "连续订了两次固定期限劳动合同",

    ]

    if contains_any(
        question,
        two_fixed_patterns,
    ):

        facts.append(
            "连续订立二次固定期限劳动合同"
        )

    # --------------------------------------------------------
    # 已经完成续订
    # --------------------------------------------------------

    if has_completed_renewal(
        question
    ):

        facts.append(
            "存在明确续订劳动合同事实"
        )

    # --------------------------------------------------------
    # 劳动者提出 / 同意
    # --------------------------------------------------------

    worker_agreement_patterns = [

        "劳动者提出续订",
        "劳动者同意续订",

        "劳动者提出续签",
        "劳动者同意续签",

        "劳动者提出订立",
        "劳动者同意订立",

        "劳动者提出签订",
        "劳动者同意签订",

        "劳动者也同意续订",
        "劳动者也同意续签",

        "劳动者也同意订立",
        "劳动者也同意签订",

        "员工提出续订",
        "员工同意续订",

        "员工提出续签",
        "员工同意续签",

        "员工提出订立",
        "员工同意订立",

        "员工提出签订",
        "员工同意签订",

    ]

    if contains_any(
        question,
        worker_agreement_patterns,
    ):

        facts.append(
            "劳动者明确提出或者同意续订、订立劳动合同"
        )

    # --------------------------------------------------------
    # 固定期限例外
    # --------------------------------------------------------

    fixed_term_proposal_patterns = [

        "劳动者提出订立固定期限劳动合同",

        "劳动者要求签固定期限劳动合同",

        "劳动者要求订立固定期限劳动合同",

        "员工提出订立固定期限劳动合同",

        "员工要求签固定期限劳动合同",

        "员工要求订立固定期限劳动合同",
    ]

    if contains_any(
        question,
        fixed_term_proposal_patterns,
    ):

        facts.append(
            "劳动者提出订立固定期限劳动合同"
        )

    # --------------------------------------------------------
    # 第39条
    # --------------------------------------------------------

    article_39_patterns = [

        "存在第39条情形",
        "存在第39条规定的情形",

        "存在第三十九条情形",
        "存在第三十九条规定的情形",

        "符合第39条",
        "符合第39条规定的情形",

        "符合第三十九条",
        "符合第三十九条规定的情形",

        "劳动者有第39条情形",
        "劳动者有第39条规定的情形",

        "劳动者有第三十九条情形",
        "劳动者有第三十九条规定的情形",

        "劳动者存在第39条",
        "劳动者存在第39条规定的情形",

        "劳动者存在第三十九条",
        "劳动者存在第三十九条规定的情形",

        "存在劳动合同法第39条规定的情形",
        "存在劳动合同法第三十九条规定的情形",

        "存在《劳动合同法》第39条规定的情形",
        "存在《劳动合同法》第三十九条规定的情形",

        "符合劳动合同法第39条规定的情形",
        "符合劳动合同法第三十九条规定的情形",

        "符合《劳动合同法》第39条规定的情形",
        "符合《劳动合同法》第三十九条规定的情形",

        "劳动者存在劳动合同法第39条规定的情形",
        "劳动者存在劳动合同法第三十九条规定的情形",

        "劳动者存在《劳动合同法》第39条规定的情形",
        "劳动者存在《劳动合同法》第三十九条规定的情形",
    ]

    if contains_any(
        question,
        article_39_patterns,
    ):

        facts.append(
            "劳动者存在《劳动合同法》第三十九条规定的情形"
        )

    # --------------------------------------------------------
    # 第40条第一项
    # --------------------------------------------------------

    article_40_1_patterns = [

        "第40条第一项",
        "第四十条第一项",

        "第40条第1项",
        "第四十条第1项",

        "第40条第一项规定的情形",
        "第四十条第一项规定的情形",

        "第40条第1项规定的情形",
        "第四十条第1项规定的情形",
    ]

    if contains_any(
        question,
        article_40_1_patterns,
    ):

        facts.append(
            "劳动者存在《劳动合同法》第四十条第一项规定的情形"
        )

    # --------------------------------------------------------
    # 第40条第二项
    # --------------------------------------------------------

    article_40_2_patterns = [

        "第40条第二项",
        "第四十条第二项",

        "第40条第2项",
        "第四十条第2项",

        "第40条第二项规定的情形",
        "第四十条第二项规定的情形",

        "第40条第2项规定的情形",
        "第四十条第2项规定的情形",
    ]

    if contains_any(
        question,
        article_40_2_patterns,
    ):

        facts.append(
            "劳动者存在《劳动合同法》第四十条第二项规定的情形"
        )

    return unique_texts(
        facts
    )


# ============================================================
# Contract Sequence Extraction
# ============================================================

def extract_contract_sequence(
    question: str,
) -> ContractSequence:
    """
    提取合同序列。

    ========================================================
    核心原则
    ========================================================

    1. 用户明确说“三次固定期限劳动合同”
       → count = 3

    2. 用户明确说“两次固定期限劳动合同，
       第三次已经续签”
       → count = 3

    3. 用户明确说“两次固定期限劳动合同，
       之后已经续订劳动合同”
       → 至少存在后续合同，
          因此 count = 3

    4. 准备续订、计划续订、打算续订、
       拟续订不能增加合同次数。

    5. 不修改用户原始事实。
    """

    question = normalize_text(
        question
    )

    # ========================================================
    # 三次固定期限劳动合同
    # ========================================================

    three_fixed_patterns = [

        "连续签订三次固定期限劳动合同",
        "连续签了三次固定期限劳动合同",
        "连续签署三次固定期限劳动合同",
        "连续订立三次固定期限劳动合同",
        "连续订了三次固定期限劳动合同",

        "三次固定期限劳动合同",
        "三份固定期限劳动合同",
    ]

    if contains_any(
        question,
        three_fixed_patterns,
    ):

        return ContractSequence(
            count=3,
            term_type="fixed",
            continuous=True,
        )

    # ========================================================
    # 两次固定期限劳动合同
    # ========================================================

    two_fixed_patterns = [

        "连续签订两次固定期限劳动合同",
        "连续签了两次固定期限劳动合同",
        "连续签署两次固定期限劳动合同",
        "连续订立两次固定期限劳动合同",
        "连续订了两次固定期限劳动合同",
    ]

    has_two_fixed = contains_any(
        question,
        two_fixed_patterns,
    )

    # ========================================================
    # 第三次续订 / 续签
    # ========================================================

    has_third_renewal = contains_any(
        question,
        [
            "第三次已经续签",
            "第三次已续签",
            "第三次已经续订",
            "第三次已续订",
            "第三次续签",
            "第三次续订",
        ],
    )

    # ========================================================
    # 后来 / 之后已经发生续订
    # ========================================================

    has_later_completed_renewal = contains_any(
        question,
        [
            "之后已经续订劳动合同",
            "之后已经续签劳动合同",

            "之后已经续订了劳动合同",
            "之后已经续签了劳动合同",

            "后来已经续订劳动合同",
            "后来已经续签劳动合同",

            "后来已经续订了劳动合同",
            "后来已经续签了劳动合同",

            "之后又已经续订劳动合同",
            "之后又已经续签劳动合同",

            "后来又已经续订劳动合同",
            "后来又已经续签劳动合同",
        ],
    )

    # ========================================================
    # 明确“后来续订”但没有“已经”
    # ========================================================

    has_later_renewal = contains_any(
        question,
        [
            "之后续订劳动合同",
            "之后续签劳动合同",

            "之后又续订劳动合同",
            "之后又续签劳动合同",

            "后来续订劳动合同",
            "后来续签劳动合同",

            "后来又续订劳动合同",
            "后来又续签劳动合同",
        ],
    )

    if has_two_fixed and (
        has_third_renewal
        or has_later_completed_renewal
        or has_later_renewal
    ):

        return ContractSequence(
            count=3,
            term_type="fixed",
            continuous=True,
        )

    # ========================================================
    # 单纯两次固定期限劳动合同
    # ========================================================

    if has_two_fixed:

        return ContractSequence(
            count=2,
            term_type="fixed",
            continuous=True,
        )

    # ========================================================
    # 默认
    # ========================================================

    return ContractSequence()


# ============================================================
# Rule Construction
# ============================================================

def build_core_rule() -> Dict[str, Any]:
    """
    构建《劳动合同法》第十四条核心规则。

    这里定义的是：

        法律规则

    而不是：

        当前案件的判断结果。

    判断结果必须通过：

        match_condition()

    产生。
    """

    return {

        "law_name":
            LABOR_CONTRACT_LAW,

        "article":
            LABOR_CONTRACT_LAW_ARTICLE_14,

        "rule_name":
            (
                "连续订立二次固定期限劳动合同后"
                "订立无固定期限劳动合同规则"
            ),

        "rule_text":
            (
                "连续订立二次固定期限劳动合同，"
                "且不存在法定排除情形，"
                "在符合法定条件的情况下，"
                "劳动者可以要求或者同意订立无固定期限劳动合同。"
            ),

        "conditions":
            list(
                REQUIRED_CONDITIONS
            ),

        "exclusion_conditions":
            list(
                EXCLUSION_CONDITIONS
            ),

        "exceptions":
            list(
                EXCEPTION_CONDITIONS
            ),

        "priority":
            100,
    }


# ============================================================
# Rule Dependency
# ============================================================

def build_rule_dependency(
    question: str,
    contract_sequence: ContractSequence,
) -> RuleDependency:
    """
    构建核心规则的事实依赖关系。

    ========================================================
    三次固定期限合同
    ========================================================

    如果用户明确说：

        连续签订三次固定期限劳动合同

    那么：

        3 >= 2

    因此可以证明：

        连续订立二次固定期限劳动合同
            → SATISFIED

    同时存在第三份合同，因此：

        存在后续订立的劳动合同
            → SATISFIED

    但是不能仅凭这个事实证明：

        续订劳动合同
        劳动者提出或者同意
        第39条不存在
        第40条不存在
        劳动者没有提出固定期限
    """

    dependency = RuleDependency(
        rule_name="劳动合同法第十四条",
    )

    # ========================================================
    # 三次固定期限合同
    # ========================================================

    if (
        contract_sequence.count >= 3
        and contract_sequence.term_type == "fixed"
        and contract_sequence.continuous
    ):

        dependency.satisfied_by_fact.extend(
            [
                "连续签订三次固定期限劳动合同",
                "连续订立二次固定期限劳动合同",
                "存在后续订立的劳动合同",
            ]
        )

        dependency.not_proven_by_fact.extend(
            [
                "续订劳动合同",
                "劳动者提出或者同意续订、订立劳动合同",

                "劳动者不存在《劳动合同法》第三十九条规定的情形",

                "劳动者不存在《劳动合同法》第四十条第一项规定的情形",

                "劳动者不存在《劳动合同法》第四十条第二项规定的情形",

                "劳动者未提出订立固定期限劳动合同",
            ]
        )

        dependency.explanation = (
            "连续签订三次固定期限劳动合同可以证明"
            "已经达到连续订立二次固定期限劳动合同的"
            "数量门槛，并且存在后续劳动合同；"
            "但该事实本身不能进一步证明第三份合同的"
            "法律性质属于续订，也不能证明劳动者已经"
            "提出或者同意订立劳动合同，更不能推定"
            "第39条、第40条排除情形不存在。"
        )

        return dependency

    # ========================================================
    # 两次固定期限合同
    # ========================================================

    if (
        contract_sequence.count == 2
        and contract_sequence.term_type == "fixed"
        and contract_sequence.continuous
    ):

        dependency.satisfied_by_fact.extend(
            [
                "连续订立二次固定期限劳动合同",
            ]
        )

        dependency.not_proven_by_fact.extend(
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

        dependency.explanation = (
            "连续订立二次固定期限劳动合同可以满足"
            "数量门槛，但仍不能仅凭该事实证明后续合同"
            "已经订立、属于续订或者劳动者已经提出或者"
            "同意相关订立，也不能推定法定排除情形不存在。"
        )

        return dependency

    # ========================================================
    # 默认
    # ========================================================

    dependency.explanation = (
        "当前用户问题没有提供足够的合同序列事实，"
        "因此不能仅凭现有事实满足核心数量条件。"
    )

    return dependency


# ============================================================
# Condition Matching
# ============================================================

def match_condition(
    condition: str,
    question: str,
    contract_sequence: ContractSequence,
    explicit_facts: List[str],
    condition_type: str = REQUIRED,
) -> ConditionResult:
    """
    判断单个法律条件。

    ========================================================
    核心原则
    ========================================================

    1. 明确事实 → SATISFIED

    2. 明确相反事实 → NOT_SATISFIED

    3. 用户没有提供足够信息 → UNKNOWN

    4. 不允许通过推测把 UNKNOWN 变成 SATISFIED。
    """

    question = normalize_text(
        question
    )

    explicit_fact_text = " ".join(
        explicit_facts
    )

    # ========================================================
    # REQUIRED 1
    # ========================================================

    if condition == "连续订立二次固定期限劳动合同":

        # ----------------------------------------------------
        # 三次固定期限合同
        # ----------------------------------------------------

        if (
            contract_sequence.count >= 3
            and contract_sequence.term_type == "fixed"
            and contract_sequence.continuous
        ):

            return ConditionResult(
                condition=condition,
                status=SATISFIED,
                reason=(
                    "用户明确陈述连续签订三次固定期限劳动合同；"
                    "三次合同在数量上已经覆盖连续订立二次固定期限"
                    "劳动合同的数量门槛。"
                ),
                condition_type=REQUIRED,
            )

        # ----------------------------------------------------
        # 两次固定期限合同
        # ----------------------------------------------------

        if (
            contract_sequence.count == 2
            and contract_sequence.term_type == "fixed"
            and contract_sequence.continuous
        ):

            return ConditionResult(
                condition=condition,
                status=SATISFIED,
                reason=(
                    "用户明确陈述连续订立二次固定期限劳动合同，"
                    "满足该条件的数量要求。"
                ),
                condition_type=REQUIRED,
            )

        return ConditionResult(
            condition=condition,
            status=UNKNOWN,
            reason=(
                "当前用户事实不足以确认已经连续订立二次"
                "固定期限劳动合同。"
            ),
            condition_type=REQUIRED,
        )

    # ========================================================
    # REQUIRED 2
    # 存在后续订立的劳动合同
    # ========================================================

    if condition == "存在后续订立的劳动合同":

        # ----------------------------------------------------
        # 三次固定期限合同
        # ----------------------------------------------------

        if (
            contract_sequence.count >= 3
            and contract_sequence.term_type == "fixed"
            and contract_sequence.continuous
        ):

            return ConditionResult(
                condition=condition,
                status=SATISFIED,
                reason=(
                    "用户明确陈述连续签订三次固定期限劳动合同，"
                    "因此已经存在第三份后续劳动合同。"
                ),
                condition_type=REQUIRED,
            )

        # ----------------------------------------------------
        # 明确提及后续合同
        # ----------------------------------------------------

        if contains_any(
            question,
            [
                "后续劳动合同",
                "后续订立的劳动合同",
                "后来又签订劳动合同",
                "之后又签订劳动合同",
                "再次签订劳动合同",
                "第三份劳动合同",
                "第三次劳动合同",
            ],
        ):

            return ConditionResult(
                condition=condition,
                status=SATISFIED,
                reason=(
                    "用户明确陈述存在后续订立的劳动合同。"
                ),
                condition_type=REQUIRED,
            )

        # ----------------------------------------------------
        # 已经完成续订
        # ----------------------------------------------------

        if has_completed_renewal(
            question
        ):

            return ConditionResult(
                condition=condition,
                status=SATISFIED,
                reason=(
                    "用户明确提供了劳动合同已经完成续订"
                    "或者续签的事实；因此可以确认"
                    "存在后续订立的劳动合同。"
                ),
                condition_type=REQUIRED,
            )

        return ConditionResult(
            condition=condition,
            status=UNKNOWN,
            reason=(
                "用户没有明确提供后续劳动合同已经订立的事实。"
            ),
            condition_type=REQUIRED,
        )

    # ========================================================
    # REQUIRED 3
    # 续订劳动合同
    # ========================================================

    if condition == "续订劳动合同":

        # ----------------------------------------------------
        # 已经完成的续订
        # ----------------------------------------------------

        if has_completed_renewal(
            question
        ):

            return ConditionResult(
                condition=condition,
                status=SATISFIED,
                reason=(
                    "用户明确提供了劳动合同已经续订"
                    "或者续签的事实。"
                ),
                condition_type=REQUIRED,
            )

        # ----------------------------------------------------
        # 三次固定期限合同不能自动证明续订
        # ----------------------------------------------------

        if (
            contract_sequence.count >= 3
            and contract_sequence.term_type == "fixed"
            and contract_sequence.continuous
        ):

            return ConditionResult(
                condition=condition,
                status=UNKNOWN,
                reason=(
                    "连续签订三次固定期限劳动合同可以证明存在"
                    "后续劳动合同，但仅凭合同次数本身不能当然"
                    "证明该后续合同在本规则下属于续订劳动合同。"
                ),
                condition_type=REQUIRED,
            )

        # ----------------------------------------------------
        # 两次合同不能证明已经续订
        # ----------------------------------------------------

        if (
            contract_sequence.count == 2
            and contract_sequence.term_type == "fixed"
            and contract_sequence.continuous
        ):

            return ConditionResult(
                condition=condition,
                status=UNKNOWN,
                reason=(
                    "用户明确提供连续签订两次固定期限劳动合同，"
                    "但没有明确提供劳动合同已经续订或者续签的事实；"
                    "不能仅凭两次固定期限合同推定已经续订。"
                ),
                condition_type=REQUIRED,
            )

        return ConditionResult(
            condition=condition,
            status=UNKNOWN,
            reason=(
                "用户没有明确提供劳动合同属于续订或者续签的事实。"
            ),
            condition_type=REQUIRED,
        )

    # ========================================================
    # REQUIRED 4
    # 劳动者提出或者同意
    # ========================================================

    if condition == "劳动者提出或者同意续订、订立劳动合同":

        worker_agreement_patterns = [

            "劳动者提出续订",
            "劳动者同意续订",

            "劳动者提出续签",
            "劳动者同意续签",

            "劳动者提出订立",
            "劳动者同意订立",

            "劳动者提出签订",
            "劳动者同意签订",

            "劳动者也同意续订",
            "劳动者也同意续签",

            "劳动者也同意订立",
            "劳动者也同意签订",

            "员工提出续订",
            "员工同意续订",

            "员工提出续签",
            "员工同意续签",

            "员工提出订立",
            "员工同意订立",

            "员工提出签订",
            "员工同意签订",
        ]

        if contains_any(
            question,
            worker_agreement_patterns,
        ):

            return ConditionResult(
                condition=condition,
                status=SATISFIED,
                reason=(
                    "用户明确陈述劳动者提出或者同意"
                    "续订、订立劳动合同。"
                ),
                condition_type=REQUIRED,
            )

        # ----------------------------------------------------
        # 根据当前合同序列动态生成 UNKNOWN 原因
        # ----------------------------------------------------

        if (
            contract_sequence.count >= 1
            and contract_sequence.term_type == "fixed"
            and contract_sequence.continuous
        ):

            count_text = str(
                contract_sequence.count
            )

            reason = (
                f"用户明确提供连续签订{count_text}次固定期限劳动合同的事实，"
                "但没有明确提供劳动者提出或者同意续订、订立劳动合同的事实；"
                f"不能仅凭连续签订{count_text}次固定期限劳动合同"
                "推定劳动者已经提出或者同意。"
            )

        else:

            reason = (
                "用户没有明确提供劳动者提出或者同意"
                "续订、订立劳动合同的事实。"
            )

        return ConditionResult(
            condition=condition,
            status=UNKNOWN,
            reason=reason,
            condition_type=REQUIRED,
        )

    # ========================================================
    # EXCLUSION
    # ========================================================

    # ========================================================
    # 第39条
    # ========================================================

    if (
        condition
        == "劳动者存在《劳动合同法》第三十九条规定的情形"
    ):

        # ----------------------------------------------------
        # 注意：
        #
        # 必须先判断“不存在”，
        # 再判断“存在”。
        #
        # 因为：
        #
        #     劳动者存在第三十九条
        #
        # 是：
        #
        #     劳动者不存在第三十九条
        #
        # 的子字符串。
        # ----------------------------------------------------

        article_39_negative_patterns = [

            "劳动者不存在第39条情形",
            "劳动者不存在第39条规定的情形",

            "劳动者不存在第三十九条情形",
            "劳动者不存在第三十九条规定的情形",

            "不存在第39条情形",
            "不存在第39条规定的情形",

            "不存在第三十九条情形",
            "不存在第三十九条规定的情形",

            "劳动者不符合第39条",
            "劳动者不符合第39条规定的情形",

            "劳动者不符合第三十九条",
            "劳动者不符合第三十九条规定的情形",

            "不存在劳动合同法第39条规定的情形",
            "不存在劳动合同法第三十九条规定的情形",

            "不存在《劳动合同法》第39条规定的情形",
            "不存在《劳动合同法》第三十九条规定的情形",

            "劳动者不存在劳动合同法第39条规定的情形",
            "劳动者不存在劳动合同法第三十九条规定的情形",

            "劳动者不存在《劳动合同法》第39条规定的情形",
            "劳动者不存在《劳动合同法》第三十九条规定的情形",
        ]

        if contains_any(
            question,
            article_39_negative_patterns,
        ):

            return ConditionResult(
                condition=condition,
                status=SATISFIED,
                reason=(
                    "用户明确陈述劳动者不存在"
                    "《劳动合同法》第三十九条规定的情形，"
                    "因此该排除情形未被触发。"
                ),
                condition_type=EXCLUSION,
            )

        article_39_positive_patterns = [

            "存在第39条情形",
            "存在第39条规定的情形",

            "存在第三十九条情形",
            "存在第三十九条规定的情形",

            "符合第39条",
            "符合第39条规定的情形",

            "符合第三十九条",
            "符合第三十九条规定的情形",

            "劳动者有第39条情形",
            "劳动者有第39条规定的情形",

            "劳动者有第三十九条情形",
            "劳动者有第三十九条规定的情形",

            "劳动者存在第39条",
            "劳动者存在第39条规定的情形",

            "劳动者存在第三十九条",
            "劳动者存在第三十九条规定的情形",

            "存在劳动合同法第39条规定的情形",
            "存在劳动合同法第三十九条规定的情形",

            "存在《劳动合同法》第39条规定的情形",
            "存在《劳动合同法》第三十九条规定的情形",

            "符合劳动合同法第39条规定的情形",
            "符合劳动合同法第三十九条规定的情形",

            "符合《劳动合同法》第39条规定的情形",
            "符合《劳动合同法》第三十九条规定的情形",

            "劳动者存在劳动合同法第39条规定的情形",
            "劳动者存在劳动合同法第三十九条规定的情形",

            "劳动者存在《劳动合同法》第39条规定的情形",
            "劳动者存在《劳动合同法》第三十九条规定的情形",
        ]

        if contains_any(
            question,
            article_39_positive_patterns,
        ):

            return ConditionResult(
                condition=condition,
                status=NOT_SATISFIED,
                reason=(
                    "用户明确提供劳动者存在"
                    "《劳动合同法》第三十九条规定情形，"
                    "因此核心规则的该排除条件成立。"
                ),
                condition_type=EXCLUSION,
            )

        return ConditionResult(
            condition=condition,
            status=UNKNOWN,
            reason=(
                "用户没有提供足够事实确认劳动者是否存在"
                "《劳动合同法》第三十九条规定的情形。"
            ),
            condition_type=EXCLUSION,
        )

    # ========================================================
    # 第40条第一项
    # ========================================================

    if (
        condition
        == "劳动者存在《劳动合同法》第四十条第一项规定的情形"
    ):

        article_40_1_negative_patterns = [

            "劳动者不存在第40条第一项情形",
            "劳动者不存在第40条第一项规定的情形",

            "劳动者不存在第四十条第一项情形",
            "劳动者不存在第四十条第一项规定的情形",

            "劳动者不存在第40条第1项情形",
            "劳动者不存在第40条第1项规定的情形",

            "劳动者不存在第四十条第1项情形",
            "劳动者不存在第四十条第1项规定的情形",

            "不存在第40条第一项情形",
            "不存在第40条第一项规定的情形",

            "不存在第四十条第一项情形",
            "不存在第四十条第一项规定的情形",

            "不存在第40条第1项情形",
            "不存在第40条第1项规定的情形",

            "不存在第四十条第1项情形",
            "不存在第四十条第1项规定的情形",

            "不存在劳动合同法第40条第一项规定的情形",
            "不存在劳动合同法第四十条第一项规定的情形",

            "不存在《劳动合同法》第40条第一项规定的情形",
            "不存在《劳动合同法》第四十条第一项规定的情形",

            "劳动者不存在劳动合同法第40条第一项规定的情形",
            "劳动者不存在劳动合同法第四十条第一项规定的情形",

            "劳动者不存在《劳动合同法》第40条第一项规定的情形",
            "劳动者不存在《劳动合同法》第四十条第一项规定的情形",
        ]

        if contains_any(
            question,
            article_40_1_negative_patterns,
        ):

            return ConditionResult(
                condition=condition,
                status=SATISFIED,
                reason=(
                    "用户明确陈述劳动者不存在"
                    "《劳动合同法》第四十条第一项规定的情形，"
                    "因此该排除情形未被触发。"
                ),
                condition_type=EXCLUSION,
            )

        article_40_1_positive_patterns = [

            "存在第40条第一项情形",
            "存在第40条第一项规定的情形",

            "存在第四十条第一项情形",
            "存在第四十条第一项规定的情形",

            "存在第40条第1项情形",
            "存在第40条第1项规定的情形",

            "存在第四十条第1项情形",
            "存在第四十条第1项规定的情形",

            "符合第40条第一项",
            "符合第40条第一项规定的情形",

            "符合第四十条第一项",
            "符合第四十条第一项规定的情形",

            "符合第40条第1项",
            "符合第40条第1项规定的情形",

            "符合第四十条第1项",
            "符合第四十条第1项规定的情形",

            "劳动者存在劳动合同法第四十条第一项规定的情形",
            "劳动者存在《劳动合同法》第四十条第一项规定的情形",
        ]

        if contains_any(
            question,
            article_40_1_positive_patterns,
        ):

            return ConditionResult(
                condition=condition,
                status=NOT_SATISFIED,
                reason=(
                    "用户明确提供劳动者存在"
                    "《劳动合同法》第四十条第一项规定的情形。"
                ),
                condition_type=EXCLUSION,
            )

        return ConditionResult(
            condition=condition,
            status=UNKNOWN,
            reason=(
                "用户没有提供足够事实确认劳动者是否存在"
                "《劳动合同法》第四十条第一项规定的情形。"
            ),
            condition_type=EXCLUSION,
        )

    # ========================================================
    # 第40条第二项
    # ========================================================

    if (
        condition
        == "劳动者存在《劳动合同法》第四十条第二项规定的情形"
    ):

        article_40_2_negative_patterns = [

            "劳动者不存在第40条第二项情形",
            "劳动者不存在第40条第二项规定的情形",

            "劳动者不存在第四十条第二项情形",
            "劳动者不存在第四十条第二项规定的情形",

            "劳动者不存在第40条第2项情形",
            "劳动者不存在第40条第2项规定的情形",

            "劳动者不存在第四十条第2项情形",
            "劳动者不存在第四十条第2项规定的情形",

            "不存在第40条第二项情形",
            "不存在第40条第二项规定的情形",

            "不存在第四十条第二项情形",
            "不存在第四十条第二项规定的情形",

            "不存在第40条第2项情形",
            "不存在第40条第2项规定的情形",

            "不存在第四十条第2项情形",
            "不存在第四十条第2项规定的情形",

            "不存在劳动合同法第40条第二项规定的情形",
            "不存在劳动合同法第四十条第二项规定的情形",

            "不存在《劳动合同法》第40条第二项规定的情形",
            "不存在《劳动合同法》第四十条第二项规定的情形",

            "劳动者不存在劳动合同法第40条第二项规定的情形",
            "劳动者不存在劳动合同法第四十条第二项规定的情形",

            "劳动者不存在《劳动合同法》第40条第二项规定的情形",
            "劳动者不存在《劳动合同法》第四十条第二项规定的情形",
        ]

        if contains_any(
            question,
            article_40_2_negative_patterns,
        ):

            return ConditionResult(
                condition=condition,
                status=SATISFIED,
                reason=(
                    "用户明确陈述劳动者不存在"
                    "《劳动合同法》第四十条第二项规定的情形，"
                    "因此该排除情形未被触发。"
                ),
                condition_type=EXCLUSION,
            )

        article_40_2_positive_patterns = [

            "存在第40条第二项情形",
            "存在第40条第二项规定的情形",

            "存在第四十条第二项情形",
            "存在第四十条第二项规定的情形",

            "存在第40条第2项情形",
            "存在第40条第2项规定的情形",

            "存在第四十条第2项情形",
            "存在第四十条第2项规定的情形",

            "符合第40条第二项",
            "符合第40条第二项规定的情形",

            "符合第四十条第二项",
            "符合第四十条第二项规定的情形",

            "符合第40条第2项",
            "符合第40条第2项规定的情形",

            "符合第四十条第2项",
            "符合第四十条第2项规定的情形",

            "劳动者存在劳动合同法第四十条第二项规定的情形",
            "劳动者存在《劳动合同法》第四十条第二项规定的情形",
        ]

        if contains_any(
            question,
            article_40_2_positive_patterns,
        ):

            return ConditionResult(
                condition=condition,
                status=NOT_SATISFIED,
                reason=(
                    "用户明确提供劳动者存在"
                    "《劳动合同法》第四十条第二项规定的情形。"
                ),
                condition_type=EXCLUSION,
            )

        return ConditionResult(
            condition=condition,
            status=UNKNOWN,
            reason=(
                "用户没有提供足够事实确认劳动者是否存在"
                "《劳动合同法》第四十条第二项规定的情形。"
            ),
            condition_type=EXCLUSION,
        )

    # ========================================================
    # EXCEPTION
    # ========================================================

    if condition == "劳动者提出订立固定期限劳动合同":

        fixed_term_proposal_patterns = [

            "劳动者提出订立固定期限劳动合同",

            "劳动者要求签固定期限劳动合同",

            "劳动者要求订立固定期限劳动合同",

            "员工提出订立固定期限劳动合同",

            "员工要求签固定期限劳动合同",

            "员工要求订立固定期限劳动合同",
        ]

        # ----------------------------------------------------
        # 明确提出固定期限
        # ----------------------------------------------------

        if contains_any(
            question,
            fixed_term_proposal_patterns,
        ):

            return ConditionResult(
                condition=condition,
                status=NOT_SATISFIED,
                reason=(
                    "用户明确陈述劳动者提出订立固定期限劳动合同，"
                    "因此固定期限例外条件成立。"
                ),
                condition_type=EXCEPTION,
            )

        # ----------------------------------------------------
        # 明确没有提出固定期限
        #
        # 注意：
        #
        # EXCEPTION 的 SATISFIED 表示：
        #
        #     例外条件未被触发。
        #
        # 这是当前内部状态模型。
        # ----------------------------------------------------

        fixed_term_negative_patterns = [

            "劳动者没有提出订立固定期限劳动合同",

            "劳动者未提出订立固定期限劳动合同",

            "劳动者没有提出签订固定期限劳动合同",

            "劳动者未提出签订固定期限劳动合同",

            "劳动者没有要求签固定期限劳动合同",

            "劳动者未要求签固定期限劳动合同",

            "劳动者没有要求订立固定期限劳动合同",

            "劳动者未要求订立固定期限劳动合同",

            "员工没有提出订立固定期限劳动合同",

            "员工未提出订立固定期限劳动合同",
        ]

        if contains_any(
            question,
            fixed_term_negative_patterns,
        ):

            return ConditionResult(
                condition=condition,
                status=SATISFIED,
                reason=(
                    "用户明确陈述劳动者没有提出"
                    "订立固定期限劳动合同，"
                    "因此固定期限例外条件未被触发。"
                ),
                condition_type=EXCEPTION,
            )

        return ConditionResult(
            condition=condition,
            status=UNKNOWN,
            reason=(
                "用户没有明确说明劳动者是否提出订立"
                "固定期限劳动合同；不能因为用户没有提及"
                "就直接认定该例外不存在。"
            ),
            condition_type=EXCEPTION,
        )

    # ========================================================
    # Unknown Condition
    # ========================================================

    return ConditionResult(
        condition=condition,
        status=UNKNOWN,
        reason=(
            "当前 Decision Engine 没有针对该法律条件建立"
            "明确的事实匹配规则。"
        ),
        condition_type=condition_type,
    )


# ============================================================
# Evaluate Rule
# ============================================================

def evaluate_rule(
    rule: Dict[str, Any],
    question: str,
    explicit_facts: List[str],
    contract_sequence: ContractSequence,
) -> Tuple[
    str,
    List[ConditionResult],
]:
    """
    对核心法律规则执行完整条件评估。

    固定：

        REQUIRED   = 4
        EXCLUSION  = 3
        EXCEPTION  = 1
        TOTAL      = 8
    """

    condition_results: List[
        ConditionResult
    ] = []

    # --------------------------------------------------------
    # REQUIRED
    # --------------------------------------------------------

    for condition in REQUIRED_CONDITIONS:

        result = match_condition(
            condition=condition,
            question=question,
            contract_sequence=contract_sequence,
            explicit_facts=explicit_facts,
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
            condition=condition,
            question=question,
            contract_sequence=contract_sequence,
            explicit_facts=explicit_facts,
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
            condition=condition,
            question=question,
            contract_sequence=contract_sequence,
            explicit_facts=explicit_facts,
            condition_type=EXCEPTION,
        )

        condition_results.append(
            result
        )

    # --------------------------------------------------------
    # Structural Validation
    # --------------------------------------------------------

    validate_condition_structure(
        condition_results
    )

    # --------------------------------------------------------
    # Decision
    # --------------------------------------------------------

    statuses = [
        item.status
        for item in condition_results
    ]

    if NOT_SATISFIED in statuses:

        decision = NOT_ESTABLISHED

    elif UNKNOWN in statuses:

        decision = CONDITIONAL

    else:

        decision = DEFINITE

    return (
        decision,
        condition_results,
    )


# ============================================================
# Validate Condition Structure
# ============================================================

def validate_condition_structure(
    condition_results: List[ConditionResult],
) -> None:
    """
    验证固定 8 条 ConditionResult。

    REQUIRED:
        4

    EXCLUSION:
        3

    EXCEPTION:
        1

    TOTAL:
        8
    """

    if len(condition_results) != 8:

        raise ValueError(
            "Legal Decision Engine V6.0-15: "
            "ConditionResult 数量必须为 8，"
            f"实际为 {len(condition_results)}。"
        )

    required_count = sum(
        1
        for item in condition_results
        if item.condition_type == REQUIRED
    )

    exclusion_count = sum(
        1
        for item in condition_results
        if item.condition_type == EXCLUSION
    )

    exception_count = sum(
        1
        for item in condition_results
        if item.condition_type == EXCEPTION
    )

    if required_count != 4:

        raise ValueError(
            "Legal Decision Engine V6.0-15: "
            "REQUIRED 条件必须为 4，"
            f"实际为 {required_count}。"
        )

    if exclusion_count != 3:

        raise ValueError(
            "Legal Decision Engine V6.0-15: "
            "EXCLUSION 条件必须为 3，"
            f"实际为 {exclusion_count}。"
        )

    if exception_count != 1:

        raise ValueError(
            "Legal Decision Engine V6.0-15: "
            "EXCEPTION 条件必须为 1，"
            f"实际为 {exception_count}。"
        )

    if (
        required_count
        + exclusion_count
        + exception_count
        != 8
    ):

        raise ValueError(
            "Legal Decision Engine V6.0-15: "
            "ConditionResult 分类总数不等于 8。"
        )

    conditions = [
        item.condition
        for item in condition_results
    ]

    if len(set(conditions)) != len(
        conditions
    ):

        raise ValueError(
            "Legal Decision Engine V6.0-15: "
            "ConditionResult 中存在重复法律条件。"
        )

    expected_required = set(
        REQUIRED_CONDITIONS
    )

    expected_exclusion = set(
        EXCLUSION_CONDITIONS
    )

    expected_exception = set(
        EXCEPTION_CONDITIONS
    )

    actual_required = {
        item.condition
        for item in condition_results
        if item.condition_type == REQUIRED
    }

    actual_exclusion = {
        item.condition
        for item in condition_results
        if item.condition_type == EXCLUSION
    }

    actual_exception = {
        item.condition
        for item in condition_results
        if item.condition_type == EXCEPTION
    }

    if actual_required != expected_required:

        raise ValueError(
            "Legal Decision Engine V6.0-15: "
            "REQUIRED 条件集合不正确。"
        )

    if actual_exclusion != expected_exclusion:

        raise ValueError(
            "Legal Decision Engine V6.0-15: "
            "EXCLUSION 条件集合不正确。"
        )

    if actual_exception != expected_exception:

        raise ValueError(
            "Legal Decision Engine V6.0-15: "
            "EXCEPTION 条件集合不正确。"
        )


# ============================================================
# Select Core Rule
# ============================================================

def select_core_rule(
    rules: Optional[List[Dict[str, Any]]],
    fallback_rule: Dict[str, Any],
) -> Dict[str, Any]:
    """
    从 Retriever 返回的规则中选择第十四条核心规则。

    Retriever 可以返回多个法律规则。

    Decision Engine 只使用：

        《劳动合同法》第十四条

    的固定结构化条件体系。

    即使 Retriever 返回的规则缺少条件，
    也不会允许其覆盖固定 8 条条件。
    """

    if not rules:

        return fallback_rule

    for rule in rules:

        if not isinstance(
            rule,
            dict,
        ):

            continue

        law_name = normalize_text(
            rule.get("law_name")
        )

        article = normalize_text(
            rule.get("article")
        )

        rule_text = normalize_text(
            rule.get("rule_text")
        )

        matched = (
            "劳动合同法" in law_name
            and (
                "第十四条" in article
                or "第14条" in article
                or (
                    "十四条" in rule_text
                    and "无固定期限" in rule_text
                )
            )
        )

        if not matched:
            continue

        merged = dict(
            fallback_rule
        )

        merged.update(
            rule
        )

        # ----------------------------------------------------
        # 强制使用 Decision Engine 固定条件
        # ----------------------------------------------------

        merged["conditions"] = list(
            REQUIRED_CONDITIONS
        )

        merged["exclusion_conditions"] = list(
            EXCLUSION_CONDITIONS
        )

        merged["exceptions"] = list(
            EXCEPTION_CONDITIONS
        )

        return merged

    return fallback_rule


# ============================================================
# Decision Explanation
# ============================================================

def build_decision_explanation(
    decision: str,
    condition_results: List[ConditionResult],
    contract_sequence: ContractSequence,
) -> str:
    """
    根据已经产生的 ConditionResult 构建结构化说明。

    注意：

        这里不重新进行法律判断。
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

    not_satisfied = [
        item.condition
        for item in condition_results
        if item.status == NOT_SATISFIED
    ]

    parts: List[str] = []

    parts.append(
        f"Decision={decision}"
    )

    if contract_sequence.count:

        parts.append(
            "合同序列="
            f"{contract_sequence.count}次/"
            f"{contract_sequence.term_type or 'unknown'}"
        )

    if satisfied:

        parts.append(
            "已满足条件="
            + "；".join(satisfied)
        )

    if unknown:

        parts.append(
            "尚不确定条件="
            + "；".join(unknown)
        )

    if not_satisfied:

        parts.append(
            "不满足条件="
            + "；".join(not_satisfied)
        )

    return "。".join(parts)


# ============================================================
# Make Decision
# ============================================================

def make_decision(
    question: str,
    rules: Optional[List[Dict[str, Any]]] = None,
) -> DecisionResult:
    """
    对用户问题执行完整法律决策。

    输入：

        question
            用户法律问题

        rules
            Retriever 返回的规则。
            可以为空。

    输出：

        DecisionResult
    """

    question = normalize_text(
        question
    )

    # --------------------------------------------------------
    # Explicit Facts
    # --------------------------------------------------------

    explicit_facts = extract_explicit_facts(
        question
    )

    # --------------------------------------------------------
    # Contract Sequence
    # --------------------------------------------------------

    contract_sequence = extract_contract_sequence(
        question
    )

    # --------------------------------------------------------
    # Core Rule
    # --------------------------------------------------------

    core_rule = build_core_rule()

    selected_rule = select_core_rule(
        rules=rules,
        fallback_rule=core_rule,
    )

    # --------------------------------------------------------
    # Rule Dependency
    # --------------------------------------------------------

    dependency = build_rule_dependency(
        question=question,
        contract_sequence=contract_sequence,
    )

    # --------------------------------------------------------
    # Evaluate
    # --------------------------------------------------------

    decision, condition_results = evaluate_rule(
        rule=selected_rule,
        question=question,
        explicit_facts=explicit_facts,
        contract_sequence=contract_sequence,
    )

    # --------------------------------------------------------
    # Explanation
    # --------------------------------------------------------

    explanation = build_decision_explanation(
        decision=decision,
        condition_results=condition_results,
        contract_sequence=contract_sequence,
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
        selected_rule=selected_rule,
        explanation=explanation,
        engine_version=ENGINE_VERSION,
    )

    # --------------------------------------------------------
    # Final Validation
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

    # --------------------------------------------------------
    # UNKNOWN → 不能 DEFINITE
    # --------------------------------------------------------

    if (
        unknown_count > 0
        and decision.decision == DEFINITE
    ):

        raise ValueError(
            "Legal Decision Engine V6.0-15: "
            "存在 UNKNOWN 条件时不能输出 DEFINITE。"
        )

    # --------------------------------------------------------
    # NOT_SATISFIED → 必须 NOT_ESTABLISHED
    # --------------------------------------------------------

    if (
        not_satisfied_count > 0
        and decision.decision != NOT_ESTABLISHED
    ):

        raise ValueError(
            "Legal Decision Engine V6.0-15: "
            "存在 NOT_SATISFIED 条件时必须输出 "
            "NOT_ESTABLISHED。"
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
            "Legal Decision Engine V6.0-15: "
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
        "Explanation:"
    )

    print(
        f"  {decision.explanation}"
    )

    print("=" * 70)


# ============================================================
# Test Helpers
# ============================================================

def assert_condition_status(
    decision: DecisionResult,
    condition: str,
    expected_status: str,
) -> None:
    """
    检查指定法律条件的状态。
    """

    result = next(
        (
            item
            for item in decision.condition_results
            if item.condition == condition
        ),
        None,
    )

    assert result is not None, (
        f"未找到条件：{condition}"
    )

    assert result.status == expected_status, (
        f"条件：{condition}\n"
        f"期望：{expected_status}\n"
        f"实际：{result.status}\n"
        f"原因：{result.reason}"
    )


# ============================================================
# Component Test
# ============================================================

def run_component_test() -> None:
    """
    V6.0-15 Component Test。

    验证核心问题：

        公司连续签订三次固定期限劳动合同后，
        是否必须签订无固定期限劳动合同？

    预期：

        Decision = CONDITIONAL

        REQUIRED = 4
        EXCLUSION = 3
        EXCEPTION = 1

        TOTAL = 8

        SATISFIED：

            连续订立二次固定期限劳动合同
            存在后续订立的劳动合同

        UNKNOWN：

            续订劳动合同
            劳动者提出或者同意续订、订立劳动合同
            第39条
            第40条第一项
            第40条第二项
            劳动者提出固定期限
    """

    print()
    print("=" * 70)

    print(
        f"Legal Decision Engine {ENGINE_VERSION}"
    )

    print("=" * 70)

    question = (
        "公司连续签订三次固定期限劳动合同后，"
        "是否必须签订无固定期限劳动合同？"
    )

    print()

    print(
        "Test Question:"
    )

    print(
        question
    )

    decision = make_decision(
        question
    )

    print_decision_result(
        decision
    )

    print()

    print(
        "Running assertions..."
    )

    # --------------------------------------------------------
    # Decision
    # --------------------------------------------------------

    assert decision.decision == CONDITIONAL

    # --------------------------------------------------------
    # Explicit Fact
    # --------------------------------------------------------

    assert (
        "公司连续签订三次固定期限劳动合同"
        in decision.explicit_facts
    )

    # --------------------------------------------------------
    # Contract Sequence
    # --------------------------------------------------------

    assert decision.contract_sequence is not None

    assert (
        decision.contract_sequence.count
        == 3
    )

    assert (
        decision.contract_sequence.term_type
        == "fixed"
    )

    assert (
        decision.contract_sequence.continuous
        is True
    )

    # --------------------------------------------------------
    # Condition Count
    # --------------------------------------------------------

    assert (
        len(decision.condition_results)
        == 8
    )

    assert (
        len(get_required_results(decision))
        == 4
    )

    assert (
        len(get_exclusion_results(decision))
        == 3
    )

    assert (
        len(get_exception_results(decision))
        == 1
    )

    # --------------------------------------------------------
    # Required 1
    # --------------------------------------------------------

    assert_condition_status(
        decision,
        "连续订立二次固定期限劳动合同",
        SATISFIED,
    )

    # --------------------------------------------------------
    # Required 2
    # --------------------------------------------------------

    assert_condition_status(
        decision,
        "存在后续订立的劳动合同",
        SATISFIED,
    )

    # --------------------------------------------------------
    # Required 3
    # --------------------------------------------------------

    assert_condition_status(
        decision,
        "续订劳动合同",
        UNKNOWN,
    )

    # --------------------------------------------------------
    # Required 4
    # --------------------------------------------------------

    assert_condition_status(
        decision,
        "劳动者提出或者同意续订、订立劳动合同",
        UNKNOWN,
    )

    # --------------------------------------------------------
    # Exclusion
    # --------------------------------------------------------

    assert_condition_status(
        decision,
        "劳动者存在《劳动合同法》第三十九条规定的情形",
        UNKNOWN,
    )

    assert_condition_status(
        decision,
        "劳动者存在《劳动合同法》第四十条第一项规定的情形",
        UNKNOWN,
    )

    assert_condition_status(
        decision,
        "劳动者存在《劳动合同法》第四十条第二项规定的情形",
        UNKNOWN,
    )

    # --------------------------------------------------------
    # Exception
    # --------------------------------------------------------

    assert_condition_status(
        decision,
        "劳动者提出订立固定期限劳动合同",
        UNKNOWN,
    )

    # --------------------------------------------------------
    # Satisfied Set
    # --------------------------------------------------------

    assert set(
        decision.satisfied_conditions
    ) == {
        "连续订立二次固定期限劳动合同",
        "存在后续订立的劳动合同",
    }

    # --------------------------------------------------------
    # Unknown Set
    # --------------------------------------------------------

    assert set(
        decision.unknown_conditions
    ) == {
        "续订劳动合同",
        "劳动者提出或者同意续订、订立劳动合同",
        "劳动者存在《劳动合同法》第三十九条规定的情形",
        "劳动者存在《劳动合同法》第四十条第一项规定的情形",
        "劳动者存在《劳动合同法》第四十条第二项规定的情形",
        "劳动者提出订立固定期限劳动合同",
    }

    assert (
        len(decision.not_satisfied_conditions)
        == 0
    )

    validate_decision_result(
        decision
    )

    print()

    print(
        "All Component Test assertions passed."
    )

    print()

    print(
        "============================================================"
    )

    print(
        "V6.0-15 Component Test PASSED"
    )

    print(
        "============================================================"
    )


# ============================================================
# Additional Tests
# ============================================================

def run_additional_tests() -> None:
    """
    V6.0-15 额外测试。

    重点验证：

        1. 三次合同
        2. 明确续订 + 明确同意
        3. 明确第39条排除
        4. 明确“不存在第39条”
        5. 明确“不存在第40条第一项”
        6. 明确“不存在第40条第二项”
        7. 明确“没有提出固定期限”
        8. 准备续订不能等同于已经续订
        9. 同意续订不能自动等于已经完成续订
    """

    print()
    print("=" * 70)

    print(
        "Additional Tests"
    )

    print("=" * 70)

    # ========================================================
    # Test 1
    # 三次固定期限
    # ========================================================

    question_1 = (
        "公司连续签订三次固定期限劳动合同后，"
        "是否必须签订无固定期限劳动合同？"
    )

    result_1 = make_decision(
        question_1
    )

    assert result_1.decision == CONDITIONAL

    assert (
        len(result_1.condition_results)
        == 8
    )

    # ========================================================
    # Test 2
    # 明确续订 + 劳动者同意
    # ========================================================

    question_2 = (
        "公司连续签订两次固定期限劳动合同，"
        "之后续订劳动合同，劳动者同意续订，"
        "劳动者没有提出订立固定期限劳动合同。"
    )

    result_2 = make_decision(
        question_2
    )

    assert_condition_status(
        result_2,
        "连续订立二次固定期限劳动合同",
        SATISFIED,
    )

    assert_condition_status(
        result_2,
        "存在后续订立的劳动合同",
        SATISFIED,
    )

    assert_condition_status(
        result_2,
        "续订劳动合同",
        SATISFIED,
    )

    assert_condition_status(
        result_2,
        "劳动者提出或者同意续订、订立劳动合同",
        SATISFIED,
    )

    # --------------------------------------------------------
    # 明确没有提出固定期限
    # --------------------------------------------------------

    assert_condition_status(
        result_2,
        "劳动者提出订立固定期限劳动合同",
        SATISFIED,
    )

    # ========================================================
    # Test 3
    # 明确存在第39条
    # ========================================================

    question_3 = (
        "公司连续签订三次固定期限劳动合同，"
        "劳动者存在劳动合同法第三十九条规定的情形，"
        "是否必须签订无固定期限劳动合同？"
    )

    result_3 = make_decision(
        question_3
    )

    assert_condition_status(
        result_3,
        "劳动者存在《劳动合同法》第三十九条规定的情形",
        NOT_SATISFIED,
    )

    assert (
        result_3.decision
        == NOT_ESTABLISHED
    )

    # ========================================================
    # Test 4
    # 明确不存在第39条
    # ========================================================

    question_4 = (
        "公司连续签订三次固定期限劳动合同，"
        "劳动者不存在劳动合同法第三十九条规定的情形。"
    )

    result_4 = make_decision(
        question_4
    )

    assert_condition_status(
        result_4,
        "劳动者存在《劳动合同法》第三十九条规定的情形",
        SATISFIED,
    )

    # ========================================================
    # Test 5
    # 明确不存在第40条第一项
    # ========================================================

    question_5 = (
        "公司连续签订三次固定期限劳动合同，"
        "劳动者不存在劳动合同法第四十条第一项规定的情形。"
    )

    result_5 = make_decision(
        question_5
    )

    assert_condition_status(
        result_5,
        "劳动者存在《劳动合同法》第四十条第一项规定的情形",
        SATISFIED,
    )

    # ========================================================
    # Test 6
    # 明确不存在第40条第二项
    # ========================================================

    question_6 = (
        "公司连续签订三次固定期限劳动合同，"
        "劳动者不存在劳动合同法第四十条第二项规定的情形。"
    )

    result_6 = make_decision(
        question_6
    )

    assert_condition_status(
        result_6,
        "劳动者存在《劳动合同法》第四十条第二项规定的情形",
        SATISFIED,
    )

    # ========================================================
    # Test 7
    # 明确没有提出固定期限
    # ========================================================

    question_7 = (
        "公司连续签订三次固定期限劳动合同，"
        "劳动者没有提出订立固定期限劳动合同。"
    )

    result_7 = make_decision(
        question_7
    )

    assert_condition_status(
        result_7,
        "劳动者提出订立固定期限劳动合同",
        SATISFIED,
    )

    # ========================================================
    # Test 8
    # 准备续订不能证明已经续订
    # ========================================================

    question_8 = (
        "公司连续签订两次固定期限劳动合同，"
        "公司准备与劳动者续订劳动合同。"
    )

    result_8 = make_decision(
        question_8
    )

    assert_condition_status(
        result_8,
        "续订劳动合同",
        UNKNOWN,
    )

    assert_condition_status(
        result_8,
        "存在后续订立的劳动合同",
        UNKNOWN,
    )

    # ========================================================
    # Test 9
    # 同意续订不能自动证明已经完成续订
    # ========================================================

    question_9 = (
        "公司连续签订两次固定期限劳动合同，"
        "劳动者同意续订劳动合同。"
    )

    result_9 = make_decision(
        question_9
    )

    assert_condition_status(
        result_9,
        "劳动者提出或者同意续订、订立劳动合同",
        SATISFIED,
    )

    assert_condition_status(
        result_9,
        "续订劳动合同",
        UNKNOWN,
    )

    assert_condition_status(
        result_9,
        "存在后续订立的劳动合同",
        UNKNOWN,
    )

    # ========================================================
    # Test 10
    # 已经续订 + 同意续订
    # ========================================================

    question_10 = (
        "公司连续签订两次固定期限劳动合同，"
        "之后已经续订劳动合同，"
        "劳动者也同意续订，"
        "劳动者没有提出订立固定期限劳动合同。"
    )

    result_10 = make_decision(
        question_10
    )

    assert_condition_status(
        result_10,
        "存在后续订立的劳动合同",
        SATISFIED,
    )

    assert_condition_status(
        result_10,
        "续订劳动合同",
        SATISFIED,
    )

    assert_condition_status(
        result_10,
        "劳动者提出或者同意续订、订立劳动合同",
        SATISFIED,
    )

    assert_condition_status(
        result_10,
        "劳动者提出订立固定期限劳动合同",
        SATISFIED,
    )

    # ========================================================
    # Print
    # ========================================================

    print()

    print(
        "Additional tests passed."
    )

    print()

    print(
        "V6.0-15 negative-fact tests PASSED."
    )


# ============================================================
# Manual Scenario Test
# ============================================================

def run_manual_scenario_tests() -> None:
    """
    输出关键场景的完整 DecisionResult。

    该测试主要用于人工观察，
    不作为 RAG Pipeline 的正式输入。

    V6.0-15 边界回归测试：

    A. 三次固定期限合同
    B. 已经续订 + 劳动者同意
    C. 准备续订
    D. 存在第39条情形

    E. 两次合同 + 后来已经续签
    F. 两次合同 + 准备续签
    G. 两次合同 + 计划续签
    H. 两次合同 + 劳动者同意续订
    I. 已经续订 + 劳动者没有同意
    J. 已经续订 + 劳动者同意 + 提出订立固定期限合同

    这些场景用于验证：

    - 已经完成的续订与准备续订不能混淆
    - 后续合同与续订事实之间的逻辑关系
    - 劳动者同意不能被自动推定
    - EXCEPTION 条件能够正确识别
    """

    scenarios = [

        # ====================================================
        # 场景 A
        # ====================================================

        (
            "场景 A：三次固定期限合同",
            (
                "公司连续签订三次固定期限劳动合同后，"
                "是否必须签订无固定期限劳动合同？"
            ),
        ),

        # ====================================================
        # 场景 B
        # ====================================================

        (
            "场景 B：已经续订且劳动者同意",
            (
                "公司连续签订两次固定期限劳动合同，"
                "之后已经续订劳动合同，"
                "劳动者同意续订，"
                "劳动者没有提出订立固定期限劳动合同。"
            ),
        ),

        # ====================================================
        # 场景 C
        # ====================================================

        (
            "场景 C：准备续订",
            (
                "公司连续签订两次固定期限劳动合同，"
                "公司准备与劳动者续订劳动合同。"
            ),
        ),

        # ====================================================
        # 场景 D
        # ====================================================

        (
            "场景 D：存在第39条",
            (
                "公司连续签订三次固定期限劳动合同，"
                "劳动者存在劳动合同法第三十九条规定的情形。"
            ),
        ),

        # ====================================================
        # 场景 E
        # 两次合同 + 后来已经续签
        # ====================================================

        (
            "场景 E：后来已经续签",
            (
                "公司连续签订两次固定期限劳动合同，"
                "后来已经续签劳动合同。"
            ),
        ),

        # ====================================================
        # 场景 F
        # 两次合同 + 准备续签
        # ====================================================

        (
            "场景 F：准备续签",
            (
                "公司连续签订两次固定期限劳动合同，"
                "准备续签劳动合同。"
            ),
        ),

        # ====================================================
        # 场景 G
        # 两次合同 + 计划续签
        # ====================================================

        (
            "场景 G：计划续签",
            (
                "公司连续签订两次固定期限劳动合同，"
                "计划续签劳动合同。"
            ),
        ),

        # ====================================================
        # 场景 H
        # 两次合同 + 劳动者同意续订
        # ====================================================

        (
            "场景 H：劳动者同意续订",
            (
                "公司连续签订两次固定期限劳动合同，"
                "劳动者同意续订劳动合同。"
            ),
        ),

        # ====================================================
        # 场景 I
        # 已经续订 + 劳动者没有同意
        # ====================================================

        (
            "场景 I：已经续订，但劳动者没有同意",
            (
                "公司连续签订两次固定期限劳动合同，"
                "已经续订劳动合同，"
                "但劳动者没有同意续订。"
            ),
        ),

        # ====================================================
        # 场景 J
        # 已经续订 + 劳动者同意 + 提出固定期限
        # ====================================================

        (
            "场景 J：例外条件被触发",
            (
                "公司连续签订两次固定期限劳动合同，"
                "之后已经续订劳动合同，"
                "劳动者同意续订，"
                "并且劳动者提出订立固定期限劳动合同。"
            ),
        ),
    ]

    # ========================================================
    # 逐个执行场景
    # ========================================================

    for title, question in scenarios:

        print()
        print("=" * 70)

        print(
            title
        )

        print("=" * 70)

        print()

        print(
            f"问题：{question}"
        )

        decision = make_decision(
            question
        )

        print_decision_result(
            decision
        )


# ============================================================
# Regression Test
# ============================================================

def run_regression_tests() -> None:
    """
    V6.0-15 回归测试。

    将 A-J 场景从：

        人工观察

    提升为：

        自动断言。

    目标：

        每次修改 Decision Engine 后，
        可以快速确认核心逻辑没有回归。
    """

    print()
    print("=" * 70)

    print(
        "V6.0-15 Regression Tests"
    )

    print("=" * 70)

    scenarios = [

        {
            "name": "A",
            "question": (
                "公司连续签订三次固定期限劳动合同后，"
                "是否必须签订无固定期限劳动合同？"
            ),
            "decision": CONDITIONAL,
            "statuses": {
                "连续订立二次固定期限劳动合同":
                    SATISFIED,

                "存在后续订立的劳动合同":
                    SATISFIED,

                "续订劳动合同":
                    UNKNOWN,

                "劳动者提出或者同意续订、订立劳动合同":
                    UNKNOWN,

                "劳动者存在《劳动合同法》第三十九条规定的情形":
                    UNKNOWN,

                "劳动者存在《劳动合同法》第四十条第一项规定的情形":
                    UNKNOWN,

                "劳动者存在《劳动合同法》第四十条第二项规定的情形":
                    UNKNOWN,

                "劳动者提出订立固定期限劳动合同":
                    UNKNOWN,
            },
        },

        {
            "name": "B",
            "question": (
                "公司连续签订两次固定期限劳动合同，"
                "之后已经续订劳动合同，"
                "劳动者同意续订，"
                "劳动者没有提出订立固定期限劳动合同。"
            ),
            "decision": CONDITIONAL,
            "statuses": {
                "连续订立二次固定期限劳动合同":
                    SATISFIED,

                "存在后续订立的劳动合同":
                    SATISFIED,

                "续订劳动合同":
                    SATISFIED,

                "劳动者提出或者同意续订、订立劳动合同":
                    SATISFIED,

                "劳动者提出订立固定期限劳动合同":
                    SATISFIED,
            },
        },

        {
            "name": "C",
            "question": (
                "公司连续签订两次固定期限劳动合同，"
                "公司准备与劳动者续订劳动合同。"
            ),
            "decision": CONDITIONAL,
            "statuses": {
                "连续订立二次固定期限劳动合同":
                    SATISFIED,

                "存在后续订立的劳动合同":
                    UNKNOWN,

                "续订劳动合同":
                    UNKNOWN,

                "劳动者提出或者同意续订、订立劳动合同":
                    UNKNOWN,
            },
        },

        {
            "name": "D",
            "question": (
                "公司连续签订三次固定期限劳动合同，"
                "劳动者存在劳动合同法第三十九条规定的情形。"
            ),
            "decision": NOT_ESTABLISHED,
            "statuses": {
                "连续订立二次固定期限劳动合同":
                    SATISFIED,

                "存在后续订立的劳动合同":
                    SATISFIED,

                "劳动者存在《劳动合同法》第三十九条规定的情形":
                    NOT_SATISFIED,
            },
        },

        {
            "name": "E",
            "question": (
                "公司连续签订两次固定期限劳动合同，"
                "后来已经续签劳动合同。"
            ),
            "decision": CONDITIONAL,
            "statuses": {
                "连续订立二次固定期限劳动合同":
                    SATISFIED,

                "存在后续订立的劳动合同":
                    SATISFIED,

                "续订劳动合同":
                    SATISFIED,

                "劳动者提出或者同意续订、订立劳动合同":
                    UNKNOWN,
            },
        },

        {
            "name": "F",
            "question": (
                "公司连续签订两次固定期限劳动合同，"
                "准备续签劳动合同。"
            ),
            "decision": CONDITIONAL,
            "statuses": {
                "连续订立二次固定期限劳动合同":
                    SATISFIED,

                "存在后续订立的劳动合同":
                    UNKNOWN,

                "续订劳动合同":
                    UNKNOWN,
            },
        },

        {
            "name": "G",
            "question": (
                "公司连续签订两次固定期限劳动合同，"
                "计划续签劳动合同。"
            ),
            "decision": CONDITIONAL,
            "statuses": {
                "连续订立二次固定期限劳动合同":
                    SATISFIED,

                "存在后续订立的劳动合同":
                    UNKNOWN,

                "续订劳动合同":
                    UNKNOWN,
            },
        },

        {
            "name": "H",
            "question": (
                "公司连续签订两次固定期限劳动合同，"
                "劳动者同意续订劳动合同。"
            ),
            "decision": CONDITIONAL,
            "statuses": {
                "连续订立二次固定期限劳动合同":
                    SATISFIED,

                "存在后续订立的劳动合同":
                    UNKNOWN,

                "续订劳动合同":
                    UNKNOWN,

                "劳动者提出或者同意续订、订立劳动合同":
                    SATISFIED,
            },
        },

        {
            "name": "I",
            "question": (
                "公司连续签订两次固定期限劳动合同，"
                "已经续订劳动合同，"
                "但劳动者没有同意续订。"
            ),
            "decision": CONDITIONAL,
            "statuses": {
                "连续订立二次固定期限劳动合同":
                    SATISFIED,

                "存在后续订立的劳动合同":
                    SATISFIED,

                "续订劳动合同":
                    SATISFIED,

                "劳动者提出或者同意续订、订立劳动合同":
                    UNKNOWN,
            },
        },

        {
            "name": "J",
            "question": (
                "公司连续签订两次固定期限劳动合同，"
                "之后已经续订劳动合同，"
                "劳动者同意续订，"
                "并且劳动者提出订立固定期限劳动合同。"
            ),
            "decision": NOT_ESTABLISHED,
            "statuses": {
                "连续订立二次固定期限劳动合同":
                    SATISFIED,

                "存在后续订立的劳动合同":
                    SATISFIED,

                "续订劳动合同":
                    SATISFIED,

                "劳动者提出或者同意续订、订立劳动合同":
                    SATISFIED,

                "劳动者提出订立固定期限劳动合同":
                    NOT_SATISFIED,
            },
        },
    ]

    passed = 0

    failed = 0

    for scenario in scenarios:

        name = scenario["name"]

        question = scenario["question"]

        expected_decision = scenario["decision"]

        expected_statuses = scenario["statuses"]

        print()

        print(
            f"[Scenario {name}]"
        )

        try:

            decision = make_decision(
                question
            )

            assert (
                decision.decision
                == expected_decision
            ), (
                f"Decision 期望 "
                f"{expected_decision}，"
                f"实际 "
                f"{decision.decision}"
            )

            for (
                condition,
                expected_status,
            ) in expected_statuses.items():

                assert_condition_status(
                    decision,
                    condition,
                    expected_status,
                )

            print(
                f"  Scenario {name}: PASS"
            )

            passed += 1

        except AssertionError as exc:

            print(
                f"  Scenario {name}: FAIL"
            )

            print(
                f"  Reason: {exc}"
            )

            failed += 1

    print()
    print("=" * 70)

    print(
        "Regression Test Result"
    )

    print("=" * 70)

    print()

    print(
        f"PASS: {passed}"
    )

    print(
        f"FAIL: {failed}"
    )

    print()

    if failed == 0:

        print(
            "ALL REGRESSION TESTS PASSED"
        )

    else:

        raise AssertionError(
            f"Regression Tests failed: "
            f"{failed}"
        )


# ============================================================
# Module Entry
# ============================================================

def main() -> None:
    """
    模块入口。
    """

    print()
    print("=" * 70)

    print(
        f"Legal Decision Engine {ENGINE_VERSION}"
    )

    print("=" * 70)

    print()

    print(
        "请选择测试："
    )

    print()

    print(
        "1. Component Test"
    )

    print(
        "2. Additional Tests"
    )

    print(
        "3. 全部测试"
    )

    print(
        "4. Manual Scenario Tests"
    )

    print(
        "5. Regression Tests"
    )

    print()

    try:

        choice = input(
            "请输入 1、2、3、4 或 5："
        ).strip()

    except EOFError:

        choice = "1"

    if choice == "1":

        run_component_test()

    elif choice == "2":

        run_additional_tests()

    elif choice == "3":

        run_component_test()

        run_additional_tests()

    elif choice == "4":

        run_manual_scenario_tests()

    elif choice == "5":

        run_regression_tests()

    else:

        print(
            "输入无效，默认运行 Component Test。"
        )

        run_component_test()


# ============================================================
# Execute
# ============================================================

if __name__ == "__main__":

    main()