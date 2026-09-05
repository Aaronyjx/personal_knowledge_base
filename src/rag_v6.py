# -*- coding: utf-8 -*-

"""
RAG V6.0
法律智能问答完整流水线

功能：

1. 用户问题输入
2. Retriever 法律知识召回
3. Legal Rule Extractor 法律规则提取
4. Rule Normalizer 法律规则规范化
5. Legal Decision Engine 法律条件判断
6. Legal Answer Builder 最终答案结构生成
7. Ollama 负责自然语言表达
8. 最终输出结构化法律答案


V6.0 核心原则：

    Retriever
        ↓
    法律依据
        ↓
    Rule Extractor
        ↓
    Rule Normalizer
        ↓
    Decision Engine
        ↓
    法律决策
        ↓
    Answer Builder
        ↓
    Ollama
        ↓
    最终答案


特别注意：

V6.0 不允许 Ollama 自行决定法律结论。

法律结论首先由：

    legal_decision_engine.py

完成。

Ollama 的职责主要是：

    1. 根据已经确定的法律决策组织语言
    2. 将结构化结果转换成自然语言
    3. 保持回答格式统一
    4. 不得修改 Decision Engine 的结论


这样可以避免：

    RAG → LLM → LLM 自行推理法律规则

升级为：

    RAG
      ↓
    法律规则
      ↓
    Python 决策引擎
      ↓
    确定法律结论
      ↓
    LLM 负责表达


V6.0 数据结构接口：

    Retriever
        ↓
    List[Dict]
        ↓
    Legal Rule Extractor
        ↓
    List[Dict]
        ↓
    Rule Normalizer
        ↓
    List[NormalizedLegalRule]
        ↓
    rule_to_dict()
        ↓
    List[Dict]
        ↓
    Legal Decision Engine


注意：

Rule Normalizer 内部使用：

    NormalizedLegalRule

Legal Decision Engine 当前使用：

    rule["conditions"]

因此必须在模块边界：

    NormalizedLegalRule → Dict

进行显式转换。
"""

import re
import requests

from typing import Any, Dict, List, Optional


# ============================================================
# V6.0 模块
# ============================================================

from .retriever import build_context
from .retriever import retrieve_articles


# ------------------------------------------------------------
# Legal Rule Extractor
#
# 当前 legal_rule_extractor.py 实际提供：
#
#     extract_rule()
#     extract_rules()
#
# 并不存在：
#
#     extract_legal_rules()
#
# 因此这里使用实际存在的 extract_rules()。
# ------------------------------------------------------------

from .legal_rule_extractor import (
    extract_rules,
)


# ------------------------------------------------------------
# Rule Normalizer
#
# normalize_rules() 返回：
#
#     List[NormalizedLegalRule]
#
# rule_to_dict() 用于转换成：
#
#     Dict
#
# 供 Decision Engine 使用。
# ------------------------------------------------------------

from .rule_normalizer import (
    normalize_rules,
    rule_to_dict,
)


# ------------------------------------------------------------
# Legal Decision Engine
# ------------------------------------------------------------

from .legal_decision_engine import (
    make_decision,
)


# ------------------------------------------------------------
# Legal Answer Builder
# ------------------------------------------------------------

from .legal_answer_builder import (
    build_answer_structure,
    build_legal_basis,
    build_conclusion,
    build_analysis,
    build_notices,
)


# ============================================================
# Ollama 配置
# ============================================================

OLLAMA_URL = (
    "http://127.0.0.1:11434/api/generate"
)

OLLAMA_MODEL = "qwen3:14b"


# ============================================================
# 默认参数
# ============================================================

DEFAULT_TOP_K = 5

DEFAULT_SCORE_THRESHOLD = 0.55


# ============================================================
# 输出结构
# ============================================================

REQUIRED_SECTIONS = [
    "【结论】",
    "【法律依据】",
    "【法律分析】",
    "【需要注意】",
]


# ============================================================
# 工具函数
# ============================================================

def _safe_get(
    obj: Any,
    key: str,
    default=None,
):
    """
    安全读取对象字段。

    兼容：

        dict
        dataclass
        普通对象
    """

    if obj is None:

        return default

    if isinstance(
        obj,
        dict,
    ):

        return obj.get(
            key,
            default,
        )

    return getattr(
        obj,
        key,
        default,
    )


# ============================================================
# Context 调试
# ============================================================

