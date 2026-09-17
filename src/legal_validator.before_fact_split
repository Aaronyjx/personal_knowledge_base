# -*- coding: utf-8 -*-

"""
RAG V6.0-27
Legal Validation Layer

============================================================
功能
============================================================

负责 Legal RAG 的最终答案验证与安全边界检查。

主要职责：

    1. 答案清洗与结构验证
    2. 用户事实忠实性验证
    3. Fact → Condition 映射验证
    4. Decision 与答案一致性验证
    5. UNKNOWN / CONDITIONAL 安全验证
    6. 法律条件防臆造验证
    7. 法律依据与 Citation 验证
    8. Decision Engine ConditionResult 完整性验证
    9. Condition Category 完整性验证
    10. 最终 Validation 与安全 Fallback 调度

本模块不负责：

    - Structured Article → Rule
    - Legal Decision Engine 判定
    - Decision Adapter
    - Answer Builder
    - Ollama Prompt / LLM 调用

原则：

    Validation 只能验证已经产生的结构化结果，
    不得在验证阶段重新推导法律结论。
============================================================
"""

import re
from typing import Any, Dict, List

from src.legal_common import (
    ensure_list,
    get_rule_value,
    normalize_text,
)

from src.legal_rule_builder import (
    build_rules_from_articles,
)


# ============================================================
# Legal Decision Engine 状态
# ============================================================

DECISION_DEFINITE = "DEFINITE"

DECISION_CONDITIONAL = "CONDITIONAL"

DECISION_NOT_ESTABLISHED = "NOT_ESTABLISHED"


# ============================================================
# 最终答案结构
# ============================================================

SECTION_CONCLUSION = "【结论】"

SECTION_BASIS = "【法律依据】"

SECTION_ANALYSIS = "【法律分析】"

SECTION_NOTICE = "【需要注意】"


REQUIRED_SECTIONS = [
    SECTION_CONCLUSION,
    SECTION_BASIS,
    SECTION_ANALYSIS,
    SECTION_NOTICE,
]


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


def clean_answer(
    answer: str,
) -> str:

    if not answer:
        return ""

    answer = normalize_text(answer)

    # 删除 Qwen Thinking 内容。

    answer = re.sub(
        r"<think>.*?</think>",
        "",
        answer,
        flags=re.DOTALL,
    )

    answer = re.sub(
        r"<think>.*",
        "",
        answer,
        flags=re.DOTALL,
    )

    answer = answer.strip()

    # 删除 Markdown 标题符号。

    answer = re.sub(
        r"(?m)^\s*#+\s*【",
        "【",
        answer,
    )

    # 多个空行压缩。

    answer = re.sub(
        r"\n{3,}",
        "\n\n",
        answer,
    )

    # 如果四段标题存在，
    # 从第一个标题开始保留。

    positions = []

    for section in REQUIRED_SECTIONS:

        position = answer.find(section)

        if position >= 0:
            positions.append(
                position
            )

    if positions:

        start = min(positions)

        answer = answer[start:]

    # 删除重复标题。

    answer = remove_duplicate_sections(
        answer
    )

    return answer.strip()


def remove_duplicate_sections(
    text: str,
) -> str:

    if not text:
        return ""

    pattern = (
        r"(【结论】|【法律依据】|【法律分析】|【需要注意】)"
    )

    parts = re.split(
        pattern,
        text,
    )

    if len(parts) < 3:
        return text

    result = []

    seen = set()

    i = 0

    while i < len(parts):

        part = parts[i]

        if part in REQUIRED_SECTIONS:

            section_name = part

            body = ""

            if i + 1 < len(parts):
                body = parts[i + 1]

            if section_name not in seen:

                result.append(
                    section_name
                )

                result.append(
                    body
                )

                seen.add(
                    section_name
                )

            i += 2

        else:

            if part.strip() and not result:

                result.append(part)

            i += 1

    return "".join(result).strip()


def validate_answer_structure(
    answer: str,
) -> bool:

    if not answer:
        return False

    for section in REQUIRED_SECTIONS:

        if answer.count(section) != 1:
            return False

    # 检查标题顺序。

    positions = [
        answer.find(section)
        for section in REQUIRED_SECTIONS
    ]

    if positions != sorted(positions):
        return False

    return True


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

            # ------------------------------------------------
            # 如果没有出现完整事实表达，
            # 再检查“连续 + 两次/二次 + 固定期限劳动合同”
            # 的组合表达。
            # ------------------------------------------------

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

            # ------------------------------------------------
            # 两次事实完全没有被保留。
            #
            # 注意：
            #
            # 这正是当前 Ollama 输出的问题。
            #
            # 当前输出没有“两次/二次固定期限劳动合同”
            # 的用户事实，因此这里应当返回 False。
            # ------------------------------------------------

            if not matched:
                return False

            # ------------------------------------------------
            # 防止“两次”被错误扩大成“三次”。
            #
            # 这里主要检查具有用户事实语义的表达，
            # 而不是简单禁止答案中出现“三次”。
            #
            # 因为法律规则中也可能出现“三次”等讨论。
            # ------------------------------------------------

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

        # ====================================================
        # 事实二：
        #
        # 存在明确续订劳动合同事实
        #
        # 允许：
        #
        # 后来又续签了劳动合同
        # 后来又续订了劳动合同
        # 之后又续签了劳动合同
        # 之后又续订了劳动合同
        # 已经续签劳动合同
        # 已经续订劳动合同
        # 存在续签劳动合同事实
        # 存在续订劳动合同事实
        # ====================================================

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

            # ------------------------------------------------
            # 补充组合判断。
            #
            # 例如：
            #
            # “双方后来再次签订劳动合同”
            #
            # 也可以表达续订事实。
            # ------------------------------------------------

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

        # ====================================================
        # 事实三：
        #
        # 劳动者存在《劳动合同法》第三十九条规定的情形
        # ====================================================

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

        # ====================================================
        # 其它用户事实
        #
        # 对目前已经结构化的核心事实采用保守策略：
        #
        # 如果事实没有被上述规则识别，
        # 则要求该事实的核心文本直接出现。
        #
        # 防止未来新增 user_facts 后，
        # 验证器静默放过未验证事实。
        # ====================================================

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
    # 三次固定期限劳动合同的反向验证
    #
    # 如果用户事实本身明确是“三次”，
    # 则必须保留“三次”，并禁止被改写成“两次”。
    # ========================================================

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

    # ========================================================
    # 所有用户事实均通过验证
    # ========================================================

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

    # 只禁止明确把用户事实改写成“二次”。
    # 法律规则本身出现“二次”是允许的。
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


def validate_no_manufactured_unknown(
    answer: str,
    decision: Dict[str, Any],
) -> bool:
    """
    V6.0-27：禁止对已经明确存在的合同事实再次制造 UNKNOWN。

    注意：

    “续订劳动合同”本身仍然可以是 Engine 返回的 UNKNOWN。
    本检查只禁止把用户已经明确给出的：

        公司连续签订三次固定期限劳动合同

    再写成“第三份合同是否存在”等重复事实确认。
    """

    facts = ensure_list(
        decision.get("user_facts", [])
    )

    fact_text = "；".join(
        normalize_text(item)
        for item in facts
    )

    if not (
        "三次" in fact_text
        and "固定期限劳动合同" in fact_text
    ):
        return True

    answer_text = normalize_text(answer)

    forbidden = [
        "第三次合同是否存在",
        "第三次合同是否已经存在",
        "第三份合同是否存在",
        "第三份合同是否已经存在",
        "是否已经签订第三份合同",
        "是否已经签订第三次合同",
        "第三次是否属于连续合同序列",
        "第三次合同是否属于连续合同序列",
    ]

    unresolved = [
        "是否",
        "尚不明确",
        "尚未明确",
        "无法确认",
        "不能确认",
        "需要进一步确认",
        "需进一步确认",
        "仍需确认",
        "需要进一步判断",
        "需进一步判断",
        "无法判断",
        "不能判断",
        "尚待确认",
        "待确认",
    ]

    for pattern in forbidden:
        if pattern in answer_text and any(
            marker in answer_text
            for marker in unresolved
        ):
            return False

    return True


