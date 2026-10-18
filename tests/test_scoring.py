"""Unit tests for ScoringEngine."""

from src.mutant_model import Mutant, MutationStatus
from src.scoring import ScoringEngine


def test_mutation_score_standard_formula():
    """Verify standard formula: K / (M - I - E) * 100."""
    mutants = [
        Mutant("M1", "UNCHECKED_MATH", "B.sol", 1, "h", "h", {}, "", MutationStatus.KILLED, compilation_success=True),
        Mutant("M2", "UNCHECKED_MATH", "B.sol", 2, "h", "h", {}, "", MutationStatus.SURVIVED, compilation_success=True),
        Mutant("M3", "REENTRANCY", "B.sol", 3, "h", "h", {}, "", MutationStatus.INVALID, compilation_success=False),
        Mutant("M4", "REENTRANCY", "B.sol", 4, "h", "h", {}, "", MutationStatus.KILLED, compilation_success=True),
    ]
    # M = 4, K = 2, I = 1, E = 0.
    # Score = 2 / (4 - 1 - 0) * 100 = 2 / 3 * 100 = 66.67%
    metrics = ScoringEngine.calculate(mutants, total_candidates=4, rejected_candidates=0)
    assert metrics.total_mutants == 4
    assert metrics.killed == 2
    assert metrics.survived == 1
    assert metrics.invalid == 1
    assert metrics.mutation_score == 66.67
    assert metrics.compilation_success_rate == 75.0


def test_zero_denominator_handling():
    """Verify that zero denominator (e.g., all mutants invalid) does not divide by zero."""
    mutants = [
        Mutant("M1", "UNCHECKED_MATH", "B.sol", 1, "h", "h", {}, "", MutationStatus.INVALID, compilation_success=False),
        Mutant("M2", "UNCHECKED_MATH", "B.sol", 2, "h", "h", {}, "", MutationStatus.INVALID, compilation_success=False),
    ]
    metrics = ScoringEngine.calculate(mutants, total_candidates=2, rejected_candidates=0)
    assert metrics.total_mutants == 2
    assert metrics.invalid == 2
    assert metrics.mutation_score == 0.0


def test_operator_score_breakdown():
    """Verify per-operator score computation."""
    mutants = [
        Mutant("M1", "OP_A", "B.sol", 1, "h", "h", {}, "", MutationStatus.KILLED, compilation_success=True),
        Mutant("M2", "OP_B", "B.sol", 2, "h", "h", {}, "", MutationStatus.SURVIVED, compilation_success=True),
    ]
    metrics = ScoringEngine.calculate(mutants, total_candidates=2, rejected_candidates=0)
    assert "OP_A" in metrics.operator_scores
    assert "OP_B" in metrics.operator_scores
    assert metrics.operator_scores["OP_A"].mutation_score == 100.0
    assert metrics.operator_scores["OP_B"].mutation_score == 0.0
