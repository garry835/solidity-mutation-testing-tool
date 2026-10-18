"""Unit tests for ProjectLoader and ProjectDetector."""

import tempfile
from pathlib import Path
import pytest

from src.exceptions import InvalidProjectError, ProjectNotFoundError
from src.project_detector import ProjectDetector
from src.project_loader import ProjectLoader


def test_project_not_found():
    """Verify that a nonexistent project directory raises ProjectNotFoundError."""
    loader = ProjectLoader(Path("/nonexistent/directory/path/solidity"))
    with pytest.raises(ProjectNotFoundError):
        loader.validate_and_load()


def test_invalid_project_no_sources(tmp_path: Path):
    """Verify that a project without src directory or .sol files raises InvalidProjectError."""
    loader = ProjectLoader(tmp_path)
    with pytest.raises(InvalidProjectError):
        loader.validate_and_load()


def test_project_detector_foundry(tmp_path: Path):
    """Verify correct detection of Foundry project structure and configuration."""
    src = tmp_path / "src"
    src.mkdir()
    (src / "Sample.sol").write_text("pragma solidity 0.8.20;\ncontract Sample {}", encoding="utf-8")
    (tmp_path / "foundry.toml").write_text('solc = "0.8.20"\n', encoding="utf-8")

    info = ProjectDetector.detect(tmp_path)
    assert info.framework == "foundry"
    assert info.solidity_version == "0.8.20"
    assert info.src_dir == src


def test_project_loader_hashing_and_isolation(tmp_path: Path):
    """Verify source hashing, workspace isolation, and immutability verification."""
    src = tmp_path / "src"
    src.mkdir()
    contract_file = src / "Vault.sol"
    contract_content = "pragma solidity 0.8.20;\ncontract Vault { uint256 public x; }"
    contract_file.write_text(contract_content, encoding="utf-8")

    loader = ProjectLoader(tmp_path)
    info = loader.validate_and_load()
    assert info.src_dir == src

    rel_path = "src/Vault.sol"
    hash_val = loader.get_source_hash(rel_path)
    assert len(hash_val) == 64
    assert loader.verify_sources_unmodified() is True

    # Test isolated workspace creation
    workspace = loader.create_isolated_workspace()
    try:
        assert workspace.exists()
        isolated_file = workspace / "src" / "Vault.sol"
        assert isolated_file.exists()
        assert isolated_file.read_text(encoding="utf-8") == contract_content

        # Modify isolated file and verify original remains unmodified
        isolated_file.write_text("modified", encoding="utf-8")
        assert contract_file.read_text(encoding="utf-8") == contract_content
        assert loader.verify_sources_unmodified() is True
    finally:
        loader.cleanup_workspace(workspace)
        assert not workspace.exists()