def validate_legal_condition_invention(
    answer: str,
    decision: Dict[str, Any],
) -> bool:
    """
    V6.0-27：法律条件防臆造验证。

    核心原则：

        Ollama 只能表达 Structured Decision / Rules 中已经存在的
        法律条件，不能自行创造新的法律前提、例外或义务条件。

    V6.0-19 暴露的问题：

        Structured Decision = CONDITIONAL
                ↓
        Ollama 自行补充“劳动者未明确提出订立无固定期限劳动合同”等条件
                ↓
        原有 UNKNOWN / CONDITIONAL Validation 仍可能通过

    因此 V6.0-22 增加一层独立验证：

    1. 收集当前 Structured Rules 的全部结构化文本。
    2. 对明显的“法律条件发明”表达进行拦截。
    3. 特别禁止把“劳动者未提出订立无固定期限劳动合同”写成
       无固定期限劳动合同的前置条件，除非 Structured Rules 明确包含
       该条件。
    4. 禁止使用笼统的“劳动者不符合条件”替代具体结构化法律条件。
    5. 不禁止合法引用 Rules 中真实存在的“劳动者提出订立固定期限劳动合同”
       等条件；是否允许必须以 Structured Rules 实际内容为准。

    返回：
        True  = 未发现结构化法律条件之外的明显新增条件。
        False = 发现法律条件臆造。
    """

    if not answer:
        return False

    answer_text = normalize_text(answer)

    rules = ensure_list(
        decision.get(
            "rules",
            [],
        )
    )

    # --------------------------------------------------------
    # 构建 Structured Rules 文本。
    # --------------------------------------------------------
    #
    # 不要求规则必须使用固定字段。
    # 尽可能收集所有常见结构化字段，避免误伤真实规则条件。
    # --------------------------------------------------------

    rule_text_parts = []

    preferred_fields = [
        "law_name",
        "article_number",
        "article_text",
        "rule_summary",
        "condition",
        "conditions",
        "requirements",
        "requirement",
        "exception",
        "exceptions",
        "rule_text",
        "text",
        "legal_effect",
        "legal_consequence",
    ]

    def append_rule_value(value: Any):
        if isinstance(value, dict):
            for nested_value in value.values():
                append_rule_value(nested_value)
        elif isinstance(value, list):
            for nested_value in value:
                append_rule_value(nested_value)
        else:
            text = normalize_text(value)
            if text:
                rule_text_parts.append(text)

    for rule in rules:
        if isinstance(rule, dict):
            for field in preferred_fields:
                if field in rule:
                    append_rule_value(rule.get(field))
        else:
            append_rule_value(rule)

    rule_text = "；".join(rule_text_parts)

    # --------------------------------------------------------
    # 明显的法律条件臆造模式。
    # --------------------------------------------------------
    #
    # 注意：
    #
    # 不能仅仅因为回答“提到了”错误条件，就认定模型臆造了该条件。
    #
    # 例如：
    #
    #     “不能将‘劳动者未提出订立无固定期限劳动合同’
    #      作为本题的判断前提。”
    #
    # 这是在“否定错误条件”，不是在“创造错误条件”。
    #
    # 因此必须区分：
    #
    #     正向使用错误条件
    #
    # 与：
    #
    #     否定 / 禁止 / 纠正错误条件
    #
    # --------------------------------------------------------

    invented_patterns = [
        "劳动者未明确提出订立无固定期限劳动合同",
        "劳动者未提出订立无固定期限劳动合同",
        "劳动者未明确提出签订无固定期限劳动合同",
        "劳动者未提出签订无固定期限劳动合同",
        "劳动者没有提出订立无固定期限劳动合同",
        "劳动者没有提出签订无固定期限劳动合同",
        "劳动者未明确要求订立无固定期限劳动合同",
        "劳动者未明确要求签订无固定期限劳动合同",
        "劳动者没有要求订立无固定期限劳动合同",
        "劳动者没有要求签订无固定期限劳动合同",
        "劳动者必须明确提出订立无固定期限劳动合同",
        "劳动者必须明确提出签订无固定期限劳动合同",
        "劳动者必须提出订立无固定期限劳动合同",
        "劳动者必须提出签订无固定期限劳动合同",
        "劳动者需要明确提出订立无固定期限劳动合同",
        "劳动者需要明确提出签订无固定期限劳动合同",
        "劳动者需要提出订立无固定期限劳动合同",
        "劳动者需要提出签订无固定期限劳动合同",
        "劳动者不符合订立无固定期限劳动合同的条件",
        "劳动者不符合签订无固定期限劳动合同的条件",
        "劳动者不符合无固定期限劳动合同的条件",
        "劳动者不具备订立无固定期限劳动合同的条件",
        "劳动者不具备签订无固定期限劳动合同的条件",
        "劳动者不具备无固定期限劳动合同的条件",
    ]

    # --------------------------------------------------------
    # 判断某个错误条件是否只是被“否定/禁止/纠正”提及。
    # --------------------------------------------------------

    negation_patterns = [
        "不能将",
        "不能把",
        "不得将",
        "不得把",
        "不应将",
        "不应把",
        "禁止将",
        "禁止把",
        "不可将",
        "不可把",
        "不宜将",
        "不能认为",
        "不得认为",
        "不应认为",
        "不能视为",
        "不得视为",
        "不应视为",
        "并不能证明",
        "不能证明",
        "不足以证明",
        "不足以认定",
        "不能据此认定",
        "不能据此认为",
        "不属于",
        "并非",
        "不是",
        "并不能作为",
        "不能作为",
        "不得作为",
        "不应作为",
        "不应当作为",
    ]

    # --------------------------------------------------------
    # 逐项检查。
    # --------------------------------------------------------

    for pattern in invented_patterns:

        position = answer_text.find(pattern)

        if position < 0:
            continue

        # 取出错误条件前面的有限上下文。
        #
        # 中文法律回答中，否定性表达通常会紧邻被否定的条件。
        context_start = max(
            0,
            position - 40,
        )

        prefix_context = answer_text[
            context_start:position
        ]

        # 如果错误条件只是出现在：
        #
        #     不能将……
        #     不得把……
        #     不能证明……
        #
        # 等纠错性上下文中，则不能判定为“臆造”。
        if any(
            marker in prefix_context
            for marker in negation_patterns
        ):
            continue

        # 如果 Structured Rules 明确存在该条件，
        # 则也不能视为新条件。
        if pattern in rule_text:
            continue

        # 到这里才认为模型真正把该错误条件当作
        # 当前法律判断的一个实质性前提。
        return False

    # 如果 Rules 中没有对应条件，则属于新增法律条件。
    for pattern in invented_patterns:
        if pattern in answer_text and pattern not in rule_text:
            return False

    # --------------------------------------------------------
    # “其他法定条件”笼统化检查。
    # --------------------------------------------------------
    #
    # “其他法定条件”本身不是法律依据。
    # 如果它被写成当前 UNKNOWN / 免责条件，而 Rules 中没有
    # 对应的具体例外或条件，就属于模型自行扩张。
    # --------------------------------------------------------

    vague_condition_patterns = [
        "其他法定条件",
        "其他法律条件",
        "其他法定要求",
        "其他法律要求",
        "不符合其他法定条件",
        "不符合其他法律条件",
        "存在其他法定条件",
        "存在其他法律条件",
    ]

    has_structured_exception = any(
        field in rule_text
        for field in [
            "例外",
            "除外",
            "不适用",
            "终止",
            "解除",
            "固定期限劳动合同",
        ]
    )

    # 仅当模型把笼统条件写成新的判断依据时拦截。
    # “结构化法律规则中仍存在尚未确认的条件”属于流程性表达，
    # 不在这里拦截。
    for pattern in vague_condition_patterns:
        if pattern not in answer_text:
            continue

        structural_reference_patterns = [
            "结构化",
            "规则中",
            "法律依据中",
            "法律规则中",
            "已经确认",
            "尚未确认",
            "未确认",
        ]

        if any(
            marker in answer_text
            for marker in structural_reference_patterns
        ):
            continue

        if not has_structured_exception:
            return False

    return True


