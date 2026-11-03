"""
权威 DOCX 法律文档解析器。

职责：
1. 读取 DOCX 正文直接段落。
2. 保留所有原始段落编号，包括空段落。
3. 识别 Article 标题和章、节边界。
4. 生成 Article 正文及 SourceLocation。
5. 计算 source、document、article 三种独立 SHA256。

不负责：
- 创建或修改 Canonical Registry。
- 生成 law_id / version_id / article_id / source_id。
- 生成 Embedding。
- 连接或写入 Qdrant。
"""

from __future__ import annotations

import hashlib
from io import BytesIO
import json
import re
import zipfile

from dataclasses import dataclass
from pathlib import Path
from typing import Tuple

from docx import Document
from docx.oxml.ns import qn

from src.legal_identity import normalize_article_number
from src.legal_registry_models import SourceLocation


NORMALIZATION_PROFILE = "legal-text-normalization-v1"

ARTICLE_NUMBER_PATTERN = (
    r"[零〇一二两三四五六七八九十百千万\d]+"
)

ARTICLE_HEADER_PATTERN = re.compile(
    rf"^(?P<header>第{ARTICLE_NUMBER_PATTERN}条"
    rf"(?:之{ARTICLE_NUMBER_PATTERN})?)(?=\s|$)"
)

STRUCTURE_PATTERN = re.compile(
    rf"^第{ARTICLE_NUMBER_PATTERN}[章节]"
)

# 第一版只允许正文直接段落。
# 这些 XML 元素可能包含无法由 paragraph.text 完整表达的内容。
UNSUPPORTED_PARAGRAPH_ELEMENTS = {
    qn("w:hyperlink"): "超链接",
    qn("w:drawing"): "绘图或图片",
    qn("w:pict"): "旧式图片或 VML 图形",
    qn("w:object"): "嵌入对象",
    qn("w:altChunk"): "外部导入内容",
    qn("w:footnoteReference"): "脚注引用",
    qn("w:endnoteReference"): "尾注引用",
    qn("w:fldSimple"): "Word 域",
    qn("w:instrText"): "Word 域指令",
    qn("w:del"): "修订删除内容",
    qn("w:ins"): "修订插入内容",
    qn("w:txbxContent"): "文本框内容",
    qn("w:moveFrom"): "修订移动来源内容",
    qn("w:moveTo"): "修订移动目标内容",
    qn("w:delText"): "修订删除文本",
    qn("w:fldChar"): "复杂 Word 域结构",
    qn("w:sdt"): "内容控件",
    qn("w:customXml"): "自定义 XML 内容",
    qn("w:customXmlInsRangeStart"): "自定义 XML 插入修订范围起点",
    qn("w:customXmlInsRangeEnd"): "自定义 XML 插入修订范围终点",
    qn("w:customXmlDelRangeStart"): "自定义 XML 删除修订范围起点",
    qn("w:customXmlDelRangeEnd"): "自定义 XML 删除修订范围终点",
    qn("w:customXmlMoveFromRangeStart"): "自定义 XML 移动来源范围起点",
    qn("w:customXmlMoveFromRangeEnd"): "自定义 XML 移动来源范围终点",
    qn("w:customXmlMoveToRangeStart"): "自定义 XML 移动目标范围起点",
    qn("w:customXmlMoveToRangeEnd"): "自定义 XML 移动目标范围终点",
}

# 允许的正文直接子节点。
W_P = qn("w:p")
W_TBL = qn("w:tbl")
W_SECT_PR = qn("w:sectPr")


class LegalDocumentParseError(ValueError):
    """权威法律 DOCX 无法安全解析时抛出。"""


@dataclass(frozen=True)
class ParsedParagraph:
    paragraph_number: int
    original_text: str
    normalized_text: str


@dataclass(frozen=True)
class ParsedArticle:
    article_number: str
    article_text: str
    article_text_sha256: str
    source_location: SourceLocation


@dataclass(frozen=True)
class ParsedDocument:
    source_path: str
    source_file_sha256: str
    normalized_document_sha256: str
    normalization_profile: str
    paragraphs: Tuple[ParsedParagraph, ...]
    articles: Tuple[ParsedArticle, ...]


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()




