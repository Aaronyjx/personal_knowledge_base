# -*- coding: utf-8 -*-

# ============================================================
# RAG V6.0-27
# Legal RAG Pipeline
#
# 完整流程：
#
#     User Question
#           ↓
#     Retriever
#           ↓
#     Structured Articles
#           ↓
#     Legal Rules
#           ↓
#     Legal Decision Engine
#           ↓
#     DecisionResult
#           ↓
#     Decision Adapter
#           ↓
#     Legal Answer Builder
#           ↓
#     Ollama
#           ↓
#     Final Validation
#           ↓
#     Final Legal Answer
#
# ============================================================
#
# V6.0-13 核心原则
#
# 1. Retriever 负责寻找法律依据。
#
# 2. Legal Decision Engine 负责结构化法律判断。
#
# 3. Decision Adapter 负责接口适配。
#
# 4. Legal Answer Builder 负责构建结构化回答。
#
# 5. Ollama 只负责自然语言表达。
#
# 6. Ollama 不允许重新判断法律。
#
# 7. 用户事实必须保持原意。
#
# 8. 法律规则和用户事实必须严格区分。
#
# 9. CONDITIONAL 必须保持条件性。
#
# 10. UNKNOWN 条件不得自行补充。
#
# 11. 最终回答必须经过 Validation。
#
# ============================================================
#
# V6.0-13 相对于 V6.0-11 的主要改进
#
# 1. 用户事实层增加“事实保真”保护。
# 2. “连续签订三次固定期限劳动合同”必须保留为用户事实。
# 3. “连续订立二次固定期限劳动合同”只能作为法律规则/条件表达。
# 4. 三次合同事实达到“两次”数量门槛时，只确认数量条件，不覆盖原始事实。
# 5. 不再把“第三次是否属于续订”作为机械 UNKNOWN 条件重复追问。
# 6. UNKNOWN 仅保留真正尚未提供的法律事实。
# 7. 修复 Fallback Validation 将法律规则“二次”误判为用户事实错误的问题。
# 8. THREE_CONTRACT_FACT 只检查用户事实是否被错误替换，不再禁止法律规则中正常出现“二次”。
# 9. Fallback 明确区分“用户事实三次”和“法律规则二次门槛”。
# 10. 保留 V6.0-11 全部 Retriever、Decision Engine、Answer Builder、Ollama 和 Validation 接口兼容性。
# 11. 不改变 Legal Decision Engine 的核心法律判断职责。
# 12. 不让 RAG 层自行把 CONDITIONAL 转换为 DEFINITE。
#
# ============================================================
#
# 运行方式：
#
#     cd ~/Projects/Jupyter/personal_knowledge_base
#
#     python -m src.rag
#
# ============================================================

#
# V6.0-13 相对于 V6.0-12 的主要改进：
#
# 1. 法律规则增加 CORE / RELATED 分层。
# 2. 与用户问题直接相关的核心法条优先展示，不删除相关规则。
# 3. “固定期限劳动合同 + 三次”问题优先突出《劳动合同法》第十四条。
# 4. Legal Basis Validation 支持“第十四条”和“第14条”等等价写法。
# 5. Legal Basis Validation 忽略引用中的普通空格，减少合法引用误判。
# 6. 保留“当前 Rules 之外的法条不得凭空引用”的安全限制。
# 7. Fallback 结论更准确地区分“数量门槛已达到”和“最终法律义务仍需检查其他条件”。
# 8. Fallback 法律依据按核心规则优先输出。
# 9. 不修改用户事实：“连续签订三次固定期限劳动合同”仍然保持为用户事实。
# 10. “连续订立二次固定期限劳动合同”只作为法律规则门槛，不覆盖用户事实。
# 11. 保留 V6.0-12 的 Fallback、UNKNOWN、CONDITIONAL、THREE_CONTRACT_FACT 安全机制。
#
#
# V6.0-18 相对于 V6.0-17 的主要改进：
#
# 1. 强化“连续签订三次固定期限劳动合同”用户事实保护。
# 2. 禁止 Ollama 将“第三次合同是否属于续订”等已被用户事实包含的内容再次制造为 UNKNOWN。
# 3. 新增 MANUFACTURED_UNKNOWN Validation，发现重复制造未知条件时自动进入安全 Fallback。
# 4. 保留 V6.0-17 的严格 Legal Basis Validation：只识别明确的《法律名称》第X条引用。
# 5. 不改变 Legal Decision Engine 的核心 Decision。
# 6. 不改变 CONDITIONAL 的条件性，不删除真正未知的法定条件。
#
# V6.0-22 相对于 V6.0-18 的主要改进：
#
# 1. Deterministic Fallback 正式升级为 V6.0-22。
# 2. Fallback 直接使用 Structured Answer 中的 User Facts、Satisfied、
#    Unsatisfied、Unknown 和 Rules，不重新进行法律推理。
# 3. Fallback 不再使用固定的“其他法定条件或例外”替代结构化 UNKNOWN。
# 4. CONDITIONAL 结论与 Structured Decision 保持严格一致。
# 5. Fallback 日志、注释与 RAG_VERSION 全部统一到 V6.0-22。
# 6. 保留 V6.0-18 的 MANUFACTURED_UNKNOWN、LEGAL_BASIS 等安全验证。
#
# ============================================================
#
# V6.0-22 相对于 V6.0-21 的主要改进：
#
# 1. 修复 ENGINE_CONDITION_COMPLETENESS 误报：支持 DecisionResult 对象。
# 2. Decision Adapter 正式区分 REQUIRED / EXCLUSION / EXCEPTION。
# 3. Exclusion / Exception 不再错误进入 unknown_conditions。
# 4. unknown_conditions 只保留必备条件中的 UNKNOWN。
# 5. 增加 condition_results 分类结果，供 Builder / Ollama / Validation 使用。
# 6. Ollama Prompt 明确展示三类条件及其状态，禁止重新解释类别。
# 7. Final Validation 增加 CONDITION_CATEGORY 检查。
# 8. Legal Basis Validation 统一先规范化 Rules，并兼容 dict / object。
# 9. Fallback 按“必备条件 / 排除条件 / 例外条件”分层输出。
# 10. 不改变 Retriever 和 Legal Decision Engine 的核心法律判断职责。
# 11. 不修改用户事实；“三次”继续作为用户事实，“二次”继续作为法律规则门槛。
# 12. 保留 V6.0-21 的用户事实、CONDITIONAL、UNKNOWN、法律依据安全机制。
#
# ============================================================
# 标准库
# ============================================================

import re
from typing import Any, Dict, List


# ============================================================
# 第三方库
# ============================================================

import requests


# ============================================================
# 项目内部模块
# ============================================================

from src.retriever import build_context

from src.legal_decision_engine import (
    make_decision,
)

from src.legal_answer_builder import (
    adapt_decision_for_answer_builder as builder_adapt_decision,
    build_plain_answer,
    get_value,
    safe_text,
)


# ============================================================
# 常量
# ============================================================

RAG_VERSION = "V6.0-27"

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"

OLLAMA_MODEL = "qwen3:14b"


# ============================================================
# Legal Decision Engine 状态
# ============================================================

DECISION_DEFINITE = "DEFINITE"

DECISION_CONDITIONAL = "CONDITIONAL"

DECISION_NOT_ESTABLISHED = "NOT_ESTABLISHED"


VALID_ENGINE_DECISIONS = {
    DECISION_DEFINITE,
    DECISION_CONDITIONAL,
    DECISION_NOT_ESTABLISHED,
}


# ============================================================
# Legal Answer Builder 状态
# ============================================================

ANSWER_SATISFIED = "SATISFIED"

ANSWER_UNSATISFIED = "UNSATISFIED"

ANSWER_UNKNOWN = "UNKNOWN"

ANSWER_CONDITIONAL = "CONDITIONAL"


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


# ============================================================
# 通用文本函数
# ============================================================

def normalize_text(value: Any) -> str:
    # 安全文本转换。
    #
    # None 返回空字符串。
    #
    # 其他类型转换为字符串。

    if value is None:
        return ""

    return str(value).strip()


# ============================================================
# 通用列表函数
# ============================================================

def ensure_list(value: Any) -> List[Any]:
    # 将对象转换为列表。

    if value is None:
        return []

    if isinstance(value, list):
        return value

    if isinstance(value, tuple):
        return list(value)

    if isinstance(value, set):
        return list(value)

    return [value]


# ============================================================
# 文本去重
# ============================================================

def unique_texts(values: List[Any]) -> List[str]:
    # 保持原始顺序进行文本去重。

    result = []

    seen = set()

    for value in values:
        text = normalize_text(value)

        if not text:
            continue

        if text in seen:
            continue

        seen.add(text)

        result.append(text)

    return result


# ============================================================
# 通用字段读取
# ============================================================

def get_field(value: Any, name: str, default: Any = None) -> Any:
    # 同时支持 dict 和 object.attribute。

    if value is None:
        return default

    if isinstance(value, dict):
        return value.get(name, default)

    if hasattr(value, name):
        return getattr(value, name)

    return default


# ============================================================
# 多字段读取
# ============================================================

def get_first_field(
    value: Any,
    names: List[str],
    default: Any = None,
) -> Any:
    # 按顺序读取第一个存在的字段。

    for name in names:
        result = get_field(value, name, None)

        if result is not None:
            return result

    return default


# ============================================================
# Rule 字段读取
# ============================================================

def get_rule_value(
    rule: Any,
    *names: str,
) -> Any:
    # 从 Rule 中读取字段。
    #
    # 同时兼容：
    #
    #     dict
    #
    #     object.attribute

    if rule is None:
        return None

    for name in names:
        result = get_field(rule, name, None)

        if result is not None:
            return result

    return None


# ============================================================
# Structured Article → Rule
# ============================================================

def normalize_rule(article: Any) -> Dict[str, Any]:
    # 将 Retriever 返回的结构化法律条文
    # 转换成统一 Rule。
    #
    # 兼容字段：
    #
    #     law_name
    #     law
    #     title
    #     article_number
    #     article
    #     article_no
    #     rule_summary
    #     summary
    #     content
    #     text
    #     rule_type
    #     type
    #     conditions
    #     exceptions

    source = {}

    if isinstance(article, dict):
        source = dict(article)

    else:
        for name in [
            "law_name",
            "law",
            "title",
            "article_number",
            "article",
            "article_no",
            "rule_summary",
            "summary",
            "content",
            "text",
            "rule_type",
            "type",
            "conditions",
            "exceptions",
        ]:
            value = get_field(article, name, None)

            if value is not None:
                source[name] = value

    law_name = get_first_field(
        source,
        [
            "law_name",
            "law",
            "title",
        ],
        "",
    )

    article_number = get_first_field(
        source,
        [
            "article_number",
            "article",
            "article_no",
        ],
        "",
    )

    rule_summary = get_first_field(
        source,
        [
            "rule_summary",
            "summary",
            "content",
            "text",
        ],
        "",
    )

    rule_type = get_first_field(
        source,
        [
            "rule_type",
            "type",
        ],
        "",
    )

    conditions = ensure_list(
        source.get("conditions", [])
    )

    exceptions = ensure_list(
        source.get("exceptions", [])
    )

    result = dict(source)

    result["law_name"] = normalize_text(law_name)

    result["article_number"] = normalize_text(
        article_number
    )

    result["rule_summary"] = normalize_text(
        rule_summary
    )

    result["rule_type"] = normalize_text(
        rule_type
    )

    result["conditions"] = conditions

    result["exceptions"] = exceptions

    return result


# ============================================================
# Articles → Rules
# ============================================================

def _article_number_value(article_number: str) -> int:
    """将常见中文/阿拉伯数字法条号转换为整数，用于稳定排序。"""

    text = normalize_text(article_number)

    match = re.search(r"第?([0-9]+)条", text)
    if match:
        try:
            return int(match.group(1))
        except ValueError:
            return 999999

    chinese_digits = {
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
        "十": 10,
        "百": 100,
        "千": 1000,
    }

    match = re.search(r"第([零一二两三四五六七八九十百千万]+)条", text)
    if not match:
        return 999999

    raw = match.group(1)
    if raw.isdigit():
        return int(raw)

    total = 0
    section = 0
    number = 0
    units = {"十": 10, "百": 100, "千": 1000, "万": 10000}

    for ch in raw:
        if ch in units:
            unit = units[ch]
            if number == 0:
                number = 1
            section += number * unit
            number = 0
        else:
            number = chinese_digits.get(ch, 0)

    return section + number


def _rule_text(rule: Dict[str, Any]) -> str:
    """提取 Rule 的可检索文本，不修改原始 Rule。"""

    parts = [
        normalize_text(rule.get("law_name", "")),
        normalize_text(rule.get("article_number", "")),
        normalize_text(rule.get("rule_summary", "")),
        normalize_text(rule.get("rule_type", "")),
        normalize_text(rule.get("conditions", "")),
        normalize_text(rule.get("exceptions", "")),
    ]
    return " ".join(part for part in parts if part)


def _rule_priority(rule: Dict[str, Any], question: str) -> tuple:
    """
    V6.0-13 法律规则相关性排序。

    目标不是删除法律依据，而是把与问题直接对应的核心法条放在前面，
    同时保留例外、法律后果等相关规则。
    """

    q = normalize_text(question)
    text = _rule_text(rule)
    law_name = normalize_text(rule.get("law_name", ""))
    article_number = normalize_text(rule.get("article_number", ""))

    score = 0

    # 劳动合同“连续两次固定期限后无固定期限”问题的核心法条。
    if "固定期限劳动合同" in q:
        if "第十四条" in article_number or "第14条" in article_number:
            score += 100
        if "无固定期限劳动合同" in text:
            score += 80
        if "连续订立二次固定期限劳动合同" in text:
            score += 80

    # 用户问题包含“三次”时，第十四条仍是最直接的法律依据。
    if "三次" in q and ("第十四条" in article_number or "第14条" in article_number):
        score += 40

    # 与签订/续订直接相关的规则优先。
    for keyword, weight in [
        ("订立", 20),
        ("续订", 20),
        ("无固定期限", 30),
        ("固定期限", 20),
        ("劳动合同", 10),
    ]:
        if keyword in text:
            score += weight

    # 法律后果/例外属于相关依据，但不应压过核心法条。
    if "解除" in text or "终止" in text:
        score -= 8
    if "法律责任" in text or "赔偿" in text or "罚款" in text:
        score -= 5

    # 保持原 Retriever 顺序作为最后稳定排序键。
    return (-score, _article_number_value(article_number), law_name, article_number)


