"""Executes test suites using Foundry/Forge and parses test execution results."""

import re
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass
class TestRunResult:
    """Outcome of running test suite against a project."""
    __test__ = False
    success: bool
    exit_code: int
    duration_seconds: float
    stdout: str
    stderr: str
    passing_tests: List[str] = field(default_factory=list)
    failing_tests: List[str] = field(default_factory=list)
    failure_details: str = ""
    is_timeout: bool = False
    is_compiler_error: bool = False
    is_crash: bool = False


class TestRunner:
    """Runs test suite using Foundry/Forge and parses structured results."""

    def __init__(self, forge_bin_path: str):
        self.forge_bin = forge_bin_path

    def run_tests(
        self,
        project_root: Path,
        timeout_seconds: int = 60,
        extra_args: Optional[List[str]] = None
    ) -> TestRunResult:
        """Execute 'forge test' against specified project directory.

        Args:
            project_root: Root directory containing smart contracts and tests.
            timeout_seconds: Time limit for test execution.
            extra_args: Additional command line flags for forge test.

        Returns:
            TestRunResult containing parsed test outcomes.
        """
        start_time = time.perf_counter()
        cmd = [self.forge_bin, "test", "--root", str(project_root)]
        if extra_args:
            cmd.extend(extra_args)

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
            exit_code = proc.returncode

            # Check for compiler failure during forge test
            is_compiler_error = (
                "compiler run failed" in stdout.lower()
                or "error[" in stdout.lower()
                or "error:" in stdout.lower()
                or "error[" in stderr.lower()
            )

            # Check for catastrophic test runner crash
            is_crash = exit_code != 0 and not is_compiler_error and "[FAIL" not in stdout

            passing_tests, failing_tests, failure_details = self._parse_test_output(stdout)

            success = (exit_code == 0) and (len(failing_tests) == 0)

            return TestRunResult(
                success=success,
                exit_code=exit_code,
                duration_seconds=duration,
                stdout=stdout,
                stderr=stderr,
                passing_tests=passing_tests,
                failing_tests=failing_tests,
                failure_details=failure_details,
                is_timeout=False,
                is_compiler_error=is_compiler_error,
                is_crash=is_crash
            )

        except subprocess.TimeoutExpired:
            duration = time.perf_counter() - start_time
            return TestRunResult(
                success=False,
                exit_code=-1,
                duration_seconds=duration,
                stdout="",
                stderr=f"Test run timed out after {timeout_seconds} seconds",
                is_timeout=True,
                failure_details=f"Execution exceeded timeout limit ({timeout_seconds}s)"
            )
        except Exception as e:
            duration = time.perf_counter() - start_time
            return TestRunResult(
                success=False,
                exit_code=-1,
                duration_seconds=duration,
                stdout="",
                stderr=str(e),
                is_crash=True,
                failure_details=f"Test runner error: {str(e)}"
            )

    @staticmethod
    def _parse_test_output(stdout: str) -> tuple[List[str], List[str], str]:
        """Extract passing tests, failing tests, and failure snippets from stdout."""
        passing: List[str] = []
        failing: List[str] = []
        failure_lines: List[str] = []

        # Matches [PASS] testName()
        pass_pattern = re.compile(r'\[PASS\]\s+([a-zA-Z0-9_]+)\(')
        # Matches [FAIL: reason] testName()
        fail_pattern = re.compile(r'\[FAIL(?:[:\s][^\]]*)?\]\s+([a-zA-Z0-9_]+)\(')

        for line in stdout.splitlines():
            line_str = line.strip()
            pass_match = pass_pattern.search(line_str)
            if pass_match:
                passing.append(pass_match.group(1))

            fail_match = fail_pattern.search(line_str)
            if fail_match:
                test_name = fail_match.group(1)
                failing.append(test_name)
                failure_lines.append(line_str)

        # Look for the "Failing tests:" section in Forge output
        if "Failing tests:" in stdout:
            section = stdout.split("Failing tests:")[1].split("Encountered")[0].strip()
            failure_lines.append(section)

        failure_details = "\n".join(failure_lines).strip()
        return passing, failing, failure_details
