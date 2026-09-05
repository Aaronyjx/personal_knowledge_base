# src/law_metadata.py
# -*- coding: utf-8 -*-

"""
个人法律知识库
Law Metadata V5.2

功能：
1. 统一法律元数据 Schema
2. 区分“名称字段”和“数值评分字段”
3. 支持法律层级
4. 支持现行有效状态
5. 支持专门性
6. 支持具体性
7. 支持法律优先级
8. 为 Reranker 提供稳定的数据结构

V5.2 重点修复：
V5.1 中 speciality 字段同时被当作：
    "劳动合同专项法律"
和：
    1.0

导致：

ValueError:
could not convert string to float: '劳动合同专项法律'

V5.2 将字段彻底拆分：
    specialty_name
    specialty_score
"""

from dataclasses import dataclass, asdict
from typing import Dict, Any


# ============================================================
# 法律元数据 Schema
# ============================================================

@dataclass
class LawMetadata:
    """
    单部法律的结构化元数据。
    """

    # --------------------------------------------------------
    # 基础信息
    # --------------------------------------------------------

    law_name: str

    # 法律层级：
    # 法律
    # 行政法规
    # 部门规章
    # 地方性法规
    # 地方政府规章
    # 司法解释
    # 未知
    law_level: str

    # --------------------------------------------------------
    # 权威性
    # --------------------------------------------------------

    authority_score: float

    # --------------------------------------------------------
    # 效力状态
    # --------------------------------------------------------

    validity_status: str

    validity_score: float

    # --------------------------------------------------------
    # 专门法
    # --------------------------------------------------------

    # 注意：
    # 这是“名称”，不能参与 float()
    #
    # 例如：
    # 劳动合同专项法律
    # 一般劳动法
    # 劳动合同专项行政法规
    specialty_name: str

    # 专门性评分
    specialty_score: float

    # --------------------------------------------------------
    # 具体性
    # --------------------------------------------------------

    specificity_score: float

    # --------------------------------------------------------
    # 基础法律优先级
    # --------------------------------------------------------

    base_priority: float

    # --------------------------------------------------------
    # 综合法律优先级
    # --------------------------------------------------------

    priority_score: float


# ============================================================
# 工具函数
# ============================================================

def _clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    """
    将评分限制在 0~1。
    """

    try:
        value = float(value)
    except (TypeError, ValueError):
        value = 0.0

    return max(minimum, min(maximum, value))


# ============================================================
# 法律元数据数据库
# ============================================================

LAW_METADATA: Dict[str, LawMetadata] = {

    # --------------------------------------------------------
    # 劳动法
    # --------------------------------------------------------

    "中华人民共和国劳动法": LawMetadata(
        law_name="中华人民共和国劳动法",
        law_level="法律",

        authority_score=0.95,

        validity_status="现行有效",
        validity_score=1.00,

        specialty_name="一般劳动法",
        specialty_score=0.80,

        specificity_score=0.80,

        base_priority=0.08,

        priority_score=0.87,
    ),

    # --------------------------------------------------------
    # 劳动合同法
    # --------------------------------------------------------

    "中华人民共和国劳动合同法": LawMetadata(
        law_name="中华人民共和国劳动合同法",
        law_level="法律",

        authority_score=0.95,

        validity_status="现行有效",
        validity_score=1.00,

        specialty_name="劳动合同专项法律",
        specialty_score=1.00,

        specificity_score=1.00,

        base_priority=0.10,

        priority_score=0.93,
    ),

    # --------------------------------------------------------
    # 劳动合同法实施条例
    # --------------------------------------------------------

    "中华人民共和国劳动合同法实施条例": LawMetadata(
        law_name="中华人民共和国劳动合同法实施条例",
        law_level="行政法规",

        authority_score=0.85,

        validity_status="现行有效",
        validity_score=1.00,

        specialty_name="劳动合同专项行政法规",
        specialty_score=1.00,

        specificity_score=1.00,

        base_priority=0.09,

        priority_score=0.88,
    ),
}


# ============================================================
# 未知法律默认元数据
# ============================================================

