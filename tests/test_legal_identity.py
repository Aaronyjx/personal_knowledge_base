import uuid
import pytest

from src.legal_identity import (
    ARTICLE_NAMESPACE,
    LAW_NAMESPACE,
    VERSION_NAMESPACE,
    SOURCE_NAMESPACE,
    ARTICLE_SOURCE_NAMESPACE,
    InvalidArticleNumberError,
    normalize_article_number,
    build_article_id,
    build_law_id,
    build_version_id,
    normalize_official_source_url,
    build_source_id,
    build_article_source_id,
    _build_identity_uuid,
)


VERSION_A = "11111111-1111-4111-8111-111111111111"
VERSION_B = "22222222-2222-4222-8222-222222222222"


# ============================================================
# 1. 中文数字规范化
# ============================================================

@pytest.mark.parametrize(
    "source, expected",
    [
        ("第一条", "第一条"),
        ("第十条", "第十条"),
        ("第十一条", "第十一条"),
        ("第十四条", "第十四条"),
        ("第二十条", "第二十条"),
        ("第一百条", "第一百条"),
        ("第一百零七条", "第一百零七条"),
        ("第两百条", "第二百条"),
        ("第一千条", "第一千条"),
        ("第一万零一条", "第一万零一条"),
    ],
)
def test_normalize_chinese_article_numbers(source, expected):
    assert normalize_article_number(source) == expected


# ============================================================
# 2. 阿拉伯数字规范化
# ============================================================

@pytest.mark.parametrize(
    "source, expected",
    [
        ("第1条", "第一条"),
        ("第10条", "第十条"),
        ("第14条", "第十四条"),
        ("第20条", "第二十条"),
        ("第100条", "第一百条"),
        ("第107条", "第一百零七条"),
        ("第1000条", "第一千条"),
        ("第10001条", "第一万零一条"),
    ],
)
def test_normalize_arabic_article_numbers(source, expected):
    assert normalize_article_number(source) == expected


# ============================================================
# 3. 空格和全角字符
# ============================================================

@pytest.mark.parametrize(
    "source, expected",
    [
        ("第 14 条", "第十四条"),
        ("第14 条", "第十四条"),
        ("第 14条", "第十四条"),
        ("第１４条", "第十四条"),
    ],
)
def test_normalize_spaces_and_fullwidth_digits(source, expected):
    assert normalize_article_number(source) == expected


# ============================================================
# 4. 附加条号
# ============================================================

@pytest.mark.parametrize(
    "source, expected",
    [
        ("第十四条之一", "第十四条之一"),
        ("第14条之1", "第十四条之一"),
        ("第十四条之二", "第十四条之二"),
        ("第14条之2", "第十四条之二"),
        ("第十四条之十", "第十四条之十"),
        ("第十四条之二十一", "第十四条之二十一"),
    ],
)
def test_normalize_supplementary_article_numbers(source, expected):
    assert normalize_article_number(source) == expected


def test_supplementary_article_is_not_main_article():
    assert normalize_article_number("第十四条之一") != (
        normalize_article_number("第十四条")
    )


# ============================================================
# 5. 非法输入必须抛出异常
# ============================================================

@pytest.mark.parametrize(
    "source",
    [
        "",
        " ",
        "第零条",
        "第0条",
        "第-1条",
        "第十四条第一款",
        "第十四条第一项",
        "第十四条之一第一项",
        "第十四",
        "十四条",
        "第ABC条",
        "第十四条之零",
        "第十四条之",
        "第十四条之一二",
        "第一二条",
        "第百条",
        "第十十条",
        "第十四条附注",
    ],
)
def test_invalid_article_numbers_raise_error(source):
    with pytest.raises(InvalidArticleNumberError):
        normalize_article_number(source)


def test_non_string_article_number_raises_error():
    with pytest.raises(InvalidArticleNumberError):
        normalize_article_number(14)


# ============================================================
# 6. article_id 确定性
# ============================================================

