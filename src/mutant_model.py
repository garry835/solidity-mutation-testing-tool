"""Data models for mutation candidates, mutants, and campaign results."""

from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class MutationStatus(str, Enum):
    """Classification of mutant evaluation outcome."""
    KILLED = "KILLED"
    SURVIVED = "SURVIVED"
    INVALID = "INVALID"
    EQUIVALENT = "EQUIVALENT"
    TIMEOUT = "TIMEOUT"
    UNRESOLVED = "UNRESOLVED"

    def __str__(self) -> str:
        return self.value


@dataclass
class MutationCandidate:
    """Represents an identified, eligible mutation location in source code."""
    candidate_id: str
    operator_id: str
    file_path: Path
    start_line: int
    end_line: int
    start_offset: int
    end_offset: int
    original_text: str
    replacement_text: str
    description: str
    is_eligible: bool = True
    rejection_reason: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert candidate to serializable dictionary."""
        d = asdict(self)
        d["file_path"] = str(self.file_path)
        return d


@dataclass
class Mutant:
    """Represents a concrete mutant applied to an isolated copy of the contract."""
    mutant_id: str
    operator_name: str
    source_file: str
    line_number: int
    original_source_hash: str
    mutated_source_hash: str
    transformation: Dict[str, str]
    description: str
    status: MutationStatus = MutationStatus.UNRESOLVED
    status_reason: str = ""
    compilation_success: bool = False
    execution_time_seconds: float = 0.0
    stdout: str = ""
    stderr: str = ""
    exit_code: Optional[int] = None
    failing_tests: List[str] = field(default_factory=list)
    passing_tests: List[str] = field(default_factory=list)
    failure_details: str = ""
    suspected_equivalent: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert mutant record to serializable dictionary."""
        d = asdict(self)
        d["status"] = self.status.value
        return d
