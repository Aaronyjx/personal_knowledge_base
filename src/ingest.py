# -*- coding: utf-8 -*-

"""
RAG V5.1
法律知识库增量入库

功能：

1. 自动扫描 data/raw/
2. 支持 PDF / DOCX / TXT / MD
3. 使用 document_loader.load_document()
4. 自动识别法律条款
5. DOCX 整文 Block 自动拆分成独立条款
6. PDF 多页面 Block 自动合并后拆分条款
7. 使用 BGE-M3 生成向量
8. 写入 Qdrant
9. 保存法律名称、法条编号、条款正文、来源文件、页码等 metadata
10. 支持增量入库
11. 使用稳定 UUID 避免重复
12. 同一法律 + 同一条款重复运行时自动更新
"""


# ============================================================
# 标准库
# ============================================================

from pathlib import Path
import hashlib
import re
import sys
import time
from typing import List, Dict, Optional


# ============================================================
# 项目路径
# ============================================================

BASE_DIR = Path(
    __file__
).resolve().parent.parent

DATA_DIR = BASE_DIR / "data"

RAW_DIR = DATA_DIR / "raw"

SRC_DIR = BASE_DIR / "src"


# ============================================================
# Python Path
# ============================================================

if str(BASE_DIR) not in sys.path:

    sys.path.insert(
        0,
        str(BASE_DIR)
    )


# ============================================================
# 导入项目模块
# ============================================================

from src.document_loader import (
    load_document
)

from src.embedding import (
    embed_texts
)

from src.vector_store import (
    ensure_collection,
    upsert_documents,
    make_point_id,
)


# ============================================================
# 支持的文件类型
# ============================================================

SUPPORTED_EXTENSIONS = {

    ".pdf",

    ".docx",

    ".txt",

    ".md",
}


# ============================================================
# 法律条款标题
# ============================================================

"""
注意：

这里必须限制为“行首”。

正确：

第一条 为了……
第二条 中华人民共和国……

错误：

根据劳动合同法第八十二条规定……

否则正文里的法律引用也可能被当成新条款。
"""

ARTICLE_PATTERN = re.compile(
    r"""
    (?m)
    ^
    (?P<header>
        第
        [零〇一二两三四五六七八九十百千万\d]+
        条
    )
    (?=\s|$)
    """,
    re.VERBOSE,
)


# ============================================================
# 清理文本
# ============================================================

def clean_text(
    text: str
) -> str:
    """
    清理 PDF / DOCX 中的格式噪音。

    处理：

    1. 全角空格
    2. Windows 换行
    3. PDF 页码
    4. 行尾空格
    5. 连续空行
    """

    if not text:

        return ""

    text = str(text)

    # --------------------------------------------------------
    # 全角空格
    # --------------------------------------------------------

    text = text.replace(
        "\u3000",
        " "
    )

    # --------------------------------------------------------
    # 换行统一
    # --------------------------------------------------------

    text = text.replace(
        "\r\n",
        "\n"
    )

    text = text.replace(
        "\r",
        "\n"
    )

    # --------------------------------------------------------
    # PDF 页码
    #
    # 例如：
    #
    # －1－
    # －2－
    # -1-
    #
    # --------------------------------------------------------

    text = re.sub(
        r"(?m)^\s*[－-]?\s*\d+\s*[－-]?\s*$",
        "",
        text,
    )

    # --------------------------------------------------------
    # 行首行尾空白
    # --------------------------------------------------------

    lines = []

    for line in text.split("\n"):

        line = line.strip()

        lines.append(line)

    text = "\n".join(lines)

    # --------------------------------------------------------
    # 连续空行
    # --------------------------------------------------------

    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text,
    )

    return text.strip()


# ============================================================
# 判断是否是法条标题
# ============================================================

def is_article_header(
    text: str
) -> bool:
    """
    判断一行是不是：

        第一条
        第二条
        第十九条
        第一百零二条

    """

    if not text:

        return False

    text = text.strip()

    return bool(
        re.match(
            r"^第[零〇一二两三四五六七八九十百千万\d]+条(?=\s|$)",
            text,
        )
    )


# ============================================================
# 提取法条编号
# ============================================================

def extract_article_number(
    text: str
) -> Optional[str]:
    """
    从：

        第十九条 劳动合同期限……

    提取：

        第十九条
    """

    if not text:

        return None

    match = re.match(
        r"^(第[零〇一二两三四五六七八九十百千万\d]+条)",
        text.strip(),
    )

    if match:

        return match.group(1)

    return None


# ============================================================
# 拆分整份法律文本
# ============================================================

