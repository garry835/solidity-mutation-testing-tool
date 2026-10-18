"""Unit tests for MutationEngine."""

from pathlib import Path
import pytest

from src.exceptions import BaselineVerificationError
from src.mutation_engine import MutationEngine


def test_mutation_engine_operator_filtering():
    """Verify that specifying operators limits the engine to only those operators."""
    bank_path = Path("examples/bank_project").resolve()
    engine = MutationEngine(
        project_path=bank_path,
        operator_names=["reentrancy"]
    )
    assert len(engine.operators) == 1
    assert engine.operators[0].operator_id == "REENTRANCY"

    candidates = engine.discover_candidates()
    assert all(c.operator_id == "REENTRANCY" for c in candidates)


def test_mutation_engine_multiple_operator_selection():
    """Verify that multiple operators can be selected simultaneously."""
    bank_path = Path("examples/bank_project").resolve()
    engine = MutationEngine(
        project_path=bank_path,
        operator_names=["reentrancy", "timestamp_reliance"]
    )
    assert len(engine.operators) == 2
    op_ids = {op.operator_id for op in engine.operators}
    assert op_ids == {"REENTRANCY", "TIMESTAMP_RELIANCE"}
