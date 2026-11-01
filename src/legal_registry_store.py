"""
法律注册表存储层。

职责：
1. 读取和反序列化法律注册表。
2. 校验注册表内部对象关系。
3. 通过跨进程文件锁执行事务。
4. 使用临时文件和 os.replace 原子提交。
5. 在提交前创建原文件备份。

注册表结构：
{
    "schema_version": "1.0",
    "updated_at": "...",
    "laws": [],
    "law_versions": []
}

不负责：
- 法律真实性核验
- 法律效力判断
- Qdrant 写入
- Canonical Rule 注册
"""

from copy import deepcopy
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import shutil
import tempfile
from typing import Callable
import uuid

from src.legal_identity import (
    build_article_id,
    normalize_article_number,
)

from src.legal_registry_models import (
    Law,
    LawVersion,
    LawVersionSource,
    LegalArticle,
    LegalArticleSource,
    SourceLocation,
)


SCHEMA_VERSION = "1.0"

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_REGISTRY_PATH = (
    PROJECT_ROOT
    / "data"
    / "legal_registry"
    / "legal_registry.json"
)


# ============================================================
# 1. 空注册表
# ============================================================

def _empty_registry() -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "updated_at": None,
        "laws": [],
        "law_versions": [],
    }


# ============================================================
# 2. 反序列化
# ============================================================

def _deserialize_source_location(data: dict) -> SourceLocation:
    return SourceLocation(**data)


def _deserialize_law_version_source(data: dict) -> LawVersionSource:
    return LawVersionSource(**data)


def _deserialize_article_source(data: dict) -> LegalArticleSource:

    locations = [
        _deserialize_source_location(item)
        for item in data.get("locations", [])
    ]

    values = dict(data)
    values["locations"] = locations

    return LegalArticleSource(**values)


def _deserialize_article(data: dict) -> LegalArticle:

    sources = [
        _deserialize_article_source(item)
        for item in data.get("sources", [])
    ]

    values = dict(data)
    values["sources"] = sources

    return LegalArticle(**values)


def _deserialize_law_version(data: dict) -> LawVersion:

    sources = [
        _deserialize_law_version_source(item)
        for item in data.get("sources", [])
    ]

    articles = [
        _deserialize_article(item)
        for item in data.get("articles", [])
    ]

    values = dict(data)
    values["sources"] = sources
    values["articles"] = articles

    return LawVersion(**values)


def _deserialize_registry(data: dict) -> dict:

    if not isinstance(data, dict):
        raise ValueError("注册表顶层必须是 JSON 对象")

    expected_keys = {
        "schema_version",
        "updated_at",
        "laws",
        "law_versions",
    }

    if set(data) != expected_keys:
        raise ValueError(
            "注册表顶层字段不正确；"
            f"实际字段：{sorted(data)}；"
            f"预期字段：{sorted(expected_keys)}"
        )

    if data["schema_version"] != SCHEMA_VERSION:
        raise ValueError(
            "不支持的注册表 schema_version："
            f"{data['schema_version']!r}"
        )

    if not isinstance(data["laws"], list):
        raise ValueError("laws 必须是数组")

    if not isinstance(data["law_versions"], list):
        raise ValueError("law_versions 必须是数组")

    laws = [
        Law(**item)
        for item in data["laws"]
    ]

    versions = [
        _deserialize_law_version(item)
        for item in data["law_versions"]
    ]

    return {
        "schema_version": data["schema_version"],
        "updated_at": data["updated_at"],
        "laws": laws,
        "law_versions": versions,
    }


# ============================================================
# 3. 注册表完整性校验
# ============================================================