def print_context_summary(
    context: Any,
) -> None:
    """
    输出 Retriever Context 摘要。

    不直接打印全部 Context，
    避免终端输出过长。
    """

    print()

    print(
        "Retriever 返回法律依据："
        f"{len(context.split('【法律依据')) - 1 if isinstance(context, str) else 0} 条"
    )

    if not context:

        print(
            "⚠️ Context 为空"
        )

        return

    if not isinstance(
        context,
        str,
    ):

        print(
            f"Context 类型：{type(context)}"
        )

        return

    print(
        f"Context 字符数："
        f"{len(context)}"
    )


# ============================================================
# Structured Articles 调试
# ============================================================

def print_article_summary(
    articles: List[Dict[str, Any]],
) -> None:
    """
    输出结构化法律依据摘要。
    """

    print()

    print("=" * 70)
    print("V6.0 Structured Articles")
    print("=" * 70)

    print(
        f"法律依据数量："
        f"{len(articles)}"
    )

    for index, article in enumerate(
        articles,
        start=1,
    ):

        law_name = article.get(
            "law_name",
            "",
        )

        article_number = article.get(
            "article_number",
            "",
        )

        score = article.get(
            "score",
            0,
        )

        rule_score = article.get(
            "rule_score",
            0,
        )

        print(
            f"  {index}. "
            f"{law_name} "
            f"{article_number} "
            f"score={score} "
            f"rule_score={rule_score}"
        )


# ============================================================
# Legal Rule 调试
# ============================================================

def print_rule_summary(
    rules: List[Any],
) -> None:
    """
    输出法律规则摘要。

    兼容：

        NormalizedLegalRule
        Dict
    """

    print()

    print(
        f"结构化法律规则："
        f"{len(rules)} 条"
    )

    for index, rule in enumerate(
        rules,
        start=1,
    ):

        law_name = _safe_get(
            rule,
            "law_name",
            "",
        )

        article_number = _safe_get(
            rule,
            "article_number",
            "",
        )

        rule_type = _safe_get(
            rule,
            "rule_type",
            "",
        )

        summary = _safe_get(
            rule,
            "summary",
            "",
        )

        print(
            f"  {index}. "
            f"{law_name} "
            f"{article_number}"
        )

        print(
            f"     规则类型："
            f"{rule_type}"
        )

        if summary:

            print(
                f"     规则摘要："
                f"{summary}"
            )


# ============================================================
# Decision 调试
# ============================================================

def print_decision(
    decision: Any,
) -> None:
    """
    输出法律决策结果。

    兼容：

        DecisionResult
        Dict
    """

    print()

    print(
        "法律决策结果："
    )

    status = _safe_get(
        decision,
        "decision",
        "",
    )

    conclusion = _safe_get(
        decision,
        "conclusion",
        "",
    )

    print(
        f"  Decision："
        f"{status}"
    )

    print(
        f"  Conclusion："
        f"{conclusion}"
    )

    facts = _safe_get(
        decision,
        "facts",
        [],
    )

    if facts:

        print(
            f"  Facts："
            f"{len(facts)}"
        )


# ============================================================
# Answer Structure 调试
# ============================================================

def print_answer_structure(
    answer_structure: Any,
) -> None:
    """
    输出 Answer Builder 结果摘要。
    """

    print()

    print(
        "Answer Structure："
    )

    if not isinstance(
        answer_structure,
        dict,
    ):

        print(
            f"  类型："
            f"{type(answer_structure)}"
        )

        return

    for key in [
        "decision",
        "conclusion",
        "legal_basis",
        "analysis",
        "notices",
    ]:

        value = answer_structure.get(
            key
        )

        if isinstance(
            value,
            list,
        ):

            print(
                f"  {key}："
                f"{len(value)} 项"
            )

        else:

            print(
                f"  {key}："
                f"{value}"
            )


# ============================================================
# Ollama 调用
# ============================================================

def call_ollama(
    prompt: str,
    model: str = OLLAMA_MODEL,
    timeout: int = 180,
) -> str:
    """
    调用 Ollama。

    Ollama 只负责：

        自然语言表达

    不负责：

        法律结论判断
    """

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
    }

    try:

        response = requests.post(
            OLLAMA_URL,
            json=payload,
            timeout=timeout,
        )

        response.raise_for_status()

        data = response.json()

        return str(
            data.get(
                "response",
                "",
            )
            or ""
        ).strip()

    except Exception as exc:

        print()

        print(
            "⚠️ Ollama 调用失败："
        )

        print(exc)

        return ""