def validate_conditional_state(
    answer: str,
    decision: Dict[str, Any],
) -> bool:

    engine_status = normalize_text(
        decision.get(
            "engine_decision",
            "",
        )
    ).upper()

    if engine_status != DECISION_CONDITIONAL:
        return True

    # CONDITIONAL 状态必须保留条件性。
    #
    # 检查是否存在明显的绝对性表达。

    absolute_patterns = [
        "一定必须",
        "必然必须",
        "当然必须",
        "无条件必须",
        "肯定必须",
        "一定应当",
        "必然应当",
    ]

    for pattern in absolute_patterns:

        if pattern in answer:
            return False

    # 至少应当出现一个条件性表达。

    conditional_patterns = [
        "如果",
        "若",
        "在",
        "条件成立",
        "符合条件",
        "视情况",
        "视具体情况",
        "取决于",
        "仍需结合",
        "还需结合",
        "尚需确认",
        "仍需确认",
        "仍待确认",
        "需要进一步确认",
        "需要进一步核实",
        "还需进一步判断",
        "不能直接认定",
        "无法直接认定",
        "尚不能认定",
        "尚不能确认",
        "无法作出最终判断",
        "不能作出最终判断",
    ]

    for pattern in conditional_patterns:

        if pattern in answer:
            return True

    return False


