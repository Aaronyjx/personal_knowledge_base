from src.legal_decision_engine import DecisionResult


def build_decision_result():
    """构造包含嵌套结构化引用的最小 DecisionResult。"""

    runtime_rule = {
        "rule_id": "RULE-TEST-REFERENCE-001",
        "references": [
            {
                "reference_id": (
                    "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"
                ),
                "rule_id": "RULE-TEST-REFERENCE-001",
                "article_id": (
                    "11111111-2222-4333-8444-555555555555"
                ),
                "reference_type": "PRIMARY",
                "legal_role": "主要法律依据",
                "location": {
                    "paragraph_number": 2,
                    "item_number": 1,
                    "subitem_number": None,
                },
            }
        ],
    }

    return DecisionResult(
        decision="CONDITIONAL",
        condition_results=[],
        explicit_facts=[],
        contract_sequence=None,
        rule_dependencies=[],
        selected_rule=runtime_rule,
        explanation="对象隔离回归测试",
    )


def test_to_dict_preserves_structured_references():
    """验证 to_dict() 保留完整结构化引用。"""

    decision = build_decision_result()
    result = decision.to_dict()

    assert (
        result["selected_rule"]["references"]
        == decision.selected_rule["references"]
    )


def test_to_dict_selected_rule_is_deepcopy():
    """验证 to_dict() 输出与原始规则深度隔离。"""

    decision = build_decision_result()
    result = decision.to_dict()

    assert result["selected_rule"] is not decision.selected_rule

    assert (
        result["selected_rule"]["references"]
        is not decision.selected_rule["references"]
    )

    assert (
        result["selected_rule"]["references"][0]
        is not decision.selected_rule["references"][0]
    )

    assert (
        result["selected_rule"]["references"][0]["location"]
        is not decision.selected_rule["references"][0]["location"]
    )

    result["selected_rule"]["references"][0]["location"][
        "item_number"
    ] = 99

    assert (
        decision.selected_rule["references"][0]["location"][
            "item_number"
        ] == 1
    )
