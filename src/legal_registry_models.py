"""
法律注册数据模型。

职责：
1. 定义法律、法律版本、法条和来源的数据结构。
2. 在对象创建时执行字段级结构校验。
3. 提供 JSON 兼容的 to_dict() 序列化接口。

不负责：
- 法律真实性核验
- 法律效力判断
- 注册表文件读写
- 跨对象完整性事务
- Qdrant 查询或写入
"""

from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import date, datetime
import re
import uuid
from typing import Any, Dict, List, Optional, Tuple

from src.legal_identity import normalize_article_number


# ============================================================
# 1. 枚举候选值
# ============================================================

LAW_TYPES = {
    "LAW",
    "ADMINISTRATIVE_REGULATION",
}

VERIFICATION_STATUSES = {
    "UNVERIFIED",
    "VERIFIED",
    "DISPUTED",
}

VALIDITY_STATUSES = {
    "UNKNOWN",
    "IN_FORCE",
    "NOT_IN_FORCE",
}

OFFICIAL_SOURCE_TYPES = {
    "NPC_DATABASE_RECORD",
    "GOVERNMENT_OFFICIAL_TEXT",
    "GOVERNMENT_REPUBLICATION",
    "UNKNOWN",
}

PROVENANCE_TYPES = {
    "USER_CONFIRMED",
    "OFFICIAL_DOWNLOAD",
    "OFFICIAL_RECORD",
    "THIRD_PARTY_COPY",
    "UNKNOWN",
}

PROVENANCE_STATUSES = {
    "UNVERIFIED",
    "VERIFIED",
    "DISPUTED",
}

CONTENT_MATCH_STATUSES = {
    "UNVERIFIED",
    "MATCHED",
    "MISMATCHED",
}


# ============================================================
# 2. 通用校验辅助函数
# ============================================================

def _require_non_empty_string(value: Any, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} 必须是非空字符串")


def _validate_optional_string(value: Any, field_name: str) -> None:
    if value is not None and not isinstance(value, str):
        raise ValueError(f"{field_name} 必须是字符串或 None")


def _validate_uuid(value: str, field_name: str) -> None:
    _require_non_empty_string(value, field_name)

    try:
        uuid.UUID(value)
    except (ValueError, TypeError, AttributeError) as exc:
        raise ValueError(
            f"{field_name} 必须是合法 UUID：{value!r}"
        ) from exc


def _validate_choice(
    value: str,
    allowed: set,
    field_name: str,
) -> None:
    if value not in allowed:
        raise ValueError(
            f"{field_name} 值非法：{value!r}；允许值：{sorted(allowed)}"
        )


def _validate_positive_integer(value: Any, field_name: str) -> None:
    if (
        not isinstance(value, int)
        or isinstance(value, bool)
        or value <= 0
    ):
        raise ValueError(f"{field_name} 必须是正整数")


def _validate_iso_date(value: Optional[str], field_name: str) -> None:
    if value is None:
        return

    if not isinstance(value, str):
        raise ValueError(f"{field_name} 必须是 ISO 日期字符串或 None")

    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(
            f"{field_name} 日期格式错误，应为 YYYY-MM-DD：{value!r}"
        ) from exc


def _validate_iso_datetime(
    value: Optional[str],
    field_name: str,
) -> None:
    if value is None:
        return

    if not isinstance(value, str):
        raise ValueError(f"{field_name} 必须是 ISO 日期时间字符串或 None")

    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(
            f"{field_name} 日期时间格式错误：{value!r}"
        ) from exc


def _validate_sha256(value: Optional[str], field_name: str) -> None:
    if value is None:
        return

    if not isinstance(value, str) or not re.fullmatch(
        r"[0-9a-fA-F]{64}",
        value,
    ):
        raise ValueError(
            f"{field_name} 必须是 64 位 SHA256 十六进制字符串"
        )


def _to_json_compatible(value: Any) -> Any:
    """
    将 dataclass 内容转换为 JSON 兼容数据。

    tuple 转换为 list。
    dict/list 递归转换。
    """

    if is_dataclass(value):
        return _to_json_compatible(asdict(value))

    if isinstance(value, dict):
        return {
            key: _to_json_compatible(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple)):
        return [
            _to_json_compatible(item)
            for item in value
        ]

    return value


class SerializableModel:
    """提供 JSON 兼容的字典序列化接口。"""

    def to_dict(self) -> Dict[str, Any]:
        return _to_json_compatible(self)


# ============================================================
# 3. Law
# ============================================================

