"""
法律身份模块。

职责：
1. 严格规范化完整法条编号。
2. 根据 version_id 和规范化法条编号生成稳定 article_id。

不负责：
- 法条提取
- Qdrant 查询或写入
- 法律版本注册
- JSON 注册表管理
- 款、项、目引用解析
"""

import json
import re
import unicodedata
import uuid
from urllib.parse import urlsplit, urlunsplit


class InvalidArticleNumberError(ValueError):
    """法条编号无法严格解析或不符合规范。"""


# ============================================================
# Article ID 固定命名空间
# ============================================================
#
# 这是项目级永久常量。
#
# 一旦正式生成 article_id，不得随意修改。
# 修改此 UUID 会导致相同 version_id 和条号生成不同 article_id。
#
ARTICLE_NAMESPACE = uuid.UUID(
    "b6d7e8f1-2a3c-4d5e-8f90-1a2b3c4d5e6f"
)


# ============================================================
# Canonical Registry V2 固定命名空间
# ============================================================

LAW_NAMESPACE = uuid.UUID(
    "0e6d1b4a-72c8-5f31-9a40-2b7e6d8c1f53"
)

VERSION_NAMESPACE = uuid.UUID(
    "1f7c2a90-8b43-5d61-ae20-3c9f7b5d1a64"
)

SOURCE_NAMESPACE = uuid.UUID(
    "2a8e3c51-9d74-5f20-b136-4e0a8c6d2f75"
)

ARTICLE_SOURCE_NAMESPACE = uuid.UUID(
    "3b9f4d62-ae85-5c31-c247-5f1b9d7e3a86"
)


# ============================================================
# 中文数字定义
# ============================================================

CHINESE_DIGITS = {
    "零": 0,
    "〇": 0,
    "一": 1,
    "二": 2,
    "两": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
}

CHINESE_SMALL_UNITS = {
    "十": 10,
    "百": 100,
    "千": 1000,
}

CHINESE_LARGE_UNITS = {
    "万": 10000,
}

ARTICLE_PATTERN = re.compile(
    r"^第\s*"
    r"(?P<main>[零〇一二两三四五六七八九十百千万0-9]+)"
    r"\s*条"
    r"(?:\s*之\s*"
    r"(?P<suffix>[零〇一二两三四五六七八九十百千万0-9]+)"
    r")?$"
)


# ============================================================
# 内部函数：整数转换为规范中文数字
# ============================================================

def _section_to_chinese(value: int) -> str:
    """将 0 到 9999 的整数转换为中文数字。"""

    if not isinstance(value, int) or not 0 <= value <= 9999:
        raise ValueError("section 数值必须在 0 到 9999 之间")

    if value == 0:
        return "零"

    digits = "零一二三四五六七八九"
    units = ["", "十", "百", "千"]

    result = []
    zero_pending = False

    for position in range(3, -1, -1):

        divisor = 10 ** position
        digit = value // divisor % 10

        if digit == 0:

            if result and value % divisor != 0:
                zero_pending = True

            continue

        if zero_pending:
            result.append("零")
            zero_pending = False

        # 10 到 19 的规范写法为十、十一……十九
        if not (
            position == 1
            and digit == 1
            and not result
        ):
            result.append(digits[digit])

        result.append(units[position])

    return "".join(result)


def _number_to_chinese(value: int) -> str:
    """将正整数转换为规范中文数字，最大支持 99999999。"""

    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("数值必须是整数")

    if not 1 <= value <= 99999999:
        raise ValueError("法条编号数字超出支持范围")

    if value < 10000:
        return _section_to_chinese(value)

    high = value // 10000
    low = value % 10000

    result = _section_to_chinese(high) + "万"

    if low == 0:
        return result

    if low < 1000:
        result += "零"

    result += _section_to_chinese(low)

    return result


# ============================================================
# 内部函数：严格解析中文数字
# ============================================================