def test_same_version_and_same_article_have_same_id():
    first = build_article_id(VERSION_A, "第十四条")
    second = build_article_id(VERSION_A, "第14条")

    assert first == second


def test_different_versions_have_different_article_ids():
    first = build_article_id(VERSION_A, "第十四条")
    second = build_article_id(VERSION_B, "第十四条")

    assert first != second


def test_supplementary_article_has_different_id():
    main_id = build_article_id(VERSION_A, "第十四条")
    supplementary_id = build_article_id(VERSION_A, "第十四条之一")

    assert main_id != supplementary_id


def test_article_id_is_valid_uuid():
    result = build_article_id(VERSION_A, "第十四条")

    parsed = uuid.UUID(result)

    assert str(parsed) == result
    assert parsed.version == 5


def test_article_namespace_is_fixed_uuid():
    assert isinstance(ARTICLE_NAMESPACE, uuid.UUID)


# ============================================================
# 7. version_id 校验
# ============================================================

@pytest.mark.parametrize(
    "version_id",
    [
        "",
        "not-a-uuid",
        "12345",
        None,
    ],
)
def test_invalid_version_id_raises_error(version_id):
    with pytest.raises(ValueError):
        build_article_id(version_id, "第十四条")


# ============================================================
# 8. Canonical Registry V2：固定 Namespace
# ============================================================

def test_v2_identity_namespaces_are_fixed():
    assert str(LAW_NAMESPACE) == (
        "0e6d1b4a-72c8-5f31-9a40-2b7e6d8c1f53"
    )

    assert str(VERSION_NAMESPACE) == (
        "1f7c2a90-8b43-5d61-ae20-3c9f7b5d1a64"
    )

    assert str(SOURCE_NAMESPACE) == (
        "2a8e3c51-9d74-5f20-b136-4e0a8c6d2f75"
    )

    assert str(ARTICLE_SOURCE_NAMESPACE) == (
        "3b9f4d62-ae85-5c31-c247-5f1b9d7e3a86"
    )

    assert ARTICLE_NAMESPACE != LAW_NAMESPACE
    assert ARTICLE_NAMESPACE != VERSION_NAMESPACE
    assert ARTICLE_NAMESPACE != SOURCE_NAMESPACE
    assert ARTICLE_NAMESPACE != ARTICLE_SOURCE_NAMESPACE


# ============================================================
# 9. Canonical Registry V2：规范 JSON
# ============================================================

def test_identity_json_key_order_does_not_change_uuid():
    first = {
        "jurisdiction": "CN",
        "canonical_law_name": "中华人民共和国劳动合同法",
    }

    second = {
        "canonical_law_name": "中华人民共和国劳动合同法",
        "jurisdiction": "CN",
    }

    assert _build_identity_uuid(
        LAW_NAMESPACE,
        first,
    ) == _build_identity_uuid(
        LAW_NAMESPACE,
        second,
    )


def test_identity_json_is_unicode_preserving():
    identity = {
        "name": "中华人民共和国劳动合同法",
    }

    result = _build_identity_uuid(
        LAW_NAMESPACE,
        identity,
    )

    assert result == (
        "4fffbdd2-3149-5003-a75b-cf3701cec420"
    )


# ============================================================
# 10. Canonical Registry V2：Law ID
# ============================================================

def test_v2_law_id_is_deterministic():
    first = build_law_id(
        "CN",
        "中华人民共和国劳动合同法",
    )

    second = build_law_id(
        "CN",
        "中华人民共和国劳动合同法",
    )

    assert first == second
    assert uuid.UUID(first).version == 5


def test_v2_law_id_has_fixed_regression_value():
    result = build_law_id(
        "CN",
        "中华人民共和国劳动合同法",
    )

    assert result == "6669a5a0-a176-554d-bf34-3eda799c6309"


def test_v2_law_name_nfkc_and_whitespace_normalization():
    first = build_law_id(
        "CN",
        "中华人民共和国劳动合同法",
    )

    second = build_law_id(
        "CN",
        "  中华人民共和国劳动合同法  ",
    )

    third = build_law_id(
        "CN",
        "中华人民共和国劳动合同法",
    )

    assert first == second == third