def validate_registry(registry: dict) -> None:
    """
    校验注册表对象及跨对象关系。

    主要检查：
    - Law ID 全局唯一
    - LawVersion ID 全局唯一
    - 同一 Law 下 version_key 唯一
    - Source ID 全局唯一
    - Article ID 全局唯一
    - 同一版本内条号唯一
    - Article ID 与 version_id + 条号一致
    - 法条来源必须属于当前版本
    """

    if not isinstance(registry, dict):
        raise ValueError("registry 必须是 dict")

    if registry.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("schema_version 不正确")

    if not isinstance(registry.get("laws"), list):
        raise ValueError("laws 必须是 list")

    if not isinstance(registry.get("law_versions"), list):
        raise ValueError("law_versions 必须是 list")

    # --------------------------------------------------------
    # Law
    # --------------------------------------------------------

    law_ids = set()

    for law in registry["laws"]:

        if not isinstance(law, Law):
            raise ValueError("laws 中必须全部是 Law 对象")

        if law.law_id in law_ids:
            raise ValueError(
                f"Law ID 重复：{law.law_id}"
            )

        law_ids.add(law.law_id)

    # --------------------------------------------------------
    # LawVersion
    # --------------------------------------------------------

    version_ids = set()
    version_keys = set()

    # 全局 source_id
    source_ids = set()

    # 全局 article_id
    article_ids = set()

    # 全局 article_source_id
    article_source_ids = set()

    for version in registry["law_versions"]:

        if not isinstance(version, LawVersion):
            raise ValueError(
                "law_versions 中必须全部是 LawVersion 对象"
            )

        if version.version_id in version_ids:
            raise ValueError(
                f"LawVersion ID 重复：{version.version_id}"
            )

        version_ids.add(version.version_id)

        if version.law_id not in law_ids:
            raise ValueError(
                f"LawVersion 引用了不存在的 Law：{version.law_id}"
            )

        version_key = (
            version.law_id,
            version.version_key,
        )

        if version_key in version_keys:
            raise ValueError(
                "同一法律下 version_key 重复："
                f"{version.law_id} / {version.version_key}"
            )

        version_keys.add(version_key)

        # ----------------------------------------------------
        # 来源文件
        # ----------------------------------------------------

        current_version_source_ids = set()

        for source in version.sources:

            if source.source_id in source_ids:
                raise ValueError(
                    f"source_id 全局重复：{source.source_id}"
                )

            source_ids.add(source.source_id)
            current_version_source_ids.add(source.source_id)

        # ----------------------------------------------------
        # 法条
        # ----------------------------------------------------

        current_article_numbers = set()

        for article in version.articles:

            normalized_number = normalize_article_number(
                article.article_number
            )

            if normalized_number != article.article_number:
                raise ValueError(
                    f"法条编号不是规范形式：{article.article_number}"
                )

            # 先检查同一版本内的规范化条号唯一性。
            # 例如“第十四条”和“第14条”必须先被识别为同一条号。
            if normalized_number in current_article_numbers:
                raise ValueError(
                    "同一版本内法条编号重复："
                    f"{version.version_key} / {normalized_number}"
                )

            current_article_numbers.add(normalized_number)

            # 再检查 article_id 全局唯一性。
            if article.article_id in article_ids:
                raise ValueError(
                    f"article_id 全局重复：{article.article_id}"
                )

            article_ids.add(article.article_id)

            expected_article_id = build_article_id(
                version.version_id,
                normalized_number,
            )

            if article.article_id != expected_article_id:
                raise ValueError(
                    "article_id 与版本身份和规范化条号不一致："
                    f"{article.article_id}"
                )

            # ------------------------------------------------
            # 法条来源关联
            # ------------------------------------------------

            article_source_pairs = set()

            for link in article.sources:

                # article_source_id 在整个注册表中必须唯一。
                if link.article_source_id in article_source_ids:
                    raise ValueError(
                        "article_source_id 全局重复："
                        f"{link.article_source_id}"
                    )

                article_source_ids.add(link.article_source_id)

                if link.article_id != article.article_id:
                    raise ValueError(
                        "LegalArticleSource.article_id "
                        "与所属法条不一致"
                    )

                if link.source_id not in current_version_source_ids:
                    raise ValueError(
                        "法条来源指向不属于当前版本的 source_id："
                        f"{link.source_id}"
                    )

                pair = (
                    link.article_id,
                    link.source_id,
                )

                if pair in article_source_pairs:
                    raise ValueError(
                        "同一法条与来源文件的关联重复："
                        f"{pair}"
                    )

                article_source_pairs.add(pair)

                if not isinstance(link.article_source_id, str):
                    raise ValueError(
                        "article_source_id 必须是字符串"
                    )

    return None


