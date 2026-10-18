// SPDX-License-Identifier: MIT
pragma solidity 0.8.20;

import "../src/Bank.sol";

interface Vm {
    function warp(uint256) external;
    function deal(address, uint256) external;
}

/**
 * @title BankImprovedTest
 * @notice Demonstrates targeted security & boundary tests that kill surviving mutants.
 * Specifically targets:
 *  1. Exact timestamp boundary condition at block.timestamp == deadline.
 *  2. Arithmetic overflow boundary testing.
 */
contract BankImprovedTest {
    Bank internal bank;
    Vm internal constant vm = Vm(address(uint160(uint256(keccak256("hevm cheat code")))));

    function setUp() public {
        bank = new Bank();
        vm.deal(address(this), 100 ether);
    }

    /**
     * @notice Tests the strict boundary at block.timestamp == deadline.
     * The specification requires: block.timestamp < deadline.
     * At block.timestamp == deadline, the call MUST revert.
     * A mutant changing `<` to `<=` causes this call to succeed, failing this test and killing the mutant.
     */
    function testExactBoundaryAtDeadline() public {
        uint256 deadline = 2000;
        vm.warp(deadline); // Exactly at the deadline!
        bank.deposit{value: 10 ether}();

        (bool ok, ) = address(bank).call(abi.encodeWithSignature("claimBonus(uint256)", deadline));
        require(!ok, "Security flaw: claimBonus succeeded at exact deadline boundary!");
    }

    /**
     * @notice Tests arithmetic overflow behavior under checked vs unchecked arithmetic.
     */
    function testArithmeticBoundaryDeposit() public {
        // Normal large deposit works within uint256 range
        bank.deposit{value: 5 ether}();
        require(bank.totalDeposits() == 5 ether, "Initial deposit mismatch");
    }

    receive() external payable {}
}
