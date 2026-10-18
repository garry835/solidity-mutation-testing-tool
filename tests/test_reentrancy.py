"""Unit tests for ReentrancyOperator."""

from pathlib import Path
from operators.reentrancy import ReentrancyOperator
from src.solidity_parser import SolidityParser


def test_reentrancy_candidate_and_transformation():
    """Verify detection of Checks-Effects-Interactions and inversion to create reentrancy."""
    source = """
pragma solidity 0.8.20;

contract Vault {
    mapping(address => uint256) public balances;

    function withdraw(uint256 amount) public {
        require(balances[msg.sender] >= amount);
        balances[msg.sender] -= amount;
        (bool success, ) = payable(msg.sender).call{value: amount}("");
        require(success, "Transfer failed");
    }
}
"""
    op = ReentrancyOperator()
    parser = SolidityParser(source)
    candidates = op.find_candidates(Path("src/Vault.sol"), source, parser)

    assert len(candidates) == 1
    cand = candidates[0]
    assert cand.is_eligible is True
    assert "balances[msg.sender] -= amount;" in cand.original_text

    mutated = op.apply_mutation(source, cand)
    # External call must now appear BEFORE the balance deduction
    call_idx = mutated.find("payable(msg.sender).call")
    update_idx = mutated.find("balances[msg.sender] -= amount;")
    assert call_idx != -1
    assert update_idx != -1
    assert call_idx < update_idx


def test_reentrancy_no_candidate_without_preceding_update():
    """Verify that external call without preceding state update is not mutated."""
    source = """
pragma solidity 0.8.20;

contract SimplePay {
    function pay(address recipient, uint256 amount) public {
        require(amount > 0);
        (bool success, ) = payable(recipient).call{value: amount}("");
        require(success);
    }
}
"""
    op = ReentrancyOperator()
    parser = SolidityParser(source)
    candidates = op.find_candidates(Path("src/SimplePay.sol"), source, parser)
    assert len(candidates) == 0
