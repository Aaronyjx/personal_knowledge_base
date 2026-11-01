# -*- coding: utf-8 -*-
"""ContractSequence 与 LegalFacts 模型运行时类型契约测试。"""

from dataclasses import replace

import pytest

from src.legal_fact_models import ContractSequence, LegalFacts


@pytest.mark.parametrize("count", [2, 3])
def test_contract_sequence_accepts_current_production_counts(count):
    sequence = ContractSequence(
        count=count,
        term_type="fixed",
        continuous=True,
    )

    assert sequence.count == count
    assert sequence.term_type == "fixed"
    assert sequence.continuous is True


@pytest.mark.parametrize("count", ["3", 3.0, True, False, None])
def test_contract_sequence_rejects_invalid_count_types(count):
    with pytest.raises(TypeError, match="count"):
        ContractSequence(
            count=count,
            term_type="fixed",
            continuous=True,
        )


@pytest.mark.parametrize("term_type", [None, 1, {"value": "fixed"}])
def test_contract_sequence_rejects_invalid_term_type(term_type):
    with pytest.raises(TypeError, match="term_type"):
        ContractSequence(
            count=3,
            term_type=term_type,
            continuous=True,
        )


@pytest.mark.parametrize("continuous", ["true", 1, 0, None])
def test_contract_sequence_rejects_invalid_continuous_type(continuous):
    with pytest.raises(TypeError, match="continuous"):
        ContractSequence(
            count=3,
            term_type="fixed",
            continuous=continuous,
        )


def test_legal_facts_accepts_none_contract_sequence():
    facts = LegalFacts(contract_sequence=None)

    assert facts.contract_sequence is None


def test_legal_facts_accepts_valid_contract_sequence():
    sequence = ContractSequence(
        count=3,
        term_type="fixed",
        continuous=True,
    )

    facts = LegalFacts(contract_sequence=sequence)

    assert facts.contract_sequence is sequence


@pytest.mark.parametrize(
    "invalid_sequence",
    [
        {},
        {"count": 3, "term_type": "fixed", "continuous": True},
        object(),
        "contract sequence",
        3,
    ],
)
def test_legal_facts_rejects_invalid_contract_sequence_object(
    invalid_sequence,
):
    with pytest.raises(TypeError, match="contract_sequence"):
        LegalFacts(contract_sequence=invalid_sequence)


def test_dataclasses_replace_preserves_valid_contract_sequence():
    sequence = ContractSequence(
        count=3,
        term_type="fixed",
        continuous=True,
    )

    original = LegalFacts(
        contract_sequence=sequence,
        completed_renewal=None,
    )

    updated = replace(
        original,
        completed_renewal=True,
    )

    assert updated is not original
    assert updated.contract_sequence is sequence
    assert updated.completed_renewal is True
    assert original.completed_renewal is None


def test_dataclasses_replace_rejects_invalid_contract_sequence():
    original = LegalFacts(
        contract_sequence=ContractSequence(
            count=3,
            term_type="fixed",
            continuous=True,
        )
    )

    with pytest.raises(TypeError, match="contract_sequence"):
        replace(
            original,
            contract_sequence={"count": 3},
        )
