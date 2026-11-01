from pathlib import Path
from uuid import uuid4
from hashlib import sha256
import re

from docx import Document
from qdrant_client import QdrantClient

# 将项目根目录加入 Python 模块搜索路径。
# 这样直接运行 scripts/preview_legal_registry.py 时也能导入 src。
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.ingest import ARTICLE_PATTERN, clean_text
from src.legal_identity import normalize_article_number, build_article_id
from src.legal_registry_models import (
    Law,
    LawVersion,
    LawVersionSource,
    LegalArticle,
    LegalArticleSource,
    SourceLocation,
)
from src.legal_registry_store import validate_registry


ROOT = Path.cwd()
RAW_DIR = ROOT / "data" / "raw"

COLLECTION_NAME = "labor_dispute_legal_knowledge"
QDRANT_URL = "http://127.0.0.1:6333"

# 所有日期直接使用 ISO 字符串，符合模型接口要求。
LAW_CONFIGS = [
    {
        "law_name": "中华人民共和国劳动争议调解仲裁法",
        "law_type": "LAW",
        "issuing_authority": "全国人民代表大会常务委员会",
        "filename": "中华人民共和国劳动争议调解仲裁法_20071229.docx",
        "expected_hash": "9bc113c9324fd4ba1b0569b8545e8e3e7b8022554a54eb6029616f38c2ff495c",
        "expected_articles": 54,
        "version_key": "2007-12-29-promulgated-text",
        "version_label": "2007年通过文本",
        "promulgation_date": "2007-12-29",
        "effective_date": "2008-05-01",
        "amendment_description": "2007年12月29日通过的文本",
        "official_source_url": (
            "https://flk.npc.gov.cn/detail?id=2c909fdd678bf17901678bf64f28039d"
            "&fileId=&type=&title="
            "%E4%B8%AD%E5%8D%8E%E4%BA%BA%E6%B0%91"
            "%E5%85%B1%E5%92%8C%E5%9B%BD%E5%8A%B3"
            "%E5%8A%A8%E4%BA%89%E8%AE%AE%E8%B0%83"
            "%E8%A7%A3%E4%BB%B2%E8%A3%81%E6%B3%95"
        ),
        "official_source_type": "NPC_DATABASE_RECORD",
    },
    {
        "law_name": "中华人民共和国劳动合同法",
        "law_type": "LAW",
        "issuing_authority": "全国人民代表大会常务委员会",
        "filename": "中华人民共和国劳动合同法_20121228.docx",
        "expected_hash": "ede08615cfea42f23c6650c852cd5a3a7641bd176c12b2d34428cce5822938dc",
        "expected_articles": 98,
        "version_key": "2012-12-28-amended-text",
        "version_label": "2012年修正文本",
        "promulgation_date": "2012-12-28",
        "effective_date": "2013-07-01",
        "amendment_description": (
            "根据2012年12月28日《关于修改"
            "〈中华人民共和国劳动合同法〉的决定》修正"
        ),
        "official_source_url": (
            "https://www.beijing.gov.cn/zhengce/zhengcefagui/"
            "qtwj/201307/t20130701_780700.html"
        ),
        "official_source_type": "GOVERNMENT_OFFICIAL_TEXT",
    },
    {
        "law_name": "中华人民共和国劳动合同法实施条例",
        "law_type": "ADMINISTRATIVE_REGULATION",
        "issuing_authority": "国务院",
        "filename": "中华人民共和国劳动合同法实施条例_20080918.docx",
        "expected_hash": "f0692e2df571fee2d799c6e391e3168837f40bb422c6696f55aeafd9b952aa9e",
        "expected_articles": 38,
        "version_key": "2008-09-18-promulgated-text",
        "version_label": "2008年公布文本",
        "promulgation_date": "2008-09-18",
        "effective_date": "2008-09-18",
        "amendment_description": "2008年9月18日国务院令第535号公布",
        "official_source_url": (
            "https://www.mofcom.gov.cn/zcfb/zgdwjjmywg/"
            "art/2008/art_a38af549771c4f998ffabc6221502ed4.html"
        ),
        "official_source_type": "GOVERNMENT_REPUBLICATION",
    },
    {
        "law_name": "中华人民共和国劳动法",
        "law_type": "LAW",
        "issuing_authority": "全国人民代表大会常务委员会",
        "filename": "中华人民共和国劳动法_20181229.docx",
        "expected_hash": "011cdbc0c80d1441e86340579a4f082c40eefb1b5dc204bc0127b3ef777b62a2",
        "expected_articles": 107,
        "version_key": "2018-12-29-second-amendment-text",
        "version_label": "2018年第二次修正文本",
        "promulgation_date": "2018-12-29",
        "effective_date": "2018-12-29",
        "amendment_description": (
            "1994年7月5日通过，2009年8月27日第一次修正，"
            "2018年12月29日第二次修正"
        ),
        "official_source_url": (
            "https://flk.npc.gov.cn/detail"
            "?id=ff8080816f135f46016f20f16ee11737"
        ),
        "official_source_type": "NPC_DATABASE_RECORD",
    },
]

