"""Core mutation testing engine orchestrating discovery, isolation, execution, and reporting."""

import hashlib
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from operators import get_available_operators, get_operator
from operators.base_operator import BaseMutationOperator
from src.compiler_manager import CompilerManager
from src.exceptions import BaselineVerificationError, MutationToolError
from src.mutant_model import Mutant, MutationCandidate, MutationStatus
from src.project_loader import ProjectLoader
from src.report_generator import ReportGenerator
from src.result_classifier import ResultClassifier
from src.scoring import CampaignMetrics, ScoringEngine
from src.solidity_parser import SolidityParser
from src.test_runner import TestRunner


class MutationEngine:
    """Orchestrates the entire Solidity mutation testing pipeline."""

    def __init__(
        self,
        project_path: Path,
        operator_names: Optional[List[str]] = None,
        timeout_seconds: int = 60,
        forge_bin_path: Optional[str] = None,
        output_dir: Optional[Path] = None,
        logger: Optional[logging.Logger] = None
    ):
        self.project_path = Path(project_path).resolve()
        self.timeout_seconds = timeout_seconds
        self.output_dir = Path(output_dir or "./reports").resolve()
        self.logger = logger or logging.getLogger("mutation_engine")

        self.project_loader = ProjectLoader(self.project_path)
        self.compiler_manager = CompilerManager(forge_bin_path)
        self.test_runner = TestRunner(self.compiler_manager.forge_bin)

        # Resolve operators
        if operator_names:
            self.operators: List[BaseMutationOperator] = [
                get_operator(name) for name in operator_names
            ]
        else:
            self.operators = get_available_operators()

        self.candidates: List[MutationCandidate] = []
        self.rejected_candidates: List[MutationCandidate] = []
        self.rejection_reasons: Dict[str, int] = {}
        self.mutants: List[Mutant] = []
        self.metrics: Optional[CampaignMetrics] = None

    def verify_baseline(self) -> None:
        """Verify that the original project compiles and its tests pass completely."""
        self.logger.info("Validating baseline project integrity...")
        self.compiler_manager.ensure_ast_enabled(self.project_path)

        comp_result = self.compiler_manager.compile_project(
            self.project_path, timeout_seconds=self.timeout_seconds
        )
        if not comp_result.success:
            raise BaselineVerificationError(
                f"Baseline project compilation failed:\n{comp_result.error_summary or comp_result.stderr}"
            )

        test_result = self.test_runner.run_tests(
            self.project_path, timeout_seconds=self.timeout_seconds
        )
        if not test_result.success:
            failing = ", ".join(test_result.failing_tests) if test_result.failing_tests else "Unknown error"
            raise BaselineVerificationError(
                f"Baseline project test suite failed before mutation testing:\n{failing}\n{test_result.stderr}"
            )
        self.logger.info(
            f"Baseline passed: {len(test_result.passing_tests)} tests passing cleanly."
        )

    def discover_candidates(self) -> List[MutationCandidate]:
        """Scan project contracts and discover all mutation candidates across operators."""
        self.candidates.clear()
        self.rejected_candidates.clear()
        self.rejection_reasons.clear()

        info = self.project_loader.validate_and_load()
        source_files = self.project_loader.get_source_files()

        self.logger.info(
            f"Scanning {len(source_files)} Solidity source files for mutation candidates..."
        )

        for src_file in source_files:
            rel_path = src_file.relative_to(self.project_path)
            # Find artifact path if present
            artifact_name = src_file.stem
            artifact_path = (
                self.project_path / "out" / src_file.name / f"{artifact_name}.json"
            )
            parser = SolidityParser.from_file(src_file, artifact_path)

            source_code = src_file.read_text(encoding="utf-8")

            for op in self.operators:
                op_candidates = op.find_candidates(rel_path, source_code, parser)
                for cand in op_candidates:
                    if cand.is_eligible:
                        self.candidates.append(cand)
                    else:
                        self.rejected_candidates.append(cand)
                        reason = cand.rejection_reason or "Ineligible candidate"
                        self.rejection_reasons[reason] = (
                            self.rejection_reasons.get(reason, 0) + 1
                        )

        self.logger.info(
            f"Discovered {len(self.candidates)} eligible mutation candidates "
            f"({len(self.rejected_candidates)} rejected)."
        )
        return self.candidates

    def run_campaign(self) -> Tuple[List[Mutant], CampaignMetrics]:
        """Execute the full mutation campaign: baseline, mutant generation, testing, scoring."""
        self.verify_baseline()
        self.discover_candidates()

        self.mutants.clear()
        op_lookup = {op.operator_id: op for op in self.operators}

        self.logger.info(f"Beginning evaluation of {len(self.candidates)} mutants...")

        for idx, cand in enumerate(self.candidates, start=1):
            mutant_id = f"MUT-{idx:04d}"
            op = op_lookup.get(cand.operator_id)
            if not op:
                continue

            # Original source info
            orig_rel_path = cand.file_path.as_posix()
            orig_hash = self.project_loader.get_source_hash(orig_rel_path)

            mutant = Mutant(
                mutant_id=mutant_id,
                operator_name=cand.operator_id,
                source_file=orig_rel_path,
                line_number=cand.start_line,
                original_source_hash=orig_hash,
                mutated_source_hash="",
                transformation={
                    "original": cand.original_text,
                    "mutated": cand.replacement_text
                },
                description=cand.description
            )

            # Create isolated workspace
            workspace = self.project_loader.create_isolated_workspace(prefix=f"{mutant_id}_")
            try:
                target_file = workspace / cand.file_path
                if not target_file.exists():
                    mutant.status = MutationStatus.INVALID
                    mutant.status_reason = f"Target file '{cand.file_path}' missing in isolated workspace."
                    self.mutants.append(mutant)
                    continue

                original_source = target_file.read_text(encoding="utf-8")
                mutated_source = op.apply_mutation(original_source, cand)
                target_file.write_text(mutated_source, encoding="utf-8")

                mutant.mutated_source_hash = hashlib.sha256(
                    mutated_source.encode("utf-8")
                ).hexdigest()

                # Step A: Compile mutant in isolated workspace
                comp_result = self.compiler_manager.compile_project(
                    workspace, timeout_seconds=self.timeout_seconds
                )
                mutant.compilation_success = comp_result.success

                test_result = None
                if comp_result.success:
                    # Step B: Execute tests on compiled mutant
                    test_result = self.test_runner.run_tests(
                        workspace, timeout_seconds=self.timeout_seconds
                    )
                    mutant.execution_time_seconds = round(test_result.duration_seconds, 3)
                    mutant.stdout = test_result.stdout
                    mutant.stderr = test_result.stderr
                    mutant.exit_code = test_result.exit_code
                    mutant.passing_tests = test_result.passing_tests
                    mutant.failing_tests = test_result.failing_tests
                    mutant.failure_details = test_result.failure_details
                else:
                    mutant.execution_time_seconds = round(comp_result.duration_seconds, 3)
                    mutant.stdout = comp_result.stdout
                    mutant.stderr = comp_result.stderr
                    mutant.exit_code = comp_result.exit_code

                # Step C: Classify outcome
                outcome = ResultClassifier.classify(comp_result, test_result, mutant)
                mutant.status = outcome.status
                mutant.status_reason = outcome.reason
                mutant.suspected_equivalent = outcome.is_equivalent_suspected

                self.logger.info(
                    f"[{mutant_id}] {cand.operator_id} (line {cand.start_line}): {mutant.status.value}"
                )

            finally:
                # Clean up isolated workspace
                self.project_loader.cleanup_workspace(workspace)

            self.mutants.append(mutant)

        # Safety invariant check: Ensure original source was never touched!
        if not self.project_loader.verify_sources_unmodified():
            self.logger.critical(
                "CRITICAL WARNING: Original project files were modified during campaign!"
            )
        else:
            self.logger.info("Verified: Original project files remained completely unmodified.")

        # Compute metrics
        self.metrics = ScoringEngine.calculate(
            mutants=self.mutants,
            total_candidates=len(self.candidates) + len(self.rejected_candidates),
            rejected_candidates=len(self.rejected_candidates),
            rejection_reasons=self.rejection_reasons
        )

        return self.mutants, self.metrics

    def generate_reports(self, command_line: str = "") -> Tuple[Path, Path]:
        """Generate machine-readable JSON and local interactive HTML reports."""
        assert self.metrics is not None
        info = self.project_loader.project_info
        reporter = ReportGenerator(
            output_dir=self.output_dir,
            project_name=self.project_path.name,
            solidity_version=info.solidity_version if info else "0.8.20",
            framework=info.framework if info else "Foundry",
            command_line=command_line
        )

        json_path = reporter.generate_json(self.mutants, self.metrics)
        html_path = reporter.generate_html(self.mutants, self.metrics)

        self.logger.info(f"JSON Report written to: {json_path}")
        self.logger.info(f"HTML Report written to: {html_path}")
        return json_path, html_path
