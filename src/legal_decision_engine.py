# -*- coding: utf-8 -*-

"""
RAG V6.0-10
Legal Decision Engine

============================================================
功能
============================================================

本模块负责：

    用户问题
        ↓
    显式事实提取
        ↓
    核心法律规则选择
        ↓
    法律规则条件匹配
        ↓
    条件状态判断
        ↓
    综合法律决策
        ↓
    DecisionResult
        ↓
    Legal Answer Builder

============================================================
V6.0-10 核心升级
============================================================

1. Retriever 返回的多条法律依据不再直接互相竞争最终结论。
2. 增加 Core Rule Selection，优先识别真正负责回答问题的核心规则。
3. 对“是否必须签订无固定期限劳动合同”类问题，优先选择
   《劳动合同法》第十四条作为核心决策规则。
4. 空条件规则不得直接产生 DEFINITE。
5. 只有存在有效条件、全部必要条件明确满足、排除条件明确满足、
   且例外条件明确排除时，才允许 DEFINITE。
6. 只要核心规则仍存在 UNKNOWN，就保持 CONDITIONAL。
7. 用户事实“连续签订三次固定期限劳动合同”必须保持原意。
8. “三次”可以满足法律规则中的“连续订立二次”数量门槛，
   但不得被改写成用户事实“二次”。
9. “三次固定期限合同”不得自动证明“第三次属于续订”。
10. “劳动者提出或者同意”采用 OR 逻辑，任一明确事实即可满足。
11. 第三十九条、第四十条属于排除条件：
       明确不存在 → SATISFIED
       明确存在   → NOT_SATISFIED
       未提供     → UNKNOWN
12. “劳动者提出订立固定期限劳动合同”属于例外条件：
       明确提出 → NOT_SATISFIED
       未提供   → UNKNOWN
13. 保持 V6.0-6 Legal Answer Builder 所依赖的标准接口：
       DecisionResult
       Fact
       ConditionResult
       satisfied_conditions
       not_satisfied_conditions
       unknown_conditions
       facts
       rules

============================================================
重要设计原则
============================================================

Retriever 的职责：

    找到可能相关的法律依据。

Legal Decision Engine 的职责：

    从相关依据中识别核心规则，并进行结构化条件判断。

Legal Answer Builder 的职责：

    把结构化法律判断转换成回答结构。

Ollama 的职责：

    只负责自然语言表达，不重新决定法律结论。

============================================================
"""

from typing import List, Dict, Optional, Any, Tuple


# ============================================================
# Decision Status
# ============================================================

SATISFIED = "SATISFIED"
NOT_SATISFIED = "NOT_SATISFIED"
UNKNOWN = "UNKNOWN"


# ============================================================
# Decision Result Status
# ============================================================

DEFINITE = "DEFINITE"
CONDITIONAL = "CONDITIONAL"
NOT_ESTABLISHED = "NOT_ESTABLISHED"


# ============================================================
# Rule Types
# ============================================================

RULE_DUTY = "义务规则"
RULE_AUTHORIZATION = "授权规则"
RULE_PROHIBITION = "禁止规则"
RULE_DEFINITION = "定义规则"


# ============================================================
# Fact Status
# ============================================================

FACT_EXPLICIT = "EXPLICIT"


# ============================================================
# Fact
# ============================================================

class Fact:
    """用户明确提供的事实。"""

    def __init__(
        self,
        fact: str,
        status: str = FACT_EXPLICIT,
    ):
        self.fact = fact
        self.status = status

    def to_dict(self) -> Dict[str, str]:
        return {
            "fact": self.fact,
            "status": self.status,
        }

    def __str__(self) -> str:
        return self.fact

    def __repr__(self) -> str:
        return repr(self.to_dict())


# ============================================================
# Condition Result
# ============================================================

class ConditionResult:
    """单个法律条件的结构化判断结果。"""

    def __init__(
        self,
        condition: str,
        status: str,
        reason: str = "",
    ):
        self.condition = condition
        self.status = status
        self.reason = reason

    def to_dict(self) -> Dict[str, str]:
        return {
            "condition": self.condition,
            "status": self.status,
            "reason": self.reason,
        }

    def __str__(self) -> str:
        return (
            f"[{self.status}] "
            f"{self.condition}"
        )

    def __repr__(self) -> str:
        return repr(self.to_dict())


# ============================================================
# Decision Result
# ============================================================