def validate_unknown_conditions(
    answer: str,
    decision: Dict[str, Any],
) -> bool:
    """
    V6.0-16 UNKNOWN 语义验证。

    V6.0-13 的问题是：
    UNKNOWN 验证只接受少量固定关键词。
    Ollama 即使正确表达“该事实目前无法确认”，
    只要没有命中固定词表，也会被误判为 UNKNOWN FAIL。

    V6.0-15 改为“语义标记 + 结构化 UNKNOWN 内容”双重验证：

    1. 接受多种表达“未知/待核实/材料不足/无法作出最终判断”的句式。
    2. 同时允许 UNKNOWN 条件本身出现在回答中。
    3. 对明显的确定性表达保持保守，不因为出现“条件”二字就通过。

    V6.0-16 修复：

    1. 不再因为命中任意一个 UNKNOWN 语义关键词就直接返回 True。
    2. 当 Engine 存在多个 UNKNOWN 条件时，逐项验证 UNKNOWN 条件是否被回答保留。
    3. 明确支持：
           “UNKNOWN”
           “未知”
           “尚未确认”
           “尚不明确”
           “无法确认”
           “待进一步确认”
           等表达。
    4. 如果回答明确列出了 Engine 的 UNKNOWN 条件，
       即使没有使用“无法确认”等固定句式，也允许通过。
    5. 中文条件没有天然空格，因此不再依赖 split()
       来判断 UNKNOWN 条件是否出现。
    6. 对较长条件使用“关键片段”匹配，而不是要求完整字符串完全一致。
    7. 至少要求大部分 UNKNOWN 条件被正确表达，
       防止模型只写一个 UNKNOWN 条件就通过。
    8. 如果回答明确声明“其他条件状态为 UNKNOWN”，
       并完整列出 Engine 的 UNKNOWN 条件，应当通过。
    """

    unknown = ensure_list(
        decision.get(
            "unknown_conditions",
            [],
        )
    )

    # --------------------------------------------------------
    # Engine 没有 UNKNOWN 条件
    # --------------------------------------------------------
    #
    # 如果 Decision Engine 没有任何 UNKNOWN 条件，
    # 那么回答中自然不需要表达 UNKNOWN。
    # --------------------------------------------------------

    if not unknown:
        return True

    answer_text = normalize_text(answer)

    if not answer_text:
        return False

    # ========================================================
    # 第一层：广义 UNKNOWN / 待确认语义标记
    # ========================================================
    #
    # 不再依赖单一固定短语。
    # 这些表达均可以合理表示“当前材料不足以确认”。
    #
    # V6.0-16 新增：
    #
    #   UNKNOWN
    #   未知
    #   未确定
    #   状态为 UNKNOWN
    #   条件为 UNKNOWN
    #   尚不确定
    #
    # 这是因为 Ollama 可能直接复制 Engine 的结构化状态，
    # 而不是改写成“无法确认”。
    # --------------------------------------------------------

    unresolved_patterns = [
        "UNKNOWN",
        "unknown",
        "未知",
        "未确定",
        "尚未确定",
        "未能确定",
        "未确认",
        "尚未提供",
        "未提供",
        "没有提供",
        "未说明",
        "尚未说明",
        "没有说明",
        "未明确",
        "尚未明确",
        "尚未确认",
        "尚不明确",
        "尚不确定",
        "无法确认",
        "不能确认",
        "难以确认",
        "不足以确认",
        "无法判断",
        "不能判断",
        "难以判断",
        "无法作出判断",
        "不能作出判断",
        "无法作出最终判断",
        "不能作出最终判断",
        "无法作出最终认定",
        "不能作出最终认定",
        "无法直接认定",
        "不能直接认定",
        "尚不能认定",
        "尚不能确认",
        "尚不能判断",
        "目前不能确认",
        "目前无法确认",
        "目前无法判断",
        "目前无法认定",
        "当前不能确认",
        "当前无法确认",
        "当前无法判断",
        "当前无法认定",
        "现阶段无法",
        "现阶段不能",
        "现有材料不足",
        "材料不足",
        "事实不足",
        "证据不足以确认",
        "信息不足以确认",
        "目前材料不足以",
        "现有信息不足以",
        "需要进一步确认",
        "需要进一步核实",
        "还需要进一步确认",
        "还需进一步确认",
        "还需要核实",
        "仍需确认",
        "仍需进一步确认",
        "仍待确认",
        "待进一步确认",
        "待核实",
        "有待核实",
        "尚待核实",
        "尚需确认",
        "尚需进一步确认",
        "需要补充事实",
        "需要补充材料",
        "需要补充信息",
        "需补充事实",
        "需补充材料",
        "需补充信息",
        "最终结论仍取决于",
        "最终判断仍取决于",
        "还需结合",
        "仍需结合",
        "需要结合其他",
        "是否存在其他法定情形尚不能",
        "是否存在法定例外目前无法",
    ]

    has_unresolved_marker = any(
        pattern in answer_text
        for pattern in unresolved_patterns
    )

    # ========================================================
    # 第二层：提取 Engine 的 UNKNOWN 条件
    # ========================================================
    #
    # V6.0-16 不再使用：
    #
    #     condition_core.split()
    #
    # 因为中文条件通常没有空格。
    #
    # 例如：
    #
    #     劳动者提出或者同意续订、订立劳动合同
    #
    # 整个字符串很可能被 split() 当成一个 token。
    #
    # 因此这里直接对中文连续字符串进行关键片段匹配。
    # ========================================================

    normalized_conditions: List[str] = []

    for item in unknown:

        if isinstance(item, dict):

            condition = normalize_text(
                item.get(
                    "condition",
                    item.get(
                        "description",
                        "",
                    ),
                )
            )

        else:

            condition = normalize_text(item)

        if condition:
            normalized_conditions.append(condition)

    # --------------------------------------------------------
    # 如果 Engine 有 UNKNOWN，但没有成功提取条件文本，
    # 则退回到 UNKNOWN 语义标记验证。
    # --------------------------------------------------------

    if not normalized_conditions:

        return has_unresolved_marker

    # ========================================================
    # 第三层：为每一个 UNKNOWN 条件提取关键片段
    # ========================================================
    #
    # 目的不是要求模型逐字复制条件，
    # 而是判断该 UNKNOWN 条件是否被实际表达。
    #
    # 例如 Engine：
    #
    #     劳动者提出或者同意续订、订立劳动合同
    #
    # 回答：
    #
    #     劳动者是否提出或者同意续订、订立劳动合同，
    #     目前尚未确认。
    #
    # 应当判定为该 UNKNOWN 条件已经正确表达。
    #
    # 同时允许模型略微改写：
    #
    #     是否由劳动者提出或者同意续订劳动合同，
    #     目前无法确认。
    #
    # 也应当判定为正确。
    # ========================================================

    def build_condition_fragments(
        condition: str,
    ) -> List[str]:
        """
        从一个 UNKNOWN 条件中提取若干具有辨识度的关键片段。
        """

        condition = normalize_text(condition)

        if not condition:
            return []

        # ----------------------------------------------------
        # 去除标点。
        # ----------------------------------------------------

        condition_core = re.sub(
            r"[，。；：、（）()【】\[\]“”‘’：;,.!?！？]",
            "",
            condition,
        )

        condition_core = condition_core.strip()

        if not condition_core:
            return []

        fragments: List[str] = []

        # ----------------------------------------------------
        # 完整条件本身是最强匹配项。
        # ----------------------------------------------------

        if len(condition_core) >= 4:
            fragments.append(condition_core)

        # ----------------------------------------------------
        # 中文条件通常较长。
        #
        # 提取前部、中部、后部关键片段。
        # ----------------------------------------------------

        if len(condition_core) >= 8:
            fragments.append(
                condition_core[:8]
            )

        if len(condition_core) >= 12:
            fragments.append(
                condition_core[:12]
            )

        if len(condition_core) >= 16:
            fragments.append(
                condition_core[:16]
            )

        # ----------------------------------------------------
        # 针对劳动合同法律条件的常见核心短语。
        # ----------------------------------------------------

        legal_keywords = [
            "连续订立二次固定期限劳动合同",
            "连续签订二次固定期限劳动合同",
            "连续订立两次固定期限劳动合同",
            "连续签订两次固定期限劳动合同",
            "存在后续订立的劳动合同",
            "续订劳动合同",
            "提出或者同意续订",
            "提出或者同意订立",
            "提出订立固定期限劳动合同",
            "第三十九条规定的情形",
            "第四十条第一项规定的情形",
            "第四十条第二项规定的情形",
        ]

        for keyword in legal_keywords:

            if keyword in condition_core:
                fragments.append(keyword)

        # ----------------------------------------------------
        # 去重，同时保持原顺序。
        # ----------------------------------------------------

        unique_fragments: List[str] = []

        for fragment in fragments:

            fragment = fragment.strip()

            if not fragment:
                continue

            if fragment not in unique_fragments:
                unique_fragments.append(fragment)

        return unique_fragments

    # ========================================================
    # 第四层：逐项验证 UNKNOWN 条件
    # ========================================================
    #
    # V6.0-16 核心修复：
    #
    # 不再：
    #
    #     任意一个条件出现
    #         +
    #     任意一个 UNKNOWN 关键词出现
    #         =
    #     PASS
    #
    # 而是：
    #
    #     Engine UNKNOWN 条件
    #         ↓
    #     逐项检查
    #         ↓
    #     统计已经被回答表达的 UNKNOWN 条件
    #
    # 这样才能真正验证 Engine → Ollama 的 UNKNOWN 保真度。
    # ========================================================

    matched_conditions: List[str] = []

    for condition in normalized_conditions:

        fragments = build_condition_fragments(
            condition
        )

        if not fragments:
            continue

        # ----------------------------------------------------
        # 完整条件命中。
        # ----------------------------------------------------

        condition_mentioned = any(
            fragment in answer_text
            for fragment in fragments
            if len(fragment) >= 8
        )

        if condition_mentioned:

            matched_conditions.append(
                condition
            )

            continue

        # ----------------------------------------------------
        # 如果没有完整关键片段命中，
        # 再检查短关键词组合。
        # ----------------------------------------------------

        condition_core = re.sub(
            r"[，。；：、（）()【】\[\]“”‘’：;,.!?！？]",
            "",
            condition,
        )

        keyword_groups: List[List[str]] = []

        if "劳动者提出或者同意续订、订立劳动合同" in condition:
            keyword_groups.append(
                [
                    "劳动者",
                    "提出",
                    "同意",
                    "续订",
                ]
            )

            keyword_groups.append(
                [
                    "劳动者",
                    "提出",
                    "同意",
                    "订立",
                    "劳动合同",
                ]
            )

        elif "第三十九条" in condition:
            keyword_groups.append(
                [
                    "第三十九条",
                    "情形",
                ]
            )

        elif "第四十条第一项" in condition:
            keyword_groups.append(
                [
                    "第四十条第一项",
                    "情形",
                ]
            )

        elif "第四十条第二项" in condition:
            keyword_groups.append(
                [
                    "第四十条第二项",
                    "情形",
                ]
            )

        elif "提出订立固定期限劳动合同" in condition:
            keyword_groups.append(
                [
                    "提出",
                    "订立",
                    "固定期限劳动合同",
                ]
            )

        else:
            keyword_groups.append(
                [
                    condition_core[:6]
                ]
            )

        group_matched = False

        for group in keyword_groups:

            if all(
                keyword in answer_text
                for keyword in group
            ):
                group_matched = True
                break

        if group_matched:

            matched_conditions.append(
                condition
            )

    # ========================================================
    # 第五层：计算 UNKNOWN 条件覆盖率
    # ========================================================
    #
    # 正常情况下，Engine 有几个 UNKNOWN，
    # Ollama 就应该表达几个 UNKNOWN。
    #
    # 对本项目当前法律 RAG：
    #
    #     UNKNOWN = 4
    #
    # 正确回答：
    #
    #     4 / 4
    #
    # 应当 PASS。
    #
    # 如果只回答：
    #
    #     1 / 4
    #
    # 则不能认为 UNKNOWN 已经完整保真。
    # ========================================================

    matched_count = len(
        matched_conditions
    )

    unknown_count = len(
        normalized_conditions
    )

    # --------------------------------------------------------
    # 所有 UNKNOWN 条件都被明确表达。
    # --------------------------------------------------------

    if matched_count == unknown_count:

        # ----------------------------------------------------
        # 如果回答明确出现 UNKNOWN / 未确认语义，
        # 直接通过。
        #
        # 例如：
        #
        #     其他条件状态为 UNKNOWN：
        #     - 条件 A
        #     - 条件 B
        #     - 条件 C
        #     - 条件 D
        # ----------------------------------------------------

        if has_unresolved_marker:
            return True

        # ----------------------------------------------------
        # 即使没有出现固定 UNKNOWN 关键词，
        # 只要每一个 Engine UNKNOWN 条件都被保留，
        # 并且回答使用明显的未决结构，也允许通过。
        # ----------------------------------------------------

        unresolved_structure_patterns = [
            "是否存在",
            "是否具有",
            "是否符合",
            "是否属于",
            "是否满足",
            "是否发生",
            "是否具备",
            "取决于",
            "有待",
            "视",
            "尚需",
            "仍需",
            "待",
        ]

        if any(
            pattern in answer_text
            for pattern in unresolved_structure_patterns
        ):
            return True

        # ----------------------------------------------------
        # 如果条件本身全部被保留，但没有任何 UNKNOWN
        # 语义，也不能贸然认定为 UNKNOWN。
        # ----------------------------------------------------

        return False

    # ========================================================
    # 第六层：允许少量自然语言改写，但保持严格
    # ========================================================
    #
    # 某些回答可能没有逐项完整复制 Engine 条件，
    # 而是将多个 UNKNOWN 条件合并描述。
    #
    # 如果回答明确声明：
    #
    #     其他条件状态为 UNKNOWN
    #
    # 且至少有一半 UNKNOWN 条件被明确列出，
    # 可以认为 UNKNOWN 语义基本被保留。
    #
    # 但不能只因为出现一个“尚未确认”就通过。
    # ========================================================

    if has_unresolved_marker:

        # ----------------------------------------------------
        # 少于 2 个 UNKNOWN 条件时，
        # 必须至少匹配其中一个。
        # ----------------------------------------------------

        if unknown_count == 1:

            return matched_count == 1

        # ----------------------------------------------------
        # 多个 UNKNOWN 条件：
        # 至少覆盖一半。
        # ----------------------------------------------------

        minimum_required = (
            unknown_count + 1
        ) // 2

        if matched_count >= minimum_required:

            return True

    # ========================================================
    # 第七层：结构化 UNKNOWN 表达
    # ========================================================
    #
    # 即使没有出现：
    #
    #     尚未确认
    #     无法确认
    #     UNKNOWN
    #
    # 如果回答明确把条件写成：
    #
    #     是否……
    #     取决于……
    #     有待……
    #
    # 并且覆盖足够多的 Engine UNKNOWN 条件，
    # 仍然可以通过。
    # ========================================================

    unresolved_structure_patterns = [
        "是否存在",
        "是否具有",
        "是否符合",
        "是否属于",
        "是否满足",
        "是否发生",
        "是否具备",
        "取决于",
        "有待",
        "视",
        "尚需",
        "仍需",
        "待",
    ]

    has_unresolved_structure = any(
        pattern in answer_text
        for pattern in unresolved_structure_patterns
    )

    if has_unresolved_structure:

        if unknown_count == 1:
            return matched_count == 1

        minimum_required = (
            unknown_count + 1
        ) // 2

        if matched_count >= minimum_required:
            return True

    # ========================================================
    # 最终：UNKNOWN 验证失败
    # ========================================================
    #
    # 说明：
    #
    # Engine 明确存在 UNKNOWN 条件，
    # 但 Ollama 没有充分保留这些 UNKNOWN 条件的语义。
    #
    # 这种情况下必须 FAIL，
    # 防止 Ollama 把“不确定”错误表达成确定结论。
    # ========================================================

    return False


