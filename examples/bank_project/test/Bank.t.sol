// SPDX-License-Identifier: MIT
pragma solidity 0.8.20;

import "../src/Bank.sol";

interface Vm {
    function warp(uint256) external;
    function deal(address, uint256) external;
}

/**
 * @title BankBaselineTest
 * @notice Baseline test suite for Bank contract.
 * Focuses on happy paths and general functional assertions.
 */
contract BankBaselineTest {
    Bank internal bank;
    Vm internal constant vm = Vm(address(uint160(uint256(keccak256("hevm cheat code")))));

    function setUp() public {
        bank = new Bank();
        vm.deal(address(this), 100 ether);
    }

    function testDeposit() public {
        bank.deposit{value: 10 ether}();
        require(bank.balances(address(this)) == 10 ether, "Balance mismatch after deposit");
        require(bank.totalDeposits() == 10 ether, "Total deposits mismatch");
    }

    function testWithdrawStandard() public {
        bank.deposit{value: 20 ether}();
        bank.withdraw(5 ether);
        require(bank.balances(address(this)) == 15 ether, "Balance should be 15 ether");
        require(bank.totalDeposits() == 15 ether, "Total deposits should be 15 ether");
    }

    function testWithdrawInsufficient() public {
        bank.deposit{value: 2 ether}();
        // Attempting to withdraw 10 ether must fail
        (bool ok, ) = address(bank).call(abi.encodeWithSignature("withdraw(uint256)", 10 ether));
        require(!ok, "Should revert on insufficient balance");
    }

    function testTimelockFlow() public {
        vm.warp(1000);
        bank.deposit{value: 5 ether}();
        bank.setTimelock(500); // Release at 1500

        // Before release: call fails
        vm.warp(1200);
        (bool ok, ) = address(bank).call(abi.encodeWithSignature("withdrawLocked(uint256)", 1 ether));
        require(!ok, "Should revert before timelock release");

        // After release: call succeeds
        vm.warp(1600);
        bank.withdrawLocked(1 ether);
        require(bank.balances(address(this)) == 4 ether, "Balance should be 4 ether");
    }

    function testClaimBonusFarBeforeDeadline() public {
        vm.warp(1000);
        // Fund the bank so it has liquidity
        bank.deposit{value: 10 ether}();

        // Deadline is 2000, current timestamp is 1000
        bank.claimBonus(2000);
        // Balance increases by 1 ether bonus
        require(bank.balances(address(this)) == 11 ether, "Bonus not credited");
    }

    function testClaimBonusFarAfterDeadline() public {
        vm.warp(3000);
        bank.deposit{value: 10 ether}();

        // Deadline is 2000, current timestamp is 3000 (clearly expired)
        (bool ok, ) = address(bank).call(abi.encodeWithSignature("claimBonus(uint256)", 2000));
        require(!ok, "Bonus claim should fail after deadline");
    }

    receive() external payable {}
}