class DecisionResult:
    """
    V6.0-10-FIXED 标准 Decision Result。

    保持与现有 Legal Answer Builder 的兼容接口。
    """

    def __init__(
        self,
        decision: str,
        conclusion: str,
        condition_results: Optional[List[ConditionResult]] = None,
        facts: Optional[List[Fact]] = None,
        rules: Optional[List[Dict]] = None,
    ):
        self.decision = decision
        self.conclusion = conclusion
        self.condition_results = condition_results or []
        self.facts = facts or []
        self.rules = rules or []

    @property
    def satisfied_conditions(self) -> List[ConditionResult]:
        return [
            item
            for item in self.condition_results
            if item.status == SATISFIED
        ]

    @property
    def not_satisfied_conditions(self) -> List[ConditionResult]:
        return [
            item
            for item in self.condition_results
            if item.status == NOT_SATISFIED
        ]

    @property
    def unknown_conditions(self) -> List[ConditionResult]:
        return [
            item
            for item in self.condition_results
            if item.status == UNKNOWN
        ]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision": self.decision,
            "conclusion": self.conclusion,
            "facts": [
                item.to_dict()
                for item in self.facts
            ],
            # V6.0-10-FIXED：标准字段。
            #
            # RAG / Decision Adapter 优先读取 condition_results。
            # 保留 conditions 作为旧版 Answer Builder 的兼容字段。
            "condition_results": [
                item.to_dict()
                for item in self.condition_results
            ],
            "conditions": [
                item.to_dict()
                for item in self.condition_results
            ],
            "satisfied_conditions": [
                item.to_dict()
                for item in self.satisfied_conditions
            ],
            "not_satisfied_conditions": [
                item.to_dict()
                for item in self.not_satisfied_conditions
            ],
            "unknown_conditions": [
                item.to_dict()
                for item in self.unknown_conditions
            ],
            "rules": self.rules,
        }

    def __repr__(self) -> str:
        return repr(self.to_dict())


# ============================================================
# Question Fact Extraction
# ============================================================

def extract_explicit_facts(question: str) -> List[Fact]:
    """
    从用户问题中提取明确事实。

    原则：

        只记录用户明确说出的事实。
        不根据法律规则反向制造事实。

    特别注意：

        “三次固定期限劳动合同”

    必须作为独立用户事实保留。
    """

    facts: List[Fact] = []

    if not question:
        return facts

    text = str(question).strip()

    def add(fact_text: str) -> None:
        if not any(item.fact == fact_text for item in facts):
            facts.append(Fact(fact_text))

    # --------------------------------------------------------
    # 三次固定期限劳动合同
    # --------------------------------------------------------
    if (
        ("三次" in text or "三份" in text)
        and "固定期限劳动合同" in text
    ):
        add("连续签订三次固定期限劳动合同")

    # --------------------------------------------------------
    # 二次固定期限劳动合同
    # --------------------------------------------------------
    if (
        "二次" in text
        and "固定期限劳动合同" in text
    ):
        add("连续订立二次固定期限劳动合同")

    # --------------------------------------------------------
    # 明确出现第三次续订
    # --------------------------------------------------------
    if "第三次" in text and "续订" in text:
        add("第三次属于续订劳动合同")

    # --------------------------------------------------------
    # 明确出现续订劳动合同
    # --------------------------------------------------------
    if (
        "续订劳动合同" in text
        and "第三次" not in text
    ):
        add("存在续订劳动合同")

    # --------------------------------------------------------
    # 劳动者提出
    # --------------------------------------------------------
    if "劳动者提出" in text:
        add("劳动者提出续订或者订立劳动合同")

    # --------------------------------------------------------
    # 劳动者同意
    # --------------------------------------------------------
    if "劳动者同意" in text:
        add("劳动者同意续订或者订立劳动合同")

    # --------------------------------------------------------
    # 明确不存在第三十九条
    # --------------------------------------------------------
    if (
        "不存在第三十九条" in text
        or "没有第三十九条" in text
        or "不属于第三十九条" in text
    ):
        add(
            "劳动者不存在《劳动合同法》第三十九条规定的情形"
        )

    # --------------------------------------------------------
    # 明确存在第三十九条
    # --------------------------------------------------------
    if (
        "存在第三十九条" in text
        or "符合第三十九条" in text
        or "属于第三十九条" in text
    ):
        add(
            "劳动者存在《劳动合同法》第三十九条规定的情形"
        )

    # --------------------------------------------------------
    # 明确不存在第四十条
    # --------------------------------------------------------
    if (
        "不存在第四十条" in text
        or "没有第四十条" in text
        or "不属于第四十条" in text
    ):
        add(
            "劳动者不存在《劳动合同法》第四十条第一项、第二项规定的情形"
        )

    # --------------------------------------------------------
    # 明确存在第四十条
    # --------------------------------------------------------
    if (
        "存在第四十条" in text
        or "符合第四十条" in text
        or "属于第四十条" in text
    ):
        add(
            "劳动者存在《劳动合同法》第四十条第一项、第二项规定的情形"
        )

    # --------------------------------------------------------
    # 劳动者明确提出订立固定期限劳动合同
    # --------------------------------------------------------
    if "劳动者提出订立固定期限劳动合同" in text:
        add("劳动者提出订立固定期限劳动合同")

    # --------------------------------------------------------
    # 明确不存在例外
    # --------------------------------------------------------
    if (
        "劳动者没有提出订立固定期限劳动合同" in text
        or "劳动者未提出订立固定期限劳动合同" in text
        or "劳动者不要求订立固定期限劳动合同" in text
    ):
        add("劳动者未提出订立固定期限劳动合同")

    return facts