def _chinese_article_to_int(text: str):
    """将中文法条数字转换为整数。"""

    text = normalize_text(text)
    if not text:
        return None

    if text.isdigit():
        return int(text)

    digits = {
        "零": 0,
        "一": 1,
        "二": 2,
        "两": 2,
        "三": 3,
        "四": 4,
        "五": 5,
        "六": 6,
        "七": 7,
        "八": 8,
        "九": 9,
    }

    if text == "十":
        return 10

    if "十" in text:
        parts = text.split("十")
        left = parts[0]
        right = parts[1] if len(parts) > 1 else ""

        tens = 1 if not left else digits.get(left)
        ones = 0 if not right else digits.get(right)

        if tens is None or ones is None:
            return None

        return tens * 10 + ones

    if all(char in digits for char in text):
        value = 0
        for char in text:
            value = value * 10 + digits[char]
        return value

    return None


def _normalize_law_name(law_name: str) -> str:
    """
    V6.0-16 法律名称归一化。

    目的：
        将 Ollama 常见的简称映射到 Retriever / Structured Rules
        中的完整法律名称，避免仅因为法律名称表达不同而误判
        LEGAL_BASIS。

    例如：
        《中华人民共和国劳动合同法》
        《劳动合同法》
        劳动合同法

    统一为：
        中华人民共和国劳动合同法

    注意：这里只做名称归一化，不新增任何法律或法条。
    """

    text = normalize_text(law_name)
    text = text.replace("《", "").replace("》", "")
    text = text.replace(" ", "").replace("　", "")

    aliases = {
        "劳动合同法": "中华人民共和国劳动合同法",
        "中华人民共和国劳动合同法": "中华人民共和国劳动合同法",
        "劳动合同法实施条例": "中华人民共和国劳动合同法实施条例",
        "中华人民共和国劳动合同法实施条例": "中华人民共和国劳动合同法实施条例",
        "劳动法": "中华人民共和国劳动法",
        "中华人民共和国劳动法": "中华人民共和国劳动法",
    }

    return aliases.get(text, text)


def _normalize_article_number(article_number: str) -> str:
    """统一“第十四条 / 第14条”等法条编号。"""

    text = normalize_text(article_number)
    text = text.replace(" ", "").replace("　", "")

    match = re.search(
        r"第([一二三四五六七八九十百千万零两\d]+)条",
        text,
    )

    if match:
        value = _chinese_article_to_int(match.group(1))
        if value is not None:
            return f"第{value}条"

    match = re.search(
        r"([一二三四五六七八九十百千万零两\d]+)条",
        text,
    )

    if match:
        value = _chinese_article_to_int(match.group(1))
        if value is not None:
            return f"第{value}条"

    return text


def _normalize_citation(citation: str) -> str:
    """V6.0-16：统一法律名称及法条编号。"""

    text = normalize_text(citation)
    text = text.replace(" ", "").replace("　", "")

    match = re.match(
        r"《([^》]+)》第([一二三四五六七八九十百千万零两\d]+)条$",
        text,
    )

    if not match:
        match = re.match(
            r"([^《》]+)第([一二三四五六七八九十百千万零两\d]+)条$",
            text,
        )

    if match:
        law_name = _normalize_law_name(match.group(1))
        article_value = _chinese_article_to_int(match.group(2))
        if article_value is not None:
            return f"《{law_name}》第{article_value}条"

    return text


def _citation_key(law_name: str, article_number: str):
    """生成法律依据的结构化比较键。"""

    normalized_law = _normalize_law_name(law_name)
    normalized_article = _normalize_article_number(article_number)
    return normalized_law, normalized_article