# ============================================================
# 检查答案结构
# ============================================================

def validate_answer(
    answer: str,
) -> bool:
    """
    检查最终答案是否包含必要结构。

    必须包含：

        【结论】
        【法律依据】
        【法律分析】
        【需要注意】
    """

    if not answer:

        return False

    for section in REQUIRED_SECTIONS:

        if section not in answer:

            return False

    return True


# ============================================================
# 结构化答案 → Ollama Prompt
# ============================================================

def build_ollama_prompt(
    question: str,
    answer_structure: Dict[str, Any],
) -> str:
    """
    构造 Ollama 自然语言生成 Prompt。

    核心原则：

        Ollama 不得修改法律结论。

    Python Decision Engine
        ↓
    已确定的法律结论
        ↓
    Ollama
        ↓
    只负责表达
    """

    decision = answer_structure.get(
        "decision",
        "",
    )

    conclusion = answer_structure.get(
        "conclusion",
        "",
    )

    legal_basis = answer_structure.get(
        "legal_basis",
        [],
    )

    analysis = answer_structure.get(
        "analysis",
        [],
    )

    notices = answer_structure.get(
        "notices",
        [],
    )

    if not isinstance(
        legal_basis,
        list,
    ):

        legal_basis = [
            str(legal_basis)
        ]

    if not isinstance(
        analysis,
        list,
    ):

        analysis = [
            str(analysis)
        ]

    if not isinstance(
        notices,
        list,
    ):

        notices = [
            str(notices)
        ]

    legal_basis_text = "\n".join(
        f"{index}. {item}"
        for index, item
        in enumerate(
            legal_basis,
            start=1,
        )
    )

    analysis_text = "\n".join(
        f"{index}. {item}"
        for index, item
        in enumerate(
            analysis,
            start=1,
        )
    )

    notices_text = "\n".join(
        f"{index}. {item}"
        for index, item
        in enumerate(
            notices,
            start=1,
        )
    )

    prompt = f"""
你是一名法律问答系统的自然语言表达模块。

你的任务不是重新判断法律结论。

Python 法律决策引擎已经完成法律条件判断。

你只能根据下面已经确定的结构化结果组织自然语言。

============================================================
用户问题
============================================================

{question}

============================================================
Python 已确定的 Decision
============================================================

{decision}

============================================================
Python 已确定的 Conclusion
============================================================

{conclusion}

============================================================
法律依据
============================================================

{legal_basis_text}

============================================================
法律分析
============================================================

{analysis_text}

============================================================
需要注意
============================================================

{notices_text}

============================================================
输出要求
============================================================

必须严格按照以下结构输出：

【结论】

【法律依据】

【法律分析】

【需要注意】

重要要求：

1. 不得修改 Python Decision Engine 的法律结论。
2. 不得自行增加法律规则。
3. 不得自行创造不存在的法律条文。
4. 不得把 UNKNOWN 条件说成已经确定。
5. 不得把 CONDITIONAL 说成 DEFINITE。
6. 不得把 NOT_ESTABLISHED 说成已经成立。
7. 法律依据只能来自提供的数据。
8. 可以改善语言表达，但不能改变事实判断。
9. 如果条件不足，应明确说明还缺少什么事实。
10. 使用简洁、专业、清晰的中文。
"""

    return prompt.strip()


# ============================================================
# 无 Ollama 时的 Plain Answer
# ============================================================

