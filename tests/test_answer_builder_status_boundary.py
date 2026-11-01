# -*- coding: utf-8 -*-

"""
Answer Builder Status Boundary Regression Tests

测试目标：
1. 缺失 status 的 ConditionResult 必须被拒绝。
2. 非法 status 必须被拒绝。
3. 合法 UNKNOWN 必须保持 UNKNOWN。
4. ConditionView 的字段与序列化接口保持兼容。
"""

from dataclasses import fields
from types import SimpleNamespace

import pytest

from src.legal_constants import (
    SATISFIED,
    NOT_SATISFIED,
    UNKNOWN,
    REQUIRED,
)
from src.legal_answer_builder import (
    ConditionView,
    _condition_to_view,
)


def make_condition_result(**overrides):
    """创建最小的测试 ConditionResult 对象。"""
    values = {
        "condition_id": "TEST-REQUIRED-001",
        "condition": "测试法律条件",
        "status": UNKNOWN,
        "reason": "状态边界测试",
        "condition_type": REQUIRED,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_unknown_status_is_preserved():
    """合法 UNKNOWN 必须原样保留。"""
    view = _condition_to_view(
        make_condition_result(status=UNKNOWN)
    )

    assert view.status == UNKNOWN
    assert view.to_dict()["status"] == UNKNOWN


@pytest.mark.parametrize(
    "status",
    [SATISFIED, NOT_SATISFIED],
)
def test_definitive_status_is_preserved(status):
    """合法确定状态必须原样保留。"""
    view = _condition_to_view(
        make_condition_result(status=status)
    )

    assert view.status == status
    assert view.to_dict()["status"] == status


def test_missing_status_is_rejected():
    """缺失 status 不得被静默转换为 UNKNOWN。"""
    result = make_condition_result()
    del result.status

    with pytest.raises(ValueError):
        _condition_to_view(result)


def test_invalid_status_is_rejected():
    """非法状态不得进入 ConditionView。"""
    with pytest.raises(ValueError):
        _condition_to_view(
            make_condition_result(status="INVALID_STATUS")
        )


def test_condition_view_legacy_fields_are_preserved():
    """保持 ConditionView 的字段和字典接口。"""
    assert [item.name for item in fields(ConditionView)] == [
        "condition_id",
        "condition",
        "status",
        "reason",
        "condition_type",
    ]

    view = ConditionView(
        condition_id="TEST-REQUIRED-001",
        condition="测试法律条件",
        status=UNKNOWN,
        reason="状态边界测试",
        condition_type=REQUIRED,
    )

    assert view.type == REQUIRED
    assert view.to_dict() == {
        "condition_id": "TEST-REQUIRED-001",
        "condition": "测试法律条件",
        "status": UNKNOWN,
        "reason": "状态边界测试",
        "condition_type": REQUIRED,
        "type": REQUIRED,
    }


# RAW_STATUS_EXACT_VALIDATION_REGRESSION_TESTS

@pytest.mark.parametrize(
    "status",
    [
        " UNKNOWN ",
        " SATISFIED ",
        "NOT_SATISFIED ",
    ],
)
def test_condition_view_rejects_whitespace_status(status):
    """ConditionView 不得把首尾带空格的状态清洗成合法状态。"""
    with pytest.raises(ValueError, match="ConditionResult.status 非法"):
        _condition_to_view(
            make_condition_result(status=status)
        )

# ============================================================
# RAW_IDENTITY_AND_TYPE_EXACT_VALIDATION_TESTS
# ============================================================

@pytest.mark.parametrize(
    "condition_id",
    [
        " TEST-REQUIRED-001",
        "TEST-REQUIRED-001 ",
        "",
        None,
        123,
    ],
)
def test_condition_view_rejects_invalid_raw_condition_id(condition_id):
    """condition_id 不得被清洗、转换或默认补全。"""
    with pytest.raises(ValueError, match="condition_id 非法"):
        _condition_to_view(
            make_condition_result(condition_id=condition_id)
        )


@pytest.mark.parametrize(
    "condition",
    [
        " 测试法律条件",
        "测试法律条件 ",
        "",
        None,
        123,
    ],
)
def test_condition_view_rejects_invalid_raw_condition(condition):
    """condition 不得通过 safe_text() 清洗成合法文本。"""
    with pytest.raises(ValueError, match="condition 非法"):
        _condition_to_view(
            make_condition_result(condition=condition)
        )


@pytest.mark.parametrize(
    "condition_type",
    [
        " REQUIRED ",
        "required",
        "",
        "UNKNOWN_TYPE",
        None,
        123,
    ],
)
def test_condition_view_rejects_invalid_raw_condition_type(condition_type):
    """condition_type 必须是原始规范枚举值。"""
    with pytest.raises(ValueError, match="condition_type 非法"):
        _condition_to_view(
            make_condition_result(condition_type=condition_type)
        )


def test_condition_view_preserves_valid_raw_identity_fields():
    """规范的原始身份、文本和分类字段必须原样保留。"""
    original = make_condition_result(
        condition_id="TEST-REQUIRED-001",
        condition="测试法律条件",
        condition_type=REQUIRED,
    )

    view = _condition_to_view(original)

    assert view.condition_id == "TEST-REQUIRED-001"
    assert view.condition == "测试法律条件"
    assert view.condition_type == REQUIRED
