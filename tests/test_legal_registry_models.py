import json
import uuid

import pytest

from src.legal_registry_models import (
    Law,
    LawVersion,
    LawVersionSource,
    LegalArticle,
    LegalArticleSource,
    SourceLocation,
    ArticleLocation,
)


LAW_ID = "11111111-1111-4111-8111-111111111111"
VERSION_ID = "22222222-2222-4222-8222-222222222222"
SOURCE_ID = "33333333-3333-4333-8333-333333333333"
ARTICLE_ID = "44444444-4444-4444-8444-444444444444"
ARTICLE_SOURCE_ID = "55555555-5555-4555-8555-555555555555"


def test_law_creation():
    law = Law(
        law_id=LAW_ID,
        law_name="中华人民共和国劳动合同法",
        law_type="LAW",
        issuing_authority="全国人民代表大会常务委员会",
        aliases=["劳动合同法"],
    )

    assert law.law_name == "中华人民共和国劳动合同法"
    assert law.aliases == ["劳动合同法"]


def test_law_rejects_invalid_uuid():
    with pytest.raises(ValueError):
        Law(
            law_id="invalid",
            law_name="测试法律",
            law_type="LAW",
        )


def test_law_rejects_unknown_type():
    with pytest.raises(ValueError):
        Law(
            law_id=LAW_ID,
            law_name="测试法律",
            law_type="UNKNOWN_TYPE",
        )


def test_law_rejects_empty_name():
    with pytest.raises(ValueError):
        Law(
            law_id=LAW_ID,
            law_name=" ",
            law_type="LAW",
        )


def test_source_location_creation():
    location = SourceLocation(
        paragraph_start=10,
        paragraph_end=13,
        paragraph_numbers=(10, 11, 13),
    )

    assert location.paragraph_numbers == (10, 11, 13)


def test_source_location_accepts_list_and_freezes_as_tuple():
    location = SourceLocation(
        paragraph_start=10,
        paragraph_end=12,
        paragraph_numbers=[10, 12],
    )

    assert location.paragraph_numbers == (10, 12)


@pytest.mark.parametrize(
    "kwargs",
    [
        {
            "paragraph_start": 0,
            "paragraph_end": 1,
            "paragraph_numbers": (1,),
        },
        {
            "paragraph_start": 2,
            "paragraph_end": 1,
            "paragraph_numbers": (2,),
        },
        {
            "paragraph_start": 1,
            "paragraph_end": 3,
            "paragraph_numbers": (),
        },
        {
            "paragraph_start": 1,
            "paragraph_end": 3,
            "paragraph_numbers": (1, 1, 3),
        },
        {
            "paragraph_start": 1,
            "paragraph_end": 3,
            "paragraph_numbers": (2, 3),
        },
        {
            "paragraph_start": 1,
            "paragraph_end": 3,
            "paragraph_numbers": (1, 2),
        },
    ],
)
def test_source_location_rejects_invalid_structure(kwargs):
    with pytest.raises(ValueError):
        SourceLocation(**kwargs)


def test_article_location_creation():
    location = ArticleLocation(
        paragraph_number=2,
        item_number=1,
        subitem_number=3,
    )

    assert location.paragraph_number == 2
    assert location.item_number == 1
    assert location.subitem_number == 3


def test_article_location_allows_unspecified_position():
    location = ArticleLocation()

    assert location.paragraph_number is None
    assert location.item_number is None
    assert location.subitem_number is None


def test_article_location_rejects_subitem_without_item():
    with pytest.raises(ValueError):
        ArticleLocation(subitem_number=1)


def test_article_location_rejects_zero():
    with pytest.raises(ValueError):
        ArticleLocation(item_number=0)


def test_law_version_source_creation():
    source = LawVersionSource(
        source_id=SOURCE_ID,
        source_name="劳动合同法.docx",
        official_source_type="GOVERNMENT_OFFICIAL_TEXT",
        provenance_type="USER_CONFIRMED",
        source_hash="a" * 64,
    )

    assert source.source_name == "劳动合同法.docx"
    assert source.provenance_status == "UNVERIFIED"


def test_law_version_source_rejects_invalid_hash():
    with pytest.raises(ValueError):
        LawVersionSource(
            source_id=SOURCE_ID,
            source_name="劳动合同法.docx",
            source_hash="invalid",
        )


