import json
import uuid

import pytest

from src.legal_identity import build_article_id

from src.legal_registry_models import (
    Law,
    LawVersion,
    LawVersionSource,
    LegalArticle,
    LegalArticleSource,
    SourceLocation,
)

from src.legal_registry_store import (
    SCHEMA_VERSION,
    load_registry,
    registry_transaction,
    validate_registry,
)


LAW_ID = "11111111-1111-4111-8111-111111111111"
VERSION_ID = "22222222-2222-4222-8222-222222222222"
SOURCE_ID = "33333333-3333-4333-8333-333333333333"


def make_law():
    return Law(
        law_id=LAW_ID,
        law_name="中华人民共和国劳动合同法",
        law_type="LAW",
    )


def make_source():
    return LawVersionSource(
        source_id=SOURCE_ID,
        source_name="劳动合同法.docx",
    )


def make_article(article_number="第十四条"):
    article_id = build_article_id(
        VERSION_ID,
        article_number,
    )

    return LegalArticle(
        article_id=article_id,
        article_number=article_number,
    )


def make_version():
    return LawVersion(
        version_id=VERSION_ID,
        law_id=LAW_ID,
        version_key="2012-12-28-amended-text",
        version_label="2012年修正文本",
        sources=[make_source()],
        articles=[make_article()],
    )


def add_initial_data(registry):
    registry["laws"].append(make_law())
    registry["law_versions"].append(make_version())


def test_load_missing_file_returns_empty_registry(tmp_path):
    path = tmp_path / "registry.json"

    registry = load_registry(path)

    assert registry["schema_version"] == SCHEMA_VERSION
    assert registry["laws"] == []
    assert registry["law_versions"] == []
    assert not path.exists()


def test_transaction_creates_registry_file(tmp_path):
    path = tmp_path / "registry.json"

    result = registry_transaction(
        add_initial_data,
        path=path,
    )

    assert path.exists()
    assert len(result["laws"]) == 1
    assert len(result["law_versions"]) == 1

    raw = json.loads(path.read_text(encoding="utf-8"))

    assert raw["schema_version"] == SCHEMA_VERSION
    assert len(raw["laws"]) == 1


def test_load_registry_deserializes_nested_models(tmp_path):
    path = tmp_path / "registry.json"

    registry_transaction(
        add_initial_data,
        path=path,
    )

    loaded = load_registry(path)

    assert isinstance(loaded["laws"][0], Law)
    assert isinstance(loaded["law_versions"][0], LawVersion)
    assert isinstance(
        loaded["law_versions"][0].sources[0],
        LawVersionSource,
    )
    assert isinstance(
        loaded["law_versions"][0].articles[0],
        LegalArticle,
    )


def test_transaction_creates_backup_before_second_commit(tmp_path):
    path = tmp_path / "registry.json"

    registry_transaction(
        add_initial_data,
        path=path,
    )

    def update(registry):
        registry["laws"][0].aliases.append("劳动合同法")

    registry_transaction(
        update,
        path=path,
    )

    backups = list(
        tmp_path.glob("registry.json.bak_*")
    )

    assert len(backups) == 1

    backup_data = json.loads(
        backups[0].read_text(encoding="utf-8")
    )

    assert backup_data["laws"][0]["aliases"] == []


def test_mutator_failure_does_not_commit(tmp_path):
    path = tmp_path / "registry.json"

    registry_transaction(
        add_initial_data,
        path=path,
    )

    before = path.read_bytes()

    def broken_mutator(registry):
        registry["laws"].clear()
        raise RuntimeError("模拟事务失败")

    with pytest.raises(RuntimeError):
        registry_transaction(
            broken_mutator,
            path=path,
        )

    assert path.read_bytes() == before


def test_validation_failure_does_not_commit(tmp_path):
    path = tmp_path / "registry.json"

    registry_transaction(
        add_initial_data,
        path=path,
    )

    before = path.read_bytes()

    def invalid_mutator(registry):
        registry["law_versions"][0].law_id = (
            "99999999-9999-4999-8999-999999999999"
        )

    with pytest.raises(ValueError):
        registry_transaction(
            invalid_mutator,
            path=path,
        )

    assert path.read_bytes() == before


def test_duplicate_law_id_is_rejected():
    registry = {
        "schema_version": SCHEMA_VERSION,
        "updated_at": None,
        "laws": [
            make_law(),
            make_law(),
        ],
        "law_versions": [],
    }

    with pytest.raises(ValueError, match="Law ID 重复"):
        validate_registry(registry)


def test_version_must_reference_existing_law():
    version = make_version()
    version.law_id = "99999999-9999-4999-8999-999999999999"

    registry = {
        "schema_version": SCHEMA_VERSION,
        "updated_at": None,
        "laws": [make_law()],
        "law_versions": [version],
    }

    with pytest.raises(ValueError, match="不存在的 Law"):
        validate_registry(registry)


def test_version_key_must_be_unique_within_law():
    first = make_version()

    second = LawVersion(
        version_id="66666666-6666-4666-8666-666666666666",
        law_id=LAW_ID,
        version_key=first.version_key,
        version_label="另一个标签",
    )

    registry = {
        "schema_version": SCHEMA_VERSION,
        "updated_at": None,
        "laws": [make_law()],
        "law_versions": [first, second],
    }

    with pytest.raises(ValueError, match="version_key 重复"):
        validate_registry(registry)


def test_article_id_must_match_version_and_number():
    article = make_article()
    article.article_id = str(uuid.uuid4())

    version = make_version()
    version.articles = [article]

    registry = {
        "schema_version": SCHEMA_VERSION,
        "updated_at": None,
        "laws": [make_law()],
        "law_versions": [version],
    }

    with pytest.raises(ValueError, match="article_id"):
        validate_registry(registry)


