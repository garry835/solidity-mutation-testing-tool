// SPDX-License-Identifier: MIT
pragma solidity 0.8.20;

/**
 * @title Bank
 * @notice Realistic vault and balance accounting contract used as a subject
 * for mutation testing experiments.
 */
contract Bank {
    mapping(address => uint256) public balances;
    mapping(address => uint256) public lockReleaseTimes;
    uint256 public totalDeposits;
    address public owner;

    event Deposited(address indexed account, uint256 amount);
    event Withdrawn(address indexed account, uint256 amount);
    event TimelockSet(address indexed account, uint256 releaseTime);
    event BonusClaimed(address indexed account, uint256 bonus);

    constructor() {
        owner = msg.sender;
    }

    /**
     * @notice Deposit funds into the bank.
     */
    function deposit() public payable {
        require(msg.value > 0, "Deposit must be positive");
        balances[msg.sender] += msg.value;
        totalDeposits += msg.value;
        emit Deposited(msg.sender, msg.value);
    }

    /**
     * @notice Standard withdrawal adhering strictly to Checks-Effects-Interactions.
     * @param amount The amount to withdraw in wei.
     */
    function withdraw(uint256 amount) public {
        require(amount > 0, "Withdraw must be positive");
        require(balances[msg.sender] >= amount, "Insufficient balance");

        balances[msg.sender] -= amount;
        totalDeposits -= amount;

        (bool success, ) = payable(msg.sender).call{value: amount}("");
        require(success, "Transfer failed");

        emit Withdrawn(msg.sender, amount);
    }

    /**
     * @notice Set a lock duration for the caller's account.
     */
    function setTimelock(uint256 duration) public {
        require(duration > 0, "Duration must be positive");
        lockReleaseTimes[msg.sender] = block.timestamp + duration;
        emit TimelockSet(msg.sender, lockReleaseTimes[msg.sender]);
    }

    /**
     * @notice Claim a promotional bonus before the strict deadline.
     * Must be called strictly before the deadline (block.timestamp < deadline).
     */
    function claimBonus(uint256 deadline) public {
        require(block.timestamp < deadline, "Deadline passed");
        uint256 bonus = 1 ether;
        require(address(this).balance >= bonus, "Insufficient bank funds");
        balances[msg.sender] += bonus;
        totalDeposits += bonus;
        emit BonusClaimed(msg.sender, bonus);
    }

    /**
     * @notice Emergency unlock requiring the timelock to be strictly reached or passed.
     */
    function withdrawLocked(uint256 amount) public {
        require(block.timestamp >= lockReleaseTimes[msg.sender], "Lock active");
        withdraw(amount);
    }

    receive() external payable {
        deposit();
    }
}