def prioritize_legal_rules(
    question: str,
    rules: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    V6.0-13：规则分层排序。

    不删除规则，不改变 Rule 内容，只增加：
        rule_priority = CORE / RELATED
        rule_relevance_score = int

    CORE：直接回答问题的主要法律依据。
    RELATED：例外、法律后果或其他辅助法律依据。
    """

    normalized = build_rules_from_articles(rules)

    if not normalized:
        return []

    result = []

    q = normalize_text(question)

    for rule in normalized:
        item = dict(rule)
        text = _rule_text(item)
        article_number = normalize_text(item.get("article_number", ""))

        priority = 0

        if "固定期限劳动合同" in q:
            if "第十四条" in article_number or "第14条" in article_number:
                priority += 100
            if "无固定期限劳动合同" in text:
                priority += 80
            if "连续订立二次固定期限劳动合同" in text:
                priority += 80

        if "三次" in q and ("第十四条" in article_number or "第14条" in article_number):
            priority += 40

        for keyword, weight in [
            ("订立", 20),
            ("续订", 20),
            ("无固定期限", 30),
            ("固定期限", 20),
            ("劳动合同", 10),
        ]:
            if keyword in text:
                priority += weight

        if "解除" in text or "终止" in text:
            priority -= 8
        if "法律责任" in text or "赔偿" in text or "罚款" in text:
            priority -= 5

        item["rule_relevance_score"] = priority
        item["rule_priority"] = "CORE" if priority >= 100 else "RELATED"
        result.append(item)

    result.sort(key=lambda r: _rule_priority(r, question))
    return result


def build_rules_from_articles(
    articles: Any,
) -> List[Dict[str, Any]]:
    # 将 Retriever Articles 转换成 Rules。
    #
    # 注意：
    # 这里负责的是：
    #
    # Retriever Articles
    #       ↓
    # normalize_rule()
    #       ↓
    # Normalized Rules
    #
    # 不负责：
    # Decision Adapter
    # Ollama
    # Answer Builder
    #
    # 因此这里应该保持“纯 Rules 构建”职责。

    if articles is None:
        return []

    if isinstance(articles, dict):
        articles = [articles]

    if not isinstance(articles, (list, tuple)):
        return []

    rules = []

    seen = set()

    for article in articles:
        rule = normalize_rule(article)

        # --------------------------------------------------------
        # 防止 normalize_rule() 返回空结果
        # --------------------------------------------------------

        if not isinstance(rule, dict) or not rule:
            continue

        law_name = rule.get(
            "law_name",
            "",
        )

        article_number = rule.get(
            "article_number",
            "",
        )

        summary = rule.get(
            "rule_summary",
            "",
        )

        # --------------------------------------------------------
        # 去重
        # --------------------------------------------------------

        key = (
            law_name,
            article_number,
            summary,
        )

        if key in seen:
            continue

        seen.add(key)

        rules.append(rule)

    return rules

# ============================================================
# V6.0-27 Decision Engine Boundary
# ============================================================
#
# V6.0-14 之后，Decision Engine 已经负责完整生成 8 条
# ConditionResult。
#
# RAG 层不得再补充、删除或修改 ConditionResult。
#
# 特别是：
#
#     "存在后续订立的劳动合同"
#
# 已经由 Legal Decision Engine V6.0-14 正式产生。
# RAG 不再使用旧版兼容函数追加该条件。
#
# ============================================================

# ============================================================
# Decision 状态提取
# ============================================================

def extract_engine_decision(
    decision: Any,
) -> str:
    # 提取 Legal Decision Engine 状态。

    value = get_first_field(
        decision,
        [
            "decision",
            "status",
        ],
        "",
    )

    value = normalize_text(value).upper()

    if value in VALID_ENGINE_DECISIONS:
        return value

    # 如果 Decision Engine 没有明确返回状态，
    # 默认按照 CONDITIONAL 处理。
    #
    # 这样比擅自判断为 DEFINITE 更安全。

    return DECISION_CONDITIONAL


# ============================================================
# Condition 字段读取
# ============================================================

def extract_condition_value(
    condition: Any,
    name: str,
) -> Any:
    return get_field(
        condition,
        name,
        None,
    )


# ============================================================
# Fact 文本提取
# ============================================================

def extract_fact_text(
    fact: Any,
) -> str:
    # Fact 可能是字符串，也可能是对象。

    if fact is None:
        return ""

    if isinstance(fact, str):
        return fact.strip()

    value = (
        get_first_field(
            fact,
            [
                "text",
                "value",
                "fact",
                "content",
            ],
            None,
        )
    )

    if value is not None:
        return normalize_text(value)

    return normalize_text(
        safe_text(fact)
    )


# ============================================================
# V6.0-10 Conditional Condition Enrichment
# ============================================================

def enrich_conditional_conditions(
    question: str,
    user_facts: List[str],
    rules: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    V6.0-27：取消 Adapter 层的法律条件推理。

    核心原则：

    1. Legal Decision Engine 是唯一的法律条件判定来源。
    2. Adapter 不得根据问题、用户事实或 Rules 自行创造
       SATISFIED / UNSATISFIED / UNKNOWN 条件。
    3. 特别禁止自动生成“其他法定情形”等笼统 UNKNOWN。
    4. 保留函数只是为了兼容旧接口；V6.0-22 默认返回空列表。
    5. 如果 Engine 返回 CONDITIONAL 但 Condition Results = 0，
       必须由 Engine 本身修复输出，而不是由 Adapter 猜测条件。
    """

    # V6.0-27：故意不进行任何条件补全。
    #
    # 旧版本的问题：
    #     Engine = CONDITIONAL
    #     Condition Results = 0
    #             ↓
    #     Adapter 自行推导条件
    #             ↓
    #     自动制造 UNKNOWN
    #
    # 这会破坏“Decision Engine 是唯一法律判断来源”的架构边界。
    # 因此本函数保留为兼容入口，但不再返回任何法律条件。
    return []


# ============================================================
# Decision Adapter
# ============================================================

def _condition_text(value: Any) -> str:
    """提取单个条件对象的规范文本。"""

    if isinstance(value, dict):
        return normalize_text(
            get_first_field(
                value,
                [
                    "condition",
                    "name",
                    "text",
                    "value",
                ],
                "",
            )
        )

    return normalize_text(value)


def _condition_list_from_rule(
    rules: List[Dict[str, Any]],
    field_names: List[str],
) -> List[str]:
    """从结构化 Rules 中提取条件名称，保持原始顺序并去重。"""

    result = []

    for rule in rules:
        if not isinstance(rule, dict):
            continue

        for field_name in field_names:
            values = ensure_list(rule.get(field_name, []))
            for value in values:
                text = _condition_text(value)
                if text and text not in result:
                    result.append(text)

    return result


def _condition_category_map(
    rules: List[Dict[str, Any]],
) -> Dict[str, str]:
    """
    建立条件名称 → 类别映射。

    类别严格来自 Structured Rules：

        REQUIRED   必备条件
        EXCLUSION  排除条件
        EXCEPTION  例外条件

    不根据自然语言问题自行创造类别。
    """

    mapping = {}

    for condition in _condition_list_from_rule(
        rules,
        ["conditions", "required_conditions"],
    ):
        mapping[condition] = "REQUIRED"

    for condition in _condition_list_from_rule(
        rules,
        ["exclusion_conditions", "exclusions"],
    ):
        mapping[condition] = "EXCLUSION"

    for condition in _condition_list_from_rule(
        rules,
        ["exceptions", "exception_conditions"],
    ):
        mapping[condition] = "EXCEPTION"

    return mapping


def build_fact_condition_mappings(
    question: str,
    user_facts: List[str],
    rules: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    V6.0-27：Fact-to-Condition Mapping + Rule Dependency。

    核心原则：

    1. 用户事实“连续签订三次固定期限劳动合同”可以确定已经达到
       “连续订立二次固定期限劳动合同”的数量门槛。
    2. 该事实不能自动证明未来还会发生“续订劳动合同”。
    3. 不能把“劳动者提出或者同意续订、订立劳动合同”改写成
       “劳动者提出或者同意订立无固定期限劳动合同”。
    4. 排除条件和例外条件必须保持 UNKNOWN，除非用户提供相应事实。
    5. Mapping 只记录事实覆盖关系，不直接修改 Decision Engine 状态。

    这里明确区分三个概念：

        已签订三次固定期限合同
                ↓
        已达到连续订立二次的数量门槛
                ↓
        下一次是否发生续订 / 订立劳动合同
                ↓
        第十四条其它条件是否满足
                ↓
        法律后果

    因此，“三次”绝不能被错误映射为“劳动者已经同意下一次续订”。
    """
    question_text = normalize_text(question)
    facts = unique_texts(user_facts)
    normalized_rules = build_rules_from_articles(rules)

    has_three_contract_fact = (
        "三次" in question_text
        and "固定期限劳动合同" in question_text
    ) or any(
        "三次" in normalize_text(fact)
        and "固定期限劳动合同" in normalize_text(fact)
        for fact in facts
    )

    if not has_three_contract_fact:
        return []

    target_condition = "连续订立二次固定期限劳动合同"

    for rule in normalized_rules:
        conditions = ensure_list(
            get_rule_value(rule, "conditions", "required_conditions")
        )
        for item in conditions:
            if _condition_text(item) == target_condition:
                return [{
                    "fact": "公司连续签订三次固定期限劳动合同",
                    "condition": target_condition,
                    "status": "SATISFIED",
                    "mapping_type": "NUMERIC_THRESHOLD",
                    "dependency": "THREE_CONTRACTS_MEET_TWO_CONTRACT_THRESHOLD",
                    "reason": (
                        "用户明确说明连续签订三次固定期限劳动合同；三次已经达到连续订立二次固定期限劳动合同的最低数量门槛。"
                    ),
                    "does_not_prove": [
                        "续订劳动合同",
                        "劳动者提出或者同意续订、订立劳动合同",
                        "不存在第三十九条规定情形",
                        "不存在第四十条第一项规定情形",
                        "不存在第四十条第二项规定情形",
                        "劳动者未提出订立固定期限劳动合同",
                    ],
                }]

    return []


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


def build_structured_conclusion(
    decision: Any,
    condition_results: List[Dict[str, Any]],
) -> str:
    """
    只把 Decision Engine 已经作出的法律判断
    转换成结构化结论。

    不重新进行法律推理。
    """

    engine_decision = extract_engine_decision(
        decision
    )

    explanation = normalize_text(
        get_field(
            decision,
            "explanation",
            "",
        )
    )

    if engine_decision == DECISION_DEFINITE:
        prefix = (
            "Decision Engine 已确认满足相关法律条件。"
        )

    elif engine_decision == DECISION_NOT_ESTABLISHED:
        prefix = (
            "Decision Engine 已确认当前不能认定满足相关法律条件。"
        )

    else:
        prefix = (
            "Decision Engine 判定当前法律结论为条件性结论。"
        )

    exclusion_triggered = []

    for item in condition_results:
        condition_type = normalize_text(
            item.get(
                "condition_type",
                item.get("type", ""),
            )
        ).upper()

        status = normalize_text(
            item.get("status", "")
        ).upper()

        if (
            condition_type == "EXCLUSION"
            and status == "NOT_SATISFIED"
        ):
            condition = normalize_text(
                item.get("condition", "")
            )

            if condition:
                exclusion_triggered.append(
                    condition
                )

    lines = [prefix]

    if exclusion_triggered:
        lines.append(
            "Decision Engine 已确认以下排除条件触发："
            + "；".join(exclusion_triggered)
            + "。"
        )

    if explanation:
        lines.append(
            "Engine 原始说明："
            + explanation
        )

    return "\n".join(lines)

def adapt_decision_for_answer_builder(
    decision: Any,
    question: str = "",
) -> Dict[str, Any]:
    """
    V6.0-27 Decision Adapter。

    架构边界：

        Legal Decision Engine V6.0-14
                    ↓
              DecisionResult
                    ↓
        Legal Answer Builder V6.0-14
                    ↓
            StructuredAnswer
                    ↓
              RAG presentation

    本函数只负责接口适配，不重新进行法律推理。

    关键要求：

    1. 原始 8 条 ConditionResult 必须全部保留。
    2. REQUIRED / EXCLUSION / EXCEPTION 严格分开。
    3. UNKNOWN 只能来自 Engine 的实际状态。
    4. 不根据问题自行制造 ConditionResult。
    5. 不根据合同次数自行补充法律条件。
    """

    engine_status = extract_engine_decision(decision)

    structured = builder_adapt_decision(
        decision,
        strict=True,
    )

    if hasattr(structured, "to_dict"):
        adapted = structured.to_dict()
    elif isinstance(structured, dict):
        adapted = dict(structured)
    else:
        raise TypeError(
            "Legal Answer Builder 必须返回 StructuredAnswer 或 dict"
        )

    # Engine 状态必须直接来自 DecisionResult。
    adapted["engine_decision"] = engine_status

    # V6.0-27：法律结论锁定。
    #
    # Legal Decision Engine 已经完成法律条件判断。
    # 后续 Answer Builder 和 Ollama 只能表达该结果，
    # 不得重新进行法律推理。
    adapted["engine_decision_locked"] = True
    adapted["engine_decision_source"] = "Legal Decision Engine"

    adapted["engine_decision_source"] = (
        "Legal Decision Engine"
    )

    adapted["engine_explanation"] = normalize_text(
        get_field(
            decision,
            "explanation",
            "",
        )
    )

    adapted["engine_rule_dependencies"] = ensure_list(
        get_field(
            decision,
            "rule_dependencies",
            [],
        )
    )

    if engine_status == DECISION_DEFINITE:
        adapted["decision"] = ANSWER_SATISFIED
    elif engine_status == DECISION_NOT_ESTABLISHED:
        adapted["decision"] = ANSWER_UNSATISFIED
    else:
        adapted["decision"] = ANSWER_CONDITIONAL

    # DecisionResult 的正式字段是 explicit_facts。
    # Builder 已经负责读取该字段。这里仅做旧接口兼容。
    adapted["user_facts"] = unique_texts(
        ensure_list(adapted.get("user_facts", []))
    )

    normalized_rules = build_rules_from_articles(
        ensure_list(
            get_field(decision, "rules", [])
        )
    )

    adapted["fact_condition_mappings"] = build_fact_condition_mappings(
        question=question,
        user_facts=adapted["user_facts"],
        rules=normalized_rules,
    )

    # StructuredAnswer 的 condition_results 是唯一状态来源。
    raw_condition_results = ensure_list(
        adapted.get("condition_results", [])
    )

    required_results = []
    exclusion_results = []
    exception_results = []

    for item in raw_condition_results:
        if not isinstance(item, dict):
            continue

        condition = normalize_text(
            item.get("condition", "")
        )
        if not condition:
            continue

        condition_type = normalize_text(
            item.get(
                "condition_type",
                item.get("type", "REQUIRED"),
            )
        ).upper()

        normalized_item = dict(item)
        normalized_item["condition"] = condition
        normalized_item["status"] = normalize_text(
            item.get("status", ANSWER_UNKNOWN)
        ).upper() or ANSWER_UNKNOWN
        normalized_item["category"] = condition_type

        if condition_type == "EXCLUSION":
            exclusion_results.append(normalized_item)
        elif condition_type == "EXCEPTION":
            exception_results.append(normalized_item)
        else:
            required_results.append(normalized_item)

    # ============================================================
    # Conditions
    # ============================================================

    adapted["condition_results"] = raw_condition_results

    adapted["required_condition_results"] = required_results

    adapted["exclusion_condition_results"] = exclusion_results

    adapted["exception_results"] = exception_results


    # ============================================================
    # Satisfied Conditions
    # ============================================================

    adapted["satisfied_conditions"] = [
        item["condition"]
        for item in required_results
        if item["status"] == ANSWER_SATISFIED
    ]


    # ============================================================
    # Unsatisfied Conditions
    # ============================================================

    adapted["unsatisfied_conditions"] = [
        item["condition"]
        for item in required_results
        if item["status"] in {
            "NOT_SATISFIED",
            ANSWER_UNSATISFIED,
        }
    ]


    # ============================================================
    # Required Unknown Conditions
    #
    # 注意：
    # unknown_conditions 只表示 REQUIRED 条件中的 UNKNOWN。
    # 不包含 EXCLUSION / EXCEPTION。
    # ============================================================

    adapted["unknown_conditions"] = [
        {
            "condition": item["condition"],
            **(
                {"reason": item["reason"]}
                if item.get("reason")
                else {}
            ),
        }
        for item in required_results
        if item["status"] == ANSWER_UNKNOWN
    ]


    # ============================================================
    # All Unknown Conditions
    #
    # 表示全部 8 个法律条件中的 UNKNOWN。
    #
    # REQUIRED    × 4
    # EXCLUSION   × 3
    # EXCEPTION   × 1
    #
    # 注意：
    # 这里不能替代 unknown_conditions。
    # ============================================================

    adapted["all_unknown_conditions"] = [
        {
            "condition": item["condition"],
            "condition_type": item.get(
                "condition_type",
                item.get("type", "REQUIRED"),
            ),
            **(
                {"reason": item["reason"]}
                if item.get("reason")
                else {}
            ),
        }
        for item in raw_condition_results
        if item["status"] == ANSWER_UNKNOWN
    ]
    adapted["engine_condition_results_count"] = len(
        get_field(decision, "condition_results", []) or []
    )
    adapted["engine_output_incomplete"] = (
        engine_status == DECISION_CONDITIONAL
        and adapted["engine_condition_results_count"] != 8
    )

    adapted["conclusion"] = build_structured_conclusion(
        decision=decision,
        condition_results=raw_condition_results,
    )

    adapted["raw_decision"] = decision

    return adapted


# ============================================================
# Rules 合并
# ============================================================

def merge_rules_into_decision(
    adapted_decision: Dict[str, Any],
    rules: List[Dict[str, Any]],
) -> Dict[str, Any]:
    # Decision Engine 可能只返回 selected rules。
    #
    # Answer Builder 需要完整法律依据。
    #
    # 因此：
    #
    #     Decision Rules
    #           +
    #     Retriever Rules
    #
    # 进行合并。

    existing_rules = ensure_list(
        adapted_decision.get(
            "rules",
            [],
        )
    )

    all_rules = (
        existing_rules
        + ensure_list(rules)
    )

    print("\n" + "-" * 70)
    print("DEBUG / all_rules")
    print("-" * 70)
    print("all_rules type:", type(all_rules))
    print("all_rules count:", len(all_rules) if isinstance(all_rules, (list, tuple, dict)) else "N/A")
    print("all_rules:", all_rules)

    adapted_decision["rules"] = (
        build_rules_from_articles(
            all_rules
        )
    )

    print("\n" + "-" * 70)
    print("DEBUG / adapted_decision rules")
    print("-" * 70)
    print("rules type:", type(adapted_decision.get("rules")))
    print("rules count:", len(adapted_decision.get("rules", [])))
    print("rules:", adapted_decision.get("rules"))

    adapted_decision["rules"] = (
        build_rules_from_articles(
            all_rules
        )
    )

    return adapted_decision


# ============================================================
# Structured Context
# ============================================================

def format_rules_for_display(
    rules: List[Dict[str, Any]],
) -> str:
    # 将 Rules 转换为可阅读法律依据。

    if not rules:
        return "当前没有结构化法律规则。"

    lines = []

    seen = set()

    index = 1

    for rule in rules:

        law_name = normalize_text(
            rule.get(
                "law_name",
                "",
            )
        )

        article_number = normalize_text(
            rule.get(
                "article_number",
                "",
            )
        )

        summary = normalize_text(
            rule.get(
                "rule_summary",
                "",
            )
        )

        if law_name and article_number:

            title = (
                f"《{law_name}》"
                f"{article_number}"
            )

        elif law_name:

            title = f"《{law_name}》"

        else:

            title = article_number

        if not title:
            continue

        priority = normalize_text(
            rule.get("rule_priority", "")
        )

        if summary:
            prefix = "[核心依据] " if priority == "CORE" else "[相关依据] "
            text = (
                f"{prefix}{title}："
                f"{summary}"
            )
        else:
            text = title

        if text in seen:
            continue

        seen.add(text)

        lines.append(
            f"{index}. {text}"
        )

        index += 1

    if not lines:
        return "当前没有结构化法律规则。"

    return "\n".join(lines)


# ============================================================
# Retriever
# ============================================================

def build_structured_context(
    question: str,
    top_k: int = 5,
    score_threshold: float = 0.55,
) -> Dict[str, Any]:

    print()
    print("=" * 70)
    print("Step 1 / Retriever")
    print("=" * 70)

    articles = build_context(
        question=question,
        top_k=top_k,
        score_threshold=score_threshold,
        return_articles=True,
    )

    if articles is None:
        articles = []

    if isinstance(articles, str):

        print()
        print(
            "⚠️ Retriever 返回的是字符串，"
            "无法构建 Structured Articles。"
        )

        return {
            "articles": [],
            "rules": [],
            "context": articles,
        }

    rules = build_rules_from_articles(
        articles
    )

    # V6.0-13：不删除 Retriever 结果，只按问题相关性排序。
    # 核心法条优先展示，相关法条继续保留供 Decision Engine 使用。
    rules = prioritize_legal_rules(
        question=question,
        rules=rules,
    )

    context = format_rules_for_display(
        rules
    )

    print()
    print("✅ Retriever 完成")

    print(
        f"Structured Articles：{len(articles)}"
    )

    print(
        f"Normalized Rules：{len(rules)}"
    )

    print(
        f"Context 字符数：{len(context)}"
    )

    return {
        "articles": articles,
        "rules": rules,
        "context": context,
    }


# ============================================================
# Decision Engine
# ============================================================

def run_decision_engine(
    question: str,
    rules: List[Dict[str, Any]],
) -> Any:

    print()
    print("=" * 70)
    print("Step 2 / Legal Decision Engine V6.0-14")
    print("=" * 70)

    print()
    print(
        f"Rules：{len(rules)}"
    )

    try:

        decision = make_decision(
            question=question,
            rules=rules,
        )

    except TypeError:

        # 兼容部分旧版 Decision Engine
        # 可能使用位置参数。

        decision = make_decision(
            question,
            rules,
        )

    status = extract_engine_decision(
        decision
    )

    print()
    print(
        f"Decision：{status}"
    )

    condition_results = ensure_list(
        get_field(
            decision,
            "condition_results",
            [],
        )
    )

    facts = ensure_list(
        get_field(
            decision,
            "explicit_facts",
            get_field(
                decision,
                "facts",
                [],
            ),
        )
    )

    print(
        f"Condition Results："
        f"{len(condition_results)}"
    )

    print(
        f"Explicit Facts："
        f"{len(facts)}"
    )

    return decision

# ============================================================
# Answer Builder
# ============================================================

def run_answer_builder(
    decision: Any,
    rules: List[Dict[str, Any]],
    question: str = "",
) -> Dict[str, Any]:
    """
    Step 3：调用正式 Legal Answer Builder V6.0-14。

    Builder 只读取 DecisionResult，RAG 不再修改 ConditionResult。

    V6.0-27 修复原则：

        1. Engine Decision 是唯一法律决策来源。

        2. Structured Decision 必须直接继承 Engine Decision。

        3. 不允许 Adapter / RAG 根据 ConditionResult
           重新生成法律决策。

        4. ConditionResult 的状态统计必须直接来自
           DecisionResult.condition_results。

        5. UNKNOWN 必须保持 UNKNOWN。

        6. NOT_SATISFIED 必须保持 NOT_SATISFIED。

        7. EXCLUSION 的 NOT_SATISFIED 表示：
               已触发排除条件

           不应被错误理解为：
               REQUIRED 条件不满足

        8. Builder / Adapter 只能做结构化展示，
           不能重新进行法律推理。

    当前 Article 14 条件结构：

        REQUIRED   = 4
        EXCLUSION  = 3
        EXCEPTION  = 1
        TOTAL      = 8

    因此对于：

        3 个 SATISFIED
        4 个 UNKNOWN
        1 个 EXCLUSION NOT_SATISFIED

    Engine Decision 应保持：

        NOT_ESTABLISHED

    Builder 不得把它改成：

        UNSATISFIED
    """

    print()
    print("=" * 70)
    print("Step 3 / Legal Answer Builder V6.0-14")
    print("=" * 70)

    # ========================================================
    # Step 3.1
    # 读取 Engine Decision
    # ========================================================
    #
    # 重要：
    #
    # DecisionResult 是唯一法律决策来源。
    #
    # 这里先从原始 DecisionResult 中读取 decision，
    # 后续所有 Structured Answer 的 Decision
    # 都必须以这个值为准。
    #
    # 不允许：
    #
    #     DecisionResult
    #          ↓
    #     Adapter
    #          ↓
    #     重新解释 Decision
    #
    # 正确流程：
    #
    #     DecisionResult.decision
    #          ↓
    #     Structured Answer.decision
    #
    # ========================================================

    engine_decision = extract_engine_decision(
        decision
    )

    if not engine_decision:
        raise ValueError(
            "Step 3 / Legal Answer Builder："
            "Engine Decision 不能为空。"
        )

    # ========================================================
    # Step 3.2
    # 读取 Engine 原始 ConditionResult
    # ========================================================
    #
    # 注意：
    #
    # 这里读取的是 Engine 原始输出。
    #
    # 不创建新的 ConditionResult。
    # 不修改原始 ConditionResult。
    # 不根据用户问题重新判断 Condition。
    #
    # ========================================================

    engine_condition_results = ensure_list(
        get_field(
            decision,
            "condition_results",
            [],
        )
    )

    if not engine_condition_results:
        raise ValueError(
            "Step 3 / Legal Answer Builder："
            "Engine condition_results 不能为空。"
        )

    # --------------------------------------------------------
    # V6.0-27 ConditionResult 数量保护
    # --------------------------------------------------------
    #
    # 当前 Legal Decision Engine 的固定结构：
    #
    #     REQUIRED   = 4
    #     EXCLUSION  = 3
    #     EXCEPTION  = 1
    #     TOTAL      = 8
    #
    # Builder 不允许发现数量异常后自行“补条件”。
    #
    # 如果 Engine 输出不是 8 条，
    # 应该让问题暴露出来。
    # --------------------------------------------------------

    if len(engine_condition_results) != 8:
        raise ValueError(
            "Step 3 / Legal Answer Builder："
            "Engine ConditionResult 数量错误："
            f"{len(engine_condition_results)} != 8"
        )

    # ========================================================
    # Step 3.3
    # 调用正式 Legal Answer Builder
    # ========================================================
    #
    # 注意：
    #
    # 当前 legal_answer_builder.py 中：
    #
    #     adapt_decision_for_answer_builder()
    #
    # 的正式接口是：
    #
    #     decision
    #     strict
    #
    # 并没有 question 参数。
    #
    # 因此这里不再向 Adapter 传递 question，
    # 避免：
    #
    #     TypeError:
    #     unexpected keyword argument 'question'
    #
    # question 已经用于 Fact → Condition Mapping，
    # 不应该成为 Builder Decision Adapter 的法律推理输入。
    #
    # ========================================================

    adapted = adapt_decision_for_answer_builder(
        decision=decision,
    )

    # --------------------------------------------------------
    # V6.0-27 Fact → Condition Mapping
    # --------------------------------------------------------
    #
    # 注意：
    #
    # Decision Adapter 执行时使用的是 DecisionResult 自带 Rules。
    # 这些 Rules 可能只是 Decision Engine 选中的部分结构，
    # 不一定包含 Retriever 返回的完整条件字段。
    #
    # merge_rules_into_decision() 执行后，
    # adapted["rules"] 已经包含完整 Structured Rules。
    #
    # 因此 Fact → Condition Mapping 必须在 Rules 合并完成后
    # 再建立一次，确保“三次 → 二次”数量门槛映射能够使用
    # 完整 Structured Rules。
    #
    # 这里不会修改任何 ConditionResult。
    # Mapping 只是事实与法律条件之间的显式依赖关系。
    # --------------------------------------------------------

    adapted = merge_rules_into_decision(
        adapted_decision=adapted,
        rules=rules,
    )

    adapted["fact_condition_mappings"] = (
        build_fact_condition_mappings(
            question=question,
            user_facts=ensure_list(
                adapted.get(
                    "user_facts",
                    [],
                )
            ),
            rules=ensure_list(
                adapted.get(
                    "rules",
                    [],
                )
            ),
        )
    )

    # ========================================================
    # Step 3.4
    # 强制 Structured Decision 与 Engine Decision 一致
    # ========================================================
    #
    # 这是本次修复的核心。
    #
    # Builder 不允许重新解释：
    #
    #     NOT_ESTABLISHED
    #
    # 更不能产生：
    #
    #     UNSATISFIED
    #
    # Structured Decision 必须直接来自：
    #
    #     DecisionResult.decision
    #
    # 这里写入的是 adapted 这个结构化副本，
    # 不修改原始 DecisionResult。
    #
    # ========================================================

    adapted["engine_decision"] = engine_decision

    adapted["decision"] = engine_decision

    # ========================================================
    # Step 3.5
    # 保存原始 DecisionResult
    # ========================================================

    adapted["raw_decision"] = decision

    adapted["engine_condition_results_count"] = (
        len(engine_condition_results)
    )

    # ========================================================
    # Step 3.6
    # 直接根据 Engine ConditionResult 统计状态
    # ========================================================
    #
    # 不再相信 Adapter 中可能已经转换过的：
    #
    #     satisfied_conditions
    #     unsatisfied_conditions
    #     unknown_conditions
    #
    # 而是直接读取 Engine 原始 ConditionResult。
    #
    # 这样可以保证：
    #
    #     SATISFIED
    #     UNKNOWN
    #     NOT_SATISFIED
    #
    # 三种状态不会在 Adapter 层被错误转换。
    #
    # ========================================================

    satisfied_conditions = []
    unknown_conditions = []
    not_satisfied_conditions = []

    required_not_satisfied_conditions = []
    triggered_exclusion_conditions = []
    triggered_exception_conditions = []

    required_condition_results = []
    exclusion_condition_results = []
    exception_condition_results = []

    for condition_result in engine_condition_results:

        condition = get_field(
            condition_result,
            "condition",
            "",
        )

        status = get_field(
            condition_result,
            "status",
            "",
        )

        condition_type = get_field(
            condition_result,
            "condition_type",
            "",
        )

        # ----------------------------------------------------
        # 安全转换
        # ----------------------------------------------------

        condition = (
            str(condition).strip()
            if condition is not None
            else ""
        )

        status = (
            str(status).strip()
            if status is not None
            else ""
        )

        condition_type = (
            str(condition_type).strip()
            if condition_type is not None
            else ""
        )

        # ----------------------------------------------------
        # Condition Type
        # ----------------------------------------------------

        if condition_type == "REQUIRED":

            required_condition_results.append(
                condition_result
            )

        elif condition_type == "EXCLUSION":

            exclusion_condition_results.append(
                condition_result
            )

        elif condition_type == "EXCEPTION":

            exception_condition_results.append(
                condition_result
            )

        # ----------------------------------------------------
        # Condition Status
        # ----------------------------------------------------

        if status == "SATISFIED":

            if condition:
                satisfied_conditions.append(
                    condition
                )

        elif status == "UNKNOWN":

            if condition:
                unknown_conditions.append(
                    condition
                )

        elif status == "NOT_SATISFIED":

            if condition:
                not_satisfied_conditions.append(
                    condition
                )

                # --------------------------------------------
                # REQUIRED NOT_SATISFIED
                # --------------------------------------------

                if condition_type == "REQUIRED":

                    required_not_satisfied_conditions.append(
                        condition
                    )

                # --------------------------------------------
                # EXCLUSION NOT_SATISFIED
                #
                # 在 Engine 语义中：
                #
                #     EXCLUSION + NOT_SATISFIED
                #
                # 表示：
                #
                #     排除条件已经被触发。
                #
                # 例如：
                #
                #     劳动者存在第三十九条规定的情形
                #
                # 因此这里必须单独记录，
                # 不能简单归入“未满足必备条件”。
                # --------------------------------------------

                elif condition_type == "EXCLUSION":

                    triggered_exclusion_conditions.append(
                        condition
                    )

                # --------------------------------------------
                # EXCEPTION NOT_SATISFIED
                # --------------------------------------------

                elif condition_type == "EXCEPTION":

                    triggered_exception_conditions.append(
                        condition
                    )

    # ========================================================
    # Step 3.7
    # 去除展示层重复项
    # ========================================================
    #
    # 注意：
    #
    # 这里只处理摘要展示。
    #
    # 不修改 Engine 原始 ConditionResult。
    #
    # ========================================================

    adapted["satisfied_conditions"] = list(
        dict.fromkeys(
            satisfied_conditions
        )
    )

    adapted["unknown_conditions"] = list(
        dict.fromkeys(
            unknown_conditions
        )
    )

    adapted["unsatisfied_conditions"] = list(
        dict.fromkeys(
            not_satisfied_conditions
        )
    )

    adapted["required_not_satisfied_conditions"] = list(
        dict.fromkeys(
            required_not_satisfied_conditions
        )
    )

    adapted["triggered_exclusion_conditions"] = list(
        dict.fromkeys(
            triggered_exclusion_conditions
        )
    )

    adapted["triggered_exception_conditions"] = list(
        dict.fromkeys(
            triggered_exception_conditions
        )
    )

    # ========================================================
    # Step 3.8
    # 保留按类别划分的原始 ConditionResult
    # ========================================================
    #
    # 这些列表只是引用 Engine 已经产生的对象，
    # 不创建新的 ConditionResult。
    #
    # ========================================================

    adapted["required_condition_results"] = (
        required_condition_results
    )

    adapted["exclusion_condition_results"] = (
        exclusion_condition_results
    )

    adapted["exception_results"] = (
        exception_condition_results
    )

    # ============================================================
    # Step 3.9
    # ConditionResult 状态数量完整性校验
    # ============================================================
    #
    # 重要：
    #
    # adapted["satisfied_conditions"]
    # adapted["unknown_conditions"]
    # adapted["unsatisfied_conditions"]
    #
    # 属于用于展示 / 输出的条件列表。
    #
    # 在 Step 3.7 中，这些列表已经进行了去重，因此：
    #
    #     len(adapted["xxx_conditions"])
    #
    # 不能用于验证原始 Engine ConditionResult 的数量。
    #
    # 本步骤必须直接基于：
    #
    #     engine_condition_results
    #
    # 对每一个原始 ConditionResult 的 status 进行统计。
    #
    # 这样才能确保：
    #
    #     SATISFIED
    #   + UNKNOWN
    #   + NOT_SATISFIED
    #   = Engine ConditionResult 总数
    #
    # ============================================================

    satisfied_count = sum(
        1
        for condition_result in engine_condition_results
        if get_field(
            condition_result,
            "status",
            "",
        ) == "SATISFIED"
    )

    unknown_count = sum(
        1
        for condition_result in engine_condition_results
        if get_field(
            condition_result,
            "status",
            "",
        ) == "UNKNOWN"
    )

    not_satisfied_count = sum(
        1
        for condition_result in engine_condition_results
        if get_field(
            condition_result,
            "status",
            "",
        ) == "NOT_SATISFIED"
    )

    if (
        satisfied_count
        + unknown_count
        + not_satisfied_count
        != len(engine_condition_results)
    ):
        raise ValueError(
            "Step 3 / Legal Answer Builder："
            "Condition 状态数量不一致："
            f"SATISFIED={satisfied_count}, "
            f"UNKNOWN={unknown_count}, "
            f"NOT_SATISFIED={not_satisfied_count}, "
            f"TOTAL={len(engine_condition_results)}"
        )

    # ========================================================
    # Step 3.10
    # Decision 一致性检查
    # ========================================================
    #
    # Builder 不重新计算法律 Decision。
    #
    # 这里只检查：
    #
    #     adapted["decision"]
    #
    # 是否仍然等于：
    #
    #     Engine Decision
    #
    # ========================================================

    if (
        adapted.get("decision")
        != engine_decision
    ):
        raise ValueError(
            "Step 3 / Legal Answer Builder："
            "Structured Decision 与 Engine Decision 不一致："
            f"Engine={engine_decision}, "
            f"Structured={adapted.get('decision')}"
        )

    # ========================================================
    # Step 3.11
    # 输出 Structured Answer 摘要
    # ========================================================

    print()
    print("✅ Structured Answer 已生成")

    print(
        f"Engine Decision："
        f"{engine_decision}"
    )

    print(
        f"Structured Decision："
        f"{adapted['decision']}"
    )

    print(
        f"User Facts："
        f"{len(adapted.get('user_facts', []))}"
    )

    print(
        f"Condition Results："
        f"{len(engine_condition_results)}"
    )

    print(
        f"REQUIRED："
        f"{len(required_condition_results)}"
    )

    print(
        f"EXCLUSION："
        f"{len(exclusion_condition_results)}"
    )

    print(
        f"EXCEPTION："
        f"{len(exception_condition_results)}"
    )

    print(
        f"Satisfied Conditions："
        f"{satisfied_count}"
    )

    print(
        f"Unknown Conditions："
        f"{unknown_count}"
    )

    print(
        f"NOT_SATISFIED Conditions："
        f"{not_satisfied_count}"
    )

    print(
        f"Required Not Satisfied："
        f"{len(required_not_satisfied_conditions)}"
    )

    print(
        f"Triggered Exclusions："
        f"{len(triggered_exclusion_conditions)}"
    )

    print(
        f"Triggered Exceptions："
        f"{len(triggered_exception_conditions)}"
    )

    print(
        f"Legal Rules："
        f"{len(adapted.get('rules', []))}"
    )

    return adapted

# ============================================================
# Deterministic Engine State Block
# ============================================================

def build_deterministic_engine_state_block(
    decision: Dict[str, Any],
) -> str:
    """
    RAG V6.0-27
    构建确定性的 Engine 状态块。

    核心原则：

    1. Engine 是唯一法律条件判定来源。
    2. UNKNOWN 必须 1:1 保留。
    3. 已触发 EXCLUSION 必须 1:1 保留。
    4. 已触发 EXCEPTION 必须 1:1 保留。
    5. Ollama 不得修改这些内容。
    """

    def _condition_text(item: Any) -> str:
        """
        从 ConditionResult / dict / 字符串中提取 condition。
        """

        if isinstance(item, dict):
            return str(
                item.get(
                    "condition",
                    item.get(
                        "description",
                        item,
                    ),
                )
            )

        return str(
            getattr(
                item,
                "condition",
                item,
            )
        )

    unknown_conditions = decision.get(
        "unknown_conditions",
        [],
    ) or []

    triggered_exclusion_conditions = decision.get(
        "triggered_exclusion_conditions",
        [],
    ) or []

    triggered_exception_conditions = decision.get(
        "triggered_exception_conditions",
        [],
    ) or []

    engine_decision = decision.get(
        "engine_decision",
        decision.get(
            "decision",
            "UNKNOWN",
        ),
    )

    lines = []

    lines.append(
        "============================================================"
    )
    lines.append(
        "ENGINE DETERMINISTIC STATE"
    )
    lines.append(
        "============================================================"
    )

    lines.append(
        f"Engine Decision：{engine_decision}"
    )

    # --------------------------------------------------------
    # UNKNOWN
    # --------------------------------------------------------

    lines.append("")
    lines.append(
        f"UNKNOWN 条件数量：{len(unknown_conditions)}"
    )

    if unknown_conditions:

        lines.append(
            "【必须逐项保留的 UNKNOWN 条件】"
        )

        for index, condition in enumerate(
            unknown_conditions,
            start=1,
        ):
            lines.append(
                f"{index}. {_condition_text(condition)}"
            )

    else:

        lines.append(
            "无 UNKNOWN 条件。"
        )

    # --------------------------------------------------------
    # Triggered Exclusions
    # --------------------------------------------------------

    lines.append("")
    lines.append(
        f"已触发 EXCLUSION 数量："
        f"{len(triggered_exclusion_conditions)}"
    )

    if triggered_exclusion_conditions:

        lines.append(
            "【已经触发的 EXCLUSION】"
        )

        for index, condition in enumerate(
            triggered_exclusion_conditions,
            start=1,
        ):
            lines.append(
                f"{index}. {_condition_text(condition)}"
            )

    else:

        lines.append(
            "无已经触发的 EXCLUSION。"
        )

    # --------------------------------------------------------
    # Triggered Exceptions
    # --------------------------------------------------------

    lines.append("")
    lines.append(
        f"已触发 EXCEPTION 数量："
        f"{len(triggered_exception_conditions)}"
    )

    if triggered_exception_conditions:

        lines.append(
            "【已经触发的 EXCEPTION】"
        )

        for index, condition in enumerate(
            triggered_exception_conditions,
            start=1,
        ):
            lines.append(
                f"{index}. {_condition_text(condition)}"
            )

    else:

        lines.append(
            "无已经触发的 EXCEPTION。"
        )

    lines.append("")
    lines.append(
        "============================================================"
    )
    lines.append(
        "END ENGINE DETERMINISTIC STATE"
    )
    lines.append(
        "============================================================"
    )

    return "\n".join(lines)

# ============================================================
# Ollama Prompt
# ============================================================

def build_ollama_prompt(
    question: str,
    decision: Dict[str, Any],
) -> str:
    """
    RAG V6.0-27
    Ollama 最终回答 Prompt

    ============================================================
    核心原则
    ============================================================

    1. Legal Decision Engine 是唯一法律条件判定来源。
    2. Ollama 只能解释 Engine 已经形成的 DecisionResult。
    3. Ollama 不得重新进行法律条件判断。
    4. Ollama 不得新增用户事实。
    5. Ollama 不得把 UNKNOWN 推断为 SATISFIED。
    6. Ollama 不得把 UNKNOWN 推断为 NOT_SATISFIED。
    7. Ollama 不得把 SATISFIED 改写成 UNKNOWN。
    8. Ollama 不得把 NOT_SATISFIED 改写成 UNKNOWN。
    9. EXCLUSION / EXCEPTION 中的 NOT_SATISFIED
       表示该排除条件 / 例外条件已经触发。
    10. 最终回答必须保持 Engine Decision 不变。
    11. 法律条文中的列举事项不得自动转换为本案事实。
    12. Engine 只确认概括性事实时，Ollama 必须保持概括性表达。
    """

    from typing import Any, Dict, List

    prompt_parts: List[str] = []

    # ========================================================
    # 基础身份
    # ========================================================

    prompt_parts.append(
        "你是一个法律问答系统中的最终答案生成器。\n"
        "你的职责不是重新进行法律推理，而是严格根据已经由 Legal Decision Engine "
        "计算完成的结构化结果生成自然语言法律回答。\n"
    )

    # ========================================================
    # 用户问题
    # ========================================================

    prompt_parts.append(
        "\n============================================================\n"
        "用户问题\n"
        "============================================================\n"
        f"\n{question}\n"
    )

    # ========================================================
    # Engine Decision
    # ========================================================

    engine_decision = decision.get(
        "engine_decision",
        decision.get("decision", "UNKNOWN"),
    )

    prompt_parts.append(
        "\n============================================================\n"
        "Engine Decision\n"
        "============================================================\n"
        f"\n{engine_decision}\n"
        "\n"
        "【最高优先级规则】\n"
        "以上 Engine Decision 是 Legal Decision Engine 的最终判定结果。\n"
        "你必须原样遵守该 Decision，不得重新计算、修改、覆盖或推翻。\n"
    )

    # ========================================================
    # Decision Semantics
    # ========================================================

    prompt_parts.append(
        "\n============================================================\n"
        "Decision 语义\n"
        "============================================================\n"
        "\n"
        "DEFINITE：\n"
        "表示 Engine 已经确认相关必要条件全部满足，并且不存在已经触发的排除条件或例外条件。\n"
        "\n"
        "CONDITIONAL：\n"
        "表示目前没有已经确认的不满足条件、已经触发的排除条件或已经触发的例外条件，"
        "但仍存在 UNKNOWN 条件，因此当前结论具有条件性。\n"
        "\n"
        "NOT_ESTABLISHED：\n"
        "表示当前不能建立题目所询问的法律义务或法律结论。\n"
        "NOT_ESTABLISHED 不等于“所有 REQUIRED 条件都不满足”。\n"
        "它可能由以下任一情况造成：\n"
        "1. REQUIRED 条件存在 NOT_SATISFIED；\n"
        "2. EXCLUSION 条件存在 NOT_SATISFIED，即排除条件已经触发；\n"
        "3. EXCEPTION 条件存在 NOT_SATISFIED，即例外条件已经触发。\n"
        "\n"
        "因此，生成 NOT_ESTABLISHED 回答时，必须准确指出 Engine 已确认的实际原因，"
        "不得笼统表述为“所有条件均不满足”。\n"
    )

    # ========================================================
    # Decision Statistics
    # ========================================================

    condition_results = decision.get(
        "condition_results",
        decision.get("conditions", []),
    )

    if condition_results is None:
        condition_results = []

    satisfied_conditions = decision.get(
        "satisfied_conditions",
        [],
    ) or []

    unknown_conditions = decision.get(
        "unknown_conditions",
        [],
    ) or []

    not_satisfied_conditions = decision.get(
        "not_satisfied_conditions",
        [],
    ) or []

    required_results = decision.get(
        "required_condition_results",
        [],
    ) or []

    exclusion_results = decision.get(
        "exclusion_condition_results",
        [],
    ) or []

    exception_results = decision.get(
        "exception_results",
        [],
    ) or []

    required_not_satisfied_conditions = decision.get(
        "required_not_satisfied_conditions",
        [],
    ) or []

    triggered_exclusion_conditions = decision.get(
        "triggered_exclusion_conditions",
        [],
    ) or []

    triggered_exception_conditions = decision.get(
        "triggered_exception_conditions",
        [],
    ) or []

    prompt_parts.append(
        "\n============================================================\n"
        "Decision Structure Statistics\n"
        "============================================================\n"
        f"\n"
        f"Condition Results = {len(condition_results)}\n"
        f"REQUIRED = {len(required_results)}\n"
        f"EXCLUSION = {len(exclusion_results)}\n"
        f"EXCEPTION = {len(exception_results)}\n"
        f"SATISFIED Conditions = {len(satisfied_conditions)}\n"
        f"UNKNOWN Conditions = {len(unknown_conditions)}\n"
        f"NOT_SATISFIED Conditions = {len(not_satisfied_conditions)}\n"
        f"Required Not Satisfied = {len(required_not_satisfied_conditions)}\n"
        f"Triggered Exclusions = {len(triggered_exclusion_conditions)}\n"
        f"Triggered Exceptions = {len(triggered_exception_conditions)}\n"
    )

    # ========================================================
    # Decision Categories
    # ========================================================

    def _category_result_text(
        title: str,
        results: List[Any],
    ) -> str:
        """
        将 ConditionResult 分类结果转换为 Prompt 文本。
        """

        lines: List[str] = [
            f"\n--- {title} ---"
        ]

        if not results:
            lines.append("无")
            return "\n".join(lines)

        for index, result in enumerate(results, start=1):

            if isinstance(result, dict):
                condition = result.get(
                    "condition",
                    result.get("description", ""),
                )

                status = result.get(
                    "status",
                    result.get("result", ""),
                )

                category = result.get(
                    "category",
                    "",
                )

                reason = result.get(
                    "reason",
                    "",
                )

            else:
                condition = getattr(
                    result,
                    "condition",
                    "",
                )

                status = getattr(
                    result,
                    "status",
                    "",
                )

                category = getattr(
                    result,
                    "category",
                    "",
                )

                reason = getattr(
                    result,
                    "reason",
                    "",
                )

            lines.append(
                f"{index}. "
                f"category={category}; "
                f"status={status}; "
                f"condition={condition}; "
                f"reason={reason}"
            )

        return "\n".join(lines)

    prompt_parts.append(
        "\n============================================================\n"
        "Condition Results - REQUIRED\n"
        "============================================================\n"
        + _category_result_text(
            "REQUIRED",
            required_results,
        )
    )

    prompt_parts.append(
        "\n============================================================\n"
        "Condition Results - EXCLUSION\n"
        "============================================================\n"
        + _category_result_text(
            "EXCLUSION",
            exclusion_results,
        )
    )

    prompt_parts.append(
        "\n============================================================\n"
        "Condition Results - EXCEPTION\n"
        "============================================================\n"
        + _category_result_text(
            "EXCEPTION",
            exception_results,
        )
    )

    # ========================================================
    # Raw ConditionResult
    # ========================================================

    prompt_parts.append(
        "\n============================================================\n"
        "Raw ConditionResult\n"
        "============================================================\n"
        "\n"
        "以下 ConditionResult 是法律条件状态的最高优先级数据来源。\n"
        "生成最终回答时必须优先依据这些结果。\n"
        "\n"
    )

    for index, result in enumerate(
        condition_results,
        start=1,
    ):

        if isinstance(result, dict):

            condition = result.get(
                "condition",
                result.get("description", ""),
            )

            category = result.get(
                "category",
                "",
            )

            status = result.get(
                "status",
                result.get("result", ""),
            )

            reason = result.get(
                "reason",
                "",
            )

            fact = result.get(
                "fact",
                "",
            )

        else:

            condition = getattr(
                result,
                "condition",
                "",
            )

            category = getattr(
                result,
                "category",
                "",
            )

            status = getattr(
                result,
                "status",
                "",
            )

            reason = getattr(
                result,
                "reason",
                "",
            )

            fact = getattr(
                result,
                "fact",
                "",
            )

        prompt_parts.append(
            f"{index}. "
            f"category={category}; "
            f"status={status}; "
            f"condition={condition}; "
            f"fact={fact}; "
            f"reason={reason}"
        )

    # ========================================================
    # Condition Status Semantics
    # ========================================================

    prompt_parts.append(
        "\n============================================================\n"
        "Condition Status 语义\n"
        "============================================================\n"
        "\n"
        "REQUIRED 条件：\n"
        "1. SATISFIED = 该必备条件已经满足。\n"
        "2. NOT_SATISFIED = 该必备条件没有满足。\n"
        "3. UNKNOWN = 当前信息不足，无法确认该必备条件是否满足。\n"
        "\n"
        "EXCLUSION 条件：\n"
        "1. SATISFIED = 排除条件没有被确认触发。\n"
        "2. NOT_SATISFIED = 排除条件已经触发。\n"
        "3. UNKNOWN = 当前信息不足，无法确认是否触发排除条件。\n"
        "\n"
        "EXCEPTION 条件：\n"
        "1. SATISFIED = 例外条件没有被确认触发。\n"
        "2. NOT_SATISFIED = 例外条件已经触发。\n"
        "3. UNKNOWN = 当前信息不足，无法确认是否触发例外条件。\n"
        "\n"
        "特别重要：\n"
        "EXCLUSION / EXCEPTION 中的 NOT_SATISFIED 不能解释为“该条件不成立”。\n"
        "在本系统的语义中，它表示该排除条件 / 例外条件已经触发。\n"
    )

    # ========================================================
    # User Facts
    # ========================================================

    user_facts = decision.get(
        "user_facts",
        decision.get(
            "explicit_facts",
            [],
        ),
    ) or []

    prompt_parts.append(
        "\n============================================================\n"
        "Engine Explicit Facts\n"
        "============================================================\n"
        "\n"
    )

    if user_facts:

        for index, fact in enumerate(
            user_facts,
            start=1,
        ):
            prompt_parts.append(
                f"{index}. {fact}\n"
            )

    else:
        prompt_parts.append(
            "无。\n"
        )

    # ========================================================
    # User Fact Preservation — Hard Requirement
    # ========================================================

    prompt_parts.append(
        "\n============================================================\n"
        "USER FACT PRESERVATION — HARD REQUIREMENT\n"
        "============================================================\n"
        "\n"
        "Engine Explicit Facts 是已经由 Decision Engine 提取并确认的用户事实。\n"
        "这些事实不是可选参考信息，而是最终答案必须保留的事实数据。\n"
        "\n"
        "【绝对要求】\n"
        "\n"
        "1. Engine Explicit Facts 有多少条，最终【法律分析】中的“用户事实”"
        "就必须明确保留多少条。\n"
        "\n"
        "2. 不得遗漏任何一条 Engine Explicit Fact。\n"
        "\n"
        "3. 不得因为某一用户事实同时对应某一个 ConditionResult，"
        "就省略该用户事实。\n"
        "\n"
        "4. ConditionResult 是法律条件状态数据，"
        "Engine Explicit Facts 是用户事实数据，二者不能相互替代。\n"
        "\n"
        "5. 法律依据中的法条内容不能代替 Engine Explicit Facts。\n"
        "\n"
        "6. Legal Rules 中出现的法律条件不能代替用户事实。\n"
        "\n"
        "7. 用户事实必须在【法律分析】中单独列出，"
        "建议使用“1. 用户事实：”作为明确的小节。\n"
        "\n"
        "8. 用户事实可以进行自然语言等价改写，"
        "但不得改变事实的核心含义。\n"
        "\n"
        "9. 合同次数属于不可改变的事实：\n"
        "“两次”不得改写成“三次”；\n"
        "“三次”不得改写成“两次”。\n"
        "\n"
        "10. 用户已经明确陈述“续签/续订劳动合同”的，"
        "最终答案不得遗漏该续签/续订事实。\n"
        "\n"
        "11. 用户已经明确陈述某一法定情形存在的，"
        "最终答案不得仅保留法律条件名称而删除该用户事实。\n"
        "\n"
        "12. 不得因为某一个事实已经作为 EXCLUSION、EXCEPTION 或 REQUIRED"
        "条件出现，就认为该事实已经被输出而无需再次保留。\n"
        "\n"
        "13. 最终答案中的“用户事实”必须能够逐条对应 Engine Explicit Facts。\n"
        "\n"
        "【事实数量锁定】\n"
        f"Engine Explicit Facts 数量 = {len(user_facts)}\n"
        "\n"
    )

    if user_facts:

        prompt_parts.append(
            "【必须逐条保留的用户事实】\n"
        )

        for index, fact in enumerate(
            user_facts,
            start=1,
        ):
            prompt_parts.append(
                f"USER FACT #{index}：{fact}\n"
            )

        prompt_parts.append(
            "\n"
            "【最终输出要求】\n"
            f"最终【法律分析】必须明确保留以上 {len(user_facts)} 条用户事实。\n"
            "不得遗漏、合并、删除或改变任何一条用户事实。\n"
            "如果某一事实同时属于法律条件，也必须在“用户事实”部分单独保留。\n"
        )

    else:

        prompt_parts.append(
            "当前 Engine Explicit Facts = 0。\n"
            "不得自行创造用户事实。\n"
        )

    # ========================================================
    # User Fact Exact Preservation — Final Hard Lock
    # ========================================================

    prompt_parts.append(
        "\n============================================================\n"
        "USER FACT EXACT PRESERVATION — FINAL HARD LOCK\n"
        "============================================================\n"
        "\n"
        "以下 Engine Explicit Facts 是最终答案中的原始事实集合。\n"
        "最终答案不得对这些事实进行摘要、压缩、筛选或合并。\n"
        "\n"
        "【绝对禁止】\n"
        "\n"
        "1. 禁止把多条用户事实合并成一条。\n"
        "\n"
        "2. 禁止认为某条事实已经出现在 ConditionResult 中，"
        "因此可以不再输出该事实。\n"
        "\n"
        "3. 禁止只输出导致 Decision = NOT_ESTABLISHED 的事实。\n"
        "\n"
        "4. 禁止只输出你认为最重要的用户事实。\n"
        "\n"
        "5. 禁止根据法律依据、法律条件或排除条件重新筛选用户事实。\n"
        "\n"
        "6. 禁止删除“连续签订两次固定期限劳动合同”这一事实。\n"
        "\n"
        "7. 禁止删除“后来又续签了劳动合同”这一事实。\n"
        "\n"
        "8. 如果用户明确陈述某一法定情形存在，该情形才属于用户事实；"
        "如果仅作为 ConditionResult 出现，则只能作为法律条件状态处理，"
        "不得自动转化为用户事实。\n"
        "\n"
        "9. 禁止改变合同次数。\n"
        "“两次”必须保持为“两次”，不得改写为“三次”。\n"
        "\n"
        "10. 禁止把“续签了劳动合同”改写成用户没有明确陈述的"
        "“劳动者提出续签”或者“劳动者同意续签”。\n"
        "\n"
        "11. 禁止把“存在第三十九条规定的情形”扩展成具体第三十九条"
        "情形，除非 Engine Explicit Facts 中已经明确存在该具体事实。\n"
        "\n"
        "【机械保留规则】\n"
        "\n"
        f"Engine Explicit Facts 总数 = {len(user_facts)}。\n"
        f"最终答案必须明确出现 {len(user_facts)} 条用户事实。\n"
        "\n"
        "这里的“明确出现”是指：每一条 Engine Explicit Fact 都必须在"
        "“用户事实”部分单独形成一条事实记录。\n"
        "\n"
        "不能通过其他章节间接表达来代替。\n"
        "不能通过 ConditionResult 间接表达来代替。\n"
        "不能通过法律依据间接表达来代替。\n"
        "不能通过结论间接表达来代替。\n"
        "\n"
    )

    if user_facts:
        prompt_parts.append(
            "【最终用户事实清单——必须逐条输出】\n"
        )

        for index, fact in enumerate(
            user_facts,
            start=1,
        ):
            prompt_parts.append(
                f"FACT #{index}：{fact}\n"
            )

        prompt_parts.append(
            "\n"
            "【输出模板约束】\n"
            "最终【法律分析】必须包含：\n"
            "1. 用户事实：\n"
        )

        for index, fact in enumerate(
            user_facts,
            start=1,
        ):
            prompt_parts.append(
                f"- 用户事实 #{index}：{fact}\n"
            )

        prompt_parts.append(
            "\n"
            "以上事实必须全部保留。\n"
            "之后才能继续输出“已满足条件”“已触发排除条件”"
            "“尚未确认条件”等法律分析内容。\n"
        )

    # ========================================================
    # Fact-Condition Mapping
    # ========================================================

    fact_condition_mappings = decision.get(
        "fact_condition_mappings",
        [],
    ) or []

    prompt_parts.append(
        "\n============================================================\n"
        "Fact → Condition Mapping\n"
        "============================================================\n"
        "\n"
    )

    if fact_condition_mappings:

        for index, mapping in enumerate(
            fact_condition_mappings,
            start=1,
        ):

            if isinstance(mapping, dict):

                fact = mapping.get(
                    "fact",
                    "",
                )

                condition = mapping.get(
                    "condition",
                    "",
                )

                status = mapping.get(
                    "status",
                    "",
                )

            else:

                fact = getattr(
                    mapping,
                    "fact",
                    "",
                )

                condition = getattr(
                    mapping,
                    "condition",
                    "",
                )

                status = getattr(
                    mapping,
                    "status",
                    "",
                )

            prompt_parts.append(
                f"{index}. "
                f"fact={fact}; "
                f"condition={condition}; "
                f"status={status}\n"
            )

    else:

        prompt_parts.append(
            "无。\n"
        )

    # ========================================================
    # Required / Exclusion / Exception Explanation
    # ========================================================

    prompt_parts.append(
        "\n============================================================\n"
        "Decision Explanation\n"
        "============================================================\n"
        "\n"
        "以下内容用于帮助你解释 Engine 的最终判定。\n"
        "不得修改其中已经确定的状态。\n"
        "\n"
        f"已满足条件 = {satisfied_conditions}\n"
        f"尚不确定条件 = {unknown_conditions}\n"
        f"不满足必备条件 = {required_not_satisfied_conditions}\n"
        f"已触发排除条件 = {triggered_exclusion_conditions}\n"
        f"已触发例外条件 = {triggered_exception_conditions}\n"
    )

    # ========================================================
    # Final Output State Integrity
    # ========================================================

    prompt_parts.append(
        "\n============================================================\n"
        "最终输出状态完整性规则\n"
        "============================================================\n"
        "\n"
        "最终回答中的事实和条件状态必须与 Engine 完全一致，不得发生状态逆转。\n"
        "\n"
        "1. Engine = SATISFIED：只能表达为已经满足；不得写成尚未确认、需核实。\n"
        "\n"
        "2. Engine = NOT_SATISFIED：必须保持 NOT_SATISFIED 的原始语义。\n"
        "   对 EXCLUSION / EXCEPTION，必须表达为“已经触发”；不得写成需核实。\n"
        "\n"
        "3. Engine = UNKNOWN：只有 UNKNOWN 才能进入【需要注意】作为待确认事项。\n"
        "\n"
        "4. 已确认的 EXCLUSION 不得在【需要注意】中再次写成待核实。\n"
        "\n"
        "5. 不得把已经确认的事实改写成假设事实。\n"
        "\n"
        "6. 不得使用“如果……”“若……”“假如……”创造 Engine 未提供的反事实场景。\n"
        "\n"
        "7. 不得使用“如……等”“例如……”自行举出用户未提供的具体事实。\n"
        "\n"
        "8. 对第三十九条、第四十条等法定情形，如果 Engine 只确认条文层级，"
        "只能使用 Engine 提供的完整条件名称，不得自行举例具体行为或具体情形。\n"
        "\n"
        "9. 【需要注意】只能列出 Engine 明确标记为 UNKNOWN 的条件，"
        "并且应尽量使用其原始 condition 文本。\n"
        "\n"
        "10. 不得因为法律依据中出现其它条款，就自行添加本案的法律责任、赔偿、"
        "二倍工资等法律后果，除非 Engine explanation / condition result "
        "已经明确要求表达该法律后果，或者用户明确询问该法律后果。\n"
        "\n"
        "11. 法律条文中的列举事项、举例事项、行为类型、事实类型，"
        "除非已经明确出现在用户问题或 Engine Explicit Facts 中，"
        "否则一律不得视为本案用户事实。\n"
    )

    # ========================================================
    # Deterministic Condition Output Mapping
    # ========================================================

    prompt_parts.append(
        "\n============================================================\n"
        "确定性条件输出映射\n"
        "============================================================\n"
        "\n"
        "最终回答必须逐项保持以下 Engine 状态，不得遗漏、合并或改变状态。\n"
        "\n"
        f"SATISFIED 条件数量：{len(satisfied_conditions)}\n"
        f"UNKNOWN 条件数量：{len(unknown_conditions)}\n"
        f"NOT_SATISFIED 条件数量：{len(not_satisfied_conditions)}\n"
        f"已触发 EXCLUSION 数量：{len(triggered_exclusion_conditions)}\n"
        f"已触发 EXCEPTION 数量：{len(triggered_exception_conditions)}\n"
        "\n"
    )

    if unknown_conditions:
        prompt_parts.append(
            "【必须保留的 UNKNOWN 条件】\n"
        )

        for index, condition in enumerate(
            unknown_conditions,
            start=1,
        ):
            if isinstance(condition, dict):
                condition_text = condition.get(
                    "condition",
                    condition.get(
                        "description",
                        str(condition),
                    ),
                )
            else:
                condition_text = getattr(
                    condition,
                    "condition",
                    str(condition),
                )

            prompt_parts.append(
                f"UNKNOWN #{index}：{condition_text}\n"
            )

        prompt_parts.append(
            "\n"
            "强制要求：\n"
            "1. 【需要注意】必须覆盖以上全部 UNKNOWN 条件。\n"
            "2. 不得遗漏任何一个 UNKNOWN 条件。\n"
            "3. 不得增加不属于 UNKNOWN 的条件。\n"
            "4. 不得把 UNKNOWN 改写成已经满足或已经触发。\n"
            "5. 尽量直接使用以上 condition 原文。\n"
        )
    else:
        prompt_parts.append(
            "当前没有 UNKNOWN 条件。\n"
            "【需要注意】不得自行创造待确认事项。\n"
        )

    if triggered_exclusion_conditions:
        prompt_parts.append(
            "\n"
            "【已经触发的 EXCLUSION】\n"
        )

        for index, condition in enumerate(
            triggered_exclusion_conditions,
            start=1,
        ):
            if isinstance(condition, dict):
                condition_text = condition.get(
                    "condition",
                    condition.get(
                        "description",
                        str(condition),
                    ),
                )
            else:
                condition_text = getattr(
                    condition,
                    "condition",
                    str(condition),
                )

            prompt_parts.append(
                f"EXCLUSION #{index}：{condition_text}\n"
            )

        prompt_parts.append(
            "\n"
            "强制要求：\n"
            "1. 以上 EXCLUSION 已经由 Engine 确认触发。\n"
            "2. 最终回答必须明确表达“已经触发”。\n"
            "3. 禁止使用“可能”“可能构成”“或许”“视情况”等不确定表达。\n"
            "4. 禁止把该 EXCLUSION 放入【需要注意】作为 UNKNOWN。\n"
            "5. 禁止要求用户再次确认该 EXCLUSION 是否存在。\n"
            "6. 禁止自行举出该法条下的具体行为或具体案例。\n"
            "7. 如果 EXCLUSION 的 condition 仅为概括性法定情形，"
            "必须保持该概括性表达，不得自行具体化。\n"
        )

    if triggered_exception_conditions:
        prompt_parts.append(
            "\n"
            "【已经触发的 EXCEPTION】\n"
        )

        for index, condition in enumerate(
            triggered_exception_conditions,
            start=1,
        ):
            if isinstance(condition, dict):
                condition_text = condition.get(
                    "condition",
                    condition.get(
                        "description",
                        str(condition),
                    ),
                )
            else:
                condition_text = getattr(
                    condition,
                    "condition",
                    str(condition),
                )

            prompt_parts.append(
                f"EXCEPTION #{index}：{condition_text}\n"
            )

        prompt_parts.append(
            "\n"
            "强制要求：\n"
            "以上 EXCEPTION 已经由 Engine 确认触发。\n"
            "必须表达为已经触发，不得改写为 UNKNOWN。\n"
            "如果 EXCEPTION 的 condition 仅为概括性法定情形，"
            "不得自行具体化其中的行为或事实。\n"
        )

    # ========================================================
    # Anti-Hallucination Rules
    # ========================================================

    prompt_parts.append(
        "\n============================================================\n"
        "事实边界与反幻觉规则\n"
        "============================================================\n"
        "\n"
        "你只能使用以下信息来源：\n"
        "1. 用户问题；\n"
        "2. Engine Explicit Facts；\n"
        "3. Raw ConditionResult；\n"
        "4. Fact → Condition Mapping；\n"
        "5. Engine Decision Explanation；\n"
        "6. 已提供的法律依据。\n"
        "\n"
        "特别说明：Raw ConditionResult 仅用于判断法律条件的状态，"
        "不得作为“用户事实”的来源。\n"
        "\n"
        "其中必须严格区分“本案事实”和“法律规则”。\n"
        "\n"
        "【本案事实的唯一来源】\n"
        "【用户事实与 ConditionResult 绝对隔离规则】\n"
        "\n"
        "这是最高优先级的事实边界规则：\n"
        "\n"
        "1. 只有 Engine Explicit Facts 中列出的内容，才能标记为“用户事实”。\n"
        "2. Raw ConditionResult 中的 condition、fact、reason、status、condition_type、type 等字段，"
        "无论内容是什么、无论状态是 SATISFIED、UNKNOWN 还是 NOT_SATISFIED，"
        "都不得自动转换为用户事实。\n"
        "3. ConditionResult 中出现“劳动者存在某种情形”的句子，"
        "仍然只是法律条件，不代表用户已经陈述该事实。\n"
        "4. UNKNOWN 的 ConditionResult 特别禁止称为“用户事实”。\n"
        "5. EXCLUSION 或 EXCEPTION 类型的 ConditionResult，"
        "除非同一事实已经明确存在于 Engine Explicit Facts 中，否则不得称为用户事实。\n"
        "6. “Engine 已确认条件”不等于“Engine 已确认用户事实”。\n"
        "7. “ConditionResult 已确认”只表示该条件的状态已经由 Engine 确定，"
        "不表示该条件对应的事实已经发生。\n"
        "8. 最终答案中出现“用户事实”四个字时，"
        "其后的每一条内容必须能够逐字对应 Engine Explicit Facts 中的一项。\n"
        "\n"
        "当前 Engine Explicit Facts 是唯一允许用于构建“用户事实”列表的数据源。\n"
        "【最终输出事实硬约束】\n"
        "最终答案中的“用户事实”只能来自 Engine Explicit Facts。\n"
        "本次 Engine Explicit Facts 只有以下事实：\n"
        f"{chr(10).join('- ' + str(fact) for fact in user_facts)}\n"
        "\n"
        "最终答案中的“用户事实”必须严格等于上述事实集合。\n"
        "不得从 ConditionResult 新增任何用户事实。\n"
        "不得把 UNKNOWN 条件写成用户事实。\n"
        "不得把 EXCLUSION 条件写成用户事实。\n"
        "不得把 EXCEPTION 条件写成用户事实。\n"
        "不得把 Legal Rules 中的法律条件写成用户事实。\n"
        "不得把法律条文中的列举事项写成用户已经发生的事实。\n"
        "如果某项内容不在上述 Engine Explicit Facts 中，即使它出现在 ConditionResult、"
        "Legal Rules、法律条文或分析说明中，也不得标记为“用户事实”。\n"
        "\n"
        "【UNKNOWN 语义绝对锁定】\n"
        "UNKNOWN 不等于 NOT_SATISFIED。\n"
        "UNKNOWN 不等于条件未满足。\n"
        "UNKNOWN 不等于条件已经触发。\n"
        "UNKNOWN 只能表达为当前事实不足以确认该条件是否成立或是否触发。\n"
        "不得使用“条件未满足”“已经不成立”“已经不存在”等表述替代 UNKNOWN。\n"
        "\n"
        "【CONDITIONAL 输出措辞锁定】\n"
        "当 Engine Decision = CONDITIONAL 时，禁止写“当前条件尚未满足”。\n"
        "禁止写“条件未满足”。\n"
        "禁止写“条件不成立”。\n"
        "禁止写“已经不满足”。\n"
        "禁止将 UNKNOWN 描述为 NOT_SATISFIED。\n"
        "必须明确表达为：当前存在尚未确认的条件，"
        "因此暂时不能作出确定性结论。\n"
        "\n"
        "Raw ConditionResult 只用于判断法律条件状态，"
        "不得因为 ConditionResult 中存在 fact、condition 或其它文字，"
        "就将其自动视为用户事实。\n"
        "\n"
        "Engine 已确认的 SATISFIED / UNKNOWN / NOT_SATISFIED 状态，"
        "属于法律条件状态，不属于用户事实来源。\n"
        "\n"
        "【法律规则不是本案事实】\n"
        "Legal Rules 中出现的法条内容、法律定义、法律列举、行为类型、"
        "举例事项和法律后果，仅属于法律规则信息。\n"
        "不得因为这些内容出现在 Legal Rules 中，就认为用户已经发生这些行为。\n"
        "\n"
        "严禁：\n"
        "1. 新增用户没有说过的事实；\n"
        "2. 根据法律条文自行推测具体行为；\n"
        "3. 根据某一法条自行举出具体案例；\n"
        "4. 将法律条文中的示例当成本案事实；\n"
        "5. 将法律条文中的列举行为当成本案已经发生的行为；\n"
        "6. 将 UNKNOWN 推断为 SATISFIED；\n"
        "7. 将 UNKNOWN 推断为 NOT_SATISFIED；\n"
        "8. 将 SATISFIED 改写为 UNKNOWN；\n"
        "9. 将 NOT_SATISFIED 改写为 UNKNOWN；\n"
        "10. 自行添加反事实条件；\n"
        "11. 自行添加用户没有询问的法律责任后果；\n"
        "12. 将概括性的 Engine 条件自动具体化为某一种具体行为。\n"
        "\n"
        "特别禁止：\n"
        "如果用户只提供“存在《劳动合同法》第三十九条规定的情形”，"
        "且 Engine 只确认“劳动者存在《劳动合同法》第三十九条规定的情形”，\n"
        "则最终回答只能保持这一概括性表达。\n"
        "\n"
        "禁止自行扩展为：\n"
        "“严重违反规章制度”；\n"
        "“严重失职”；\n"
        "“营私舞弊”；\n"
        "“被依法追究刑事责任”；\n"
        "或者第三十九条规定的其它具体行为。\n"
        "\n"
        "除非上述具体事实明确出现在用户问题或 Engine Explicit Facts 中。\n"
        "Raw ConditionResult 只能用于判断法律条件状态，"
        "不得作为用户事实来源。\n"
    )

    # ========================================================
    # UNKNOWN Rules
    # ========================================================

    prompt_parts.append(
        "\n============================================================\n"
        "UNKNOWN 条件处理规则\n"
        "============================================================\n"
        "\n"
        "UNKNOWN 表示当前资料不足，不能确认该条件是否成立。\n"
        "\n"
        "UNKNOWN 不等于 SATISFIED。\n"
        "UNKNOWN 不等于 NOT_SATISFIED。\n"
        "\n"
        "因此：\n"
        "1. 不得自行补充 UNKNOWN 条件的事实；\n"
        "2. 不得自行推断 UNKNOWN 条件已经满足；\n"
        "3. 不得自行推断 UNKNOWN 条件已经触发；\n"
        "4. 可以在【需要注意】中指出这些条件尚未确认；\n"
        "5. 必须尽量使用 Engine 给出的原始 condition 文本。\n"
    )

    # ========================================================
    # NOT_ESTABLISHED Rules
    # ========================================================

    prompt_parts.append(
        "\n============================================================\n"
        "NOT_ESTABLISHED 特别规则\n"
        "============================================================\n"
        "\n"
        "当 Engine Decision = NOT_ESTABLISHED 时：\n"
        "\n"
        "1. 不得写成“所有条件均不满足”。\n"
        "\n"
        "2. 不得写成“所有 REQUIRED 条件均不满足”，除非 Engine 明确显示所有 REQUIRED 条件均为 NOT_SATISFIED。\n"
        "\n"
        "3. 必须指出造成 NOT_ESTABLISHED 的已确认原因。\n"
        "\n"
        "4. 如果存在 REQUIRED + NOT_SATISFIED，说明相应必备条件没有满足。\n"
        "\n"
        "5. 如果存在 EXCLUSION + NOT_SATISFIED，必须说明相应排除条件已经触发。\n"
        "\n"
        "6. 如果存在 EXCEPTION + NOT_SATISFIED，必须说明相应例外条件已经触发。\n"
        "\n"
        "7. 必须区分 SATISFIED、NOT_SATISFIED 和 UNKNOWN。\n"
        "\n"
        "8. UNKNOWN 必须继续保持 UNKNOWN。\n"
        "\n"
        "9. 如果 Required Not Satisfied = 0，"
        "但 Triggered Exclusions > 0，则不要说“必备条件没有满足”，"
        "而应以“排除条件已经触发”为当前不能建立法律义务的直接原因。\n"
        "\n"
        "10. 如果 Triggered Exceptions > 0，"
        "则应以“例外条件已经触发”为当前不能建立法律义务的直接原因。\n"
    )

    # ========================================================
    # Legal Rules
    # ========================================================

    legal_rules = decision.get(
        "legal_rules",
        decision.get(
            "rules",
            [],
        ),
    ) or []

    prompt_parts.append(
        "\n============================================================\n"
        "Legal Rules\n"
        "============================================================\n"
        "\n"
    )

    if legal_rules:
        for index, rule in enumerate(
            legal_rules,
            start=1,
        ):

            if isinstance(rule, dict):

                law_name = rule.get(
                    "law_name",
                    rule.get(
                        "law",
                        rule.get(
                            "title",
                            "",
                        ),
                    ),
                )

                article_number = rule.get(
                    "article_number",
                    rule.get(
                        "article",
                        rule.get(
                            "article_no",
                            "",
                        ),
                    ),
                )

                rule_summary = rule.get(
                    "rule_summary",
                    rule.get(
                        "summary",
                        rule.get(
                            "content",
                            rule.get(
                                "text",
                                "",
                            ),
                        ),
                    ),
                )

            else:

                law_name = getattr(
                    rule,
                    "law_name",
                    getattr(
                        rule,
                        "law",
                        getattr(
                            rule,
                            "title",
                            "",
                        ),
                    ),
                )

                article_number = getattr(
                    rule,
                    "article_number",
                    getattr(
                        rule,
                        "article",
                        getattr(
                            rule,
                            "article_no",
                            "",
                        ),
                    ),
                )

                rule_summary = getattr(
                    rule,
                    "rule_summary",
                    getattr(
                        rule,
                        "summary",
                        getattr(
                            rule,
                            "content",
                            getattr(
                                rule,
                                "text",
                                "",
                            ),
                        ),
                    ),
                )

            prompt_parts.append(
                f"{index}. "
                f"law_name={law_name}; "
                f"article_number={article_number}; "
                f"rule_summary={rule_summary}\n"
            )

    else:

        prompt_parts.append(
            "无。\n"
        )

    # ========================================================
    # Legal Rules Usage Boundary
    # ========================================================

    prompt_parts.append(
        "\n============================================================\n"
        "Legal Rules 使用边界\n"
        "============================================================\n"
        "\n"
        "Legal Rules 只能用于解释 Engine 已经作出的条件判断。\n"
        "\n"
        "Legal Rules 是法律依据，不是用户事实数据库。\n"
        "\n"
        "【核心法律依据规则】\n"
        "Legal Rules 中的 rule_priority = CORE 表示该规则是直接回答当前问题的主要法律依据。\n"
        "Legal Rules 中的 rule_priority = RELATED 表示该规则属于相关、辅助、"
        "例外、法律后果或其他补充法律依据。\n"
        "\n"
        "当 Legal Rules 同时存在 CORE 和 RELATED 规则时，"
        "应当理解为 CORE 规则优先，RELATED 规则作为补充。\n"
        "\n"
        "如果 CORE 规则中存在 importance = CRITICAL、"
        "classification = 核心法条或 structured_rule = True 的规则，"
        "该规则具有更高的核心法律依据优先级。\n"
        "\n"
        "RELATED 规则不得因为其内容涉及排除条件、例外条件、法律后果或其他辅助事项，"
        "而取代 CORE 规则成为主要法律依据。\n"
        "\n"
        "如果某一 RELATED 规则只是 CORE 规则所引用的排除条件或辅助规定，"
        "应当将其理解为 CORE 规则的辅助法律依据，"
        "不得将该 RELATED 规则解释为取代 CORE 规则的主要法律依据。\n"
        "\n"
        "【最终法律依据输出边界】\n"
        "最终答案中的“【法律依据】”由 Python 根据当前 Structured Rules "
        "和 rule_priority 确定性生成。\n"
        "Ollama 不得自行重新选择、替换、删除或增加最终法律依据。\n"
        "\n"
        "Ollama 可以对已经提供的 CORE 和 RELATED 法律依据进行解释，"
        "但不得根据自己的法律知识重新检索、补充或替换法律条文。\n"
        "\n"
        "不得因为某一 RELATED 规则涉及排除条件、例外条件或法律后果，"
        "就将该规则排列在 CORE 规则之前。\n"
        "\n"
        "【法律规则与用户事实严格分离】\n"
        "法律规则中的具体行为、具体情形、排除条件、例外条件和法律后果，"
        "均属于法律规则内容，不属于用户事实。\n"
        "\n"
        "即使 Legal Rules 中完整列出了某一法条的多个具体行为、"
        "具体情形或法律后果，也不得因此认定本案已经发生这些行为或情形。\n"
        "\n"
        "只有当某一具体行为已经明确出现在用户问题或 "
        "Engine Explicit Facts 中时，"
        "才可以在最终回答中将该具体行为作为本案用户事实进行表述。\n"
        "\n"
        "Raw ConditionResult 不属于用户事实来源。\n"
        "\n"
        "【条件表述边界】\n"
        "如果 Engine 的 condition 仅为概括性表述，"
        "最终回答必须继续使用概括性表述，"
        "不得根据 Legal Rules 自行扩展为更加具体的事实。\n"
        "\n"
        "不得因为检索结果中存在其它法律条文，"
        "就自行扩大 Engine 已经作出的法律判断。\n"
        "\n"
        "尤其不得仅因为检索到了某个责任条款，"
        "就在最终回答中自行增加二倍工资、赔偿、违约责任、解除责任等法律后果。\n"
        "\n"
        "如果用户没有询问法律责任后果，且 Engine 没有明确要求表达该后果，"
        "不要主动展开责任后果。\n"
    )

    # ========================================================
    # Final Output Format
    # ========================================================

    prompt_parts.append(
        "\n============================================================\n"
        "最终回答格式\n"
        "============================================================\n"
        "\n"
        "最终回答必须严格使用以下四个标题：\n"
        "\n"
        "【结论】\n"
        "【法律依据】\n"
        "【法律分析】\n"
        "【需要注意】\n"
        "\n"
        "不得增加第五个标题。\n"
        "\n"
        "【结论】：\n"
        "只表达 Engine Decision 及其已经确认的直接原因。\n"
        "如果存在 EXCLUSION + NOT_SATISFIED，"
        "必须明确说明该排除条件已经触发。\n"
        "不得加入反事实、假设或用户未提供的具体情形。\n"
        "\n"
        "【法律依据】：\n"
        "只引用已经提供且与当前 Engine Decision 直接相关的法律依据。\n"
        "法律依据中的具体列举事项不得自动转换为本案事实。\n"
        "不得借助其它法律条文自行扩展新的法律后果。\n"
        "\n"
        "【法律分析】：\n"
        "只解释已经存在的 ConditionResult。\n"
        "不得将 NOT_SATISFIED 改成 UNKNOWN。\n"
        "不得将 UNKNOWN 改成确定状态。\n"
        "不得自行举例。\n"
        "不得把法律条文中的具体行为写成用户已经实施的具体行为，"
        "除非该行为已经明确存在于 Engine 事实数据中。\n"
        "\n"
        "【需要注意】：\n"
        "只能列出 UNKNOWN 条件。\n"
        "已经 SATISFIED 的条件不得写入这里。\n"
        "已经触发的 EXCLUSION / EXCEPTION 不得写入这里。\n"
        "不得把已经确认的排除条件再次写成“需要核实”。\n"
    )

    # ========================================================
    # Deterministic Engine State
    # ========================================================

    deterministic_state = (
        build_deterministic_engine_state_block(
            decision
        )
    )

    prompt_parts.append(
        "\n"
        + deterministic_state
        + "\n"
    )

    # ========================================================
    # Final Generation Rules
    # ========================================================

    prompt_parts.append(
        "\n============================================================\n"
        "最终生成要求\n"
        "============================================================\n"
        "\n"
        "现在请根据以上 Engine 数据生成最终法律回答。\n"
        "\n"
        "【最终事实边界锁定】\n"
        "在生成最终回答前，必须执行以下规则：\n"
        "\n"
        "1. 先读取用户问题和 Engine Explicit Facts，确定本案事实。\n"
        "2. 再读取 Raw ConditionResult，确定每个条件的状态。\n"
        "3. Legal Rules 只用于提供法律依据，不得用来补充本案事实。\n"
        "4. 如果用户事实或 Engine 条件只有概括性表述，必须保持概括性。\n"
        "5. 不得从法条列举内容中挑选一个具体行为作为本案事实。\n"
        "6. 不得为了使回答更具体而自行补充事实。\n"
        "7. 不得把法律条文中的例子、列举、定义转换成用户已经发生的事实。\n"
        "8. 不得使用 Engine 没有提供的具体行为证明已经发生了某种事实。\n"
        "\n"
        "【当前系统的强制事实映射原则】\n"
        "用户事实 = Engine 明确确认的事实。\n"
        "法律规则 = 法律规则。\n"
        "二者不得混合。\n"
        "\n"
        "【最终用户事实数量硬锁定】\n"
        f"Engine Explicit Facts 数量 = {len(user_facts)}。\n"
        f"最终答案中的“用户事实”必须明确输出 {len(user_facts)} 条。\n"
        "每一条 Engine Explicit Fact 都必须单独出现。\n"
        "不得合并、摘要、筛选、删除或隐含表达。\n"
        "导致 NOT_ESTABLISHED 的事实，也不得因此成为唯一输出的用户事实。\n"
        "\n"
        "【用户事实逐条保留规则】\n"
        f"Engine Explicit Facts 数量 = {len(user_facts)}。\n"
        f"最终【法律分析】中的“用户事实”必须明确保留 {len(user_facts)} 条。\n"
        "每一条都必须能够对应 Engine Explicit Facts 中的一条事实。\n"
        "不得因为该事实已经出现在 ConditionResult、EXCLUSION、"
        "REQUIRED 或其它结构中，就省略用户事实本身。\n"
        "不得只输出某一个最重要的用户事实。\n"
        "不得只输出导致 NOT_ESTABLISHED 的事实。\n"
        "必须完整保留全部用户事实。\n"
        "\n"
        "例如，如果 Engine 仅确认：\n"
        "“劳动者存在《劳动合同法》第三十九条规定的情形”\n"
        "\n"
        "则允许：\n"
        "“劳动者存在《劳动合同法》第三十九条规定的情形，"
        "该排除条件已经触发。”\n"
        "\n"
        "但禁止：\n"
        "“劳动者严重违反用人单位规章制度。”\n"
        "“劳动者严重失职。”\n"
        "“劳动者被依法追究刑事责任。”\n"
        "以及其它未经 Engine 确认的第三十九条具体行为。\n"
        "\n"
        "再次强调：\n"
        "Engine Decision 是最终法律判定，不允许修改。\n"
        "ConditionResult 是条件状态的最高优先级来源。\n"
        "不得自行重新推理。\n"
        "不得新增事实。\n"
        "不得自行举例。\n"
        "不得创造反事实。\n"
        "不得改变 SATISFIED / NOT_SATISFIED / UNKNOWN 的状态。\n"
        "EXCLUSION / EXCEPTION 的 NOT_SATISFIED 表示已经触发。\n"
        "【需要注意】只能写 UNKNOWN。\n"
        "法律条文中的具体列举事项不得自动成为本案事实。\n"
        "\n"
                "\n"
        "============================================================\n"
        "最终状态锁定\n"
        "============================================================\n"
        "\n"
        "下面的 ENGINE DETERMINISTIC STATE 是 Python 根据 Legal Decision Engine "
        "直接生成的确定性状态数据。\n"
        "\n"
        "这是最终答案中的不可修改数据。\n"
        "\n"
        "【绝对禁止】\n"
        "1. 不得增加 UNKNOWN 条件。\n"
        "2. 不得删除 UNKNOWN 条件。\n"
        "3. 不得合并 UNKNOWN 条件。\n"
        "4. 不得拆分 UNKNOWN 条件。\n"
        "5. 不得改变 UNKNOWN 条件的原文含义。\n"
        "6. 不得把 UNKNOWN 改成 SATISFIED。\n"
        "7. 不得把 UNKNOWN 改成 NOT_SATISFIED。\n"
        "8. 不得把已经触发的 EXCLUSION 改成 UNKNOWN。\n"
        "9. 不得把已经触发的 EXCEPTION 改成 UNKNOWN。\n"
        "10. 不得从 Legal Rules 增加新的 UNKNOWN 条件。\n"
        "11. 不得使用“其他可能影响……”等 Engine 没有提供的条件。\n"
        "\n"
        "【UNKNOWN 一一对应规则】\n"
        "如果 ENGINE DETERMINISTIC STATE 显示 UNKNOWN 条件数量为 N，\n"
        "则最终【需要注意】必须恰好列出 N 项。\n"
        "\n"
        "每一项必须对应 ENGINE DETERMINISTIC STATE 中的一项 UNKNOWN。\n"
        "\n"
        "不得合并，例如：\n"
        "“第四十条第一项、第二项规定的情形”\n"
        "不能代替两个独立的 UNKNOWN 条件。\n"
        "\n"
        "不得概括，例如：\n"
        "“其他可能影响劳动合同续订的情形”\n"
        "不得作为 UNKNOWN。\n"
        "\n"
        "【EXCLUSION 一一对应规则】\n"
        "已经触发的 EXCLUSION 必须明确表达为“已经触发”。\n"
        "禁止使用：\n"
        "“可能”\n"
        "“可能构成”\n"
        "“或许”\n"
        "“视情况而定”\n"
        "\n"
        "【事实具体化禁止】\n"
        "如果 ENGINE DETERMINISTIC STATE 中只有：\n"
        "“劳动者存在《劳动合同法》第三十九条规定的情形”\n"
        "\n"
        "则最终回答只能使用该概括性事实。\n"
        "\n"
        "不得根据 Legal Rules 中的第三十九条、第四十条或者实施条例中的列举内容，"
        "自行选择具体行为作为本案事实。\n"
        "\n"
        "特别禁止把：\n"
        "“劳动者存在《劳动合同法》第三十九条规定的情形”\n"
        "扩展成：\n"
        "“严重违反规章制度”\n"
        "“严重失职”\n"
        "“营私舞弊”\n"
        "“被依法追究刑事责任”\n"
        "或者其它具体行为。\n"
        "\n"
        "这些具体行为只有在用户问题或者 Engine Explicit Facts 明确出现时才允许使用。\n"
        "\n"
        "请直接输出最终法律回答，不要解释你的生成过程。\n"
    )

    return "".join(prompt_parts)


# ============================================================
# Ollama
# ============================================================

def call_ollama(
    prompt: str,
    model: str = OLLAMA_MODEL,
) -> str:

    # V6.0-13：Step 4 日志由 answer_question() 统一输出。
    # call_ollama() 只负责 HTTP 调用，避免重复打印 Step 4。

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.05,
            "top_p": 0.8,
        },
    }

    response = requests.post(
        OLLAMA_URL,
        json=payload,
        timeout=300,
    )

    response.raise_for_status()

    data = response.json()

    answer = data.get(
        "response",
        "",
    )

    return clean_answer(answer)


# ============================================================
# 清理 Ollama 输出
# ============================================================

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


# ============================================================
# 删除重复 Section
# ============================================================

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


# ============================================================
# 最终结构验证
# ============================================================

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


# ============================================================
# 用户事实验证
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

# ============================================================
# 验证 Ollama 的答案是否严格遵守 Legal Decision Engine 已经产生的法律判断。
# ============================================================

def validate_decision_consistency(
    answer: str,
    decision: Dict[str, Any],
) -> bool:
    """
    V6.0-27
    Decision Consistency Validation

    功能：
    ------------------------------------------------------------
    验证 Ollama 最终答案是否严格遵守 Legal Decision Engine
    已经产生的法律判断。

    核心原则：
    ------------------------------------------------------------
    1. Legal Decision Engine 是唯一法律判断来源。
    2. Ollama 只能表达 Engine 的判断，不得重新推理。
    3. 最终答案不得把 Engine 的 DEFINITE 改写成 CONDITIONAL。
    4. 最终答案不得把 Engine 的 NOT_ESTABLISHED 改写成
       “无法确定”“需要进一步确认”等模糊 CONDITIONAL。
    5. 已经 SATISFIED 的排除条件，不得被 Ollama 表达为
       “不影响法律义务”“尚未确认”“可能存在”等相反含义。
    6. 已经 SATISFIED 的条件，不得被 Ollama 否定。
    7. 已经 UNSATISFIED 的条件，不得被 Ollama 表达为已经满足。
    """

    answer_text = normalize_text(answer)

    # ============================================================
    # 1. 提取 Engine Decision
    # ============================================================

    engine_decision = safe_text(
        decision.get("decision", "")
    ).upper().strip()

    # 如果 Decision Engine 没有返回明确状态，
    # 不进行强制判断，避免 Validator 自己制造法律结论。
    if not engine_decision:
        return True

    # ============================================================
    # 2. 提取 Structured Decision 状态
    # ============================================================

    answer_state = safe_text(
        decision.get("answer_state", "")
    ).upper().strip()

    # ============================================================
    # 3. 提取 Condition Results
    # ============================================================

    condition_results = decision.get(
        "condition_results",
        [],
    )

    if not isinstance(condition_results, list):
        condition_results = []

    # ============================================================
    # 4. 分类已经确认的条件
    # ============================================================

    satisfied_conditions: List[str] = []
    unsatisfied_conditions: List[str] = []
    unknown_conditions: List[str] = []

    for item in condition_results:

        if not isinstance(item, dict):
            continue

        condition = safe_text(
            item.get("condition", "")
        ).strip()

        status = safe_text(
            item.get("status", "")
        ).upper().strip()

        if not condition:
            continue

        if status == "SATISFIED":
            satisfied_conditions.append(condition)

        elif status == "UNSATISFIED":
            unsatisfied_conditions.append(condition)

        elif status == "UNKNOWN":
            unknown_conditions.append(condition)

    # ============================================================
    # 5. Engine = DEFINITE
    # ============================================================

    if engine_decision == "DEFINITE":

        # 如果 Engine 已经明确认定，
        # Ollama 不得重新输出“无法确定”“需要进一步确认”等。
        conditional_patterns = [
            "无法确定",
            "尚不能确定",
            "不能确定",
            "仍需确认",
            "需要进一步确认",
            "需进一步确认",
            "有待确认",
            "尚待确认",
            "可能需要",
            "是否必须尚不明确",
        ]

        for pattern in conditional_patterns:
            if pattern in answer_text:
                print(
                    f"❌ Decision Consistency："
                    f"Engine=DEFINITE，但最终答案出现条件性表述："
                    f"{pattern}"
                )
                return False

    # ============================================================
    # 6. Engine = CONDITIONAL
    # ============================================================

    elif engine_decision == "CONDITIONAL":

        # CONDITIONAL 不能被 Ollama 改写成绝对结论。
        definite_patterns = [
            "必须签订无固定期限劳动合同",
            "当然必须签订无固定期限劳动合同",
            "一定必须签订无固定期限劳动合同",
            "已经确定必须签订无固定期限劳动合同",
            "无需进一步判断",
            "已经满足全部条件",
            "全部条件均已满足",
        ]

        for pattern in definite_patterns:

            # 注意：
            # “如果……则必须签订……”属于条件表达，
            # 不能简单因为出现“必须签订”就判错。
            #
            # 因此这里只拦截明显绝对化表达。
            if pattern in answer_text:

                conditional_markers = [
                    "如果",
                    "若",
                    "在……情况下",
                    "在满足",
                    "前提是",
                    "只有",
                    "需同时满足",
                ]

                has_conditional_marker = any(
                    marker in answer_text
                    for marker in conditional_markers
                )

                if not has_conditional_marker:
                    print(
                        f"❌ Decision Consistency："
                        f"Engine=CONDITIONAL，但最终答案出现绝对结论："
                        f"{pattern}"
                    )
                    return False

    # ============================================================
    # 7. Engine = NOT_ESTABLISHED
    # ============================================================

    elif engine_decision == "NOT_ESTABLISHED":

        # --------------------------------------------------------
        # 7.1 检查是否存在已经 SATISFIED 的排除条件
        # --------------------------------------------------------

        exclusion_conditions = []

        for item in condition_results:

            if not isinstance(item, dict):
                continue

            condition = safe_text(
                item.get("condition", "")
            ).strip()

            status = safe_text(
                item.get("status", "")
            ).upper().strip()

            category = safe_text(
                item.get("category", "")
            ).upper().strip()

            condition_type = safe_text(
                item.get("condition_type", "")
            ).upper().strip()

            if status != "SATISFIED":
                continue

            if (
                category == "EXCLUSION"
                or condition_type == "EXCLUSION"
            ):
                exclusion_conditions.append(condition)

        # --------------------------------------------------------
        # 7.2 如果存在 SATISFIED 排除条件，
        #     最终答案不得重新说“排除条件不影响义务”
        # --------------------------------------------------------

        if exclusion_conditions:

            contradiction_patterns = [
                "不影响法律义务",
                "不影响签订无固定期限劳动合同的义务",
                "不直接免除签订无固定期限劳动合同的义务",
                "不影响订立无固定期限劳动合同",
                "不影响用人单位的义务",
                "仍然必须签订",
                "仍应签订无固定期限劳动合同",
                "仍然应当签订无固定期限劳动合同",
                "不影响第十四条规定的订立义务",
            ]

            for pattern in contradiction_patterns:

                if pattern in answer_text:

                    print(
                        "❌ Decision Consistency："
                        "Engine=NOT_ESTABLISHED，"
                        "且存在 SATISFIED 排除条件，"
                        f"但最终答案出现矛盾表述：{pattern}"
                    )

                    print(
                        "   已确认排除条件："
                        + "；".join(exclusion_conditions)
                    )

                    return False

        # --------------------------------------------------------
        # 7.3 NOT_ESTABLISHED 不允许被表达成“可以确定必须签订”
        # --------------------------------------------------------

        definite_patterns = [
            "必须签订无固定期限劳动合同",
            "应当签订无固定期限劳动合同",
            "就必须签订无固定期限劳动合同",
            "依法必须签订无固定期限劳动合同",
        ]

        for pattern in definite_patterns:

            if pattern not in answer_text:
                continue

            # 如果前面存在明显否定结构，
            # 例如“不属于必须签订”，不要误判。
            negative_patterns = [
                "不能认定必须签订",
                "不能认定为必须签订",
                "并非必须签订",
                "不是必须签订",
                "目前不能认定必须签订",
                "当前不能认定必须签订",
                "不满足必须签订",
                "不具备必须签订",
            ]

            if any(
                negative in answer_text
                for negative in negative_patterns
            ):
                continue

            print(
                "❌ Decision Consistency："
                "Engine=NOT_ESTABLISHED，"
                f"但最终答案出现确定性义务表述：{pattern}"
            )

            return False

    # ============================================================
    # 8. SATISFIED 条件保护
    # ============================================================

    for condition in satisfied_conditions:

        # 对特别关键的 Article 39 排除条件进行保护。
        if "第三十九条" in condition:

            contradiction_patterns = [
                "第三十九条规定的情形不影响",
                "第三十九条情形不影响",
                "第三十九条不影响",
                "第三十九条并不影响",
                "存在第三十九条情形但仍然必须",
                "存在第三十九条情形仍然必须",
            ]

            for pattern in contradiction_patterns:

                if pattern in answer_text:

                    print(
                        "❌ Decision Consistency："
                        "Engine 已确认第三十九条排除条件 SATISFIED，"
                        f"但最终答案出现矛盾表述：{pattern}"
                    )

                    return False

    # ============================================================
    # 9. UNSATISFIED 条件保护
    # ============================================================

    for condition in unsatisfied_conditions:

        if "第三十九条" in condition:
            continue

        # 当前不直接根据自然语言判断，
        # 避免 Validator 自己重新进行法律推理。
        #
        # 这里暂时只做 Engine 状态级验证。
        pass

    # ============================================================
    # 10. UNKNOWN 条件保护
    # ============================================================

    # Validator 不负责重新判断 UNKNOWN。
    #
    # UNKNOWN 必须由 Engine 决定。
    # 因此这里只禁止明显的“全部条件已经满足”表达。
    if unknown_conditions:

        dangerous_patterns = [
            "所有条件均已满足",
            "全部条件均已满足",
            "已经满足全部条件",
            "已完全满足第十四条全部条件",
        ]

        for pattern in dangerous_patterns:

            if pattern in answer_text:

                print(
                    "❌ Decision Consistency："
                    f"Engine 仍存在 UNKNOWN 条件，"
                    f"但最终答案声称：{pattern}"
                )

                print(
                    "   UNKNOWN 条件："
                    + "；".join(unknown_conditions)
                )

                return False

    # ============================================================
    # 11. 最终通过
    # ============================================================

    return True

# ============================================================
# 三次固定期限合同专项验证
# ============================================================

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


# ============================================================
# 已确认用户事实 / 人工制造 UNKNOWN 专项验证
# ============================================================

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


# ============================================================
# CONDITIONAL 状态验证
# ============================================================

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


# ============================================================
# CONDITIONAL 状态验证
# ============================================================

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


# ============================================================
# UNKNOWN 条件验证
# ============================================================

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


# ============================================================
# 法律依据验证
# ============================================================

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


# ============================================================
# Decision 不可被 Ollama 修改
# ============================================================

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


# ============================================================
# 最终 Validation
# ============================================================

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


# ============================================================
# Condition Category / Completeness Validation
# ============================================================

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

# ============================================================
# Final Validation
# ============================================================

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


def build_fallback_answer(
    question: str,
    decision: Dict[str, Any],
) -> str:
    """
    V6.0-27 确定性 Python Fallback。

    重要原则：

    1. 不调用 Ollama。
    2. 不重新进行法律推理。
    3. 不修改 Decision。
    4. 不删除 UNKNOWN。
    5. 不把用户事实改写成法律规则。
    6. 法律依据只来自结构化 Rules。
    7. 最终结果仍然必须通过 Final Validation。
    8. REQUIRED / EXCLUSION / EXCEPTION 必须保持独立语义。
    9. EXCLUSION / EXCEPTION 的 NOT_SATISFIED 表示
       对应的排除情形 / 例外情形已经触发，
       不能输出为普通“未满足条件”。
    10. UNKNOWN 条件必须逐项保留，不能合并或丢失。

    V6.0-10 的问题是：

        Ollama Validation FAIL
                ↓
        build_plain_answer()
                ↓
        THREE_CONTRACT_FACT FAIL

    V6.0-13 不再让旧版 Answer Builder 作为安全 Fallback 的最终
    事实来源，而是直接使用已经完成的 Structured Answer 数据生成
    一个确定性的回答。

    V6.0-26 修正：

        1. 正确读取 not_satisfied_conditions。
        2. REQUIRED 的 NOT_SATISFIED 才进入“不满足必备条件”。
        3. EXCLUSION 的 NOT_SATISFIED 进入“已触发排除条件”。
        4. EXCEPTION 的 NOT_SATISFIED 进入“已触发例外条件”。
        5. UNKNOWN 条件逐项保留。
        6. 不再把 EXCLUSION 错误写成“未满足条件”。
        7. 不再把 UNKNOWN 条件错误写成“尚未确认的必备条件”。

    V6.0-27 修正：

        1. DEFINITE 结论不得再使用泛化占位语句：
               “可以按照 Decision Engine 的确定性结论处理。”

        2. DEFINITE 的最终法律结论必须直接读取
           Structured Rules 已经提供的：
               legal_obligations

        3. DEFINITE 的“法律后果”必须直接读取
           Structured Rules 已经提供的：
               legal_consequences
               legal_obligations

        4. Fallback 不重新进行法律推理。
           只负责把已经存在于 Structured Rules 中的
           确定性法律义务转换为最终回答。

        5. 如果 Structured Rules 没有提供
           legal_obligations / legal_consequences，
           不允许 Fallback 自行创造新的法律义务。
           此时只能使用安全的结构化 Decision 表述。

    V6.0-27 条件语义修正：

        REQUIRED：

            SATISFIED
                → 已满足

            NOT_SATISFIED
                → 未满足

            UNKNOWN
                → 尚未确认

        EXCLUSION：

            SATISFIED
                → 排除情形不存在 / 未触发

            NOT_SATISFIED
                → 排除情形存在 / 已触发

            UNKNOWN
                → 尚未确认

        EXCEPTION：

            SATISFIED
                → 例外情形不存在 / 未触发

            NOT_SATISFIED
                → 例外情形存在 / 已触发

            UNKNOWN
                → 尚未确认

    特别注意：

        Decision Engine 内部可以继续使用统一的
        SATISFIED / NOT_SATISFIED / UNKNOWN 状态。

        但是 Fallback 在展示和分类时，
        必须结合 condition_type 解释其语义。

        不能简单地认为：

            NOT_SATISFIED
                =
            普通“未满足条件”。

        对 EXCLUSION / EXCEPTION 而言：

            NOT_SATISFIED
                =
            对应的排除 / 例外情形已经触发。
    """

    print()
    print("=" * 70)
    print("Fallback / Deterministic Legal Answer Builder V6.0-27")
    print("=" * 70)

    question = normalize_text(
        question
    )

    engine_decision = normalize_text(
        decision.get(
            "engine_decision",
            decision.get(
                "decision",
                "",
            ),
        )
    ).upper()

    # ========================================================
    # 用户事实
    # ========================================================

    user_facts = unique_texts(
        ensure_list(
            decision.get(
                "user_facts",
                [],
            )
        )
    )

    # ========================================================
    # 不满足条件
    #
    # DecisionResult 的正式字段是：
    #
    #     not_satisfied_conditions
    #
    # 不能再使用旧的：
    #
    #     unsatisfied_conditions
    #
    # 但是这里仍然只作为兼容读取，不参与重新推理。
    # ========================================================

    not_satisfied = unique_texts(
        ensure_list(
            decision.get(
                "not_satisfied_conditions",
                decision.get(
                    "unsatisfied_conditions",
                    [],
                ),
            )
        )
    )

    # ========================================================
    # UNKNOWN
    # ========================================================

    unknown = ensure_list(
        decision.get(
            "unknown_conditions",
            [],
        )
    )

    # ========================================================
    # Structured Rules
    # ========================================================

    print()
    print("----------------------------------------------------------------------")
    print("DEBUG / Fallback Decision Fields")
    print("----------------------------------------------------------------------")
    print("decision keys:")
    print(list(decision.keys()))

    print()
    print("required_results:")
    print(decision.get("required_results"))

    print()
    print("condition_results:")
    print(decision.get("condition_results"))

    print()
    print("satisfied_conditions:")
    print(decision.get("satisfied_conditions"))

    print()
    print("required_satisfied_conditions:")
    print(decision.get("required_satisfied_conditions"))

    rules = build_rules_from_articles(
        ensure_list(
            decision.get(
                "rules",
                [],
            )
        )
    )

    # ========================================================
    # 分类条件结果
    # ========================================================

    condition_results = ensure_list(
        decision.get(
            "condition_results",
            [],
        )
    )

    # ========================================================
    # REQUIRED 条件结果
    #
    # 当前 DecisionResult 的正式结构中，
    # 所有条件统一存放在：
    #
    #     condition_results
    #
    # 每一项通过：
    #
    #     condition_type
    #
    # 或：
    #
    #     type
    #
    # 区分 REQUIRED / EXCLUSION / EXCEPTION。
    #
    # 因此不能再假定：
    #
    #     decision["required_results"]
    #
    # 一定存在。
    #
    # 这里直接从正式的 condition_results
    # 中提取 REQUIRED。
    #
    # 只做结构分类，不重新进行法律推理。
    # ========================================================

    required_results = []

    for item in condition_results:

        if not isinstance(item, dict):
            continue

        condition_type = normalize_text(
            item.get(
                "condition_type",
                item.get(
                    "type",
                    "",
                ),
            )
        ).upper()

        if condition_type == "REQUIRED":
            required_results.append(
                item
            )

    # --------------------------------------------------------
    # EXCLUSION 条件结果
    # --------------------------------------------------------

    exclusion_results = ensure_list(
        decision.get(
            "exclusion_condition_results",
            decision.get(
                "exclusion_results",
                [],
            ),
        )
    )

    # --------------------------------------------------------
    # 如果正式字段没有提供 EXCLUSION，
    # 同样从 condition_results 中提取。
    # --------------------------------------------------------

    if not exclusion_results:

        exclusion_results = []

        for item in condition_results:

            if not isinstance(item, dict):
                continue

            condition_type = normalize_text(
                item.get(
                    "condition_type",
                    item.get(
                        "type",
                        "",
                    ),
                )
            ).upper()

            if condition_type == "EXCLUSION":
                exclusion_results.append(
                    item
                )

    # --------------------------------------------------------
    # EXCEPTION 条件结果
    # --------------------------------------------------------

    exception_results = ensure_list(
        decision.get(
            "exception_condition_results",
            decision.get(
                "exception_results",
                [],
            ),
        )
    )

    # --------------------------------------------------------
    # 如果正式字段没有提供 EXCEPTION，
    # 同样从 condition_results 中提取。
    # --------------------------------------------------------

    if not exception_results:

        exception_results = []

        for item in condition_results:

            if not isinstance(item, dict):
                continue

            condition_type = normalize_text(
                item.get(
                    "condition_type",
                    item.get(
                        "type",
                        "",
                    ),
                )
            ).upper()

            if condition_type == "EXCEPTION":
                exception_results.append(
                    item
                )

    # ========================================================
    # 已满足条件
    #
    # 这里只展示 REQUIRED + SATISFIED。
    #
    # Decision Engine 的 satisfied_conditions
    # 同时可能包含：
    #
    #     REQUIRED + SATISFIED
    #     EXCLUSION + SATISFIED
    #     EXCEPTION + SATISFIED
    #
    # 其中：
    #
    #     EXCLUSION + SATISFIED
    #         = 排除情形不存在，排除条件未触发
    #
    #     EXCEPTION + SATISFIED
    #         = 例外情形不存在，例外条件未触发
    #
    # 因此不能把它们直接显示为“已满足条件”。
    #
    # 这里只读取 Decision Engine 已经分类好的
    # required_results，不重新进行法律推理。
    # ========================================================

    satisfied = []

    # ========================================================
    # 从 Decision Engine 已经生成的 condition_results 中，
    # 提取 REQUIRED + SATISFIED 条件。
    #
    # 注意：
    #
    # condition_results 是 Decision Engine 的正式条件判定结果。
    #
    # 这里仅做展示分类：
    #
    #     REQUIRED + SATISFIED
    #
    # 不重新进行任何法律推理。
    #
    # 不能直接使用 satisfied_conditions，
    # 因为 satisfied_conditions 可能同时包含：
    #
    #     REQUIRED
    #     EXCLUSION
    #     EXCEPTION
    #
    # 而 Fallback 的“已满足条件”栏目只应展示 REQUIRED。
    # ========================================================

    for item in condition_results:

        if not isinstance(item, dict):
            continue

        condition = normalize_text(
            item.get(
                "condition",
                "",
            )
        )

        status = normalize_text(
            item.get(
                "status",
                "UNKNOWN",
            )
        ).upper()

        condition_type = normalize_text(
            item.get(
                "condition_type",
                item.get(
                    "type",
                    "",
                ),
            )
        ).upper()

        if not condition:
            continue

        if (
            condition_type == "REQUIRED"
            and status == "SATISFIED"
        ):

            satisfied.append(
                condition
            )

    satisfied = unique_texts(
        satisfied
    )

    # --------------------------------------------------------
    # 如果分类结果没有提供，
    # 使用 DecisionResult 已经生成的 REQUIRED 满足条件。
    #
    # 仍然不重新推理。
    # --------------------------------------------------------

    if not satisfied:

        required_satisfied_conditions = unique_texts(
            ensure_list(
                decision.get(
                    "required_satisfied_conditions",
                    [],
                )
            )
        )

        satisfied = required_satisfied_conditions

    # ========================================================
    # 从分类结果中提取：
    #
    # 1. 不满足的 REQUIRED
    # 2. 已触发的 EXCLUSION
    # 3. 已触发的 EXCEPTION
    #
    # 注意：
    #
    # EXCLUSION / EXCEPTION 的 NOT_SATISFIED
    # 不能进入普通 not_satisfied。
    # ========================================================

    required_not_satisfied = []

    for item in required_results:

        if not isinstance(item, dict):
            continue

        condition = normalize_text(
            item.get(
                "condition",
                "",
            )
        )

        status = normalize_text(
            item.get(
                "status",
                "UNKNOWN",
            )
        ).upper()

        if not condition:
            continue

        if status in {
            "NOT_SATISFIED",
            "UNSATISFIED",
        }:
            required_not_satisfied.append(
                condition
            )

    required_not_satisfied = unique_texts(
        required_not_satisfied
    )

    # --------------------------------------------------------
    # 如果 Required Results 没有提供，
    # 使用 DecisionResult 已经分类好的
    # required_not_satisfied_conditions。
    #
    # 仍然不重新推理。
    # --------------------------------------------------------

    if not required_not_satisfied:

        required_not_satisfied = unique_texts(
            ensure_list(
                decision.get(
                    "required_not_satisfied_conditions",
                    [],
                )
            )
        )

    # --------------------------------------------------------
    # 已触发排除条件
    #
    # EXCLUSION 的语义：
    #
    #     SATISFIED
    #         = 排除情形不存在 / 未触发
    #
    #     NOT_SATISFIED
    #         = 排除情形存在 / 已触发
    #
    # 因此这里只收集 NOT_SATISFIED。
    # --------------------------------------------------------

    triggered_exclusions = []

    for item in exclusion_results:

        if not isinstance(item, dict):
            continue

        condition = normalize_text(
            item.get(
                "condition",
                "",
            )
        )

        status = normalize_text(
            item.get(
                "status",
                "UNKNOWN",
            )
        ).upper()

        if not condition:
            continue

        if status in {
            "NOT_SATISFIED",
            "UNSATISFIED",
        }:
            triggered_exclusions.append(
                condition
            )

    triggered_exclusions = unique_texts(
        triggered_exclusions
    )

    # --------------------------------------------------------
    # 如果分类结果没有提供，
    # 直接使用 DecisionResult 已经生成的字段。
    # --------------------------------------------------------

    if not triggered_exclusions:

        triggered_exclusions = unique_texts(
            ensure_list(
                decision.get(
                    "triggered_exclusion_conditions",
                    [],
                )
            )
        )

    # --------------------------------------------------------
    # 未触发排除条件
    #
    # EXCLUSION + SATISFIED
    #     = 排除情形不存在，因此没有触发排除条件。
    #
    # 这里仅用于最终自然语言展示。
    # --------------------------------------------------------

    untriggered_exclusions = []

    for item in exclusion_results:

        if not isinstance(item, dict):
            continue

        condition = normalize_text(
            item.get(
                "condition",
                "",
            )
        )

        status = normalize_text(
            item.get(
                "status",
                "UNKNOWN",
            )
        ).upper()

        if not condition:
            continue

        if status == "SATISFIED":

            untriggered_exclusions.append(
                condition
            )

    untriggered_exclusions = unique_texts(
        untriggered_exclusions
    )

    # ========================================================
    # 已触发例外条件
    #
    # EXCEPTION 的语义：
    #
    #     SATISFIED
    #         = 例外情形不存在 / 未触发
    #
    #     NOT_SATISFIED
    #         = 例外情形存在 / 已触发
    #
    # 因此这里只收集 NOT_SATISFIED。
    # ========================================================

    triggered_exceptions = []

    for item in exception_results:

        if not isinstance(item, dict):
            continue

        condition = normalize_text(
            item.get(
                "condition",
                "",
            )
        )

        status = normalize_text(
            item.get(
                "status",
                "UNKNOWN",
            )
        ).upper()

        if not condition:
            continue

        if status in {
            "NOT_SATISFIED",
            "UNSATISFIED",
        }:
            triggered_exceptions.append(
                condition
            )

    triggered_exceptions = unique_texts(
        triggered_exceptions
    )

    # --------------------------------------------------------
    # 如果分类结果没有提供，
    # 直接使用 DecisionResult 已经生成的字段。
    # --------------------------------------------------------

    if not triggered_exceptions:

        triggered_exceptions = unique_texts(
            ensure_list(
                decision.get(
                    "triggered_exception_conditions",
                    [],
                )
            )
        )

    # --------------------------------------------------------
    # 未触发例外条件
    #
    # EXCEPTION + SATISFIED
    #     = 例外情形不存在，因此没有触发例外条件。
    #
    # 这里仅用于最终自然语言展示。
    # --------------------------------------------------------

    untriggered_exceptions = []

    for item in exception_results:

        if not isinstance(item, dict):
            continue

        condition = normalize_text(
            item.get(
                "condition",
                "",
            )
        )

        status = normalize_text(
            item.get(
                "status",
                "UNKNOWN",
            )
        ).upper()

        if not condition:
            continue

        if status == "SATISFIED":

            untriggered_exceptions.append(
                condition
            )

    untriggered_exceptions = unique_texts(
        untriggered_exceptions
    )

    # ========================================================
    # 最终“未满足必备条件”
    #
    # 只允许 REQUIRED 条件进入这里。
    #
    # 绝对不能把：
    #
    #     EXCLUSION
    #     EXCEPTION
    #
    # 的 NOT_SATISFIED 放进来。
    # ========================================================

    required_not_satisfied = unique_texts(
        required_not_satisfied
    )

    # ========================================================
    # DEFINITE 法律义务 / 法律后果
    #
    # V6.0-27 修正：
    #
    # Fallback 不再自己生成：
    #
    #     “应当订立无固定期限劳动合同”
    #
    # 这样的法律结论。
    #
    # 而是直接读取 Structured Rules 已经提供的：
    #
    #     legal_obligations
    #     legal_consequences
    #
    # 这样可以保证：
    #
    #     Structured Rule
    #          ↓
    #     Decision Engine
    #          ↓
    #     Fallback
    #
    # 整个过程没有新的法律推理。
    #
    # 如果当前规则没有提供法律义务或法律后果，
    # Fallback 不得自行创造新的法律内容。
    # ========================================================

    definite_obligations = []
    definite_consequences = []

    for rule in rules:

        if not isinstance(rule, dict):
            continue

        legal_obligations = ensure_list(
            rule.get(
                "legal_obligations",
                [],
            )
        )

        legal_consequences = ensure_list(
            rule.get(
                "legal_consequences",
                [],
            )
        )

        for obligation in legal_obligations:

            obligation_text = normalize_text(
                obligation
            )

            if obligation_text:

                definite_obligations.append(
                    obligation_text
                )

        for consequence in legal_consequences:

            consequence_text = normalize_text(
                consequence
            )

            if consequence_text:

                definite_consequences.append(
                    consequence_text
                )

    definite_obligations = unique_texts(
        definite_obligations
    )

    definite_consequences = unique_texts(
        definite_consequences
    )

    # ========================================================
    # CONDITIONAL / DEFINITE / NOT_ESTABLISHED
    #
    # 这里只读取 Engine Decision。
    # 不重新进行法律推理。
    # ========================================================

    if engine_decision == DECISION_CONDITIONAL:

        if satisfied:

            conclusion_lines = [
                "根据现有事实及已经确认的结构化法律条件，当前至少已经满足以下条件："
                + "、".join(
                    satisfied
                )
                + "。"
            ]

        else:

            conclusion_lines = [
                "根据现有事实，当前法律结论仍属于条件性结论。"
            ]

        if unknown:

            conclusion_lines.append(
                "但结构化法律规则中仍存在尚未确认的条件，因此当前不能将 CONDITIONAL 直接转换为确定性结论。"
            )

        if triggered_exclusions:

            conclusion_lines.append(
                "同时，以下排除条件已经触发："
                + "、".join(
                    triggered_exclusions
                )
                + "。"
            )

        if triggered_exceptions:

            conclusion_lines.append(
                "同时，以下例外条件已经触发："
                + "、".join(
                    triggered_exceptions
                )
                + "。"
            )

    elif engine_decision == DECISION_DEFINITE:

        # ----------------------------------------------------
        # DEFINITE：
        #
        # 直接使用 Structured Rules 中已经存在的
        # legal_obligations。
        #
        # 不重新进行法律推理。
        # ----------------------------------------------------

        if definite_obligations:

            conclusion_lines = [
                "是。"
                + "根据已经确认的结构化法律条件，"
                + "、".join(
                    definite_obligations
                )
                + "。"
            ]

        else:

            # ------------------------------------------------
            # 如果 Structured Rules 没有提供
            # legal_obligations，
            # 不自行创造法律义务。
            #
            # 使用安全的结构化 Decision 表述。
            # ------------------------------------------------

            conclusion_lines = [
                "根据已经确认的结构化法律条件，"
                "Decision Engine 的结论为 DEFINITE。"
            ]

    elif engine_decision == DECISION_NOT_ESTABLISHED:

        conclusion_lines = [
            "根据 Decision Engine 已确认的结构化法律条件，"
            "当前不能认定已经满足相关法律规则所规定的订立无固定期限劳动合同条件。"
        ]

        if required_not_satisfied:

            conclusion_lines.append(
                "其中，以下必备条件尚未满足："
                + "、".join(
                    required_not_satisfied
                )
                + "。"
            )

        if triggered_exclusions:

            conclusion_lines.append(
                "同时，以下排除条件已经触发："
                + "、".join(
                    triggered_exclusions
                )
                + "。"
            )

        if triggered_exceptions:

            conclusion_lines.append(
                "同时，以下例外条件已经触发："
                + "、".join(
                    triggered_exceptions
                )
                + "。"
            )

    else:

        conclusion_lines = [
            "根据 Decision Engine 已确认的结构化法律条件，"
            "当前不能认定相关法律条件已经成立。"
        ]

    # ========================================================
    # 用户事实
    # ========================================================

    fact_lines = []

    if user_facts:

        for fact in user_facts:

            fact_text = normalize_text(
                fact
            )

            if fact_text:

                fact_lines.append(
                    f"- {fact_text}"
                )

    else:

        fact_lines.append(
            "- 当前没有提取到明确用户事实。"
        )

    # ========================================================
    # 已满足条件
    #
    # 这里只展示 REQUIRED + SATISFIED。
    # ========================================================

    satisfied_lines = []

    if satisfied:

        for item in satisfied:

            satisfied_lines.append(
                f"- {item}"
            )

    else:

        satisfied_lines.append(
            "- 无。"
        )

    # ========================================================
    # 不满足的 REQUIRED 条件
    #
    # 这里不是所有 NOT_SATISFIED。
    #
    # 这里只输出 REQUIRED。
    # ========================================================

    required_not_satisfied_lines = []

    if required_not_satisfied:

        for item in required_not_satisfied:

            required_not_satisfied_lines.append(
                f"- {item}"
            )

    else:

        required_not_satisfied_lines.append(
            "- 无。"
        )

    # ========================================================
    # UNKNOWN 条件
    #
    # 每一个 UNKNOWN 必须逐项输出。
    # ========================================================

    unknown_lines = []

    for item in unknown:

        if isinstance(item, dict):

            condition = normalize_text(
                item.get(
                    "condition",
                    "",
                )
            )

            reason = normalize_text(
                item.get(
                    "reason",
                    "",
                )
            )

            if not condition:
                continue

            if reason:

                unknown_lines.append(
                    f"- {condition}：{reason}"
                )

            else:

                unknown_lines.append(
                    f"- {condition}"
                )

        else:

            condition = normalize_text(
                item
            )

            if condition:

                unknown_lines.append(
                    f"- {condition}"
                )

    if not unknown_lines:

        unknown_lines.append(
            "- 无。"
        )

    # ========================================================
    # 分类条件结果
    #
    # 这里保留原始 ConditionResult 的：
    #
    #     condition
    #     status
    #     condition_type
    #     reason
    #
    # 仅用于调试和透明展示。
    #
    # 不重新进行法律推理。
    # ========================================================

    condition_result_lines = []

    for index, item in enumerate(
        condition_results,
        start=1,
    ):

        if not isinstance(item, dict):
            continue

        condition = normalize_text(
            item.get(
                "condition",
                "",
            )
        )

        status = normalize_text(
            item.get(
                "status",
                "UNKNOWN",
            )
        ).upper()

        condition_type = normalize_text(
            item.get(
                "condition_type",
                item.get(
                    "type",
                    "REQUIRED",
                ),
            )
        ).upper()

        reason = normalize_text(
            item.get(
                "reason",
                "",
            )
        )

        if not condition:
            continue

        line = (
            f"{index}. "
            f"condition={condition}；"
            f"status={status}；"
            f"type={condition_type}"
        )

        if reason:

            line += (
                f"；reason={reason}"
            )

        condition_result_lines.append(
            line
        )

    condition_results_text = (
        "\n".join(
            condition_result_lines
        )
        or "无。"
    )

    # ========================================================
    # 分类结果自然语言转换
    # ========================================================

    def format_category_results(
        items,
        category,
        empty="- 无。",
    ):
        """
        将内部 ConditionResult 状态转换为最终回答中的自然语言语义。

        注意：

            REQUIRED：

                SATISFIED
                    → 已满足

                NOT_SATISFIED
                    → 未满足

                UNKNOWN
                    → 尚未确认

            EXCLUSION：

                SATISFIED
                    → 未触发

                NOT_SATISFIED
                    → 已触发

                UNKNOWN
                    → 尚未确认

            EXCEPTION：

                SATISFIED
                    → 未触发

                NOT_SATISFIED
                    → 已触发

                UNKNOWN
                    → 尚未确认

        这是内部状态到自然语言语义的映射，
        不属于重新法律推理。
        """

        lines = []

        semantic_map = {

            "REQUIRED": {
                "SATISFIED": "已满足",
                "NOT_SATISFIED": "未满足",
                "UNSATISFIED": "未满足",
                "UNKNOWN": "尚未确认",
            },

            "EXCLUSION": {
                "SATISFIED": "未触发",
                "NOT_SATISFIED": "已触发",
                "UNSATISFIED": "已触发",
                "UNKNOWN": "尚未确认",
            },

            "EXCEPTION": {
                "SATISFIED": "未触发",
                "NOT_SATISFIED": "已触发",
                "UNSATISFIED": "已触发",
                "UNKNOWN": "尚未确认",
            },
        }

        category = normalize_text(
            category
        ).upper()

        category_map = semantic_map.get(
            category,
            semantic_map["REQUIRED"],
        )

        for item in items:

            if not isinstance(item, dict):
                continue

            condition = normalize_text(
                item.get(
                    "condition",
                    "",
                )
            )

            status = normalize_text(
                item.get(
                    "status",
                    "UNKNOWN",
                )
            ).upper()

            reason = normalize_text(
                item.get(
                    "reason",
                    "",
                )
            )

            if not condition:
                continue

            semantic_status = category_map.get(
                status,
                "尚未确认",
            )

            line = (
                f"- [{semantic_status}] "
                f"{condition}"
            )

            if reason:

                line += (
                    f"：{reason}"
                )

            lines.append(
                line
            )

        return lines or [empty]

    exclusion_lines = format_category_results(
        exclusion_results,
        "EXCLUSION",
    )

    exception_lines = format_category_results(
        exception_results,
        "EXCEPTION",
    )

    # ========================================================
    # 法律依据
    #
    # 绝不凭记忆增加法条。
    # 所有法律依据直接来自当前 Structured Rules。
    # ========================================================

    core_basis_lines = []
    related_basis_lines = []
    seen_basis = set()

    rules = prioritize_legal_rules(
        question=question,
        rules=rules,
    )

    for rule in rules:

        if not isinstance(rule, dict):
            continue

        law_name = normalize_text(
            rule.get(
                "law_name",
                "",
            )
        )

        article_number = normalize_text(
            rule.get(
                "article_number",
                "",
            )
        )

        if not law_name or not article_number:
            continue

        citation = (
            f"《{law_name}》"
            f"{article_number}"
        )

        if citation in seen_basis:
            continue

        seen_basis.add(
            citation
        )

        priority = normalize_text(
            rule.get(
                "rule_priority",
                "RELATED",
            )
        ).upper()

        if priority == "CORE":

            core_basis_lines.append(
                citation
            )

        else:

            related_basis_lines.append(
                citation
            )

    # ========================================================
    # 核心依据与相关依据分层
    # ========================================================

    basis_lines = []

    if core_basis_lines:

        basis_lines.append(
            "【核心法律依据】"
        )

        basis_lines.extend(
            f"{index}. {citation}"
            for index, citation in enumerate(
                core_basis_lines,
                1,
            )
        )

    if related_basis_lines:

        basis_lines.append(
            "【相关法律依据】"
        )

        start_index = (
            len(core_basis_lines)
            + 1
        )

        basis_lines.extend(
            f"{index}. {citation}"
            for index, citation in enumerate(
                related_basis_lines,
                start_index,
            )
        )

    if not basis_lines:

        basis_lines.append(
            "当前没有可用于最终回答的结构化法律依据。"
        )

    # ========================================================
    # 法律分析
    # ========================================================

    analysis_lines = []

    # --------------------------------------------------------
    # 1. 用户事实
    # --------------------------------------------------------

    analysis_lines.append(
        "1. 用户事实："
    )

    analysis_lines.extend(
        fact_lines
    )

    # --------------------------------------------------------
    # 2. 已满足条件
    # --------------------------------------------------------

    analysis_lines.append(
        "2. 已满足条件："
    )

    analysis_lines.extend(
        satisfied_lines
    )

    # --------------------------------------------------------
    # 3. 不满足的必备条件
    # --------------------------------------------------------

    analysis_lines.append(
        "3. 不满足的必备条件："
    )

    analysis_lines.extend(
        required_not_satisfied_lines
    )

    # --------------------------------------------------------
    # 4. 已触发排除条件
    # --------------------------------------------------------

    analysis_lines.append(
        "4. 已触发排除条件："
    )

    if triggered_exclusions:

        for item in triggered_exclusions:

            analysis_lines.append(
                f"- {item}"
            )

    else:

        analysis_lines.append(
            "- 无。"
        )

    # --------------------------------------------------------
    # 未触发排除条件
    #
    # EXCLUSION + SATISFIED
    # 表示排除情形不存在，因此排除条件没有被触发。
    #
    # 不能将其显示为“已满足条件”。
    # --------------------------------------------------------

    if untriggered_exclusions:

        analysis_lines.append(
            "未触发排除条件："
        )

        for item in untriggered_exclusions:

            analysis_lines.append(
                f"- {item}"
            )

    # --------------------------------------------------------
    # 5. 已触发例外条件
    # --------------------------------------------------------

    analysis_lines.append(
        "5. 已触发例外条件："
    )

    if triggered_exceptions:

        for item in triggered_exceptions:

            analysis_lines.append(
                f"- {item}"
            )

    else:

        analysis_lines.append(
            "- 无。"
        )

    # --------------------------------------------------------
    # 未触发例外条件
    #
    # EXCEPTION + SATISFIED
    # 表示例外情形不存在，因此例外条件没有被触发。
    #
    # 不能将其显示为“已满足条件”。
    # --------------------------------------------------------

    if untriggered_exceptions:

        analysis_lines.append(
            "未触发例外条件："
        )

        for item in untriggered_exceptions:

            analysis_lines.append(
                f"- {item}"
            )

    # --------------------------------------------------------
    # 6. 尚未确认条件
    #
    # 注意：
    #
    # UNKNOWN 不应该被写成“尚未确认的必备条件”，
    # 因为其中可能包含 EXCLUSION / EXCEPTION。
    # ========================================================

    analysis_lines.append(
        "6. 尚未确认条件："
    )

    analysis_lines.extend(
        unknown_lines
    )

    # --------------------------------------------------------
    # 7. 法律后果
    # --------------------------------------------------------

    analysis_lines.append(
        "7. 法律后果："
    )

    if engine_decision == DECISION_CONDITIONAL:

        analysis_lines.append(
            "- 当前属于条件性结论，在关键事实尚未确认之前，不能直接将条件性 Decision 转换为确定性结论。"
        )

    elif engine_decision == DECISION_DEFINITE:

        # ----------------------------------------------------
        # DEFINITE：
        #
        # 直接读取 Structured Rules 已经提供的
        # legal_consequences。
        #
        # 如果 legal_consequences 为空，
        # 再使用 legal_obligations。
        #
        # 这不是重新推理，只是结构化字段展示。
        # ----------------------------------------------------

        if definite_consequences:

            for consequence in definite_consequences:

                analysis_lines.append(
                    f"- {consequence}"
                )

        elif definite_obligations:

            for obligation in definite_obligations:

                analysis_lines.append(
                    f"- {obligation}"
                )

        else:

            analysis_lines.append(
                "- Decision Engine 已确认当前 Decision 为 DEFINITE，"
                "但 Structured Rules 未提供具体 legal_obligations 或 legal_consequences。"
            )

    elif engine_decision == DECISION_NOT_ESTABLISHED:

        analysis_lines.append(
            "- 根据 Decision Engine 的 NOT_ESTABLISHED 结论，"
            "当前不能认定已经满足相关法律规则所规定的订立无固定期限劳动合同条件。"
        )

    else:

        analysis_lines.append(
            "- 根据 Decision Engine 已确认的结构化法律条件，"
            "当前不能认定相关法律条件已经成立。"
        )

    # ========================================================
    # 需要注意
    #
    # 这里暂时保留兼容内容。
    #
    # answer_question() 在 Final Validation 之后，
    # 会再次调用 build_deterministic_notices()
    # 并用确定性 UNKNOWN 列表替换这里的内容。
    #
    # 因此最终输出中的【需要注意】不依赖这里的自然语言。
    # ========================================================

    notice_lines = []

    if unknown:

        notice_lines.append(
            "- 当前存在尚未确认的条件，不能自行将 UNKNOWN 条件视为已经成立。"
        )

        notice_lines.append(
            "- UNKNOWN 条件的最终列表及顺序以 Structured Decision 为准。"
        )

    if triggered_exclusions:

        notice_lines.append(
            "- 已触发排除条件不得写成普通“未满足条件”。"
        )

    if triggered_exceptions:

        notice_lines.append(
            "- 已触发例外条件不得写成普通“未满足条件”。"
        )

    if not notice_lines:

        notice_lines.append(
            "- 最终回答仅依据当前结构化 Decision 和 Rules，不新增结构化数据之外的法律判断。"
        )

    # ========================================================
    # 组装最终答案
    # ========================================================

    answer = (
        SECTION_CONCLUSION
        + "\n"
        + "\n".join(
            conclusion_lines
        )
        + "\n\n"
        + SECTION_BASIS
        + "\n"
        + "\n".join(
            basis_lines
        )
        + "\n\n"
        + SECTION_ANALYSIS
        + "\n"
        + "\n".join(
            analysis_lines
        )
        + "\n\n"
        + SECTION_NOTICE
        + "\n"
        + "\n".join(
            notice_lines
        )
    )

    return clean_answer(
        answer
    )


# ============================================================
# Component Test
# ============================================================

def component_test():
    """
    RAG V6.0-26-FIXED Component Test。

    本测试不依赖 Ollama 生成结果，专门验证 V6.0-25 新增的：

        Fact
          ↓
        Condition
          ↓
        Rule Dependency
          ↓
        Legal Consequence

    测试重点：

    1. “连续签订三次固定期限劳动合同”必须映射为：
           连续订立二次固定期限劳动合同 = SATISFIED

    2. “三次”不得自动证明：
           - 续订劳动合同
           - 劳动者提出或者同意续订、订立劳动合同
           - 第39条 / 第40条排除情形不存在
           - 劳动者未提出订立固定期限劳动合同

    3. Required / Exclusion / Exception 必须保持独立分类。

    4. unknown_conditions 只能包含 Required UNKNOWN。

    5. 不允许把法律条件偷换成：
           “劳动者是否提出或同意订立无固定期限劳动合同”。

    6. Final Fact-to-Condition Validation 必须接受正确表达，
       拒绝错误的条件偷换。
    """

    print()
    print("=" * 70)
    print(f"RAG {RAG_VERSION} Component Test")
    print("=" * 70)

    question = (
        "公司连续签订三次固定期限劳动合同后，"
        "是否必须签订无固定期限劳动合同？"
    )

    print()
    print(f"问题：{question}")

    # --------------------------------------------------------
    # Step 1：Retriever / Structured Context
    # --------------------------------------------------------

    context_data = build_structured_context(
        question=question,
        top_k=5,
        score_threshold=0.55,
    )

    rules = ensure_list(context_data.get("rules", []))

    assert len(rules) > 0, (
        "V6.0-27 Component Test：没有检索到任何法律规则"
    )

    print()
    print(f"Structured Rules：{len(rules)}")

    # --------------------------------------------------------
    # Step 2：Legal Decision Engine
    # --------------------------------------------------------

    decision = run_decision_engine(
        question=question,
        rules=rules,
    )

    engine_condition_results = ensure_list(
        get_field(decision, "condition_results", [])
    )

    assert len(engine_condition_results) == 8, (
        "V6.0-27 Component Test：Engine Condition Results 应为 8"
    )

    print(f"Engine Condition Results：{len(engine_condition_results)}")

    # --------------------------------------------------------
    # Step 3：Answer Builder Adapter
    # --------------------------------------------------------

    adapted = run_answer_builder(
        decision=decision,
        rules=rules,
        question=question,
    )

    assert adapted["engine_decision"] == DECISION_CONDITIONAL, (
        "V6.0-27 Component Test：Engine Decision 应为 CONDITIONAL"
    )

    assert adapted["decision"] == ANSWER_CONDITIONAL, (
        "V6.0-27 Component Test：Builder Decision 应为 CONDITIONAL"
    )

    # --------------------------------------------------------
    # Test 1：用户事实保持原意
    # --------------------------------------------------------

    facts = ensure_list(adapted.get("user_facts", []))

    assert any(
        "三次" in normalize_text(fact)
        and "固定期限劳动合同" in normalize_text(fact)
        for fact in facts
    ), (
        "V6.0-27 Component Test：用户事实“三次固定期限劳动合同”丢失"
    )

    print("✅ Test 1：用户事实“三次固定期限劳动合同”保持原意")

    # --------------------------------------------------------
    # Test 2：Fact → Condition Numeric Threshold Mapping
    # --------------------------------------------------------

    mappings = ensure_list(
        adapted.get("fact_condition_mappings", [])
    )

    three_mapping = next(
        (
            item for item in mappings
            if isinstance(item, dict)
            and normalize_text(item.get("condition", ""))
            == "连续订立二次固定期限劳动合同"
        ),
        None,
    )

    assert three_mapping is not None, (
        "V6.0-27 Component Test：缺少“三次→二次”数量门槛映射"
    )

    assert normalize_text(
        three_mapping.get("status", "")
    ).upper() == "SATISFIED", (
        "V6.0-27 Component Test：三次→二次数量门槛必须为 SATISFIED"
    )

    assert normalize_text(
        three_mapping.get("mapping_type", "")
    ) == "NUMERIC_THRESHOLD", (
        "V6.0-27 Component Test：映射类型必须为 NUMERIC_THRESHOLD"
    )

    print(
        "✅ Test 2：三次固定期限合同 → 连续订立二次固定期限劳动合同 = SATISFIED"
    )

    # --------------------------------------------------------
    # Test 3：Mapping 不得越权证明其它条件
    # --------------------------------------------------------

    does_not_prove = ensure_list(
        three_mapping.get("does_not_prove", [])
    )

    forbidden_proofs = {
        "续订劳动合同",
        "劳动者提出或者同意续订、订立劳动合同",
        "不存在第三十九条规定情形",
        "不存在第四十条第一项规定情形",
        "不存在第四十条第二项规定情形",
        "劳动者未提出订立固定期限劳动合同",
    }

    assert forbidden_proofs.issubset(
        set(normalize_text(item) for item in does_not_prove)
    ), (
        "V6.0-27 Component Test：三次合同的 does_not_prove 信息不完整"
    )

    print("✅ Test 3：三次事实不得越权证明其它法律条件")

    # --------------------------------------------------------
    # Test 4：Required / Exclusion / Exception 分类
    # --------------------------------------------------------

    required_results = ensure_list(
        adapted.get("required_condition_results", [])
    )
    exclusion_results = ensure_list(
        adapted.get("exclusion_condition_results", [])
    )
    exception_results = ensure_list(
        adapted.get("exception_results", [])
    )

    assert len(required_results) == 4, (
        "V6.0-27 Component Test：Required Condition Results 应为 4"
    )
    assert len(exclusion_results) == 3, (
        "V6.0-27 Component Test：Exclusion Condition Results 应为 3"
    )
    assert len(exception_results) == 1, (
        "V6.0-27 Component Test：Exception Results 应为 1"
    )

    required_names = {
        normalize_text(item.get("condition", ""))
        for item in required_results
        if isinstance(item, dict)
    }
    exclusion_names = {
        normalize_text(item.get("condition", ""))
        for item in exclusion_results
        if isinstance(item, dict)
    }
    exception_names = {
        normalize_text(item.get("condition", ""))
        for item in exception_results
        if isinstance(item, dict)
    }

    assert required_names.isdisjoint(exclusion_names), (
        "V6.0-27 Component Test：Required / Exclusion 条件发生重复"
    )
    assert required_names.isdisjoint(exception_names), (
        "V6.0-27 Component Test：Required / Exception 条件发生重复"
    )
    assert exclusion_names.isdisjoint(exception_names), (
        "V6.0-27 Component Test：Exclusion / Exception 条件发生重复"
    )

    print("✅ Test 4：Required / Exclusion / Exception 分类正确")

    # --------------------------------------------------------
    # Test 5：三次事实只能满足数量门槛
    # --------------------------------------------------------

    satisfied = set(
        normalize_text(item)
        for item in ensure_list(
            adapted.get("satisfied_conditions", [])
        )
    )

    assert satisfied == {
        "连续订立二次固定期限劳动合同",
        "存在后续订立的劳动合同",
    }, (
        "V6.0-27 Component Test：当前事实下应满足数量门槛和后续合同存在条件"
    )

    print("✅ Test 5：当前事实仅自动满足数量门槛")

    # --------------------------------------------------------
    # Test 6：Required UNKNOWN 必须恰好为 2
    # --------------------------------------------------------

    unknown_conditions = ensure_list(
        adapted.get("unknown_conditions", [])
    )

    unknown_names = {
        _condition_text(item)
        for item in unknown_conditions
        if _condition_text(item)
    }

    assert unknown_names == {
        "续订劳动合同",
        "劳动者提出或者同意续订、订立劳动合同",
    }, (
        "V6.0-27 Component Test：Required UNKNOWN 条件集合错误"
    )

    print("✅ Test 6：Required UNKNOWN = 2，且只包含两个必备条件")

    # --------------------------------------------------------
    # Test 7：Exclusion / Exception 不得混入 unknown_conditions
    # --------------------------------------------------------

    forbidden_unknown_names = (
        exclusion_names | exception_names
    )

    assert unknown_names.isdisjoint(forbidden_unknown_names), (
        "V6.0-27 Component Test：Exclusion / Exception 被错误加入 unknown_conditions"
    )

    print("✅ Test 7：Exclusion / Exception 未混入普通 UNKNOWN")

    # --------------------------------------------------------
    # Test 8：Condition Dependency 不允许条件偷换
    # --------------------------------------------------------

    correct_answer = (
        "公司连续签订三次固定期限劳动合同，已经达到连续订立二次固定期限劳动合同的数量门槛；"
        "但仍需判断续订劳动合同以及劳动者提出或者同意续订、订立劳动合同等法定条件。"
        "现有事实不能直接证明劳动者已经提出或者同意下一次订立劳动合同，也不能证明不存在法定排除情形。"
    )

    assert validate_fact_condition_mapping(
        answer=correct_answer,
        question=question,
        decision=adapted,
    ), (
        "V6.0-27 Component Test：正确的 Fact → Condition 表达未通过验证"
    )

    wrong_answer_1 = (
        "因为连续签订三次固定期限劳动合同，所以已经证明劳动者同意订立无固定期限劳动合同。"
    )

    assert not validate_fact_condition_mapping(
        answer=wrong_answer_1,
        question=question,
        decision=adapted,
    ), (
        "V6.0-27 Component Test：错误的无固定期限合同条件偷换未被拦截"
    )

    wrong_answer_2 = (
        "第三次合同是否存在仍然需要确认。"
    )

    assert not validate_fact_condition_mapping(
        answer=wrong_answer_2,
        question=question,
        decision=adapted,
    ), (
        "V6.0-27 Component Test：错误的第三次合同存在性判断未被拦截"
    )

    print("✅ Test 8：Fact → Condition 条件偷换验证正确")

    # --------------------------------------------------------
    # Test 9：Rule Dependency 结构完整性
    # --------------------------------------------------------

    assert three_mapping.get("dependency") == (
        "THREE_CONTRACTS_MEET_TWO_CONTRACT_THRESHOLD"
    ), (
        "V6.0-27 Component Test：Rule Dependency 标识错误"
    )

    assert normalize_text(
        three_mapping.get("fact", "")
    ) == "公司连续签订三次固定期限劳动合同", (
        "V6.0-27 Component Test：Mapping fact 必须保持用户事实原意"
    )

    print("✅ Test 9：Rule Dependency 结构完整")

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("Component Test Result")
    print("=" * 70)
    print()
    print(f"Engine Decision：{adapted['engine_decision']}")
    print(f"Builder Decision：{adapted['decision']}")
    print(f"Rules：{len(adapted['rules'])}")
    print(f"Facts：{len(adapted['user_facts'])}")
    print(f"Required Conditions：{len(required_results)}")
    print(f"Exclusion Conditions：{len(exclusion_results)}")
    print(f"Exceptions：{len(exception_results)}")
    print(f"Satisfied Conditions：{len(adapted['satisfied_conditions'])}")
    print(f"Unknown Conditions：{len(unknown_conditions)}")
    print(f"Fact Mappings：{len(mappings)}")
    print()
    print("🎉 RAG V6.0-27 Component Test 全部通过")

    return adapted

# ============================================================
# Deterministic Notices
# ============================================================

def build_deterministic_notices(
    decision: Dict[str, Any],
) -> str:
    """
    根据 Engine 的 UNKNOWN 条件生成确定性的【需要注意】。

    核心原则：

    1. UNKNOWN 条件完全来自 Legal Decision Engine。
    2. Ollama 不参与 UNKNOWN 条件的增删。
    3. Ollama 不允许合并 UNKNOWN 条件。
    4. 每一个 UNKNOWN 条件必须逐项输出。
    5. 输出顺序保持 Engine 顺序。
    """

    unknown_conditions = decision.get(
        "unknown_conditions",
        [],
    ) or []

    lines = [
        "【需要注意】"
    ]

    if not unknown_conditions:

        lines.append(
            "当前没有 Engine 标记为 UNKNOWN 的条件。"
        )

        return "\n".join(lines)

    for index, condition in enumerate(
        unknown_conditions,
        start=1,
    ):

        if isinstance(condition, dict):

            condition_text = condition.get(
                "condition",
                condition.get(
                    "description",
                    str(condition),
                ),
            )

        else:

            condition_text = getattr(
                condition,
                "condition",
                str(condition),
            )

        lines.append(
            f"{index}. {condition_text}"
        )

    return "\n".join(lines)

# ============================================================
# Replace Deterministic Notices
# ============================================================

def replace_deterministic_notices(
    answer: str,
    deterministic_notices: str,
) -> str:
    """
    用 Python 确定性生成的【需要注意】替换 Ollama 原有内容。

    核心原则：

    1. 【需要注意】只替换当前章节。
    2. 保留【结论】。
    3. 保留【法律依据】。
    4. 保留【法律分析】。
    5. 不允许因为替换【需要注意】而删除前面的章节。
    6. 【需要注意】应当是最终答案的最后一个正式章节。
    """

    if not answer:
        return deterministic_notices

    marker = "【需要注意】"

    if marker not in answer:

        return (
            answer.rstrip()
            + "\n\n"
            + deterministic_notices
        )

    prefix = answer.split(
        marker,
        1,
    )[0].rstrip()

    return (
        prefix
        + "\n\n"
        + deterministic_notices
    )

# ============================================================
# Deterministic Legal Basis
# ============================================================

def build_deterministic_legal_basis(
    question: str,
    rules: List[Dict[str, Any]],
) -> str:
    """
    根据当前 Structured Rules 确定性生成【法律依据】。

    核心原则：

    1. 法律依据只能来自当前 Structured Rules。
    2. 不允许 Ollama 自行选择、增加或替换法律依据。
    3. CORE 规则优先于 RELATED 规则。
    4. CORE 规则中的 CRITICAL / 核心法条 / structured_rule
       优先作为首要法律依据。
    5. 不凭模型记忆增加法条。
    6. 不将 EXCLUSION / EXCEPTION 条件本身错误地提升为
       核心法律依据。
    """

    if not isinstance(rules, list):
        rules = []

    ordered_rules = prioritize_legal_rules(
        question=question,
        rules=rules,
    )

    core_basis_lines = []
    related_basis_lines = []

    seen_basis = set()

    for rule in ordered_rules:

        if not isinstance(rule, dict):
            continue

        law_name = normalize_text(
            rule.get(
                "law_name",
                "",
            )
        )

        article_number = normalize_text(
            rule.get(
                "article_number",
                "",
            )
        )

        if not law_name or not article_number:
            continue

        citation = (
            f"《{law_name}》"
            f"{article_number}"
        )

        if citation in seen_basis:
            continue

        seen_basis.add(
            citation
        )

        priority = normalize_text(
            rule.get(
                "rule_priority",
                "RELATED",
            )
        ).upper()

        if priority == "CORE":

            core_basis_lines.append(
                citation
            )

        else:

            related_basis_lines.append(
                citation
            )

    lines = [
        "【法律依据】"
    ]

    if core_basis_lines:

        lines.append(
            "【核心法律依据】"
        )

        lines.extend(
            f"{index}. {citation}"
            for index, citation in enumerate(
                core_basis_lines,
                start=1,
            )
        )

    if related_basis_lines:

        lines.append(
            "【相关法律依据】"
        )

        start_index = (
            len(core_basis_lines)
            + 1
        )

        lines.extend(
            f"{index}. {citation}"
            for index, citation in enumerate(
                related_basis_lines,
                start=start_index,
            )
        )

    if len(lines) == 1:

        lines.append(
            "当前没有可用于最终回答的结构化法律依据。"
        )

    return "\n".join(lines)

# ============================================================
# Deterministic Conclusion
# ============================================================

def build_deterministic_conclusion(
    decision: Dict[str, Any],
) -> str:
    """
    根据 Legal Decision Engine 的最终 Decision，
    确定性生成【结论】。

    核心原则：

    1. Decision Engine 是最终法律结论的唯一来源。
    2. Ollama 不得决定 DEFINITE / CONDITIONAL / NOT_ESTABLISHED。
    3. Ollama 不得把 CONDITIONAL 改写成 NOT_ESTABLISHED。
    4. Ollama 不得把 UNKNOWN 改写成 NOT_SATISFIED。
    5. Python 最终覆盖 Ollama 原有【结论】。
    6. 结论只允许表达 Engine 已经确认的状态。
    """

    engine_decision = extract_engine_decision(
        decision
    )

    condition_results = ensure_list(
        get_field(
            decision,
            "condition_results",
            [],
        )
    )

    required_satisfied = []
    required_not_satisfied = []
    unknown_conditions = []

    triggered_exclusions = []
    triggered_exceptions = []

    for item in condition_results:

        if not isinstance(item, dict):
            continue

        condition = normalize_text(
            item.get(
                "condition",
                "",
            )
        )

        status = normalize_text(
            item.get(
                "status",
                "",
            )
        ).upper()

        condition_type = normalize_text(
            item.get(
                "condition_type",
                item.get(
                    "type",
                    "REQUIRED",
                ),
            )
        ).upper()

        if not condition:
            continue

        # ----------------------------------------------------
        # REQUIRED
        # ----------------------------------------------------

        if condition_type == "REQUIRED":

            if status == ANSWER_SATISFIED:

                required_satisfied.append(
                    condition
                )

            elif status in {
                "NOT_SATISFIED",
                ANSWER_UNSATISFIED,
            }:

                required_not_satisfied.append(
                    condition
                )

            elif status == ANSWER_UNKNOWN:

                unknown_conditions.append(
                    condition
                )

        # ----------------------------------------------------
        # EXCLUSION
        #
        # EXCLUSION + NOT_SATISFIED
        # = 排除条件已经触发
        # ----------------------------------------------------

        elif condition_type == "EXCLUSION":

            if status in {
                "NOT_SATISFIED",
                ANSWER_UNSATISFIED,
            }:

                triggered_exclusions.append(
                    condition
                )

            elif status == ANSWER_UNKNOWN:

                unknown_conditions.append(
                    condition
                )

        # ----------------------------------------------------
        # EXCEPTION
        #
        # EXCEPTION + NOT_SATISFIED
        # = 例外条件已经触发
        # ----------------------------------------------------

        elif condition_type == "EXCEPTION":

            if status in {
                "NOT_SATISFIED",
                ANSWER_UNSATISFIED,
            }:

                triggered_exceptions.append(
                    condition
                )

            elif status == ANSWER_UNKNOWN:

                unknown_conditions.append(
                    condition
                )

    # ========================================================
    # DEFINITE
    # ========================================================

    if engine_decision == DECISION_DEFINITE:

        return (
            "Decision Engine 已确认当前满足相关法律条件，"
            "可以作出确定性法律结论。"
        )

    # ========================================================
    # CONDITIONAL
    # ========================================================

    if engine_decision == DECISION_CONDITIONAL:

        lines = [
            "Decision Engine 判定当前法律结论为条件性结论。"
        ]

        if required_satisfied:

            lines.append(
                "当前已经确认满足以下条件："
                + "、".join(
                    required_satisfied
                )
                + "。"
            )

        if unknown_conditions:

            lines.append(
                "但当前仍存在尚未确认的条件，"
                "因此暂时不能作出确定性结论。"
            )

        if triggered_exclusions:

            lines.append(
                "同时，以下排除条件已经触发："
                + "、".join(
                    triggered_exclusions
                )
                + "。"
            )

        if triggered_exceptions:

            lines.append(
                "同时，以下例外条件已经触发："
                + "、".join(
                    triggered_exceptions
                )
                + "。"
            )

        return "\n".join(
            lines
        )

    # ========================================================
    # NOT_ESTABLISHED
    # ========================================================

    if engine_decision == DECISION_NOT_ESTABLISHED:

        lines = [
            "Decision Engine 已确认当前不能认定满足相关法律条件。"
        ]

        if required_not_satisfied:

            lines.append(
                "原因是以下必备条件已经确认未满足："
                + "、".join(
                    required_not_satisfied
                )
                + "。"
            )

        if triggered_exclusions:

            lines.append(
                "同时，以下排除条件已经触发："
                + "、".join(
                    triggered_exclusions
                )
                + "。"
            )

        if triggered_exceptions:

            lines.append(
                "同时，以下例外条件已经触发："
                + "、".join(
                    triggered_exceptions
                )
                + "。"
            )

        return "\n".join(
            lines
        )

    # ========================================================
    # 未知 Decision
    # ========================================================

    return (
        "Decision Engine 未返回有效的最终法律结论。"
    )

# ============================================================
# Replace Deterministic Conclusion
# ============================================================

def replace_deterministic_conclusion(
    answer: str,
    deterministic_conclusion: str,
) -> str:
    """
    用 Python 确定性生成的【结论】
    替换 Ollama 原有【结论】内容。

    核心原则：

    1. Ollama 不负责最终法律结论。
    2. 只替换【结论】章节。
    3. 必须保留【法律依据】。
    4. 必须保留【法律分析】。
    5. 必须保留【需要注意】。
    """

    if not answer:
        return (
            "【结论】\n"
            + deterministic_conclusion
        )

    marker = "【结论】"

    if marker not in answer:

        return (
            marker
            + "\n"
            + deterministic_conclusion
            + "\n\n"
            + answer.lstrip()
        )

    before_conclusion, after_conclusion = (
        answer.split(
            marker,
            1,
        )
    )

    next_markers = [
        "【法律依据】",
        "【法律分析】",
        "【需要注意】",
    ]

    next_positions = []

    for next_marker in next_markers:

        position = after_conclusion.find(
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

        remaining_sections = (
            after_conclusion[
                next_position:
            ].lstrip()
        )

        return (
            before_conclusion.rstrip()
            + "\n\n"
            + "【结论】"
            + "\n"
            + deterministic_conclusion
            + "\n\n"
            + remaining_sections
        )

    return (
        before_conclusion.rstrip()
        + "\n\n"
        + "【结论】"
        + "\n"
        + deterministic_conclusion
    )

# ============================================================
# Replace Deterministic Legal Basis
# ============================================================

def replace_deterministic_legal_basis(
    answer: str,
    deterministic_legal_basis: str,
) -> str:
    """
    用 Python 确定性生成的【法律依据】
    替换 Ollama 原有的【法律依据】内容。

    核心原则：

    1. Ollama 不得自行选择最终法律依据。
    2. Ollama 不得删除 Structured Rules 已确定的核心法律依据。
    3. Ollama 不得将 RELATED 法条提升为 CORE 法条。
    4. Ollama 不得增加当前 Structured Rules 之外的新法条。
    5. 只替换【法律依据】章节本身。
    6. 必须保留【法律分析】。
    7. 必须保留【需要注意】。
    8. 不允许因为替换法律依据而删除后续章节。
    """

    if not answer:
        return deterministic_legal_basis

    marker = "【法律依据】"

    if marker not in answer:
        return (
            answer.rstrip()
            + "\n\n"
            + deterministic_legal_basis
        )

    before_basis, after_basis = answer.split(
        marker,
        1,
    )

    before_basis = before_basis.rstrip()

    # --------------------------------------------------------
    # 查找【法律依据】之后的下一个正式章节
    #
    # 注意：
    #
    # 【法律依据】后面可能继续存在：
    #
    # 【法律分析】
    # 【需要注意】
    #
    # 必须保留这些章节，不能像旧版本一样
    # 直接丢弃 after_basis。
    # --------------------------------------------------------

    next_markers = [
        "【法律分析】",
        "【需要注意】",
        "【结论】",
    ]

    next_positions = []

    for next_marker in next_markers:
        position = after_basis.find(
            next_marker
        )

        if position >= 0:
            next_positions.append(
                position
            )

    # --------------------------------------------------------
    # 找到后续章节
    # --------------------------------------------------------

    if next_positions:

        next_position = min(
            next_positions
        )

        remaining_sections = (
            after_basis[
                next_position:
            ].lstrip()
        )

        return (
            before_basis
            + "\n\n"
            + deterministic_legal_basis
            + "\n\n"
            + remaining_sections
        )

    # --------------------------------------------------------
    # 没有后续章节
    #
    # 直接用确定性的法律依据替换
    # Ollama 原有法律依据。
    # --------------------------------------------------------

    return (
        before_basis
        + "\n\n"
        + deterministic_legal_basis
    )

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

    import re

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
        r"^\s*用户事实：\s*\n"
        r".*?"
        r"(?=^\s*(?:当前条件状态|条件状态|法律分析|分析结果|判断结果)\s*：)",
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
        r"^\s*用户事实：\s*\n"
        r".*\Z",
    )

    if re.search(
        r"(?ms)^\s*用户事实：\s*\n",
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
# 完整 Pipeline
# ============================================================

def answer_question(
    question: str,
    top_k: int = 5,
    score_threshold: float = 0.55,
    model: str = OLLAMA_MODEL,
) -> str:

    print()
    print("=" * 70)
    print(
        f"RAG {RAG_VERSION} - 法律智能问答"
    )
    print("=" * 70)

    question = normalize_text(question)

    print()
    print(
        f"用户问题：{question}"
    )

    if not question:

        print()
        print(
            "⚠️ 用户问题不能为空。"
        )

        return ""

    # ========================================================
    # Step 1
    # ========================================================

    context_data = build_structured_context(
        question=question,
        top_k=top_k,
        score_threshold=score_threshold,
    )

    rules = context_data.get(
        "rules",
        [],
    )

    # ========================================================
    # Step 2
    # ========================================================

    decision = run_decision_engine(
        question=question,
        rules=rules,
    )

    # ========================================================
    # Step 3
    # ========================================================

    structured_decision = run_answer_builder(
        decision=decision,
        rules=rules,
        question=question,
    )

    # ========================================================
    # Step 4
    # Ollama
    #
    # 注意：
    #
    # V6.0-11 修正：
    #
    # 这里只输出一次 Step 4 / Ollama。
    #
    # call_ollama() 本身不再重复打印 Step 4。
    # ========================================================

    prompt = build_ollama_prompt(
        question=question,
        decision=structured_decision,
    )

    try:

        print()
        print("=" * 70)
        print("Step 4 / Ollama")
        print("=" * 70)

        print()
        print(
            f"Model：{model}"
        )

        answer = call_ollama(
            prompt=prompt,
            model=model,
        )

    except Exception as exc:

        print()
        print(
            "⚠️ Ollama 调用失败："
            f"{exc}"
        )

        print()
        print(
            "⚠️ 使用纯 Python Legal Answer Builder fallback。"
        )

        answer = build_fallback_answer(
            question=question,
            decision=structured_decision,
        )

    # ========================================================
    # Step 5
    #
    # V6.0-27：
    #
    # 在 Final Validation 之前，
    # 由 Python 根据 Decision Engine 的用户事实，
    # 确定性恢复 / 覆盖 Ollama 的“用户事实”部分。
    #
    # 注意：
    #
    # 这里不是重新提取用户事实。
    #
    # 用户事实已经由 Legal Decision Engine 确定。
    #
    # Python 这里只负责保证：
    #
    #     Engine User Facts
    #            ↓
    #     Deterministic Injection
    #            ↓
    #     Final Validation
    #
    # 防止 Ollama 漏掉用户事实。
    # ========================================================

    print("\n" + "=" * 70)
    print("DEBUG / Ollama Raw Answer")
    print("=" * 70)
    print(answer)
    print("=" * 70)

    answer = inject_deterministic_user_facts(
        answer=answer,
        decision=structured_decision,
    )

    print()
    print("=" * 70)
    print("DEBUG / Deterministic User Facts Injected")
    print("=" * 70)
    print(answer)
    print("=" * 70)

    # ========================================================
    # Deterministic Legal Basis
    #
    # Ollama 不负责最终法律依据选择。
    #
    # 法律依据直接来自当前 Structured Rules，
    # 并按照 CORE / RELATED 进行确定性排序。
    #
    # 这样可以防止 Ollama 将第39条、第40条等
    # 排除条件错误地提升为核心法律依据。
    # ========================================================

    deterministic_legal_basis = build_deterministic_legal_basis(
        question=question,
        rules=rules,
    )

    answer = replace_deterministic_legal_basis(
        answer=answer,
        deterministic_legal_basis=deterministic_legal_basis,
    )

    answer = final_validation(
        answer=answer,
        question=question,
        decision=structured_decision,
    )

    # ============================================================
    # Deterministic Conclusion
    #
    # 注意：
    #
    # Final Validation 可能通过 Ollama 原始答案，
    # 但这并不意味着 Ollama 有权决定最终法律结论。
    #
    # Engine Decision 才是唯一法律决策来源。
    #
    # 因此在 Final Validation 完成以后，
    # 必须再次使用 Python 根据 Decision Engine
    # 确定性锁定【结论】。
    #
    # 这样可以防止 Ollama 出现：
    #
    # CONDITIONAL
    # ↓
    # “当前条件未满足”
    #
    # 这种错误的语义降级。
    # ============================================================

    deterministic_conclusion = (
        build_deterministic_conclusion(
            decision=structured_decision,
        )
    )

    answer = replace_deterministic_conclusion(
        answer=answer,
        deterministic_conclusion=deterministic_conclusion,
    )


    # ============================================================
    # Deterministic Notices
    #
    # 注意：
    # 必须放在 Final Validation 之后。
    # 因为 Final Validation 失败时可能启动 Fallback，
    # Fallback 会重新生成 answer。
    # 因此只有在 Final Validation 完成以后，
    # 才能最终锁定【需要注意】。
    # ============================================================

    deterministic_notices = build_deterministic_notices(
        decision=structured_decision,
    )

    answer = replace_deterministic_notices(
        answer=answer,
        deterministic_notices=deterministic_notices,
    )

    print()
    print("=" * 70)
    print("DEBUG / After Replace Deterministic Notices")
    print("=" * 70)
    print(answer)
    print("=" * 70)

    # ========================================================
    # Final Output
    # ========================================================

    print()
    print("=" * 70)
    print(
        f"RAG {RAG_VERSION} 最终回答"
    )
    print("=" * 70)

    print()
    print(answer)

    return answer


# ============================================================
# Demo Question
# ============================================================

def create_demo_question() -> str:

    return (
        "公司连续签订三次固定期限劳动合同后，"
        "是否必须签订无固定期限劳动合同？"
    )


# ============================================================
# Pipeline Test
# ============================================================

def run_pipeline_test():

    question = create_demo_question()

    return answer_question(
        question=question,
        top_k=5,
        score_threshold=0.55,
        model=OLLAMA_MODEL,
    )


# ============================================================
# Interactive Question
# ============================================================

def interactive_question():

    print()
    print("=" * 70)
    print(
        f"RAG {RAG_VERSION} Interactive Question"
    )
    print("=" * 70)

    print()
    print(
        "请输入法律问题："
    )

    try:

        question = input(
            "> "
        ).strip()

    except EOFError:

        question = ""

    if not question:

        print()
        print(
            "⚠️ 未输入问题。"
        )

        return ""

    return answer_question(
        question=question,
        top_k=5,
        score_threshold=0.55,
        model=OLLAMA_MODEL,
    )


# ============================================================
# Main Menu
# ============================================================

def main():

    print()
    print("=" * 70)
    print(
        f"RAG {RAG_VERSION}"
    )
    print("=" * 70)

    print()
    print(
        "Legal RAG Pipeline"
    )

    print()
    print(
        "请选择测试："
    )

    print()
    print(
        "1. 完整 Pipeline 测试"
    )

    print(
        "2. Component Test"
    )

    print(
        "3. 输入自定义法律问题"
    )

    print()

    try:

        choice = input(
            "请输入 1、2 或 3："
        ).strip()

    except EOFError:

        choice = "1"

    # --------------------------------------------------------
    # 完整 Pipeline
    # --------------------------------------------------------

    if choice == "1":

        run_pipeline_test()

        return

    # --------------------------------------------------------
    # Component Test
    # --------------------------------------------------------

    if choice == "2":

        component_test()

        return

    # --------------------------------------------------------
    # 自定义问题
    # --------------------------------------------------------

    if choice == "3":

        interactive_question()

        return

    # --------------------------------------------------------
    # 无效输入
    # --------------------------------------------------------

    print()
    print(
        "⚠️ 无效选择。"
    )

    print(
        "默认执行完整 Pipeline 测试。"
    )

    run_pipeline_test()


# ============================================================
# Module Entry
# ============================================================

if __name__ == "__main__":

    main()