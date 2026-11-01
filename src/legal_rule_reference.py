# -*- coding: utf-8 -*-

"""
Structured Rule Legal Reference

职责：
1. 定义 Canonical Rule 的结构化法条引用。
2. 为引用建立稳定、确定性的 reference_id。
3. 校验引用身份、引用类型和款项位置。
4. 将引用对象序列化为普通 dict。

本模块不负责：
- 法律文本真实性核验
- Law / LawVersion / LegalArticle 注册
- Canonical Rule 注册
- Runtime Rule 执行
- Decision 计算
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Dict, Optional
from uuid import UUID, uuid5

from src.legal_registry_models import ArticleLocation


# ============================================================
# Reference Identity
# ============================================================

# 此命名空间是 RuleLegalReference 身份算法的一部分。
# 一旦正式生成引用 ID，不得随意修改。
REFERENCE_NAMESPACE = UUID(
    "7c1e9a42-5d83-4f61-9b20-6a8d3e5f710c"
)


# ============================================================
# Reference Types
# ============================================================

REFERENCE_TYPES = frozenset({
    "PRIMARY",
    "EXCLUSION",
    "EXCEPTION",
    "RELATED",
    "PROCEDURAL",
})


class InvalidRuleLegalReferenceError(ValueError):
    """RuleLegalReference 结构或身份不合法。"""


# ============================================================
# Validation Helpers
# ============================================================

def _validate_non_empty_string(
    value: Any,
    field_name: str,
) -> str:
    if not isinstance(value, str):
        raise TypeError(
            f"{field_name} 必须是 str"
        )

    if not value.strip():
        raise ValueError(
            f"{field_name} 不能为空字符串"
        )

    return value


def _validate_uuid(
    value: Any,
    field_name: str,
) -> str:
    if not isinstance(value, str):
        raise TypeError(
            f"{field_name} 必须是 UUID 字符串"
        )

    try:
        parsed = UUID(value)
    except (ValueError, AttributeError, TypeError) as exc:
        raise ValueError(
            f"{field_name} 不是有效的 UUID：{value!r}"
        ) from exc

    return str(parsed)


def _normalize_location(
    location: Optional[ArticleLocation],
) -> Optional[ArticleLocation]:
    if location is None:
        return None

    if not isinstance(location, ArticleLocation):
        raise TypeError(
            "location 必须是 ArticleLocation 或 None"
        )

    return location


def _location_identity(
    location: Optional[ArticleLocation],
) -> Dict[str, Optional[int]]:
    if location is None:
        return {
            "paragraph_number": None,
            "item_number": None,
            "subitem_number": None,
        }

    return {
        "paragraph_number": location.paragraph_number,
        "item_number": location.item_number,
        "subitem_number": location.subitem_number,
    }


# ============================================================
# Deterministic Reference ID
# ============================================================

def build_reference_id(
    rule_id: str,
    article_id: str,
    reference_type: str,
    location: Optional[ArticleLocation] = None,
) -> str:
    """
    根据引用身份生成确定性 UUID5。

    身份组成：
        rule_id
        article_id
        reference_type
        paragraph_number
        item_number
        subitem_number

    legal_role 不参与身份计算。
    """

    _validate_non_empty_string(rule_id, "rule_id")
    normalized_article_id = _validate_uuid(
        article_id,
        "article_id",
    )

    if not isinstance(reference_type, str):
        raise TypeError(
            "reference_type 必须是 str"
        )

    if reference_type not in REFERENCE_TYPES:
        raise ValueError(
            f"不支持的 reference_type：{reference_type!r}"
        )

    normalized_location = _normalize_location(location)

    identity = {
        "rule_id": rule_id,
        "article_id": normalized_article_id,
        "reference_type": reference_type,
        "location": _location_identity(normalized_location),
    }

    identity_text = json.dumps(
        identity,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )

    return str(
        uuid5(REFERENCE_NAMESPACE, identity_text)
    )


# ============================================================
# RuleLegalReference
# ============================================================

@dataclass(frozen=True)
class RuleLegalReference:
    """
    Canonical Rule 与具体 LegalArticle 之间的引用关系。

    reference_id：
        根据引用身份确定性生成。

    location：
        法律文本内部位置，使用 ArticleLocation。
        不表示 DOCX / PDF 文件中的物理位置。
    """

    reference_id: str
    rule_id: str
    article_id: str
    reference_type: str
    legal_role: Optional[str] = None
    location: Optional[ArticleLocation] = None

    def __post_init__(self) -> None:
        normalized_rule_id = _validate_non_empty_string(
            self.rule_id,
            "rule_id",
        )

        normalized_article_id = _validate_uuid(
            self.article_id,
            "article_id",
        )

        normalized_reference_id = _validate_uuid(
            self.reference_id,
            "reference_id",
        )

        if not isinstance(self.reference_type, str):
            raise TypeError(
                "reference_type 必须是 str"
            )

        if self.reference_type not in REFERENCE_TYPES:
            raise ValueError(
                f"不支持的 reference_type：{self.reference_type!r}"
            )

        if self.legal_role is not None:
            _validate_non_empty_string(
                self.legal_role,
                "legal_role",
            )

        normalized_location = _normalize_location(
            self.location
        )

        expected_reference_id = build_reference_id(
            rule_id=normalized_rule_id,
            article_id=normalized_article_id,
            reference_type=self.reference_type,
            location=normalized_location,
        )

        if normalized_reference_id != expected_reference_id:
            raise InvalidRuleLegalReferenceError(
                "reference_id 与引用身份不匹配："
                f"expected={expected_reference_id}, "
                f"actual={normalized_reference_id}"
            )

        object.__setattr__(
            self,
            "article_id",
            normalized_article_id,
        )

        object.__setattr__(
            self,
            "reference_id",
            normalized_reference_id,
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        转换为 Canonical Rule 可保存的普通 dict。
        """

        location_data = None

        if self.location is not None:
            location_data = _location_identity(
                self.location
            )

        return {
            "reference_id": self.reference_id,
            "rule_id": self.rule_id,
            "article_id": self.article_id,
            "reference_type": self.reference_type,
            "legal_role": self.legal_role,
            "location": location_data,
        }


