"""
法律注册表读取接口。

职责：
    从 legal_registry.json 查询 Law、LawVersion、LegalArticle。

与 legal_reference.py 的区别：
    legal_registry.py 负责法律身份和版本主数据读取。
    legal_reference.py 保留原有 Qdrant 检索和引用展开职责。

本模块只读，不提供注册表写入接口。
"""

from copy import deepcopy
from pathlib import Path
from typing import List, Optional

from src.legal_identity import normalize_article_number
from src.legal_registry_models import Law, LawVersion, LegalArticle
from src.legal_registry_store import load_registry


def _load_registry(path=None) -> dict:
    """读取注册表，并检查基本结构。"""

    registry = load_registry(path=path)

    if not isinstance(registry, dict):
        raise TypeError("法律注册表必须是 dict")

    if not isinstance(registry.get("laws"), list):
        raise ValueError("法律注册表 laws 必须是 list")

    if not isinstance(registry.get("law_versions"), list):
        raise ValueError("法律注册表 law_versions 必须是 list")

    return registry


def get_law(law_id: str, path=None) -> Law:
    """
    根据稳定 law_id 获取法律。

    找不到时抛出 KeyError。
    返回对象为独立副本，调用方修改不会影响注册表。
    """

    if not isinstance(law_id, str) or not law_id.strip():
        raise ValueError("law_id 必须是非空字符串")

    registry = _load_registry(path)

    for law in registry["laws"]:
        if law.law_id == law_id:
            return deepcopy(law)

    raise KeyError(f"没有找到 law_id：{law_id}")


def find_law_by_name(name: str, path=None) -> List[Law]:
    """
    根据规范名称或 aliases 精确查找法律候选。

    匹配规则：
        1. 去除输入首尾空白。
        2. 使用 casefold() 做大小写无关比较。
        3. 只匹配 law_name 和 aliases。
        4. 不进行模糊匹配。
        5. 不自动合并法律。

    返回：
        匹配的 Law 对象列表。
        无匹配时返回空列表。
        多个法律匹配时全部返回，交由调用方处理。
    """

    if not isinstance(name, str) or not name.strip():
        raise ValueError("name 必须是非空字符串")

    target = name.strip().casefold()

    registry = _load_registry(path)

    matches = []

    for law in registry["laws"]:

        candidates = [law.law_name]
        candidates.extend(law.aliases or [])

        matched = any(
            isinstance(candidate, str)
            and candidate.strip().casefold() == target
            for candidate in candidates
        )

        if matched:
            matches.append(deepcopy(law))

    return matches


def get_law_version(version_id: str, path=None) -> LawVersion:
    """
    根据稳定 version_id 获取法律版本。

    找不到时抛出 KeyError。
    返回对象为独立副本。
    """

    if not isinstance(version_id, str) or not version_id.strip():
        raise ValueError("version_id 必须是非空字符串")

    registry = _load_registry(path)

    for version in registry["law_versions"]:
        if version.version_id == version_id:
            return deepcopy(version)

    raise KeyError(
        f"没有找到 version_id：{version_id}"
    )


def find_article(
    version_id: str,
    article_number: str,
    path=None,
) -> Optional[LegalArticle]:
    """
    在指定法律版本中按规范化条号查找法条。

    必须指定 version_id，不允许跨版本查询。

    article_number 会通过 normalize_article_number()
    统一规范化。

    返回：
        找到时返回 LegalArticle 独立副本。
        找不到法条时返回 None。
        找不到版本时抛出 KeyError。
        条号格式不合法时抛出 InvalidArticleNumberError。
    """

    if not isinstance(version_id, str) or not version_id.strip():
        raise ValueError("version_id 必须是非空字符串")

    normalized_number = normalize_article_number(
        article_number
    )

    version = get_law_version(
        version_id=version_id,
        path=path,
    )

    for article in version.articles:
        if article.article_number == normalized_number:
            return deepcopy(article)

    return None
