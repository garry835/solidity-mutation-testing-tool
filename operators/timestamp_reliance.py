"""Timestamp Reliance Mutation Operator (TIMESTAMP_RELIANCE).

Mutates conditions and calculations involving block.timestamp (such as deadline
boundaries and comparison operators) to test whether test suites detect time-dependent faults.
"""

import re
from pathlib import Path
from typing import List

from operators.base_operator import BaseMutationOperator
from src.mutant_model import MutationCandidate
from src.solidity_parser import SolidityParser


class TimestampRelianceOperator(BaseMutationOperator):
    """Operator that mutates block.timestamp boundary conditions and expressions."""

    COMPARISON_MAP = {
        "<": "<=",
        "<=": "<",
        ">": ">=",
        ">=": ">",
        "==": "!=",
        "!=": "=="
    }

    @property
    def operator_id(self) -> str:
        return "TIMESTAMP_RELIANCE"

    @property
    def description(self) -> str:
        return (
            "Mutates comparison operators (<, <=, >, >=) and time offsets involving block.timestamp "
            "to test whether test suites detect off-by-one deadline and time-boundary faults."
        )

    def find_candidates(
        self,
        file_path: Path,
        source_code: str,
        parser: SolidityParser
    ) -> List[MutationCandidate]:
        candidates: List[MutationCandidate] = []

        # Pattern 1: block.timestamp <op> expression
        # e.g., block.timestamp < deadline
        pattern1 = re.compile(
            r'\bblock\.timestamp\s*(<=|>=|<|>|==|!=)\s*([a-zA-Z0-9_\.\[\]]+)',
            re.MULTILINE
        )

        for match in pattern1.finditer(source_code):
            orig_op = match.group(1)
            target_expr = match.group(2)
            full_match = match.group(0)
            
            mutated_op = self.COMPARISON_MAP.get(orig_op, "<=")
            mutated_text = f"block.timestamp {mutated_op} {target_expr}"

            start_offset = match.start(0)
            end_offset = match.end(0)
            start_line = parser.offset_to_line(start_offset)
            end_line = parser.offset_to_line(end_offset)

            # Check if inside comment
            line_str = source_code[source_code.rfind('\n', 0, start_offset) + 1 : source_code.find('\n', end_offset)]
            if line_str.strip().startswith("//") or line_str.strip().startswith("/*"):
                continue

            cand = MutationCandidate(
                candidate_id=f"CAND-TIMESTAMP-{start_line}-{start_offset}",
                operator_id=self.operator_id,
                file_path=file_path,
                start_line=start_line,
                end_line=end_line,
                start_offset=start_offset,
                end_offset=end_offset,
                original_text=full_match,
                replacement_text=mutated_text,
                description=(
                    f"Mutate timestamp boundary at line {start_line}: "
                    f"'{orig_op}' -> '{mutated_op}'"
                ),
                is_eligible=True,
                rejection_reason=None,
                metadata={
                    "original_operator": orig_op,
                    "mutated_operator": mutated_op
                }
            )
            candidates.append(cand)

        # Pattern 2: block.timestamp + offset (timelock calculation)
        pattern2 = re.compile(
            r'\bblock\.timestamp\s*(\+)\s*([a-zA-Z0-9_]+)',
            re.MULTILINE
        )
        for match in pattern2.finditer(source_code):
            full_match = match.group(0)
            target_var = match.group(2)
            mutated_text = f"block.timestamp - {target_var}"
            start_offset = match.start(0)
            end_offset = match.end(0)
            start_line = parser.offset_to_line(start_offset)
            end_line = parser.offset_to_line(end_offset)

            line_str = source_code[source_code.rfind('\n', 0, start_offset) + 1 : source_code.find('\n', end_offset)]
            if line_str.strip().startswith("//") or line_str.strip().startswith("/*"):
                continue

            cand = MutationCandidate(
                candidate_id=f"CAND-TIMESTAMP-CALC-{start_line}-{start_offset}",
                operator_id=self.operator_id,
                file_path=file_path,
                start_line=start_line,
                end_line=end_line,
                start_offset=start_offset,
                end_offset=end_offset,
                original_text=full_match,
                replacement_text=mutated_text,
                description=f"Invert timelock addition to subtraction at line {start_line}",
                is_eligible=True,
                rejection_reason=None,
                metadata={"type": "calculation", "original": "+", "mutated": "-"}
            )
            candidates.append(cand)

        return candidates

    def apply_mutation(
        self,
        source_code: str,
        candidate: MutationCandidate
    ) -> str:
        """Apply timestamp condition or calculation mutation."""
        start = candidate.start_offset
        end = candidate.end_offset
        return source_code[:start] + candidate.replacement_text + source_code[end:]
