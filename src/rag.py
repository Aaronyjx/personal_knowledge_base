# -*- coding: utf-8 -*-

# ============================================================
# RAG V6.0-23
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

from src.legal_decision_engine import make_decision

from src.legal_answer_builder import (
    build_plain_answer,
    get_value,
    safe_text,
)


# ============================================================
# 常量
# ============================================================

RAG_VERSION = "V6.0-23"

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

        law_name = rule.get("law_name", "")

        article_number = rule.get(
            "article_number",
            "",
        )

        summary = rule.get(
            "rule_summary",
            "",
        )

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
    V6.0-23：取消 Adapter 层的法律条件推理。

    核心原则：

    1. Legal Decision Engine 是唯一的法律条件判定来源。
    2. Adapter 不得根据问题、用户事实或 Rules 自行创造
       SATISFIED / UNSATISFIED / UNKNOWN 条件。
    3. 特别禁止自动生成“其他法定情形”等笼统 UNKNOWN。
    4. 保留函数只是为了兼容旧接口；V6.0-22 默认返回空列表。
    5. 如果 Engine 返回 CONDITIONAL 但 Condition Results = 0，
       必须由 Engine 本身修复输出，而不是由 Adapter 猜测条件。
    """

    # V6.0-23：故意不进行任何条件补全。
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


def adapt_decision_for_answer_builder(
    decision: Any,
    question: str = "",
) -> Dict[str, Any]:
    """
    V6.0-22 Decision Adapter。

    核心修复：

    1. 保留 Legal Decision Engine 的全部 Condition Results。
    2. 根据 Structured Rules 将 Condition Results 分类为：
           REQUIRED / EXCLUSION / EXCEPTION
    3. Exclusion / Exception 不再错误塞入 unknown_conditions。
    4. unknown_conditions 只保存“必备条件”中的 UNKNOWN。
    5. 同时保留 category-specific condition results，供 Answer Builder
       和 Final Validation 使用。
    6. 不在 Adapter 层重新进行任何法律事实判断。
    """

    engine_status = extract_engine_decision(decision)

    if engine_status == DECISION_DEFINITE:
        builder_status = ANSWER_SATISFIED
    elif engine_status == DECISION_NOT_ESTABLISHED:
        builder_status = ANSWER_UNSATISFIED
    else:
        builder_status = ANSWER_CONDITIONAL

    conclusion = normalize_text(
        get_field(decision, "conclusion", "")
    )

    facts = ensure_list(
        get_field(decision, "facts", [])
    )

    user_facts = []
    for fact in facts:
        text = extract_fact_text(fact)
        if text:
            user_facts.append(text)

    normalized_question = normalize_text(question)

    if (
        "三次" in normalized_question
        and "固定期限劳动合同" in normalized_question
    ):
        canonical_three_fact = "公司连续签订三次固定期限劳动合同"
        if not any(
            "三次" in normalize_text(item)
            and "固定期限劳动合同" in normalize_text(item)
            for item in user_facts
        ):
            user_facts.append(canonical_three_fact)

    user_facts = unique_texts(user_facts)

    selected_rules = ensure_list(
        get_field(decision, "rules", [])
    )
    normalized_rules = build_rules_from_articles(selected_rules)
    category_map = _condition_category_map(normalized_rules)

    raw_condition_results = ensure_list(
        get_field(decision, "condition_results", [])
    )

    # 如果 Engine 返回的 Rule 中已经带有 category/type 字段，优先读取；
    # 否则使用 Structured Rules 的字段归属进行确定性分类。
    required_results = []
    exclusion_results = []
    exception_results = []

    satisfied_conditions = []
    unsatisfied_conditions = []
    unknown_conditions = []

    all_condition_results = []

    for condition_result in raw_condition_results:
        condition_name = normalize_text(
            get_first_field(
                condition_result,
                ["condition", "name", "text"],
                "",
            )
        )

        if not condition_name:
            continue

        status = normalize_text(
            get_field(condition_result, "status", "")
        ).upper()

        reason = normalize_text(
            get_field(condition_result, "reason", "")
        )

        explicit_category = normalize_text(
            get_first_field(
                condition_result,
                ["category", "condition_category", "type"],
                "",
            )
        ).upper()

        if explicit_category in {
            "REQUIRED",
            "EXCLUSION",
            "EXCEPTION",
        }:
            category = explicit_category
        else:
            category = category_map.get(
                condition_name,
                "REQUIRED",
            )

        item = {
            "condition": condition_name,
            "status": status or "UNKNOWN",
            "category": category,
        }

        if reason:
            item["reason"] = reason

        all_condition_results.append(item)

        if category == "EXCLUSION":
            exclusion_results.append(item)
        elif category == "EXCEPTION":
            exception_results.append(item)
        else:
            required_results.append(item)

        # Answer Builder 的传统状态列表只统计 REQUIRED 条件。
        # Exclusion / Exception 单独保存，避免语义污染。
        if category != "REQUIRED":
            continue

        if status == "SATISFIED":
            satisfied_conditions.append(condition_name)
        elif status in {"NOT_SATISFIED", "UNSATISFIED"}:
            unsatisfied_conditions.append(condition_name)
        else:
            unknown_item = {"condition": condition_name}
            if reason:
                unknown_item["reason"] = reason
            unknown_conditions.append(unknown_item)

    required_conditions = _condition_list_from_rule(
        normalized_rules,
        ["conditions", "required_conditions"],
    )
    exclusion_conditions = _condition_list_from_rule(
        normalized_rules,
        ["exclusion_conditions", "exclusions"],
    )
    exceptions = _condition_list_from_rule(
        normalized_rules,
        ["exceptions", "exception_conditions"],
    )

    # 去重，保持顺序。
    satisfied_conditions = unique_texts(satisfied_conditions)
    unsatisfied_conditions = unique_texts(unsatisfied_conditions)

    dedup_unknown = []
    seen_unknown = set()
    for item in unknown_conditions:
        condition = _condition_text(item)
        reason = normalize_text(
            item.get("reason", "")
            if isinstance(item, dict)
            else ""
        )
        key = (condition, reason)
        if not condition or key in seen_unknown:
            continue
        seen_unknown.add(key)
        value = {"condition": condition}
        if reason:
            value["reason"] = reason
        dedup_unknown.append(value)

    unknown_conditions = dedup_unknown

    return {
        "decision": builder_status,
        "engine_decision": engine_status,
        "conclusion": conclusion,
        "user_facts": user_facts,
        "required_conditions": required_conditions,
        "exclusion_conditions": exclusion_conditions,
        "exceptions": exceptions,
        "required_condition_results": required_results,
        "exclusion_condition_results": exclusion_results,
        "exception_results": exception_results,
        "condition_results": all_condition_results,
        "satisfied_conditions": satisfied_conditions,
        "unsatisfied_conditions": unsatisfied_conditions,
        "unknown_conditions": unknown_conditions,
        "engine_condition_results_count": len(raw_condition_results),
        "engine_output_incomplete": (
            engine_status == DECISION_CONDITIONAL
            and not raw_condition_results
        ),
        "rules": normalized_rules,
        "raw_decision": decision,
    }


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
    print("Step 2 / Legal Decision Engine V6.0-10-FIXED")
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
            "facts",
            [],
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

    print()
    print("=" * 70)
    print("Step 3 / Legal Answer Builder V6.0-7")
    print("=" * 70)

    adapted = adapt_decision_for_answer_builder(
        decision,
        question=question,
    )

    adapted = merge_rules_into_decision(
        adapted_decision=adapted,
        rules=rules,
    )

    print()
    print(
        "✅ Structured Answer 已生成"
    )

    print(
        f"Engine Decision："
        f"{adapted['engine_decision']}"
    )

    print(
        f"Structured Decision："
        f"{adapted['decision']}"
    )

    print(
        f"User Facts："
        f"{len(adapted['user_facts'])}"
    )

    print(
        f"Satisfied Conditions："
        f"{len(adapted['satisfied_conditions'])}"
    )

    print(
        f"Unsatisfied Conditions："
        f"{len(adapted['unsatisfied_conditions'])}"
    )

    print(
        f"Unknown Conditions："
        f"{len(adapted['unknown_conditions'])}"
    )

    print(
        f"Legal Rules："
        f"{len(adapted['rules'])}"
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
        "你现在处于 RAG V6.0-23 最终回答阶段。\n"
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
        "连续订立二次固定期限劳动合同、第三次续订劳动合同、"
        "用户实际所称连续签订三次固定期限劳动合同。\n"
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
        "14. 特别规则：用户事实‘连续签订三次固定期限劳动合同’不得被解释为与‘连续订立二次固定期限劳动合同后第三次续订’当然冲突。\n"
        "在本题语境下，‘连续签订三次固定期限劳动合同’已经明确包含三次合同、连续合同序列以及第三份合同已经签订这一事实。\n"
        "因此不得再制造‘第三次合同是否存在’、‘是否已经签订第三份合同’、‘第三次是否属于连续合同序列’或‘第三次合同是否属于续订’作为 UNKNOWN。\n"
        "尤其不得输出‘第三次合同是否属于续订需进一步确认’、‘第三次是否属于续订情形尚不明确’等与已确认用户事实重复冲突的未知条件。\n"
        "该用户事实可以直接满足法律规则中的‘连续订立二次固定期限劳动合同’数量门槛；这里的‘二次’是法律规则的最低数量门槛，不是对用户‘三次’事实的改写。\n"
        "如果需要保留 UNKNOWN，只能针对用户确实没有提供、且属于结构化法律规则要求的其他法定条件或法定例外。\n"
    )

    prompt_parts.append(
        "15. 严禁自行创造结构化 Rules 中没有出现的法律条件、前置条件或法定例外。\n"
        "如果某个条件没有出现在 Structured Rules / Decision 中，不得为了让 CONDITIONAL 更完整而自行补充。\n"
        "16. 特别禁止把‘劳动者未提出/未明确提出订立或签订无固定期限劳动合同’写成签订无固定期限劳动合同的前置条件，除非该条件在 Structured Rules 中明确出现。\n"
        "17. 不得用‘劳动者不符合无固定期限劳动合同的条件’、‘劳动者不符合订立无固定期限劳动合同的条件’等笼统表述制造新的法律例外。必须对应具体 Structured Rule。\n"
        "18. ‘其他法定条件’不能作为模型自行增加的兜底法律条件。只有 Structured Rules 明确存在对应条件时，才能引用该条件。\n"
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

def validate_user_facts(
    answer: str,
    decision: Dict[str, Any],
) -> bool:

    facts = ensure_list(
        decision.get(
            "user_facts",
            [],
        )
    )

    if not facts:
        return True

    # 核心事实保护。
    #
    # 不要求所有 Fact 必须逐字出现，
    # 因为自然语言表达允许合理改写。
    #
    # 但是“三次固定期限劳动合同”
    # 属于当前 Demo 的核心事实，
    # 必须进行专项检查。

    fact_text = "；".join(
        normalize_text(item)
        for item in facts
    )

    if (
        "三次" in fact_text
        and
        "固定期限劳动合同" in fact_text
    ):

        if "三次" not in answer:
            return False

        wrong_patterns = [
            "用户连续签订二次固定期限劳动合同",
            "用户连续订立二次固定期限劳动合同",
            "公司连续签订二次固定期限劳动合同",
            "公司连续订立二次固定期限劳动合同",
        ]

        for pattern in wrong_patterns:

            if pattern in answer:
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
    V6.0-18：禁止 Ollama 对已经明确确认的用户事实再次制造 UNKNOWN。

    当前重点保护：
        用户事实“连续签订三次固定期限劳动合同”。

    该事实已经明确包含三次合同及连续合同序列。
    因此，以下问题不能再次被当成未知事实：
        - 第三次合同是否存在
        - 是否已经签订第三份合同
        - 第三次是否属于连续合同序列
        - 第三次合同是否属于续订

    注意：
        “第三次续订”作为法律规则的描述可以出现；
        只有将上述事项写成“是否……、尚不明确、需进一步确认”等未知
        判断时才判定为 Validation 失败。
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

    answer_text = normalize_text(answer)

    # 明确禁止的“重复事实确认”型 UNKNOWN。
    forbidden_unknown_patterns = [
        "第三次合同是否存在",
        "第三次合同是否已经存在",
        "第三份合同是否存在",
        "第三份合同是否已经存在",
        "是否已经签订第三份合同",
        "是否已经签订第三次合同",
        "第三次是否属于连续合同序列",
        "第三次合同是否属于连续合同序列",
        "第三次是否属于续订",
        "第三次合同是否属于续订",
        "第三次是否属于续订情形",
        "第三次合同是否属于续订情形",
        "第三次续订是否明确",
        "第三次续订是否成立",
    ]

    # 只有当这些表达附近同时出现明显 UNKNOWN 语义时才拦截，
    # 避免正常法律规则说明中的“第三次续订”被误伤。
    unresolved_markers = [
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

    for pattern in forbidden_unknown_patterns:
        if pattern not in answer_text:
            continue

        if any(marker in answer_text for marker in unresolved_markers):
            return False

    # 对最常见的完整错误句式进行直接拦截。
    direct_forbidden = [
        "第三次合同是否属于续订需进一步确认",
        "第三次合同是否属于续订需要进一步确认",
        "第三次是否属于续订情形尚不明确",
        "第三次合同是否属于续订情形尚不明确",
        "第三次是否属于续订需要进一步确认",
        "第三次合同是否属于续订需要进一步判断",
    ]

    for pattern in direct_forbidden:
        if pattern in answer_text:
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
    V6.0-23：法律条件防臆造验证。

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
    # 注意：这里不是简单禁止“劳动者提出”四个字。
    # 因为某些真实法律规则本身可能包含“劳动者提出”的条件。
    # 只禁止本题中典型的错误法律命题：
    #     “劳动者没有/未提出无固定期限合同”
    #     → 被当成必须签无固定期限合同的前置条件。
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
    V6.0-23 法律依据验证。

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
    # V6.0-23：区分“法律依据法条”和“结构化规则中的交叉引用”
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
    V6.0-23：验证 Engine 的 Condition Results 完整性。

    V6.0-21 的问题：

        Decision Engine 返回的是 DecisionResult 对象，
        Adapter 将其保存为 raw_decision。

        原验证逻辑只接受：
            isinstance(raw_decision, dict)

        因此真实的 DecisionResult 对象会被错误读取成 0 条 Condition Results，
        即使 Step 2 已经打印出：
            Condition Results：7

    V6.0-22 修复：

        1. 优先读取 Adapter 已保存的 engine_condition_results_count。
        2. 同时兼容 dict / object 两种 raw_decision。
        3. CONDITIONAL + 真实 Condition Results > 0 才通过。
        4. 不再因为 DecisionResult 是对象而误报 ENGINE_CONDITION_COMPLETENESS。
    """

    if not isinstance(decision, dict):
        return False

    engine_decision = normalize_text(
        decision.get("engine_decision", "")
    ).upper()

    if engine_decision != DECISION_CONDITIONAL:
        return True

    count = decision.get(
        "engine_condition_results_count",
        None,
    )

    if isinstance(count, int):
        return count > 0

    raw_decision = decision.get("raw_decision")

    raw_results = get_field(
        raw_decision,
        "condition_results",
        [],
    )

    return len(ensure_list(raw_results)) > 0


