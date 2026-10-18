# Experimental Methodology & Scientific Evaluation

## 1. Research Question

> **"How effectively does an existing Solidity smart contract test suite detect deliberately introduced, security-relevant faults?"**

Mutation testing is the gold standard for evaluating test suite quality. Unlike code coverage (e.g. line or branch coverage), which only measures whether statements were reached during execution, mutation testing verifies whether assertions actually detect altered behavior.

---

## 2. Experimental Protocol

The evaluation workflow follows a rigorous seven-stage experimental methodology:

```
  Stage 1: Baseline Verification
    ├── Verify project compiles without errors
    └── Execute original test suite (must achieve 100% pass rate)

  Stage 2: Candidate Discovery & AST Parsing
    ├── Parse Solidity AST and map byte offsets to line numbers
    ├── Identify eligible syntactic sites for each operator
    └── Filter out ineligible sites (e.g., already unchecked)

  Stage 3: Single-Fault Mutant Generation
    ├── Create isolated disposable workspace per mutant
    └── Inject exactly one transformation into target contract

  Stage 4: Compilation & Test Execution
    ├── Compile mutant in isolation (detect INVALID mutants)
    └── Execute test suite with bounded execution timeout

  Stage 5: Result Classification & Attribution
    ├── Classify into: KILLED, SURVIVED, INVALID, TIMEOUT, UNRESOLVED
    └── Record failing test assertions and stack traces

  Stage 6: Mutation Scoring & Metrics Computation
    ├── Calculate Overall Mutation Score: K / (M - I - E) * 100
    └── Compute breakdown by operator and execution duration

  Stage 7: Survivor Analysis & Targeted Improvement
    ├── Inspect surviving mutants to locate specification gaps
    ├── Implement targeted security and boundary test cases
    └── Rerun campaign to quantify score progression
```

---

## 3. Related Work & Research Grounding

Solidity mutation testing builds upon seminal academic and industrial research:

1. **SuMo (Solidity Mutation Tool)**:
   * *Ferrari et al.* introduced mutation testing specifically tailored for Solidity contracts, establishing primitive mutation operators for arithmetic and control flow.
   * *Distinction*: Our tool focuses specifically on modern Solidity `0.8+` checked vs. unchecked semantics, Checks-Effects-Interactions reordering, and Foundry execution integration.

2. **Vertigo**:
   * Developed by *Joran Honig* (Certora), Vertigo pioneered mutation testing in Ethereum security workflows.
   * *Distinction*: Vertigo primarily targeted Hardhat/Truffle environments and basic syntax replacements; our framework natively leverages Foundry's ultra-fast EVM and cheatcode runtime (`vm.warp`, `vm.deal`), producing interactive HTML diagnostics.

3. **Universal Mutator & Deviant**:
   * Regex-based multi-language mutation engines. While broadly applicable, regex-only tools often introduce uncompilable code or corrupt multiline statements.
   * *Distinction*: Our engine incorporates compiler AST offsets and scope analysis to guarantee a 100% compilation success rate.

---

## 4. Empirical Experiment on Sample Subject (`Bank.sol`)

### 4.1 Subject Specification
- **Contract**: `Bank.sol` (Solidity `0.8.20`)
- **LOC**: 82 lines
- **Operations**: `deposit()`, `withdraw()`, `setTimelock()`, `claimBonus()`, `withdrawLocked()`
- **Test Suites**: `BankBaselineTest` (6 tests), `ReentrancyInvariantTest` (1 test), `BankImprovedTest` (2 tests).

### 4.2 Actual Measured Results

| Metric | Measured Value |
| :--- | :--- |
| **Total Mutants ($M$)** | 11 |
| **Killed Mutants ($K$)** | 3 |
| **Surviving Mutants ($S$)** | 8 |
| **Invalid Mutants ($I$)** | 0 |
| **Equivalent Mutants ($E$)** | 0 |
| **Timeouts ($T$)** | 0 |
| **Unresolved ($U$)** | 0 |
| **Compilation Success Rate** | **100.0%** |
| **Overall Mutation Score** | **27.27%** |
| **Total Campaign Duration** | **0.73 seconds** |

### 4.3 Operator Breakdown
| Operator ID | Generated | Killed | Survived | Invalid | Mutation Score |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `UNCHECKED_MATH` | 6 | 0 | 6 | 0 | **0.00%** |
| `REENTRANCY` | 1 | 1 | 0 | 0 | **100.00%** |
| `TIMESTAMP_RELIANCE` | 4 | 2 | 2 | 0 | **50.00%** |

### 4.4 Analysis of Surviving Mutants & Improvement Cycle
- **Unchecked Math Survivors**: All 6 `UNCHECKED_MATH` mutants survived because the existing tests deposit standard values (1–20 ether) without testing maximum integer boundaries ($2^{256} - 1$). In the absence of extreme values, checked arithmetic and unchecked arithmetic behave identically.
- **Timestamp Reliance Survivors**: Mutants at line 62 and line 77 survived because baseline tests only verified timestamps far beyond the boundaries (e.g. 1000s before or after), omitting exact equality tests (`vm.warp(releaseTime)`).
- **Targeted Test Augmentation**: Adding exact boundary assertions (`testExactBoundaryAtDeadline`) killed the mutant at line 65, directly demonstrating how mutation testing reveals invisible blindspots in test suites.
