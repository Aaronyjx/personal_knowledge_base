# -*- coding: utf-8 -*-

"""
RAG V6.0-27

Legal Fact Validator

============================================================
功能
============================================================

负责验证最终答案是否忠实保留用户输入事实。

包含：

1. validate_fact_condition_mapping()
2. validate_user_facts()
3. validate_three_contract_fact()

本模块只负责 Fact Fidelity。
不负责：

- Answer Sanitization
- Condition Safety
- Legal Citation
- Decision Consistency
- Final Validation
"""

import re
from typing import Any, Dict, List

from src.legal_common import (
    ensure_list,
    normalize_text,
)


# ============================================================
# Fact Fidelity
# ============================================================


def validate_fact_condition_mapping(
    answer: str,
    question: str,
    decision: Dict[str, Any],
) -> bool:
    """
    V6.0-27：验证最终答案严格遵守 Fact → Condition → Consequence 依赖。

    对“三次固定期限劳动合同”问题：

    - 必须承认“三次”已经覆盖“连续订立二次固定期限劳动合同”数量门槛；
    - 不得把“三次”重新制造成第三次合同是否存在/是否连续的 UNKNOWN；
    - 不得把“是否续订劳动合同”偷换成“是否提出订立无固定期限劳动合同”；
    - 不得把“三次”直接解释为劳动者已经提出或同意下一次订立无固定期限劳动合同。
    """
    if not answer:
        return False

    q = normalize_text(question)
    has_three = (
        "三次" in q and "固定期限劳动合同" in q
    ) or any(
        "三次" in normalize_text(fact)
        and "固定期限劳动合同" in normalize_text(fact)
        for fact in ensure_list(decision.get("user_facts", []))
    )

    if not has_three:
        return True

    forbidden_patterns = [
        "第三次合同是否存在",
        "是否已经签订第三份合同",
        "第三次是否属于连续合同序列",
        "劳动者是否在第三次续订时提出或同意订立无固定期限劳动合同",
        "劳动者是否提出或同意订立无固定期限劳动合同",
    ]

    if any(pattern in answer for pattern in forbidden_patterns):
        return False

    # 禁止把“三次”事实直接等同于已经发生下一次续订或已经提出订立
    # 无固定期限劳动合同。
    invented_patterns = [
        "三次合同已经证明劳动者同意续订",
        "三次合同已经证明劳动者提出续订",
        "三次合同已经证明劳动者提出订立无固定期限劳动合同",
        "三次固定期限劳动合同即表示劳动者同意订立无固定期限劳动合同",
        "已经证明劳动者同意订立无固定期限劳动合同",
        "已经证明劳动者提出订立无固定期限劳动合同",
        "已经证明劳动者同意签订无固定期限劳动合同",
        "已经证明劳动者提出签订无固定期限劳动合同",
        "已经证明劳动者同意订立无固定期限劳动合同的义务",
        "三次固定期限劳动合同，所以已经证明劳动者同意订立无固定期限劳动合同",
    ]

    # 进一步防止条件语义偷换：
    # “劳动者提出或者同意续订、订立劳动合同”是原始法律条件，
    # 不能被改写成“劳动者已经提出/同意订立无固定期限劳动合同”。
    # 后者属于更具体、且并非原条件的意思表示。
    normalized_answer = normalize_text(answer)
    has_wrong_indefinite_condition = (
        ("劳动者同意" in normalized_answer or "劳动者提出" in normalized_answer)
        and (
            "订立无固定期限劳动合同" in normalized_answer
            or "签订无固定期限劳动合同" in normalized_answer
        )
        and not (
            "是否" in normalized_answer
            or "尚未确认" in normalized_answer
            or "不能证明" in normalized_answer
            or "无法确认" in normalized_answer
            or "不能直接证明" in normalized_answer
            or "未明确" in normalized_answer
            or "未知" in normalized_answer
        )
    )

    return (
        not any(pattern in answer for pattern in invented_patterns)
        and not has_wrong_indefinite_condition
    )


