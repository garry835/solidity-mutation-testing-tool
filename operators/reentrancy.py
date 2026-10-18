"""Reentrancy Mutation Operator (REENTRANCY).

Introduces unsafe ordering between external interactions and state updates,
evaluating whether test suites detect reentrancy vulnerabilities and broken invariants.
"""

import re
from pathlib import Path
from typing import List, Optional

from operators.base_operator import BaseMutationOperator
from src.mutant_model import MutationCandidate
from src.solidity_parser import SolidityParser


class ReentrancyOperator(BaseMutationOperator):
    """Operator that inverts Checks-Effects-Interactions to introduce reentrancy windows."""

    @property
    def operator_id(self) -> str:
        return "REENTRANCY"

    @property
    def description(self) -> str:
        return (
            "Reorders state balance reductions and external calls to evaluate "
            "whether test suites detect reentrancy vulnerability and state invariants."
        )

    def find_candidates(
        self,
        file_path: Path,
        source_code: str,
        parser: SolidityParser
    ) -> List[MutationCandidate]:
        candidates: List[MutationCandidate] = []

        # Regex to locate external call and optional subsequent require check
        # Patterns supported:
        # Pattern A: (bool success, ...) = payable(...).call{value: ...}(""); [optional require]
        # Pattern B: payable(...).transfer(...); or payable(...).send(...);
        call_pattern = re.compile(
            r'([ \t]*)(\([^\)]*\)\s*=\s*[^;]+?\.call\{value:[^;]+;\s*(?:\n[ \t]*require\([^;]+;\))?)',
            re.MULTILINE
        )

        for match in call_pattern.finditer(source_code):
            indent = match.group(1)
            call_block = match.group(2).strip()
            call_start = match.start(2)
            call_end = match.end(2)

            # Search backwards from call_start to find state updates in the same block
            # Look at lines immediately before the call up to the previous control statement or block open
            preceding_text = source_code[:call_start]
            lines = preceding_text.splitlines()

            # Collect preceding assignment statements (e.g. -=, +=, =)
            state_update_lines: List[str] = []
            collected_chars = 0

            for line in reversed(lines):
                stripped = line.strip()
                if not stripped:
                    collected_chars += len(line) + 1
                    continue
                if stripped.startswith("//") or stripped.startswith("/*"):
                    collected_chars += len(line) + 1
                    continue
                # If we hit require or if or block start, stop collecting
                if (
                    stripped.startswith("require")
                    or stripped.startswith("if")
                    or stripped.startswith("{")
                    or stripped.startswith("function")
                ):
                    break
                # Check if it looks like a state update assignment
                if any(op in stripped for op in ["-=", "+=", "="]) and stripped.endswith(";"):
                    state_update_lines.insert(0, line)
                    collected_chars += len(line) + 1
                else:
                    break

            if not state_update_lines:
                # No preceding state updates found to invert
                continue

            # Calculate start offset of the state update block
            state_updates_block = "\n".join(state_update_lines)
            start_offset = source_code.rfind(state_updates_block, 0, call_start)
            if start_offset == -1:
                continue

            end_offset = call_end
            start_line = parser.offset_to_line(start_offset)
            end_line = parser.offset_to_line(end_offset)

            original_block = source_code[start_offset:end_offset]

            # Construct mutated block:
            # External call first, followed by state updates
            call_formatted = "\n".join(f"{indent}{l.strip()}" for l in call_block.splitlines())
            updates_formatted = "\n".join(f"{indent}{l.strip()}" for l in state_update_lines)
            mutated_block = f"{call_formatted}\n{updates_formatted}"

            cand = MutationCandidate(
                candidate_id=f"CAND-REENTRANCY-{start_line}",
                operator_id=self.operator_id,
                file_path=file_path,
                start_line=start_line,
                end_line=end_line,
                start_offset=start_offset,
                end_offset=end_offset,
                original_text=original_block.strip(),
                replacement_text=mutated_block.strip(),
                description=(
                    f"Invert external interaction and state update at lines {start_line}-{end_line} "
                    "to expose reentrancy window."
                ),
                is_eligible=True,
                rejection_reason=None,
                metadata={
                    "state_updates": state_updates_block,
                    "external_call": call_block
                }
            )
            candidates.append(cand)

        return candidates

    def apply_mutation(
        self,
        source_code: str,
        candidate: MutationCandidate
    ) -> str:
        """Apply the reentrancy reordering mutation."""
        start = candidate.start_offset
        end = candidate.end_offset
        return source_code[:start] + candidate.replacement_text + source_code[end:]