# ============================================================
# Condition Category / Completeness Validation
# ============================================================

def validate_condition_categories(
    decision: Dict[str, Any],
) -> bool:
    """
    V6.0-23：验证 Adapter 是否正确保留三类法律条件。

    REQUIRED / EXCLUSION / EXCEPTION 必须严格分开。
    该检查只验证数据结构，不重新进行法律判断。
    """

    if not isinstance(decision, dict):
        return False

    required = set(
        _condition_list_from_rule(
            ensure_list(decision.get("rules", [])),
            ["conditions", "required_conditions"],
        )
    )
    exclusion = set(
        _condition_list_from_rule(
            ensure_list(decision.get("rules", [])),
            ["exclusion_conditions", "exclusions"],
        )
    )
    exceptions = set(
        _condition_list_from_rule(
            ensure_list(decision.get("rules", [])),
            ["exceptions", "exception_conditions"],
        )
    )

    # 三类结构之间不应出现同名交叉。
    if required & exclusion:
        return False
    if required & exceptions:
        return False
    if exclusion & exceptions:
        return False

    # unknown_conditions 只能来自 REQUIRED。
    for item in ensure_list(decision.get("unknown_conditions", [])):
        condition = _condition_text(item)
        if not condition:
            continue
        if condition not in required:
            return False

    return True