def _parse_chinese_number(value: str) -> int:
    """
    严格解析中文数字。

    支持：
        十
        十四
        一百零七
        两百
        一千零一
        一万零一

    零作为数位占位符处理，不作为普通数字累加。
    不接受无法明确解释的连续数字写法。
    """

    if not isinstance(value, str) or not value:
        raise InvalidArticleNumberError("中文数字不能为空")

    normalized = value.replace("〇", "零").replace("两", "二")

    total = 0
    section = 0
    number = None

    last_small_unit = 10000
    last_large_unit = 100000000

    zero_pending = False
    has_large_unit = False

    for char in normalized:

        # ----------------------------------------------------
        # 数字字符
        # ----------------------------------------------------

        if char in CHINESE_DIGITS:

            digit = CHINESE_DIGITS[char]

            if digit == 0:

                # 零不能连续出现，也不能紧跟一个尚未使用的数字
                if number is not None or zero_pending:
                    raise InvalidArticleNumberError(
                        f"中文数字零的位置不合法：{value}"
                    )

                zero_pending = True
                continue

            # 非零数字前面不能已有尚未使用的数字
            if number is not None:
                raise InvalidArticleNumberError(
                    f"中文数字存在连续数字：{value}"
                )

            number = digit
            zero_pending = False
            continue

        # ----------------------------------------------------
        # 十、百、千
        # ----------------------------------------------------

        if char in CHINESE_SMALL_UNITS:

            unit = CHINESE_SMALL_UNITS[char]

            if zero_pending:
                raise InvalidArticleNumberError(
                    f"中文数字零不能直接作为单位前数字：{value}"
                )

            if unit >= last_small_unit:
                raise InvalidArticleNumberError(
                    f"中文数字单位顺序错误：{value}"
                )

            if number is None:

                # 允许“十”“十一”等省略十位前面的“一”
                if unit == 10 and section == 0:
                    number = 1
                else:
                    raise InvalidArticleNumberError(
                        f"中文数字缺少单位前数字：{value}"
                    )

            section += number * unit

            number = None
            last_small_unit = unit
            continue

        # ----------------------------------------------------
        # 万
        # ----------------------------------------------------

        if char in CHINESE_LARGE_UNITS:

            unit = CHINESE_LARGE_UNITS[char]

            if zero_pending:
                raise InvalidArticleNumberError(
                    f"中文数字零不能直接作为大单位前数字：{value}"
                )

            if has_large_unit or unit >= last_large_unit:
                raise InvalidArticleNumberError(
                    f"中文大单位顺序错误：{value}"
                )

            section += number or 0

            if section == 0:
                raise InvalidArticleNumberError(
                    f"中文数字大单位前缺少数字：{value}"
                )

            total += section * unit

            section = 0
            number = None

            last_small_unit = 10000
            last_large_unit = unit
            has_large_unit = True
            continue

        raise InvalidArticleNumberError(
            f"包含不支持的中文数字字符：{char}"
        )

    if zero_pending:
        raise InvalidArticleNumberError(
            f"中文数字不能以零结尾：{value}"
        )

    result = total + section + (number or 0)

    if not 1 <= result <= 99999999:
        raise InvalidArticleNumberError(
            f"数字超出支持范围或为零：{value}"
        )

    # 严格要求输入符合唯一规范中文数字形式
    canonical = _number_to_chinese(result)

    if canonical != normalized:
        raise InvalidArticleNumberError(
            f"中文数字不是规范写法：{value}，"
            f"规范写法应为：{canonical}"
        )

    return result
def _parse_number(value: str) -> int:
    """解析阿拉伯数字或中文数字。"""

    if not isinstance(value, str) or not value:
        raise InvalidArticleNumberError("数字部分不能为空")

    if re.fullmatch(r"[0-9]+", value):

        number = int(value)

        if not 1 <= number <= 99999999:
            raise InvalidArticleNumberError(
                f"数字超出支持范围或为零：{value}"
            )

        return number

    if re.fullmatch(r"[零〇一二两三四五六七八九十百千万]+", value):
        return _parse_chinese_number(value)

    raise InvalidArticleNumberError(
        f"无法严格解析数字：{value}"
    )


# ============================================================
# 公共接口：规范化法条编号
# ============================================================

