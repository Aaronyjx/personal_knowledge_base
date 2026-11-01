"""
法律注册表读取接口测试。

测试数据来自正式初始化的 legal_registry.json。
所有测试均只读，不修改正式注册表。
"""

from copy import deepcopy

import pytest

import src.legal_registry as legal_registry


@pytest.fixture(scope="module")
def registry_data():
    """读取正式注册表作为测试数据。"""

    return legal_registry.load_registry()


@pytest.fixture
def isolated_registry(monkeypatch, registry_data):
    """为每个测试提供独立注册表副本。"""

    def fake_load_registry(path=None):
        return deepcopy(registry_data)

    monkeypatch.setattr(
        legal_registry,
        "load_registry",
        fake_load_registry,
    )

    return registry_data


def test_get_law_returns_matching_law(isolated_registry):
    law = isolated_registry["laws"][0]

    result = legal_registry.get_law(law.law_id)

    assert result.law_id == law.law_id
    assert result.law_name == law.law_name


def test_get_law_unknown_id_raises_key_error(isolated_registry):
    with pytest.raises(KeyError):
        legal_registry.get_law("missing-law-id")


def test_get_law_returns_independent_copy(isolated_registry):
    law = isolated_registry["laws"][0]

    result = legal_registry.get_law(law.law_id)

    result.law_name = "临时修改名称"

    original = legal_registry.get_law(law.law_id)

    assert original.law_name == law.law_name


def test_find_law_by_exact_name(isolated_registry):
    law = isolated_registry["laws"][0]

    results = legal_registry.find_law_by_name(
        law.law_name
    )

    assert len(results) == 1
    assert results[0].law_id == law.law_id


def test_find_law_by_name_ignores_outer_whitespace(
    isolated_registry,
):
    law = isolated_registry["laws"][0]

    results = legal_registry.find_law_by_name(
        f"  {law.law_name}  "
    )

    assert len(results) == 1
    assert results[0].law_id == law.law_id


def test_find_law_by_unknown_name_returns_empty_list(
    isolated_registry,
):
    results = legal_registry.find_law_by_name(
        "不存在的法律名称"
    )

    assert results == []


def test_get_law_version_returns_matching_version(
    isolated_registry,
):
    version = isolated_registry["law_versions"][0]

    result = legal_registry.get_law_version(
        version.version_id
    )

    assert result.version_id == version.version_id
    assert result.law_id == version.law_id


def test_get_law_version_unknown_id_raises_key_error(
    isolated_registry,
):
    with pytest.raises(KeyError):
        legal_registry.get_law_version(
            "missing-version-id"
        )


def test_find_article_by_normalized_number(
    isolated_registry,
):
    version = isolated_registry["law_versions"][0]
    article = version.articles[0]

    result = legal_registry.find_article(
        version.version_id,
        article.article_number,
    )

    assert result is not None
    assert result.article_id == article.article_id
    assert result.article_number == article.article_number


def test_find_article_returns_none_when_not_found(
    isolated_registry,
):
    version = isolated_registry["law_versions"][0]

    result = legal_registry.find_article(
        version.version_id,
        "第九十九万九千九百九十九条",
    )

    assert result is None


def test_find_article_requires_version_id(
    isolated_registry,
):
    with pytest.raises(ValueError):
        legal_registry.find_article(
            "",
            "第一条",
        )


def test_find_article_unknown_version_raises_key_error(
    isolated_registry,
):
    with pytest.raises(KeyError):
        legal_registry.find_article(
            "missing-version-id",
            "第一条",
        )


def test_find_article_returns_independent_copy(
    isolated_registry,
):
    version = isolated_registry["law_versions"][0]
    article = version.articles[0]

    result = legal_registry.find_article(
        version.version_id,
        article.article_number,
    )

    result.article_number = "临时修改"

    original = legal_registry.find_article(
        version.version_id,
        article.article_number,
    )

    assert original.article_number == article.article_number


def test_find_article_normalizes_arabic_article_number(
    isolated_registry,
):
    version = isolated_registry["law_versions"][0]
    article = version.articles[0]

    # 从规范中文条号中提取阿拉伯数字形式。
    from src.legal_identity import normalize_article_number

    normalized = normalize_article_number(
        article.article_number
    )

    assert normalized == article.article_number

    # 使用规范化结果再次查询，必须得到同一条法条。
    result = legal_registry.find_article(
        version.version_id,
        normalized,
    )

    assert result.article_id == article.article_id
