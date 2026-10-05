"""
RAG V6.9 Retrieval → LegalFacts Boundary Regression Test

============================================================
测试目标
============================================================

本测试锁定：

    Retrieval / Ranking / Retrieved Articles
                    ↓
                    X
                    ↓
                LegalFacts

核心原则：

    LegalFacts 只能来自用户明确表达的问题事实。

Retriever 返回的：

    - Article
    - Structured Rule
    - rule_summary
    - importance
    - ranking score
    - legal context
    - retrieved article metadata

均不得自动成为 LegalFacts。

============================================================
数据流
============================================================

正确的数据流：

    用户问题
        ↓
    extract_legal_facts(question)
        ↓
    LegalFacts
        ↓
    ConditionResult
        ↓
    Decision

同时：

    用户问题
        ↓
    Retriever
        ↓
    retrieved_articles
        ↓
    select_core_rule()

两条路径在 Decision Engine 汇合。

============================================================
本测试不测试
============================================================

1. Retriever 排名算法是否正确。
2. BGE Reranker 是否正确。
3. Article 14 法律规则是否正确。
4. Ollama。
5. Answer Builder。
6. Decision Engine 的全部 Condition Matrix。

上述内容已经由其他回归测试负责。

============================================================
运行方式
============================================================

    PYTHONPATH="$PWD" python tests/test_retrieval_fact_boundary.py
"""

from __future__ import annotations

from typing import Any, Dict, List

from src.legal_decision_engine import make_decision
from src.legal_fact_extractor import extract_legal_facts


# ============================================================
# Test Constants
# ============================================================

BASELINE_QUESTION = (
    "公司连续签订三次固定期限劳动合同。"
)


# ============================================================
# Assertion Helpers
# ============================================================


def _assert_equal(
    actual: Any,
    expected: Any,
    message: str,
) -> None:
    """
    通用相等断言。
    """

    if actual != expected:
        raise AssertionError(
            f"{message}\n"
            f"期望：{expected!r}\n"
            f"实际：{actual!r}"
        )


def _assert_none(
    facts: Any,
    field_name: str,
) -> None:
    """
    断言 LegalFacts 某字段必须保持 None。
    """

    actual = getattr(
        facts,
        field_name,
        None,
    )

    if actual is not None:
        raise AssertionError(
            f"LegalFacts 污染：字段 {field_name!r} "
            f"不应由当前问题自动产生事实。\n"
            f"实际值：{actual!r}"
        )


def _condition_results_by_id(
    decision: Any,
) -> Dict[str, Any]:
    """
    将 DecisionResult.condition_results 转换为：

        condition_id → ConditionResult

    本测试只用于验证最终 Decision 没有因为
    retrieved_articles 而改变事实驱动的条件状态。
    """

    results = getattr(
        decision,
        "condition_results",
        None,
    )

    if not isinstance(results, list):
        raise AssertionError(
            "DecisionResult.condition_results "
            "不是 list。"
        )

    mapping: Dict[str, Any] = {}

    for result in results:

        condition_id = getattr(
            result,
            "condition_id",
            None,
        )

        if not condition_id:
            raise AssertionError(
                "ConditionResult 缺少 condition_id。"
            )

        condition_id = str(
            condition_id
        ).strip()

        if condition_id in mapping:
            raise AssertionError(
                f"ConditionResult 存在重复 condition_id："
                f"{condition_id}"
            )

        mapping[condition_id] = result

    return mapping


# ============================================================
# Retrieved Article Fixtures
# ============================================================