def normalize_article_number(article_number: str) -> str:
    """
    将完整法条编号转换为规范形式。

    示例：
        第十四条       -> 第十四条
        第14条         -> 第十四条
        第 14 条       -> 第十四条
        第十四条之一   -> 第十四条之一
        第14条之1      -> 第十四条之一

    失败时抛出 InvalidArticleNumberError。
    """

    if not isinstance(article_number, str):
        raise InvalidArticleNumberError(
            "法条编号必须是字符串"
        )

    value = unicodedata.normalize(
        "NFKC",
        article_number,
    ).strip()

    if not value:
        raise InvalidArticleNumberError(
            "法条编号不能为空"
        )

    match = ARTICLE_PATTERN.fullmatch(value)

    if not match:
        raise InvalidArticleNumberError(
            f"非法法条编号格式：{article_number!r}"
        )

    main_value = _parse_number(match.group("main"))

    normalized = (
        "第"
        + _number_to_chinese(main_value)
        + "条"
    )

    suffix = match.group("suffix")

    if suffix is not None:

        suffix_value = _parse_number(suffix)

        normalized += (
            "之"
            + _number_to_chinese(suffix_value)
        )

    return normalized


# ============================================================
# 内部函数：校验版本 ID
# ============================================================

def _validate_version_id(version_id: str) -> str:
    """校验并返回标准 UUID 字符串。"""

    if not isinstance(version_id, str) or not version_id.strip():
        raise ValueError("version_id 必须是非空 UUID 字符串")

    try:
        parsed = uuid.UUID(version_id)
    except (ValueError, AttributeError, TypeError) as exc:
        raise ValueError(
            f"version_id 不是有效 UUID：{version_id!r}"
        ) from exc

    return str(parsed)


# ============================================================
# 公共接口：生成 article_id
# ============================================================

def build_article_id(
    version_id: str,
    article_number: str,
) -> str:
    """
    根据版本 ID 和规范化法条编号生成稳定 article_id。

    同一版本、同一规范化条号：
        生成相同 article_id。

    不同版本、相同条号：
        生成不同 article_id。
    """

    normalized_version_id = _validate_version_id(version_id)

    normalized_article_number = normalize_article_number(
        article_number
    )

    identity_name = (
        f"{normalized_version_id}|{normalized_article_number}"
    )

    return str(
        uuid.uuid5(
            ARTICLE_NAMESPACE,
            identity_name,
        )
    )


# ============================================================
# Canonical Registry V2：通用身份辅助函数
# ============================================================

def _normalize_identity_text(value: str, field_name: str) -> str:
    """执行 NFKC、去除首尾空白并合并连续空白。"""

    if not isinstance(value, str):
        raise ValueError(f"{field_name} 必须是字符串")

    normalized = unicodedata.normalize("NFKC", value)
    normalized = " ".join(normalized.split())

    if not normalized:
        raise ValueError(f"{field_name} 不能为空")

    return normalized


def _validate_identity_uuid(value: str, field_name: str) -> str:
    """校验 UUID，并返回标准 UUID 字符串。"""

    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} 必须是非空 UUID 字符串")

    try:
        parsed = uuid.UUID(value)
    except (ValueError, AttributeError, TypeError) as exc:
        raise ValueError(
            f"{field_name} 不是有效 UUID：{value!r}"
        ) from exc

    return str(parsed)


def _build_identity_uuid(namespace: uuid.UUID, identity: dict) -> str:
    """使用规范 JSON 和 UUID5 生成稳定身份。"""

    identity_json = json.dumps(
        identity,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )

    return str(uuid.uuid5(namespace, identity_json))


# ============================================================
# Canonical Registry V2：Law 身份
# ============================================================

def build_law_id(
    jurisdiction: str,
    canonical_law_name: str,
) -> str:
    """根据法域和规范法律名称生成稳定 Law ID。"""

    normalized_jurisdiction = _normalize_identity_text(
        jurisdiction,
        "jurisdiction",
    )

    normalized_law_name = _normalize_identity_text(
        canonical_law_name,
        "canonical_law_name",
    )

    identity = {
        "jurisdiction": normalized_jurisdiction,
        "canonical_law_name": normalized_law_name,
    }

    return _build_identity_uuid(LAW_NAMESPACE, identity)


# ============================================================
# Canonical Registry V2：Version 身份
# ============================================================

def build_version_id(
    law_id: str,
    version_key: str,
) -> str:
    """根据 Law ID 和版本键生成稳定 Version ID。"""

    normalized_law_id = _validate_identity_uuid(
        law_id,
        "law_id",
    )

    normalized_version_key = _normalize_identity_text(
        version_key,
        "version_key",
    )

    identity = {
        "law_id": normalized_law_id,
        "version_key": normalized_version_key,
    }

    return _build_identity_uuid(VERSION_NAMESPACE, identity)