# ============================================================
# Fact Matching Helpers
# ============================================================

def fact_contains(
    facts: List[Fact],
    keywords: List[str],
) -> bool:
    """判断用户明确事实中是否存在指定关键词组合。"""
    for fact in facts:
        text = fact.fact or ""
        if all(keyword in text for keyword in keywords):
            return True
    return False


def _fact_exists(
    facts: List[Fact],
    text: str,
) -> bool:
    target = (text or "").strip()
    if not target:
        return False
    return any(
        (fact.fact or "").strip() == target
        for fact in facts
    )


def _fact_contains_phrase(
    facts: List[Fact],
    phrase: str,
) -> bool:
    phrase = (phrase or "").strip()
    if not phrase:
        return False
    return any(
        phrase in (fact.fact or "")
        for fact in facts
    )


# ============================================================
# Condition Matching
# ============================================================

def match_condition(
    condition: str,
    facts: List[Fact],
) -> ConditionResult:
    """
    V6.0-10 条件匹配器。

    不允许从“没有事实”推导“事实不存在”。
    """

    condition = (condition or "").strip()

    if not condition:
        return ConditionResult(
            condition,
            UNKNOWN,
            "法律条件为空，无法根据用户明确事实进行判断。",
        )

    # ========================================================
    # 连续订立二次固定期限劳动合同
    # ========================================================
    if (
        "连续订立二次固定期限劳动合同" in condition
        or "连续签订二次固定期限劳动合同" in condition
    ):
        if _fact_contains_phrase(
            facts,
            "连续订立二次固定期限劳动合同",
        ):
            return ConditionResult(
                condition,
                SATISFIED,
                "用户明确提供了连续订立二次固定期限劳动合同的事实。",
            )

        if _fact_contains_phrase(
            facts,
            "连续签订三次固定期限劳动合同",
        ):
            return ConditionResult(
                condition,
                SATISFIED,
                "用户明确说明连续签订三次固定期限劳动合同，因此合同次数已经达到法律规则中的至少二次数量门槛；该判断不改变用户原始事实，也不等同于确认第三次属于续订。",
            )

        return ConditionResult(
            condition,
            UNKNOWN,
            "用户没有明确提供连续订立二次固定期限劳动合同的事实。",
        )

    # ========================================================
    # 续订劳动合同
    # ========================================================
    if "续订劳动合同" in condition:
        if _fact_contains_phrase(
            facts,
            "第三次属于续订劳动合同",
        ):
            return ConditionResult(
                condition,
                SATISFIED,
                "用户明确说明第三次属于续订劳动合同。",
            )

        if _fact_contains_phrase(
            facts,
            "存在续订劳动合同",
        ):
            return ConditionResult(
                condition,
                SATISFIED,
                "用户明确说明存在续订劳动合同。",
            )

        return ConditionResult(
            condition,
            UNKNOWN,
            "用户没有明确说明相关合同是否属于法律意义上的续订劳动合同。",
        )

    # ========================================================
    # 劳动者提出或者同意续订、订立劳动合同
    # ========================================================
    if (
        "劳动者提出或者同意" in condition
        or (
            "劳动者" in condition
            and "提出" in condition
            and "同意" in condition
            and "订立" in condition
        )
    ):
        has_propose = _fact_contains_phrase(
            facts,
            "劳动者提出续订或者订立劳动合同",
        )
        has_agree = _fact_contains_phrase(
            facts,
            "劳动者同意续订或者订立劳动合同",
        )

        if has_propose or has_agree:
            return ConditionResult(
                condition,
                SATISFIED,
                "用户明确提供了劳动者提出或者同意续订、订立劳动合同的事实。",
            )

        return ConditionResult(
            condition,
            UNKNOWN,
            "用户没有提供劳动者是否提出或者同意续订、订立劳动合同的事实。",
        )

    # ========================================================
    # 第三十九条排除条件
    # ========================================================
    if "第三十九条" in condition:
        has_exist = _fact_contains_phrase(
            facts,
            "劳动者存在《劳动合同法》第三十九条规定的情形",
        )
        has_not_exist = _fact_contains_phrase(
            facts,
            "劳动者不存在《劳动合同法》第三十九条规定的情形",
        )

        if has_exist:
            return ConditionResult(
                condition,
                NOT_SATISFIED,
                "用户明确说明劳动者存在第三十九条规定的情形，因此该排除条件不能满足。",
            )

        if has_not_exist:
            return ConditionResult(
                condition,
                SATISFIED,
                "用户明确说明劳动者不存在第三十九条规定的情形。",
            )

        return ConditionResult(
            condition,
            UNKNOWN,
            "用户没有提供劳动者是否存在第三十九条规定情形的事实。",
        )

    # ========================================================
    # 第四十条第一项排除条件
    # ========================================================
    if "第四十条第一项" in condition:
        has_exist = _fact_contains_phrase(
            facts,
            "劳动者存在《劳动合同法》第四十条第一项、第二项规定的情形",
        )
        has_not_exist = _fact_contains_phrase(
            facts,
            "劳动者不存在《劳动合同法》第四十条第一项、第二项规定的情形",
        )

        if has_exist:
            return ConditionResult(
                condition,
                NOT_SATISFIED,
                "用户明确说明存在第四十条相关情形，因此该排除条件不能满足。",
            )

        if has_not_exist:
            return ConditionResult(
                condition,
                SATISFIED,
                "用户明确说明不存在第四十条第一项、第二项规定的情形。",
            )

        return ConditionResult(
            condition,
            UNKNOWN,
            "用户没有提供是否存在第四十条第一项规定情形的事实。",
        )

    # ========================================================
    # 第四十条第二项排除条件
    # ========================================================
    if "第四十条第二项" in condition:
        has_exist = _fact_contains_phrase(
            facts,
            "劳动者存在《劳动合同法》第四十条第一项、第二项规定的情形",
        )
        has_not_exist = _fact_contains_phrase(
            facts,
            "劳动者不存在《劳动合同法》第四十条第一项、第二项规定的情形",
        )

        if has_exist:
            return ConditionResult(
                condition,
                NOT_SATISFIED,
                "用户明确说明存在第四十条相关情形，因此该排除条件不能满足。",
            )

        if has_not_exist:
            return ConditionResult(
                condition,
                SATISFIED,
                "用户明确说明不存在第四十条第一项、第二项规定的情形。",
            )

        return ConditionResult(
            condition,
            UNKNOWN,
            "用户没有提供是否存在第四十条第二项规定情形的事实。",
        )

    # ========================================================
    # 劳动者提出订立固定期限劳动合同：例外
    # ========================================================
    if "劳动者提出订立固定期限劳动合同" in condition:
        if _fact_contains_phrase(
            facts,
            "劳动者提出订立固定期限劳动合同",
        ):
            return ConditionResult(
                condition,
                NOT_SATISFIED,
                "用户明确说明劳动者提出订立固定期限劳动合同，因此该例外成立，核心义务不能直接成立。",
            )

        if _fact_contains_phrase(
            facts,
            "劳动者未提出订立固定期限劳动合同",
        ):
            return ConditionResult(
                condition,
                SATISFIED,
                "用户明确说明劳动者未提出订立固定期限劳动合同，因此该例外未成立。",
            )

        return ConditionResult(
            condition,
            UNKNOWN,
            "用户没有说明劳动者是否主动提出订立固定期限劳动合同。",
        )

    # ========================================================
    # 其他条件：保守 UNKNOWN
    # ========================================================
    return ConditionResult(
        condition,
        UNKNOWN,
        "当前规则匹配器无法仅根据用户明确事实判断该法律条件。",
    )