def validate_legal_basis(
    answer: str,
    rules: List[Dict[str, Any]],
) -> bool:
    """
    V6.0-27 法律依据验证。

    核心原则：

        Ollama 明确写出的《法律名称》第X条，
        必须能够在当前 Structured Rules 中找到对应的法律 + 法条。

    V6.0-22 同时修复：

        1. Rules 可能是对象而不是 dict；先统一 normalize_rule。
        2. 法律简称与完整法律名称统一归一化。
        3. 第14条与第十四条统一归一化。
        4. 不允许引用当前 Rules 之外的新法条。

    V6.0-27 修复：

        5. Structured Rules 存在时，
           【法律依据】章节不得为空。

        6. 【法律依据】章节不得仅包含：
               无
               暂无
               没有
               无明确法律依据
               当前没有可用于最终回答的结构化法律依据
           等无实际法律依据内容的占位表达。

        7. 当 Structured Rules 存在时，
           【法律依据】章节必须至少包含一个
           当前 Structured Rules 允许的法律法条引用。

        8. 仍然禁止引用当前 Structured Rules
           体系之外的新法律、新法条。

    重要边界：

        - Validator 只负责验证 Ollama 是否忠实引用
          Structured Rules。
        - Validator 不负责新增法律知识。
        - Validator 不负责重新进行法律条件判断。
        - Rules 为空时，保持原有安全策略：
          没有明确法条引用可以通过；
          一旦出现明确法条引用，则必须验证其来源。
    """

    if not answer:
        return False

    # ============================================================
    # 1. Structured Rules 统一归一化
    # ============================================================

    normalized_rules = build_rules_from_articles(
        ensure_list(rules)
    )

    # ============================================================
    # 2. Rules 为空
    # ============================================================
    #
    # 没有结构化 Rules 时：
    #
    #     - 如果答案没有明确引用法条，可以通过；
    #     - 如果答案主动引用了《某某法律》第X条，
    #       则无法证明该法条来自当前 Structured Rules，
    #       必须失败。
    #
    # 这里保持原有 V6.0-27 的安全原则，
    # 不让 Validator 自己制造法律依据。
    #

    citation_pattern = (
        r"《\s*([^》]+?)\s*》\s*第\s*"
        r"([一二三四五六七八九十百千万零两\d]+)\s*条"
    )

    if not normalized_rules:

        citations = re.findall(
            citation_pattern,
            answer,
        )

        if citations:
            return False

        return True

    # ============================================================
    # 3. 提取【法律依据】章节
    # ============================================================
    #
    # 当 Structured Rules 存在时，
    # 法律依据章节必须真正提供法律依据。
    #
    # 不能只因为整个 answer 中没有非法法条引用，
    # 就直接认为法律依据验证通过。
    #
    # V6.0-27 原来的问题就在这里：
    #
    #     citations = re.findall(...)
    #
    #     if not citations:
    #         return True
    #
    # 这会导致：
    #
    #     【法律依据】
    #
    #     【法律分析】
    #
    # 这样的空法律依据直接通过 Validator。
    #

    basis_marker = "【法律依据】"
    analysis_marker = "【法律分析】"

    if basis_marker not in answer:
        return False

    basis_start = answer.find(basis_marker)

    if basis_start < 0:
        return False

    basis_content_start = (
        basis_start + len(basis_marker)
    )

    analysis_start = answer.find(
        analysis_marker,
        basis_content_start,
    )

    if analysis_start >= 0:
        legal_basis_text = answer[
            basis_content_start:analysis_start
        ].strip()
    else:
        legal_basis_text = answer[
            basis_content_start:
        ].strip()

    # ============================================================
    # 4. 法律依据章节不能为空
    # ============================================================

    if not legal_basis_text:
        return False

    # ============================================================
    # 5. 过滤无实际法律依据意义的占位文本
    # ============================================================
    #
    # 以下表达虽然 technically 有文字，
    # 但并没有提供真正的法律依据。
    #
    # 因此不能因为它们不为空就认为法律依据有效。
    #

    placeholder_patterns = [
        "无",
        "暂无",
        "没有",
        "无明确法律依据",
        "暂无明确法律依据",
        "没有明确法律依据",
        "当前没有可用于最终回答的结构化法律依据",
        "当前没有可用的结构化法律依据",
        "没有可用的结构化法律依据",
        "当前没有结构化法律依据",
        "没有结构化法律依据",
        "暂无结构化法律依据",
        "无结构化法律依据",
    ]

    normalized_basis_text = normalize_text(
        legal_basis_text
    ).strip()

    if normalized_basis_text in placeholder_patterns:
        return False

    # ============================================================
    # 6. 建立允许引用的法条集合
    # ============================================================
    #
    # Structured Rules 共有若干法律规则。
    #
    # 允许的法律依据包括：
    #
    #     A. Rule 自身的主法条；
    #
    #     B. Rule 中已经明确存在的 references；
    #
    #     C. conditions；
    #
    #     D. exclusion_conditions；
    #
    #     E. exceptions；
    #
    #     F. legal_obligations；
    #
    #     G. legal_consequences；
    #
    # 这样可以避免：
    #
    #     第十四条 Rule
    #         ↓
    #     第三十九条 / 第四十条
    #
    # 这些已经由 Structured Rule 明确引用的法条，
    # 被错误判断成 Ollama 新增的法律依据。
    #

    allowed_keys = set()

    # --------------------------------------------------------
    # V6.0-27：区分“法律依据法条”和“结构化规则中的交叉引用”
    # --------------------------------------------------------
    #
    # Structured Rules 共有 5 条法律规则。
    #
    # 但是第十四条的 exclusion_conditions 本身合法地引用了：
    #
    #     《劳动合同法》第三十九条
    #     《劳动合同法》第四十条第一项
    #     《劳动合同法》第四十条第二项
    #
    # 因此不能只把 Rule 自身 article_number
    # 作为 allowed_keys。
    #
    # 正确原则：
    #
    #     1. 法律依据部分不能引用当前规则体系之外的新法条；
    #     2. Structured Rule 自己明确引用的法条，
    #        可以在法律分析中出现；
    #     3. 不因此把新的法律知识添加进 Retriever。
    #
    # 所以这里同时收集：
    #
    #     A. Rule 自身的主法条；
    #     B. Rule 中已经存在的 references / conditions
    #        / exclusion_conditions / exceptions
    #        / legal_obligations / legal_consequences
    #        等交叉引用。
    #

    citation_pattern_for_rule = (
        r"《\s*([^》]+?)\s*》\s*第\s*"
        r"([一二三四五六七八九十百千万零两\d]+)\s*条"
    )

    rule_citation_fields = [
        "rule_summary",
        "content",
        "text",
        "conditions",
        "exclusion_conditions",
        "exceptions",
        "legal_obligations",
        "legal_consequences",
        "references",
    ]

    for rule in normalized_rules:

        law_name = normalize_text(
            get_rule_value(
                rule,
                "law_name",
                "law",
                "title",
            ) or ""
        )

        article_number = normalize_text(
            get_rule_value(
                rule,
                "article_number",
                "article",
                "article_no",
            ) or ""
        )

        # --------------------------------------------------------
        # 6.1 Rule 自身主法条
        # --------------------------------------------------------

        if law_name and article_number:

            allowed_keys.add(
                _citation_key(
                    law_name,
                    article_number,
                )
            )

        # --------------------------------------------------------
        # 6.2 Rule 中明确存在的交叉引用
        # --------------------------------------------------------

        for field_name in rule_citation_fields:

            value = get_rule_value(
                rule,
                field_name,
            )

            for item in ensure_list(value):

                if isinstance(item, str):

                    source_text = item

                elif isinstance(item, dict):

                    source_text = " ".join(
                        str(v)
                        for v in item.values()
                        if v is not None
                    )

                else:

                    source_text = (
                        str(item)
                        if item is not None
                        else ""
                    )

                for ref_law, ref_article in re.findall(
                    citation_pattern_for_rule,
                    source_text,
                ):

                    ref_value = _chinese_article_to_int(
                        ref_article
                    )

                    if ref_value is None:
                        continue

                    ref_law_name = _normalize_law_name(
                        ref_law
                    )

                    if ref_law_name:

                        allowed_keys.add(
                            (
                                ref_law_name,
                                f"第{ref_value}条",
                            )
                        )

    # ============================================================
    # 7. 提取整个答案中的法条引用
    # ============================================================

    citations = re.findall(
        citation_pattern,
        answer,
    )

    # ============================================================
    # 8. Structured Rules 存在时，
    #    【法律依据】必须至少存在一个合法法条引用
    # ============================================================
    #
    # 这是本次 V6.0-27 修复的核心。
    #
    # 不能再使用：
    #
    #     if not citations:
    #         return True
    #
    # 因为这会让：
    #
    #     【法律依据】
    #
    #     【法律分析】
    #
    # 直接通过。
    #
    # 必须确认法律依据章节本身存在至少一个
    # 当前 Structured Rules 允许的法律依据。
    #

    basis_citations = re.findall(
        citation_pattern,
        legal_basis_text,
    )

    if not basis_citations:
        return False

    # ============================================================
    # 9. 验证【法律依据】章节中的每一个法条
    # ============================================================

    valid_basis_citation_found = False

    for law_name, article_raw in basis_citations:

        article_value = _chinese_article_to_int(
            article_raw
        )

        if article_value is None:
            return False

        normalized_law_name = _normalize_law_name(
            law_name
        )

        if not normalized_law_name:
            return False

        key = (
            normalized_law_name,
            f"第{article_value}条",
        )

        if key not in allowed_keys:
            return False

        valid_basis_citation_found = True

    # ============================================================
    # 10. 至少存在一个合法的 Structured Rule 法条
    # ============================================================

    if not valid_basis_citation_found:
        return False

    # ============================================================
    # 11. 验证整个答案中的所有明确法条引用
    # ============================================================
    #
    # 法律依据章节通过后，
    # 仍然要继续验证整个答案。
    #
    # 这样可以防止：
    #
    #     【法律依据】
    #     《劳动合同法》第十四条
    #
    #     【法律分析】
    #     《某不存在的法律》第999条……
    #
    # 这种情况绕过 Validator。
    #
    # 因此整个 answer 中出现的每一个明确法条，
    # 都必须属于 Structured Rules 允许范围。
    #

    for law_name, article_raw in citations:

        article_value = _chinese_article_to_int(
            article_raw
        )

        if article_value is None:
            return False

        normalized_law_name = _normalize_law_name(
            law_name
        )

        if not normalized_law_name:
            return False

        key = (
            normalized_law_name,
            f"第{article_value}条",
        )

        if key in allowed_keys:
            continue

        # --------------------------------------------------------
        # 出现当前 Structured Rules 之外的新法条
        # --------------------------------------------------------

        return False

    # ============================================================
    # 12. 全部验证通过
    # ============================================================

    return True


