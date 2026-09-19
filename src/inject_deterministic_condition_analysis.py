# -*- coding: utf-8 -*-

"""
RAG V6.0-27
Deterministic Condition Analysis

============================================================
功能
============================================================

本模块负责：

    Decision Engine
          ↓
    condition_results
          ↓
    Deterministic Condition Analysis
          ↓
    Final Answer

============================================================
核心原则
============================================================

1. Legal Decision Engine 是唯一的法律条件判定来源。

2. 本模块不得重新进行法律推理。

3. 必须直接使用 Decision Engine 返回的
   condition_results。

4. 所有 ConditionResult 必须逐条保留。

5. 不允许 LLM 合并、删除或修改条件状态。

6. 必须严格保持 Engine 返回的原始条件顺序。

7. 最终章节边界必须使用完整 Marker：

       【结论】
       【法律依据】
       【法律分析】
       【需要注意】

8. 特别防止条件状态替换时误删除
   【需要注意】等后续章节。

============================================================
"""

import re

from typing import Any, Dict, List, Optional

from src.legal_common import ensure_list
from src.legal_answer_builder import safe_text, get_value
from src.legal_decision_engine import (
    SATISFIED,
    NOT_SATISFIED,
    UNKNOWN,
)

def build_deterministic_condition_analysis(
    decision: Dict[str, Any],
) -> str:
    """
    构造确定性的 ConditionResult 法律分析。

    RAG V6.0-27

    重要原则：

    1. 必须直接读取 Decision Engine 的完整
       condition_results。

    2. 不使用：
           unknown_conditions
       因为该字段现在只表示：
           REQUIRED + UNKNOWN

    3. 所有 ConditionResult 都必须逐条输出。

    4. 不允许 LLM 合并多个条件。

    5. 不允许 LLM 删除 SATISFIED 条件。

    6. ConditionResult 的 status、condition、
       reason 等信息均以 Engine 为准。

    7. 当前阶段只确定性替换“条件状态”部分，
       不让该函数参与法律结论生成。

    8. 条件状态使用项目统一的
       “2. 条件状态：”标题。

    9. 每条 ConditionResult 使用无序列表，
       不再重新编号 1～8。

       原因：

           1. 用户事实
           2. 条件状态

       已经是法律分析的顶层结构。

       如果 ConditionResult 再使用
       1～8 编号，就会形成：

           2. 条件状态：
           1. 条件A
           2. 条件B

       造成顶层编号和内部编号混乱。

    10. ConditionResult 的顺序必须严格保持
        Decision Engine 返回的原始顺序。
    """

    # ========================================================
    # 1. 读取 Engine 完整 ConditionResult
    # ========================================================

    condition_results = ensure_list(
        decision.get(
            "condition_results",
            [],
        )
    )

    # ========================================================
    # 2. 构造确定性条件状态标题
    # ========================================================

    lines = [
        "2. 条件状态："
    ]

    # ========================================================
    # 3. Engine 没有返回 ConditionResult
    #
    # 不能自行制造法律条件。
    # ========================================================

    if not condition_results:

        lines.append(
            "- 当前 Decision Engine 未返回条件状态。"
        )

        return "\n".join(lines)

    # ========================================================
    # 4. 逐条输出完整 ConditionResult
    #
    # 注意：
    #
    # 这里故意不使用 enumerate() 生成 1～8 编号。
    #
    # 必须保证：
    #
    #     8 条 Engine ConditionResult
    #         ↓
    #     8 条最终条件状态
    #
    # 一条都不能删除，也不能合并。
    # ========================================================

    for item in condition_results:

        condition = safe_text(
            get_value(
                item,
                "condition",
                "",
            )
        ).strip()

        status = safe_text(
            get_value(
                item,
                "status",
                "",
            )
        ).strip()

        # ----------------------------------------------------
        # Engine ConditionResult 如果没有 condition，
        # 不允许自行推测法律条件。
        #
        # 这里只使用安全占位文本。
        # ----------------------------------------------------

        if not condition:

            condition = "未命名条件"

        # ====================================================
        # 5. 将 Engine 状态转换成展示文本
        #
        # 这里只做显示转换：
        #
        # SATISFIED
        #     ↓
        # 已满足
        #
        # NOT_SATISFIED
        #     ↓
        # 未满足
        #
        # UNKNOWN
        #     ↓
        # 未知
        #
        # 不改变 Engine 的实际状态。
        # ====================================================

        if status == SATISFIED:

            status_text = "已满足"

        elif status == NOT_SATISFIED:

            status_text = "未满足"

        elif status == UNKNOWN:

            status_text = "未知"

        else:

            # ------------------------------------------------
            # Engine 出现未知状态时，
            # 不允许自行解释成满足或不满足。
            # ------------------------------------------------

            status_text = (
                f"状态：{status or '未知状态'}"
            )

        # ====================================================
        # 6. 使用无序列表输出
        #
        # 例如：
        #
        # - 连续订立二次固定期限劳动合同：已满足
        # - 存在后续订立的劳动合同：已满足
        # - 续订劳动合同：未知
        #
        # 不再输出：
        #
        # 1.
        # 2.
        # 3.
        #
        # 防止与“2. 条件状态”发生编号冲突。
        # ====================================================

        lines.append(
            f"- {condition}："
            f"{status_text}"
        )

    # ========================================================
    # 7. 返回确定性的 Condition Analysis
    # ========================================================

    return "\n".join(lines)

