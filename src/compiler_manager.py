"""Orchestrates Solidity project compilation via Foundry/Forge."""

import os
import re
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from src.exceptions import ToolchainNotFoundError


@dataclass
class CompilationResult:
    """Result of compiling a Solidity project."""
    success: bool
    exit_code: int
    duration_seconds: float
    stdout: str
    stderr: str
    error_summary: str = ""


class CompilerManager:
    """Manages compilation of original and mutated Solidity projects."""

    def __init__(self, forge_bin_path: Optional[str] = None):
        self.forge_bin = self._resolve_forge_binary(forge_bin_path)

    @staticmethod
    def _resolve_forge_binary(configured_path: Optional[str] = None) -> str:
        """Find forge binary from config, PATH, or ~/.foundry/bin."""
        if configured_path and Path(configured_path).exists():
            return str(Path(configured_path).resolve())

        # Check PATH
        which_forge = shutil.which("forge") or shutil.which("forge.exe")
        if which_forge:
            return which_forge

        # Check ~/.foundry/bin
        home = Path.home()
        exe_name = "forge.exe" if os.name == "nt" else "forge"
        foundry_bin = home / ".foundry" / "bin" / exe_name
        if foundry_bin.exists():
            return str(foundry_bin.resolve())

        raise ToolchainNotFoundError(
            "Foundry 'forge' binary not found. Please install Foundry or specify path in config."
        )

    def ensure_ast_enabled(self, project_root: Path) -> None:
        """Ensure foundry.toml has 'ast = true' so compiler artifacts include AST."""
        config_path = project_root / "foundry.toml"
        if not config_path.exists():
            return
        try:
            content = config_path.read_text(encoding="utf-8")
            if "ast = true" not in content and "ast=true" not in content:
                content += "\nast = true\n"
                config_path.write_text(content, encoding="utf-8")
        except Exception:
            pass

    def compile_project(self, project_root: Path, timeout_seconds: int = 60) -> CompilationResult:
        """Compile a Foundry project using 'forge build'.

        Args:
            project_root: Root directory of the Foundry project.
            timeout_seconds: Maximum time allowed for compilation.

        Returns:
            CompilationResult with status and execution details.
        """
        start_time = time.perf_counter()
        cmd = [self.forge_bin, "build", "--root", str(project_root)]

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout_seconds,
                check=False
            )
            duration = time.perf_counter() - start_time
            stdout = proc.stdout or ""
            stderr = proc.stderr or ""
            success = proc.returncode == 0

            error_summary = ""
            if not success:
                # Extract compiler error lines
                lines = (stdout + "\n" + stderr).splitlines()
                err_lines = [l for l in lines if "error[" in l.lower() or "error:" in l.lower()]
                error_summary = "\n".join(err_lines[:5]) if err_lines else stderr[:500]

            return CompilationResult(
                success=success,
                exit_code=proc.returncode,
                duration_seconds=duration,
                stdout=stdout,
                stderr=stderr,
                error_summary=error_summary
            )

        except subprocess.TimeoutExpired:
            duration = time.perf_counter() - start_time
            return CompilationResult(
                success=False,
                exit_code=-1,
                duration_seconds=duration,
                stdout="",
                stderr=f"Compilation timed out after {timeout_seconds}s",
                error_summary=f"Compilation timed out after {timeout_seconds}s"
            )
        except Exception as e:
            duration = time.perf_counter() - start_time
            return CompilationResult(
                success=False,
                exit_code=-1,
                duration_seconds=duration,
                stdout="",
                stderr=str(e),
                error_summary=str(e)
            )
