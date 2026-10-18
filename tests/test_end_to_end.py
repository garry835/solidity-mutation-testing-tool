"""Integration and End-to-End tests for the mutation testing framework."""

import shutil
from pathlib import Path
import pytest

from src.compiler_manager import CompilerManager
from src.mutant_model import MutationStatus
from src.mutation_engine import MutationEngine


@pytest.fixture
def foundry_available() -> bool:
    """Check if forge binary is available in the environment."""
    try:
        CompilerManager._resolve_forge_binary()
        return True
    except Exception:
        return False


def test_end_to_end_campaign_on_bank_project(tmp_path: Path, foundry_available: bool):
    """Execute complete end-to-end mutation testing campaign on the bank_project."""
    if not foundry_available:
        pytest.skip("Foundry 'forge' binary not available in environment.")

    bank_dir = Path("examples/bank_project").resolve()
    reports_dir = tmp_path / "reports"

    engine = MutationEngine(
        project_path=bank_dir,
        timeout_seconds=45,
        output_dir=reports_dir
    )

    mutants, metrics = engine.run_campaign()

    assert len(mutants) > 0
    assert metrics.total_mutants == len(mutants)
    assert metrics.compilation_success_rate == 100.0

    # Ensure operators were evaluated
    assert "UNCHECKED_MATH" in metrics.operator_scores
    assert "REENTRANCY" in metrics.operator_scores
    assert "TIMESTAMP_RELIANCE" in metrics.operator_scores

    # Verify that at least one mutant was killed
    assert metrics.killed >= 1
    # Verify that at least one mutant survived
    assert metrics.survived >= 1

    # Verify report generation
    json_path, html_path = engine.generate_reports()
    assert json_path.exists()
    assert html_path.exists()

    # Safety check: original project sources must remain untouched
    assert engine.project_loader.verify_sources_unmodified() is True
