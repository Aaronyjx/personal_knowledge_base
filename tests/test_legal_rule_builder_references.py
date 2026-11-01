from copy import deepcopy
from types import SimpleNamespace

from src.legal_rule_builder import (
    build_rules_from_articles,
    normalize_rule,
)


def make_structured_references():
    """构造包含嵌套 location 的结构化法律引用。"""

    return [
        {
            "reference_id": "reference-001",
            "rule_id": "RULE-001",
            "article_id": "article-014",
            "reference_type": "PRIMARY",
            "legal_role": "主要法律依据",
            "location": None,
        },
        {
            "reference_id": "reference-002",
            "rule_id": "RULE-001",
            "article_id": "article-040",
            "reference_type": "EXCLUSION",
            "legal_role": "排除情形",
            "location": {
                "paragraph_number": None,
                "item_number": 1,
                "subitem_number": None,
            },
        },
    ]


def test_normalize_rule_deepcopies_structured_references():
    """normalize_rule 不得与输入共享引用列表及嵌套对象。"""

    references = make_structured_references()

    article = {
        "law_name": "中华人民共和国劳动合同法",
        "article_number": "第十四条",
        "rule_summary": "无固定期限劳动合同",
        "references": references,
    }

    original = deepcopy(references)

    result = normalize_rule(article)

    assert result["references"] == original
    assert result["references"] is not article["references"]
    assert result["references"][1] is not article["references"][1]
    assert (
        result["references"][1]["location"]
        is not article["references"][1]["location"]
    )

    result["references"][1]["location"]["item_number"] = 2

    assert article["references"] == original


def test_normalize_rule_reads_references_from_object_input():
    """对象形式的 Article 也必须保留并隔离 references。"""

    references = make_structured_references()

    article = SimpleNamespace(
        law_name="中华人民共和国劳动合同法",
        article_number="第十四条",
        rule_summary="无固定期限劳动合同",
        references=references,
    )

    result = normalize_rule(article)

    assert result["references"] == references
    assert result["references"] is not references
    assert result["references"][1]["location"] is not (
        references[1]["location"]
    )

    result["references"][1]["location"]["item_number"] = 2

    assert references[1]["location"]["item_number"] == 1


def test_build_rules_from_articles_isolates_references():
    """Rules 构建结果不能与输入 Article 共享引用对象。"""

    references = make_structured_references()

    article = {
        "law_name": "中华人民共和国劳动合同法",
        "article_number": "第十四条",
        "rule_summary": "无固定期限劳动合同",
        "references": references,
    }

    original = deepcopy(references)

    rules = build_rules_from_articles([article])

    assert len(rules) == 1
    assert rules[0]["references"] == original
    assert rules[0]["references"] is not article["references"]

    rules[0]["references"][1]["location"]["item_number"] = 2

    assert article["references"] == original


def test_normalize_rule_without_references_remains_compatible():
    """没有 references 的旧 Article 不应被强制增加该字段。"""

    article = {
        "law_name": "测试法律",
        "article_number": "第一条",
        "rule_summary": "测试规则",
    }

    result = normalize_rule(article)

    assert "references" not in result
    assert result["law_name"] == "测试法律"
    assert result["article_number"] == "第一条"


def test_build_structured_context_preserves_and_isolates_references(
    monkeypatch,
):
    """Context Builder 必须保留结构化引用并隔离 Articles 与 Rules。"""

    import src.legal_context_builder as context_builder

    references = make_structured_references()

    articles = [
        {
            "law_name": "中华人民共和国劳动合同法",
            "article_number": "第十四条",
            "rule_summary": "无固定期限劳动合同",
            "references": references,
        }
    ]

    original_references = deepcopy(references)

    def fake_build_context(**kwargs):
        assert kwargs["return_articles"] is True
        return articles

    monkeypatch.setattr(
        context_builder,
        "build_context",
        fake_build_context,
    )

    result = context_builder.build_structured_context(
        question="连续订立固定期限劳动合同",
    )

    # Articles 应保持 Retriever 返回的数据。
    assert result["articles"] is articles
    assert result["articles"][0]["references"] == original_references

    # Rules 必须保留结构化引用。
    assert len(result["rules"]) == 1

    rule_references = result["rules"][0]["references"]

    assert rule_references == original_references
    assert rule_references is not references
    assert rule_references[1] is not references[1]
    assert (
        rule_references[1]["location"]
        is not references[1]["location"]
    )

    # 修改最终 Rules 不得污染原始 Articles。
    rule_references[1]["location"]["item_number"] = 2

    assert articles[0]["references"] == original_references

    # 展示层只生成法律依据文本，不应把结构化引用序列化进 Context。
    assert "第十四条" in result["context"]
    assert "无固定期限劳动合同" in result["context"]
    assert "reference-001" not in result["context"]
