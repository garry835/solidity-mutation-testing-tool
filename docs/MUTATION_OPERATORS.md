# Solidity Mutation Operators Specification

This document provides formal specifications for the three core security-oriented mutation operators implemented in the framework.

---

## Operator 1: Unchecked Arithmetic (`UNCHECKED_MATH`)

### 1. Identifier
- **Operator ID**: `UNCHECKED_MATH`
- **Aliases**: `unchecked_math`, `unchecked`, `math`

### 2. Purpose and Fault Model
In Solidity `0.8.0` and above, integer arithmetic is checked by default; operations that overflow or underflow automatically revert with an arithmetic panic (`0x11`). Developers frequently wrap arithmetic in `unchecked { ... }` blocks for gas optimization under the assumption that invariants guarantee values remain within range.

The `UNCHECKED_MATH` operator simulates the omission of checked arithmetic or an erroneous `unchecked` gas optimization. It tests whether the existing test suite exercises boundary conditions (e.g., values exceeding $2^{256} - 1$ or falling below 0) to verify safe accounting.

### 3. Preconditions & Rejection Criteria
- **Precondition**: The target contract must target Solidity `0.8.0` or higher.
- **Rejection Rule**: If the arithmetic statement is already located inside an existing `unchecked { ... }` block, the candidate is **rejected** with reason `"Already inside unchecked block"`.
- **Rejection Rule**: Constant expressions, variable declarations without side effects, and string/comment literals are excluded.

### 4. Transformation Example
**Original:**
```solidity
function deposit() public payable {
    balances[msg.sender] += msg.value;
    totalDeposits += msg.value;
}
```

**Mutated:**
```solidity
function deposit() public payable {
    unchecked { balances[msg.sender] += msg.value; }
    unchecked { totalDeposits += msg.value; }
}
```

---

## Operator 2: Reentrancy (`REENTRANCY`)

### 1. Identifier
- **Operator ID**: `REENTRANCY`
- **Aliases**: `reentrancy`, `reentrant`

### 2. Purpose and Fault Model
The Checks-Effects-Interactions (CEI) design pattern dictates that all internal state updates must occur before any external call or ether transfer. Violations of this pattern create a reentrancy window where a malicious recipient contract can re-enter the caller while contract state is stale.

The `REENTRANCY` operator targets withdrawal or payment functions that adhere to CEI and inverts the ordering: the external interaction is moved **before** the state balance update. This evaluates whether the test suite includes reentrancy invariant assertions or attacker contracts capable of detecting delayed accounting updates.

### 3. Preconditions & Rejection Criteria
- **Precondition**: An external call (`call{value:...}`, `transfer`, or `send`) must be preceded by one or more state updates (e.g. balance deduction or flag clearing) in the same function scope.
- **Rejection Rule**: If the external call has a direct data dependency on the modified state variable (such that reordering produces structurally invalid or uncompilable Solidity), the transformation is rejected.

### 4. Transformation Example
**Original (Checks-Effects-Interactions):**
```solidity
require(balances[msg.sender] >= amount, "Insufficient balance");

balances[msg.sender] -= amount;
totalDeposits -= amount;

(bool success, ) = payable(msg.sender).call{value: amount}("");
require(success, "Transfer failed");
```

**Mutated (Reentrancy Window Exposed):**
```solidity
require(balances[msg.sender] >= amount, "Insufficient balance");

(bool success, ) = payable(msg.sender).call{value: amount}("");
require(success, "Transfer failed");

balances[msg.sender] -= amount;
totalDeposits -= amount;
```

---

## Operator 3: Timestamp Reliance (`TIMESTAMP_RELIANCE`)

### 1. Identifier
- **Operator ID**: `TIMESTAMP_RELIANCE`
- **Aliases**: `timestamp_reliance`, `timestamp`, `time`

### 2. Purpose and Fault Model
Smart contracts frequently rely on `block.timestamp` for time-locks, auctions, deadline enforcement, and vesting schedules. Common software bugs arise from off-by-one boundary comparisons (e.g., using `<=` instead of `<`) or incorrect offset arithmetic.

The `TIMESTAMP_RELIANCE` operator injects boundary-condition mutations into expressions evaluating `block.timestamp`. This determines whether test suites test exact boundary timestamps (`vm.warp(deadline)`) versus only times far in the past or future.

### 3. Preconditions & Rejection Criteria
- **Precondition**: The comparison expression must contain `block.timestamp` and an operator from the set $\{<, <=, >, >=, ==, !=\}$, or a timelock addition calculation `block.timestamp + duration`.
- **Rejection Rule**: Timestamp occurrences in comments or logging strings are excluded.

### 4. Comparison Mutation Mapping
| Original Comparison | Injected Mutation | Security Context |
| :--- | :--- | :--- |
| `block.timestamp < deadline` | `block.timestamp <= deadline` | Permits execution at the exact deadline boundary |
| `block.timestamp <= deadline` | `block.timestamp < deadline` | Rejects valid transactions arriving at the deadline |
| `block.timestamp > releaseTime` | `block.timestamp >= releaseTime` | Relaxes timelock enforcement by one second |
| `block.timestamp >= releaseTime` | `block.timestamp > releaseTime` | Stricter timelock requirement |
| `block.timestamp + duration` | `block.timestamp - duration` | Inverts future release lock to the past |

### 5. Transformation Example
**Original:**
```solidity
function claimBonus(uint256 deadline) public {
    require(block.timestamp < deadline, "Deadline passed");
    ...
}
```

**Mutated:**
```solidity
function claimBonus(uint256 deadline) public {
    require(block.timestamp <= deadline, "Deadline passed");
    ...
}
```
