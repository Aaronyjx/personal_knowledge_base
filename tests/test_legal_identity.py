import uuid
import pytest

from src.legal_identity import (
    ARTICLE_NAMESPACE,
    InvalidArticleNumberError,
    normalize_article_number,
    build_article_id,
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
