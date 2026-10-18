"""Base class for all Solidity mutation operators."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Tuple

from src.mutant_model import MutationCandidate
from src.solidity_parser import SolidityParser


class BaseMutationOperator(ABC):
    """Abstract base class defining the contract for all mutation operators."""

    @property
    @abstractmethod
    def operator_id(self) -> str:
        """Unique uppercase operator identifier, e.g. 'UNCHECKED_MATH'."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable explanation of the operator's purpose and fault model."""
        pass

    @abstractmethod
    def find_candidates(
        self,
        file_path: Path,
        source_code: str,
        parser: SolidityParser
    ) -> List[MutationCandidate]:
        """Scan source code / AST and return eligible and validated mutation candidates.

        Args:
            file_path: Path to the target Solidity source file.
            source_code: Full string content of the source file.
            parser: SolidityParser instance with AST and offset indexing.

        Returns:
            List of MutationCandidate objects.
        """
        pass

    @abstractmethod
    def apply_mutation(
        self,
        source_code: str,
        candidate: MutationCandidate
    ) -> str:
        """Generate mutated source code by applying the candidate transformation.

        Args:
            source_code: Original source code string.
            candidate: Validated candidate to apply.

        Returns:
            Mutated source code string.
        """
        pass
