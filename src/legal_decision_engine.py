# -*- coding: utf-8 -*-

"""
RAG V6.0-14
Legal Decision Engine

============================================================
功能
============================================================

本模块负责：

    用户问题
        ↓
    显式事实提取
        ↓
    法律规则条件匹配
        ↓
    条件状态判断
        ↓
    综合法律决策
        ↓
    DecisionResult

============================================================
V6.0-14 核心修复
============================================================

1. Decision Engine 是唯一法律条件判断来源

2. ConditionResult 只能在本模块创建

3. 固定条件结构：

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

4. “连续签订三次固定期限劳动合同”是用户事实，
   不是法律规则条件本身。

5. “连续签订三次固定期限劳动合同”可以证明：

        连续订立二次固定期限劳动合同
            → SATISFIED

        存在后续订立的劳动合同
            → SATISFIED

   但不能仅凭该事实证明：

        续订劳动合同
            → UNKNOWN

        劳动者提出或者同意续订、订立劳动合同
            → UNKNOWN

6. UNKNOWN 不得被自动升级为 SATISFIED。

7. UNKNOWN 导致最终决策：

        CONDITIONAL

8. Decision Engine 不负责生成自然语言答案。

9. Decision Engine 不调用 Ollama。

10. Decision Engine 不负责修改 Retriever 返回的法律规则。

11. Decision Engine 输出 DecisionResult，
    供 Legal Answer Builder 消费。

============================================================
V6.0-14 与上一版本的主要区别
============================================================

V6.0-13 中虽然已经建立了：

    REQUIRED
    EXCLUSION
    EXCEPTION

三类条件，

但上层 rag.py 又存在兼容性补充逻辑，
导致 ConditionResult 数量可能出现：

    7
    8
    9

之间的不一致。

V6.0-14 明确规定：

    Decision Engine
        ↓
    唯一生成 ConditionResult
        ↓
    固定 8 条

上层模块不得再次 append 法律条件。

============================================================
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# Version
# ============================================================

ENGINE_VERSION = "V6.0-14"


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
    type
    ========================================================

    为兼容旧版本代码，提供：

        result.type

    作为：

        result.condition_type

    的别名。
    """

    condition: str
    status: str
    reason: str = ""
    condition_type: str = REQUIRED

    @property
    def type(self) -> str:
        """
        兼容旧版本字段：

            result.type
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

    该结构用于表达：

        某个用户事实
            ↓
        可以证明什么
            ↓
        不能证明什么

    ========================================================
    重要原则
    ========================================================

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

    satisfied_by_fact: List[str] = field(default_factory=list)

    not_proven_by_fact: List[str] = field(default_factory=list)

    explanation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """
        转换为 dict。
        """

        return {
            "rule_name": self.rule_name,
            "satisfied_by_fact": list(self.satisfied_by_fact),
            "not_proven_by_fact": list(self.not_proven_by_fact),
            "explanation": self.explanation,
        }


# ============================================================
# DecisionResult
# ============================================================

@dataclass
class DecisionResult:
    """
    法律决策最终结果。

    ========================================================
    核心字段
    ========================================================

    decision:
        DEFINITE
        CONDITIONAL
        NOT_ESTABLISHED

    condition_results:
        全部法律条件判断。

    explicit_facts:
        用户明确陈述的事实。

    contract_sequence:
        合同序列。

    rule_dependencies:
        法律规则依赖关系。

    ========================================================
    重要原则
    ========================================================

    DecisionResult 是 Decision Engine 对外输出的
    唯一标准数据结构。

    Answer Builder 不应该重新判断法律条件。
    """

    decision: str

    condition_results: List[ConditionResult] = field(
        default_factory=list
    )

    explicit_facts: List[str] = field(
        default_factory=list
    )

    contract_sequence: Optional[ContractSequence] = None

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

        注意：

        这里仅做数据读取，
        不进行新的法律判断。
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
    def required_results(self) -> List[ConditionResult]:
        """
        REQUIRED 条件结果。
        """

        return [
            item
            for item in self.condition_results
            if item.condition_type == REQUIRED
        ]

    @property
    def exclusion_results(self) -> List[ConditionResult]:
        """
        EXCLUSION 条件结果。
        """

        return [
            item
            for item in self.condition_results
            if item.condition_type == EXCLUSION
        ]

    @property
    def exception_results(self) -> List[ConditionResult]:
        """
        EXCEPTION 条件结果。
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
            "satisfied_conditions": self.satisfied_conditions,
            "unknown_conditions": self.unknown_conditions,
            "not_satisfied_conditions": (
                self.not_satisfied_conditions
            ),
        }


# ============================================================
# Text Helpers
# ============================================================

