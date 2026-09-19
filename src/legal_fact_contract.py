# -*- coding: utf-8 -*-

"""
RAG V6.1
Legal Fact Contract Extractor

============================================================
功能
============================================================

从用户自然语言问题中提取：

    合同序列事实
        ↓
    ContractSequence

当前负责：

    - 三次固定期限劳动合同
    - 两次固定期限劳动合同
    - 两次固定期限 + 后续续订/续签
    - 合同次数
    - 固定期限
    - 连续性

============================================================
职责边界
============================================================

本模块只负责：

    1. 识别用户明确表达的合同次数事实
    2. 识别固定期限劳动合同
    3. 识别连续签订/订立
    4. 根据已经明确表达的续订事实，
       构造合同序列

本模块不负责：

    - 法律条件判断
    - Decision 判断
    - ConditionResult
    - DecisionResult
    - Ollama
    - 最终答案生成
    - 法律结论推定

============================================================
事实提取原则
============================================================

1. 只提取用户明确表达的合同事实。

2. 不因为“第三次合同”自动推定：
       续订劳动合同
       劳动者同意续订

3. 两次固定期限劳动合同本身：

       count = 2

4. 两次固定期限劳动合同 + 明确后续续订/续签：

       count = 3

5. 三次固定期限劳动合同：

       count = 3

6. ContractSequence 只是事实结构：

       count
       term_type
       continuous

   不表示法律条件已经满足。

============================================================
V6.1 第一刀
============================================================

从：

    legal_fact_extractor.py

中独立：

    extract_contract_sequence()

本模块不重新实现：

    has_completed_renewal()

而是从：

    legal_fact_renewal.py

导入。

这样可以保证：

    “已完成续订”的事实识别规则只有一套。

============================================================
"""

from __future__ import annotations

from typing import Optional

from src.legal_common import (
    contains_any,
    normalize_text,
)
from src.legal_fact_models import ContractSequence
from src.legal_fact_renewal import has_completed_renewal


# ============================================================
# Contract Sequence Extraction
# ============================================================

def extract_contract_sequence(
    question: str,
) -> Optional[ContractSequence]:
    """
    提取合同序列。

    规则：

        三次固定期限
            → count = 3

        两次固定期限 + 明确后续续订/续签
            → count = 3

        两次固定期限
            → count = 2

    注意：

        合同次数只表达合同序列事实，
        不直接表达法律条件是否满足。

    例如：

        公司连续签订三次固定期限劳动合同

    只能得到：

        count = 3
        term_type = "fixed"
        continuous = True

    不能由此自动得到：

        续订劳动合同 = True
        劳动者同意续订 = True
    """

    text = normalize_text(question)

    # --------------------------------------------------------
    # 三次固定期限劳动合同
    # --------------------------------------------------------

    three_contract_patterns = [
        "连续签订三次固定期限劳动合同",
        "连续订立三次固定期限劳动合同",
        "连续签了三次固定期限劳动合同",
        "连续签订了三次固定期限劳动合同",
        "连续订立了三次固定期限劳动合同",
    ]

    if contains_any(
        text,
        three_contract_patterns,
    ):

        return ContractSequence(
            count=3,
            term_type="fixed",
            continuous=True,
        )

    # --------------------------------------------------------
    # 两次固定期限劳动合同
    # --------------------------------------------------------

    two_contract_patterns = [
        "连续签订两次固定期限劳动合同",
        "连续订立两次固定期限劳动合同",
        "连续签了两次固定期限劳动合同",
        "连续签订了两次固定期限劳动合同",
        "连续订立了两次固定期限劳动合同",
    ]

    if contains_any(
        text,
        two_contract_patterns,
    ):

        # ----------------------------------------------------
        # 两次固定期限 + 已明确完成续订/续签
        #
        # 注意：
        #
        # 这里调用 renewal 层的事实识别函数。
        #
        # 不复制 has_completed_renewal() 的规则。
        # ----------------------------------------------------

        if has_completed_renewal(text):

            return ContractSequence(
                count=3,
                term_type="fixed",
                continuous=True,
            )

        # ----------------------------------------------------
        # 两次固定期限 + 后续明确续订/续签
        #
        # 这些表达属于合同序列事实：
        #
        #     后来续订
        #     后来续签
        #     之后续订
        #     之后续签
        #     又续订
        #     又续签
        #
        # 注意：
        #
        # 这里仅用于确定合同序列数量，
        # 不负责判断：
        #
        #     续订劳动合同 Condition
        #     劳动者同意 Condition
        #
        # Condition 判断仍由 Legal Decision Engine 负责。
        # ----------------------------------------------------

        later_renewal_patterns = [
            "后来续订",
            "后来续签",
            "之后续订",
            "之后续签",
            "又续订",
            "又续签",
        ]

        if contains_any(
            text,
            later_renewal_patterns,
        ):

            return ContractSequence(
                count=3,
                term_type="fixed",
                continuous=True,
            )

        # ----------------------------------------------------
        # 只有两次固定期限劳动合同
        # ----------------------------------------------------

        return ContractSequence(
            count=2,
            term_type="fixed",
            continuous=True,
        )

    # --------------------------------------------------------
    # 未识别到合同序列
    # --------------------------------------------------------

    return None