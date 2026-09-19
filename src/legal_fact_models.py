# -*- coding: utf-8 -*-

"""
RAG V6.1
Legal Fact Models

============================================================
功能
============================================================

定义 Legal Fact Extraction 层使用的纯数据模型。

本模块只负责数据结构：

    Fact Extractor
          ↓
    ContractSequence
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

6. 后续 V6.1 如果增加更多结构化事实模型，
   可以继续在本模块扩展。
============================================================
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


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