def split_articles(
    text: str
) -> List[Dict]:
    """
    将整份法律文本拆成独立法条。

    输入：

        第一条……
        第二条……
        第三条……

    输出：

        [
            {
                "article_number": "第一条",
                "article_text": "第一条……"
            },
            ...
        ]

    """

    text = clean_text(text)

    if not text:

        return []

    # --------------------------------------------------------
    # 找所有“行首法条”
    # --------------------------------------------------------

    matches = list(
        ARTICLE_PATTERN.finditer(text)
    )

    if not matches:

        return []

    articles = []

    # --------------------------------------------------------
    # 逐条切割
    # --------------------------------------------------------

    for index, match in enumerate(
        matches
    ):

        start = match.start()

        if index + 1 < len(matches):

            end = matches[
                index + 1
            ].start()

        else:

            end = len(text)

        article_text = text[
            start:end
        ].strip()

        if not article_text:

            continue

        article_number = match.group(
            "header"
        )

        articles.append(
            {
                "article_number":
                    article_number,

                "article_text":
                    article_text,
            }
        )

    return articles


# ============================================================
# 判断无效条款
# ============================================================

def is_noise_article(
    article_text: str
) -> bool:
    """
    排除明显无效的条款。

    注意：

    不能因为正文包含“第一章”等关键词
    就过滤整个法条。

    这里只过滤：

        空文本
        极短文本
        明显目录噪音
    """

    if not article_text:

        return True

    text = article_text.strip()

    # --------------------------------------------------------
    # 太短
    # --------------------------------------------------------

    if len(text) < 8:

        return True

    # --------------------------------------------------------
    # 明显目录
    # --------------------------------------------------------

    noise_exact = {

        "第一章",

        "第二章",

        "第三章",

        "第四章",

        "第五章",

        "第六章",

        "第七章",

        "第八章",

        "第九章",

        "第十章",

        "第一节",

        "第二节",

        "第三节",

        "第四节",
    }

    if text in noise_exact:

        return True

    return False


# ============================================================
# 从 Blocks 提取法律条款
# ============================================================

def extract_articles_from_blocks(
    blocks: List[Dict]
) -> List[Dict]:
    """
    兼容当前 document_loader.py 的实际结构。

    DOCX：

        load_document()
        ↓
        1 Block
        ↓
        Block 内包含整份法律
        ↓
        再统一拆分

    PDF：

        load_document()
        ↓
        多个 Block
        ↓
        每个 Block 通常对应页面
        ↓
        合并
        ↓
        再统一拆分
    """

    if not blocks:

        return []

    all_text_parts = []

    # --------------------------------------------------------
    # 收集所有 Block
    # --------------------------------------------------------

    for block in blocks:

        if not isinstance(
            block,
            dict
        ):

            continue

        text = block.get(
            "text",
            ""
        )

        if not text:

            continue

        text = clean_text(
            text
        )

        if text:

            all_text_parts.append(
                text
            )

    # --------------------------------------------------------
    # 合并
    # --------------------------------------------------------

    full_text = "\n".join(
        all_text_parts
    )

    full_text = clean_text(
        full_text
    )

    if not full_text:

        return []

    # --------------------------------------------------------
    # 拆分
    # --------------------------------------------------------

    articles = split_articles(
        full_text
    )

    # --------------------------------------------------------
    # 过滤
    # --------------------------------------------------------

    valid_articles = []

    for article in articles:

        if is_noise_article(
            article["article_text"]
        ):

            continue

        valid_articles.append(
            article
        )

    return valid_articles


# ============================================================
# 从 Block 中推断页码
# ============================================================

def get_article_page(
    blocks: List[Dict],
    article_text: str,
) -> Optional[int]:
    """
    尝试根据法条正文所在 Block 推断页码。

    对 DOCX：

        page 通常为空

    对 PDF：

        page 通常为数字

    这里做一个简单兼容处理。

    如果找不到，则返回 None。
    """

    if not blocks:

        return None

    first_line = (
        article_text
        .splitlines()[0]
        .strip()
    )

    article_number = extract_article_number(
        first_line
    )

    if not article_number:

        return None

    # --------------------------------------------------------
    # 查找包含该法条的 Block
    # --------------------------------------------------------

    for block in blocks:

        if not isinstance(
            block,
            dict
        ):

            continue

        block_text = block.get(
            "text",
            ""
        )

        if not block_text:

            continue

        block_text = clean_text(
            block_text
        )

        # 法条编号必须出现在 Block 行首
        pattern = re.compile(
            rf"(?m)^{re.escape(article_number)}(?=\s|$)"
        )

        if pattern.search(
            block_text
        ):

            page = block.get(
                "page"
            )

            if page is not None:

                try:

                    return int(page)

                except (
                    TypeError,
                    ValueError,
                ):

                    return None

    return None


# ============================================================
# 推断法律名称
# ============================================================

