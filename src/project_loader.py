"""Loads, validates, and creates isolated workspaces for Solidity projects."""

import hashlib
import os
import shutil
import tempfile
from pathlib import Path
from typing import Dict, List, Optional

from src.exceptions import InvalidProjectError, ProjectNotFoundError
from src.project_detector import ProjectDetector, ProjectInfo


class ProjectLoader:
    """Handles project discovery, hashing, and temporary workspace isolation."""

    def __init__(self, project_path: Path):
        self.project_path = Path(project_path).resolve()
        self.project_info: Optional[ProjectInfo] = None
        self._source_hashes: Dict[str, str] = {}

    def validate_and_load(self) -> ProjectInfo:
        """Validates project existence and loads project information.

        Returns:
            ProjectInfo containing validated directory structure.

        Raises:
            ProjectNotFoundError: If project directory does not exist.
            InvalidProjectError: If essential files or directories are missing.
        """
        if not self.project_path.exists():
            raise ProjectNotFoundError(f"Project directory not found: {self.project_path}")
        if not self.project_path.is_dir():
            raise InvalidProjectError(f"Specified path is not a directory: {self.project_path}")

        info = ProjectDetector.detect(self.project_path)
        if not info.src_dir.exists():
            raise InvalidProjectError(
                f"Source directory '{info.src_dir}' does not exist in project {self.project_path}"
            )

        sol_files = list(info.src_dir.rglob("*.sol"))
        if not sol_files:
            raise InvalidProjectError(
                f"No Solidity (*.sol) source files found in '{info.src_dir}'"
            )

        self.project_info = info
        self._compute_source_hashes()
        return info

    def _compute_source_hashes(self) -> Dict[str, str]:
        """Compute SHA-256 hash for every Solidity source file in src_dir."""
        assert self.project_info is not None
        self._source_hashes.clear()
        for file_path in self.project_info.src_dir.rglob("*.sol"):
            rel_path = file_path.relative_to(self.project_info.root_dir).as_posix()
            content = file_path.read_bytes()
            sha256 = hashlib.sha256(content).hexdigest()
            self._source_hashes[rel_path] = sha256
        return self._source_hashes

    def get_source_hash(self, relative_path: str) -> str:
        """Get the original SHA-256 hash for a given relative path."""
        norm_path = Path(relative_path).as_posix()
        return self._source_hashes.get(norm_path, "")

    def get_source_files(self) -> List[Path]:
        """Return list of all Solidity source files in src directory."""
        if not self.project_info:
            self.validate_and_load()
        assert self.project_info is not None
        return sorted(list(self.project_info.src_dir.rglob("*.sol")))

    def verify_sources_unmodified(self) -> bool:
        """Verify that no source file in the original project was altered.

        Returns:
            True if all current hashes match the stored original hashes.
        """
        if not self.project_info:
            return True
        for file_path in self.project_info.src_dir.rglob("*.sol"):
            rel_path = file_path.relative_to(self.project_info.root_dir).as_posix()
            original = self._source_hashes.get(rel_path)
            if not original:
                return False
            current = hashlib.sha256(file_path.read_bytes()).hexdigest()
            if current != original:
                return False
        return True

    def create_isolated_workspace(self, prefix: str = "mutant_ws_") -> Path:
        """Creates a temporary isolated copy of the entire project.

        Args:
            prefix: Temporary directory prefix.

        Returns:
            Path to the isolated temporary project directory.
        """
        temp_dir = Path(tempfile.mkdtemp(prefix=prefix))
        
        # Copy project files, ignoring build caches and git history to ensure speed & isolation
        def ignore_patterns(path: str, names: List[str]) -> List[str]:
            ignored = set()
            for name in names:
                if name in [".git", "node_modules", "out", "cache", "reports", ".venv"]:
                    ignored.add(name)
            return list(ignored)

        # Copy entire project directory contents into temp_dir
        for item in self.project_path.iterdir():
            if item.name in [".git", "node_modules", "out", "cache", "reports", ".venv"]:
                continue
            dest = temp_dir / item.name
            if item.is_dir():
                shutil.copytree(item, dest, ignore=ignore_patterns)
            else:
                shutil.copy2(item, dest)

        return temp_dir

    @staticmethod
    def cleanup_workspace(workspace_path: Path) -> None:
        """Safely removes an isolated temporary workspace directory."""
        if workspace_path and workspace_path.exists():
            try:
                shutil.rmtree(workspace_path, ignore_errors=True)
            except Exception:
                pass
