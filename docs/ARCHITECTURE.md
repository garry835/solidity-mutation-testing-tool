# Mutation Engine Architecture

## 1. System Overview

The **Solidity Mutation Testing Framework** evaluates the fault-detection capability of smart contract test suites by systematically injecting controlled, security-relevant bug operators into Solidity contracts and measuring whether the existing test suite fails (kills) or passes (survives).

```
                      +-----------------------------+
                      |   Target Solidity Project   |
                      | (Sources, Tests, foundry.toml)|
                      +--------------+--------------+
                                     |
                                     v
                      +-----------------------------+
                      |       ProjectLoader         |
                      | - Validates directories     |
                      | - Computes SHA-256 hashes   |
                      +--------------+--------------+
                                     |
                                     v
                      +-----------------------------+
                      |    Baseline Verification    |
                      | - forge build               |
                      | - forge test (must pass!)   |
                      +--------------+--------------+
                                     |
                                     v
                      +-----------------------------+
                      |     SolidityParser / AST    |
                      | - Source offset mapping     |
                      | - Unchecked block detection |
                      | - Statement boundaries      |
                      +--------------+--------------+
                                     |
                                     v
                      +-----------------------------+
                      |   Mutation Operator Pool    |
                      | - UNCHECKED_MATH            |
                      | - REENTRANCY                |
                      | - TIMESTAMP_RELIANCE        |
                      +--------------+--------------+
                                     |
                                     v
                      +-----------------------------+
                      |    Mutant Candidate Pool    |
                      | (Filtered & Validated Sites)|
                      +--------------+--------------+
                                     |
                      +--------------v--------------+
                      |  Isolated Workspace Engine  | <---+ Iterates sequentially
                      | - Temp dir copy             |     | for each mutant
                      | - Apply single mutation     |     |
                      | - Compile (forge build)     |     |
                      | - Test (forge test)         |     |
                      | - Classify outcome          |     |
                      | - Safe cleanup              | ----+
                      +--------------+--------------+
                                     |
                                     v
                      +-----------------------------+
                      |   ResultClassifier & Metric |
                      | - KILLED, SURVIVED, etc.    |
                      | - Mutation Score:           |
                      |   K / (M - I - E) * 100     |
                      +--------------+--------------+
                                     |
                                     v
                      +-----------------------------+
                      |       Report Generator      |
                      | - mutation_report.json      |
                      | - mutation_report.html      |
                      +-----------------------------+
```

---

## 2. Core Modules

| Module | Responsibility |
| :--- | :--- |
| `src/project_loader.py` | Discovers project contracts, computes cryptographic SHA-256 hashes, creates isolated temporary workspaces, and guarantees source file immutability. |
| `src/project_detector.py` | Automatically detects the testing framework (Foundry, Hardhat), sources directory, test directory, and Solidity compiler pragma. |
| `src/solidity_parser.py` | Combines compiler AST metadata with source offset mapping and block scanning to detect unchecked blocks, statements, and expressions. |
| `src/compiler_manager.py` | Resolves the Foundry `forge` binary, ensures AST generation in configuration, and compiles workspaces with error parsing. |
| `src/test_runner.py` | Executes `forge test` with timeouts, parses test output (`[PASS]`, `[FAIL]`), and extracts failure traces. |
| `src/result_classifier.py` | Classifies execution outcomes into scientific categories: `KILLED`, `SURVIVED`, `INVALID`, `EQUIVALENT`, `TIMEOUT`, `UNRESOLVED`. |
| `src/scoring.py` | Calculates the academic mutation score $Score = \frac{K}{M - I - E} \times 100$, compilation rates, and operator score breakdowns. |
| `src/report_generator.py` | Exports structured machine-readable JSON and standalone interactive HTML reports with syntax-highlighted diffs. |
| `src/mutation_engine.py` | Coordinates the end-to-end pipeline, baseline enforcement, mutant isolation loop, and progress reporting. |

---

## 3. Mutant Isolation & Filesystem Safety Model

A key vulnerability of naive mutation tools is in-place file modification, which risks corrupting developers' contracts or leaving mutated files behind if execution crashes.

Our framework enforces **complete physical isolation**:
1. **Source Immutability**: All original `.sol` files are read-only referenced. SHA-256 hashes are recorded before the campaign and verified after execution.
2. **Disposable Workspaces**: For every single mutant, a clean, disposable temporary directory is provisioned using Python's `tempfile.mkdtemp()`.
3. **Single-Fault Injection**: Exactly one mutation is applied per isolated workspace copy.
4. **Deterministic Mutant IDs**: Mutants receive reproducible identifiers (`MUT-0001`, `MUT-0002`, ...).
5. **Deterministic Cleanup**: The workspace is guaranteed to be destroyed in a `finally:` block immediately after test execution.