STRUCTURE_PATTERN = re.compile(
    r"^第[零〇一二两三四五六七八九十百千万\d]+[章节]"
)


def sha256_file(path):
    digest = sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def get_article_header(text):
    match = ARTICLE_PATTERN.match(text)
    if not match:
        return None

    if "header" in match.groupdict():
        header = match.group("header")
    else:
        header = match.group(0)

    extension = re.match(
        r"之[零〇一二两三四五六七八九十百千万\d]+",
        text[len(header):],
    )
    if extension:
        header += extension.group(0)

    return normalize_article_number(header)


def extract_article_locations(document):
    articles = []
    current = None

    def finish_current():
        nonlocal current
        if current is None:
            return

        numbers = current["paragraph_numbers"]
        if not numbers:
            raise ValueError(
                f"法条没有有效正文段落：{current['article_number']}"
            )

        current["paragraph_start"] = numbers[0]
        current["paragraph_end"] = numbers[-1]
        articles.append(current)
        current = None

    for paragraph_number, paragraph in enumerate(
        document.paragraphs, start=1
    ):
        text = clean_text(paragraph.text or "")
        if not text:
            continue

        article_number = get_article_header(text)
        if article_number:
            finish_current()
            current = {
                "article_number": article_number,
                "paragraph_numbers": [paragraph_number],
            }
            continue

        if STRUCTURE_PATTERN.match(text):
            finish_current()
            continue

        if current is not None:
            current["paragraph_numbers"].append(paragraph_number)

    finish_current()
    return articles


def read_qdrant_articles():
    client = QdrantClient(url=QDRANT_URL)
    payloads = []
    offset = None

    while True:
        points, next_offset = client.scroll(
            collection_name=COLLECTION_NAME,
            limit=256,
            offset=offset,
            with_payload=True,
            with_vectors=False,
        )

        for point in points:
            if not point.payload:
                raise ValueError(f"Qdrant Point 缺少 Payload：{point.id}")
            payloads.append(point.payload)

        if next_offset is None:
            break
        offset = next_offset

    if len(payloads) != 297:
        raise ValueError(f"预期297条Qdrant记录，实际{len(payloads)}条")

    article_map = {}
    for payload in payloads:
        law_name = payload.get("law_name")
        article_number = payload.get("article_number")
        article_text = payload.get("article_text")

        if not law_name or not article_number:
            raise ValueError("Qdrant Payload 缺少法律名称或法条编号")
        if not isinstance(article_text, str) or not article_text:
            raise ValueError(f"法条正文为空：{law_name}/{article_number}")

        key = (law_name, normalize_article_number(article_number))
        if key in article_map:
            raise ValueError(f"Qdrant 法条重复：{key}")
        article_map[key] = article_text

    print("Qdrant Point 数量：", len(payloads))
    return article_map


