"""Unit tests for ResultClassifier."""

from src.compiler_manager import CompilationResult
from src.mutant_model import Mutant, MutationStatus
from src.result_classifier import ResultClassifier
from src.test_runner import TestRunResult


def test_classify_compiler_failure():
    """Verify that compilation errors are strictly classified as INVALID."""
    comp = CompilationResult(
        success=False,
        exit_code=1,
        duration_seconds=0.5,
        stdout="",
        stderr="ParserError: expected ';' but got '}'",
        error_summary="ParserError"
    )
    mutant = Mutant(
        mutant_id="MUT-0001",
        operator_name="UNCHECKED_MATH",
        source_file="Bank.sol",
        line_number=10,
        original_source_hash="h1",
        mutated_source_hash="h2",
        transformation={"original": "a;", "mutated": "b;"},
        description="desc"
    )
    outcome = ResultClassifier.classify(comp, None, mutant)
    assert outcome.status == MutationStatus.INVALID
    assert "Compilation error" in outcome.reason


def test_classify_killed_mutant():
    """Verify that a test failure detecting the fault is classified as KILLED."""
    comp = CompilationResult(success=True, exit_code=0, duration_seconds=0.2, stdout="", stderr="")
    test_res = TestRunResult(
        success=False,
        exit_code=1,
        duration_seconds=0.3,
        stdout="[FAIL: Revert] testWithdraw()",
        stderr="",
        passing_tests=["testDeposit"],
        failing_tests=["testWithdraw"]
    )
    mutant = Mutant(
        mutant_id="MUT-0002",
        operator_name="REENTRANCY",
        source_file="Bank.sol",
        line_number=20,
        original_source_hash="h1",
        mutated_source_hash="h2",
        transformation={"original": "a;", "mutated": "b;"},
        description="desc"
    )
    outcome = ResultClassifier.classify(comp, test_res, mutant)
    assert outcome.status == MutationStatus.KILLED
    assert "testWithdraw" in outcome.reason


def test_classify_survived_mutant():
    """Verify that all passing tests results in SURVIVED classification."""
    comp = CompilationResult(success=True, exit_code=0, duration_seconds=0.2, stdout="", stderr="")
    test_res = TestRunResult(
        success=True,
        exit_code=0,
        duration_seconds=0.4,
        stdout="[PASS] testAll()",
        stderr="",
        passing_tests=["testAll"],
        failing_tests=[]
    )
    mutant = Mutant(
        mutant_id="MUT-0003",
        operator_name="TIMESTAMP_RELIANCE",
        source_file="Bank.sol",
        line_number=30,
        original_source_hash="h1",
        mutated_source_hash="h2",
        transformation={"original": "<", "mutated": "<="},
        description="desc"
    )
    outcome = ResultClassifier.classify(comp, test_res, mutant)
    assert outcome.status == MutationStatus.SURVIVED


def test_classify_timeout():
    """Verify that timeout flag results in TIMEOUT classification."""
    comp = CompilationResult(success=True, exit_code=0, duration_seconds=0.2, stdout="", stderr="")
    test_res = TestRunResult(
        success=False,
        exit_code=-1,
        duration_seconds=60.0,
        stdout="",
        stderr="Timeout expired",
        is_timeout=True
    )
    mutant = Mutant(
        mutant_id="MUT-0004",
        operator_name="UNCHECKED_MATH",
        source_file="Bank.sol",
        line_number=40,
        original_source_hash="h1",
        mutated_source_hash="h2",
        transformation={"original": "a", "mutated": "b"},
        description="desc"
    )
    outcome = ResultClassifier.classify(comp, test_res, mutant)
    assert outcome.status == MutationStatus.TIMEOUT
