"""
正式初始化法律注册表。

数据来源：
    scripts/preview_legal_registry.py

写入目标：
    data/legal_registry/legal_registry.json

安全约束：
    1. 只允许初始化空注册表。
    2. 事务锁内重新检查注册表状态。
    3. 不重新生成 Law、LawVersion、LegalArticle 的身份 ID。
    4. 使用 registry_transaction() 完成原子提交。
    5. 写入后重新加载并核对完整数据。
    6. 不修改 Qdrant。
"""

from pathlib import Path
from copy import deepcopy
import sys


# ============================================================
# 一、项目路径
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ============================================================
# 二、导入项目接口
# ============================================================

from scripts.preview_legal_registry import build_preview_registry

from src.legal_registry_store import (
    load_registry,
    registry_transaction,
    validate_registry,
)


REGISTRY_PATH = (
    PROJECT_ROOT
    / "data"
    / "legal_registry"
    / "legal_registry.json"
)


# ============================================================
# 三、预期数据数量
# ============================================================

EXPECTED_COUNTS = {
    "laws": 4,
    "law_versions": 4,
    "law_version_sources": 4,
    "articles": 297,
    "article_sources": 297,
    "source_locations": 297,
}


# ============================================================
# 四、统计注册表数据
# ============================================================

def count_registry_objects(registry):
    """统计注册表中的核心对象数量。"""

    laws = registry["laws"]
    versions = registry["law_versions"]

    law_version_sources = sum(
        len(version.sources)
        for version in versions
    )

    articles = sum(
        len(version.articles)
        for version in versions
    )

    article_sources = sum(
        len(article.sources)
        for version in versions
        for article in version.articles
    )

    source_locations = sum(
        len(link.locations)
        for version in versions
        for article in version.articles
        for link in article.sources
    )

    return {
        "laws": len(laws),
        "law_versions": len(versions),
        "law_version_sources": law_version_sources,
        "articles": articles,
        "article_sources": article_sources,
        "source_locations": source_locations,
    }


def print_registry_counts(registry, title):
    """输出注册表对象统计。"""

    counts = count_registry_objects(registry)

    print()
    print("=" * 72)
    print(title)
    print("=" * 72)

    for name, count in counts.items():
        expected = EXPECTED_COUNTS[name]

        status = "PASS" if count == expected else "FAIL"

        print(
            f"{name:24s}"
            f"实际：{count:4d}  "
            f"预期：{expected:4d}  "
            f"{status}"
        )

    return counts


# ============================================================
# 五、检查预览数据
# ============================================================

def validate_preview(preview):
    """验证预览数据结构和数量。"""

    if not isinstance(preview, dict):
        raise TypeError("预览数据必须是 dict")

    required_keys = {
        "schema_version",
        "updated_at",
        "laws",
        "law_versions",
    }

    if set(preview.keys()) != required_keys:
        raise ValueError(
            "预览数据顶层字段不符合预期："
            f"{list(preview.keys())}"
        )

    if preview["schema_version"] != "1.0":
        raise ValueError(
            "预览数据 schema_version 不正确："
            f"{preview['schema_version']}"
        )

    # 使用正式注册表校验器检查对象和关联。
    validate_registry(preview)

    counts = print_registry_counts(
        preview,
        "预览数据数量检查",
    )

    if counts != EXPECTED_COUNTS:
        raise ValueError(
            "预览数据数量与预期不一致，拒绝初始化。"
        )

    return None


# ============================================================
# 六、事务写入
# ============================================================

def initialize_registry(preview):
    """
    将预览数据写入正式注册表。

    registry_transaction 会：
        获取文件锁
        重读磁盘
        深拷贝
        执行 mutator
        完整校验
        原子写入
    """

    def mutator(registry):
        # ----------------------------------------------------
        # 1. 再次确认 schema
        # ----------------------------------------------------

        if registry.get("schema_version") != preview["schema_version"]:
            raise ValueError(
                "正式注册表 schema_version 不匹配，拒绝初始化。"
            )

        # ----------------------------------------------------
        # 2. 防止覆盖已经存在的数据
        # ----------------------------------------------------

        if registry.get("laws"):
            raise RuntimeError(
                "法律注册表已经包含 Law 数据，拒绝重复初始化。"
            )

        if registry.get("law_versions"):
            raise RuntimeError(
                "法律注册表已经包含 LawVersion 数据，拒绝重复初始化。"
            )

        # ----------------------------------------------------
        # 3. 保持预览阶段生成的身份 ID
        # ----------------------------------------------------

        registry["laws"] = deepcopy(
            preview["laws"]
        )

        registry["law_versions"] = deepcopy(
            preview["law_versions"]
        )

    return registry_transaction(
        mutator,
        path=REGISTRY_PATH,
    )


# ============================================================
# 七、写入后完整核对
# ============================================================

