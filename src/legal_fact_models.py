# -*- coding: utf-8 -*-

"""
RAG V6.1
Legal Fact Models

============================================================
功能
============================================================

定义 Legal Fact Extraction 层使用的纯数据模型。

本模块只负责数据结构：

    Natural Language Question
            ↓
    Legal Fact Extractor
            ↓
    LegalFacts
            ↓
    Legal Decision Engine

============================================================
设计原则
============================================================

1. 本模块不负责法律判断。

2. 本模块不调用 Ollama。

3. 本模块不负责 ConditionResult。

4. 本模块不负责 DecisionResult。

5. ContractSequence 从 Legal Decision Engine 中独立出来，
   避免：

       legal_decision_engine
              ↓
       legal_fact_extractor
              ↓
       legal_decision_engine

   所形成的循环 import。

6. LegalFacts 表示“用户明确陈述出来的事实”，
   不表示法律条件是否满足。

7. 布尔型事实统一使用：

       True
           明确存在 / 明确发生

       False
           明确不存在 / 明确未发生

       None
           当前问题没有明确说明

   None 是 Fact 层的“未知”，
   后续由 Legal Decision Engine 将其映射为
   ConditionResult.UNKNOWN。

8. ContractSequence 是“事实结构”，
   不是法律结论。

   例如：

       count = 3

   只能说明问题中识别出了三次固定期限劳动合同，
   不能直接推出：

       - 已经完成续订
       - 劳动者已经同意续订
       - 不存在第三十九条规定的情形
       - 不存在第四十条第一项规定的情形
       - 不存在第四十条第二项规定的情形
       - 不存在固定期限合同例外

9. 后续 V6.1 如果增加更多结构化事实模型，
   可以继续在本模块扩展。

============================================================
V6.1 第二阶段
============================================================

核心数据流：

    question
        ↓
    Legal Fact Extractor
        ↓
    LegalFacts
        ↓
    Legal Decision Engine
        ↓
    ConditionResult

其中：

    LegalFacts
        =
    “用户说了什么事实”

而：

    ConditionResult
        =
    “这些事实是否满足某个法律条件”

两者必须保持分离。

============================================================
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ============================================================
# Contract Sequence
# ============================================================

@dataclass
class ContractSequence:
    """
    合同序列信息。

    用于描述问题中明确识别出的劳动合同序列事实。

    示例：

        公司连续签订三次固定期限劳动合同

    对应：

        count = 3
        term_type = "fixed"
        continuous = True

    注意：

        ContractSequence 是“事实结构”，
        不是法律结论。

        count=3 并不自动证明：

            - 已经完成续订
            - 劳动者已经同意续订
            - 不存在法定排除情形
            - 不存在法定例外情形
    """

    count: int

    term_type: str

    continuous: bool

    def to_dict(self) -> Dict[str, object]:
        """
        转换为字典。
        """

        return {
            "count": self.count,
            "term_type": self.term_type,
            "continuous": self.continuous,
        }


# ============================================================
# Legal Facts
# ============================================================

@dataclass
class LegalFacts:
    """
    V6.1 结构化法律事实。

    ========================================================
    核心职责
    ========================================================

    LegalFacts 只表示：

        用户在自然语言问题中明确陈述了什么事实。

    不负责：

        - 法律条件判断
        - DecisionResult
        - ConditionResult
        - 法律结论
        - Ollama 调用
        - 最终答案生成

    ========================================================
    Fact 层与 Condition 层的区别
    ========================================================

    例如用户说：

        公司连续签订三次固定期限劳动合同，
        员工也同意续订。

    Fact Extractor 可以提取：

        contract_sequence.count = 3
        completed_renewal = None
        worker_agreement = True

    这里：

        worker_agreement = True

    只是说明：

        “用户明确说劳动者同意续订”。

    它不是：

        “劳动合同法第十四条第四项已经满足”。

    后者属于 Legal Decision Engine 的职责。

    ========================================================
    三态事实
    ========================================================

    对于可以明确表示“存在 / 不存在”的事实，
    使用 Optional[bool]：

        True
            用户明确陈述事实存在。

        False
            用户明确陈述事实不存在。

        None
            用户没有明确说明。

    例如：

        article_39 = True

    表示：

        用户明确陈述劳动者存在
        《劳动合同法》第三十九条规定的情形。

    而：

        article_39 = False

    表示：

        用户明确陈述劳动者不存在
        《劳动合同法》第三十九条规定的情形。

    如果用户没有提到：

        article_39 = None

    后续 Decision Engine 才会将其转换为：

        EXCLUSION
        UNKNOWN
    """

    # ========================================================
    # 用户明确事实
    # ========================================================

    explicit_facts: List[str] = field(
        default_factory=list
    )

    # ========================================================
    # 合同序列事实
    # ========================================================

    contract_sequence: Optional[
        ContractSequence
    ] = None

    # ========================================================
    # REQUIRED 相关事实
    # ========================================================

    completed_renewal: Optional[bool] = None

    """
    是否已经完成劳动合同续订 / 续签。

    True：
        用户明确陈述已经续订 / 已经续签。

    False：
        用户明确陈述没有续订 / 没有续签。

    None：
        用户没有明确说明。

    注意：

        合同次数本身不能自动将该字段设置为 True。
    """

    worker_agreement: Optional[bool] = None

    """
    劳动者是否提出或者同意续订、订立劳动合同。

    True：
        用户明确陈述劳动者提出或者同意。

    False：
        用户明确陈述劳动者没有提出或者不同意。

    None：
        用户没有明确说明。

    注意：

        “存在三次固定期限劳动合同”
        不能自动将该字段设置为 True。
    """

    # ========================================================
    # EXCLUSION 相关事实
    # ========================================================

    article_39: Optional[bool] = None

    """
    劳动者是否存在《劳动合同法》第三十九条规定的情形。

    True：
        用户明确陈述存在第三十九条情形。

    False：
        用户明确陈述不存在第三十九条情形。

    None：
        用户没有明确说明。
    """

    article_40_1: Optional[bool] = None

    """
    劳动者是否存在《劳动合同法》第四十条第一项规定的情形。

    True：
        用户明确陈述存在第四十条第一项情形。

    False：
        用户明确陈述不存在第四十条第一项情形。

    None：
        用户没有明确说明。
    """

    article_40_2: Optional[bool] = None

    """
    劳动者是否存在《劳动合同法》第四十条第二项规定的情形。

    True：
        用户明确陈述存在第四十条第二项情形。

    False：
        用户明确陈述不存在第四十条第二项情形。

    None：
        用户没有明确说明。
    """

    # ========================================================
    # EXCEPTION 相关事实
    # ========================================================

    fixed_term_exception: Optional[bool] = None

    """
    劳动者是否提出订立固定期限劳动合同。

    True：
        用户明确陈述劳动者提出订立固定期限劳动合同。

    False：
        用户明确陈述劳动者没有提出订立固定期限劳动合同。

    None：
        用户没有明确说明。

    注意：

        该字段只表示用户陈述的事实，
        不表示法律上的例外条件已经被 Engine 判定为触发。
    """

    # ========================================================
    # Dict Conversion
    # ========================================================

    def to_dict(self) -> Dict[str, object]:
        """
        将 LegalFacts 转换为普通字典。

        注意：

            这里仅进行数据转换，
            不进行任何法律判断。
        """

        return {
            "explicit_facts": list(
                self.explicit_facts
            ),
            "contract_sequence": (
                self.contract_sequence.to_dict()
                if self.contract_sequence is not None
                else None
            ),
            "completed_renewal": (
                self.completed_renewal
            ),
            "worker_agreement": (
                self.worker_agreement
            ),
            "article_39": (
                self.article_39
            ),
            "article_40_1": (
                self.article_40_1
            ),
            "article_40_2": (
                self.article_40_2
            ),
            "fixed_term_exception": (
                self.fixed_term_exception
            ),
        }