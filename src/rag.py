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

    adapted["conclusion"] = normalize_text(
        get_field(decision, "conclusion", "")
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
    """

    print()
    print("=" * 70)
    print("Step 3 / Legal Answer Builder V6.0-14")
    print("=" * 70)

    adapted = adapt_decision_for_answer_builder(
        decision=decision,
        question=question,
    )

    adapted = merge_rules_into_decision(
        adapted_decision=adapted,
        rules=rules,
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

    adapted["fact_condition_mappings"] = build_fact_condition_mappings(
        question=question,
        user_facts=ensure_list(
            adapted.get("user_facts", [])
        ),
        rules=ensure_list(
            adapted.get("rules", [])
        ),
    )

    # merge_rules_into_decision 只补充 Retriever 法律依据，
    # 不允许改变 Engine Decision / Condition Results。
    adapted["engine_decision"] = extract_engine_decision(
        decision
    )
    adapted["raw_decision"] = decision
    adapted["engine_condition_results_count"] = len(
        ensure_list(
            get_field(
                decision,
                "condition_results",
                [],
            )
        )
    )

    print()
    print("✅ Structured Answer 已生成")
    print(
        f"Engine Decision：{adapted['engine_decision']}"
    )
    print(
        f"Structured Decision：{adapted['decision']}"
    )
    print(
        f"User Facts：{len(adapted.get('user_facts', []))}"
    )
    print(
        f"Condition Results：{len(adapted.get('condition_results', []))}"
    )
    print(
        f"REQUIRED：{len(adapted.get('required_condition_results', []))}"
    )
    print(
        f"EXCLUSION：{len(adapted.get('exclusion_condition_results', []))}"
    )
    print(
        f"EXCEPTION：{len(adapted.get('exception_results', []))}"
    )
    print(
        f"Satisfied Conditions：{len(adapted.get('satisfied_conditions', []))}"
    )
    print(
        f"Unsatisfied Conditions：{len(adapted.get('unsatisfied_conditions', []))}"
    )
    print(
        f"Unknown Conditions：{len(adapted.get('unknown_conditions', []))}"
    )
    print(
        f"Legal Rules：{len(adapted.get('rules', []))}"
    )

    return adapted


# ============================================================
# Ollama Prompt
# ============================================================

def build_ollama_prompt_v6(
    question: str,
    decision: Dict[str, Any],
) -> str:

    question = normalize_text(question)

    engine_decision = normalize_text(
        decision.get(
            "engine_decision",
            "",
        )
    )

    builder_decision = normalize_text(
        decision.get(
            "decision",
            "",
        )
    )

    conclusion = normalize_text(
        decision.get(
            "conclusion",
            "",
        )
    )

    user_facts = ensure_list(
        decision.get(
            "user_facts",
            [],
        )
    )

    satisfied = ensure_list(
        decision.get(
            "satisfied_conditions",
            [],
        )
    )

    unsatisfied = ensure_list(
        decision.get(
            "unsatisfied_conditions",
            [],
        )
    )

    unknown = ensure_list(
        decision.get(
            "unknown_conditions",
            [],
        )
    )

    rules = ensure_list(
        decision.get(
            "rules",
            [],
        )
    )

    facts_text = (
        "\n".join(
            f"- {normalize_text(item)}"
            for item in user_facts
            if normalize_text(item)
        )
        or
        "当前没有提取到明确用户事实。"
    )

    fact_condition_mappings = ensure_list(
        decision.get("fact_condition_mappings", [])
    )

    mapping_lines = []
    for mapping in fact_condition_mappings:
        if not isinstance(mapping, dict):
            continue
        fact = normalize_text(mapping.get("fact", ""))
        condition = normalize_text(mapping.get("condition", ""))
        status = normalize_text(mapping.get("status", "UNKNOWN")).upper()
        reason = normalize_text(mapping.get("reason", ""))
        if not fact or not condition:
            continue
        line = f"- 用户事实：{fact} → 法律条件：{condition} = {status}"
        if reason:
            line += f"；依据：{reason}"
        mapping_lines.append(line)

    mapping_text = "\n".join(mapping_lines) or "无。"

    satisfied_text = (
        "\n".join(
            f"- {normalize_text(item)}"
            for item in satisfied
            if normalize_text(item)
        )
        or
        "无。"
    )

    unsatisfied_text = (
        "\n".join(
            f"- {normalize_text(item)}"
            for item in unsatisfied
            if normalize_text(item)
        )
        or
        "无。"
    )

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

            if condition and reason:

                unknown_lines.append(
                    f"- {condition}：{reason}"
                )

            elif condition:

                unknown_lines.append(
                    f"- {condition}"
                )

        else:

            text = normalize_text(item)

            if text:
                unknown_lines.append(
                    f"- {text}"
                )

    unknown_text = (
        "\n".join(unknown_lines)
        or
        "无。"
    )

    rules_text = format_rules_for_display(
        rules
    )

    required_conditions = ensure_list(
        decision.get("required_conditions", [])
    )
    exclusion_conditions = ensure_list(
        decision.get("exclusion_conditions", [])
    )
    exceptions = ensure_list(
        decision.get("exceptions", [])
    )

    exclusion_results = ensure_list(
        decision.get("exclusion_condition_results", [])
    )
    exception_results = ensure_list(
        decision.get("exception_results", [])
    )

    def _category_result_text(items):
        lines = []
        for item in items:
            if not isinstance(item, dict):
                continue
            condition = normalize_text(item.get("condition", ""))
            status = normalize_text(item.get("status", "UNKNOWN")).upper()
            reason = normalize_text(item.get("reason", ""))
            if not condition:
                continue
            line = f"- [{status}] {condition}"
            if reason:
                line += f"：{reason}"
            lines.append(line)
        return "\n".join(lines) or "无。"

    required_text = "\n".join(
        f"- {normalize_text(item)}"
        for item in required_conditions
        if normalize_text(item)
    ) or "无。"

    exclusion_text = "\n".join(
        f"- {normalize_text(item)}"
        for item in exclusion_conditions
        if normalize_text(item)
    ) or "无。"

    exception_text = "\n".join(
        f"- {normalize_text(item)}"
        for item in exceptions
        if normalize_text(item)
    ) or "无。"

    # ========================================================
    # 使用普通字符串拼接。
    #
    # 不使用三引号。
    # ========================================================

    prompt_parts = []

    prompt_parts.append(
        "你是一名严谨的中国劳动法法律智能问答助手。\n"
    )

    prompt_parts.append(
        "你现在处于 RAG V6.0-27 最终回答阶段。\n"
    )

    prompt_parts.append(
        "法律判断已经由 V6.0-5 Legal Decision Engine 完成。\n"
    )

    prompt_parts.append(
        "你的任务不是重新判断法律，而是将结构化判断转换成准确、清晰、克制的中文法律回答。\n"
    )

    prompt_parts.append(
        "\n============================================================\n"
        "用户问题\n"
        "============================================================\n"
        f"{question}\n"
    )

    prompt_parts.append(
        "\n============================================================\n"
        "Fact-to-Condition Mapping（事实到法律条件映射）\n"
        "============================================================\n"
        f"{mapping_text}\n"
        "以上映射是系统已经确定的事实覆盖关系。SATISFIED 映射不得被改写为 UNKNOWN。\n"
        "映射只证明明确列出的条件，不代表其它法律条件自动成立。\n"
    )

    prompt_parts.append(
        "\n============================================================\n"
        "V6.0-5 原始 Decision\n"
        "============================================================\n"
        f"{engine_decision}\n"
    )

    prompt_parts.append(
        "\n============================================================\n"
        "V6.0-6 Answer Builder Decision\n"
        "============================================================\n"
        f"{builder_decision}\n"
    )

    prompt_parts.append(
        "\n============================================================\n"
        "结构化结论\n"
        "============================================================\n"
        f"{conclusion}\n"
    )

    prompt_parts.append(
        "\n============================================================\n"
        "用户明确事实\n"
        "============================================================\n"
        f"{facts_text}\n"
    )

    prompt_parts.append(
        "\n============================================================\n"
        "已经满足的条件\n"
        "============================================================\n"
        f"{satisfied_text}\n"
    )

    prompt_parts.append(
        "\n============================================================\n"
        "明确不满足的条件\n"
        "============================================================\n"
        f"{unsatisfied_text}\n"
    )

    prompt_parts.append(
        "\n============================================================\n"
        "尚未确认的条件\n"
        "============================================================\n"
        f"{unknown_text}\n"
    )

    prompt_parts.append(
        "\n============================================================\n"
        "必备条件（REQUIRED）\n"
        "============================================================\n"
        f"{required_text}\n"
    )

    prompt_parts.append(
        "\n============================================================\n"
        "排除条件（EXCLUSION）\n"
        "============================================================\n"
        f"{exclusion_text}\n"
        "排除条件是负向条件：需要确认不存在相应情形；UNKNOWN 不等于该情形已经存在。\n"
        f"实际判断结果：\n{_category_result_text(exclusion_results)}\n"
    )

    prompt_parts.append(
        "\n============================================================\n"
        "例外条件（EXCEPTION）\n"
        "============================================================\n"
        f"{exception_text}\n"
        "例外条件必须单独表达，不得混入普通 UNKNOWN 条件。\n"
        f"实际判断结果：\n{_category_result_text(exception_results)}\n"
    )

    prompt_parts.append(
        "\n============================================================\n"
        "结构化法律依据\n"
        "============================================================\n"
        f"{rules_text}\n"
    )

    prompt_parts.append(
        "\n============================================================\n"
        "V6.0-22 强制规则\n"
        "============================================================\n"
    )

    prompt_parts.append(
        "1. 禁止修改用户事实。\n"
        "用户明确说“三次”，必须保持“三次”。\n"
    )

    prompt_parts.append(
        "2. 必须严格区分用户事实与法律规则。\n"
    )

    prompt_parts.append(
        "3. CONDITIONAL 必须保持条件性。\n"
        "必须使用“如果……则……”或者“在……条件成立的情况下……”等表达。\n"
    )

    prompt_parts.append(
        "4. UNKNOWN 条件不得自行补充。\n"
        "如果用户没有提供相关事实，应明确说明现阶段无法确认。\n"
    )

    prompt_parts.append(
        "5. 不得增加结构化法律依据之外的新法条。\n"
    )

    prompt_parts.append(
        "6. 不得改变法律义务强度。\n"
        "不得将“可以”改成“应当”，不得将“可能”改成“一定”。\n"
    )

    prompt_parts.append(
        "7. 对《中华人民共和国劳动合同法》第十四条必须严格区分：\n"
        "‘连续订立二次固定期限劳动合同’属于法律规则中的数量门槛；"
        "‘连续签订三次固定期限劳动合同’属于用户明确提供的事实；"
        "‘续订劳动合同’属于 Structured Decision 中独立的法律条件。\n"
        "不得把三次用户事实改写成二次用户事实，也不得把三次用户事实重新改写为‘第三次合同是否属于续订劳动合同’。\n"
    )

    prompt_parts.append(
        "8. 不得因为用户说“三次固定期限劳动合同”就自动认定全部法律条件已经满足。\n"
    )

    prompt_parts.append(
        "9. 如果结构化 Decision 为 CONDITIONAL，最终结论不能写成确定性结论。\n"
    )

    prompt_parts.append(
        "10. 如果结构化 Decision 为 NOT_ESTABLISHED，不能将其改写为法律明确否定。\n"
    )

    prompt_parts.append(
        "11. 第八十二条只能在结构化 Decision 已经确认相应法律条件成立时说明法律责任。\n"
    )

    prompt_parts.append(
        "12. 不得自行重新推理、修改 Decision、删除 UNKNOWN 条件或者增加法律条件。\n"
    )

    prompt_parts.append(
        "13. 如果 Engine Decision 为 CONDITIONAL，且存在 UNKNOWN 条件，最终回答必须明确保留这些未知条件。\n"
    )

    prompt_parts.append(
        "14. V6.0-25 Fact-to-Condition Mapping / Rule Dependency 规则。\n"
        "用户事实‘连续签订三次固定期限劳动合同’已经明确证明：连续固定期限合同的数量至少达到二次，因此‘连续订立二次固定期限劳动合同’这一数量门槛为 SATISFIED。\n"
        "但是，该事实不等于劳动者已经提出或同意下一次续订、订立劳动合同，也不等于劳动者已经选择无固定期限劳动合同。\n"
        "‘续订劳动合同’是 Structured Decision 中独立的法律条件，必须按照 Engine 返回的 ConditionResult 原样表达，不得自行改变其语义。\n"
        "如果用户已经明确说明‘连续签订三次固定期限劳动合同’，不得再次把‘第三次合同是否存在’、‘第三次合同是否连续’或‘第三次合同是否属于续订劳动合同’作为新的事实 UNKNOWN。\n"
    )

    prompt_parts.append(
        "14A. 三次合同事实保护规则。\n"
        "用户明确陈述的‘连续签订三次固定期限劳动合同’必须直接作为既定用户事实使用，不得重新提问或重新判断该事实本身。\n"
        "特别禁止以下表达作为新的 UNKNOWN 或未决事实：‘第三次合同是否存在’、‘是否已经签订第三份合同’、‘第三次是否属于连续合同序列’、‘第三次合同是否属于续订劳动合同’。\n"
        "本题中‘续订劳动合同’这一条件不得被解释为‘重新确认第三次合同是否属于续订’；不得把用户已经提供的合同事实重新拆解成新的事实障碍。\n"
        "‘三次’是用户事实；‘连续订立二次固定期限劳动合同’是法律规则中的数量门槛；‘续订劳动合同’是 Structured Decision 中独立的法律条件。三者必须严格区分，不得互相替换。\n"
        "最终回答只能按照 Structured Decision 给出的 UNKNOWN 条件表达尚未确认的法律条件，不得自行增加新的 UNKNOWN。\n"
    )

    prompt_parts.append(
        "15. 严禁把‘劳动者提出或者同意续订、订立劳动合同’偷换成‘劳动者提出或者同意订立无固定期限劳动合同’。\n"
        "前者是 Structured Rule 的法律条件；后者不是同一个条件，除非 Structured Rules 明确如此表述，否则不得自行创造。\n"
        "16. 严禁把‘三次固定期限劳动合同’直接解释为劳动者已经提出或同意下一次续订，也不得解释为劳动者已经选择无固定期限劳动合同。\n"
        "17. 排除条件和例外条件必须保持独立语义：UNKNOWN 排除条件表示尚不能确认相应排除情形不存在；UNKNOWN 例外表示尚不能确认例外是否存在。不得将其改写成肯定事实。\n"
        "18. 不得自行创造 Structured Rules 中不存在的‘其他法定条件’。\n"
        "19. CONDITIONAL 必须保持条件性；如果存在 REQUIRED UNKNOWN，最终回答必须明确指出尚未确认的必备条件。\n"
        "20. 用户事实与法律规则必须同时保留：‘三次’是用户事实，‘二次’是法律规则数量门槛，两者不能互相替换。\n"
    )

    prompt_parts.append(
        "21. ‘续订劳动合同’不得解释为‘第三次劳动合同是否属于续订劳动合同’。\n"
        "当用户已经明确提供‘公司连续签订三次固定期限劳动合同’这一事实时，不得再把‘第三次是否属于续订’作为新的 UNKNOWN、未决事实或需要进一步确认的事实。\n"
        "本题中的 UNKNOWN ‘续订劳动合同’，必须严格按照 Decision Engine 返回的 ConditionResult 原文表达，不得自行转换成‘第三次合同是否属于续订’。\n"
        "也不得在法律分析、需要注意、结论中增加‘第三次合同是否属于续订’这一新的事实判断。\n"
    )

    prompt_parts.append(
    "22. 最终回答必须同时保留用户事实与法律规则。\n"
    "用户明确提供的事实‘公司连续签订三次固定期限劳动合同’不得在结论中被省略或改写为‘连续订立二次固定期限劳动合同’。\n"
    "可以同时说明‘三次事实已经达到连续订立二次固定期限劳动合同的数量门槛’，但不得用‘二次’替代用户的‘三次’事实。\n"
    )

    prompt_parts.append(
        "23. UNKNOWN 条件必须保持原始语义。\n"
        "Structured Decision 中的 UNKNOWN ‘续订劳动合同’必须直接表达为该法律条件尚未确认，不得进一步解释、扩展或改写成‘第三次合同是否属于续订’、‘第三次合同是否为续订合同’或其他对第三次合同性质的重新判断。\n"
        "最终回答不得出现‘第三次劳动合同是否属于续订’、‘第三次合同是否属于续订’、‘第三次是否属于续订’等表达。\n"
    )

    prompt_parts.append(
        "24. 严禁重新解释 UNKNOWN 条件的逻辑含义。\n"
        "Structured Decision 中的 UNKNOWN 条件‘续订劳动合同’，只能作为一个尚未确认的独立法律条件原样保留。\n"
        "不得将其改写为‘后续订立的劳动合同是否属于续订劳动合同’，也不得写成‘该后续合同属于续订劳动合同’、‘后续合同是否属于续订’、‘第三次合同是否属于续订’或其他具有相同逻辑含义的表达。\n"
        "尤其不得把‘存在后续订立的劳动合同’这一已经 SATISFIED 的条件，与 UNKNOWN 的‘续订劳动合同’合并后重新制造一个新的事实判断。\n"
        "最终回答必须严格区分：‘存在后续订立的劳动合同’是已经确认的条件；‘续订劳动合同’是 Engine 返回的 UNKNOWN 条件。二者不得互相改写、合并或推导。\n"
    )

    prompt_parts.append(
        "25. 结论必须保留用户事实。\n"
        "如果用户问题明确包含‘连续签订三次固定期限劳动合同’，结论中应优先说明‘用户已经明确提供连续签订三次固定期限劳动合同这一事实’以及该事实已经达到‘连续订立二次固定期限劳动合同’的数量门槛。\n"
        "不得在结论开头直接把用户事实改写成‘连续订立二次固定期限劳动合同’而省略‘三次’事实。\n"
        "‘二次’只能作为法律规则的最低数量门槛说明，不能替代用户已经提供的‘三次’事实。\n"
    )

    prompt_parts.append(
        "26. 结论起点必须优先使用用户事实。\n"
        "当用户问题明确陈述‘公司连续签订三次固定期限劳动合同’时，"
        "【结论】部分第一句应优先以该用户事实作为事实起点，"
        "例如‘根据你提供的事实，公司已经连续签订三次固定期限劳动合同……’。\n"
        "随后可以说明‘三次已经达到法律规则中的连续订立二次固定期限劳动合同数量门槛’，"
        "但不得在【结论】第一句直接以‘连续订立二次固定期限劳动合同’替代用户的‘三次’事实。\n"
        "‘二次’只用于说明法律规则的最低数量门槛，不能替代用户事实。\n"
    )
    
    prompt_parts.append(
        "\n============================================================\n"
        "最终回答格式\n"
        "============================================================\n"
        "必须严格使用以下四个标题，而且每个标题只能出现一次：\n\n"
        "【结论】\n"
        "【法律依据】\n"
        "【法律分析】\n"
        "【需要注意】\n"
    )

    prompt_parts.append(
        "\n最终只输出法律回答，不输出思考过程，不输出内部推理，不输出额外说明。\n"
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

# ============================================================
# 用户事实验证
# ============================================================

def validate_user_facts(
    answer: str,
    decision: Dict[str, Any],
) -> bool:
    """
    V6.0-27：用户事实保真验证。

    核心原则：

    1. Ollama 不得修改用户已经确认的事实。
    2. 用户事实中的合同次数必须保持一致。
    3. “两次”不能被改写成“三次”。
    4. “三次”不能被改写成“两次”。
    5. “两次”问题不能被模型自行扩张成“三次合同已经签订”。
    6. 法律规则中的“连续订立二次固定期限劳动合同”可以正常出现，
       但不能被误当成新的用户事实。
    """

    facts = ensure_list(
        decision.get(
            "user_facts",
            [],
        )
    )

    if not facts:
        return True

    fact_text = "；".join(
        normalize_text(item)
        for item in facts
    )

    answer_text = normalize_text(answer)

    # ========================================================
    # 两次固定期限劳动合同
    # ========================================================

    has_two_fact = (
        "两次" in fact_text
        and "固定期限劳动合同" in fact_text
    ) or (
        "二次" in fact_text
        and "固定期限劳动合同" in fact_text
    )

    if has_two_fact:

        # -----------------------------------------------
        # 用户明确是“两次”，最终回答必须保留这一事实。
        # -----------------------------------------------

        if not (
            "两次" in answer_text
            or "二次" in answer_text
        ):
            return False

        # -----------------------------------------------
        # 禁止将“两次”扩张成“三次”用户事实。
        #
        # 注意：
        #
        # 法律规则中的“连续订立二次固定期限劳动合同”
        # 是允许出现的。
        #
        # 这里禁止的是明确把用户事实写成“三次”。
        # -----------------------------------------------

        wrong_three_fact_patterns = [
            "公司连续签订三次固定期限劳动合同",
            "公司连续订立三次固定期限劳动合同",
            "公司已经连续签订三次固定期限劳动合同",
            "公司已经连续订立三次固定期限劳动合同",
            "用户连续签订三次固定期限劳动合同",
            "用户连续订立三次固定期限劳动合同",
            "已连续签订三次固定期限劳动合同",
            "已连续订立三次固定期限劳动合同",
            "已经连续签订三次固定期限劳动合同",
            "已经连续订立三次固定期限劳动合同",
        ]

        for pattern in wrong_three_fact_patterns:

            if pattern in answer_text:
                return False

    # ========================================================
    # 三次固定期限劳动合同
    # ========================================================

    has_three_fact = (
        "三次" in fact_text
        and "固定期限劳动合同" in fact_text
    )

    if has_three_fact:

        if "三次" not in answer_text:
            return False

        # -----------------------------------------------
        # 禁止将“三次”用户事实改写成“二次”用户事实。
        # -----------------------------------------------

        wrong_two_fact_patterns = [
            "用户连续签订二次固定期限劳动合同",
            "用户连续订立二次固定期限劳动合同",
            "公司连续签订二次固定期限劳动合同",
            "公司连续订立二次固定期限劳动合同",
            "用户事实是二次固定期限劳动合同",
            "用户事实为二次固定期限劳动合同",
            "用户实际签订二次固定期限劳动合同",
            "公司实际签订二次固定期限劳动合同",
        ]

        for pattern in wrong_two_fact_patterns:

            if pattern in answer_text:
                return False

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
    V6.0-15 UNKNOWN 语义验证。

    V6.0-13 的问题是：
    UNKNOWN 验证只接受少量固定关键词。
    Ollama 即使正确表达“该事实目前无法确认”，
    只要没有命中固定词表，也会被误判为 UNKNOWN FAIL。

    V6.0-15 改为“语义标记 + 结构化 UNKNOWN 内容”双重验证：

    1. 接受多种表达“未知/待核实/材料不足/无法作出最终判断”的句式。
    2. 同时允许 UNKNOWN 条件本身出现在回答中。
    3. 对明显的确定性表达保持保守，不因为出现“条件”二字就通过。
    """

    unknown = ensure_list(
        decision.get(
            "unknown_conditions",
            [],
        )
    )

    if not unknown:
        return True

    answer_text = normalize_text(answer)

    if not answer_text:
        return False

    # --------------------------------------------------------
    # 第一层：广义 UNKNOWN / 待确认语义标记
    # --------------------------------------------------------
    #
    # 不再依赖单一固定短语。
    # 这些表达均可以合理表示“当前材料不足以确认”。
    # --------------------------------------------------------

    unresolved_patterns = [
        "未提供",
        "尚未提供",
        "没有提供",
        "未说明",
        "尚未说明",
        "没有说明",
        "未明确",
        "尚未明确",
        "尚不明确",
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

    if any(pattern in answer_text for pattern in unresolved_patterns):
        return True

    # --------------------------------------------------------
    # 第二层：检查结构化 UNKNOWN 条件是否被保留。
    # --------------------------------------------------------
    #
    # 某些模型会直接写：
    #   “是否存在……，这一点需要结合现有材料进一步判断。”
    # 而不会使用“无法确认”等固定词。
    # 因此，只要回答保留 UNKNOWN 条件的主要内容，并使用
    # “是否/存在/取决于/视……而定”等未决结构，也允许通过。
    # --------------------------------------------------------

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
    ]

    for item in unknown:

        if isinstance(item, dict):
            condition = normalize_text(
                item.get(
                    "condition",
                    "",
                )
            )
        else:
            condition = normalize_text(item)

        if not condition:
            continue

        # 去除过长条件中的标点，只保留若干有辨识度的片段。
        condition_core = re.sub(
            r"[，。；：、（）()【】\[\]“”‘’：;,.!?！？]",
            " ",
            condition,
        )
        condition_tokens = [
            token
            for token in condition_core.split()
            if len(token) >= 2
        ]

        # 中文条件通常没有空格，因此进一步提取连续短语。
        if not condition_tokens:
            condition_tokens = [
                condition[:12],
                condition[:8],
            ]

        condition_mentioned = any(
            token and token in answer_text
            for token in condition_tokens
        )

        if condition_mentioned and any(
            pattern in answer_text
            for pattern in unresolved_structure_patterns
        ):
            return True

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
    """

    if not answer:
        return False

    normalized_rules = build_rules_from_articles(
        ensure_list(rules)
    )

    if not normalized_rules:
        # 没有结构化 Rules 时，不应凭空制造法律依据。
        # 如果回答没有明确法条引用，则保持结构验证通过；
        # 一旦出现明确引用，则必须失败。
        citation_pattern = (
            r"《\s*([^》]+?)\s*》\s*第\s*"
            r"([一二三四五六七八九十百千万零两\d]+)\s*条"
        )
        return not re.findall(citation_pattern, answer)

    allowed_keys = set()

    # --------------------------------------------------------
    # V6.0-27：区分“法律依据法条”和“结构化规则中的交叉引用”
    # --------------------------------------------------------
    #
    # 本次实际失败原因：
    #
    # Structured Rules 共有 5 条法律规则：
    #     第十四条、第十一条、第八十二条、第二十条、第十三条
    #
    # 但是第十四条的 exclusion_conditions 本身合法地引用了：
    #     《劳动合同法》第三十九条
    #     《劳动合同法》第四十条第一项
    #     《劳动合同法》第四十条第二项
    #
    # Fallback 为了忠实输出这些结构化条件，会在法律分析中出现上述
    # 法条。V6.0-22 只把 Rule 的 article_number 作为 allowed_keys，
    # 因此把“当前结构化规则明确引用的法条”误判成“新发明的法条”。
    #
    # 正确原则：
    #     1. 法律依据部分不能引用当前规则体系之外的新法条；
    #     2. 但 Structured Rule 自己明确引用的法条，可以在分析中出现；
    #     3. 不因此把新的法律知识添加进 Retriever。
    #
    # 所以这里同时收集：
    #     A. Rule 自身的主法条；
    #     B. Rule 中已经存在的 references / conditions / exclusion_conditions
    #        / exceptions / legal_obligations / legal_consequences 等交叉引用。

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

        if law_name and article_number:
            allowed_keys.add(
                _citation_key(
                    law_name,
                    article_number,
                )
            )

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
                    source_text = str(item) if item is not None else ""

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

    citation_pattern = (
        r"《\s*([^》]+?)\s*》\s*第\s*"
        r"([一二三四五六七八九十百千万零两\d]+)\s*条"
    )

    citations = re.findall(
        citation_pattern,
        answer,
    )

    if not citations:
        return True

    for law_name, article_raw in citations:
        article_value = _chinese_article_to_int(article_raw)
        if article_value is None:
            return False

        normalized_law_name = _normalize_law_name(law_name)
        if not normalized_law_name:
            return False

        key = (
            normalized_law_name,
            f"第{article_value}条",
        )

        if key in allowed_keys:
            continue

        return False

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

        # NOT_ESTABLISHED 不允许出现明显确定满足表达。

        forbidden = [
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

    def run_checks(text: str) -> List[str]:
        failures: List[str] = []

        if not text:
            failures.append("EMPTY")
            return failures

        if not validate_engine_condition_completeness(decision):
            failures.append("ENGINE_CONDITION_COMPLETENESS")

        if not validate_condition_categories(decision):
            failures.append("CONDITION_CATEGORY")

        if not validate_answer_structure(text):
            failures.append("STRUCTURE")

        if not validate_user_facts(text, decision):
            failures.append("USER_FACTS")

        if not validate_three_contract_fact(text, decision):
            failures.append("THREE_CONTRACT_FACT")

        if not validate_fact_condition_mapping(
            text,
            question,
            decision,
        ):
            failures.append("FACT_CONDITION_MAPPING")

        if not validate_no_manufactured_unknown(
            text,
            decision,
        ):
            failures.append("MANUFACTURED_UNKNOWN")

        if not validate_legal_condition_invention(
            text,
            decision,
        ):
            failures.append("LEGAL_CONDITION_INVENTION")

        if not validate_conditional_state(
            text,
            decision,
        ):
            failures.append("CONDITIONAL")

        if not validate_unknown_conditions(
            text,
            decision,
        ):
            failures.append("UNKNOWN")

        rules = ensure_list(
            decision.get("rules", [])
        )

        if not validate_legal_basis(
            text,
            rules,
        ):
            failures.append("LEGAL_BASIS")

        if not validate_decision_consistency(
            text,
            decision,
        ):
            failures.append("DECISION_CONSISTENCY")

        return failures

    failures = run_checks(answer)

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

    fallback_failures = run_checks(fallback)

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
    V6.0-22 确定性 Python Fallback。

    重要原则：

    1. 不调用 Ollama。
    2. 不重新进行法律推理。
    3. 不修改 Decision。
    4. 不删除 UNKNOWN。
    5. 不把用户事实改写成法律规则。
    6. 法律依据只来自结构化 Rules。
    7. 最终结果仍然必须通过 Final Validation。

    V6.0-10 的问题是：

        Ollama Validation FAIL
                ↓
        build_plain_answer()
                ↓
        THREE_CONTRACT_FACT FAIL

    V6.0-13 不再让旧版 Answer Builder 作为安全 Fallback 的最终
    事实来源，而是直接使用已经完成的 Structured Answer 数据生成
    一个确定性的四段式回答。
    """

    print()
    print("=" * 70)
    print("Fallback / Deterministic Legal Answer Builder V6.0-25")
    print("=" * 70)

    question = normalize_text(question)

    engine_decision = normalize_text(
        decision.get(
            "engine_decision",
            decision.get("decision", ""),
        )
    ).upper()

    user_facts = unique_texts(
        ensure_list(
            decision.get(
                "user_facts",
                [],
            )
        )
    )

    satisfied = unique_texts(
        ensure_list(
            decision.get(
                "satisfied_conditions",
                [],
            )
        )
    )

    unsatisfied = unique_texts(
        ensure_list(
            decision.get(
                "unsatisfied_conditions",
                [],
            )
        )
    )

    unknown = ensure_list(
        decision.get(
            "unknown_conditions",
            [],
        )
    )

    rules = build_rules_from_articles(
        ensure_list(
            decision.get(
                "rules",
                [],
            )
        )
    )

    # --------------------------------------------------------
    # 结论
    # --------------------------------------------------------
    #
    # CONDITIONAL 必须保持条件性。
    #
    # 不使用旧 Answer Builder 的自然语言结果，避免它重新解释
    # 用户事实或丢失 UNKNOWN。
    # --------------------------------------------------------

    if engine_decision == DECISION_CONDITIONAL:

        if satisfied:
            conclusion_lines = [
                "根据现有事实及已经确认的结构化条件，当前至少已经满足以下条件："
                + "、".join(satisfied)
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
        elif not unsatisfied:
            conclusion_lines.append(
                "当前结构化 Decision 未确认其他未知条件，但仍应严格按照 Decision Engine 的 CONDITIONAL 结论处理。"
            )

    elif engine_decision == DECISION_DEFINITE:

        conclusion_lines = [
            "根据已经确认的结构化法律条件，可以按照 Decision Engine 的确定性结论处理。",
        ]

    else:

        conclusion_lines = [
            "根据现有事实，当前尚不能确认相关法律条件已经成立。",
        ]

    # --------------------------------------------------------
    # 用户事实
    # --------------------------------------------------------

    fact_lines = []

    if user_facts:
        for fact in user_facts:
            fact_text = normalize_text(fact)
            if fact_text:
                fact_lines.append(
                    f"- {fact_text}"
                )
    else:
        fact_lines.append(
            "- 当前没有提取到明确用户事实。"
        )

    # --------------------------------------------------------
    # 已满足条件
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # 未满足条件
    # --------------------------------------------------------

    unsatisfied_lines = []

    if unsatisfied:
        for item in unsatisfied:
            unsatisfied_lines.append(
                f"- {item}"
            )
    else:
        unsatisfied_lines.append(
            "- 无。"
        )

    # --------------------------------------------------------
    # 分类条件结果
    # --------------------------------------------------------

    required_conditions = unique_texts(
        ensure_list(
            decision.get(
                "required_conditions",
                [],
            )
        )
    )

    exclusion_results = ensure_list(
        decision.get(
            "exclusion_condition_results",
            [],
        )
    )

    exception_results = ensure_list(
        decision.get(
            "exception_results",
            [],
        )
    )

    unknown_lines = []

    for item in unknown:
        if isinstance(item, dict):
            condition = normalize_text(item.get("condition", ""))
            reason = normalize_text(item.get("reason", ""))
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
            condition = normalize_text(item)
            if condition:
                unknown_lines.append(
                    f"- {condition}"
                )

    if not unknown_lines:
        unknown_lines.append("- 无。")

    def format_category_results(items, empty="- 无。"):
        lines = []
        for item in items:
            if not isinstance(item, dict):
                continue
            condition = normalize_text(item.get("condition", ""))
            status = normalize_text(item.get("status", "UNKNOWN")).upper()
            reason = normalize_text(item.get("reason", ""))
            if not condition:
                continue
            line = f"- [{status}] {condition}"
            if reason:
                line += f"：{reason}"
            lines.append(line)
        return lines or [empty]

    exclusion_lines = format_category_results(exclusion_results)
    exception_lines = format_category_results(exception_results)

    # --------------------------------------------------------
    # 法律依据
    # --------------------------------------------------------
    #
    # 绝不凭记忆增加法条。
    # 所有法律依据直接来自当前 Structured Rules。
    # --------------------------------------------------------

    core_basis_lines = []
    related_basis_lines = []
    seen_basis = set()

    rules = prioritize_legal_rules(
        question=question,
        rules=rules,
    )

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

        if not law_name or not article_number:
            continue

        citation = (
            f"《{law_name}》"
            f"{article_number}"
        )

        if citation in seen_basis:
            continue

        seen_basis.add(citation)

        priority = normalize_text(
            rule.get(
                "rule_priority",
                "RELATED",
            )
        ).upper()

        if priority == "CORE":
            core_basis_lines.append(citation)
        else:
            related_basis_lines.append(citation)

    # V6.0-16：核心依据与相关依据分层展示。
    # 不删除 Rules，只改变最终答案的呈现层级。
    basis_lines = []

    if core_basis_lines:
        basis_lines.append("【核心法律依据】")
        basis_lines.extend(
            f"{index}. {citation}"
            for index, citation in enumerate(
                core_basis_lines,
                1,
            )
        )

    if related_basis_lines:
        basis_lines.append("【相关法律依据】")
        start_index = len(core_basis_lines) + 1
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

    # --------------------------------------------------------
    # 法律分析
    # --------------------------------------------------------

    analysis_lines = []

    analysis_lines.append(
        "1. 用户事实："
    )
    analysis_lines.extend(
        fact_lines
    )

    analysis_lines.append(
        "2. 已确认条件："
    )
    analysis_lines.extend(
        satisfied_lines
    )

    analysis_lines.append(
        "3. 未满足条件："
    )
    analysis_lines.extend(
        unsatisfied_lines
    )

    analysis_lines.append(
        "4. 尚未确认的必备条件："
    )
    analysis_lines.extend(
        unknown_lines
    )

    analysis_lines.append(
        "5. 排除条件："
    )
    analysis_lines.extend(
        exclusion_lines
    )

    analysis_lines.append(
        "6. 例外条件："
    )
    analysis_lines.extend(
        exception_lines
    )

    if engine_decision == DECISION_CONDITIONAL:

        analysis_lines.append(
            "7. 法律后果："
        )
        analysis_lines.append(
            "- 当前属于条件性结论，在关键事实尚未确认之前，不能直接将条件性 Decision 转换为确定性结论。"
        )

    elif engine_decision == DECISION_DEFINITE:

        analysis_lines.append(
            "7. 法律后果："
        )
        analysis_lines.append(
            "- 按照已经确认的结构化 Decision 处理。"
        )

    else:

        analysis_lines.append(
            "7. 法律后果："
        )
        analysis_lines.append(
            "- 当前尚不能确认相关法律条件已经成立。"
        )

    # --------------------------------------------------------
    # 需要注意
    # --------------------------------------------------------

    notice_lines = []

    if user_facts:
        for fact in user_facts:
            fact_text = normalize_text(fact)
            if fact_text:
                notice_lines.append(
                    f"- 用户明确描述的是“{fact_text}”，该事实应保持原意。"
                )

    if (
        any(
            "三次" in normalize_text(item)
            and "固定期限劳动合同" in normalize_text(item)
            for item in user_facts
        )
    ):
        notice_lines.append(
            "- “连续签订三次固定期限劳动合同”是用户事实，必须保持原意，不能把用户事实改写成“二次”。"
        )
        notice_lines.append(
            "- “连续订立二次固定期限劳动合同”可以作为法律规则中的数量门槛出现；这里的“二次”是法律条件表达，不是对用户“三次”事实的替换。"
        )
        notice_lines.append(
            "- 事实映射：用户“三次”事实已经覆盖“连续订立二次固定期限劳动合同”的数量门槛；该映射不代表其它法律条件自动成立。"
        )

    if unknown:
        notice_lines.append(
            "- 当前存在尚未确认的必备条件，不能自行将 UNKNOWN 条件视为已经成立。"
        )
        notice_lines.append(
            "- 排除条件与例外条件单独保留，不得把它们混入普通 UNKNOWN 条件。"
        )
        notice_lines.append(
            "- 尚未确认条件及其原因均以 Structured Decision 为准，Fallback 不自行增加新的法律条件。"
        )

    if not notice_lines:
        notice_lines.append(
            "- 最终回答仅依据当前结构化 Decision 和 Rules，不新增结构化数据之外的法律判断。"
        )

    # --------------------------------------------------------
    # 组装四段式答案
    # --------------------------------------------------------

    answer = (
        SECTION_CONCLUSION
        + "\n"
        + "\n".join(conclusion_lines)
        + "\n\n"
        + SECTION_BASIS
        + "\n"
        + "\n".join(basis_lines)
        + "\n\n"
        + SECTION_ANALYSIS
        + "\n"
        + "\n".join(analysis_lines)
        + "\n\n"
        + SECTION_NOTICE
        + "\n"
        + "\n".join(notice_lines)
    )

    return clean_answer(answer)


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

    prompt = build_ollama_prompt_v6(
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
    # ========================================================
    
    answer = final_validation(
        answer=answer,
        question=question,
        decision=structured_decision,
    )

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