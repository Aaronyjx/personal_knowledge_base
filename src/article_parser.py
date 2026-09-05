# src/article_parser.py

import re
from typing import List, Dict, Any


# ============================================================
# RAG V5.1 - Legal Article Parser
# ============================================================

CHINESE_NUM_MAP = {
    "零": 0,
    "〇": 0,
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
    "万": 10000,
}


def chinese_to_number(text: str) -> int:
    """
    中文数字转阿拉伯数字

    示例：
        一 -> 1
        十 -> 10
        十九 -> 19
        二十 -> 20
        九十九 -> 99
        一百 -> 100
        一百零二 -> 102
    """

    text = text.strip()

    if text.isdigit():
        return int(text)

    total = 0
    section = 0
    number = 0

    for char in text:

        if char not in CHINESE_NUM_MAP:
            continue

        value = CHINESE_NUM_MAP[char]

        if value == 10:
            if number == 0:
                number = 1

            section += number * 10
            number = 0

        elif value == 100:
            if number == 0:
                number = 1

            section += number * 100
            number = 0

        elif value == 1000:
            if number == 0:
                number = 1

            section += number * 1000
            number = 0

        elif value == 10000:
            section = (section + number) * 10000
            total += section
            section = 0
            number = 0

        else:
            number = value

    return total + section + number


# ============================================================
# 文本清洗
# ============================================================

def clean_text(text: str) -> str:
    """
    清理 PDF / DOCX 中常见的格式问题。
    """

    if not text:
        return ""

    # 去掉 PDF 页码，例如：
    # －1－
    # -1-
    # — 1 —
    text = re.sub(
        r"(?m)^\s*[－\-—–]\s*\d+\s*[－\-—–]\s*$",
        "",
        text
    )

    # 统一空白字符
    text = text.replace("\u3000", " ")
    text = text.replace("\xa0", " ")

    # 删除行尾多余空格
    text = re.sub(r"[ \t]+$", "", text, flags=re.MULTILINE)

    # 连续空行压缩
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


# ============================================================
# 判断是不是法律条款标题
# ============================================================

ARTICLE_PATTERN = re.compile(
    r"(?m)^[ \t]*"
    r"第([零〇一二两三四五六七八九十百千万]+)条"
    r"[ \t]*"
)


def find_article_positions(text: str):
    """
    找出全文中所有“第X条”的位置。
    """

    return list(ARTICLE_PATTERN.finditer(text))


# ============================================================
# 提取法律条款
# ============================================================

def extract_articles(
    text: str,
    source: str = "",
    page: Any = None,
) -> List[Dict[str, Any]]:
    """
    从完整法律文本中提取全部法律条款。

    参数：
        text:
            完整法律文本

        source:
            文件名

        page:
            默认页码（DOCX通常为空）

    返回：
        [
            {
                "article_number": "第十九条",
                "article_index": 19,
                "article_text": "...",
                "source": "...",
                "page": ...
            }
        ]
    """

    text = clean_text(text)

    if not text:
        return []

    matches = find_article_positions(text)

    if not matches:
        return []

    articles = []

    for i, match in enumerate(matches):

        article_number_text = match.group(1)

        article_index = chinese_to_number(article_number_text)

        article_number = f"第{article_number_text}条"

        start = match.start()

        if i + 1 < len(matches):
            end = matches[i + 1].start()
        else:
            end = len(text)

        article_text = text[start:end].strip()

        # ====================================================
        # 基础过滤
        # ====================================================

        if len(article_text) < 5:
            continue

        # ====================================================
        # 防止把目录误认为正文
        # ====================================================

        # 如果条款内容明显只是目录结构，则跳过
        first_line = article_text.split("\n")[0].strip()

        if (
            len(article_text) < 30
            and (
                "第一章" in article_text
                or "第二章" in article_text
                or "第三章" in article_text
                or "第四章" in article_text
            )
        ):
            continue

        articles.append(
            {
                "article_number": article_number,
                "article_index": article_index,
                "article_text": article_text,
                "source": source,
                "page": page,
                "text": article_text,
            }
        )

    return articles


# ============================================================
# 从 document blocks 中提取法律条款
# ============================================================

def extract_articles_from_blocks(
    blocks: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    将 load_document() 返回的多个 Block 合并后，
    再进行统一法律条款解析。

    这是 V5.1 的核心升级。
    """

    if not blocks:
        return []

    full_text_parts = []

    source = ""
    pages = []

    for block in blocks:

        if not block:
            continue

        text = block.get("text", "")

        if not text:
            continue

        full_text_parts.append(str(text))

        if not source:
            source = block.get("source", "")

        page = block.get("page")

        if page not in (None, ""):
            pages.append(page)

    full_text = "\n".join(full_text_parts)

    articles = extract_articles(
        full_text,
        source=source,
        page=pages[0] if pages else None,
    )

    return articles


# ============================================================
# 自动解析数量
# ============================================================

def count_articles(text: str) -> int:
    """
    返回全文识别到的法律条款数量。
    """

    return len(extract_articles(text))


# ============================================================
# 连续性检查
# ============================================================

def validate_article_sequence(
    articles: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    检查条款编号是否连续。

    示例：

    1,2,3,4,5
    -> 正常

    1,2,4,5
    -> 缺少第3条
    """

    if not articles:
        return {
            "valid": False,
            "count": 0,
            "missing": [],
            "duplicates": [],
        }

    numbers = [
        item["article_index"]
        for item in articles
        if item.get("article_index") is not None
    ]

    duplicates = sorted(
        {
            n
            for n in numbers
            if numbers.count(n) > 1
        }
    )

    if not numbers:
        return {
            "valid": False,
            "count": 0,
            "missing": [],
            "duplicates": [],
        }

    max_number = max(numbers)

    expected = set(range(1, max_number + 1))
    actual = set(numbers)

    missing = sorted(expected - actual)

    return {
        "valid": len(missing) == 0 and len(duplicates) == 0,
        "count": len(numbers),
        "max_article": max_number,
        "missing": missing,
        "duplicates": duplicates,
    }


# ============================================================
# 诊断输出
# ============================================================

def diagnostic_articles(
    articles: List[Dict[str, Any]],
    title: str = ""
):
    """
    输出法律条款解析诊断结果。
    """

    print()
    print("=" * 70)
    print("RAG V5.1 Article Parser Diagnostic")
    print("=" * 70)

    if title:
        print("文件：", title)

    print("提取条款数量：", len(articles))

    validation = validate_article_sequence(articles)

    print("最大条款编号：", validation.get("max_article"))
    print("缺失条款：", validation.get("missing"))
    print("重复条款：", validation.get("duplicates"))

    if validation["valid"]:
        print("状态：✅ 条款编号连续")
    else:
        print("状态：⚠️ 条款编号存在异常")

    print()

    for i, article in enumerate(articles[:10], 1):

        print(
            f"[{i}] "
            f"{article['article_number']} "
            f"长度={len(article['article_text'])}"
        )

        preview = article["article_text"].replace("\n", " ")

        if len(preview) > 100:
            preview = preview[:100] + "..."

        print("    ", preview)

    if len(articles) > 10:
        print()
        print(f"... 共 {len(articles)} 条，以上仅显示前10条")

    print("=" * 70)