UNKNOWN_LAW_METADATA = LawMetadata(
    law_name="未知法律文件",
    law_level="未知",

    authority_score=0.50,

    validity_status="未知",
    validity_score=0.50,

    specialty_name="未知",
    specialty_score=0.50,

    specificity_score=0.50,

    base_priority=0.00,

    priority_score=0.425,
)


# ============================================================
# 获取法律元数据
# ============================================================

def get_law_metadata(law_name: str) -> LawMetadata:
    """
    根据法律名称获取结构化元数据。

    未找到时返回 UNKNOWN_LAW_METADATA。
    """

    if not law_name:
        return UNKNOWN_LAW_METADATA

    return LAW_METADATA.get(
        law_name,
        UNKNOWN_LAW_METADATA
    )


# ============================================================
# 转换为 Dict
# ============================================================

def get_law_metadata_dict(law_name: str) -> Dict[str, Any]:
    """
    返回普通 dict。

    方便 reranker.py 使用。
    """

    metadata = get_law_metadata(law_name)

    return asdict(metadata)


# ============================================================
# 根据元数据计算排序加分
# ============================================================

def calculate_metadata_boost(law_name: str) -> Dict[str, float]:
    """
    返回 Reranker 使用的法律元数据加分。

    注意：
    这里返回的全部字段均为 float。
    """

    metadata = get_law_metadata(law_name)

    return {
        "current_law": round(
            metadata.validity_score * 0.03,
            4
        ),

        "authority": round(
            metadata.authority_score * 0.02,
            4
        ),

        "specificity": round(
            metadata.specificity_score * 0.02,
            4
        ),

        "specialty": round(
            metadata.specialty_score * 0.02,
            4
        ),

        "law_priority": round(
            metadata.priority_score * 0.10,
            4
        ),
    }


# ============================================================
# 打印单部法律
# ============================================================

def print_law_metadata(law_name: str) -> None:

    metadata = get_law_metadata(law_name)

    print("-" * 70)

    print("法律名称：", metadata.law_name)
    print("法律层级：", metadata.law_level)

    print("权威分数：", metadata.authority_score)

    print("效力状态：", metadata.validity_status)
    print("效力分数：", metadata.validity_score)

    print("专门法：", metadata.specialty_name)
    print("专门性：", metadata.specialty_score)

    print("具体性：", metadata.specificity_score)

    print("基础优先级：", metadata.base_priority)
    print("综合法律优先级：", metadata.priority_score)


# ============================================================
# 自检
# ============================================================

def validate_metadata() -> bool:
    """
    检查所有评分字段是否都是 float，
    防止 V5.1 的字符串/数字混用问题再次发生。
    """

    numeric_fields = [
        "authority_score",
        "validity_score",
        "specialty_score",
        "specificity_score",
        "base_priority",
        "priority_score",
    ]

    for law_name, metadata in LAW_METADATA.items():

        for field_name in numeric_fields:

            value = getattr(metadata, field_name)

            if not isinstance(value, (int, float)):
                raise TypeError(
                    f"{law_name} -> {field_name} "
                    f"必须是数字，实际类型：{type(value)}"
                )

    return True


# ============================================================
# 测试
# ============================================================

def main():

    print("=" * 70)
    print("个人法律知识库")
    print("Law Metadata V5.2")
    print("=" * 70)

    print()

    validate_metadata()

    test_laws = [
        "中华人民共和国劳动法",
        "中华人民共和国劳动合同法",
        "中华人民共和国劳动合同法实施条例",
        "未知法律文件",
    ]

    for law_name in test_laws:

        print_law_metadata(law_name)

    print()

    print("=" * 70)
    print("Schema 自检")
    print("=" * 70)

    for law_name in LAW_METADATA:

        metadata = get_law_metadata(law_name)

        print(
            f"✅ {law_name} "
            f"→ level={metadata.law_level}, "
            f"specialty={metadata.specialty_name}, "
            f"priority={metadata.priority_score}"
        )

    print()

    print("=" * 70)
    print("Law Metadata V5.2 测试完成")
    print("=" * 70)


if __name__ == "__main__":
    main()