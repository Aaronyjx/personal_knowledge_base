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

    RAG V6.0-27

    处理原则：

        LLM 输出
            ↓
        删除原有“条件状态”部分
            ↓
        插入 Engine 确定性的完整条件状态

    这样可以防止：

    1. LLM 漏掉 SATISFIED 条件；
    2. LLM 合并多个 EXCLUSION 条件；
    3. LLM 将 EXCEPTION 当作普通 UNKNOWN；
    4. LLM 自行改变条件状态；
    5. LLM 根据自然语言重新解释 Engine 判定。

    注意：

    用户事实由
        inject_deterministic_user_facts()
    单独负责。

    本函数只负责：
        “条件状态”
    """

    if not isinstance(answer, str):
        answer = str(answer or "")

    deterministic_analysis = (
        build_deterministic_condition_analysis(
            decision
        )
    )

    # ========================================================
    # RAG V6.0-27
    #
    # 最终答案的章节标题必须使用完整 Marker：
    #
    #     【结论】
    #     【法律依据】
    #     【法律分析】
    #     【需要注意】
    #
    # 不能只匹配：
    #
    #     结论
    #     法律依据
    #     法律分析
    #     需要注意
    #
    # 否则正则可能无法识别章节边界，
    # 导致“条件状态”替换范围一直匹配到文本末尾，
    # 从而把【需要注意】等后续章节一起删除。
    # ========================================================

    section_boundary = (
        r"【(?:结论|法律依据|法律分析|需要注意)】"
    )

    # ========================================================
    # 情况 1：
    #
    # LLM 输出标准的：
    #
    #     2. 条件状态：
    #
    # 后面紧接着：
    #
    #     【需要注意】
    #     【法律依据】
    #     【法律分析】
    #     【结论】
    #
    # 只替换“2. 条件状态”这一段。
    #
    # 绝不能吃掉后面的章节。
    # ========================================================

    condition_pattern = re.compile(
        r"(?ms)"
        r"^\s*2\.\s*条件状态\s*：?"
        r".*?"
        rf"(?=^\s*(?:3\.\s*)?{section_boundary}|\Z)"
    )

    if condition_pattern.search(answer):
        return condition_pattern.sub(
            deterministic_analysis,
            answer,
            count=1,
        )

    # ========================================================
    # 情况 2：
    #
    # LLM 使用：
    #
    #     当前条件状态：
    #
    # 或：
    #
    #     条件状态：
    #
    # 同样只替换这一部分。
    # ========================================================

    plain_condition_pattern = re.compile(
        r"(?ms)"
        r"^\s*(?:当前条件状态|条件状态)\s*：?"
        r".*?"
        rf"(?=^\s*{section_boundary}|\Z)"
    )

    if plain_condition_pattern.search(answer):
        return plain_condition_pattern.sub(
            deterministic_analysis,
            answer,
            count=1,
        )

    # ========================================================
    # 情况 3：
    #
    # LLM 没有输出条件状态，
    # 但存在【法律分析】章节。
    #
    # 直接在【法律分析】后面插入确定性的
    # Condition Analysis。
    # ========================================================

    analysis_header_pattern = re.compile(
        r"(?m)"
        r"^\s*【法律分析】\s*$"
    )

    match = analysis_header_pattern.search(answer)

    if match:
        insertion_point = match.end()

        return (
            answer[:insertion_point]
            + "\n"
            + deterministic_analysis
            + answer[insertion_point:]
        )

    # ========================================================
    # 情况 4：
    #
    # 连【法律分析】都不存在。
    #
    # 为了保证后续 Validation 可以继续处理，
    # 将确定性的条件分析追加到答案末尾。
    # ========================================================

    if answer.strip():
        return (
            answer.rstrip()
            + "\n\n"
            + deterministic_analysis
        )

    return deterministic_analysis
