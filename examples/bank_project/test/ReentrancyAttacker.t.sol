// SPDX-License-Identifier: MIT
pragma solidity 0.8.20;

import "../src/Bank.sol";

interface Vm {
    function deal(address, uint256) external;
}

/**
 * @title ReentrancyAttacker
 * @notice Recipient contract that asserts Checks-Effects-Interactions invariant
 * during external calls from Bank.withdraw().
 */
contract ReentrancyAttacker {
    Bank public immutable targetBank;
    bool public attacked;

    constructor(address _target) {
        targetBank = Bank(payable(_target));
    }

    function deposit() external payable {
        targetBank.deposit{value: msg.value}();
    }

    function initiateWithdraw(uint256 amount) external {
        targetBank.withdraw(amount);
    }

    receive() external payable {
        // Checks-Effects-Interactions Invariant:
        // When Bank makes an external call to recipient, the caller's balance
        // must already have been decremented. If delayed (reentrancy flaw), balance remains positive.
        uint256 remainingBalance = targetBank.balances(address(this));
        require(
            remainingBalance == 0,
            "Reentrancy invariant violated: balance was not decremented before external call!"
        );
    }
}

/**
 * @title ReentrancyInvariantTest
 * @notice Tests whether Bank maintains the Checks-Effects-Interactions invariant
 * to prevent reentrancy window exploits.
 */
contract ReentrancyInvariantTest {
    Bank internal bank;
    ReentrancyAttacker internal attacker;
    Vm internal constant vm = Vm(address(uint160(uint256(keccak256("hevm cheat code")))));

    function setUp() public {
        bank = new Bank();
        attacker = new ReentrancyAttacker(address(bank));

        // Fund test contract
        vm.deal(address(this), 20 ether);

        // Victim deposits 10 ether
        bank.deposit{value: 10 ether}();

        // Attacker deposits 1 ether
        attacker.deposit{value: 1 ether}();
    }

    function testReentrancyDefense() public {
        // Attacker initiates full withdrawal of its 1 ether deposit
        // Under CEI: balance is decremented to 0 BEFORE call -> receive() check passes.
        // Under Reentrancy mutant: call occurs BEFORE decrement -> receive() check reverts!
        attacker.initiateWithdraw(1 ether);
        require(bank.balances(address(attacker)) == 0, "Attacker balance should be 0");
    }

    receive() external payable {}
}