# ============================================================
# Normalize Rule
# ============================================================

def normalize_rule(rule: Dict) -> Dict:
    """对法律规则进行轻量规范化，避免输入异常导致 Engine 崩溃。"""

    if not isinstance(rule, dict):
        return {}

    normalized = {
        "law_name": rule.get("law_name", ""),
        "article_number": rule.get("article_number", ""),
        "classification": rule.get("classification", ""),
        "rule_type": rule.get("rule_type", ""),
        "rule_summary": rule.get("rule_summary", ""),
        "conditions": rule.get("conditions", []),
        "exclusion_conditions": rule.get("exclusion_conditions", []),
        "exceptions": rule.get("exceptions", []),
        "legal_obligations": rule.get("legal_obligations", []),
        "legal_consequences": rule.get("legal_consequences", []),
        "references": rule.get("references", []),
    }

    for key in [
        "conditions",
        "exclusion_conditions",
        "exceptions",
        "legal_obligations",
        "legal_consequences",
        "references",
    ]:
        if not isinstance(normalized[key], list):
            normalized[key] = []

    return normalized


# ============================================================
# Core Rule Selection
# ============================================================

def _rule_text(rule: Dict) -> str:
    """提取规则中的可检索文本。"""

    parts: List[str] = []

    for key in [
        "law_name",
        "article_number",
        "classification",
        "rule_type",
        "rule_summary",
    ]:
        value = rule.get(key, "")
        if value:
            parts.append(str(value))

    for key in [
        "conditions",
        "exclusion_conditions",
        "exceptions",
        "legal_obligations",
        "legal_consequences",
        "references",
    ]:
        values = rule.get(key, [])
        if isinstance(values, list):
            parts.extend(str(item) for item in values if item)

    return " ".join(parts)


def _is_labor_contract_indefinite_question(question: str) -> bool:
    """识别无固定期限劳动合同核心问题。"""

    if not question:
        return False

    text = str(question)

    has_contract = "劳动合同" in text
    has_indefinite = (
        "无固定期限" in text
        or "无固定期限劳动合同" in text
    )
    has_repeated = any(
        token in text
        for token in [
            "二次",
            "三次",
            "连续",
            "续订",
            "固定期限",
        ]
    )

    return has_contract and has_indefinite and has_repeated