def calculate_file_sha256(path: Path) -> str:
    """计算原始文件二进制 SHA256，不读取或改写文件内容。"""

    digest = hashlib.sha256()

    with path.open("rb") as file:
        for chunk in iter(
            lambda: file.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def normalize_paragraph_text(text: str) -> str:
    """
    legal-text-normalization-v1 的段落规范化。

    规则：
    1. 仅将全角空格 U+3000 转换为普通空格 U+0020。
    2. 统一 CRLF / CR 为 LF。
    3. 每一行去除首尾空白。
    4. 保留其他 Unicode 字符，不执行全局 NFKC。
    5. 保留段落内部换行。
    6. 不执行 PDF 页码删除。
    7. 不压缩连续空行。
    8. 不改变段落顺序。
    """

    if not isinstance(text, str):
        raise TypeError("段落文本必须是 str")

    text = text.replace("\u3000", " ")

    text = text.replace("\r\n", "\n")
    text = text.replace("\r", "\n")

    lines = [
        line.strip()
        for line in text.split("\n")
    ]

    return "\n".join(lines).strip()


def _validate_docx_package(path: Path, source_bytes: bytes | None = None) -> None:
    """
    检查第一版明确不支持的 DOCX 包结构。

    不修改 DOCX。
    """

    try:
        archive_source = (
            BytesIO(source_bytes)
            if source_bytes is not None
            else path
        )
        with zipfile.ZipFile(archive_source, "r") as archive:
            names = set(archive.namelist())

            unsupported_parts = {
                "word/footnotes.xml": "脚注部件",
                "word/endnotes.xml": "尾注部件",
                "word/comments.xml": "批注部件",
            }

            for part_name, description in unsupported_parts.items():
                if part_name in names:
                    raise LegalDocumentParseError(
                        f"DOCX 包含第一版不支持的{description}："
                        f"{part_name}"
                    )

    except zipfile.BadZipFile as exc:
        raise LegalDocumentParseError(
            f"不是有效的 DOCX ZIP 文件：{path}"
        ) from exc


def _validate_document_body(document) -> None:
    """
    验证正文只包含直接段落和 section properties。

    表格、内容控件及其他未支持的正文容器一律报错，
    防止 document.paragraphs 静默遗漏内容。
    """

    body = document._element.body

    for child in body.iterchildren():
        tag = child.tag

        if tag == W_P:
            continue

        if tag == W_SECT_PR:
            continue

        if tag == W_TBL:
            raise LegalDocumentParseError(
                "DOCX 正文包含表格；第一版 Parser 不支持表格，"
                "为避免正文丢失，已停止解析"
            )

        raise LegalDocumentParseError(
            "DOCX 正文包含未支持的 XML 容器："
            f"{tag}"
        )

    body_paragraph_count = sum(
        1
        for child in body.iterchildren()
        if child.tag == W_P
    )

    if body_paragraph_count != len(document.paragraphs):
        raise LegalDocumentParseError(
            "DOCX 正文直接段落数量与 python-docx "
            "读取结果不一致；可能存在未支持的正文结构"
        )


def _validate_paragraph_elements(
    paragraph,
    paragraph_number: int,
) -> None:
    """
    检查段落内部是否包含第一版无法安全处理的元素。
    """

    for element in paragraph._p.iter():
        description = UNSUPPORTED_PARAGRAPH_ELEMENTS.get(
            element.tag
        )

        if description:
            raise LegalDocumentParseError(
                f"第 {paragraph_number} 个正文段落"
                f"包含不支持的内容：{description}"
            )


def _read_paragraphs(document) -> Tuple[ParsedParagraph, ...]:
    paragraphs = []

    for number, paragraph in enumerate(
        document.paragraphs,
        start=1,
    ):
        _validate_paragraph_elements(
            paragraph,
            number,
        )

        original_text = paragraph.text or ""

        normalized_text = normalize_paragraph_text(
            original_text
        )

        paragraphs.append(
            ParsedParagraph(
                paragraph_number=number,
                original_text=original_text,
                normalized_text=normalized_text,
            )
        )

    return tuple(paragraphs)


def _calculate_document_hash(
    paragraphs: Tuple[ParsedParagraph, ...],
) -> str:
    """
    对规范化后的完整段落序列计算 Hash。

    使用 JSON 数组保留：
    - 段落顺序；
    - 空段落；
    - 每个段落的边界。

    将 normalization profile 纳入 Hash 输入，
    避免不同规范化版本产生相同语义身份。
    """

    payload = {
        "normalization_profile": NORMALIZATION_PROFILE,
        "paragraphs": [
            paragraph.normalized_text
            for paragraph in paragraphs
        ],
    }

    serialized = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )

    return _sha256_bytes(
        serialized.encode("utf-8")
    )