@dataclass
class Law(SerializableModel):
    law_id: str
    law_name: str
    law_type: str
    issuing_authority: Optional[str] = None
    aliases: List[str] = field(default_factory=list)
    created_at: Optional[str] = None

    def __post_init__(self):
        _validate_uuid(self.law_id, "law_id")
        _require_non_empty_string(self.law_name, "law_name")

        _validate_choice(
            self.law_type,
            LAW_TYPES,
            "law_type",
        )

        _validate_optional_string(
            self.issuing_authority,
            "issuing_authority",
        )

        _validate_iso_datetime(
            self.created_at,
            "created_at",
        )

        if not isinstance(self.aliases, list):
            raise ValueError("aliases 必须是 list")

        for alias in self.aliases:
            _require_non_empty_string(alias, "aliases 中的名称")


# ============================================================
# 4. SourceLocation
# ============================================================

@dataclass(frozen=True)
class SourceLocation(SerializableModel):
    """
    来源文件中的物理位置。

    第一版 DOCX 只记录正文直接段落。
    paragraph_number 从 1 开始，空段落也计入。
    """

    paragraph_start: int
    paragraph_end: int
    paragraph_numbers: Tuple[int, ...]

    def __post_init__(self):
        _validate_positive_integer(
            self.paragraph_start,
            "paragraph_start",
        )

        _validate_positive_integer(
            self.paragraph_end,
            "paragraph_end",
        )

        if self.paragraph_end < self.paragraph_start:
            raise ValueError(
                "paragraph_end 不能小于 paragraph_start"
            )

        if not isinstance(self.paragraph_numbers, (tuple, list)):
            raise ValueError(
                "paragraph_numbers 必须是 tuple 或 list"
            )

        numbers = tuple(self.paragraph_numbers)

        if not numbers:
            raise ValueError("paragraph_numbers 不能为空")

        for number in numbers:
            _validate_positive_integer(
                number,
                "paragraph_numbers 中的值",
            )

        if tuple(sorted(set(numbers))) != numbers:
            raise ValueError(
                "paragraph_numbers 必须严格递增且不能重复"
            )

        if numbers[0] != self.paragraph_start:
            raise ValueError(
                "paragraph_numbers 首项必须等于 paragraph_start"
            )

        if numbers[-1] != self.paragraph_end:
            raise ValueError(
                "paragraph_numbers 末项必须等于 paragraph_end"
            )

        object.__setattr__(self, "paragraph_numbers", numbers)


# ============================================================
# 5. ArticleLocation
# ============================================================

@dataclass(frozen=True)
class ArticleLocation(SerializableModel):
    """
    法律文本内部的位置。

    paragraph_number：款
    item_number：项
    subitem_number：目

    None 表示没有明确指定，不自动推断。
    """

    paragraph_number: Optional[int] = None
    item_number: Optional[int] = None
    subitem_number: Optional[int] = None

    def __post_init__(self):

        if self.paragraph_number is not None:
            _validate_positive_integer(
                self.paragraph_number,
                "paragraph_number",
            )

        if self.item_number is not None:
            _validate_positive_integer(
                self.item_number,
                "item_number",
            )

        if self.subitem_number is not None:
            _validate_positive_integer(
                self.subitem_number,
                "subitem_number",
            )

            if self.item_number is None:
                raise ValueError(
                    "subitem_number 不能在 item_number 缺失时独立存在"
                )


# ============================================================
# 6. LawVersionSource
# ============================================================

@dataclass
class LawVersionSource(SerializableModel):
    source_id: str
    source_name: str

    original_download_url: Optional[str] = None
    official_source_url: Optional[str] = None

    official_source_type: str = "UNKNOWN"

    source_hash: Optional[str] = None

    retrieved_at: Optional[str] = None
    record_located_at: Optional[str] = None

    provenance_type: str = "UNKNOWN"
    provenance_status: str = "UNVERIFIED"
    content_match_status: str = "UNVERIFIED"

    verification_note: Optional[str] = None

    def __post_init__(self):

        _validate_uuid(self.source_id, "source_id")
        _require_non_empty_string(self.source_name, "source_name")

        _validate_optional_string(
            self.original_download_url,
            "original_download_url",
        )

        _validate_optional_string(
            self.official_source_url,
            "official_source_url",
        )

        _validate_choice(
            self.official_source_type,
            OFFICIAL_SOURCE_TYPES,
            "official_source_type",
        )

        _validate_sha256(self.source_hash, "source_hash")

        _validate_iso_datetime(
            self.retrieved_at,
            "retrieved_at",
        )

        _validate_iso_datetime(
            self.record_located_at,
            "record_located_at",
        )

        _validate_choice(
            self.provenance_type,
            PROVENANCE_TYPES,
            "provenance_type",
        )

        _validate_choice(
            self.provenance_status,
            PROVENANCE_STATUSES,
            "provenance_status",
        )

        _validate_choice(
            self.content_match_status,
            CONTENT_MATCH_STATUSES,
            "content_match_status",
        )

        _validate_optional_string(
            self.verification_note,
            "verification_note",
        )