def _make_article_14() -> Dict[str, Any]:
    """
    模拟 Retriever 返回的 Article 14 材料。

    注意：

    这里故意放入大量可能诱导事实推断的信息，
    用于攻击 Retrieval → LegalFacts 边界。

    这些字段都不是用户事实。
    """

    return {
        "article_number": "第十四条",
        "law_name": "中华人民共和国劳动合同法",
        "text": (
            "无固定期限劳动合同，是指用人单位与劳动者约定"
            "无确定终止时间的劳动合同。"
        ),
        "rule_summary": (
            "连续订立二次固定期限劳动合同，且不存在法定排除"
            "情形并满足其他法定条件的，涉及无固定期限劳动合同。"
        ),
        "importance": "CRITICAL",
        "_semantic_score": 0.92,
        "_rule_score": 3.0,
        "_ranking_score": 1.07,
        "structured_rule": {
            "conditions": [
                "连续订立二次固定期限劳动合同",
                "存在后续订立的劳动合同",
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
        },
    }


def _make_article_39() -> Dict[str, Any]:
    """
    模拟 Retriever 返回 Article 39。

    该材料尤其用于验证：

        检索到第39条
            ≠
        article_39 = True
    """

    return {
        "article_number": "第三十九条",
        "law_name": "中华人民共和国劳动合同法",
        "text": (
            "劳动者有下列情形之一的，用人单位可以解除劳动合同。"
        ),
        "rule_summary": (
            "包括严重违反用人单位规章制度等法定情形。"
        ),
        "importance": "HIGH",
        "_semantic_score": 0.88,
        "_rule_score": 1.5,
        "_ranking_score": 0.955,
        "structured_rule": {
            "condition": (
                "劳动者存在《劳动合同法》第三十九条规定的情形"
            )
        },
    }


def _make_article_40() -> Dict[str, Any]:
    """
    模拟 Retriever 返回 Article 40。

    用于验证：

        检索到 Article 40
            ≠
        article_40_1 = True
        article_40_2 = True
    """

    return {
        "article_number": "第四十条",
        "law_name": "中华人民共和国劳动合同法",
        "text": (
            "有下列情形之一的，用人单位提前三十日以书面形式"
            "通知劳动者本人或者额外支付一个月工资后，可以解除劳动合同。"
        ),
        "rule_summary": (
            "涉及劳动者患病或者非因工负伤、不能胜任工作等情形。"
        ),
        "importance": "HIGH",
        "_semantic_score": 0.86,
        "_rule_score": 1.5,
        "_ranking_score": 0.935,
        "structured_rule": {
            "conditions": [
                "劳动者存在《劳动合同法》第四十条第一项规定的情形",
                "劳动者存在《劳动合同法》第四十条第二项规定的情形",
            ]
        },
    }


def _make_adversarial_retrieved_articles() -> List[Dict[str, Any]]:
    """
    构造攻击性 Retrieved Articles。

    这些材料同时包含：

        Article 14
        Article 39
        Article 40
        Structured Rule
        ranking metadata
        importance

    如果系统错误地把 Retriever 内容当作事实，
    就可能污染：

        completed_renewal
        worker_agreement
        article_39
        article_40_1
        article_40_2
        fixed_term_exception

    本测试要求这些字段仍然保持 None。
    """

    return [
        _make_article_14(),
        _make_article_39(),
        _make_article_40(),
    ]


# ============================================================
# CASE 01
# 三次固定期限合同不会因为检索 Article 14
# 自动产生续订、劳动者同意等事实
# ============================================================


def test_case_01_retrieval_cannot_create_legal_facts() -> None:
    print()
    print("=" * 70)
    print("CASE 01")
    print("Retriever 法律材料不能制造 LegalFacts")
    print("=" * 70)

    question = BASELINE_QUESTION

    facts = extract_legal_facts(
        question
    )

    sequence = facts.contract_sequence

    if sequence is None:
        raise AssertionError(
            "基准问题没有正确提取 contract_sequence。"
        )

    _assert_equal(
        sequence.count,
        3,
        "contract_sequence.count 应为 3。",
    )

    _assert_equal(
        sequence.term_type,
        "fixed",
        "contract_sequence.term_type 应为 fixed。",
    )

    _assert_equal(
        sequence.continuous,
        True,
        "contract_sequence.continuous 应为 True。",
    )

    # --------------------------------------------------------
    # 核心边界：
    # 三次合同不能推出其他事实。
    # --------------------------------------------------------

    _assert_none(
        facts,
        "completed_renewal",
    )

    _assert_none(
        facts,
        "worker_agreement",
    )

    _assert_none(
        facts,
        "article_39",
    )

    _assert_none(
        facts,
        "article_40_1",
    )

    _assert_none(
        facts,
        "article_40_2",
    )

    _assert_none(
        facts,
        "fixed_term_exception",
    )

    # --------------------------------------------------------
    # 将攻击性 Retrieved Articles 作为 Decision Engine
    # 的 retrieved_articles 输入。
    #
    # 注意：
    # 本测试不是为了验证 Retriever 本身，
    # 而是验证 retrieved_articles 不得改变事实层。
    # --------------------------------------------------------

    retrieved_articles = (
        _make_adversarial_retrieved_articles()
    )

    decision = make_decision(
        question,
        retrieved_articles=retrieved_articles,
    )

    # DecisionResult 必须继续保留同一个 ContractSequence。
    decision_sequence = getattr(
        decision,
        "contract_sequence",
        None,
    )

    if decision_sequence is None:
        raise AssertionError(
            "DecisionResult.contract_sequence 不应为空。"
        )

    _assert_equal(
        decision_sequence.count,
        3,
        "DecisionResult.contract_sequence.count 应为 3。",
    )

    _assert_equal(
        decision_sequence.term_type,
        "fixed",
        "DecisionResult.contract_sequence.term_type 应为 fixed。",
    )

    _assert_equal(
        decision_sequence.continuous,
        True,
        "DecisionResult.contract_sequence.continuous 应为 True。",
    )

    # --------------------------------------------------------
    # DecisionResult 中的事实字段也不能被检索材料污染。
    # --------------------------------------------------------

    explicit_facts = getattr(
        decision,
        "explicit_facts",
        None,
    )

    if not isinstance(
        explicit_facts,
        list,
    ):
        raise AssertionError(
            "DecisionResult.explicit_facts 应为 list。"
        )

    for forbidden_fact in [
        "已经完成续订",
        "劳动者同意续订",
        "存在第三十九条情形",
        "存在第四十条第一项情形",
        "存在第四十条第二项情形",
        "劳动者提出订立固定期限劳动合同",
    ]:
        for fact in explicit_facts:
            if forbidden_fact in str(fact):
                raise AssertionError(
                    "Retriever 内容疑似污染 explicit_facts：\n"
                    f"禁止事实：{forbidden_fact}\n"
                    f"实际事实：{fact}"
                )

    print("PASS")


# ============================================================
# CASE 02
# 无 Retrieved Articles 与有恶意 Retrieved Articles
# LegalFacts 必须完全一致
# ============================================================


def test_case_02_retrieved_articles_do_not_change_fact_state() -> None:
    print()
    print("=" * 70)
    print("CASE 02")
    print("有无 Retrieved Articles 不得改变 LegalFacts")
    print("=" * 70)

    question = BASELINE_QUESTION

    # --------------------------------------------------------
    # 基线：
    # 不提供 retrieved_articles。
    # --------------------------------------------------------

    baseline_decision = make_decision(
        question
    )

    # --------------------------------------------------------
    # 攻击：
    # 提供包含 Article 14 / 39 / 40 的材料。
    # --------------------------------------------------------

    adversarial_decision = make_decision(
        question,
        retrieved_articles=(
            _make_adversarial_retrieved_articles()
        ),
    )

    # --------------------------------------------------------
    # 比较 DecisionResult 中由 LegalFacts 派生的状态。
    # --------------------------------------------------------

    baseline_sequence = getattr(
        baseline_decision,
        "contract_sequence",
        None,
    )

    adversarial_sequence = getattr(
        adversarial_decision,
        "contract_sequence",
        None,
    )

    if baseline_sequence is None:
        raise AssertionError(
            "baseline DecisionResult.contract_sequence 为空。"
        )

    if adversarial_sequence is None:
        raise AssertionError(
            "adversarial DecisionResult.contract_sequence 为空。"
        )

    _assert_equal(
        adversarial_sequence.count,
        baseline_sequence.count,
        "Retrieved Articles 不得改变合同次数事实。",
    )

    _assert_equal(
        adversarial_sequence.term_type,
        baseline_sequence.term_type,
        "Retrieved Articles 不得改变合同类型事实。",
    )

    _assert_equal(
        adversarial_sequence.continuous,
        baseline_sequence.continuous,
        "Retrieved Articles 不得改变连续性事实。",
    )

    # --------------------------------------------------------
    # explicit_facts 必须完全一致。
    # --------------------------------------------------------

    baseline_explicit_facts = getattr(
        baseline_decision,
        "explicit_facts",
        None,
    )

    adversarial_explicit_facts = getattr(
        adversarial_decision,
        "explicit_facts",
        None,
    )

    if not isinstance(
        baseline_explicit_facts,
        list,
    ):
        raise AssertionError(
            "baseline explicit_facts 不是 list。"
        )

    if not isinstance(
        adversarial_explicit_facts,
        list,
    ):
        raise AssertionError(
            "adversarial explicit_facts 不是 list。"
        )

    _assert_equal(
        adversarial_explicit_facts,
        baseline_explicit_facts,
        "Retrieved Articles 不得改变 explicit_facts。",
    )

    # --------------------------------------------------------
    # ConditionResult 状态必须完全一致。
    #
    # 这一步不是重新测试 Decision Engine，
    # 而是锁定：
    #
    # Retriever → LegalFacts
    #
    # 不得改变事实驱动的 ConditionResult。
    # --------------------------------------------------------

    baseline_conditions = (
        _condition_results_by_id(
            baseline_decision
        )
    )

    adversarial_conditions = (
        _condition_results_by_id(
            adversarial_decision
        )
    )

    _assert_equal(
        set(adversarial_conditions.keys()),
        set(baseline_conditions.keys()),
        "Retrieved Articles 不得改变 ConditionResult 的 condition_id 集合。",
    )

    for condition_id in sorted(
        baseline_conditions.keys()
    ):

        baseline_status = getattr(
            baseline_conditions[condition_id],
            "status",
            None,
        )

        adversarial_status = getattr(
            adversarial_conditions[condition_id],
            "status",
            None,
        )

        _assert_equal(
            adversarial_status,
            baseline_status,
            (
                "Retrieved Articles 不得改变 "
                f"{condition_id} 的 ConditionResult.status。"
            ),
        )

    print("PASS")


# ============================================================
# CASE 03
# 检索材料中的法律条件文本不能被当成用户事实
# ============================================================


def test_case_03_structured_rule_text_is_not_user_fact() -> None:
    print()
    print("=" * 70)
    print("CASE 03")
    print("Structured Rule / Article 文本不能成为用户事实")
    print("=" * 70)

    question = BASELINE_QUESTION

    retrieved_articles = [
        {
            "article_number": "第十四条",
            "law_name": "中华人民共和国劳动合同法",
            "text": (
                "连续订立二次固定期限劳动合同，"
                "续订劳动合同，且劳动者提出或者同意续订、"
                "订立劳动合同的，应当订立无固定期限劳动合同。"
            ),
            "rule_summary": (
                "劳动者不存在第三十九条、第四十条第一项、"
                "第四十条第二项规定情形。"
            ),
            "importance": "CRITICAL",
            "_ranking_score": 1.25,
            "structured_rule": {
                "required_conditions": [
                    "连续订立二次固定期限劳动合同",
                    "存在后续订立的劳动合同",
                    "续订劳动合同",
                    "劳动者提出或者同意续订、订立劳动合同",
                ],
                "exclusion_conditions": [
                    "劳动者不存在第三十九条规定的情形",
                    "劳动者不存在第四十条第一项规定的情形",
                    "劳动者不存在第四十条第二项规定的情形",
                ],
                "exception": (
                    "劳动者提出订立固定期限劳动合同"
                ),
            },
        }
    ]

    # --------------------------------------------------------
    # 事实提取仍然只使用 question。
    # --------------------------------------------------------

    facts = extract_legal_facts(
        question
    )

    # --------------------------------------------------------
    # Structured Rule 中虽然明确出现了：
    #
    #     续订
    #     劳动者同意
    #     不存在第三十九条
    #     不存在第四十条
    #
    # 这些内容仍然不能成为用户事实。
    # --------------------------------------------------------

    forbidden_none_fields = [
        "completed_renewal",
        "worker_agreement",
        "article_39",
        "article_40_1",
        "article_40_2",
        "fixed_term_exception",
    ]

    for field_name in forbidden_none_fields:
        _assert_none(
            facts,
            field_name,
        )

    # --------------------------------------------------------
    # 运行完整 Decision Engine，
    # 确认恶意法律材料仍不能改变事实驱动结果。
    # --------------------------------------------------------

    decision = make_decision(
        question,
        retrieved_articles=retrieved_articles,
    )

    conditions = _condition_results_by_id(
        decision
    )

    # REQUIRED-003：续订劳动合同
    # 当前问题没有明确完成续订，因此必须 UNKNOWN。
    _assert_equal(
        getattr(
            conditions[
                "ARTICLE-14-REQUIRED-003"
            ],
            "status",
            None,
        ),
        "UNKNOWN",
        (
            "Structured Rule 中出现“续订劳动合同”"
            "不能把 REQUIRED-003 自动变成 SATISFIED。"
        ),
    )

    # REQUIRED-004：劳动者提出或者同意
    # 当前问题没有明确表达，因此必须 UNKNOWN。
    _assert_equal(
        getattr(
            conditions[
                "ARTICLE-14-REQUIRED-004"
            ],
            "status",
            None,
        ),
        "UNKNOWN",
        (
            "Structured Rule 中出现“劳动者同意”"
            "不能把 REQUIRED-004 自动变成 SATISFIED。"
        ),
    )

    # EXCLUSION-001：Article 39
    # Retriever 文本不能制造 Article 39 用户事实。
    _assert_equal(
        getattr(
            conditions[
                "ARTICLE-14-EXCLUSION-001"
            ],
            "status",
            None,
        ),
        "UNKNOWN",
        (
            "Retrieved Article 39/排除条文文本"
            "不能自动制造 Article 39 用户事实。"
        ),
    )

    # EXCLUSION-002
    _assert_equal(
        getattr(
            conditions[
                "ARTICLE-14-EXCLUSION-002"
            ],
            "status",
            None,
        ),
        "UNKNOWN",
        (
            "Retrieved Article 40(1) 文本"
            "不能自动制造 Article 40(1) 用户事实。"
        ),
    )

    # EXCLUSION-003
    _assert_equal(
        getattr(
            conditions[
                "ARTICLE-14-EXCLUSION-003"
            ],
            "status",
            None,
        ),
        "UNKNOWN",
        (
            "Retrieved Article 40(2) 文本"
            "不能自动制造 Article 40(2) 用户事实。"
        ),
    )

    print("PASS")


# ============================================================
# Regression Summary
# ============================================================


def main() -> None:
    print()
    print("=" * 70)
    print("RAG V6.9 Retrieval → LegalFacts Boundary Regression Test")
    print("=" * 70)
    print()

    print("测试目标：")
    print("  Retriever / Ranking 不得污染 LegalFacts")
    print("  Retrieved Articles 不得制造用户事实")
    print("  Structured Rule 不得制造用户事实")
    print()

    tests = [
        (
            "CASE 01",
            test_case_01_retrieval_cannot_create_legal_facts,
        ),
        (
            "CASE 02",
            test_case_02_retrieved_articles_do_not_change_fact_state,
        ),
        (
            "CASE 03",
            test_case_03_structured_rule_text_is_not_user_fact,
        ),
    ]

    passed = 0

    for name, test_function in tests:

        try:
            test_function()
            passed += 1

        except Exception as exc:
            print()
            print("=" * 70)
            print(f"{name} FAILED")
            print("=" * 70)
            print()
            print(str(exc))
            print()
            raise

    print()
    print("=" * 70)
    print("V6.9 Retrieval → LegalFacts Boundary Regression Result")
    print("=" * 70)
    print()
    print(f"PASS：{passed}/{len(tests)}")
    print()
    print("边界结论：")
    print("  ✓ Retriever 不得制造 LegalFacts")
    print("  ✓ Ranking metadata 不得制造 LegalFacts")
    print("  ✓ Retrieved Article 不得制造 LegalFacts")
    print("  ✓ Structured Rule 不得制造 LegalFacts")
    print("  ✓ LegalFacts 只能来自用户明确表达")
    print()
    print("V6.9 Retrieval / Ranking Boundary：PASS")
    print()


if __name__ == "__main__":
    main()
