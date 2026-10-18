"""Unit tests for ReportGenerator."""

import json
from pathlib import Path
from src.mutant_model import Mutant, MutationStatus
from src.report_generator import ReportGenerator
from src.scoring import ScoringEngine


def test_generate_json_and_html_reports(tmp_path: Path):
    """Verify that JSON and HTML reports are generated with complete schemas."""
    mutants = [
        Mutant(
            mutant_id="MUT-0001",
            operator_name="UNCHECKED_MATH",
            source_file="src/Bank.sol",
            line_number=18,
            original_source_hash="abcd",
            mutated_source_hash="ef01",
            transformation={"original": "a += 1;", "mutated": "unchecked { a += 1; }"},
            description="Wrap addition in unchecked block",
            status=MutationStatus.KILLED,
            compilation_success=True,
            execution_time_seconds=0.12,
            failing_tests=["testAddOverflow"]
        )
    ]
    metrics = ScoringEngine.calculate(mutants, total_candidates=1, rejected_candidates=0)
    reporter = ReportGenerator(
        output_dir=tmp_path,
        project_name="TestBank",
        solidity_version="0.8.20",
        framework="Foundry",
        command_line="python main.py"
    )

    json_file = reporter.generate_json(mutants, metrics, "test_report.json")
    assert json_file.exists()
    data = json.loads(json_file.read_text(encoding="utf-8"))
    assert data["meta"]["project_name"] == "TestBank"
    assert data["metrics"]["mutation_score"] == 100.0
    assert len(data["mutants"]) == 1

    html_file = reporter.generate_html(mutants, metrics, "test_report.html")
    assert html_file.exists()
    html_text = html_file.read_text(encoding="utf-8")
    assert "Solidity Mutation Testing Report" in html_text
    assert "MUT-0001" in html_text
    assert "100.0%" in html_text
    assert "UNCHECKED_MATH" in html_text