def normalize_text(value: Any) -> str:
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


# ============================================================
# Explicit Fact Extraction
# ============================================================

def extract_explicit_facts(
    question: str,
) -> List[str]:
    """
    从用户问题中提取明确事实。

    ========================================================
    重要原则
    ========================================================

    这里只提取用户明确说出来的事实。

    不进行法律推理。

    例如：

        公司连续签订三次固定期限劳动合同

    可以提取：

        公司连续签订三次固定期限劳动合同

    但不能直接提取：

        劳动者同意续订
        第三次合同属于续订
        不存在第39条情形

    因为这些事实用户没有明确提供。
    """

    question = normalize_text(question)

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
    # 明确续订
    # --------------------------------------------------------

    renewal_patterns = [
        "续订劳动合同",
        "续签劳动合同",
        "续订了劳动合同",
        "续签了劳动合同",
        "已经续订劳动合同",
        "已经续签劳动合同",
        "已经续订",
        "已经续签",
        "已续订劳动合同",
        "已续签劳动合同",
        "已续订",
        "已续签",
        "第三次已经续订",
        "第三次已经续签",
        "第三次已续订",
        "第三次已续签",
        "同意续订劳动合同",
        "同意续签劳动合同",
    ]

    if contains_any(
        question,
        renewal_patterns,
    ):
        facts.append(
            "存在明确续订劳动合同事实"
        )

    # --------------------------------------------------------
    # 劳动者提出 / 同意
    # --------------------------------------------------------
    #
    # 注意：
    #     “劳动者也同意续签”中的“也”属于自然语言连接词，
    #     不能因为中间多了“也”就漏掉明确事实。
    #
    #     该事实仍然只表示：
    #         劳动者明确同意续订 / 续签
    #
    #     不得进一步推定：
    #         劳动者提出订立固定期限劳动合同
    #

    worker_agreement_patterns = [
        "劳动者提出续订",
        "劳动者同意续订",
        "劳动者也同意续订",
        "劳动者提出续签",
        "劳动者同意续签",
        "劳动者也同意续签",
        "劳动者提出订立",
        "劳动者同意订立",
        "劳动者同意签订",
        "劳动者同意续订劳动合同",
        "劳动者同意续签劳动合同",
        "劳动者提出续订劳动合同",
        "劳动者提出续签劳动合同",
        "员工提出续订",
        "员工同意续订",
        "员工提出续签",
        "员工同意续签",
        "员工提出订立",
        "员工同意订立",
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
        "第39条",
        "第三十九条",
        "三十九条规定的情形",
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
    ]

    if contains_any(
        question,
        article_40_2_patterns,
    ):
        facts.append(
            "劳动者存在《劳动合同法》第四十条第二项规定的情形"
        )

    return unique_texts(facts)


# ============================================================
# Unique Text
# ============================================================

