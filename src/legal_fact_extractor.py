# -*- coding: utf-8 -*-

"""
RAG V6.1
Legal Fact Extractor

============================================================
功能
============================================================

用户自然语言问题
      ↓
Legal Fact Extractor
      ↓
结构化事实
      ├── explicit_facts
      ├── contract_sequence
      ├── completed_renewal
      ├── worker_agreement
      ├── article_39
      ├── article_40_1
      ├── article_40_2
      └── fixed_term_exception
      ↓
Legal Decision Engine

============================================================
职责边界
============================================================

本模块只负责：

    1. 统一协调事实提取模块
    2. 汇总用户明确表达的事实
    3. 将已经提取的事实组装成 LegalFacts

本模块不负责：

    - 法律条件判断
    - Decision 判断
    - ConditionResult
    - DecisionResult
    - Ollama
    - 最终答案生成
    - 法律结论推定

============================================================
V6.1 第一阶段
============================================================

从原有 Legal Decision Engine 中独立事实提取逻辑。

事实识别规则现在已经进一步拆分为：

    legal_fact_contract.py
        ↓
    合同序列事实

    legal_fact_renewal.py
        ↓
    续订 / 续签 / 劳动者同意事实

    legal_fact_exclusion.py
        ↓
    第三十九条
    第四十条第一项
    第四十条第二项
    固定期限例外
    组合否定事实

============================================================
V6.1 第二阶段
============================================================

新增：

    extract_legal_facts()

负责将事实提取结果统一组装成：

    LegalFacts

注意：

    extract_legal_facts()
    不重新实现事实识别规则。

事实识别仍然由独立模块完成：

    legal_fact_contract.py
    legal_fact_renewal.py
    legal_fact_exclusion.py

从而保证：

    “事实识别规则只有一套”。

============================================================
事实提取原则
============================================================

1. 只提取用户明确表达的事实。

2. 不因为合同次数自动推定续订。

3. 不因为合同次数自动推定劳动者同意。

4. 不因为没有提及某项事实就认为该事实不存在。

5. 组合否定必须拆解成三个明确事实。

6. Fact 层只表达事实：

       True
           明确存在 / 明确发生

       False
           明确不存在 / 明确未发生

       None
           用户没有明确说明

7. Fact 层不直接使用：

       SATISFIED
       NOT_SATISFIED
       UNKNOWN

   这些属于 Legal Decision Engine 的 Condition 层语义。

============================================================
模块依赖关系
============================================================

    legal_common.py
          │
          ├──────────────────────┐
          ↓                      ↓
    legal_fact_contract    legal_fact_renewal
          │                      │
          │                      │
          └──────────┬───────────┘
                     ↓
             legal_fact_exclusion
                     │
                     ↓
           legal_fact_extractor
                     │
                     ↓
               LegalFacts
"""

from __future__ import annotations

from typing import List