def infer_law_name(
    file_path: Path,
    blocks: Optional[List[Dict]] = None,
) -> str:
    """
    优先使用文件名。

    例如：

        中华人民共和国劳动合同法.pdf

    得到：

        中华人民共和国劳动合同法
    """

    name = file_path.stem.strip()

    if name:

        return name

    # --------------------------------------------------------
    # 文件名为空时，从正文第一行推断
    # --------------------------------------------------------

    if blocks:

        for block in blocks:

            if not isinstance(
                block,
                dict
            ):

                continue

            text = block.get(
                "text",
                ""
            )

            if not text:

                continue

            lines = [

                line.strip()

                for line in text.splitlines()

                if line.strip()
            ]

            if lines:

                return lines[0]

    return "未知法律"


# ============================================================
# 计算文件 Hash
# ============================================================

def calculate_file_hash(
    file_path: Path
) -> str:
    """
    SHA256 文件 Hash。

    用于记录文件版本。
    """

    sha256 = hashlib.sha256()

    with open(
        file_path,
        "rb"
    ) as f:

        while True:

            chunk = f.read(
                1024 * 1024
            )

            if not chunk:

                break

            sha256.update(
                chunk
            )

    return sha256.hexdigest()


# ============================================================
# 构造 Metadata
# ============================================================

def build_metadata(
    file_path: Path,
    law_name: str,
    article_number: str,
    article_text: str,
    file_hash: str,
    page=None,
) -> Dict:
    """
    构造 Qdrant Payload。
    """

    metadata = {

        # ----------------------------------------------------
        # 法律名称
        # ----------------------------------------------------

        "law_name":
            law_name,

        # ----------------------------------------------------
        # 法条编号
        # ----------------------------------------------------

        "article_number":
            article_number,

        # ----------------------------------------------------
        # 完整法条
        # ----------------------------------------------------

        "article_text":
            article_text,

        # ----------------------------------------------------
        # 来源文件
        # ----------------------------------------------------

        "source":
            file_path.name,

        "source_file":
            str(
                file_path.relative_to(
                    BASE_DIR
                )
            ),

        # ----------------------------------------------------
        # 文件 Hash
        # ----------------------------------------------------

        "file_hash":
            file_hash,

        # ----------------------------------------------------
        # 页码
        # ----------------------------------------------------

        "page":
            page,

        # ----------------------------------------------------
        # 类型
        # ----------------------------------------------------

        "text_source":
            "legal_article",

        # ----------------------------------------------------
        # 文本长度
        # ----------------------------------------------------

        "text_length":
            len(article_text),

        # ----------------------------------------------------
        # 入库时间
        # ----------------------------------------------------

        "ingest_time":
            time.strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
    }

    return metadata


# ============================================================
# 处理单个文件
# ============================================================

def process_file(
    file_path: Path
) -> int:
    """
    处理单个法律文件。
    """

    print()

    print(
        "=" * 70
    )

    print(
        f"处理文件：{file_path.name}"
    )

    print(
        "=" * 70
    )

    # ========================================================
    # 文件 Hash
    # ========================================================

    file_hash = calculate_file_hash(
        file_path
    )

    print(
        "文件 Hash：",
        file_hash[:16] + "..."
    )

    # ========================================================
    # 加载文档
    # ========================================================

    try:

        blocks = load_document(
            str(file_path)
        )

    except Exception as e:

        print()

        print(
            "❌ 文档加载失败"
        )

        print(
            "错误：",
            e
        )

        return 0

    print(
        "load_document 返回数量：",
        len(blocks)
    )

    if not blocks:

        print(
            "⚠️ 没有读取到内容"
        )

        return 0

    # ========================================================
    # 法律名称
    # ========================================================

    law_name = infer_law_name(
        file_path,
        blocks,
    )

    print(
        "法律名称：",
        law_name
    )

    # ========================================================
    # 提取法律条款
    # ========================================================

    articles = extract_articles_from_blocks(
        blocks
    )

    print(
        "提取条款：",
        len(articles)
    )

    if not articles:

        print()

        print(
            "⚠️ 没有提取到任何法律条款"
        )

        return 0

    # ========================================================
    # 条款预览
    # ========================================================

    print()

    print(
        "条款预览："
    )

    for article in articles[:3]:

        preview = article[
            "article_text"
        ].replace(
            "\n",
            " "
        )

        print(
            f"  "
            f"{article['article_number']} "
            f"{preview[:100]}"
        )

    if len(articles) > 3:

        print(
            f"  ... 共 {len(articles)} 条"
        )

    # ========================================================
    # 构造 Embedding 文本
    # ========================================================

    texts = [

        article[
            "article_text"
        ]

        for article in articles
    ]

    print()

    print(
        "开始生成 BGE-M3 Embedding..."
    )

    try:

        embeddings = embed_texts(
            texts
        )

    except Exception as e:

        print()

        print(
            "❌ Embedding 失败"
        )

        print(
            "错误：",
            e
        )

        return 0

    # ========================================================
    # 检查数量
    # ========================================================

    if len(embeddings) != len(
        articles
    ):

        raise RuntimeError(
            "Embedding 数量与条款数量不一致："
            f"{len(embeddings)} != "
            f"{len(articles)}"
        )

    # ========================================================
    # 构造 Qdrant Documents
    # ========================================================

    documents = []

    for article, vector in zip(
        articles,
        embeddings,
    ):

        article_number = article[
            "article_number"
        ]

        article_text = article[
            "article_text"
        ]

        # ----------------------------------------------------
        # 使用 vector_store 统一生成稳定 ID
        #
        # 同一法律 + 同一条款
        # 永远得到相同 UUID
        # ----------------------------------------------------

        point_id = make_point_id(
            law_name,
            article_number,
        )

        # ----------------------------------------------------
        # 页码
        # ----------------------------------------------------

        page = get_article_page(
            blocks,
            article_text,
        )

        # ----------------------------------------------------
        # Metadata
        # ----------------------------------------------------

        metadata = build_metadata(

            file_path=file_path,

            law_name=law_name,

            article_number=article_number,

            article_text=article_text,

            file_hash=file_hash,

            page=page,
        )

        # ----------------------------------------------------
        # Document
        # ----------------------------------------------------

        documents.append(

            {
                "id":
                    point_id,

                "text":
                    article_text,

                "vector":
                    vector,

                "payload":
                    metadata,
            }
        )

    # ========================================================
    # 写入 Qdrant
    # ========================================================

    print()

    print(
        "写入 Qdrant：",
        len(documents)
    )

    try:

        written = upsert_documents(
            documents
        )

    except Exception as e:

        print()

        print(
            "❌ Qdrant 写入失败"
        )

        print(
            "错误：",
            e
        )

        raise

    print()

    print(
        f"✅ 成功写入 Qdrant：{written}"
    )

    return written


