# Build a mutation testing tool that injects specific bug operators, such as unchecked arithmetic, reentrancy, and timestamp reliance, into Solidity smart contracts to measure the effectiveness of their test suites.

[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12%20%7C%203.14-blue.svg)](https://python.org)
[![Solidity](https://img.shields.io/badge/Solidity-0.8.20-363636.svg)](https://soliditylang.org/)
[![Foundry](https://img.shields.io/badge/Foundry-Forge%201.8.5-orange.svg)](https://getfoundry.sh/)
[![Tests](https://img.shields.io/badge/pytest-24%20passed-brightgreen.svg)]()
[![License](https://img.shields.io/badge/License-MIT-green.svg)]()

A modular, context-aware mutation testing framework designed to evaluate the fault-detection effectiveness of Solidity smart contract test suites by injecting controlled, security-relevant bug operators into clean isolated workspaces.

---

## 1. Project Motivation & Problem Statement

Smart contracts deployed on public blockchains are immutable and handle billions of dollars in digital assets. While standard test coverage metrics (such as statement or line coverage) show which lines of code were executed during testing, **they do not measure whether test assertions would actually catch real bugs or security faults**. A test suite can achieve 100% line coverage simply by executing transactions without asserting any invariants or post-conditions.

**Mutation testing** solves this problem by deliberately injecting small, syntactically and semantically valid bug operators ("mutants") into the contract source. If the existing test suite detects the injected bug (fails), the mutant is **KILLED**; if the tests pass despite the bug, the mutant has **SURVIVED**, revealing an undetected blind spot in the test suite.

---

## 2. Objectives & Scope

### Objectives
- Automatically discover eligible mutation sites using compiler AST and syntactic analysis.
- Inject three independent, context-aware bug operators:
  1. **Unchecked Arithmetic (`UNCHECKED_MATH`)**: Simulates dangerous `unchecked` blocks in Solidity 0.8+.
  2. **Reentrancy (`REENTRANCY`)**: Inverts Checks-Effects-Interactions to create reentrancy windows.
  3. **Timestamp Reliance (`TIMESTAMP_RELIANCE`)**: Modifies `block.timestamp` boundary conditions and timelock calculations.
- Execute mutants in disposable, isolated temporary workspaces to guarantee original files remain 100% untouched.
- Compile and execute tests using Foundry (`forge`).
- Classify outcomes into scientific categories (`KILLED`, `SURVIVED`, `INVALID`, `EQUIVALENT`, `TIMEOUT`, `UNRESOLVED`).
- Calculate mutation scores and generate structured JSON and standalone interactive HTML reports.

### Scope & Non-Goals
- **In Scope**: Local Foundry-based Solidity projects; AST-guided mutation; automated test execution; classification; local reporting.
- **Non-Goals**: This is NOT a vulnerability scanner (like Slither/Mythril), NOT a static analysis dashboard, and NOT a tool intended for live mainnet deployments.

---

## 3. Technology Stack

- **Python 3.11+** (Engine, AST parsing, scoring, reporting, and CLI)
- **Foundry / Forge (v1.8.5+)** (Solidity compilation and local EVM test execution)
- **Solidity 0.8+** (Smart contract target language)
- **pytest** (Comprehensive Python test suite)
- **Jinja2 & Standard Libraries** (Report generation and file isolation)
- **JSON & HTML5/CSS3** (Interactive local reporting without server dependencies)

---

## 4. Repository Structure

```
.
├── main.py                          # CLI execution entry point
├── config.yaml                      # Engine default configuration
├── requirements.txt                 # Pinned dependencies
├── pyproject.toml                   # Packaging and pytest configuration
├── .gitignore                       # Git ignore patterns
│
├── src/                             # Core Python engine
│   ├── __init__.py                  # Package init
│   ├── cli.py                       # Command line interface & argument parser
│   ├── project_loader.py            # Project discovery, hashing & workspace isolation
│   ├── project_detector.py          # Framework and compiler version detection
│   ├── solidity_parser.py           # AST & source offset mapping layer
│   ├── compiler_manager.py          # Forge compilation management
│   ├── test_runner.py               # Forge test execution & failure extraction
│   ├── mutant_model.py              # Data models (Mutant, Candidate, Status)
│   ├── result_classifier.py         # Outcome classification rules
│   ├── scoring.py                   # Academic mutation scoring formulas
│   ├── report_generator.py          # Standalone HTML & JSON report builders
│   ├── mutation_engine.py           # Pipeline orchestration
│   ├── logging_config.py            # Formatted console/file logging
│   └── exceptions.py                # Custom exception hierarchy
│
├── operators/                       # Mutation operators
│   ├── __init__.py                  # Operator registry and aliases
│   ├── base_operator.py             # Abstract base mutation operator
│   ├── unchecked_math.py            # UNCHECKED_MATH operator
│   ├── reentrancy.py                # REENTRANCY operator
│   └── timestamp_reliance.py        # TIMESTAMP_RELIANCE operator
│
├── examples/                        # Sample Solidity project
│   └── bank_project/
│       ├── foundry.toml             # Foundry configuration
│       ├── src/
│       │   └── Bank.sol             # Vault contract with arithmetic, timelock, withdraw
│       └── test/
│           ├── Bank.t.sol           # Baseline test suite
│           ├── ReentrancyAttacker.t.sol # Invariant recipient contract
│           └── BankImproved.t.sol   # Targeted boundary tests
│
├── tests/                           # Python unit & integration tests (24 passed)
│   ├── test_project_loader.py
│   ├── test_parser.py
│   ├── test_unchecked_math.py
│   ├── test_reentrancy.py
│   ├── test_timestamp.py
│   ├── test_result_classifier.py
│   ├── test_scoring.py
│   ├── test_report_generator.py
│   ├── test_mutation_engine.py
│   └── test_end_to_end.py
│
├── reports/                         # Default directory for generated reports
│   └── .gitkeep
│
└── docs/                            # Research & technical documentation
    ├── ARCHITECTURE.md              # System design & execution model
    ├── MUTATION_OPERATORS.md        # Operator specifications & fault models
    ├── EXPERIMENTAL_METHODOLOGY.md  # Scientific methodology & literature review
    └── LIMITATIONS.md               # Theoretical & practical boundaries
```

---

## 5. Prerequisites & Installation

### Prerequisites
1. **Python 3.11+** installed (`python --version`)
2. **Git** installed (`git --version`)
3. **Foundry (`forge`)** installed (`forge --version`)

#### Installing Foundry
- **Windows (PowerShell)**:
  Download the Windows release zip from [Foundry Releases](https://github.com/foundry-rs/foundry/releases), extract to `$HOME\.foundry\bin`, and add to your user `PATH`.
- **Linux / macOS**:
  ```bash
  curl -L https://foundry.paradigm.xyz | bash
  foundryup
  ```

### Python Setup
Clone this repository and set up a virtual environment:

```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

## 6. Usage & Example Commands

### 1. View Registered Operators
```bash
python main.py --list-operators
```

### 2. Candidate Discovery (Dry-Run Mode)
Scans project files and outputs eligible mutation sites without compiling or running tests:
```bash
python main.py --project ./examples/bank_project --dry-run
```

### 3. Run Complete Mutation Campaign
Executes baseline verification, mutant generation, testing, scoring, and report generation:
```bash
python main.py --project ./examples/bank_project
```

### 4. Run Specific Operators
```bash
# Run only Reentrancy operator
python main.py --project ./examples/bank_project --operators reentrancy

# Run Unchecked Math and Timestamp Reliance
python main.py --project ./examples/bank_project --operators unchecked_math,timestamp
```

### 5. Custom Output Directory and Timeout
```bash
python main.py --project ./examples/bank_project --timeout 45 --output ./reports/run_001
```

---

## 7. Mutation Score Formula & Status Definitions

### Mathematical Formula
The standard academic mutation score is defined as:

$$\text{Mutation Score} = \frac{K}{M - I - E} \times 100$$

Where:
- **$M$**: Total generated mutants
- **$K$**: Killed mutants (detected by test failure)
- **$I$**: Invalid mutants (syntax or compilation error)
- **$E$**: Equivalent mutants (syntactically altered but functionally identical)

*Note: Timeouts and unresolved executions are retained in the denominator $(M - I - E)$ to prevent concealing execution failures.*

### Result Status Classification
- **`KILLED`**: The test suite detected the injected fault (one or more test assertions failed).
- **`SURVIVED`**: The test suite passed completely, failing to detect the altered contract behavior.
- **`INVALID`**: The mutant could not compile or was structurally malformed.
- **`EQUIVALENT`**: The mutant has no observable behavioral difference under the contract specification.
- **`TIMEOUT`**: Execution exceeded the configured time limit.
- **`UNRESOLVED`**: Environmental crash or indeterminate failure.

---

## 8. Verified Experimental Results

Running against `examples/bank_project` produces the following verified empirical outcomes:

```
=================================================================
           MUTATION TESTING CAMPAIGN SUMMARY
=================================================================
 Target Project:           bank_project
 Overall Mutation Score:   27.27%
 Total Mutants Generated:  11
 Killed Mutants:           3
 Surviving Mutants:        8
 Invalid / Compile Errors: 0
 Equivalent / Suspected:   0
 Timeouts:                 0
 Unresolved:               0
 Compilation Rate:         100.0%
 Total Execution Time:     0.73s
-----------------------------------------------------------------
 OPERATOR BREAKDOWN:
  * UNCHECKED_MATH       Score:   0.00% (Killed: 0/6)
  * REENTRANCY           Score: 100.00% (Killed: 1/1)
  * TIMESTAMP_RELIANCE   Score:  50.00% (Killed: 2/4)
=================================================================
 JSON Report: reports/mutation_report.json
 HTML Report: reports/mutation_report.html
=================================================================
```

---

## 9. Running Tests

Run the complete Python test suite via pytest:

```bash
pytest
```

Output:
```
============================= 24 passed in 4.39s ==============================
```

Verify the sample Foundry project directly:
```bash
forge test --root ./examples/bank_project
```

Output:
```
Ran 3 test suites: 9 tests passed, 0 failed, 0 skipped
```

---

## 10. Security and Isolation Guarantees

- **Non-Destructive**: Original source files are never written to or overwritten during execution.
- **Cryptographic Hashes**: SHA-256 hashes of all source files are computed before and validated after each run.
- **Disposable Workspaces**: Each mutant runs in an isolated directory generated with `tempfile.mkdtemp()`.
- **Zero Real Funds**: All operations run locally inside Foundry's EVM sandbox without public network connections.
