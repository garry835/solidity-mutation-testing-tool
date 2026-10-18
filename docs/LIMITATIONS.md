# Theoretical and Practical Limitations

While the Solidity Mutation Testing Framework provides rigorous test evaluation, several theoretical and engineering boundaries exist.

---

## 1. The Equivalent Mutant Problem

In mutation testing research, an **equivalent mutant** is syntactically different from the original program but functionally and semantically identical under all possible execution states and inputs.

### Manifestation in Smart Contracts
- **Dead Code Arithmetic**: An arithmetic operation on a variable bounded by previous checks (e.g., `require(a < 100); require(b < 100); a += b;`) will never overflow regardless of whether it is wrapped in an `unchecked` block. The mutant behaves identically to the original contract for all admissible transactions.
- **Redundant Boundary Checks**: Comparisons where preceding invariants preclude the boundary condition cannot be killed by any valid test case.

Because determining semantic program equivalence is undecidable in general, equivalent mutants artificially deflate the mutation score unless manually inspected and annotated.

---

## 2. Mutation Score is NOT an Absolute Security Metric

A high or even 100% mutation score indicates that the test suite successfully detects the specific syntactic and semantic faults modeled by the configured operators. **It does NOT prove that the smart contract is secure against all vulnerabilities.**

Non-modeled security vulnerabilities include:
- Logic bugs in business requirements or access control logic
- Economic exploits (e.g. flash-loan price oracle manipulation)
- Gas griefing or denial-of-service (DoS) via unbound loops
- Front-running and maximal extractable value (MEV) attacks
- Assembly/Yul memory safety errors

---

## 3. Operator Scope & Contract Architectures

1. **Cross-Contract Reentrancy**:
   The `REENTRANCY` operator targets single-contract Checks-Effects-Interactions inversions. Read-only reentrancy (where Contract A calls external code which reads stale state from Contract B) or cross-contract state synchronization issues require multi-contract dependency graphing.
2. **Compiler Version Specificity**:
   The `UNCHECKED_MATH` operator is specifically engineered for Solidity `0.8.0+`. In legacy contracts (`<0.8.0`), arithmetic was unchecked by default, requiring the `SafeMath` library.
3. **Assembly Blocks**:
   Inline Yul / assembly (`assembly { ... }`) blocks are intentionally bypassed by the high-level mutation operators to prevent invalid bytecode generation.
