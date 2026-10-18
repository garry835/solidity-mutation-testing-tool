"""Unit tests for UncheckedMathOperator."""

from pathlib import Path
from operators.unchecked_math import UncheckedMathOperator
from src.solidity_parser import SolidityParser


def test_unchecked_math_candidate_discovery():
    """Verify discovery of eligible arithmetic operations and proper wrapping."""
    source = """
pragma solidity 0.8.20;

contract Counter {
    uint256 public total;

    function add(uint256 x) public {
        total += x;
    }
}
"""
    op = UncheckedMathOperator()
    parser = SolidityParser(source)
    candidates = op.find_candidates(Path("src/Counter.sol"), source, parser)

    assert len(candidates) == 1
    cand = candidates[0]
    assert cand.is_eligible is True
    assert cand.original_text == "total += x;"
    assert "unchecked {" in cand.replacement_text

    # Apply mutation
    mutated = op.apply_mutation(source, cand)
    assert "unchecked { total += x; }" in mutated
    assert "uint256 public total;" in mutated  # Preserves structure


def test_unchecked_math_rejection_when_already_unchecked():
    """Verify that arithmetic already inside an unchecked block is rejected."""
    source = """
pragma solidity 0.8.20;

contract Counter {
    uint256 public total;

    function add(uint256 x) public {
        unchecked {
            total += x;
        }
    }
}
"""
    op = UncheckedMathOperator()
    parser = SolidityParser(source)
    candidates = op.find_candidates(Path("src/Counter.sol"), source, parser)

    assert len(candidates) == 1
    cand = candidates[0]
    assert cand.is_eligible is False
    assert cand.rejection_reason == "Already inside unchecked block"