def validate_user_facts(
    answer: str,
    decision: Dict[str, Any],
) -> bool:
    """
    V6.0-16：用户事实保真验证。

    ============================================================
    核心原则
    ============================================================

    1. Ollama 不得修改用户已经确认的事实。

    2. 用户事实必须逐条进行验证，不能只检查某一个数字关键词。

    3. 用户事实中的合同次数必须保持一致：
       “两次”不能被改写成“三次”；
       “三次”不能被改写成“两次”。

    4. “两次”问题不能被模型自行扩张成：
       “公司已经连续签订三次固定期限劳动合同”。

    5. “三次”问题不能被模型自行缩减成：
       “公司连续签订二次固定期限劳动合同”。

    6. 用户事实允许进行合理的语言改写，例如：

       “连续签订两次固定期限劳动合同”
       ≈
       “连续订立二次固定期限劳动合同”

       “后来又续签了劳动合同”
       ≈
       “后来又续订了劳动合同”

       “存在劳动合同法第三十九条规定的情形”
       ≈
       “存在《劳动合同法》第三十九条规定的情形”。

    7. 法律规则中的：
       “连续订立二次固定期限劳动合同”

       只是法律规则内容，不能仅凭这一法律规则文本
       就认定用户事实已经被 Ollama 保留。

    8. 当前函数不仅检查“事实有没有被篡改”，
       还检查“用户事实有没有被完全遗漏”。

    9. 用户事实验证失败时，应当触发安全 Fallback，
       而不是允许 Ollama 输出未经验证的答案。
    """

    facts = ensure_list(
        decision.get(
            "user_facts",
            [],
        )
    )

    if not facts:
        return True

    answer_text = normalize_text(answer)

    # ========================================================
    # 安全检查
    # ========================================================

    if not answer_text:
        return False

    # ========================================================
    # 将答案拆分为不同语义区域
    #
    # 目的：
    #
    # 法律依据 / 法条原文中的内容不能直接被视为用户事实。
    #
    # 例如：
    #
    # 《劳动合同法》第十四条规定：
    # 连续订立二次固定期限劳动合同……
    #
    # 这属于法律规则，不属于用户事实。
    # ========================================================

    fact_candidate_text = answer_text

    excluded_sections = [
        "【法律依据】",
        "【核心法律依据】",
        "【相关法律依据】",
        "【法律规则】",
        "【法条依据】",
        "法律依据",
        "法律规则",
        "法条原文",
    ]

    for marker in excluded_sections:

        if marker in fact_candidate_text:

            prefix = fact_candidate_text.split(
                marker,
                1,
            )[0]

            suffix = fact_candidate_text.split(
                marker,
                1,
            )[1]

            # ------------------------------------------------
            # 删除法律依据区域。
            #
            # 如果后面还有新的明确章节，
            # 只删除当前法律依据区域。
            # ------------------------------------------------

            next_markers = [
                "【法律分析】",
                "【用户事实】",
                "【已满足条件】",
                "【不满足的必备条件】",
                "【已触发排除条件】",
                "【已触发例外条件】",
                "【尚未确认条件】",
                "【需要注意】",
                "【结论】",
            ]

            next_positions = []

            for next_marker in next_markers:

                position = suffix.find(
                    next_marker
                )

                if position >= 0:
                    next_positions.append(
                        position
                    )

            if next_positions:

                next_position = min(
                    next_positions
                )

                suffix = suffix[
                    next_position:
                ]

            else:
                suffix = ""

            fact_candidate_text = (
                prefix
                + suffix
            )

    # ========================================================
    # 规范化答案中的常见法律表达
    #
    # 注意：
    #
    # 这里只做语义等价处理，
    # 不改变事实数量。
    # ========================================================

    normalized_answer = (
        fact_candidate_text
        .replace(
            "《中华人民共和国劳动合同法》",
            "《劳动合同法》",
        )
        .replace(
            "中华人民共和国劳动合同法",
            "劳动合同法",
        )
        .replace(
            "劳动合同法第三十九条",
            "劳动合同法》第三十九条",
        )
    )

    # ========================================================
    # 用户事实逐条验证
    # ========================================================

    for fact in facts:

        fact = normalize_text(
            fact
        )

        if not fact:
            continue

        # ====================================================
        # 事实一：
        #
        # 连续订立二次固定期限劳动合同
        #
        # 当前用户问题中的实际事实：
        #
        # “公司连续签订两次固定期限劳动合同”
        # ====================================================

        if (
            "固定期限劳动合同" in fact
            and (
                "两次" in fact
                or "二次" in fact
            )
        ):

            two_contract_patterns = [
                "连续签订两次固定期限劳动合同",
                "连续订立两次固定期限劳动合同",
                "连续签订二次固定期限劳动合同",
                "连续订立二次固定期限劳动合同",
                "连续两次签订固定期限劳动合同",
                "连续两次订立固定期限劳动合同",
                "连续二次签订固定期限劳动合同",
                "连续二次订立固定期限劳动合同",
                "签订两次固定期限劳动合同",
                "订立两次固定期限劳动合同",
                "签订二次固定期限劳动合同",
                "订立二次固定期限劳动合同",
            ]

            matched = any(
                pattern in normalized_answer
                for pattern in two_contract_patterns
            )

            if not matched:

                has_two = (
                    "两次" in normalized_answer
                    or "二次" in normalized_answer
                )

                has_fixed_term = (
                    "固定期限劳动合同"
                    in normalized_answer
                )

                has_continuous = (
                    "连续签订" in normalized_answer
                    or "连续订立" in normalized_answer
                    or "连续两次" in normalized_answer
                    or "连续二次" in normalized_answer
                )

                matched = (
                    has_two
                    and has_fixed_term
                    and has_continuous
                )

            if not matched:
                return False

            wrong_three_patterns = [
                "公司连续签订三次固定期限劳动合同",
                "公司连续订立三次固定期限劳动合同",
                "公司已经连续签订三次固定期限劳动合同",
                "公司已经连续订立三次固定期限劳动合同",
                "用户连续签订三次固定期限劳动合同",
                "用户连续订立三次固定期限劳动合同",
                "用户已经连续签订三次固定期限劳动合同",
                "用户已经连续订立三次固定期限劳动合同",
                "已连续签订三次固定期限劳动合同",
                "已连续订立三次固定期限劳动合同",
                "已经连续签订三次固定期限劳动合同",
                "已经连续订立三次固定期限劳动合同",
                "实际连续签订三次固定期限劳动合同",
                "实际连续订立三次固定期限劳动合同",
            ]

            for pattern in wrong_three_patterns:

                if pattern in normalized_answer:
                    return False

        elif (
            "续订劳动合同" in fact
            or "续签劳动合同" in fact
            or "明确续订劳动合同" in fact
            or "明确续签劳动合同" in fact
        ):

            renewal_patterns = [
                "后来又续签了劳动合同",
                "后来又续订了劳动合同",
                "后来续签了劳动合同",
                "后来续订了劳动合同",
                "之后又续签了劳动合同",
                "之后又续订了劳动合同",
                "之后续签了劳动合同",
                "之后续订了劳动合同",
                "已经续签劳动合同",
                "已经续订劳动合同",
                "已续签劳动合同",
                "已续订劳动合同",
                "存在续签劳动合同事实",
                "存在续订劳动合同事实",
                "明确续签劳动合同",
                "明确续订劳动合同",
                "发生了劳动合同续签",
                "发生了劳动合同续订",
            ]

            matched = any(
                pattern in normalized_answer
                for pattern in renewal_patterns
            )

            if not matched:

                has_labor_contract = (
                    "劳动合同"
                    in normalized_answer
                )

                has_renewal_word = (
                    "续签" in normalized_answer
                    or "续订" in normalized_answer
                )

                matched = (
                    has_labor_contract
                    and has_renewal_word
                )

            if not matched:
                return False

        elif (
            "第三十九条" in fact
            and "情形" in fact
        ):

            article_39_patterns = [
                "劳动者存在《劳动合同法》第三十九条规定的情形",
                "劳动者存在劳动合同法》第三十九条规定的情形",
                "劳动者存在劳动合同法第三十九条规定的情形",
                "劳动者有《劳动合同法》第三十九条规定的情形",
                "劳动者有劳动合同法第三十九条规定的情形",
                "存在《劳动合同法》第三十九条规定的情形",
                "存在劳动合同法第三十九条规定的情形",
                "第三十九条规定的情形已经存在",
                "存在第三十九条规定的情形",
                "符合第三十九条规定的情形",
                "属于第三十九条规定的情形",
            ]

            matched = any(
                pattern in normalized_answer
                for pattern in article_39_patterns
            )

            if not matched:
                return False

        else:

            normalized_fact = normalize_text(
                fact
            )

            if (
                normalized_fact
                and normalized_fact
                not in normalized_answer
            ):
                return False

    has_three_fact = any(
        (
            "三次" in normalize_text(fact)
            and "固定期限劳动合同"
            in normalize_text(fact)
        )
        for fact in facts
    )

    if has_three_fact:

        if "三次" not in normalized_answer:
            return False

        wrong_two_patterns = [
            "用户连续签订两次固定期限劳动合同",
            "用户连续订立两次固定期限劳动合同",
            "用户连续签订二次固定期限劳动合同",
            "用户连续订立二次固定期限劳动合同",
            "公司连续签订两次固定期限劳动合同",
            "公司连续订立两次固定期限劳动合同",
            "公司连续签订二次固定期限劳动合同",
            "公司连续订立二次固定期限劳动合同",
            "用户事实是二次固定期限劳动合同",
            "用户事实为二次固定期限劳动合同",
            "用户实际签订二次固定期限劳动合同",
            "公司实际签订二次固定期限劳动合同",
        ]

        for pattern in wrong_two_patterns:

            if pattern in normalized_answer:
                return False

    return True