def test_v2_jurisdiction_fullwidth_characters_are_normalized():
    first = build_law_id(
        "CN",
        "劳动合同法",
    )

    second = build_law_id(
        "ＣＮ",
        "劳动合同法",
    )

    assert first == second


def test_v2_law_name_fullwidth_characters_are_normalized():
    first = build_law_id(
        "CN",
        "劳动合同法（2025年）",
    )

    second = build_law_id(
        "CN",
        "劳动合同法(2025年)",
    )

    assert first == second


def test_v2_law_id_differs_by_jurisdiction():
    first = build_law_id(
        "CN",
        "劳动合同法",
    )

    second = build_law_id(
        "HK",
        "劳动合同法",
    )

    assert first != second


def test_v2_law_id_differs_by_law_name():
    first = build_law_id(
        "CN",
        "劳动合同法",
    )

    second = build_law_id(
        "CN",
        "劳动法",
    )

    assert first != second


@pytest.mark.parametrize(
    "jurisdiction, law_name",
    [
        ("", "劳动合同法"),
        (" ", "劳动合同法"),
        ("CN", ""),
        ("CN", "   "),
        (None, "劳动合同法"),
        ("CN", None),
        (123, "劳动合同法"),
        ("CN", 123),
    ],
)
def test_v2_law_id_rejects_invalid_inputs(jurisdiction, law_name):
    with pytest.raises(ValueError):
        build_law_id(jurisdiction, law_name)


# ============================================================
# 11. Canonical Registry V2：Version ID
# ============================================================

LAW_ID_A = "6669a5a0-a176-554d-bf34-3eda799c6309"
LAW_ID_B = "77777777-7777-4777-8777-777777777777"


def test_v2_version_id_is_deterministic():
    first = build_version_id(
        LAW_ID_A,
        "2025-01-01",
    )

    second = build_version_id(
        LAW_ID_A,
        "2025-01-01",
    )

    assert first == second
    assert uuid.UUID(first).version == 5


def test_v2_version_id_has_fixed_regression_value():
    result = build_version_id(
        LAW_ID_A,
        "2025-01-01",
    )

    assert result == "0c8c8ef2-697b-5b62-81c2-be18d3a59d3b"


def test_v2_version_id_differs_by_law():
    first = build_version_id(
        LAW_ID_A,
        "2025-01-01",
    )

    second = build_version_id(
        LAW_ID_B,
        "2025-01-01",
    )

    assert first != second


def test_v2_version_id_differs_by_version_key():
    first = build_version_id(
        LAW_ID_A,
        "2025-01-01",
    )

    second = build_version_id(
        LAW_ID_A,
        "2026-01-01",
    )

    assert first != second


def test_v2_version_id_normalizes_uuid_format():
    first = build_version_id(
        LAW_ID_A,
        "2025-01-01",
    )

    second = build_version_id(
        LAW_ID_A.upper(),
        "2025-01-01",
    )

    assert first == second


@pytest.mark.parametrize(
    "law_id, version_key",
    [
        ("invalid", "2025-01-01"),
        ("", "2025-01-01"),
        (None, "2025-01-01"),
        (LAW_ID_A, ""),
        (LAW_ID_A, "   "),
        (LAW_ID_A, None),
        (LAW_ID_A, 123),
    ],
)
def test_v2_version_id_rejects_invalid_inputs(law_id, version_key):
    with pytest.raises(ValueError):
        build_version_id(law_id, version_key)


# ============================================================
# 12. Canonical Registry V2：官方来源 URL
# ============================================================

def test_source_url_normalizes_scheme_and_hostname():
    result = normalize_official_source_url(
        "HTTPS://FLK.NPC.GOV.CN/law"
    )

    assert result == "https://flk.npc.gov.cn/law"