def validate_decision_consistency(
    answer: str,
    decision: Dict[str, Any],
) -> bool:

    engine_status = normalize_text(
        decision.get(
            "engine_decision",
            "",
        )
    ).upper()

    if engine_status == DECISION_DEFINITE:

        forbidden = [
            "尚不能确认",
            "无法确认是否满足",
            "条件尚未确认",
        ]

        # DEFINITE 不应被 Ollama 改写成完全未知。
        #
        # 但这里只做非常保守的检查，
        # 避免误伤正常的注意事项。

        if (
            answer.count("尚不能确认") > 2
            or
            answer.count("无法确认是否满足") > 2
        ):
            return False

    if engine_status == DECISION_NOT_ESTABLISHED:

        # ========================================================
        # NOT_ESTABLISHED 语义边界
        # ========================================================
        #
        # NOT_ESTABLISHED 的含义是：
        #
        #     当前事实下，法律要件尚未被完整确认，
        #     因此不能作出已经满足全部条件的确定性结论。
        #
        # 特别注意：
        #
        #     NOT_ESTABLISHED
        #
        # 不能被 Ollama 改写成：
        #
        #     “无需签订”
        #     “不需要签订”
        #     “不必签订”
        #     “没有义务签订”
        #
        # 因为这些表达是在作出“法律义务不存在”的
        # 确定性结论，而不是表达“当前尚不能确认”。
        #
        # 本检查只针对最终回答的结论语义，
        # 不修改 Legal Decision Engine 本身。
        # ========================================================

        forbidden = [
            # ----------------------------------------------------
            # 明确表示无需履行义务
            # ----------------------------------------------------
            "无需签订",
            "无需订立",
            "不需要签订",
            "不需要订立",
            "不必签订",
            "不必订立",
            "没有义务签订",
            "没有义务订立",

            # ----------------------------------------------------
            # 明确表示不存在签订义务
            # ----------------------------------------------------
            "不存在签订义务",
            "不存在订立义务",
            "不存在签订无固定期限劳动合同的义务",
            "不存在订立无固定期限劳动合同的义务",

            # ----------------------------------------------------
            # 明确表示已经排除法律义务
            # ----------------------------------------------------
            "排除了签订无固定期限劳动合同的法律义务",
            "排除了订立无固定期限劳动合同的法律义务",
            "排除签订无固定期限劳动合同的法律义务",
            "排除订立无固定期限劳动合同的法律义务",
            "已经排除签订无固定期限劳动合同的义务",
            "已经排除订立无固定期限劳动合同的义务",

            # ----------------------------------------------------
            # 确定性“因此/所以/故”结论
            # ----------------------------------------------------
            "因此无需签订",
            "因此无需订立",
            "因此不需要签订",
            "因此不需要订立",
            "因此不必签订",
            "因此不必订立",
            "故无需签订",
            "故无需订立",
            "故不需要签订",
            "故不需要订立",
            "故不必签订",
            "故不必订立",

            # ----------------------------------------------------
            # 原有确定性表达
            # ----------------------------------------------------
            "已经确定满足全部条件",
            "已经完全满足全部条件",
            "当然必须签订",
            "一定必须签订",
        ]

        for pattern in forbidden:

            if pattern in answer:
                return False

    return True


def validate_engine_condition_completeness(
    decision: Dict[str, Any],
) -> bool:
    """
    V6.0-27：验证 Decision Engine V6.0-14 的 ConditionResult 完整性。

    正常结构固定为：

        REQUIRED   = 4
        EXCLUSION  = 3
        EXCEPTION  = 1
        TOTAL      = 8

    CONDITIONAL 情况下如果不是完整 8 条，必须进入安全 Fallback，
    RAG 不得自行补条件。
    """

    if not isinstance(decision, dict):
        return False

    engine_decision = normalize_text(
        decision.get("engine_decision", "")
    ).upper()

    count = decision.get(
        "engine_condition_results_count",
        None,
    )

    if not isinstance(count, int):
        raw_decision = decision.get("raw_decision")
        count = len(
            ensure_list(
                get_field(
                    raw_decision,
                    "condition_results",
                    [],
                )
            )
        )

    if engine_decision == DECISION_CONDITIONAL:
        return count == 8

    return count == 0 or count == 8


