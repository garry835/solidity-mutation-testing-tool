"""Detects project framework, directories, and Solidity compiler requirements."""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass
class ProjectInfo:
    """Information detected about the target Solidity project."""
    root_dir: Path
    framework: str
    src_dir: Path
    test_dir: Path
    solidity_version: Optional[str] = None
    config_file: Optional[Path] = None


class ProjectDetector:
    """Inspects project structure to detect framework and compiler configurations."""

    @staticmethod
    def detect(project_path: Path) -> ProjectInfo:
        """Analyze project root directory and infer configurations.

        Args:
            project_path: Path to target project.

        Returns:
            ProjectInfo containing detected paths and framework.
        """
        project_path = project_path.resolve()

        framework = "unknown"
        config_file = None
        solc_version = None

        # Check for Foundry
        foundry_toml = project_path / "foundry.toml"
        if foundry_toml.exists():
            framework = "foundry"
            config_file = foundry_toml
            solc_version = ProjectDetector._parse_foundry_solc(foundry_toml)

        # Check for Hardhat
        hardhat_js = project_path / "hardhat.config.js"
        hardhat_ts = project_path / "hardhat.config.ts"
        if hardhat_js.exists() or hardhat_ts.exists():
            framework = "hardhat"
            config_file = hardhat_js if hardhat_js.exists() else hardhat_ts

        # Detect source directory (src or contracts)
        src_dir = project_path / "src"
        if not src_dir.exists():
            alt_src = project_path / "contracts"
            if alt_src.exists():
                src_dir = alt_src
            else:
                # Default back to src even if absent
                src_dir = project_path / "src"

        # Detect test directory (test or tests)
        test_dir = project_path / "test"
        if not test_dir.exists():
            alt_test = project_path / "tests"
            if alt_test.exists():
                test_dir = alt_test
            else:
                test_dir = project_path / "test"

        # If solc version wasn't detected from config, attempt detection from pragma
        if not solc_version:
            solc_version = ProjectDetector.detect_solidity_version(src_dir)

        return ProjectInfo(
            root_dir=project_path,
            framework=framework,
            src_dir=src_dir,
            test_dir=test_dir,
            solidity_version=solc_version,
            config_file=config_file
        )

    @staticmethod
    def _parse_foundry_solc(config_path: Path) -> Optional[str]:
        """Extract solc version from foundry.toml if specified."""
        try:
            content = config_path.read_text(encoding="utf-8")
            match = re.search(r'solc\s*=\s*["\']([^"\']+)["\']', content)
            if match:
                return match.group(1).strip()
        except Exception:
            pass
        return None

    @staticmethod
    def detect_solidity_version(source_dir: Path) -> Optional[str]:
        """Scan Solidity files in directory and find pragma solidity directive."""
        if not source_dir.exists():
            return None

        pragma_pattern = re.compile(r'pragma\s+solidity\s+([^;]+);')
        versions: List[str] = []

        for sol_file in source_dir.rglob("*.sol"):
            try:
                content = sol_file.read_text(encoding="utf-8")
                match = pragma_pattern.search(content)
                if match:
                    versions.append(match.group(1).strip())
            except Exception:
                continue

        if versions:
            # Return the first encountered pragma version
            return versions[0]
        return None