def inject_deterministic_condition_analysis(
    answer: str,
    decision: Dict[str, Any],
) -> str:
    """
    将 Decision Engine 的完整 ConditionResult
    确定性注入最终法律分析。

    RAG V6.1

    ========================================================
    单一职责
    ========================================================

    本函数只负责：

        1. 定位【法律分析】章节。

        2. 清理 Ollama 对 Engine User Facts /
           ConditionResult 的重复解释。

        3. 保留已经由
           inject_deterministic_user_facts()
           注入的确定性用户事实。

        4. 插入由
           build_deterministic_condition_analysis()
           构造的确定性条件状态。

        5. 保留【法律分析】之后的其他章节。

    ========================================================
    V6.1 修复原则
    ========================================================

    【法律分析】中的 User Facts /
    ConditionResult 属于 Deterministic Data。

    因此：

        Engine
            ↓
        User Facts
            ↓
        ConditionResult
            ↓
        Deterministic Analysis

    Ollama 不拥有这些数据的最终控制权。

    本函数不再尝试逐项猜测 Ollama 的编号标题，
    而是直接重建【法律分析】中的确定性结构。

    这样可以避免：

        2. **已满足条件**：...
        3. **待确认条件**：...

    等模型生成内容污染 Deterministic
    Condition Analysis。

    ========================================================
    不负责的事项
    ========================================================

    本函数绝不：

        1. 重新进行法律推理。

        2. 判断任何 ConditionResult。

        3. 修改 Decision Engine 的状态。

        4. 修改 User Facts 的内容。

        5. 修改【结论】。

        6. 修改【法律依据】。

        7. 修改【需要注意】。

        8. 生成新的法律条件。

    ========================================================
    最终结构
    ========================================================

        【法律分析】

        1. 用户事实：
        - xxx

        2. 条件状态：
        - 条件A：已满足
        - 条件B：未知
        - ...

    ========================================================
    """

    # ========================================================
    # 1. 参数安全处理
    # ========================================================

    if not answer:
        answer = ""

    # ========================================================
    # 2. 构造 Engine Deterministic Condition Analysis
    #
    # 唯一数据来源：
    #
    #     Decision Engine
    #         ↓
    #     condition_results
    # ========================================================

    deterministic_analysis = (
        build_deterministic_condition_analysis(
            decision
        )
    )

    # ========================================================
    # 3. 定位【法律分析】
    # ========================================================

    analysis_header_pattern = re.compile(
        r"(?m)^\s*【法律分析】\s*$"
    )

    analysis_header_match = (
        analysis_header_pattern.search(answer)
    )

    # ========================================================
    # 4. 如果不存在【法律分析】
    #
    # 当前答案没有标准法律分析章节时，
    # 直接追加 Deterministic Condition Analysis。
    #
    # 不虚构 User Facts。
    # ========================================================

    if not analysis_header_match:

        if answer.strip():

            return (
                answer.rstrip()
                + "\n\n"
                + "【法律分析】"
                + "\n\n"
                + deterministic_analysis
            )

        return (
            "【法律分析】\n\n"
            + deterministic_analysis
        )

    # ========================================================
    # 5. 定位【法律分析】之后的下一个标准章节
    #
    # 只识别完整章节 Marker：
    #
    #     【结论】
    #     【法律依据】
    #     【法律分析】
    #     【需要注意】
    #
    # 不使用：
    #
    #     【[^】]+】
    #
    # 避免普通中文文本中的括号
    # 被误认为章节边界。
    # ========================================================

    section_header_pattern = re.compile(
        r"(?m)^\s*【(?:结论|法律依据|法律分析|需要注意)】\s*$"
    )

    next_section_match = None

    for match in section_header_pattern.finditer(
        answer,
        analysis_header_match.end(),
    ):

        if match.start() > analysis_header_match.end():

            next_section_match = match

            break

    # ========================================================
    # 6. 拆分完整答案
    #
    # prefix：
    #
    #     【结论】
    #     【法律依据】
    #     ...
    #
    # analysis_body：
    #
    #     【法律分析】之后的原始内容
    #
    # suffix：
    #
    #     【需要注意】
    #     以及之后的内容
    # ========================================================

    if next_section_match:

        prefix = answer[
            :analysis_header_match.end()
        ]

        analysis_body = answer[
            analysis_header_match.end():
            next_section_match.start()
        ]

        suffix = answer[
            next_section_match.start():
        ]

    else:

        prefix = answer[
            :analysis_header_match.end()
        ]

        analysis_body = answer[
            analysis_header_match.end():
        ]

        suffix = ""

    # ========================================================
    # 7. 提取已经注入的 Deterministic User Facts
    #
    # --------------------------------------------------------
    # 正常结构：
    #
    #     1. 用户事实：
    #     - 公司连续签订三次固定期限劳动合同
    #
    # 这里只提取已经存在的 Deterministic
    # User Facts，不从 Ollama 重新推断事实。
    #
    # --------------------------------------------------------
    # 如果不存在 Deterministic User Facts：
    #
    #     不虚构新的 User Facts。
    # ========================================================

    deterministic_user_fact_pattern = re.compile(
        r"(?ms)"
        r"^\s*1\.\s*用户事实\s*：?"
        r"(.*?)"
        r"(?=^\s*2\.\s+|\Z)"
    )

    user_fact_match = (
        deterministic_user_fact_pattern.search(
            analysis_body
        )
    )

    deterministic_user_fact_section = ""

    if user_fact_match:

        user_fact_content = (
            user_fact_match.group(1).strip()
        )

        if user_fact_content:

            deterministic_user_fact_section = (
                "1. 用户事实：\n"
                + user_fact_content
            )

    # ========================================================
    # 8. 重新构建【法律分析】
    #
    # ========================================================
    #
    # 关键修复：
    #
    # 不再对 Ollama 原有 analysis_body
    # 做局部删除。
    #
    # 直接丢弃整个 Ollama Analysis Body，
    # 只保留：
    #
    #     A. Deterministic User Facts
    #
    #     B. Deterministic Condition Analysis
    #
    # 这样可以彻底消除：
    #
    #     2. **已满足条件**：...
    #
    #     3. **待确认条件**：...
    #
    #     1. **xxx**
    #
    #     2. 条件状态……
    #
    #     未知2.
    #
    # 等模型格式污染。
    # ========================================================

    analysis_parts = []

    if deterministic_user_fact_section:

        analysis_parts.append(
            deterministic_user_fact_section
        )

    if deterministic_analysis:

        analysis_parts.append(
            deterministic_analysis
        )

    rebuilt_body = "\n\n".join(
        part.strip()
        for part in analysis_parts
        if part and part.strip()
    ).strip()

    # ========================================================
    # 9. 如果没有任何 Deterministic Analysis
    #
    # 极端情况下保留原始 analysis_body，
    # 防止函数无故删除用户内容。
    #
    # 正常 Legal RAG Pipeline 不应进入这里。
    # ========================================================

    if not rebuilt_body:

        rebuilt_body = (
            analysis_body.strip()
        )

    # ========================================================
    # 10. 重建完整答案
    #
    # prefix
    #     +
    # 【法律分析】
    #     +
    # Deterministic Analysis
    #     +
    # suffix
    #
    # suffix 完全保持原有章节内容。
    # ========================================================

    result = (
        prefix.rstrip()
        + "\n\n"
        + rebuilt_body
    )

    if suffix:

        result += (
            "\n\n"
            + suffix.lstrip()
        )

    # ========================================================
    # 11. 最终空白清理
    #
    # 不修改任何文字内容，
    # 只压缩连续空行。
    # ========================================================

    result = re.sub(
        r"\n[ \t]*\n[ \t]*\n+",
        "\n\n",
        result,
    )

    return result.strip()