from src.legal_common import normalize_text, unique_texts
from src.legal_fact_contract import extract_contract_sequence
from src.legal_fact_exclusion import extract_exclusion_facts
from src.legal_fact_models import LegalFacts
from src.legal_fact_renewal import (
    has_completed_renewal,
    has_worker_agreement,
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
    职责
    ========================================================

    本函数现在作为：

        “事实提取总协调器”

    不再直接实现：

        - 合同次数识别规则
        - 续订识别规则
        - 劳动者同意识别规则
        - Article 39 识别规则
        - Article 40(1) 识别规则
        - Article 40(2) 识别规则
        - 固定期限例外识别规则

    上述规则分别由：

        legal_fact_contract.py
        legal_fact_renewal.py
        legal_fact_exclusion.py

    负责。

    ========================================================
    重要原则
    ========================================================

    本函数只汇总：

        用户明确表达的事实。

    不进行：

        法律推定
        条件判断
        Decision 判断
        ConditionResult 判断

    ========================================================
    V6.0-27 行为保持
    ========================================================

    保留原有 explicit_facts 输出字符串：

        公司连续签订三次固定期限劳动合同

        连续订立二次固定期限劳动合同

        存在明确续订劳动合同事实

        劳动者明确提出或者同意续订、订立劳动合同

        劳动者提出订立固定期限劳动合同

        劳动者没有提出订立固定期限劳动合同

        劳动者不存在《劳动合同法》第三十九条规定的情形

        劳动者存在《劳动合同法》第三十九条规定的情形

        劳动者不存在《劳动合同法》第四十条第一项规定的情形

        劳动者存在《劳动合同法》第四十条第一项规定的情形

        劳动者不存在《劳动合同法》第四十条第二项规定的情形

        劳动者存在《劳动合同法》第四十条第二项规定的情形

    ========================================================
    注意
    ========================================================

    本函数不直接修改：

        LegalFacts

    只返回：

        explicit_facts
    """

    facts: List[str] = []

    # ========================================================
    # 一、合同事实
    # ========================================================

    contract_sequence = extract_contract_sequence(
        question
    )

    # --------------------------------------------------------
    # 重要边界：
    #
    # explicit_facts 只记录用户明确表达的事实。
    #
    # 不能使用 contract_sequence.count 反向制造
    # 用户没有明确说出的“三次固定期限劳动合同”事实。
    #
    # 例如：
    #
    # “连续签订两次固定期限劳动合同，后来又续订”
    #
    # contract_sequence 可以结构化为：
    #
    #     count = 3
    #
    # 但用户明确表达的仍然只是：
    #
    #     连续签订两次固定期限劳动合同
    #     存在明确续订劳动合同事实
    #
    # 因此这里必须直接检查用户原文。
    # --------------------------------------------------------

    normalized_question = normalize_text(
        question
    )

    # --------------------------------------------------------
    # 用户明确表达“三次固定期限劳动合同”的事实模式。
    #
    # 注意：
    #
    # 这里与 legal_fact_contract.py 中的结构化识别规则
    # 可以存在相同模式，但职责不同。
    #
    # legal_fact_contract.py：
    #
    #     负责生成 ContractSequence
    #
    # 本函数：
    #
    #     负责判断用户是否明确说出了该事实，
    #     从而生成 explicit_facts。
    #
    # 不能使用 contract_sequence.count 作为判断依据。
    # --------------------------------------------------------

    THREE_CONTRACT_FACT_PATTERNS = [
        "连续签订三次固定期限劳动合同",
        "连续订立三次固定期限劳动合同",
        "连续签了三次固定期限劳动合同",
        "连续签订了三次固定期限劳动合同",
        "连续订立了三次固定期限劳动合同",
    ]

    TWO_CONTRACT_FACT_PATTERNS = [
        "连续签订两次固定期限劳动合同",
        "连续订立两次固定期限劳动合同",
        "连续签了两次固定期限劳动合同",
        "连续签订了两次固定期限劳动合同",
        "连续订立了两次固定期限劳动合同",
    ]

    # --------------------------------------------------------
    # 三次固定期限劳动合同
    #
    # 只有用户原文明确出现“三次”，
    # 才允许写入：
    #
    #     公司连续签订三次固定期限劳动合同
    #
    # 即使 contract_sequence.count == 3，
    # 也不能在这里自动生成该事实。
    # --------------------------------------------------------

    if any(
        normalize_text(pattern) in normalized_question
        for pattern in THREE_CONTRACT_FACT_PATTERNS
    ):
        facts.append(
            "公司连续签订三次固定期限劳动合同"
        )

    # --------------------------------------------------------
    # 两次固定期限劳动合同
    #
    # 注意：
    #
    # 如果问题是：
    #
    #     “公司连续签订两次固定期限劳动合同，
    #      后来又续订劳动合同”
    #
    # contract_sequence.count
    # 可能已经被结构化为：
    #
    #     3
    #
    # 但是 explicit_facts 仍然必须记录：
    #
    #     连续订立二次固定期限劳动合同
    #
    # 而不能错误生成：
    #
    #     公司连续签订三次固定期限劳动合同
    #
    # 这就是：
    #
    #     “结构化事实不能反向污染显式用户事实”
    # --------------------------------------------------------

    elif any(
        normalize_text(pattern) in normalized_question
        for pattern in TWO_CONTRACT_FACT_PATTERNS
    ):
        facts.append(
            "连续订立二次固定期限劳动合同"
        )

    # ========================================================
    # 二、续订事实
    # ========================================================

    if has_completed_renewal(question):

        facts.append(
            "存在明确续订劳动合同事实"
        )

    # ========================================================
    # 三、劳动者提出或者同意续订
    # ========================================================

    if has_worker_agreement(question):

        facts.append(
            "劳动者明确提出或者同意续订、订立劳动合同"
        )

    # ========================================================
    # 四、Article 39 / Article 40 / Fixed-Term Exception
    # ========================================================

    exclusion_facts = extract_exclusion_facts(
        question
    )

    # --------------------------------------------------------
    # Article 39
    # --------------------------------------------------------

    article_39 = exclusion_facts.get(
        "article_39"
    )

    if article_39 is False:

        facts.append(
            "劳动者不存在《劳动合同法》第三十九条规定的情形"
        )

    elif article_39 is True:

        facts.append(
            "劳动者存在《劳动合同法》第三十九条规定的情形"
        )

    # --------------------------------------------------------
    # Article 40(1)
    # --------------------------------------------------------

    article_40_1 = exclusion_facts.get(
        "article_40_1"
    )

    if article_40_1 is False:

        facts.append(
            "劳动者不存在《劳动合同法》第四十条第一项规定的情形"
        )

    elif article_40_1 is True:

        facts.append(
            "劳动者存在《劳动合同法》第四十条第一项规定的情形"
        )

    # --------------------------------------------------------
    # Article 40(2)
    # --------------------------------------------------------

    article_40_2 = exclusion_facts.get(
        "article_40_2"
    )

    if article_40_2 is False:

        facts.append(
            "劳动者不存在《劳动合同法》第四十条第二项规定的情形"
        )

    elif article_40_2 is True:

        facts.append(
            "劳动者存在《劳动合同法》第四十条第二项规定的情形"
        )

    # --------------------------------------------------------
    # Fixed-Term Exception
    # --------------------------------------------------------

    fixed_term_exception = exclusion_facts.get(
        "fixed_term_exception"
    )

    if fixed_term_exception is True:

        facts.append(
            "劳动者提出订立固定期限劳动合同"
        )

    elif fixed_term_exception is False:

        facts.append(
            "劳动者没有提出订立固定期限劳动合同"
        )

    # ========================================================
    # 五、最终去重
    # ========================================================

    return unique_texts(
        facts
    )


# ============================================================
# Legal Facts Extraction
# ============================================================

def extract_legal_facts(
    question: str,
) -> LegalFacts:
    """
    V6.1：

    将现有事实提取结果统一组装成 LegalFacts。

    --------------------------------------------------------
    重要设计原则
    --------------------------------------------------------

    本函数不重新实现事实识别规则。

    事实识别仍然由：

        extract_explicit_facts()
        extract_contract_sequence()
        has_completed_renewal()
        has_worker_agreement()
        extract_exclusion_facts()

    完成。

    本函数只负责：

        “把已经识别出来的事实放入 LegalFacts”。

    这样可以保证整个系统只有一套事实识别规则。

    --------------------------------------------------------
    Fact 层三态语义
    --------------------------------------------------------

        True
            明确存在 / 明确发生

        False
            明确不存在 / 明确未发生

        None
            未明确说明

    --------------------------------------------------------
    与 Condition 层的关系
    --------------------------------------------------------

    例如：

        article_39 = True

    只表示：

        用户明确说存在第三十九条情形。

    Legal Decision Engine 后续才负责将其转换成：

        EXCLUSION
        NOT_SATISFIED

    同理：

        article_39 = False

    后续转换为：

        EXCLUSION
        SATISFIED

    而：

        article_39 = None

    后续转换为：

        EXCLUSION
        UNKNOWN

    --------------------------------------------------------
    重要边界
    --------------------------------------------------------

    本函数不会因为：

        contract_sequence.count >= 3

    自动设置：

        completed_renewal = True

    也不会因为：

        worker_agreement = True

    自动设置：

        completed_renewal = True

    所有事实必须来自用户明确表达。
    """

    # ========================================================
    # 第一步：复用已经验证过的事实提取逻辑
    # ========================================================

    explicit_facts = extract_explicit_facts(
        question
    )

    contract_sequence = extract_contract_sequence(
        question
    )

    # ========================================================
    # 第二步：已完成续订
    # ========================================================

    completed_renewal = (
        True
        if has_completed_renewal(question)
        else None
    )

    # ========================================================
    # 第三步：劳动者提出或者同意续订
    #
    # V6.1：
    #
    # worker_agreement 是结构化用户事实，
    # 必须直接来自用户问题的事实提取结果。
    #
    # 不再从 explicit_facts 反向读取。
    #
    # 这样可以避免：
    #
    # question
    #     ↓
    # explicit_facts
    #     ↓
    # worker_agreement
    #
    # 形成不必要的 Fact → Fact 依赖。
    #
    # has_worker_agreement() 是 Worker Agreement
    # 事实的唯一识别入口。
    #
    # True  = 用户明确表达
    # None  = 用户没有明确表达
    #
    # 注意：
    #
    # False 不由本层推导。
    # ========================================================

    worker_agreement = (
        True
        if has_worker_agreement(question)
        else None
    )

    # ========================================================
    # 第四步：排除 / 例外事实
    #
    # 这里使用独立事实模块的统一结果。
    #
    # 注意：
    #
    # 这里不是重新实现识别规则，
    # 只是读取已经统一识别出的事实结果。
    # ========================================================

    exclusion_facts = extract_exclusion_facts(
        question
    )

    article_39 = exclusion_facts.get(
        "article_39"
    )

    article_40_1 = exclusion_facts.get(
        "article_40_1"
    )

    article_40_2 = exclusion_facts.get(
        "article_40_2"
    )

    fixed_term_exception = exclusion_facts.get(
        "fixed_term_exception"
    )

    # ========================================================
    # 第五步：构造 LegalFacts
    # ========================================================

    return LegalFacts(
        explicit_facts=explicit_facts,
        contract_sequence=contract_sequence,
        completed_renewal=completed_renewal,
        worker_agreement=worker_agreement,
        article_39=article_39,
        article_40_1=article_40_1,
        article_40_2=article_40_2,
        fixed_term_exception=fixed_term_exception,
    )


# ============================================================
# Module Self Test
# ============================================================

if __name__ == "__main__":

    print("=" * 70)
    print("RAG V6.1 Legal Fact Extractor Self Test")
    print("=" * 70)

    test_question = (
        "公司连续签订三次固定期限劳动合同，"
        "员工也同意续订，"
        "不存在劳动合同法第三十九条和第四十条第一项、第二项规定的情形。"
    )

    print("\n问题：")
    print(test_question)

    # ========================================================
    # Explicit Facts
    # ========================================================

    print("\n【Explicit Facts】")

    explicit_facts = extract_explicit_facts(
        test_question
    )

    for index, fact in enumerate(
        explicit_facts,
        start=1,
    ):

        print(
            f"{index}. {fact}"
        )

    # ========================================================
    # LegalFacts
    # ========================================================

    print("\n【LegalFacts】")

    legal_facts = extract_legal_facts(
        test_question
    )

    print(
        legal_facts.to_dict()
    )

    print("\n" + "=" * 70)
    print("Self Test Completed")
    print("=" * 70)