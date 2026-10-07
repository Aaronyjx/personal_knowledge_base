# -*- coding: utf-8 -*-

"""
RAG V6.1

Legal Fact Validator

============================================================
功能
============================================================

负责验证最终答案是否忠实保留用户输入事实。

包含：

1. validate_user_facts()

V7 职责边界：

本模块只负责 Fact Fidelity，
即验证最终答案是否忠实保留 DecisionResult 中已经存在的用户事实。

本模块不负责：

- Fact → Condition 法律关系判定
- ConditionResult 生成
- Article 14 专项法律条件推理
- 三次固定期限劳动合同专项法律判断
- UNKNOWN / SATISFIED / NOT_SATISFIED 状态判定
- Answer Sanitization
- Condition Safety
- Legal Citation
- Decision Consistency
- Final Validation

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

    # ========================================================
    # V6.0-17：禁止“用户事实区域”出现 Engine 未提供的新事实
    #
    # 上面的验证负责检查：
    #
    #     Engine 已知事实是否被最终答案保留
    #
    # 但仅检查“已知事实是否保留”还不够。
    #
    # 例如 Engine 只有：
    #
    #     公司连续签订三次固定期限劳动合同
    #
    # LLM 却输出：
    #
    #     1. 用户事实：
    #     - 公司连续签订三次固定期限劳动合同
    #     - 劳动者存在《劳动合同法》第三十九条规定的情形
    #
    # 第二条并不是 Engine 提供的用户事实，必须拒绝。
    #
    # 注意：
    # 这里只检查明确的“用户事实”区域。
    # 法律分析、条件状态、法律依据中的法律内容不受影响。
    # ========================================================

    def _extract_explicit_user_fact_items(text: str) -> List[str]:
        if not text:
            return []

        normalized = text.replace("\r\n", "\n").replace("\r", "\n")

        start_patterns = [
            r"(?m)^\s*\d+\.\s*用户事实\s*：\s*$",
            r"(?m)^\s*用户事实\s*：\s*$",
            r"(?m)^\s*【用户事实】\s*$",
        ]

        start_match = None

        for pattern in start_patterns:
            match = re.search(pattern, normalized)
            if match:
                start_match = match
                break

        if not start_match:
            return []

        section = normalized[start_match.end():]

        # 用户事实区域在下一个明确的顶层结构出现时结束。
        end_patterns = [
            # ------------------------------------------------
            # Deterministic Fallback 的用户事实之后可能出现：
            #
            # 2. 已满足条件：
            # 3. 不满足的必备条件：
            # 4. 已触发排除条件：
            # 5. 已触发例外条件：
            # 6. 尚未确认条件：
            # 7. 法律后果：
            #
            # 这些全部属于后续结构，不能继续视为用户事实。
            # ------------------------------------------------
            r"(?m)^\s*\d+\.\s*(?:已满足条件|不满足的必备条件|已触发排除条件|已触发例外条件|尚未确认条件|法律后果)\s*：",

            # 条件状态及其兼容写法。
            r"(?m)^\s*\d+\.\s*(?:条件状态|当前条件状态|法律分析|分析结果|判断结果)\s*：",
            r"(?m)^\s*(?:条件状态|当前条件状态|法律分析|分析结果|判断结果)\s*：",

            # 正式 Section。
            r"(?m)^\s*【(?:法律依据|法律分析|需要注意|结论)】",
            r"(?m)^\s*\d+\.\s*【(?:法律依据|法律分析|需要注意|结论)】",
        ]

        end_positions = []

        for pattern in end_patterns:
            match = re.search(pattern, section)
            if match:
                end_positions.append(match.start())

        if end_positions:
            section = section[:min(end_positions)]

        items: List[str] = []

        for line in section.split("\n"):
            line = line.strip()

            if not line:
                continue

            # 标准格式：
            #
            # - 公司连续签订三次固定期限劳动合同
            #
            if line.startswith("-"):
                value = line[1:].strip()

                if value:
                    items.append(value)

                continue

            # 兼容项目符号。
            if line.startswith("•"):
                value = line[1:].strip()

                if value:
                    items.append(value)

                continue

            # 兼容：
            #
            # 1. 公司连续签订三次固定期限劳动合同
            #
            numbered = re.match(
                r"^\d+[\.、]\s*(.+)$",
                line,
            )

            if numbered:
                value = numbered.group(1).strip()

                if (
                    value
                    and "用户事实" not in value
                ):
                    items.append(value)

        return items

    def _normalize_fact_for_match(
        value: str,
    ) -> str:
        value = normalize_text(value)

        value = (
            value
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

        return value.strip(
            " ：:，,。；;"
        )

    def _fact_matches_engine_fact(
        answer_fact: str,
        engine_fact: str,
    ) -> bool:
        answer_fact = _normalize_fact_for_match(
            answer_fact
        )

        engine_fact = _normalize_fact_for_match(
            engine_fact
        )

        if not answer_fact or not engine_fact:
            return False

        # ----------------------------------------------------
        # 1. 标准化后完全一致
        # ----------------------------------------------------
        if answer_fact == engine_fact:
            return True

        # ----------------------------------------------------
        # 2. 三次固定期限劳动合同事实
        # ----------------------------------------------------
        if (
            "三次" in engine_fact
            and "固定期限劳动合同" in engine_fact
        ):
            return (
                "三次" in answer_fact
                and "固定期限劳动合同" in answer_fact
                and (
                    "连续签订" in answer_fact
                    or "连续订立" in answer_fact
                    or "连续三次" in answer_fact
                )
            )

        # ----------------------------------------------------
        # 3. 两次固定期限劳动合同事实
        # ----------------------------------------------------
        if (
            "固定期限劳动合同" in engine_fact
            and (
                "两次" in engine_fact
                or "二次" in engine_fact
            )
        ):
            has_two = (
                "两次" in answer_fact
                or "二次" in answer_fact
            )

            has_fixed_term = (
                "固定期限劳动合同"
                in answer_fact
            )

            has_continuous = (
                "连续签订" in answer_fact
                or "连续订立" in answer_fact
                or "连续两次" in answer_fact
                or "连续二次" in answer_fact
            )

            return (
                has_two
                and has_fixed_term
                and has_continuous
            )

        # ----------------------------------------------------
        # 4. 续订 / 续签劳动合同事实
        # ----------------------------------------------------
        if (
            "续订劳动合同" in engine_fact
            or "续签劳动合同" in engine_fact
            or "明确续订劳动合同" in engine_fact
            or "明确续签劳动合同" in engine_fact
        ):
            return (
                "劳动合同" in answer_fact
                and (
                    "续签" in answer_fact
                    or "续订" in answer_fact
                )
            )

        # ----------------------------------------------------
        # 5. 第39条用户事实
        # ----------------------------------------------------
        if (
            "第三十九条" in engine_fact
            and "情形" in engine_fact
        ):
            return (
                "第三十九条" in answer_fact
                and "情形" in answer_fact
                and (
                    "存在" in answer_fact
                    or "有" in answer_fact
                    or "符合" in answer_fact
                    or "属于" in answer_fact
                )
            )

        return False

    explicit_user_fact_items = (
        _extract_explicit_user_fact_items(answer)
    )

    if explicit_user_fact_items:
        engine_fact_values: List[str] = []

        for engine_fact in facts:

            if isinstance(engine_fact, dict):
                engine_fact = (
                    engine_fact.get("fact")
                    or engine_fact.get("text")
                    or ""
                )

            engine_fact = normalize_text(
                engine_fact
            )

            if engine_fact:
                engine_fact_values.append(
                    engine_fact
                )

        # ----------------------------------------------------
        # 用户事实区域中的每一条事实，
        # 必须能够对应到 Engine 已确认的用户事实。
        #
        # 因此：
        #
        # Engine:
        #   三次固定期限劳动合同
        #
        # Answer:
        #   三次固定期限劳动合同
        #   + 第39条情形
        #
        # 第二条无法匹配 Engine，
        # validate_user_facts() 必须返回 False。
        # ----------------------------------------------------
        for answer_fact in explicit_user_fact_items:

            if not any(
                _fact_matches_engine_fact(
                    answer_fact=answer_fact,
                    engine_fact=engine_fact,
                )
                for engine_fact in engine_fact_values
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