def test_source_url_removes_default_https_port():
    result = normalize_official_source_url(
        "https://flk.npc.gov.cn:443/law"
    )

    assert result == "https://flk.npc.gov.cn/law"


def test_source_url_removes_default_http_port():
    result = normalize_official_source_url(
        "http://example.com:80/law"
    )

    assert result == "http://example.com/law"


def test_source_url_preserves_non_default_port():
    result = normalize_official_source_url(
        "https://example.com:8443/law"
    )

    assert result == "https://example.com:8443/law"


def test_source_url_removes_fragment():
    result = normalize_official_source_url(
        "https://example.com/law#section-1"
    )

    assert result == "https://example.com/law"


def test_source_url_preserves_path_exactly():
    source_url = (
        "https://example.com/Legal%20Files/"
        "Law%2FVersion.DOCX"
    )

    assert normalize_official_source_url(source_url) == source_url


def test_source_url_preserves_query_parameter_order():
    first = normalize_official_source_url(
        "https://example.com/law?a=1&b=2"
    )

    second = normalize_official_source_url(
        "https://example.com/law?b=2&a=1"
    )

    assert first == "https://example.com/law?a=1&b=2"
    assert second == "https://example.com/law?b=2&a=1"
    assert first != second


def test_source_url_preserves_ipv6_host():
    result = normalize_official_source_url(
        "https://[2001:DB8::1]:443/law"
    )

    assert result == "https://[2001:db8::1]/law"


@pytest.mark.parametrize(
    "source_url",
    [
        "",
        " ",
        "ftp://example.com/law",
        "file:///tmp/law.docx",
        "https:///law",
        "https://",
        "https://user@example.com/law",
        "https://user:password@example.com/law",
        "https://example.com:abc/law",
        "https://example.com:99999/law",
        "https://example.com:/law",
        "https://example.com/law with spaces",
        "https://example.com/law\n",
        None,
        123,
    ],
)
def test_source_url_rejects_invalid_urls(source_url):
    with pytest.raises(ValueError):
        normalize_official_source_url(source_url)


def test_source_url_strips_leading_and_trailing_whitespace():
    result = normalize_official_source_url(
        "  HTTPS://EXAMPLE.COM/law  "
    )

    assert result == "https://example.com/law"


# ============================================================
# 13. Canonical Registry V2：Source ID
# ============================================================

SOURCE_HASH_A = "a" * 64
SOURCE_URL_A = (
    "https://flk.npc.gov.cn/detail.html"
    "?lawId=1&query=a"
)


def test_v2_source_id_is_deterministic():
    first = build_source_id(
        SOURCE_URL_A,
        SOURCE_HASH_A,
    )

    second = build_source_id(
        SOURCE_URL_A,
        SOURCE_HASH_A,
    )

    assert first == second
    assert uuid.UUID(first).version == 5


def test_v2_source_id_has_fixed_regression_value():
    result = build_source_id(
        SOURCE_URL_A,
        SOURCE_HASH_A,
    )

    assert result == "3620eb58-efe5-5bb9-838c-2c0ad3140d38"


def test_v2_source_id_normalizes_url_before_generation():
    first = build_source_id(
        "HTTPS://FLK.NPC.GOV.CN:443/detail.html?lawId=1#top",
        SOURCE_HASH_A,
    )

    second = build_source_id(
        "https://flk.npc.gov.cn/detail.html?lawId=1",
        SOURCE_HASH_A,
    )

    assert first == second


def test_v2_source_id_normalizes_sha256_case():
    first = build_source_id(
        SOURCE_URL_A,
        "A" * 64,
    )

    second = build_source_id(
        SOURCE_URL_A,
        "a" * 64,
    )

    assert first == second


def test_v2_source_id_differs_by_raw_file_hash():
    first = build_source_id(
        SOURCE_URL_A,
        "a" * 64,
    )

    second = build_source_id(
        SOURCE_URL_A,
        "b" * 64,
    )

    assert first != second