# ============================================================
# Canonical Registry V2：官方来源 URL 规范化
# ============================================================

def normalize_official_source_url(official_source_url: str) -> str:
    """
    规范化官方来源 URL。

    - 仅允许 HTTP / HTTPS；
    - scheme 和 hostname 转小写；
    - 移除对应协议的默认端口；
    - 移除 fragment；
    - 保留 path 原样；
    - 保留 query 参数及其顺序；
    - 拒绝用户名、密码和非法端口。
    """

    if not isinstance(official_source_url, str):
        raise ValueError("official_source_url 必须是字符串")

    # 控制字符必须在 strip 之前检查，避免换行符等被提前删除。
    if any(ord(char) < 32 for char in official_source_url):
        raise ValueError("official_source_url 不允许包含控制字符")

    # 按正式身份协议去除普通首尾空白。
    normalized_input_url = official_source_url.strip()

    if not normalized_input_url:
        raise ValueError("official_source_url 不能为空")

    # URL 内部仍不允许出现空白。
    if any(char.isspace() for char in normalized_input_url):
        raise ValueError("official_source_url 不允许包含内部空白")

    try:
        parsed = urlsplit(normalized_input_url)

        scheme = parsed.scheme.lower()

        if scheme not in {"http", "https"}:
            raise ValueError("只允许 HTTP 或 HTTPS URL")

        if not parsed.netloc or not parsed.hostname:
            raise ValueError("URL 缺少有效 hostname")

        if parsed.username is not None or parsed.password is not None:
            raise ValueError("URL 不允许包含用户名或密码")

        hostname = parsed.hostname.lower()
        port = parsed.port

        # 拒绝显式但为空的端口，例如 https://example.com:
        if parsed.netloc.endswith(":"):
            raise ValueError("URL 端口不能为空")

    except ValueError as exc:
        raise ValueError(
            f"非法官方来源 URL：{official_source_url!r}；{exc}"
        ) from exc

    # IPv6 hostname 需要保留方括号。
    if ":" in hostname and not hostname.startswith("["):
        normalized_host = f"[{hostname}]"
    else:
        normalized_host = hostname

    if port is not None:
        is_default_port = (
            (scheme == "http" and port == 80)
            or (scheme == "https" and port == 443)
        )

        if is_default_port:
            normalized_netloc = normalized_host
        else:
            normalized_netloc = f"{normalized_host}:{port}"
    else:
        normalized_netloc = normalized_host

    return urlunsplit(
        (
            scheme,
            normalized_netloc,
            parsed.path,
            parsed.query,
            "",
        )
    )


# ============================================================
# Canonical Registry V2：Source 身份
# ============================================================

def build_source_id(
    official_source_url: str,
    source_hash: str,
) -> str:
    """根据官方来源 URL 和原始文件 SHA256 生成 Source ID。"""

    normalized_url = normalize_official_source_url(
        official_source_url
    )

    if not isinstance(source_hash, str):
        raise ValueError("source_hash 必须是字符串")

    if not re.fullmatch(r"[0-9a-fA-F]{64}", source_hash):
        raise ValueError(
            "source_hash 必须是 64 位十六进制 SHA256"
        )

    normalized_hash = source_hash.lower()

    identity = {
        "canonical_official_source_url": normalized_url,
        "source_hash": normalized_hash,
    }

    return _build_identity_uuid(SOURCE_NAMESPACE, identity)


# ============================================================
# Canonical Registry V2：ArticleSource 身份
# ============================================================

def build_article_source_id(
    article_id: str,
    source_id: str,
) -> str:
    """根据 Article ID 和 Source ID 生成稳定 ArticleSource ID。"""

    normalized_article_id = _validate_identity_uuid(
        article_id,
        "article_id",
    )

    normalized_source_id = _validate_identity_uuid(
        source_id,
        "source_id",
    )

    identity = {
        "article_id": normalized_article_id,
        "source_id": normalized_source_id,
    }

    return _build_identity_uuid(
        ARTICLE_SOURCE_NAMESPACE,
        identity,
    )