def test_law_version_source_rejects_unknown_provenance():
    with pytest.raises(ValueError):
        LawVersionSource(
            source_id=SOURCE_ID,
            source_name="劳动合同法.docx",
            provenance_type="TRUSTED",
        )


def test_legal_article_source_creation():
    location = SourceLocation(
        paragraph_start=10,
        paragraph_end=11,
        paragraph_numbers=(10, 11),
    )

    source = LegalArticleSource(
        article_source_id=ARTICLE_SOURCE_ID,
        article_id=ARTICLE_ID,
        source_id=SOURCE_ID,
        locations=[location],
    )

    assert len(source.locations) == 1


def test_legal_article_source_requires_location():
    with pytest.raises(ValueError):
        LegalArticleSource(
            article_source_id=ARTICLE_SOURCE_ID,
            article_id=ARTICLE_ID,
            source_id=SOURCE_ID,
        )


def test_legal_article_normalizes_article_number():
    article = LegalArticle(
        article_id=ARTICLE_ID,
        article_number="第14条",
    )

    assert article.article_number == "第十四条"


def test_legal_article_rejects_invalid_article_number():
    with pytest.raises(ValueError):
        LegalArticle(
            article_id=ARTICLE_ID,
            article_number="第十四条第一款",
        )


def test_legal_article_rejects_invalid_hash():
    with pytest.raises(ValueError):
        LegalArticle(
            article_id=ARTICLE_ID,
            article_number="第十四条",
            article_text_hash="bad-hash",
        )


def test_law_version_creation():
    version = LawVersion(
        version_id=VERSION_ID,
        law_id=LAW_ID,
        version_key="2012-12-28-amended-text",
        version_label="2012年修正文本",
        promulgation_date="2012-12-28",
        effective_date="2013-07-01",
    )

    assert version.verification_status == "UNVERIFIED"
    assert version.validity_status == "UNKNOWN"
    assert version.expiry_date is None


def test_law_version_rejects_invalid_date():
    with pytest.raises(ValueError):
        LawVersion(
            version_id=VERSION_ID,
            law_id=LAW_ID,
            version_key="test",
            version_label="测试版本",
            effective_date="2013-99-99",
        )


def test_law_version_rejects_invalid_date_range():
    with pytest.raises(ValueError):
        LawVersion(
            version_id=VERSION_ID,
            law_id=LAW_ID,
            version_key="test",
            version_label="测试版本",
            effective_date="2013-07-01",
            expiry_date="2013-07-01",
        )


def test_law_version_rejects_unknown_status():
    with pytest.raises(ValueError):
        LawVersion(
            version_id=VERSION_ID,
            law_id=LAW_ID,
            version_key="test",
            version_label="测试版本",
            validity_status="CURRENT",
        )


def test_nested_model_serialization():
    location = SourceLocation(
        paragraph_start=10,
        paragraph_end=11,
        paragraph_numbers=(10, 11),
    )

    article_source = LegalArticleSource(
        article_source_id=ARTICLE_SOURCE_ID,
        article_id=ARTICLE_ID,
        source_id=SOURCE_ID,
        locations=[location],
    )

    article = LegalArticle(
        article_id=ARTICLE_ID,
        article_number="第14条",
        sources=[article_source],
    )

    source = LawVersionSource(
        source_id=SOURCE_ID,
        source_name="劳动合同法.docx",
    )

    version = LawVersion(
        version_id=VERSION_ID,
        law_id=LAW_ID,
        version_key="2012-12-28-amended-text",
        version_label="2012年修正文本",
        sources=[source],
        articles=[article],
    )

    result = version.to_dict()

    assert result["articles"][0]["article_number"] == "第十四条"
    assert result["articles"][0]["sources"][0]["locations"][0][
        "paragraph_numbers"
    ] == [10, 11]

    # 验证整个结构可以被标准 JSON 序列化
    encoded = json.dumps(
        result,
        ensure_ascii=False,
    )

    decoded = json.loads(encoded)

    assert decoded["version_id"] == VERSION_ID
    assert len(decoded["articles"]) == 1
    assert len(decoded["sources"]) == 1


def test_source_location_is_immutable():
    location = SourceLocation(
        paragraph_start=1,
        paragraph_end=1,
        paragraph_numbers=(1,),
    )

    with pytest.raises(Exception):
        location.paragraph_start = 2


def test_article_location_is_immutable():
    location = ArticleLocation(item_number=1)

    with pytest.raises(Exception):
        location.item_number = 2
