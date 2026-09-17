# -*- coding: utf-8 -*-

"""
RAG V6.0-27
Deterministic User Facts Layer

============================================================
功能
============================================================

负责将 Legal Decision Engine 已经确认的用户事实，
确定性地注入最终答案。

核心原则：

    Decision Engine
          ↓
    user_facts / explicit_facts
          ↓
    Deterministic User Facts
          ↓
    Ollama Answer

本模块只负责：

    1. 从 Decision 中读取用户事实；
    2. 构造确定性的“用户事实”文本；
    3. 删除 LLM 原有的用户事实；
    4. 将 Engine 用户事实重新注入；
    5. 保留其他法律分析内容；
    6. 保留后续法律章节。

本模块不负责：

    1. 法律推理；
    2. 条件判定；
    3. 法律依据；
    4. 法律结论；
    5. Ollama 调用；
    6. 最终 Validation。

============================================================
重要设计原则
============================================================

LLM 不得自行创造用户事实。

例如用户问题：

    公司连续签订三次固定期限劳动合同后，
    是否必须签订无固定期限劳动合同？

Engine 明确记录：

    公司连续签订三次固定期限劳动合同

则最终答案中的：

    1. 用户事实：

必须来自 Engine。

不能被 LLM 改写成：

    劳动者存在《劳动合同法》第三十九条规定的情形

即使 LLM 自己这样生成，也必须被本模块覆盖。

============================================================
RAG V6.0-27
============================================================
"""

import re
from typing import Any, Dict


# ============================================================
# Deterministic User Facts
# ============================================================

def build_deterministic_user_facts(
    decision: Dict[str, Any],
) -> str:
    """
    根据 Legal Decision Engine 的用户事实，
    确定性生成【法律分析】中的“用户事实”部分。

    核心原则：

    1. Decision Engine 是用户事实的唯一可信来源。
    2. Ollama 不负责重新提取、判断或改写用户事实。
    3. Python 在 Final Validation 之前，
       强制将 Engine 用户事实写入最终回答。
    4. 防止 Ollama 因模型生成偏差而遗漏用户事实。
    """

    user_facts = decision.get(
        "user_facts",
        decision.get(
            "explicit_facts",
            [],
        ),
    ) or []

    lines = [
        "1. 用户事实："
    ]

    if not user_facts:

        lines.append(
            "- 无。"
        )

        return "\n".join(lines)

    for fact in user_facts:

        if isinstance(
            fact,
            dict,
        ):

            fact_text = fact.get(
                "fact",
                fact.get(
                    "description",
                    fact.get(
                        "condition",
                        str(fact),
                    ),
                ),
            )

        else:

            fact_text = getattr(
                fact,
                "fact",
                str(fact),
            )

        fact_text = str(
            fact_text
        ).strip()

        if fact_text:

            lines.append(
                f"- {fact_text}"
            )

    if len(lines) == 1:

        lines.append(
            "- 无。"
        )

    return "\n".join(lines)