def test_v2_source_id_differs_by_query_order():
    first = build_source_id(
        "https://example.com/law?a=1&b=2",
        SOURCE_HASH_A,
    )

    second = build_source_id(
        "https://example.com/law?b=2&a=1",
        SOURCE_HASH_A,
    )

    assert first != second


@pytest.mark.parametrize(
    "source_hash",
    [
        "",
        "a" * 63,
        "a" * 65,
        "g" * 64,
        "a" * 63 + " ",
        None,
        123,
    ],
)
def test_v2_source_id_rejects_invalid_sha256(source_hash):
    with pytest.raises(ValueError):
        build_source_id(
            SOURCE_URL_A,
            source_hash,
        )


# ============================================================
# 14. Canonical Registry V2：ArticleSource ID
# ============================================================

ARTICLE_ID_A = "44a70e2f-489b-5128-bdf4-2904b0d2f75a"
ARTICLE_ID_B = "55555555-5555-4555-8555-555555555555"

SOURCE_ID_A = "3620eb58-efe5-5bb9-838c-2c0ad3140d38"
SOURCE_ID_B = "66666666-6666-4666-8666-666666666666"


def test_v2_article_source_id_is_deterministic():
    first = build_article_source_id(
        ARTICLE_ID_A,
        SOURCE_ID_A,
    )

    second = build_article_source_id(
        ARTICLE_ID_A,
        SOURCE_ID_A,
    )

    assert first == second
    assert uuid.UUID(first).version == 5


def test_v2_article_source_id_has_fixed_regression_value():
    result = build_article_source_id(
        ARTICLE_ID_A,
        SOURCE_ID_A,
    )

    assert result == "cc411d7b-eb48-5015-84fa-e16849124191"


def test_v2_article_source_id_differs_by_article():
    first = build_article_source_id(
        ARTICLE_ID_A,
        SOURCE_ID_A,
    )

    second = build_article_source_id(
        ARTICLE_ID_B,
        SOURCE_ID_A,
    )

    assert first != second


def test_v2_article_source_id_differs_by_source():
    first = build_article_source_id(
        ARTICLE_ID_A,
        SOURCE_ID_A,
    )

    second = build_article_source_id(
        ARTICLE_ID_A,
        SOURCE_ID_B,
    )

    assert first != second


@pytest.mark.parametrize(
    "article_id, source_id",
    [
        ("invalid", SOURCE_ID_A),
        ("", SOURCE_ID_A),
        (None, SOURCE_ID_A),
        (ARTICLE_ID_A, "invalid"),
        (ARTICLE_ID_A, ""),
        (ARTICLE_ID_A, None),
    ],
)
def test_v2_article_source_id_rejects_invalid_inputs(
    article_id,
    source_id,
):
    with pytest.raises(ValueError):
        build_article_source_id(
            article_id,
            source_id,
        )


# ============================================================
# 15. 原 Article ID 固定身份回归
# ============================================================

def test_existing_article_id_fixed_regression_value():
    result = build_article_id(
        VERSION_A,
        "第十四条",
    )

    assert result == "44a70e2f-489b-5128-bdf4-2904b0d2f75a"

    assert str(ARTICLE_NAMESPACE) == (
        "b6d7e8f1-2a3c-4d5e-8f90-1a2b3c4d5e6f"
    )


# ============================================================
# 16. Canonical Registry V2：URL 边界测试
# ============================================================

def test_source_url_preserves_ipv6_non_default_port():
    result = normalize_official_source_url(
        "https://[2001:DB8::1]:8443/law"
    )

    assert result == "https://[2001:db8::1]:8443/law"


def test_source_url_preserves_encoded_path_and_query_order():
    source_url = (
        "HTTPS://EXAMPLE.COM/Legal%20Files/"
        "Law%2FVersion.DOCX?b=2&a=1"
    )

    result = normalize_official_source_url(source_url)

    assert result == (
        "https://example.com/Legal%20Files/"
        "Law%2FVersion.DOCX?b=2&a=1"
    )
