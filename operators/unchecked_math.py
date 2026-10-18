"""Unchecked Arithmetic Mutation Operator (UNCHECKED_MATH).

Injects unchecked arithmetic blocks around eligible Solidity 0.8+ arithmetic
operations to evaluate whether test suites detect unsafe overflow/underflow behavior.
"""

import re
from pathlib import Path
from typing import List

from operators.base_operator import BaseMutationOperator
from src.mutant_model import MutationCandidate
from src.solidity_parser import SolidityParser


class UncheckedMathOperator(BaseMutationOperator):
    """Operator that wraps eligible checked arithmetic in unchecked { ... } blocks."""

    @property
    def operator_id(self) -> str:
        return "UNCHECKED_MATH"

    @property
    def description(self) -> str:
        return (
            "Wraps Solidity 0.8+ arithmetic operations in an unchecked block "
            "to assess test suite detection of integer overflow or underflow faults."
        )

    def find_candidates(
        self,
        file_path: Path,
        source_code: str,
        parser: SolidityParser
    ) -> List[MutationCandidate]:
        candidates: List[MutationCandidate] = []
        
        # Regex to locate compound assignments and arithmetic assignment statements
        # Matches: variable/mapping += / -= / *= expression;
        stmt_pattern = re.compile(
            r'([ \t]*)([a-zA-Z0-9_\[\]\(\)\.\>\<\-]+?\s*(\+=|-=|\*=)\s*[^;]+;)',
            re.MULTILINE
        )

        for match in stmt_pattern.finditer(source_code):
            indent = match.group(1)
            full_stmt = match.group(2).strip()
            start_offset = match.start(2)
            end_offset = match.end(2)
            start_line = parser.offset_to_line(start_offset)
            end_line = parser.offset_to_line(end_offset)

            # Check precondition: already inside an unchecked block?
            if parser.is_offset_in_unchecked(start_offset):
                candidates.append(
                    MutationCandidate(
                        candidate_id=f"CAND-UNCHECKED-{start_line}",
                        operator_id=self.operator_id,
                        file_path=file_path,
                        start_line=start_line,
                        end_line=end_line,
                        start_offset=start_offset,
                        end_offset=end_offset,
                        original_text=full_stmt,
                        replacement_text=full_stmt,
                        description="Statement already inside unchecked block",
                        is_eligible=False,
                        rejection_reason="Already inside unchecked block"
                    )
                )
                continue

            # Check if this statement is part of a comment or string literal
            line_content = source_code[source_code.rfind('\n', 0, start_offset) + 1 : source_code.find('\n', end_offset)]
            if line_content.strip().startswith("//") or line_content.strip().startswith("/*"):
                continue

            # Form replacement: unchecked { statement; }
            replacement = f"unchecked {{ {full_stmt} }}"

            cand = MutationCandidate(
                candidate_id=f"CAND-UNCHECKED-{start_line}-{start_offset}",
                operator_id=self.operator_id,
                file_path=file_path,
                start_line=start_line,
                end_line=end_line,
                start_offset=start_offset,
                end_offset=end_offset,
                original_text=full_stmt,
                replacement_text=replacement,
                description=f"Wrap arithmetic operation in unchecked block at line {start_line}",
                is_eligible=True,
                rejection_reason=None,
                metadata={"indent": indent, "statement": full_stmt}
            )
            candidates.append(cand)

        return candidates

    def apply_mutation(
        self,
        source_code: str,
        candidate: MutationCandidate
    ) -> str:
        """Apply unchecked block replacement to source code."""
        start = candidate.start_offset
        end = candidate.end_offset
        return source_code[:start] + candidate.replacement_text + source_code[end:]
