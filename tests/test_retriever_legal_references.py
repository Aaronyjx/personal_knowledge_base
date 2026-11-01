from copy import deepcopy

from src.retriever import (
    expand_legal_references,
    extract_article_references,
)


def test_structured_reference_dicts_are_not_parsed_as_text():
    """结构化法律引用字典不能进入条号文本解析器。"""

    article = {
        "references": [
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
    }

    result = extract_article_references(article)

    assert result == []


def test_legacy_string_references_remain_supported():
    """旧格式字符串 references 继续支持条号提取。"""

    article = {
        "references": [
            "本规则同时涉及《劳动合同法》第三十九条。",
            "另参见《劳动合同法》第四十条。",
        ]
    }

    result = extract_article_references(article)

    assert "第三十九条" in result
    assert "第四十条" in result


def test_article_text_references_are_still_extracted():
    """正文中的法律条号引用仍然正常提取。"""

    article = {
        "text": (
            "根据《中华人民共和国劳动合同法》第三十九条，"
            "以及该法第四十条的规定。"
        )
    }

    result = extract_article_references(article)

    assert "第三十九条" in result
    assert "第四十条" in result


def test_expand_legal_references_preserves_structured_references():
    """引用扩展不能修改输入 Article 的结构化引用。"""

    structured_references = [
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

    article = {
        "law_name": "中华人民共和国劳动合同法",
        "article_number": "第十四条",
        "references": deepcopy(structured_references),
    }

    original_references = deepcopy(article["references"])

    result = expand_legal_references([article])

    assert len(result) == 1

    expanded_article = result[0]

    # 结构化引用内容必须完整保留。
    assert expanded_article["references"] == original_references

    # 扩展结果不能与输入对象共享嵌套引用对象。
    assert expanded_article["references"] is not article["references"]
    assert (
        expanded_article["references"][1]["location"]
        is not article["references"][1]["location"]
    )

    # 结构化引用不能被误解析成传统条号引用。
    assert expanded_article["_legal_references"] == []

    # 修改扩展结果不能污染输入 Article。
    expanded_article["references"][1]["location"]["item_number"] = 2

    assert article["references"] == original_references