# ============================================================
# 7. LegalArticleSource
# ============================================================

@dataclass
class LegalArticleSource(SerializableModel):
    article_source_id: str
    article_id: str
    source_id: str
    locations: List[SourceLocation] = field(default_factory=list)

    def __post_init__(self):

        _validate_uuid(
            self.article_source_id,
            "article_source_id",
        )

        _validate_uuid(self.article_id, "article_id")
        _validate_uuid(self.source_id, "source_id")

        if not isinstance(self.locations, list):
            raise ValueError("locations 必须是 list")

        if not self.locations:
            raise ValueError(
                "LegalArticleSource 至少需要一个 SourceLocation"
            )

        for location in self.locations:
            if not isinstance(location, SourceLocation):
                raise ValueError(
                    "locations 中的元素必须是 SourceLocation"
                )

        location_keys = [
            (
                item.paragraph_start,
                item.paragraph_end,
                item.paragraph_numbers,
            )
            for item in self.locations
        ]

        if len(location_keys) != len(set(location_keys)):
            raise ValueError("locations 不能包含完全重复的位置")


# ============================================================
# 8. LegalArticle
# ============================================================

@dataclass
class LegalArticle(SerializableModel):
    article_id: str
    article_number: str

    article_text_hash: Optional[str] = None

    sources: List[LegalArticleSource] = field(default_factory=list)

    def __post_init__(self):

        _validate_uuid(self.article_id, "article_id")

        _require_non_empty_string(
            self.article_number,
            "article_number",
        )

        # 使用唯一身份规范化入口
        self.article_number = normalize_article_number(
            self.article_number
        )

        _validate_sha256(
            self.article_text_hash,
            "article_text_hash",
        )

        if not isinstance(self.sources, list):
            raise ValueError("LegalArticle.sources 必须是 list")

        for source in self.sources:
            if not isinstance(source, LegalArticleSource):
                raise ValueError(
                    "LegalArticle.sources 中的元素必须是 LegalArticleSource"
                )


# ============================================================
# 9. LawVersion
# ============================================================

@dataclass
class LawVersion(SerializableModel):
    version_id: str
    law_id: str

    version_key: str
    version_label: str

    promulgation_date: Optional[str] = None
    effective_date: Optional[str] = None
    expiry_date: Optional[str] = None

    amendment_description: Optional[str] = None

    sources: List[LawVersionSource] = field(default_factory=list)
    articles: List[LegalArticle] = field(default_factory=list)

    verification_status: str = "UNVERIFIED"
    verified_at: Optional[str] = None
    verification_note: Optional[str] = None

    validity_status: str = "UNKNOWN"
    validity_checked_at: Optional[str] = None
    validity_note: Optional[str] = None

    def __post_init__(self):

        _validate_uuid(self.version_id, "version_id")
        _validate_uuid(self.law_id, "law_id")

        _require_non_empty_string(
            self.version_key,
            "version_key",
        )

        _require_non_empty_string(
            self.version_label,
            "version_label",
        )

        _validate_iso_date(
            self.promulgation_date,
            "promulgation_date",
        )

        _validate_iso_date(
            self.effective_date,
            "effective_date",
        )

        _validate_iso_date(
            self.expiry_date,
            "expiry_date",
        )

        if (
            self.effective_date is not None
            and self.expiry_date is not None
            and self.expiry_date <= self.effective_date
        ):
            raise ValueError(
                "expiry_date 必须晚于 effective_date；"
                "失效日期采用左闭右开区间的结束边界"
            )

        _validate_optional_string(
            self.amendment_description,
            "amendment_description",
        )

        _validate_choice(
            self.verification_status,
            VERIFICATION_STATUSES,
            "verification_status",
        )

        _validate_choice(
            self.validity_status,
            VALIDITY_STATUSES,
            "validity_status",
        )

        _validate_iso_datetime(
            self.verified_at,
            "verified_at",
        )

        _validate_iso_datetime(
            self.validity_checked_at,
            "validity_checked_at",
        )

        _validate_optional_string(
            self.verification_note,
            "verification_note",
        )

        _validate_optional_string(
            self.validity_note,
            "validity_note",
        )

        if not isinstance(self.sources, list):
            raise ValueError("LawVersion.sources 必须是 list")

        if not isinstance(self.articles, list):
            raise ValueError("LawVersion.articles 必须是 list")

        for source in self.sources:
            if not isinstance(source, LawVersionSource):
                raise ValueError(
                    "LawVersion.sources 中的元素必须是 LawVersionSource"
                )

        for article in self.articles:
            if not isinstance(article, LegalArticle):
                raise ValueError(
                    "LawVersion.articles 中的元素必须是 LegalArticle"
                )