def score_core_rule(
    question: str,
    rule: Dict,
) -> int:
    """
    对候选规则进行轻量相关性评分。

    目的不是重新做语义检索，而是避免 Retriever 返回的
    辅助法条直接抢走核心法律决策。
    """

    rule = normalize_rule(rule)
    text = _rule_text(rule)

    score = 0

    law_name = str(rule.get("law_name", ""))
    article = str(rule.get("article_number", ""))
    rule_type = str(rule.get("rule_type", ""))
    summary = str(rule.get("rule_summary", ""))

    # --------------------------------------------------------
    # 第十四条：无固定期限劳动合同核心规则
    # --------------------------------------------------------
    if _is_labor_contract_indefinite_question(question):
        if "第十四条" in article:
            score += 100

        if "第十四条" in text:
            score += 30

        if "无固定期限劳动合同" in text:
            score += 40

        if "连续订立二次固定期限劳动合同" in text:
            score += 30

        if "义务规则" in rule_type:
            score += 20

        if "劳动合同法" in law_name:
            score += 10

    # --------------------------------------------------------
    # 通用问题词匹配
    # --------------------------------------------------------
    question_keywords = [
        "无固定期限劳动合同",
        "固定期限劳动合同",
        "续订",
        "连续签订",
        "连续订立",
        "必须",
        "应当",
    ]

    for keyword in question_keywords:
        if keyword in question and keyword in text:
            score += 3

    if "义务规则" in rule_type:
        score += 2

    if summary and "无固定期限" in summary:
        score += 8

    return score


def select_core_rules(
    question: str,
    rules: List[Dict],
) -> List[Dict]:
    """
    从 Retriever 返回的规则中选择核心决策规则。

    V6.0-10 原则：

        Retriever 返回 8 条依据
                ↓
        不代表 8 条规则都参与最终结论竞争
                ↓
        先选择核心规则
                ↓
        再做条件判断

    对第十四条问题：

        优先选择《劳动合同法》第十四条。

    如果无法识别明确核心规则：

        选择最高评分的义务规则；
        若最高分仍为 0，则选择有有效条件的义务规则。

    空条件规则不会作为核心 DEFINITE 来源。
    """

    normalized_rules = [
        normalize_rule(rule)
        for rule in rules
        if isinstance(rule, dict)
    ]

    if not normalized_rules:
        return []

    scored: List[Tuple[int, int, Dict]] = []

    for index, rule in enumerate(normalized_rules):
        score = score_core_rule(question, rule)
        scored.append((score, -index, rule))

    # --------------------------------------------------------
    # 对第十四条核心问题做强制优先
    # --------------------------------------------------------
    if _is_labor_contract_indefinite_question(question):
        article_14 = [
            item
            for item in normalized_rules
            if "第十四条" in str(item.get("article_number", ""))
            and "劳动合同法" in str(item.get("law_name", ""))
        ]

        if article_14:
            # 保持一个核心规则即可，避免辅助规则抢结论。
            return [article_14[0]]

    # --------------------------------------------------------
    # 通用：优先义务规则
    # --------------------------------------------------------
    duty_rules = [
        item
        for item in normalized_rules
        if item.get("rule_type") == RULE_DUTY
    ]

    if duty_rules:
        duty_scored = [
            (score_core_rule(question, rule), rule)
            for rule in duty_rules
        ]
        duty_scored.sort(key=lambda x: x[0], reverse=True)

        best_score, best_rule = duty_scored[0]

        if best_score > 0:
            return [best_rule]

        # 没有语义评分时，仍然只选择第一条有有效条件的义务规则。
        for rule in duty_rules:
            if (
                rule.get("conditions")
                or rule.get("exclusion_conditions")
                or rule.get("exceptions")
            ):
                return [rule]

    # --------------------------------------------------------
    # 最后保护：只选择有有效条件的规则
    # --------------------------------------------------------
    valid_rules = [
        rule
        for rule in normalized_rules
        if (
            rule.get("conditions")
            or rule.get("exclusion_conditions")
            or rule.get("exceptions")
        )
    ]

    if valid_rules:
        valid_rules.sort(
            key=lambda rule: score_core_rule(question, rule),
            reverse=True,
        )
        return [valid_rules[0]]

    # 所有规则均没有有效条件。
    return []


# ============================================================
# Evaluate Rule
# ============================================================