def inject_deterministic_user_facts(
    answer: str,
    decision: Dict[str, Any],
) -> str:
    """
    在 Final Validation 之前，
    用 Decision Engine 的用户事实确定性覆盖
    Ollama 生成的“用户事实”部分。

    V6.0-27 修正：

    1. Decision Engine 是用户事实唯一可信来源。
    2. Python 确定性注入 Engine User Facts。
    3. 删除 Ollama 原有的“用户事实”内容。
    4. 保留 Ollama 其余法律分析内容。
    5. 重新整理“法律分析”内部的顶层编号。
    6. 不修改【法律依据】和【需要注意】等其他区域。

    核心流程：

        Engine User Facts
                ↓
        Python Deterministic Injection
                ↓
        Ollama Legal Analysis
                ↓
        Final Validation

    而不是：

        Engine User Facts
                ↓
        Ollama 自行决定是否保留
                ↓
        Final Validation

    后一种方式存在模型遗漏用户事实的风险。
    """

    # ========================================================
    # Step 1
    # 构建确定性的用户事实
    # ========================================================

    deterministic_user_facts = (
        build_deterministic_user_facts(
            decision=decision,
        )
    )

    # ========================================================
    # Step 2
    # answer 为空
    # ========================================================

    if not answer:

        return (
            "【法律分析】\n"
            + deterministic_user_facts
        )

    analysis_marker = "【法律分析】"

    # ========================================================
    # Step 3
    # Ollama 没有生成【法律分析】
    # ========================================================

    if analysis_marker not in answer:

        return (
            answer.rstrip()
            + "\n\n"
            + analysis_marker
            + "\n"
            + deterministic_user_facts
        )

    # ========================================================
    # Step 4
    # 拆分【法律分析】
    # ========================================================

    prefix, analysis_body = answer.split(
        analysis_marker,
        1,
    )

    analysis_body = analysis_body.strip()

    # ========================================================
    # Step 5
    # 找到【法律分析】结束位置
    #
    # 法律分析后面通常可能出现：
    #
    # 【需要注意】
    #
    # 或其他新的一级区块。
    #
    # 这里只处理“法律分析”本身。
    # ========================================================

    next_section_pattern = re.compile(
        r"\n(?=【[^】]+】)",
    )

    section_match = next_section_pattern.search(
        analysis_body,
    )

    if section_match:

        analysis_content = analysis_body[
            :section_match.start()
        ].rstrip()

        remaining_sections = analysis_body[
            section_match.start():
        ].lstrip()

    else:

        analysis_content = analysis_body.rstrip()

        remaining_sections = ""

    # ========================================================
    # Step 6
    # 删除 Ollama 原有的“用户事实”区域
    #
    # Ollama 可能生成多种不同格式：
    #
    # --------------------------------------------------------
    # 格式一：
    #
    # 1. 用户事实：
    # - xxx
    # - xxx
    #
    # 2. 条件状态：...
    #
    # --------------------------------------------------------
    # 格式二：
    #
    # 用户事实：
    # 1. xxx
    # 2. xxx
    #
    # 当前条件状态：
    # - xxx
    #
    # --------------------------------------------------------
    # 格式三：
    #
    # 用户事实：
    # - xxx
    # - xxx
    #
    # 条件状态：
    # - xxx
    #
    # --------------------------------------------------------
    #
    # 这些内容全部不能作为最终用户事实。
    #
    # Decision Engine 才是用户事实唯一可信来源。
    #
    # 因此：
    #
    # 1. 删除“1. 用户事实：”形式的整个顶层条目。
    # 2. 删除“用户事实：”形式的整个用户事实区域。
    # 3. 删除用户事实区域中的编号事实。
    # 4. 保留后面的“当前条件状态”“条件状态”等法律分析。
    #
    # ========================================================

    analysis_without_user_facts = (
        analysis_content
    )

    # --------------------------------------------------------
    # Step 6-A
    # 删除：
    #
    # 1. 用户事实：
    # - xxx
    # - xxx
    #
    # 直到下一个顶层编号。
    #
    # --------------------------------------------------------

    numbered_user_fact_pattern = re.compile(
        r"(?ms)"
        r"^\s*\d+\.\s*用户事实：.*?"
        r"(?=^\s*\d+\.\s+|\Z)",
    )

    analysis_without_user_facts = (
        numbered_user_fact_pattern.sub(
            "",
            analysis_without_user_facts,
        )
    )

    # --------------------------------------------------------
    # Step 6-B
    # 删除：
    #
    # 用户事实：
    # 1. xxx
    # 2. xxx
    #
    # 或：
    #
    # 用户事实：
    # - xxx
    # - xxx
    #
    # 直到下一个分析区块标题。
    #
    # 例如：
    #
    # 用户事实：
    # 1. xxx
    # 2. xxx
    #
    # 当前条件状态：
    # - xxx
    #
    # 删除结果：
    #
    # 当前条件状态：
    # - xxx
    #
    # --------------------------------------------------------

    plain_user_fact_pattern = re.compile(
        r"(?ms)"
        r"^\s*用户事实："
        r".*?"
        r"(?=^\s*(?:当前条件状态|条件状态|法律分析|分析结果|判断结果)\s*:)",
    )

    analysis_without_user_facts = (
        plain_user_fact_pattern.sub(
            "",
            analysis_without_user_facts,
        )
    )

    # --------------------------------------------------------
    # Step 6-C
    # 兼容“用户事实”后面没有明显区块标题，
    # 但直接结束于分析文本末尾的情况。
    #
    # 例如：
    #
    # 用户事实：
    # 1. xxx
    # 2. xxx
    #
    # --------------------------------------------------------

    plain_user_fact_tail_pattern = re.compile(
        r"(?ms)"
        r"^\s*用户事实：.*\Z",
    )

    if re.search(
        r"(?ms)^\s*用户事实：",
        analysis_without_user_facts,
    ):

        analysis_without_user_facts = (
            plain_user_fact_tail_pattern.sub(
                "",
                analysis_without_user_facts,
            )
        )

    analysis_without_user_facts = (
        analysis_without_user_facts
        .strip()
    )

    # ========================================================
    # Step 7
    # 重新提取 Ollama 剩余的顶层分析条目
    #
    # 例如原始：
    #
    # 1. 已确认的排除条件
    # 2. 以下条件状态为 UNKNOWN
    #
    # 注入用户事实后：
    #
    # 1. 用户事实
    # 2. 已确认的排除条件
    # 3. 以下条件状态为 UNKNOWN
    #
    # 注意：
    #
    # 这里只重新编号顶层分析条目。
    # 条目内部的：
    #
    # - xxx
    # - xxx
    #
    # 不会受到影响。
    # ========================================================

    item_pattern = re.compile(
        r"(?ms)"
        r"^\s*(\d+)\.\s+"
        r"(.*?)(?=^\s*\d+\.\s+|\Z)",
    )

    items = []

    for match in item_pattern.finditer(
        analysis_without_user_facts
    ):

        item_text = match.group(
            2
        ).strip()

        if not item_text:

            continue

        items.append(
            item_text
        )

    # ========================================================
    # Step 8
    # 构建新的法律分析
    # ========================================================

    rebuilt_analysis = [
        deterministic_user_facts
    ]

    # --------------------------------------------------------
    # 如果成功识别到了 Ollama 的顶层分析条目，
    # 则重新编号。
    # --------------------------------------------------------

    if items:

        for index, item in enumerate(
            items,
            start=2,
        ):

            rebuilt_analysis.append(
                f"{index}. {item}"
            )

    # --------------------------------------------------------
    # 如果没有识别到顶层编号，
    # 但仍然存在 Ollama 法律分析文本，
    # 则直接保留。
    # --------------------------------------------------------

    elif analysis_without_user_facts:

        rebuilt_analysis.append(
            analysis_without_user_facts
        )

    # ========================================================
    # Step 9
    # 拼接最终结果
    # ========================================================

    rebuilt_body = (
        "\n".join(
            rebuilt_analysis
        ).strip()
    )

    result = (
        prefix.rstrip()
        + "\n\n"
        + analysis_marker
        + "\n"
        + rebuilt_body
    )

    # ========================================================
    # Step 10
    # 恢复后续区块
    #
    # 例如：
    #
    # 【需要注意】
    #
    # 注意：
    #
    # 【需要注意】最终还会在 Final Validation
    # 之后由 deterministic notices 再次覆盖。
    # ========================================================

    if remaining_sections:

        result += (
            "\n\n"
            + remaining_sections
        )

    return result


# ============================================================
# End of deterministic_user_facts.py
# ============================================================
