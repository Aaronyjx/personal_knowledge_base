"""法律法条切分边界回归测试。"""

import pytest

from src.ingest import split_articles


def article_texts(text):
    """提取切分结果中的法条正文。"""
    return [
        item["article_text"]
        for item in split_articles(text)
    ]


def test_adjacent_articles_are_split_normally():
    """相邻法条仍然按照下一条法条标题切分。"""
    text = (
        "第一条 本法用于规范劳动关系。\n"
        "第二条 本法适用于中华人民共和国境内的企业。"
    )

    articles = split_articles(text)

    assert len(articles) == 2
    assert articles[0]["article_number"] == "第一条"
    assert articles[1]["article_number"] == "第二条"
    assert "第二条" not in articles[0]["article_text"]


def test_chapter_heading_terminates_previous_article():
    """独立章标题不能被纳入上一条法条。"""
    text = (
        "第三十五条 用人单位与劳动者协商一致，"
        "可以变更劳动合同约定的内容。\n"
        "\n"
        "第四章 劳动合同的解除和终止\n"
        "\n"
        "第三十六条 用人单位与劳动者协商一致，"
        "可以解除劳动合同。"
    )

    articles = split_articles(text)

    assert len(articles) == 2
    assert "第四章" not in articles[0]["article_text"]
    assert "第三十六条" not in articles[0]["article_text"]


def test_section_heading_terminates_previous_article():
    """独立节标题也应当构成法条结束边界。"""
    text = (
        "第十六条 劳动合同由用人单位与劳动者协商一致订立。\n"
        "第二节 申请和受理\n"
        "第十七条 劳动争议仲裁委员会负责管辖本区域内的劳动争议。"
    )

    articles = split_articles(text)

    assert len(articles) == 2
    assert "第二节" not in articles[0]["article_text"]
    assert "第十七条" not in articles[0]["article_text"]


def test_final_article_ends_before_trailing_chapter_heading():
    """最后一条法条之后的独立章标题不能进入法条正文。"""
    text = (
        "第五十一条 当事人对发生法律效力的调解书，"
        "应当依照规定履行。\n"
        "第四章 附则"
    )

    articles = split_articles(text)

    assert len(articles) == 1
    assert "第四章" not in articles[0]["article_text"]


def test_final_article_ends_before_trailing_section_heading():
    """最后一条法条之后的独立节标题不能进入法条正文。"""
    text = (
        "第六十七条 非全日制用工双方当事人可以订立口头协议。\n"
        "第三节 非全日制用工"
    )

    articles = split_articles(text)

    assert len(articles) == 1
    assert "第三节" not in articles[0]["article_text"]


@pytest.mark.parametrize(
    "heading",
    [
        "第四章 劳动合同的解除和终止",
        "第二节 申请和受理",
        "第十三章 附则",
        "第一章",
        "第六节 非全日制用工",
        "第4章 劳动合同的解除和终止",
        "第2节 申请和受理",
    ],
)
def test_chapter_and_section_headings_are_boundaries(heading):
    """不同数字形式、章标题和节标题均应构成边界。"""
    text = (
        "第一条 本法用于规范劳动关系。\n"
        f"{heading}\n"
        "第二条 本法适用于中华人民共和国境内的企业。"
    )

    articles = split_articles(text)

    assert len(articles) == 2
    assert heading not in articles[0]["article_text"]


@pytest.mark.parametrize(
    "sentence",
    [
        "根据第四章的规定，用人单位应当依法处理。",
        "劳动者应当遵守本法第四章的有关规定。",
        "第三十五条 用人单位应当遵守第四章的规定。",
        "本法第四章规定了劳动合同解除和终止的相关事项。",
    ],
)
def test_inline_chapter_references_do_not_create_boundaries(sentence):
    """正文中的章节引用不能被误判为独立章节标题。"""
    text = (
        "第一条 "
        + sentence
        + "\n第二条 本法适用于中华人民共和国境内的企业。"
    )

    articles = split_articles(text)

    assert len(articles) == 2
    assert sentence in articles[0]["article_text"]


def test_chapter_heading_does_not_create_an_article():
    """章节标题本身不能被识别为法条。"""
    text = (
        "第一条 本法用于规范劳动关系。\n"
        "第四章 劳动合同的解除和终止"
    )

    articles = split_articles(text)

    assert len(articles) == 1
    assert all(
        item["article_number"].endswith("条")
        for item in articles
    )


@pytest.mark.parametrize(
    "text",
    [
        "",
        "   ",
        "\n\n",
    ],
)
def test_empty_input_returns_empty_list(text):
    """空输入保持原有行为。"""
    assert split_articles(text) == []