# ============================================================
# 4. 磁盘读取
# ============================================================

def _read_registry_unlocked(path: Path) -> dict:

    if not path.exists():
        return _empty_registry()

    try:
        raw = json.loads(
            path.read_text(encoding="utf-8")
        )
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"注册表 JSON 格式错误：{path}"
        ) from exc

    registry = _deserialize_registry(raw)

    validate_registry(registry)

    return registry


def load_registry(path=None) -> dict:
    """
    读取注册表。

    文件不存在时返回空注册表，不自动创建文件。
    """

    registry_path = (
        Path(path)
        if path is not None
        else DEFAULT_REGISTRY_PATH
    )

    return _read_registry_unlocked(registry_path)


# ============================================================
# 5. 时间与文件系统辅助函数
# ============================================================

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _fsync_directory(directory: Path) -> None:

    descriptor = os.open(
        str(directory),
        os.O_RDONLY,
    )

    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _create_backup(path: Path) -> Path:

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S_%f"
    )

    backup = path.with_name(
        path.name + ".bak_" + timestamp
    )

    shutil.copy2(path, backup)

    # 确保备份内容已经同步到文件系统
    with backup.open("rb") as file:
        os.fsync(file.fileno())

    _fsync_directory(path.parent)

    return backup


def _atomic_write(path: Path, registry: dict) -> None:

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    payload = json.dumps(
        registry,
        ensure_ascii=False,
        indent=2,
    ) + "\n"

    descriptor, temporary_name = tempfile.mkstemp(
        prefix=path.name + ".tmp_",
        dir=str(path.parent),
    )

    temporary_path = Path(temporary_name)

    try:

        with os.fdopen(
            descriptor,
            "w",
            encoding="utf-8",
        ) as file:

            file.write(payload)
            file.flush()
            os.fsync(file.fileno())

        # 先备份旧文件；备份失败时不提交
        if path.exists():
            _create_backup(path)

        # 同一目录内原子替换
        os.replace(
            temporary_path,
            path,
        )

        _fsync_directory(path.parent)

    finally:

        if temporary_path.exists():
            temporary_path.unlink()


# ============================================================
# 6. 事务接口
# ============================================================

def registry_transaction(
    mutator: Callable[[dict], None],
    path=None,
) -> dict:
    """
    注册表事务。

    流程：
    1. 获取跨进程文件锁
    2. 重读磁盘最新数据
    3. 深拷贝事务工作副本
    4. 执行 mutator
    5. 更新 updated_at
    6. 完整校验
    7. 临时文件写入并 fsync
    8. 备份旧文件
    9. os.replace 原子提交
    10. 释放锁

    mutator 接收 registry dict 并原地修改。
    mutator 抛出异常时，不提交。
    """

    if not callable(mutator):
        raise TypeError("mutator 必须是可调用对象")

    registry_path = (
        Path(path)
        if path is not None
        else DEFAULT_REGISTRY_PATH
    )

    registry_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    lock_path = registry_path.with_name(
        registry_path.name + ".lock"
    )

    with lock_path.open("a+b") as lock_file:

        fcntl.flock(
            lock_file.fileno(),
            fcntl.LOCK_EX,
        )

        try:

            # 锁内重读，避免使用过期内存数据覆盖其他进程更新
            current = _read_registry_unlocked(
                registry_path
            )

            working = deepcopy(current)

            mutator(working)

            working["updated_at"] = _now_iso()

            validate_registry(working)

            serialized = {
                "schema_version": working["schema_version"],
                "updated_at": working["updated_at"],
                "laws": [
                    item.to_dict()
                    for item in working["laws"]
                ],
                "law_versions": [
                    item.to_dict()
                    for item in working["law_versions"]
                ],
            }

            _atomic_write(
                registry_path,
                serialized,
            )

            # 返回独立对象，避免调用方修改事务内部状态
            return deepcopy(working)

        finally:

            fcntl.flock(
                lock_file.fileno(),
                fcntl.LOCK_UN,
            )
