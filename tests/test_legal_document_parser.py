import hashlib

import pytest

from docx import Document

from src.legal_document_parser import (
    NORMALIZATION_PROFILE,
    LegalDocumentParseError,
    normalize_paragraph_text,
    parse_legal_docx,
)


def create_docx(path, paragraphs):
    document = Document()

    for text in paragraphs:
        document.add_paragraph(text)

    document.save(path)

    return path


def test_parser_preserves_empty_paragraph_numbers(tmp_path):
    path = create_docx(
        tmp_path / "empty_paragraphs.docx",
        [
            "第一条 本法第一条正文。",
            "第一款正文。",
            "",
            "第二款正文。",
            "第二条 本法第二条正文。",
        ],
    )

    parsed = parse_legal_docx(path)

    assert len(parsed.paragraphs) == 5

    assert parsed.paragraphs[2].paragraph_number == 3
    assert parsed.paragraphs[2].original_text == ""
    assert parsed.paragraphs[2].normalized_text == ""

    first = parsed.articles[0]

    assert first.article_number == "第一条"
    assert first.article_text == (
        "第一条 本法第一条正文。\n"
        "第一款正文。\n"
        "第二款正文。"
    )

    assert first.source_location.paragraph_start == 1
    assert first.source_location.paragraph_end == 4
    assert first.source_location.paragraph_numbers == (
        1,
        2,
        4,
    )


def test_parser_recognizes_article_extension(tmp_path):
    path = create_docx(
        tmp_path / "article_extension.docx",
        [
            "第一条 基本规定。",
            "第一条之二 补充规定。",
            "第二条 其他规定。",
        ],
    )

    parsed = parse_legal_docx(path)

    assert [
        article.article_number
        for article in parsed.articles
    ] == [
        "第一条",
        "第一条之二",
        "第二条",
    ]


def test_parser_stops_at_chapter_and_section_headings(tmp_path):
    path = create_docx(
        tmp_path / "structure_boundary.docx",
        [
            "第一条 第一条正文。",
            "第二款正文。",
            "第一章 总则",
            "第二条 第二条正文。",
            "第一节 一般规定",
            "第三条 第三条正文。",
        ],
    )

    parsed = parse_legal_docx(path)

    assert len(parsed.articles) == 3

    assert parsed.articles[0].article_text == (
        "第一条 第一条正文。\n"
        "第二款正文。"
    )

    assert parsed.articles[1].article_text == (
        "第二条 第二条正文。"
    )

    assert parsed.articles[2].article_text == (
        "第三条 第三条正文。"
    )

    assert (
        parsed.articles[0].source_location.paragraph_numbers
        == (1, 2)
    )


def test_parser_calculates_three_independent_hashes(tmp_path):
    path = create_docx(
        tmp_path / "hashes.docx",
        [
            "第一条 法律正文。",
            "",
            "第二条 第二条正文。",
        ],
    )

    parsed = parse_legal_docx(path)

    expected_source_hash = hashlib.sha256(
        path.read_bytes()
    ).hexdigest()

    expected_article_hash = hashlib.sha256(
        "第一条 法律正文。".encode("utf-8")
    ).hexdigest()

    assert parsed.source_file_sha256 == expected_source_hash

    assert (
        parsed.articles[0].article_text_sha256
        == expected_article_hash
    )

    assert (
        parsed.normalization_profile
        == NORMALIZATION_PROFILE
    )

    assert len(parsed.normalized_document_sha256) == 64


def test_document_hash_changes_when_empty_paragraph_position_changes(
    tmp_path,
):
    first_path = create_docx(
        tmp_path / "first.docx",
        [
            "第一条 正文。",
            "",
            "第二条 正文。",
        ],
    )

    second_path = create_docx(
        tmp_path / "second.docx",
        [
            "",
            "第一条 正文。",
            "第二条 正文。",
        ],
    )

    first = parse_legal_docx(first_path)
    second = parse_legal_docx(second_path)

    assert (
        first.normalized_document_sha256
        != second.normalized_document_sha256
    )


def test_parser_rejects_tables(tmp_path):
    path = tmp_path / "table.docx"

    document = Document()
    document.add_paragraph("第一条 正文。")

    table = document.add_table(
        rows=1,
        cols=1,
    )
    table.cell(0, 0).text = "表格内容"

    document.save(path)

    with pytest.raises(
        LegalDocumentParseError,
        match="表格",
    ):
        parse_legal_docx(path)


def test_parser_rejects_document_without_articles(tmp_path):
    path = create_docx(
        tmp_path / "no_articles.docx",
        [
            "法律名称",
            "第一章 总则",
            "这是前言。",
        ],
    )

    with pytest.raises(
        LegalDocumentParseError,
        match="没有识别到",
    ):
        parse_legal_docx(path)


def test_parser_normalizes_full_width_text(tmp_path):
    path = create_docx(
        tmp_path / "normalization.docx",
        [
            "第一条　这是正文。",
            "第二条 这是第二条正文。",
        ],
    )

    parsed = parse_legal_docx(path)

    assert parsed.articles[0].article_text == (
        "第一条 这是正文。"
    )



def test_normalization_preserves_unicode_compatibility_characters():
    original = "甲\u3000乙\r\n①㎏\r丙"

    normalized = normalize_paragraph_text(original)

    assert normalized == "甲 乙\n①㎏\n丙"

    # NFKC 会将部分兼容字符转换为其他字符。
    # 法律正文规范化不应执行这种转换。
    assert "①" in normalized
    assert "㎏" in normalized


def test_normalization_does_not_compress_internal_blank_lines():
    original = "甲\n\n乙"

    normalized = normalize_paragraph_text(original)

    assert normalized == "甲\n\n乙"

def test_rejects_unsupported_revision_and_content_elements(tmp_path):
    """
    Parser 必须拒绝不支持的修订、域代码和内容控件元素。
    """
    import pytest
    from docx import Document
    from docx.oxml import OxmlElement

    from src.legal_document_parser import parse_legal_docx

    unsupported_tags = [
        "w:moveFrom",
        "w:moveTo",
        "w:delText",
        "w:fldChar",
        "w:sdt",
        "w:customXml",
        "w:customXmlInsRangeStart",
        "w:customXmlInsRangeEnd",
        "w:customXmlDelRangeStart",
        "w:customXmlDelRangeEnd",
        "w:customXmlMoveFromRangeStart",
        "w:customXmlMoveFromRangeEnd",
        "w:customXmlMoveToRangeStart",
        "w:customXmlMoveToRangeEnd",
    ]

    for index, tag in enumerate(unsupported_tags):
        document = Document()
        document.add_paragraph("第一条 测试正文")

        paragraph = document.add_paragraph("第二条 测试正文")
        element = OxmlElement(tag)
        paragraph._p.append(element)

        path = tmp_path / f"unsupported_{index}.docx"
        document.save(path)

        with pytest.raises(ValueError):
            parse_legal_docx(path)


def test_source_file_hash_matches_original_file_bytes(tmp_path):
    """
    source_file_sha256 必须对应 Parser 实际读取的原始文件字节。
    """
    import hashlib
    from docx import Document

    from src.legal_document_parser import parse_legal_docx

    document = Document()
    document.add_paragraph("第一条 测试正文")

    path = tmp_path / "hash_consistency.docx"
    document.save(path)

    original_bytes = path.read_bytes()

    result = parse_legal_docx(path)

    expected_hash = hashlib.sha256(original_bytes).hexdigest()

    assert result.source_file_sha256 == expected_hash