def evaluate_rule(
    rule: Dict,
    facts: List[Fact],
) -> Dict:
    """
    判断单条核心法律规则。

    conditions：
        必须满足。

    exclusion_conditions：
        必须明确不存在相应情形。

    exceptions：
        一旦明确成立，则阻断法律义务。
        未知时不能假定例外不存在。
    """

    rule = normalize_rule(rule)

    condition_results: List[ConditionResult] = []
    exception_results: List[ConditionResult] = []

    # ========================================================
    # 普通条件
    # ========================================================
    for condition in rule["conditions"]:
        condition_results.append(
            match_condition(condition, facts)
        )

    # ========================================================
    # 排除条件
    # ========================================================
    for condition in rule["exclusion_conditions"]:
        condition_results.append(
            match_condition(condition, facts)
        )

    # ========================================================
    # 例外条件
    # ========================================================
    for exception in rule["exceptions"]:
        exception_results.append(
            match_condition(exception, facts)
        )

    # ========================================================
    # 空条件保护
    # ========================================================
    all_results = condition_results + exception_results

    if not all_results:
        return {
            "status": UNKNOWN,
            "reason": (
                "当前法律规则没有结构化条件，不能仅凭规则本身直接认定法律义务成立。"
            ),
            "conditions": [],
            "exceptions": [],
            "rule": rule,
        }

    # ========================================================
    # 普通条件状态
    # ========================================================
    condition_not_satisfied = [
        item
        for item in condition_results
        if item.status == NOT_SATISFIED
    ]

    condition_unknown = [
        item
        for item in condition_results
        if item.status == UNKNOWN
    ]

    # ========================================================
    # 例外状态
    # ========================================================
    exception_established = [
        item
        for item in exception_results
        if item.status == NOT_SATISFIED
    ]

    exception_unknown = [
        item
        for item in exception_results
        if item.status == UNKNOWN
    ]

    # ========================================================
    # 优先：明确存在阻断条件
    # ========================================================
    if condition_not_satisfied:
        return {
            "status": NOT_SATISFIED,
            "reason": (
                "至少一个必要法律条件已经被用户明确事实否定，"
                "因此当前核心法律规则不能成立。"
            ),
            "conditions": [
                item.to_dict()
                for item in condition_results
            ],
            "exceptions": [
                item.to_dict()
                for item in exception_results
            ],
            "rule": rule,
        }

    if exception_established:
        return {
            "status": NOT_SATISFIED,
            "reason": (
                "存在已经由用户明确事实确认成立的法律例外，"
                "因此当前核心法律义务不能直接成立。"
            ),
            "conditions": [
                item.to_dict()
                for item in condition_results
            ],
            "exceptions": [
                item.to_dict()
                for item in exception_results
            ],
            "rule": rule,
        }

    # ========================================================
    # UNKNOWN 优先保持条件性
    # ========================================================
    if condition_unknown or exception_unknown:
        unknown_parts = condition_unknown + exception_unknown
        names = "、".join(
            item.condition
            for item in unknown_parts
        )

        return {
            "status": UNKNOWN,
            "reason": (
                "核心法律规则仍存在尚未由用户事实确认的必要条件或例外条件："
                + names
            ),
            "conditions": [
                item.to_dict()
                for item in condition_results
            ],
            "exceptions": [
                item.to_dict()
                for item in exception_results
            ],
            "rule": rule,
        }

    # ========================================================
    # 所有有效条件明确满足
    # ========================================================
    return {
        "status": SATISFIED,
        "reason": (
            "当前核心法律规则的全部结构化必要条件均得到用户明确事实支持，"
            "且没有明确成立的排除或例外情形。"
        ),
        "conditions": [
            item.to_dict()
            for item in condition_results
        ],
        "exceptions": [
            item.to_dict()
            for item in exception_results
        ],
        "rule": rule,
    }


# ============================================================
# Evaluation Result Conversion
# ============================================================

def _condition_results_from_evaluation(
    evaluation: Dict,
) -> List[ConditionResult]:
    """将 evaluate_rule 返回值转换为标准 ConditionResult。"""

    results: List[ConditionResult] = []

    for item in evaluation.get("conditions", []):
        if isinstance(item, dict):
            results.append(
                ConditionResult(
                    item.get("condition", ""),
                    item.get("status", UNKNOWN),
                    item.get("reason", ""),
                )
            )

    for item in evaluation.get("exceptions", []):
        if isinstance(item, dict):
            results.append(
                ConditionResult(
                    item.get("condition", ""),
                    item.get("status", UNKNOWN),
                    item.get("reason", ""),
                )
            )

    return results


# ============================================================
# Main Decision
# ============================================================