def build_plain_answer(
    answer_structure: Dict[str, Any],
) -> str:
    """
    当 Ollama 不可用时，
    使用结构化结果直接生成答案。

    这样整个 RAG 系统仍然可以运行。
    """

    conclusion = answer_structure.get(
        "conclusion",
        "",
    )

    legal_basis = answer_structure.get(
        "legal_basis",
        [],
    )

    analysis = answer_structure.get(
        "analysis",
        [],
    )

    notices = answer_structure.get(
        "notices",
        [],
    )

    if not isinstance(
        legal_basis,
        list,
    ):

        legal_basis = [
            str(legal_basis)
        ]

    if not isinstance(
        analysis,
        list,
    ):

        analysis = [
            str(analysis)
        ]

    if not isinstance(
        notices,
        list,
    ):

        notices = [
            str(notices)
        ]

    result = []

    result.append(
        "【结论】"
    )

    result.append(
        str(conclusion)
    )

    result.append("")

    result.append(
        "【法律依据】"
    )

    if legal_basis:

        for item in legal_basis:

            result.append(
                f"- {item}"
            )

    else:

        result.append(
            "当前没有可直接引用的结构化法律依据。"
        )

    result.append("")

    result.append(
        "【法律分析】"
    )

    if analysis:

        for item in analysis:

            result.append(
                f"- {item}"
            )

    else:

        result.append(
            "当前没有可用的结构化法律分析。"
        )

    result.append("")

    result.append(
        "【需要注意】"
    )

    if notices:

        for item in notices:

            result.append(
                f"- {item}"
            )

    else:

        result.append(
            "最终法律结论应以已经确认的事实、"
            "有效法律法规及具体合同情况为基础。"
        )

    return "\n".join(
        result
    )


# ============================================================
# 清理 Ollama 输出
# ============================================================

def clean_ollama_answer(
    answer: str,
) -> str:
    """
    清理 Ollama 输出。

    不改变法律内容，
    只处理：

        前后空白
        多余 Markdown
        重复空行
    """

    if not answer:

        return ""

    answer = answer.strip()

    answer = answer.replace(
        "```text",
        "",
    )

    answer = answer.replace(
        "```",
        "",
    )

    answer = re.sub(
        r"\n{3,}",
        "\n\n",
        answer,
    )

    return answer.strip()


# ============================================================
# 强制补全答案结构
# ============================================================

def ensure_answer_structure(
    answer: str,
    answer_structure: Dict[str, Any],
) -> str:
    """
    如果 Ollama 没有生成完整结构，
    则退回 Python 结构化答案。

    这样可以保证：

        【结论】
        【法律依据】
        【法律分析】
        【需要注意】

    始终存在。
    """

    answer = clean_ollama_answer(
        answer
    )

    if validate_answer(
        answer
    ):

        return answer

    print(
        "⚠️ Ollama 输出结构不完整，"
        "使用 Python 结构化答案。"
    )

    return build_plain_answer(
        answer_structure
    )


# ============================================================
# 主函数
# ============================================================