def test_duplicate_article_number_in_same_version_is_rejected():
    version = make_version()

    second_id = build_article_id(
        VERSION_ID,
        "第十四条",
    )

    version.articles.append(
        LegalArticle(
            article_id=second_id,
            article_number="第14条",
        )
    )

    registry = {
        "schema_version": SCHEMA_VERSION,
        "updated_at": None,
        "laws": [make_law()],
        "law_versions": [version],
    }

    with pytest.raises(ValueError, match="编号重复"):
        validate_registry(registry)


def test_article_source_must_reference_source_in_same_version():
    version = make_version()

    article = version.articles[0]

    location = SourceLocation(
        paragraph_start=10,
        paragraph_end=10,
        paragraph_numbers=(10,),
    )

    article.sources.append(
        LegalArticleSource(
            article_source_id=str(uuid.uuid4()),
            article_id=article.article_id,
            source_id="77777777-7777-4777-8777-777777777777",
            locations=[location],
        )
    )

    registry = {
        "schema_version": SCHEMA_VERSION,
        "updated_at": None,
        "laws": [make_law()],
        "law_versions": [version],
    }

    with pytest.raises(ValueError, match="不属于当前版本"):
        validate_registry(registry)


def test_article_source_article_id_must_match_parent():
    version = make_version()

    article = version.articles[0]

    location = SourceLocation(
        paragraph_start=10,
        paragraph_end=10,
        paragraph_numbers=(10,),
    )

    article.sources.append(
        LegalArticleSource(
            article_source_id=str(uuid.uuid4()),
            article_id=str(uuid.uuid4()),
            source_id=SOURCE_ID,
            locations=[location],
        )
    )

    registry = {
        "schema_version": SCHEMA_VERSION,
        "updated_at": None,
        "laws": [make_law()],
        "law_versions": [version],
    }

    with pytest.raises(ValueError, match="所属法条不一致"):
        validate_registry(registry)


def test_article_source_id_must_be_globally_unique():
    version = make_version()

    first_article = version.articles[0]

    second_article_id = build_article_id(
        VERSION_ID,
        "第十五条",
    )

    second_article = LegalArticle(
        article_id=second_article_id,
        article_number="第十五条",
    )

    location = SourceLocation(
        paragraph_start=10,
        paragraph_end=10,
        paragraph_numbers=(10,),
    )

    duplicated_article_source_id = (
        "99999999-9999-4999-8999-999999999999"
    )

    first_article.sources.append(
        LegalArticleSource(
            article_source_id=duplicated_article_source_id,
            article_id=first_article.article_id,
            source_id=SOURCE_ID,
            locations=[location],
        )
    )

    second_article.sources.append(
        LegalArticleSource(
            article_source_id=duplicated_article_source_id,
            article_id=second_article.article_id,
            source_id=SOURCE_ID,
            locations=[location],
        )
    )

    version.articles.append(second_article)

    registry = {
        "schema_version": SCHEMA_VERSION,
        "updated_at": None,
        "laws": [make_law()],
        "law_versions": [version],
    }

    with pytest.raises(
        ValueError,
        match="article_source_id 全局重复",
    ):
        validate_registry(registry)


def test_corrupted_json_is_rejected(tmp_path):
    path = tmp_path / "registry.json"
    path.write_text("{invalid", encoding="utf-8")

    with pytest.raises(ValueError, match="JSON 格式错误"):
        load_registry(path)


def test_unknown_schema_version_is_rejected(tmp_path):
    path = tmp_path / "registry.json"

    path.write_text(
        json.dumps({
            "schema_version": "99.0",
            "updated_at": None,
            "laws": [],
            "law_versions": [],
        }),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="不支持的注册表"):
        load_registry(path)


def test_unknown_top_level_field_is_rejected(tmp_path):
    path = tmp_path / "registry.json"

    path.write_text(
        json.dumps({
            "schema_version": SCHEMA_VERSION,
            "updated_at": None,
            "laws": [],
            "law_versions": [],
            "extra": True,
        }),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="顶层字段不正确"):
        load_registry(path)


def test_transaction_returns_independent_copy(tmp_path):
    path = tmp_path / "registry.json"

    result = registry_transaction(
        add_initial_data,
        path=path,
    )

    result["laws"].clear()

    loaded = load_registry(path)

    assert len(loaded["laws"]) == 1


def test_transaction_lock_file_is_created(tmp_path):
    path = tmp_path / "registry.json"

    registry_transaction(
        add_initial_data,
        path=path,
    )

    lock_path = path.with_name(
        path.name + ".lock"
    )

    assert lock_path.exists()


def test_failed_mutator_does_not_create_registry_file(tmp_path):
    path = tmp_path / "registry.json"

    def broken(registry):
        raise RuntimeError("停止")

    with pytest.raises(RuntimeError):
        registry_transaction(
            broken,
            path=path,
        )

    assert not path.exists()


def test_multiple_transactions_preserve_previous_updates(tmp_path):
    path = tmp_path / "registry.json"

    registry_transaction(
        add_initial_data,
        path=path,
    )

    def add_alias(registry):
        registry["laws"][0].aliases.append("劳动合同法")

    def add_second_law(registry):
        registry["laws"].append(
            Law(
                law_id="88888888-8888-4888-8888-888888888888",
                law_name="中华人民共和国劳动法",
                law_type="LAW",
            )
        )

    registry_transaction(add_alias, path=path)
    registry_transaction(add_second_law, path=path)

    loaded = load_registry(path)

    assert loaded["laws"][0].aliases == ["劳动合同法"]
    assert len(loaded["laws"]) == 2
