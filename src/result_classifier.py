"""Classifies mutant execution outcomes into well-defined scientific categories."""

from dataclasses import dataclass
from typing import Optional

from src.compiler_manager import CompilationResult
from src.mutant_model import Mutant, MutationStatus
from src.test_runner import TestRunResult


@dataclass
class ClassificationOutcome:
    """The outcome and reasoning of a mutant evaluation."""
    status: MutationStatus
    reason: str
    is_equivalent_suspected: bool = False


class ResultClassifier:
    """Applies strict scientific rules to classify mutant execution outcomes."""

    @staticmethod
    def classify(
        compile_result: CompilationResult,
        test_result: Optional[TestRunResult],
        mutant: Mutant
    ) -> ClassificationOutcome:
        """Classifies a mutant outcome based on compilation and test results.

        Args:
            compile_result: Output from compiling the mutated project.
            test_result: Output from running tests against the mutated project.
            mutant: Metadata and transformation details of the mutant.

        Returns:
            ClassificationOutcome with status and diagnostic justification.
        """
        # Rule 1: Compilation Failure -> INVALID
        if not compile_result.success:
            err_msg = compile_result.error_summary or "Mutant failed to compile"
            return ClassificationOutcome(
                status=MutationStatus.INVALID,
                reason=f"Compilation error: {err_msg}"
            )

        if test_result is None:
            return ClassificationOutcome(
                status=MutationStatus.UNRESOLVED,
                reason="Test execution was not performed despite successful compilation."
            )

        # Rule 2: Timeout Exceeded -> TIMEOUT
        if test_result.is_timeout:
            return ClassificationOutcome(
                status=MutationStatus.TIMEOUT,
                reason=f"Execution exceeded configured timeout ({test_result.duration_seconds:.1f}s)."
            )

        # Rule 3: Compiler error encountered during test runner phase -> INVALID
        if test_result.is_compiler_error:
            return ClassificationOutcome(
                status=MutationStatus.INVALID,
                reason="Test runner encountered compilation errors during execution."
            )

        # Rule 4: Test runner crash / environmental error without test attribution -> UNRESOLVED
        if test_result.is_crash:
            return ClassificationOutcome(
                status=MutationStatus.UNRESOLVED,
                reason=f"Test runner crashed or encountered environmental failure: {test_result.failure_details}"
            )

        # Rule 5: Test suite detected behavioral change via failing tests -> KILLED
        if len(test_result.failing_tests) > 0:
            failed_str = ", ".join(test_result.failing_tests)
            return ClassificationOutcome(
                status=MutationStatus.KILLED,
                reason=f"Failing tests detected behavior mutation: {failed_str}"
            )

        # Rule 6: All tests passed -> SURVIVED (or suspected equivalent if flagged)
        if test_result.success and len(test_result.failing_tests) == 0:
            # Equivalence heuristic check: if transformation has zero semantic difference under all inputs
            # e.g., unchecked block around pure constants or no-op expressions
            is_equiv = ResultClassifier._check_suspected_equivalence(mutant)
            if is_equiv:
                return ClassificationOutcome(
                    status=MutationStatus.SURVIVED,
                    reason="Mutant survived; suspected equivalent due to absence of observable state delta.",
                    is_equivalent_suspected=True
                )
            return ClassificationOutcome(
                status=MutationStatus.SURVIVED,
                reason="All test cases passed. The test suite failed to detect the injected fault."
            )

        # Fallback safety
        return ClassificationOutcome(
            status=MutationStatus.UNRESOLVED,
            reason="Ambiguous test runner result could not be attributed reliably."
        )

    @staticmethod
    def _check_suspected_equivalence(mutant: Mutant) -> bool:
        """Heuristic check for potential equivalent mutants."""
        # For example, if original and mutated text are identical after whitespace normalization
        orig = mutant.transformation.get("original", "").strip()
        mut = mutant.transformation.get("mutated", "").strip()
        if orig == mut:
            return True
        return False