def final_validation(
    answer: str,
    question: str,
    decision: Dict[str, Any],
) -> str:
    """
    V6.0-13 最终回答验证。

    与 V6.0-9 的关键区别：

    如果 Ollama 输出没有通过关键安全验证，V6.0-10 不再直接把
    未通过验证的回答作为最终答案返回，而是自动切换到 Python
    Fallback，再进行一次验证。
    """

    print()
    print("=" * 70)
    print("Step 5 / Final Validation")
    print("=" * 70)

    answer = clean_answer(answer)

    def run_checks(text: str) -> List[str]:
        failures = []

        if not text:
            failures.append("EMPTY")
            return failures

        if not validate_answer_structure(text):
            failures.append("STRUCTURE")

        if not validate_user_facts(text, decision):
            failures.append("USER_FACTS")

        if not validate_three_contract_fact(text, decision):
            failures.append("THREE_CONTRACT_FACT")

        if not validate_no_manufactured_unknown(text, decision):
            failures.append("MANUFACTURED_UNKNOWN")

        if not validate_legal_condition_invention(text, decision):
            failures.append("LEGAL_CONDITION_INVENTION")

        if not validate_conditional_state(text, decision):
            failures.append("CONDITIONAL")

        if not validate_unknown_conditions(text, decision):
            failures.append("UNKNOWN")

        if not validate_condition_categories(decision):
            failures.append("CONDITION_CATEGORY")

        rules = ensure_list(
            decision.get("rules", [])
        )

        if not validate_legal_basis(text, rules):
            failures.append("LEGAL_BASIS")

        if not validate_decision_consistency(text, decision):
            failures.append("DECISION_CONSISTENCY")

        # V6.0-23：CONDITIONAL 必须具有真实的 Condition Results。
        # 如果 Engine 输出 CONDITIONAL + 0 Condition Results，
        # 后续 Adapter / Ollama 不得猜测法律条件，必须直接判定
        # Engine 输出不完整并进入安全 Fallback。
        if not validate_engine_condition_completeness(decision):
            failures.append("ENGINE_CONDITION_COMPLETENESS")

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

    print()
    print("⚠️ V6.0-22 启用安全 Fallback。")

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
    return fallback