def make_decision(
    question: str,
    rules: List[Dict],
) -> DecisionResult:
    """
    V6.0-10 综合法律决策。

    核心流程：

        Retriever Rules
              ↓
        Core Rule Selection
              ↓
        Evaluate Core Rule
              ↓
        SATISFIED / UNKNOWN / NOT_SATISFIED
              ↓
        DecisionResult

    重要：

        “任意一条 Retriever 规则 SATISFIED”

    不再等同于：

        DEFINITE

    只有“核心规则全部必要条件明确满足”才可以 DEFINITE。
    """

    facts = extract_explicit_facts(question)

    if not rules:
        return DecisionResult(
            decision=NOT_ESTABLISHED,
            conclusion=(
                "当前没有可用于判断的结构化法律规则，无法作出法律结论。"
            ),
            facts=facts,
            rules=[],
        )

    # ========================================================
    # 核心规则选择
    # ========================================================
    core_rules = select_core_rules(
        question,
        rules,
    )

    if not core_rules:
        return DecisionResult(
            decision=NOT_ESTABLISHED,
            conclusion=(
                "当前检索结果中没有可用于结构化条件判断的核心法律规则，"
                "因此不能直接作出确定法律结论。"
            ),
            facts=facts,
            rules=[],
        )

    # ========================================================
    # 核心规则评价
    # ========================================================
    evaluations: List[Dict] = []

    for rule in core_rules:
        evaluations.append(
            evaluate_rule(rule, facts)
        )

    # 当前 V6.0-10 只选择一个核心规则。
    # 这里保留列表结构，为后续多规则 AND/OR 扩展做接口准备。
    evaluation = evaluations[0]
    status = evaluation.get("status", UNKNOWN)

    condition_results = _condition_results_from_evaluation(
        evaluation
    )

    selected_rules = [
        evaluation.get("rule", core_rules[0])
    ]

    rule = selected_rules[0]
    summary = rule.get("rule_summary", "")

    # ========================================================
    # DEFINITE
    # ========================================================
    if status == SATISFIED:
        conclusion = (
            summary
            or "根据现有用户明确事实，核心法律规则的全部必要条件已经明确满足。"
        )

        return DecisionResult(
            decision=DEFINITE,
            conclusion=conclusion,
            condition_results=condition_results,
            facts=facts,
            rules=selected_rules,
        )

    # ========================================================
    # CONDITIONAL
    # ========================================================
    if status == UNKNOWN:
        conclusion = (
            "根据现有用户明确事实，核心法律规则的部分条件已经得到支持，"
            "但仍存在尚未确认的关键法律条件，因此目前只能作出条件性结论。"
        )

        return DecisionResult(
            decision=CONDITIONAL,
            conclusion=conclusion,
            condition_results=condition_results,
            facts=facts,
            rules=selected_rules,
        )

    # ========================================================
    # NOT_ESTABLISHED
    # ========================================================
    return DecisionResult(
        decision=NOT_ESTABLISHED,
        conclusion=(
            "根据现有用户明确事实，核心法律规则至少有一个必要条件未满足，"
            "因此目前不能确认相关法律义务已经成立。"
        ),
        condition_results=condition_results,
        facts=facts,
        rules=selected_rules,
    )


# ============================================================
# Decision Summary
# ============================================================

def build_decision_summary(
    result: DecisionResult,
) -> str:
    """
    将结构化 DecisionResult 转换为后续 LLM 可使用的 Context。

    注意：

        这里只输出 Engine 已经确定的结构化判断。
        不负责重新进行法律推理。
    """

    lines: List[str] = []

    lines.append("====================")
    lines.append("V6.0-10 法律决策结果")
    lines.append("====================")
    lines.append(f"决策状态：{result.decision}")
    lines.append(f"初步结论：{result.conclusion}")
    lines.append("")

    lines.append("核心法律规则：")
    if result.rules:
        for rule in result.rules:
            law_name = rule.get("law_name", "")
            article_number = rule.get("article_number", "")
            summary = rule.get("rule_summary", "")
            lines.append(
                f"- {law_name} {article_number}".strip()
            )
            if summary:
                lines.append(
                    f"  规则：{summary}"
                )
    else:
        lines.append("- 无")

    lines.append("")
    lines.append("用户明确事实：")
    if result.facts:
        for fact in result.facts:
            lines.append(
                f"- {fact.fact}"
            )
    else:
        lines.append("- 未识别到明确事实")

    lines.append("")
    lines.append("满足条件：")
    if result.satisfied_conditions:
        for item in result.satisfied_conditions:
            lines.append(
                f"- {item.condition}"
            )
            if item.reason:
                lines.append(
                    f"  原因：{item.reason}"
                )
    else:
        lines.append("- 无")

    lines.append("")
    lines.append("不满足条件：")
    if result.not_satisfied_conditions:
        for item in result.not_satisfied_conditions:
            lines.append(
                f"- {item.condition}"
            )
            if item.reason:
                lines.append(
                    f"  原因：{item.reason}"
                )
    else:
        lines.append("- 无")

    lines.append("")
    lines.append("未知条件：")
    if result.unknown_conditions:
        for item in result.unknown_conditions:
            lines.append(
                f"- {item.condition}"
            )
            if item.reason:
                lines.append(
                    f"  原因：{item.reason}"
                )
    else:
        lines.append("- 无")

    return "\n".join(lines)


# ============================================================
# Demo Rule - 劳动合同法第十四条
# ============================================================

def demo_rule() -> Dict:
    """
    V6.0-10 测试使用的《劳动合同法》第十四条结构化规则。
    """

    return {
        "law_name": "中华人民共和国劳动合同法",
        "article_number": "第十四条",
        "classification": "核心法条",
        "rule_type": RULE_DUTY,
        "rule_summary": (
            "符合《劳动合同法》第十四条规定条件时，应当订立无固定期限劳动合同"
        ),
        "conditions": [
            "连续订立二次固定期限劳动合同",
            "续订劳动合同",
            "劳动者提出或者同意续订、订立劳动合同",
        ],
        "exclusion_conditions": [
            "劳动者存在《劳动合同法》第三十九条规定的情形",
            "劳动者存在《劳动合同法》第四十条第一项规定的情形",
            "劳动者存在《劳动合同法》第四十条第二项规定的情形",
        ],
        "exceptions": [
            "劳动者提出订立固定期限劳动合同",
        ],
        "legal_obligations": [
            "用人单位应当订立无固定期限劳动合同",
        ],
        "legal_consequences": [
            "符合第十四条规定条件时，用人单位应当订立无固定期限劳动合同",
        ],
        "references": [
            "第十四条",
            "第三十九条",
            "第四十条",
            "第四十条第一项",
            "第四十条第二项",
        ],
    }