def unique_texts(
    values: List[str],
) -> List[str]:
    """
    去重并保持原顺序。
    """

    result: List[str] = []

    seen = set()

    for value in values:

        value = normalize_text(value)

        if not value:
            continue

        if value in seen:
            continue

        seen.add(value)
        result.append(value)

    return result


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
       之后续订劳动合同”
       → 至少存在后续合同，
         因此 count = 3

    4. 不把“续签”本身当成固定期限合同类型，
       只用于确认存在后续合同。

    5. 不修改用户原始事实。
    """

    question = normalize_text(question)

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
    # 两次固定期限 + 第三次续签
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
    构建《劳动合同法》第十四条相关核心规则。

    ========================================================
    注意
    ========================================================

    这里定义的是：

        法律规则

    而不是：

        当前案件的判断结果。

    判断结果必须通过：

        match_condition()

    产生。
    """

    return {
        "law_name": LABOR_CONTRACT_LAW,

        "article": LABOR_CONTRACT_LAW_ARTICLE_14,

        "rule_name": (
            "连续订立二次固定期限劳动合同后"
            "订立无固定期限劳动合同规则"
        ),

        "rule_text": (
            "连续订立二次固定期限劳动合同，"
            "且不存在法定排除情形，"
            "在符合法定条件的情况下，"
            "劳动者可以要求或者同意订立无固定期限劳动合同。"
        ),

        # ----------------------------------------------------
        # REQUIRED
        # ----------------------------------------------------

        "conditions": [
            "连续订立二次固定期限劳动合同",
            "存在后续订立的劳动合同",
            "续订劳动合同",
            "劳动者提出或者同意续订、订立劳动合同",
        ],

        # ----------------------------------------------------
        # EXCLUSION
        # ----------------------------------------------------

        "exclusion_conditions": [
            "劳动者存在《劳动合同法》第三十九条规定的情形",
            "劳动者存在《劳动合同法》第四十条第一项规定的情形",
            "劳动者存在《劳动合同法》第四十条第二项规定的情形",
        ],

        # ----------------------------------------------------
        # EXCEPTION
        # ----------------------------------------------------

        "exceptions": [
            "劳动者提出订立固定期限劳动合同",
        ],

        "priority": 100,
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

    ========================================================
    """

    question = normalize_text(question)

    explicit_fact_text = " ".join(
        explicit_facts
    )

    # ========================================================
    # REQUIRED
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

        # ----------------------------------------------------
        # 其他情况
        # ----------------------------------------------------

        return ConditionResult(
            condition=condition,
            status=UNKNOWN,
            reason=(
                "当前用户事实不足以确认已经连续订立二次"
                "固定期限劳动合同。"
            ),
            condition_type=REQUIRED,
        )

    # --------------------------------------------------------
    # 后续劳动合同
    # --------------------------------------------------------

    if condition == "存在后续订立的劳动合同":

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
                    "因此已经存在第三份后续劳动合同这一事实。"
                ),
                condition_type=REQUIRED,
            )

        # 明确提及后续合同
        if contains_any(
            question,
            [
                "后续劳动合同",
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

        return ConditionResult(
            condition=condition,
            status=UNKNOWN,
            reason=(
                "用户没有明确提供后续劳动合同已经订立的事实。"
            ),
            condition_type=REQUIRED,
        )

    # --------------------------------------------------------
    # 续订劳动合同
    # --------------------------------------------------------

    if condition == "续订劳动合同":

        if contains_any(
            question,
            [
                "明确续订劳动合同",
                "明确续签劳动合同",
                "已经续订劳动合同",
                "已经续签劳动合同",
                "已经续订",
                "已经续签",
                "已续订劳动合同",
                "已续签劳动合同",
                "已续订",
                "已续签",
                "第三次已经续订",
                "第三次已经续签",
                "第三次已续订",
                "第三次已续签",
                "第三次续订",
                "第三次续签",
                "续订了劳动合同",
                "续签了劳动合同",
                "已经续签了",
                "已经续订了",
            ],
        ):
            return ConditionResult(
                condition=condition,
                status=SATISFIED,
                reason=(
                    "用户明确提供了劳动合同已经续订或者续签的事实。"
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

        return ConditionResult(
            condition=condition,
            status=UNKNOWN,
            reason=(
                "用户没有明确提供劳动合同属于续订或者续签的事实。"
            ),
            condition_type=REQUIRED,
        )

    # --------------------------------------------------------
    # 劳动者提出或者同意
    # --------------------------------------------------------

    if condition == "劳动者提出或者同意续订、订立劳动合同":

        if contains_any(
            question,
            [
                "劳动者提出续订",
                "劳动者同意续订",
                "劳动者提出续签",
                "劳动者同意续签",
                "劳动者也同意续订",
                "劳动者也同意续签",
                "劳动者提出订立",
                "劳动者同意订立",
                "劳动者提出签订",
                "劳动者同意签订",
                "劳动者也同意订立",
                "劳动者也同意签订",
                "员工提出续订",
                "员工同意续订",
                "员工提出续签",
                "员工同意续签",
                "员工也同意续订",
                "员工也同意续签",
                "员工提出订立",
                "员工同意订立",
                "员工提出签订",
                "员工同意签订",
            ],
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
        # 用户未明确提供劳动者提出 / 同意事实
        # ----------------------------------------------------
        #
        # 不允许在通用 UNKNOWN 文案中硬编码“三次”。
        # 当前用户可能是：
        #
        #     两次固定期限劳动合同
        #     三次固定期限劳动合同
        #     其他合同事实
        #
        # 因此原因说明必须根据当前 ContractSequence 动态生成，
        # 严禁污染实际用户事实。
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

    if (
        condition
        == "劳动者存在《劳动合同法》第三十九条规定的情形"
    ):

        if contains_any(
            question,
            [
                "存在第39条情形",
                "存在第三十九条情形",
                "符合第39条",
                "符合第三十九条",
                "劳动者有第39条情形",
                "劳动者有第三十九条情形",
            ],
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

    # --------------------------------------------------------
    # 第40条第一项
    # --------------------------------------------------------

    if (
        condition
        == "劳动者存在《劳动合同法》第四十条第一项规定的情形"
    ):

        if contains_any(
            question,
            [
                "存在第40条第一项情形",
                "存在第四十条第一项情形",
                "符合第40条第一项",
                "符合第四十条第一项",
                "符合第40条第1项",
                "符合第四十条第1项",
            ],
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

    # --------------------------------------------------------
    # 第40条第二项
    # --------------------------------------------------------

    if (
        condition
        == "劳动者存在《劳动合同法》第四十条第二项规定的情形"
    ):

        if contains_any(
            question,
            [
                "存在第40条第二项情形",
                "存在第四十条第二项情形",
                "符合第40条第二项",
                "符合第四十条第二项",
                "符合第40条第2项",
                "符合第四十条第2项",
            ],
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

        if contains_any(
            question,
            [
                "劳动者提出订立固定期限劳动合同",
                "劳动者要求签固定期限劳动合同",
                "劳动者要求订立固定期限劳动合同",
                "员工提出订立固定期限劳动合同",
                "员工要求签固定期限劳动合同",
                "员工要求订立固定期限劳动合同",
            ],
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
    对核心法律规则进行完整条件评估。

    ========================================================
    固定结构
    ========================================================

    REQUIRED:

        4

    EXCLUSION:

        3

    EXCEPTION:

        1

    TOTAL:

        8

    ========================================================
    """

    condition_results: List[ConditionResult] = []

    # ========================================================
    # REQUIRED
    # ========================================================

    required_conditions = [
        "连续订立二次固定期限劳动合同",
        "存在后续订立的劳动合同",
        "续订劳动合同",
        "劳动者提出或者同意续订、订立劳动合同",
    ]

    for condition in required_conditions:

        result = match_condition(
            condition=condition,
            question=question,
            contract_sequence=contract_sequence,
            explicit_facts=explicit_facts,
            condition_type=REQUIRED,
        )

        condition_results.append(result)

    # ========================================================
    # EXCLUSION
    # ========================================================

    exclusion_conditions = [
        "劳动者存在《劳动合同法》第三十九条规定的情形",
        "劳动者存在《劳动合同法》第四十条第一项规定的情形",
        "劳动者存在《劳动合同法》第四十条第二项规定的情形",
    ]

    for condition in exclusion_conditions:

        result = match_condition(
            condition=condition,
            question=question,
            contract_sequence=contract_sequence,
            explicit_facts=explicit_facts,
            condition_type=EXCLUSION,
        )

        condition_results.append(result)

    # ========================================================
    # EXCEPTION
    # ========================================================

    exception_conditions = [
        "劳动者提出订立固定期限劳动合同",
    ]

    for condition in exception_conditions:

        result = match_condition(
            condition=condition,
            question=question,
            contract_sequence=contract_sequence,
            explicit_facts=explicit_facts,
            condition_type=EXCEPTION,
        )

        condition_results.append(result)

    # ========================================================
    # Validate Condition Structure
    # ========================================================

    validate_condition_structure(
        condition_results
    )

    # ========================================================
    # Decision
    # ========================================================

    statuses = [
        item.status
        for item in condition_results
    ]

    # --------------------------------------------------------
    # 任一明确不满足
    # --------------------------------------------------------

    if NOT_SATISFIED in statuses:

        decision = NOT_ESTABLISHED

    # --------------------------------------------------------
    # 没有不满足，但存在未知
    # --------------------------------------------------------

    elif UNKNOWN in statuses:

        decision = CONDITIONAL

    # --------------------------------------------------------
    # 全部满足
    # --------------------------------------------------------

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
    验证 ConditionResult 的结构。

    ========================================================
    V6.0-14 强约束
    ========================================================

        REQUIRED   = 4
        EXCLUSION  = 3
        EXCEPTION  = 1
        TOTAL      = 8

    如果数量不正确，直接抛出异常。

    这样可以防止上层模块出现：

        7
        8
        9

    不一致问题。

    ========================================================
    """

    if len(condition_results) != 8:

        raise ValueError(
            "Legal Decision Engine V6.0-14: "
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
            "Legal Decision Engine V6.0-14: "
            f"REQUIRED 条件必须为 4，"
            f"实际为 {required_count}。"
        )

    if exclusion_count != 3:

        raise ValueError(
            "Legal Decision Engine V6.0-14: "
            f"EXCLUSION 条件必须为 3，"
            f"实际为 {exclusion_count}。"
        )

    if exception_count != 1:

        raise ValueError(
            "Legal Decision Engine V6.0-14: "
            f"EXCEPTION 条件必须为 1，"
            f"实际为 {exception_count}。"
        )

    # --------------------------------------------------------
    # 检查分类总数
    # --------------------------------------------------------

    if (
        required_count
        + exclusion_count
        + exception_count
        != 8
    ):
        raise ValueError(
            "Legal Decision Engine V6.0-14: "
            "ConditionResult 分类总数不等于 8。"
        )

    # --------------------------------------------------------
    # 检查条件是否重复
    # --------------------------------------------------------

    conditions = [
        item.condition
        for item in condition_results
    ]

    if len(set(conditions)) != len(conditions):

        raise ValueError(
            "Legal Decision Engine V6.0-14: "
            "ConditionResult 中存在重复法律条件。"
        )

    # --------------------------------------------------------
    # 检查类别是否正确
    # --------------------------------------------------------

    expected_required = {
        "连续订立二次固定期限劳动合同",
        "存在后续订立的劳动合同",
        "续订劳动合同",
        "劳动者提出或者同意续订、订立劳动合同",
    }

    expected_exclusion = {
        "劳动者存在《劳动合同法》第三十九条规定的情形",
        "劳动者存在《劳动合同法》第四十条第一项规定的情形",
        "劳动者存在《劳动合同法》第四十条第二项规定的情形",
    }

    expected_exception = {
        "劳动者提出订立固定期限劳动合同",
    }

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
            "Legal Decision Engine V6.0-14: "
            "REQUIRED 条件集合不正确。"
        )

    if actual_exclusion != expected_exclusion:

        raise ValueError(
            "Legal Decision Engine V6.0-14: "
            "EXCLUSION 条件集合不正确。"
        )

    if actual_exception != expected_exception:

        raise ValueError(
            "Legal Decision Engine V6.0-14: "
            "EXCEPTION 条件集合不正确。"
        )


# ============================================================
# Make Decision
# ============================================================

def make_decision(
    question: str,
    rules: Optional[List[Dict[str, Any]]] = None,
) -> DecisionResult:
    """
    对用户问题执行法律决策。

    ========================================================
    输入
    ========================================================

    question:
        用户法律问题。

    rules:
        Retriever 返回并经过标准化的法律规则。

        如果没有传入 rules，
        使用内部核心规则。

    ========================================================
    输出
    ========================================================

    DecisionResult

    ========================================================
    """

    question = normalize_text(question)

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
    # Rule
    # --------------------------------------------------------

    core_rule = build_core_rule()

    selected_rule = select_core_rule(
        rules=rules,
        fallback_rule=core_rule,
    )

    # --------------------------------------------------------
    # Dependency
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
        rule_dependencies=[dependency],
        selected_rule=selected_rule,
        explanation=explanation,
        engine_version=ENGINE_VERSION,
    )

    # --------------------------------------------------------
    # Final Structural Validation
    # --------------------------------------------------------

    validate_decision_result(
        result
    )

    return result


# ============================================================
# Select Core Rule
# ============================================================

def select_core_rule(
    rules: Optional[List[Dict[str, Any]]],
    fallback_rule: Dict[str, Any],
) -> Dict[str, Any]:
    """
    从 Retriever 规则中选择核心规则。

    ========================================================
    原则
    ========================================================

    Retriever 可以提供多个法律条文。

    Decision Engine 当前只对能够识别为
    《劳动合同法》第十四条的核心规则执行
    本模块定义的结构化判断。

    如果没有找到，则使用 fallback_rule。

    ========================================================
    """

    if not rules:

        return fallback_rule

    for rule in rules:

        if not isinstance(rule, dict):

            continue

        law_name = normalize_text(
            rule.get("law_name")
        )

        article = normalize_text(
            rule.get("article")
        )

        text = normalize_text(
            rule.get("rule_text")
        )

        if (
            "劳动合同法" in law_name
            and (
                "第十四条" in article
                or "第14条" in article
                or "十四条" in text
                and "无固定期限" in text
            )
        ):

            merged = dict(
                fallback_rule
            )

            merged.update(rule)

            # ------------------------------------------------
            # 保证核心条件不会被 Retriever 截断
            # ------------------------------------------------

            merged["conditions"] = list(
                fallback_rule["conditions"]
            )

            merged["exclusion_conditions"] = list(
                fallback_rule["exclusion_conditions"]
            )

            merged["exceptions"] = list(
                fallback_rule["exceptions"]
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
    构建供 Answer Builder 使用的结构化解释。

    注意：

    这里只对已经产生的 ConditionResult 做汇总，
    不重新进行法律推理。
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
# Validate DecisionResult
# ============================================================

def validate_decision_result(
    decision: DecisionResult,
) -> None:
    """
    对最终 DecisionResult 进行结构验证。

    ========================================================
    强约束
    ========================================================

    ConditionResult:

        8

    分类：

        4 + 3 + 1

    ========================================================
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

    # --------------------------------------------------------
    # UNKNOWN 条件必须真实存在
    # --------------------------------------------------------

    unknown_count = sum(
        1
        for item in decision.condition_results
        if item.status == UNKNOWN
    )

    # --------------------------------------------------------
    # 如果存在 UNKNOWN
    # 则不能是 DEFINITE
    # --------------------------------------------------------

    if (
        unknown_count > 0
        and decision.decision == DEFINITE
    ):
        raise ValueError(
            "Decision Engine V6.0-14: "
            "存在 UNKNOWN 条件时不能输出 DEFINITE。"
        )

    # --------------------------------------------------------
    # 如果存在明确 NOT_SATISFIED
    # 则不能输出 DEFINITE / CONDITIONAL
    # --------------------------------------------------------

    not_satisfied_count = sum(
        1
        for item in decision.condition_results
        if item.status == NOT_SATISFIED
    )

    if (
        not_satisfied_count > 0
        and decision.decision
        != NOT_ESTABLISHED
    ):
        raise ValueError(
            "Decision Engine V6.0-14: "
            "存在 NOT_SATISFIED 条件时必须输出 "
            "NOT_ESTABLISHED。"
        )


# ============================================================
# Public Helper Functions
# ============================================================

def get_condition_results(
    decision: DecisionResult,
) -> List[ConditionResult]:
    """
    获取 ConditionResult。

    只读取，不修改。
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

    用于 Component Test 和人工调试。
    """

    print()
    print("=" * 70)
    print(
        f"Legal Decision Engine {ENGINE_VERSION}"
    )
    print("=" * 70)

    print(
        f"Decision: {decision.decision}"
    )

    print(
        f"Explicit Facts: "
        f"{len(decision.explicit_facts)}"
    )

    if decision.explicit_facts:

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
            f"  Term Type: "
            f"{sequence.term_type}"
        )

        print(
            f"  Continuous: "
            f"{sequence.continuous}"
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

        if result.reason:

            print(
                f"     Reason: "
                f"{result.reason}"
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
# Component Test
# ============================================================

def run_component_test() -> None:
    """
    Decision Engine V6.0-14 Component Test。

    ========================================================
    测试问题
    ========================================================

    公司连续签订三次固定期限劳动合同后，
    是否必须签订无固定期限劳动合同？

    ========================================================
    预期
    ========================================================

    Decision:

        CONDITIONAL

    Explicit Facts:

        包含：
        公司连续签订三次固定期限劳动合同

    Contract Sequence:

        count = 3
        term_type = fixed
        continuous = True

    Condition Results:

        TOTAL = 8

        REQUIRED = 4
        EXCLUSION = 3
        EXCEPTION = 1

    状态：

        连续订立二次固定期限劳动合同
            SATISFIED

        存在后续订立的劳动合同
            SATISFIED

        续订劳动合同
            UNKNOWN

        劳动者提出或者同意续订、订立劳动合同
            UNKNOWN

        第39条
            UNKNOWN

        第40条第一项
            UNKNOWN

        第40条第二项
            UNKNOWN

        劳动者提出固定期限
            UNKNOWN

    ========================================================
    """

    print()
    print("=" * 70)
    print(
        f"Legal Decision Engine "
        f"{ENGINE_VERSION}"
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

    # --------------------------------------------------------
    # Execute
    # --------------------------------------------------------

    decision = make_decision(
        question
    )

    # --------------------------------------------------------
    # Print
    # --------------------------------------------------------

    print_decision_result(
        decision
    )

    # ========================================================
    # Assertions
    # ========================================================

    print()
    print(
        "Running assertions..."
    )

    # --------------------------------------------------------
    # Decision
    # --------------------------------------------------------

    assert (
        decision.decision
        == CONDITIONAL
    ), (
        "V6.0-14 Component Test："
        "Decision 应为 CONDITIONAL"
    )

    # --------------------------------------------------------
    # Explicit Fact
    # --------------------------------------------------------

    assert (
        "公司连续签订三次固定期限劳动合同"
        in decision.explicit_facts
    ), (
        "V6.0-14 Component Test："
        "必须保留用户事实："
        "公司连续签订三次固定期限劳动合同"
    )

    # --------------------------------------------------------
    # Contract Sequence
    # --------------------------------------------------------

    assert (
        decision.contract_sequence
        is not None
    )

    assert (
        decision.contract_sequence.count
        == 3
    ), (
        "V6.0-14 Component Test："
        "合同次数必须为 3"
    )

    assert (
        decision.contract_sequence.term_type
        == "fixed"
    ), (
        "V6.0-14 Component Test："
        "合同类型必须为 fixed"
    )

    assert (
        decision.contract_sequence.continuous
        is True
    ), (
        "V6.0-14 Component Test："
        "合同必须识别为连续"
    )

    # --------------------------------------------------------
    # Total Condition Results
    # --------------------------------------------------------

    assert (
        len(decision.condition_results)
        == 8
    ), (
        "V6.0-14 Component Test："
        "Condition Results 应为 8"
    )

    # --------------------------------------------------------
    # Category Count
    # --------------------------------------------------------

    required_results = (
        get_required_results(decision)
    )

    exclusion_results = (
        get_exclusion_results(decision)
    )

    exception_results = (
        get_exception_results(decision)
    )

    assert (
        len(required_results)
        == 4
    ), (
        "V6.0-14 Component Test："
        "REQUIRED 应为 4"
    )

    assert (
        len(exclusion_results)
        == 3
    ), (
        "V6.0-14 Component Test："
        "EXCLUSION 应为 3"
    )

    assert (
        len(exception_results)
        == 1
    ), (
        "V6.0-14 Component Test："
        "EXCEPTION 应为 1"
    )

    # --------------------------------------------------------
    # Numeric Threshold
    # --------------------------------------------------------

    threshold_result = next(
        item
        for item in decision.condition_results
        if item.condition
        == "连续订立二次固定期限劳动合同"
    )

    assert (
        threshold_result.status
        == SATISFIED
    ), (
        "V6.0-14 Component Test："
        "三次固定期限合同必须满足二次数量门槛"
    )

    # --------------------------------------------------------
    # Later Contract
    # --------------------------------------------------------

    later_contract_result = next(
        item
        for item in decision.condition_results
        if item.condition
        == "存在后续订立的劳动合同"
    )

    assert (
        later_contract_result.status
        == SATISFIED
    ), (
        "V6.0-14 Component Test："
        "三次合同必须确认存在后续劳动合同"
    )

    # --------------------------------------------------------
    # Renewal
    # --------------------------------------------------------

    renewal_result = next(
        item
        for item in decision.condition_results
        if item.condition
        == "续订劳动合同"
    )

    assert (
        renewal_result.status
        == UNKNOWN
    ), (
        "V6.0-14 Component Test："
        "三次固定期限合同不能自动证明续订"
    )

    # --------------------------------------------------------
    # Worker Agreement
    # --------------------------------------------------------

    worker_result = next(
        item
        for item in decision.condition_results
        if item.condition
        == "劳动者提出或者同意续订、订立劳动合同"
    )

    assert (
        worker_result.status
        == UNKNOWN
    ), (
        "V6.0-14 Component Test："
        "不能仅凭三次合同推定劳动者提出或者同意"
    )

    # --------------------------------------------------------
    # Article 39
    # --------------------------------------------------------

    article_39_result = next(
        item
        for item in decision.condition_results
        if item.condition
        == "劳动者存在《劳动合同法》第三十九条规定的情形"
    )

    assert (
        article_39_result.status
        == UNKNOWN
    ), (
        "V6.0-14 Component Test："
        "没有第39条事实时应为 UNKNOWN，"
        "不能默认不存在"
    )

    # --------------------------------------------------------
    # Article 40(1)
    # --------------------------------------------------------

    article_40_1_result = next(
        item
        for item in decision.condition_results
        if item.condition
        == "劳动者存在《劳动合同法》第四十条第一项规定的情形"
    )

    assert (
        article_40_1_result.status
        == UNKNOWN
    ), (
        "V6.0-14 Component Test："
        "没有第40条第一项事实时应为 UNKNOWN"
    )

    # --------------------------------------------------------
    # Article 40(2)
    # --------------------------------------------------------

    article_40_2_result = next(
        item
        for item in decision.condition_results
        if item.condition
        == "劳动者存在《劳动合同法》第四十条第二项规定的情形"
    )

    assert (
        article_40_2_result.status
        == UNKNOWN
    ), (
        "V6.0-14 Component Test："
        "没有第40条第二项事实时应为 UNKNOWN"
    )

    # --------------------------------------------------------
    # Fixed-term Exception
    # --------------------------------------------------------

    fixed_term_exception = next(
        item
        for item in decision.condition_results
        if item.condition
        == "劳动者提出订立固定期限劳动合同"
    )

    assert (
        fixed_term_exception.status
        == UNKNOWN
    ), (
        "V6.0-14 Component Test："
        "没有劳动者提出固定期限事实时应为 UNKNOWN"
    )

    # --------------------------------------------------------
    # Satisfied Conditions
    # --------------------------------------------------------

    expected_satisfied = {
        "连续订立二次固定期限劳动合同",
        "存在后续订立的劳动合同",
    }

    actual_satisfied = set(
        decision.satisfied_conditions
    )

    assert (
        actual_satisfied
        == expected_satisfied
    ), (
        "V6.0-14 Component Test："
        "SATISFIED 条件集合不正确"
    )

    # --------------------------------------------------------
    # Unknown Conditions
    # --------------------------------------------------------

    expected_unknown = {
        "续订劳动合同",
        "劳动者提出或者同意续订、订立劳动合同",
        "劳动者存在《劳动合同法》第三十九条规定的情形",
        "劳动者存在《劳动合同法》第四十条第一项规定的情形",
        "劳动者存在《劳动合同法》第四十条第二项规定的情形",
        "劳动者提出订立固定期限劳动合同",
    }

    actual_unknown = set(
        decision.unknown_conditions
    )

    assert (
        actual_unknown
        == expected_unknown
    ), (
        "V6.0-14 Component Test："
        "UNKNOWN 条件集合不正确"
    )

    # --------------------------------------------------------
    # No NOT_SATISFIED
    # --------------------------------------------------------

    assert (
        len(decision.not_satisfied_conditions)
        == 0
    ), (
        "V6.0-14 Component Test："
        "测试问题不应出现 NOT_SATISFIED"
    )

    # --------------------------------------------------------
    # Dependency
    # --------------------------------------------------------

    assert (
        len(decision.rule_dependencies)
        == 1
    ), (
        "V6.0-14 Component Test："
        "应该存在一个核心规则依赖关系"
    )

    dependency = (
        decision.rule_dependencies[0]
    )

    assert (
        "连续签订三次固定期限劳动合同"
        in dependency.satisfied_by_fact
    ), (
        "V6.0-14 Component Test："
        "依赖关系必须记录三次合同事实"
    )

    assert (
        "续订劳动合同"
        in dependency.not_proven_by_fact
    ), (
        "V6.0-14 Component Test："
        "三次合同不能证明续订"
    )

    assert (
        "劳动者提出或者同意续订、订立劳动合同"
        in dependency.not_proven_by_fact
    ), (
        "V6.0-14 Component Test："
        "三次合同不能证明劳动者提出或者同意"
    )

    # --------------------------------------------------------
    # Final Validation
    # --------------------------------------------------------

    validate_decision_result(
        decision
    )

    print()
    print(
        "All assertions passed."
    )

    print()
    print(
        "============================================================"
    )
    print(
        "V6.0-14 Component Test PASSED"
    )
    print(
        "============================================================"
    )

    print()
    print(
        "Condition Result Structure:"
    )

    print(
        "  REQUIRED   = 4"
    )

    print(
        "  EXCLUSION  = 3"
    )

    print(
        "  EXCEPTION  = 1"
    )

    print(
        "  TOTAL      = 8"
    )

    print()
    print(
        "Decision:"
    )

    print(
        f"  {decision.decision}"
    )


# ============================================================
# Simple Test Cases
# ============================================================

def run_additional_tests() -> None:
    """
    额外测试。

    用于验证：

        UNKNOWN
        SATISFIED
        NOT_SATISFIED

    三种状态均可以正常工作。
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

    assert (
        result_1.decision
        == CONDITIONAL
    )

    assert (
        len(result_1.condition_results)
        == 8
    )

    # ========================================================
    # Test 2
    # 明确存在续订及劳动者同意
    # ========================================================

    question_2 = (
        "公司连续签订两次固定期限劳动合同，"
        "之后续订劳动合同，劳动者同意续订，"
        "劳动者没有提出订立固定期限劳动合同。"
    )

    result_2 = make_decision(
        question_2
    )

    # 注意：
    #
    # 当前测试模型对于：
    #
    # “没有提出订立固定期限”
    #
    # 不直接把缺失事实转换成 SATISFIED。
    #
    # 因此这里只验证：
    #
    # 明确提供的事实能够正确进入对应条件，
    # 不要求整个案件 DEFINITE。

    renewal_result = next(
        item
        for item in result_2.condition_results
        if item.condition
        == "续订劳动合同"
    )

    assert (
        renewal_result.status
        == SATISFIED
    )

    worker_result = next(
        item
        for item in result_2.condition_results
        if item.condition
        == "劳动者提出或者同意续订、订立劳动合同"
    )

    assert (
        worker_result.status
        == SATISFIED
    )

    # ========================================================
    # Test 3
    # 明确存在第39条情形
    # ========================================================

    question_3 = (
        "公司连续签订三次固定期限劳动合同，"
        "劳动者存在劳动合同法第三十九条规定的情形，"
        "是否必须签订无固定期限劳动合同？"
    )

    result_3 = make_decision(
        question_3
    )

    article_39_result = next(
        item
        for item in result_3.condition_results
        if item.condition
        == "劳动者存在《劳动合同法》第三十九条规定的情形"
    )

    assert (
        article_39_result.status
        == NOT_SATISFIED
    )

    assert (
        result_3.decision
        == NOT_ESTABLISHED
    )

    print(
        "Additional tests passed."
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

    print()

    try:

        choice = input(
            "请输入 1、2 或 3："
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