# ============================================================
# Factory
# ============================================================

def create_rule_legal_reference(
    rule_id: str,
    article_id: str,
    reference_type: str,
    legal_role: Optional[str] = None,
    location: Optional[ArticleLocation] = None,
) -> RuleLegalReference:
    """
    创建结构化引用。

    调用方不需要自行计算 reference_id。
    """

    reference_id = build_reference_id(
        rule_id=rule_id,
        article_id=article_id,
        reference_type=reference_type,
        location=location,
    )

    return RuleLegalReference(
        reference_id=reference_id,
        rule_id=rule_id,
        article_id=article_id,
        reference_type=reference_type,
        legal_role=legal_role,
        location=location,
    )


# ============================================================
# Structural Validation
# ============================================================

def rule_legal_reference_from_dict(
    value: Any,
) -> RuleLegalReference:
    """
    将 Canonical Rule 中保存的普通 dict
    严格反序列化为 RuleLegalReference。

    不允许未知字段，不允许缺失必需字段。
    """

    if not isinstance(value, dict):
        raise TypeError(
            "RuleLegalReference 数据必须是 dict"
        )

    expected_keys = {
        "reference_id",
        "rule_id",
        "article_id",
        "reference_type",
        "legal_role",
        "location",
    }

    if set(value) != expected_keys:
        missing = expected_keys - set(value)
        unexpected = set(value) - expected_keys

        raise ValueError(
            "RuleLegalReference 字段不匹配："
            f"missing={sorted(missing)}, "
            f"unexpected={sorted(unexpected)}"
        )

    location_data = value["location"]

    if location_data is None:
        location = None

    else:
        if not isinstance(location_data, dict):
            raise TypeError(
                "location 必须是 dict 或 None"
            )

        expected_location_keys = {
            "paragraph_number",
            "item_number",
            "subitem_number",
        }

        if set(location_data) != expected_location_keys:
            raise ValueError(
                "ArticleLocation 字段不匹配"
            )

        location = ArticleLocation(
            paragraph_number=location_data["paragraph_number"],
            item_number=location_data["item_number"],
            subitem_number=location_data["subitem_number"],
        )

    return RuleLegalReference(
        reference_id=value["reference_id"],
        rule_id=value["rule_id"],
        article_id=value["article_id"],
        reference_type=value["reference_type"],
        legal_role=value["legal_role"],
        location=location,
    )


def validate_rule_legal_reference(
    value: Any,
) -> bool:
    """
    验证单条引用。

    同时接受：
    - RuleLegalReference
    - Canonical Rule 使用的结构化 dict
    """

    try:
        if isinstance(value, dict):
            value = rule_legal_reference_from_dict(value)

        if not isinstance(value, RuleLegalReference):
            return False

        expected_reference_id = build_reference_id(
            rule_id=value.rule_id,
            article_id=value.article_id,
            reference_type=value.reference_type,
            location=value.location,
        )

        return value.reference_id == expected_reference_id

    except (TypeError, ValueError, InvalidRuleLegalReferenceError):
        return False


def validate_rule_legal_references(
    references: Any,
    expected_rule_id: Optional[str] = None,
) -> bool:
    """
    验证 Canonical Rule 的结构化引用列表。

    约束：
    - 必须是非空 list。
    - 每一项必须是合法的结构化引用对象或 dict。
    - reference_id 不得重复。
    - 引用身份组合不得重复。
    - 如果提供 expected_rule_id，所有引用必须属于该规则。
    """

    if not isinstance(references, list) or not references:
        return False

    normalized_references = []

    for item in references:
        if not validate_rule_legal_reference(item):
            return False

        try:
            if isinstance(item, dict):
                item = rule_legal_reference_from_dict(item)

            normalized_references.append(item)

        except (TypeError, ValueError):
            return False

    if expected_rule_id is not None:
        if any(
            item.rule_id != expected_rule_id
            for item in normalized_references
        ):
            return False

    reference_ids = [
        item.reference_id
        for item in normalized_references
    ]

    if len(reference_ids) != len(set(reference_ids)):
        return False

    identities = [
        (
            item.rule_id,
            item.article_id,
            item.reference_type,
            item.location.paragraph_number
            if item.location is not None else None,
            item.location.item_number
            if item.location is not None else None,
            item.location.subitem_number
            if item.location is not None else None,
        )
        for item in normalized_references
    ]

    return len(identities) == len(set(identities))