def answer_question(
    question: str,
    top_k: int = DEFAULT_TOP_K,
    score_threshold: float = DEFAULT_SCORE_THRESHOLD,
    use_ollama: bool = True,
    ollama_model: str = OLLAMA_MODEL,
) -> str:
    """
    完整法律智能问答。

    Pipeline：

        用户问题
            ↓
        Retriever
            ↓
        Context
            ↓
        Legal Rule Extractor
            ↓
        Rule Normalizer
            ↓
        Legal Decision Engine
            ↓
        Legal Answer Builder
            ↓
        Ollama
            ↓
        最终答案


    参数：

        question:
            用户问题

        top_k:
            Retriever 初始语义召回数量

        score_threshold:
            最低语义相关度

        use_ollama:
            是否使用 Ollama 生成自然语言

        ollama_model:
            Ollama 模型名称
    """

    print()

    print("=" * 70)
    print(
        "RAG V6.0 - 完整法律智能问答"
    )
    print("=" * 70)

    print()

    print(
        f"用户问题：{question}"
    )

    # ========================================================
    # STEP 1
    # Retriever
    # ========================================================

    print()

    print("=" * 70)
    print(
        "STEP 1 - Retriever"
    )
    print("=" * 70)

    context = build_context(
        question=question,
        top_k=top_k,
        score_threshold=score_threshold,
    )

    print_context_summary(
        context
    )

    if not context:

        print(
            "⚠️ 未检索到法律依据"
        )

        return (
            "【结论】\n"
            "根据当前知识库，暂未检索到足够的直接法律依据，"
            "因此无法作出可靠法律结论。\n\n"
            "【法律依据】\n"
            "当前知识库未提供足够的直接法律依据。\n\n"
            "【法律分析】\n"
            "由于缺少必要法律依据，暂时无法进行完整条件判断。\n\n"
            "【需要注意】\n"
            "建议补充相关法律法规、司法解释或者具体合同事实。"
        )

    # ========================================================
    # STEP 1.5
    # Structured Articles
    #
    # Retriever 同时提供：
    #
    #     build_context()
    #
    # 和：
    #
    #     retrieve_articles()
    #
    # V6 使用结构化 Articles 作为
    # Legal Rule Extractor 的输入。
    # ========================================================

    print()

    print("=" * 70)
    print(
        "STEP 1.5 - Structured Articles"
    )
    print("=" * 70)

    articles = retrieve_articles(
        question,
        top_k=top_k,
        score_threshold=score_threshold,
    )

    if articles is None:

        articles = []

    print_article_summary(
        articles
    )

    if not articles:

        print(
            "⚠️ 没有结构化法律依据"
        )

        return (
            "【结论】\n"
            "当前知识库没有返回足够的结构化法律依据，"
            "无法作出可靠法律结论。\n\n"
            "【法律依据】\n"
            "当前没有足够的结构化法律依据。\n\n"
            "【法律分析】\n"
            "由于缺少结构化法律规则，"
            "暂时无法进行完整条件判断。\n\n"
            "【需要注意】\n"
            "建议检查知识库内容及法律法规入库情况。"
        )

    # ========================================================
    # STEP 2
    # Legal Rule Extractor
    # ========================================================

    print()

    print("=" * 70)
    print(
        "STEP 2 - Legal Rule Extractor"
    )
    print("=" * 70)

    # --------------------------------------------------------
    # 当前 legal_rule_extractor.py 的实际接口：
    #
    #     extract_rules(
    #         laws,
    #         max_rules=...
    #     )
    #
    # 因此直接将结构化 Articles 传入。
    # --------------------------------------------------------

    raw_rules = extract_rules(
        laws=articles,
    )

    if raw_rules is None:

        raw_rules = []

    print(
        f"原始法律规则数量："
        f"{len(raw_rules)}"
    )

    if not raw_rules:

        print(
            "⚠️ 没有提取到结构化法律规则"
        )

        return (
            "【结论】\n"
            "当前知识库虽然检索到了法律条文，"
            "但暂未成功提取出结构化法律规则。\n\n"
            "【法律依据】\n"
            "检索到了法律条文，但规则提取失败。\n\n"
            "【法律分析】\n"
            "由于缺少结构化规则，"
            "无法进入法律条件判断阶段。\n\n"
            "【需要注意】\n"
            "建议检查 legal_rule_extractor.py。"
        )

    # ========================================================
    # STEP 3
    # Rule Normalizer
    # ========================================================

    print()

    print("=" * 70)
    print(
        "STEP 3 - Rule Normalizer"
    )
    print("=" * 70)

    normalized_rule_objects = normalize_rules(
        raw_rules
    )

    if normalized_rule_objects is None:

        normalized_rule_objects = []

    print(
        f"规范化法律规则数量："
        f"{len(normalized_rule_objects)}"
    )

    print_rule_summary(
        normalized_rule_objects
    )

    # --------------------------------------------------------
    # NormalizedLegalRule → Dictionary
    #
    # Rule Normalizer 内部使用：
    #
    #     NormalizedLegalRule
    #
    # Legal Decision Engine 使用：
    #
    #     Dict
    #
    # 因此在模块边界进行一次显式转换。
    #
    # 这一步是 V6.0 当前修复的关键。
    # --------------------------------------------------------

    normalized_rules = []

    for rule in normalized_rule_objects:

        try:

            if isinstance(
                rule,
                dict,
            ):

                normalized_rules.append(
                    rule
                )

            else:

                normalized_rules.append(
                    rule_to_dict(
                        rule
                    )
                )

        except Exception as exc:

            print(
                "⚠️ 法律规则转换失败："
            )

            print(
                exc
            )

    print()

    print(
        "法律规则数据结构转换完成："
        "NormalizedLegalRule → Dict"
    )

    print(
        f"Decision Engine 输入规则数量："
        f"{len(normalized_rules)}"
    )

    # --------------------------------------------------------
    # 再次检查 conditions
    #
    # 防止：
    #
    #     KeyError: 'conditions'
    #
    # --------------------------------------------------------

    for index, rule in enumerate(
        normalized_rules,
        start=1,
    ):

        if "conditions" not in rule:

            print(
                f"⚠️ 第 {index} 条法律规则缺少 conditions"
            )

            rule["conditions"] = []

        if "exclusions" not in rule:

            rule["exclusions"] = []

        if "exceptions" not in rule:

            rule["exceptions"] = []

        if "obligations" not in rule:

            rule["obligations"] = []

        if "consequences" not in rule:

            rule["consequences"] = []

    # ========================================================
    # STEP 4
    # Legal Decision Engine
    # ========================================================

    print()

    print("=" * 70)
    print(
        "STEP 4 - Legal Decision Engine"
    )
    print("=" * 70)

    if not normalized_rules:

        print(
            "⚠️ 没有可用于法律决策的规则"
        )

        return (
            "【结论】\n"
            "当前没有可用于判断的结构化法律规则。\n\n"
            "【法律依据】\n"
            "当前没有可用于决策的结构化法律依据。\n\n"
            "【法律分析】\n"
            "无法进入法律条件判断阶段。\n\n"
            "【需要注意】\n"
            "建议检查 Rule Normalizer 的输出。"
        )

    decision = make_decision(
        question=question,
        rules=normalized_rules,
    )

    print_decision(
        decision
    )

    # ========================================================
    # STEP 5
    # Legal Answer Builder
    # ========================================================

    print()

    print("=" * 70)
    print(
        "STEP 5 - Legal Answer Builder"
    )
    print("=" * 70)

    # --------------------------------------------------------
    # 当前 legal_answer_builder.py 提供：
    #
    #     build_answer_structure(
    #         decision,
    #         rules
    #     )
    #
    # 因此使用这个函数生成最终结构化答案。
    # --------------------------------------------------------

    answer_structure = build_answer_structure(
        decision=decision,
        rules=normalized_rules,
    )

    if answer_structure is None:

        answer_structure = {}

    print(
        "Answer Builder 生成完成"
    )

    print_answer_structure(
        answer_structure
    )

    # ========================================================
    # STEP 6
    # Ollama Natural Language Generation
    # ========================================================

    print()

    print("=" * 70)
    print(
        "STEP 6 - Ollama Natural Language Generation"
    )
    print("=" * 70)

    # --------------------------------------------------------
    # 如果关闭 Ollama：
    #
    #     直接使用 Python 结构化答案。
    #
    # 这样可以单独测试：
    #
    #     Retriever
    #     Rule Extractor
    #     Normalizer
    #     Decision Engine
    #     Answer Builder
    #
    # 而不受 Ollama 影响。
    # --------------------------------------------------------

    if not use_ollama:

        print(
            "Ollama 已关闭，"
            "直接返回 Python 结构化答案。"
        )

        return build_plain_answer(
            answer_structure
        )

    prompt = build_ollama_prompt(
        question=question,
        answer_structure=answer_structure,
    )

    print()

    print(
        f"Ollama Model："
        f"{ollama_model}"
    )

    print(
        "开始生成自然语言答案..."
    )

    ollama_answer = call_ollama(
        prompt=prompt,
        model=ollama_model,
    )

    # ========================================================
    # STEP 7
    # Final Answer Validation
    # ========================================================

    print()

    print("=" * 70)
    print(
        "STEP 7 - Final Answer Validation"
    )
    print("=" * 70)

    final_answer = ensure_answer_structure(
        ollama_answer,
        answer_structure,
    )

    if validate_answer(
        final_answer
    ):

        print(
            "✅ 最终答案结构验证成功"
        )

    else:

        print(
            "⚠️ 最终答案结构验证失败"
        )

    # ========================================================
    # STEP 8
    # 输出最终答案
    # ========================================================

    print()

    print("=" * 70)
    print(
        "RAG V6.0 最终答案"
    )
    print("=" * 70)

    print()

    print(
        final_answer
    )

    print()

    print("=" * 70)
    print(
        "RAG V6.0 完成"
    )
    print("=" * 70)

    return final_answer


# ============================================================
# 兼容旧代码
# ============================================================

def answer(
    question: str,
    **kwargs,
) -> str:
    """
    answer_question() 的兼容别名。

    方便旧代码继续使用：

        answer(...)
    """

    return answer_question(
        question,
        **kwargs,
    )


# ============================================================
# Demo
# ============================================================

def demo() -> None:
    """
    V6.0 Demo。

    测试问题：

        公司连续签订三次固定期限劳动合同后，
        是否必须签订无固定期限劳动合同？
    """

    question = (
        "公司连续签订三次固定期限劳动合同后，"
        "是否必须签订无固定期限劳动合同？"
    )

    answer_question(
        question=question,
        top_k=5,
        score_threshold=0.55,
        use_ollama=True,
        ollama_model=OLLAMA_MODEL,
    )


# ============================================================
# Main
# ============================================================

if __name__ == "__main__":

    demo()