# ============================================================
# Python Fallback
# ============================================================

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
    print("Fallback / Deterministic Legal Answer Builder V6.0-22")
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

    print()
    print("=" * 70)
    print(
        f"RAG {RAG_VERSION} Component Test"
    )
    print("=" * 70)

    question = (
        "公司连续签订三次固定期限劳动合同后，"
        "是否必须签订无固定期限劳动合同？"
    )

    print()
    print(
        f"问题：{question}"
    )

    # --------------------------------------------------------
    # Step 1
    # --------------------------------------------------------

    context_data = build_structured_context(
        question=question,
        top_k=5,
        score_threshold=0.55,
    )

    rules = context_data.get(
        "rules",
        [],
    )

    # --------------------------------------------------------
    # Step 2
    # --------------------------------------------------------

    decision = run_decision_engine(
        question=question,
        rules=rules,
    )

    # --------------------------------------------------------
    # Step 3
    # --------------------------------------------------------

    adapted = run_answer_builder(
        decision=decision,
        rules=rules,
        question=question,
    )

    print()
    print("=" * 70)
    print("Component Test Result")
    print("=" * 70)

    print()
    print(
        f"Engine Decision："
        f"{adapted['engine_decision']}"
    )

    print(
        f"Builder Decision："
        f"{adapted['decision']}"
    )

    print(
        f"Rules："
        f"{len(adapted['rules'])}"
    )

    print(
        f"Facts："
        f"{len(adapted['user_facts'])}"
    )

    print(
        f"Unknown Conditions："
        f"{len(adapted['unknown_conditions'])}"
    )

    print()
    print(
        "✅ Component Test 完成"
    )

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