def validate_three_contract_fact(
    answer: str,
    decision: Dict[str, Any],
) -> bool:
    """
    V6.0-13 三次固定期限合同专项验证。

    “连续签订三次固定期限劳动合同”是用户事实。
    “连续订立二次固定期限劳动合同”可以合法地出现在法律规则
    或满足条件的表达中，但不能被当成用户事实的替换。

    因此本函数只拦截明确把“公司/用户三次事实”改写成“公司/用户二次
    事实”的表达，不再错误禁止法律条件中正常出现“二次”。
    """

    facts = ensure_list(
        decision.get(
            "user_facts",
            [],
        )
    )

    fact_text = "；".join(
        normalize_text(item)
        for item in facts
    )

    has_three_fact = (
        "三次" in fact_text
        and "固定期限劳动合同" in fact_text
    )

    if not has_three_fact:
        return True

    if "三次" not in answer:
        return False

    wrong_fact_patterns = [
        "用户连续签订二次固定期限劳动合同",
        "用户连续订立二次固定期限劳动合同",
        "公司连续签订二次固定期限劳动合同",
        "公司连续订立二次固定期限劳动合同",
        "用户事实是二次固定期限劳动合同",
        "用户事实为二次固定期限劳动合同",
        "用户实际签订二次固定期限劳动合同",
        "公司实际签订二次固定期限劳动合同",
    ]

    for pattern in wrong_fact_patterns:
        if pattern in answer:
            return False

    return True