# -*- coding: utf-8 -*-

"""
Legal Citation Validator

从 RAG V6.0-27 原始 rag.py 拆分。

职责：
    - 法条数字归一化
    - 法律名称归一化
    - 法律依据引用归一化
    - Structured Rules 法律依据引用验证

注意：
    当前版本为了保持与原始 RAG V6.0-27 的逻辑完全一致，
    Validator 通过 src.rag 获取现有 Rules 构建及通用字段函数。
    后续在继续拆分公共 Rule/Utility 层时，再统一调整依赖边界。
"""

import re
from typing import Any, Dict, List

from src.rag import (
    build_rules_from_articles,
    ensure_list,
    get_rule_value,
    normalize_text,
)


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