def verify_persisted_registry(preview, persisted):
    """重新加载 JSON，核对持久化数据。"""

    print()
    print("=" * 72)
    print("写入后持久化验证")
    print("=" * 72)

    # --------------------------------------------------------
    # 1. 完整结构校验
    # --------------------------------------------------------

    validate_registry(persisted)

    # --------------------------------------------------------
    # 2. 数量核对
    # --------------------------------------------------------

    persisted_counts = print_registry_counts(
        persisted,
        "正式注册表数量",
    )

    if persisted_counts != EXPECTED_COUNTS:
        raise RuntimeError(
            "持久化数据数量不正确。"
        )

    # --------------------------------------------------------
    # 3. 比较 Law
    # --------------------------------------------------------

    expected_laws = [
        item.to_dict()
        for item in preview["laws"]
    ]

    actual_laws = [
        item.to_dict()
        for item in persisted["laws"]
    ]

    if expected_laws != actual_laws:
        raise RuntimeError(
            "Law 持久化内容与预览数据不一致。"
        )

    print("\nLaw 内容：一致")

    # --------------------------------------------------------
    # 4. 比较 LawVersion 及其嵌套对象
    # --------------------------------------------------------

    expected_versions = [
        item.to_dict()
        for item in preview["law_versions"]
    ]

    actual_versions = [
        item.to_dict()
        for item in persisted["law_versions"]
    ]

    if expected_versions != actual_versions:
        raise RuntimeError(
            "LawVersion 或其嵌套数据与预览数据不一致。"
        )

    print("LawVersion 及嵌套数据：一致")

    # --------------------------------------------------------
    # 5. 核对身份 ID
    # --------------------------------------------------------

    expected_law_ids = {
        item.law_id
        for item in preview["laws"]
    }

    actual_law_ids = {
        item.law_id
        for item in persisted["laws"]
    }

    if expected_law_ids != actual_law_ids:
        raise RuntimeError("Law ID 持久化前后不一致。")

    expected_version_ids = {
        item.version_id
        for item in preview["law_versions"]
    }

    actual_version_ids = {
        item.version_id
        for item in persisted["law_versions"]
    }

    if expected_version_ids != actual_version_ids:
        raise RuntimeError("LawVersion ID 持久化前后不一致。")

    expected_article_ids = {
        article.article_id
        for version in preview["law_versions"]
        for article in version.articles
    }

    actual_article_ids = {
        article.article_id
        for version in persisted["law_versions"]
        for article in version.articles
    }

    if expected_article_ids != actual_article_ids:
        raise RuntimeError("LegalArticle ID 持久化前后不一致。")

    print("Law ID：一致")
    print("LawVersion ID：一致")
    print("LegalArticle ID：一致")

    return None


# ============================================================
# 八、主流程
# ============================================================

def main():

    print("=" * 72)
    print("法律注册表正式初始化")
    print("=" * 72)

    print("项目目录：", PROJECT_ROOT)
    print("注册表路径：", REGISTRY_PATH)

    # --------------------------------------------------------
    # 1. 检查当前正式注册表
    # --------------------------------------------------------

    print()
    print("检查正式注册表当前状态……")

    current = load_registry(
        path=REGISTRY_PATH
    )

    if current["laws"] or current["law_versions"]:
        raise RuntimeError(
            "正式注册表已经包含数据，拒绝初始化。"
        )

    print("当前 Law：", len(current["laws"]))
    print("当前 LawVersion：", len(current["law_versions"]))
    print("当前状态：空注册表")

    # --------------------------------------------------------
    # 2. 构造内存预览
    # --------------------------------------------------------

    print()
    print("重新构造法律注册数据……")

    preview = build_preview_registry()

    validate_preview(preview)

    # --------------------------------------------------------
    # 3. 正式事务写入
    # --------------------------------------------------------

    print()
    print("=" * 72)
    print("开始正式事务写入")
    print("=" * 72)

    committed = initialize_registry(preview)

    print("registry_transaction 已完成。")

    # --------------------------------------------------------
    # 4. 从磁盘重新读取
    # --------------------------------------------------------

    print()
    print("重新从磁盘加载正式注册表……")

    persisted = load_registry(
        path=REGISTRY_PATH
    )

    # --------------------------------------------------------
    # 5. 完整持久化验证
    # --------------------------------------------------------

    verify_persisted_registry(
        preview,
        persisted,
    )

    # --------------------------------------------------------
    # 6. 输出结果
    # --------------------------------------------------------

    print()
    print("=" * 72)
    print("法律注册表正式初始化成功")
    print("=" * 72)

    print("注册表文件：", REGISTRY_PATH)
    print("文件存在：", REGISTRY_PATH.is_file())
    print("文件大小：", REGISTRY_PATH.stat().st_size, "bytes")

    print()
    print("本次写入对象：")

    for name, count in count_registry_objects(persisted).items():
        print(f"  {name}: {count}")

    print()
    print("身份 ID：保留预览阶段生成的值")
    print("法律核验状态：UNVERIFIED")
    print("法律效力状态：UNKNOWN")
    print("Qdrant：未修改")
    print("重复初始化保护：已启用")


if __name__ == "__main__":
    main()