# ============================================================
# Test Rules
# ============================================================

def _supporting_rule(article_number: str, summary: str) -> Dict:
    """构造无条件辅助规则，用于验证 V6.0-10 不会被其抢走结论。"""
    return {
        "law_name": "中华人民共和国劳动合同法",
        "article_number": article_number,
        "classification": "相关法条",
        "rule_type": RULE_DEFINITION,
        "rule_summary": summary,
        "conditions": [],
        "exclusion_conditions": [],
        "exceptions": [],
        "legal_obligations": [],
        "legal_consequences": [],
        "references": [article_number],
    }


# ============================================================
# Test
# ============================================================

def run_test() -> None:
    print()
    print("=" * 70)
    print("RAG V6.0-10-FIXED - Legal Decision Engine")
    print("=" * 70)

    question = (
        "公司连续签订三次固定期限劳动合同后，"
        "是否必须签订无固定期限劳动合同？"
    )

    print()
    print("问题：")
    print(question)

    # ========================================================
    # 构造 8 条类似 Retriever 返回结果
    # ========================================================
    rules = [
        demo_rule(),
        _supporting_rule(
            "第三十九条",
            "劳动者存在法定过失情形时，用人单位可以依法解除劳动合同。",
        ),
        _supporting_rule(
            "第四十条",
            "符合法定情形时，用人单位可以依法解除劳动合同。",
        ),
        _supporting_rule(
            "第十三条",
            "固定期限劳动合同属于劳动合同期限类型之一。",
        ),
        _supporting_rule(
            "第八十二条",
            "违反法律规定不订立劳动合同的，依法承担相应法律责任。",
        ),
        _supporting_rule(
            "《劳动合同法实施条例》第十一条",
            "依法处理劳动合同期限相关问题。",
        ),
        _supporting_rule(
            "《劳动合同法实施条例》第十四条",
            "依法处理劳动合同相关情形。",
        ),
        _supporting_rule(
            "《劳动法》第二十条",
            "劳动合同期限可以依法约定。",
        ),
    ]

    # ========================================================
    # Facts
    # ========================================================
    print()
    print("=" * 70)
    print("事实识别")
    print("=" * 70)

    facts = extract_explicit_facts(question)

    for fact in facts:
        print(
            f"  - {fact.fact}"
        )

    # ========================================================
    # Core Rule Selection
    # ========================================================
    print()
    print("=" * 70)
    print("核心法律规则选择")
    print("=" * 70)

    core_rules = select_core_rules(
        question,
        rules,
    )

    for rule in core_rules:
        print(
            f"  - {rule.get('law_name', '')} "
            f"{rule.get('article_number', '')}"
        )

    # ========================================================
    # Decision
    # ========================================================
    result = make_decision(
        question=question,
        rules=rules,
    )

    print()
    print("=" * 70)
    print("法律决策")
    print("=" * 70)
    print()
    print(
        f"Decision：{result.decision}"
    )
    print()
    print(
        f"Conclusion：{result.conclusion}"
    )

    print()
    print("条件判断：")

    for item in result.condition_results:
        print(
            f"  [{item.status}] {item.condition}"
        )
        if item.reason:
            print(
                f"      {item.reason}"
            )

    print()
    print(build_decision_summary(result))

    print()
    print("=" * 70)
    print("V6.0-10-FIXED 测试结果")
    print("=" * 70)

    # 对当前测试问题，只有三次合同事实已明确。
    # 续订、劳动者提出/同意以及法定排除/例外尚未确认。
    if (
        result.decision == CONDITIONAL
        and len(result.facts) == 1
        and result.facts[0].fact == "连续签订三次固定期限劳动合同"
        and any(
            item.condition == "连续订立二次固定期限劳动合同"
            and item.status == SATISFIED
            for item in result.condition_results
        )
        and len(result.unknown_conditions) >= 1
        and result.rules
        and "第十四条" in str(result.rules[0].get("article_number", ""))
    ):
        print("✅ 测试通过")
        print("核心规则：劳动合同法第十四条")
        print("合同次数门槛：SATISFIED")
        print("其余未确认条件：UNKNOWN")
        print("最终决策：CONDITIONAL")
    else:
        print("❌ 测试失败")
        print("预期：第十四条核心规则 + CONDITIONAL")
        print("实际：", result.decision)


# ============================================================
# Main
# ============================================================

if __name__ == "__main__":
    run_test()
