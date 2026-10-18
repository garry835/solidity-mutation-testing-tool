"""Unit tests for TimestampRelianceOperator."""

from pathlib import Path
from operators.timestamp_reliance import TimestampRelianceOperator
from src.solidity_parser import SolidityParser


def test_timestamp_boundary_mutation():
    """Verify mutation of boundary comparisons involving block.timestamp."""
    source = """
pragma solidity 0.8.20;

contract Auction {
    function bid(uint256 deadline) public {
        require(block.timestamp < deadline, "Auction ended");
    }
}
"""
    op = TimestampRelianceOperator()
    parser = SolidityParser(source)
    candidates = op.find_candidates(Path("src/Auction.sol"), source, parser)

    assert len(candidates) == 1
    cand = candidates[0]
    assert cand.is_eligible is True
    assert cand.original_text == "block.timestamp < deadline"
    assert cand.replacement_text == "block.timestamp <= deadline"

    mutated = op.apply_mutation(source, cand)
    assert "require(block.timestamp <= deadline, \"Auction ended\");" in mutated


def test_timestamp_calculation_mutation():
    """Verify mutation of timelock addition expressions."""
    source = """
pragma solidity 0.8.20;

contract Timelock {
    uint256 public releaseTime;
    function set(uint256 duration) public {
        releaseTime = block.timestamp + duration;
    }
}
"""
    op = TimestampRelianceOperator()
    parser = SolidityParser(source)
    candidates = op.find_candidates(Path("src/Timelock.sol"), source, parser)

    assert len(candidates) == 1
    cand = candidates[0]
    assert cand.replacement_text == "block.timestamp - duration"
    mutated = op.apply_mutation(source, cand)
    assert "releaseTime = block.timestamp - duration;" in mutated