# ============================================================
# 扫描 data/raw/
# ============================================================

def find_documents() -> List[Path]:
    """
    扫描：

        data/raw/

    支持：

        PDF
        DOCX
        TXT
        MD
    """

    if not RAW_DIR.exists():

        print()

        print(
            "❌ 数据目录不存在：",
            RAW_DIR
        )

        return []

    files = []

    for path in RAW_DIR.rglob("*"):

        if not path.is_file():

            continue

        if (
            path.suffix.lower()
            not in SUPPORTED_EXTENSIONS
        ):

            continue

        files.append(
            path
        )

    return sorted(
        files
    )


# ============================================================
# 执行完整入库
# ============================================================

def ingest():
    """
    执行完整增量入库。
    """

    print()

    print(
        "=" * 70
    )

    print(
        "RAG V5.1 - 法律知识库增量入库"
    )

    print(
        "=" * 70
    )

    # ========================================================
    # 项目目录
    # ========================================================

    print()

    print(
        "项目目录："
    )

    print(
        BASE_DIR
    )

    print()

    print(
        "数据目录："
    )

    print(
        RAW_DIR
    )

    # ========================================================
    # Qdrant
    # ========================================================

    print()

    print(
        "检查 Qdrant Collection..."
    )

    ensure_collection()

    # ========================================================
    # 扫描文件
    # ========================================================

    files = find_documents()

    print()

    print(
        "发现文件：",
        len(files)
    )

    if not files:

        print()

        print(
            "⚠️ data/raw/ 中没有支持的文件"
        )

        return

    # ========================================================
    # 文件列表
    # ========================================================

    print()

    for index, file_path in enumerate(
        files,
        start=1,
    ):

        print(
            f"{index}. {file_path.name}"
        )

    # ========================================================
    # 开始处理
    # ========================================================

    total = 0

    success_files = 0

    failed_files = 0

    # ========================================================
    # 逐个文件
    # ========================================================

    for file_path in files:

        try:

            count = process_file(
                file_path
            )

            if count > 0:

                total += count

                success_files += 1

            else:

                failed_files += 1

        except Exception as e:

            print()

            print(
                "❌ 文件处理异常：",
                file_path.name
            )

            print(
                "错误：",
                e
            )

            failed_files += 1

    # ========================================================
    # 最终统计
    # ========================================================

    print()

    print(
        "=" * 70
    )

    print(
        "RAG V5.1 入库完成"
    )

    print(
        "=" * 70
    )

    print()

    print(
        "处理文件数：",
        len(files)
    )

    print(
        "成功文件数：",
        success_files
    )

    print(
        "失败文件数：",
        failed_files
    )

    print(
        "本次处理条款：",
        total
    )

    print()

    print(
        "=" * 70
    )


# ============================================================
# Notebook / Terminal
# ============================================================

if __name__ == "__main__":

    ingest()