def build_preview_registry():
    registry = {
        "schema_version": "1.0",
        "updated_at": None,
        "laws": [],
        "law_versions": [],
    }

    qdrant_articles = read_qdrant_articles()
    matched_keys = set()

    for config in LAW_CONFIGS:
        print("\n" + "-" * 72)
        print(config["law_name"])
        print("-" * 72)

        docx_path = RAW_DIR / config["filename"]
        if not docx_path.is_file():
            raise FileNotFoundError(f"DOCX 文件不存在：{docx_path}")

        source_hash = sha256_file(docx_path)
        if source_hash != config["expected_hash"]:
            raise ValueError(
                f"DOCX SHA256 不匹配：{config['filename']}\n"
                f"预期：{config['expected_hash']}\n"
                f"实际：{source_hash}"
            )

        document = Document(str(docx_path))
        locations = extract_article_locations(document)

        if len(locations) != config["expected_articles"]:
            raise ValueError(
                f"DOCX 法条数不匹配：{config['law_name']}，"
                f"预期 {config['expected_articles']}，实际 {len(locations)}"
            )

        law_id = str(uuid4())
        version_id = str(uuid4())
        source_id = str(uuid4())

        law = Law(
            law_id=law_id,
            law_name=config["law_name"],
            law_type=config["law_type"],
            issuing_authority=config["issuing_authority"],
            aliases=[],
        )
        registry["laws"].append(law)

        version_source = LawVersionSource(
            source_id=source_id,
            source_name=config["filename"],
            original_download_url=None,
            official_source_url=config["official_source_url"],
            official_source_type=config["official_source_type"],
            source_hash=source_hash,
            retrieved_at=None,
            record_located_at=None,
            provenance_type="USER_CONFIRMED",
            provenance_status="UNVERIFIED",
            content_match_status="UNVERIFIED",
            verification_note=(
                "用户确认文件来自国家法律法规数据库首页；"
                "SHA256 仅验证本地文件指纹，不代表官方真实性核验。"
            ),
        )

        articles = []
        seen_numbers = set()

        for record in locations:
            article_number = normalize_article_number(
                record["article_number"]
            )

            if article_number in seen_numbers:
                raise ValueError(
                    f"DOCX 条号重复：{config['law_name']} / {article_number}"
                )
            seen_numbers.add(article_number)

            key = (config["law_name"], article_number)
            if key not in qdrant_articles:
                raise ValueError(f"DOCX 法条未匹配到 Qdrant：{key}")

            matched_keys.add(key)
            article_text = qdrant_articles[key]
            article_text_hash = sha256(
                article_text.encode("utf-8")
            ).hexdigest()

            article_id = build_article_id(version_id, article_number)

            source_location = SourceLocation(
                paragraph_start=record["paragraph_start"],
                paragraph_end=record["paragraph_end"],
                paragraph_numbers=tuple(record["paragraph_numbers"]),
            )

            article_source = LegalArticleSource(
                article_source_id=str(uuid4()),
                article_id=article_id,
                source_id=source_id,
                locations=[source_location],
            )

            articles.append(
                LegalArticle(
                    article_id=article_id,
                    article_number=article_number,
                    article_text_hash=article_text_hash,
                    sources=[article_source],
                )
            )

        version = LawVersion(
            version_id=version_id,
            law_id=law_id,
            version_key=config["version_key"],
            version_label=config["version_label"],
            promulgation_date=config["promulgation_date"],
            effective_date=config["effective_date"],
            expiry_date=None,
            amendment_description=config["amendment_description"],
            sources=[version_source],
            articles=articles,
            verification_status="UNVERIFIED",
            verified_at=None,
            verification_note=None,
            validity_status="UNKNOWN",
            validity_checked_at=None,
            validity_note=None,
        )

        registry["law_versions"].append(version)

        print("DOCX 段落数：", len(document.paragraphs))
        print("法条数量：", len(articles))
        print("来源关联数量：", sum(len(a.sources) for a in articles))
        print("DOCX SHA256：匹配")

    missing = set(qdrant_articles) - matched_keys
    if missing:
        raise ValueError(f"存在未匹配的 Qdrant 法条：{sorted(missing)}")

    if len(matched_keys) != 297:
        raise ValueError(f"匹配数量不是297：{len(matched_keys)}")

    return registry


def main():
    print("=" * 72)
    print("开始构造法律注册表内存预览")
    print("=" * 72)

    registry = build_preview_registry()

    print("\n执行完整注册表结构校验……")
    validate_registry(registry)

    law_count = len(registry["laws"])
    version_count = len(registry["law_versions"])
    article_count = sum(len(v.articles) for v in registry["law_versions"])
    version_source_count = sum(
        len(v.sources) for v in registry["law_versions"]
    )
    article_source_count = sum(
        len(a.sources)
        for v in registry["law_versions"]
        for a in v.articles
    )
    location_count = sum(
        len(s.locations)
        for v in registry["law_versions"]
        for a in v.articles
        for s in a.sources
    )

    print("\n" + "=" * 72)
    print("法律注册数据构造结果")
    print("=" * 72)
    print("Law：", law_count)
    print("LawVersion：", version_count)
    print("LawVersionSource：", version_source_count)
    print("LegalArticle：", article_count)
    print("LegalArticleSource：", article_source_count)
    print("SourceLocation：", location_count)

    expected = (4, 4, 4, 297, 297, 297)
    actual = (
        law_count,
        version_count,
        version_source_count,
        article_count,
        article_source_count,
        location_count,
    )

    if actual != expected:
        raise ValueError(
            f"对象数量不符合预期：expected={expected}, actual={actual}"
        )

    print("\n只读内存构造验证通过。")
    print("没有写入 legal_registry.json。")
    print("没有修改 Qdrant。")


if __name__ == "__main__":
    main()