def validate_condition_categories(
    decision: Dict[str, Any],
) -> bool:
    """
    V6.0-27：严格验证 Engine V6.0-14 的三类 ConditionResult。

        REQUIRED   = 4
        EXCLUSION  = 3
        EXCEPTION  = 1
        TOTAL      = 8

    分类直接来自 ConditionResult.condition_type / type，
    不再从 Rules 猜测类别。
    """

    if not isinstance(decision, dict):
        return False

    results = ensure_list(
        decision.get("condition_results", [])
    )

    if len(results) != 8:
        return False

    counts = {
        "REQUIRED": 0,
        "EXCLUSION": 0,
        "EXCEPTION": 0,
    }

    names = set()

    for item in results:
        if not isinstance(item, dict):
            return False

        condition = normalize_text(
            item.get("condition", "")
        )
        status = normalize_text(
            item.get("status", "")
        ).upper()
        category = normalize_text(
            item.get(
                "condition_type",
                item.get(
                    "category",
                    item.get("type", ""),
                ),
            )
        ).upper()

        if not condition or not category:
            return False

        if category not in counts:
            return False

        if status not in {
            "SATISFIED",
            "NOT_SATISFIED",
            "UNKNOWN",
            "UNSATISFIED",
        }:
            return False

        if condition in names:
            return False

        names.add(condition)
        counts[category] += 1

    return counts == {
        "REQUIRED": 4,
        "EXCLUSION": 3,
        "EXCEPTION": 1,
    }


def final_validation(
    answer: str,
    question: str,
    decision: Dict[str, Any],
) -> str:
    """
    RAG V6.0-27 Final Validation。

    最终验证层负责：

        Ollama Answer
              ↓
        Structural Validation
              ↓
        Fact Validation
              ↓
        Condition Validation
              ↓
        Legal Basis Validation
              ↓
        PASS / Deterministic Fallback

    核心原则：

    1. 不修改 Legal Decision Engine 输出。
    2. 不由 Validation 层重新进行法律推理。
    3. Ollama 失败或验证失败时，只允许使用确定性的 Python Fallback。
    4. Fallback 仍然必须经过同一套安全验证。
    5. 如果 Engine 的 ConditionResult 不完整，绝不由 RAG 自行补条件。
    6. 最终绝不返回未经验证的 Ollama 原始答案。
    """

    print()
    print("=" * 70)
    print("Step 5 / Final Validation")
    print("=" * 70)

    from src.legal_fallback import build_fallback_answer

    question = normalize_text(question)
    answer = clean_answer(answer)

    if not isinstance(decision, dict):
        print()
        print("⚠️ Decision 不是有效 Dict，使用空安全回答。")
        return build_fallback_answer(
            question=question,
            decision={},
        )

    def run_checks(
        text: str,
        question: str,
        decision: Dict[str, Any],
    ) -> List[str]:

        failures: List[str] = []

        if not text:
            failures.append("EMPTY")
            return failures

        # ============================================================
        # Final Validation 1：Engine Condition Completeness
        # ============================================================

        if not validate_engine_condition_completeness(
            decision
        ):
            failures.append(
                "ENGINE_CONDITION_COMPLETENESS"
            )

        # ============================================================
        # Final Validation 2：Condition Category
        # ============================================================

        if not validate_condition_categories(
            decision
        ):
            failures.append(
                "CONDITION_CATEGORY"
            )

        # ============================================================
        # Final Validation 3：答案结构
        # ============================================================

        if not validate_answer_structure(
            text
        ):
            failures.append(
                "ANSWER_STRUCTURE"
            )

        # ============================================================
        # Final Validation 4：用户事实保真
        # ============================================================

        if not validate_user_facts(
            text,
            decision,
        ):
            failures.append(
                "USER_FACT_VALIDATION"
            )

        # ============================================================
        # Final Validation 5：三次合同事实
        # ============================================================

        if not validate_three_contract_fact(
            text,
            decision,
        ):
            failures.append(
                "THREE_CONTRACT_FACT"
            )

        # ============================================================
        # Final Validation 6：Fact → Condition Mapping
        # ============================================================

        if not validate_fact_condition_mapping(
            text,
            question,
            decision,
        ):
            failures.append(
                "FACT_CONDITION_MAPPING"
            )

        # ============================================================
        # Final Validation 7：禁止制造 UNKNOWN
        # ============================================================

        if not validate_no_manufactured_unknown(
            text,
            decision,
        ):
            failures.append(
                "MANUFACTURED_UNKNOWN"
            )

        # ============================================================
        # Final Validation 8：禁止发明法律条件
        # ============================================================

        if not validate_legal_condition_invention(
            text,
            decision,
        ):
            failures.append(
                "LEGAL_CONDITION_INVENTION"
            )

        # ============================================================
        # Final Validation 9：Conditional 状态
        # ============================================================

        if not validate_conditional_state(
            text,
            decision,
        ):
            failures.append(
                "CONDITIONAL"
            )

        # ============================================================
        # Final Validation 10：UNKNOWN 条件
        # ============================================================

        if not validate_unknown_conditions(
            text,
            decision,
        ):
            failures.append(
                "UNKNOWN"
            )

        # ============================================================
        # Final Validation 11：法律依据
        # ============================================================

        rules = ensure_list(
            decision.get(
                "rules",
                []
            )
        )

        if not validate_legal_basis(
            text,
            rules,
        ):
            failures.append(
                "LEGAL_BASIS"
            )

        # ============================================================
        # Final Validation 12：Decision Consistency
        # ============================================================

        if not validate_decision_consistency(
            text,
            decision,
        ):
            failures.append(
                "DECISION_CONSISTENCY"
            )

        return failures

    # ========================================================
    # DEBUG：Final Validation 实际输入诊断
    #
    # V6.0-27
    #
    # 用于定位：
    #
    #     ANSWER_STRUCTURE
    #
    # 是否真的由 validate_answer_structure()
    # 返回 False 导致。
    #
    # 注意：
    #
    # 这里只是诊断代码，不修改 answer。
    # ========================================================

    print()
    print("=" * 70)
    print("DEBUG / Final Validation Input")
    print("=" * 70)

    print(answer)

    print()
    print("DEBUG / Section Counts")

    for section in REQUIRED_SECTIONS:
        print(
            f"{section}: "
            f"{answer.count(section)}"
        )

    print()
    print("DEBUG / Section Positions")

    for section in REQUIRED_SECTIONS:
        print(
            f"{section}: "
            f"{answer.find(section)}"
        )

    print()
    print(
        "DEBUG / validate_answer_structure:",
        validate_answer_structure(answer),
    )

    print("=" * 70)

    failures = run_checks(
        answer,
        question,
        decision,
    )

    if not failures:
        print()
        print("✅ 最终答案验证通过")
        return answer

    print()
    print(
        "⚠️ Ollama 回答未通过 Validation："
        + ", ".join(failures)
    )

    # --------------------------------------------------------
    # 安全 Fallback
    # --------------------------------------------------------
    #
    # 只要任意一项验证失败，就不能继续信任 Ollama 输出。
    # Fallback 使用已经完成的 Structured Decision / Rules，
    # 不重新推理，也不补充 Decision Engine 没有提供的条件。
    # --------------------------------------------------------

    print()
    print("⚠️ V6.0-27 启用安全 Fallback。")

    fallback = build_fallback_answer(
        question=question,
        decision=decision,
    )
    fallback = clean_answer(fallback)

    fallback_failures = run_checks(
        fallback,
        question,
        decision,
    )

    if not fallback_failures:
        print()
        print("✅ Fallback 最终答案验证通过")
        return fallback

    print()
    print(
        "⚠️ Fallback 仍未通过全部 Validation："
        + ", ".join(fallback_failures)
    )

    # 最后返回确定性的结构化 Fallback，而不是返回未经验证的 Ollama 答案。
    # 不递归调用 final_validation，避免无限递归。
    return fallback