def _extract_article_header(text: str):
    match = ARTICLE_HEADER_PATTERN.match(text)

    if not match:
        return None

    return normalize_article_number(
        match.group("header")
    )


def _finish_article(
    current,
    articles,
) -> None:
    if current is None:
        return

    paragraph_numbers = current["paragraph_numbers"]

    if not paragraph_numbers:
        raise LegalDocumentParseError(
            "法条没有可用于重建正文的段落："
            f"{current['article_number']}"
        )

    article_text = "\n".join(
        current["paragraph_texts"]
    ).strip()

    if not article_text:
        raise LegalDocumentParseError(
            "法条正文为空："
            f"{current['article_number']}"
        )

    source_location = SourceLocation(
        paragraph_start=paragraph_numbers[0],
        paragraph_end=paragraph_numbers[-1],
        paragraph_numbers=tuple(paragraph_numbers),
    )

    articles.append(
        ParsedArticle(
            article_number=current["article_number"],
            article_text=article_text,
            article_text_sha256=_sha256_bytes(
                article_text.encode("utf-8")
            ),
            source_location=source_location,
        )
    )


def _extract_articles(
    paragraphs: Tuple[ParsedParagraph, ...],
) -> Tuple[ParsedArticle, ...]:
    articles = []
    current = None

    for paragraph in paragraphs:
        text = paragraph.normalized_text

        # 空段落保留在 ParsedDocument 中，
        # 但不加入 Article 正文和 SourceLocation。
        if not text:
            continue

        article_number = _extract_article_header(text)

        if article_number is not None:
            if current is not None:
                _finish_article(current, articles)

            current = {
                "article_number": article_number,
                "paragraph_numbers": [
                    paragraph.paragraph_number
                ],
                "paragraph_texts": [text],
            }

            continue

        if STRUCTURE_PATTERN.match(text):
            if current is not None:
                _finish_article(current, articles)
                current = None

            continue

        if current is not None:
            current["paragraph_numbers"].append(
                paragraph.paragraph_number
            )
            current["paragraph_texts"].append(text)

    if current is not None:
        _finish_article(current, articles)

    if not articles:
        raise LegalDocumentParseError(
            "DOCX 中没有识别到任何有效法律条文"
        )

    article_numbers = [
        article.article_number
        for article in articles
    ]

    if len(article_numbers) != len(set(article_numbers)):
        raise LegalDocumentParseError(
            "DOCX 中存在重复的规范化 Article 编号"
        )

    return tuple(articles)


def parse_legal_docx(path) -> ParsedDocument:
    """
    解析权威 DOCX，返回完整、可验证的解析结果。

    本函数只读取文件，不写入 Registry 或 Qdrant。
    """

    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(path)

    if not path.is_file():
        raise ValueError(
            f"输入路径不是普通文件：{path}"
        )

    if path.suffix.lower() != ".docx":
        raise ValueError(
            f"第一版 Parser 只接受 .docx 文件：{path}"
        )

    # 只读取一次原始文件，保证所有处理使用同一份数据。
    source_bytes = path.read_bytes()

    _validate_docx_package(path, source_bytes)

    source_file_sha256 = _sha256_bytes(source_bytes)

    try:
        document = Document(BytesIO(source_bytes))
    except Exception as exc:
        raise LegalDocumentParseError(
            f"DOCX 加载失败：{path}"
        ) from exc

    _validate_document_body(document)

    paragraphs = _read_paragraphs(document)

    normalized_document_sha256 = _calculate_document_hash(
        paragraphs
    )

    articles = _extract_articles(paragraphs)

    return ParsedDocument(
        source_path=str(path.resolve()),
        source_file_sha256=source_file_sha256,
        normalized_document_sha256=normalized_document_sha256,
        normalization_profile=NORMALIZATION_PROFILE,
        paragraphs=paragraphs,
        articles=articles,
    )
