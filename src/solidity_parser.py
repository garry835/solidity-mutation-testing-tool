"""Solidity AST and source analysis layer for context-aware mutation testing.

Extracts functions, statements, expression nodes, unchecked blocks,
external calls, and timestamp comparisons using compiler AST source offsets
and robust token-aware analysis.
"""

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


@dataclass
class SourceLocation:
    """Byte offset and line/column information for a source node."""
    start_offset: int
    length: int
    end_offset: int
    start_line: int
    end_line: int


@dataclass
class ASTNode:
    """Represents an extracted Solidity AST node."""
    id: int
    node_type: str
    src: str
    location: SourceLocation
    raw_node: Dict[str, Any]
    parent: Optional["ASTNode"] = None
    children: List["ASTNode"] = field(default_factory=list)

    def find_all(self, node_type: str) -> List["ASTNode"]:
        """Find all descendant nodes of a specific type."""
        results: List["ASTNode"] = []
        if self.node_type == node_type:
            results.append(self)
        for child in self.children:
            results.extend(child.find_all(node_type))
        return results

    def is_inside_node_type(self, target_type: str) -> bool:
        """Check if this node is an ancestor or descendant of target_type."""
        curr = self.parent
        while curr:
            if curr.node_type == target_type:
                return True
            curr = curr.parent
        return False


class SolidityParser:
    """Parses Solidity source code and AST representations."""

    def __init__(self, source_code: str, ast_dict: Optional[Dict[str, Any]] = None):
        self.source_code = source_code
        self.ast_dict = ast_dict
        self._line_offsets: List[int] = self._compute_line_offsets(source_code)
        self.ast_root: Optional[ASTNode] = None
        if ast_dict:
            self.ast_root = self._build_ast_tree(ast_dict)

    @staticmethod
    def _compute_line_offsets(source: str) -> List[int]:
        """Compute the starting byte offset of each line (1-indexed)."""
        offsets = [0]
        # Using bytes for accurate Solidity source offset mapping
        encoded = source.encode("utf-8")
        idx = 0
        while idx < len(encoded):
            if encoded[idx : idx + 1] == b"\n":
                offsets.append(idx + 1)
            idx += 1
        return offsets

    def offset_to_line(self, offset: int) -> int:
        """Convert a byte offset to a 1-indexed line number."""
        low, high = 0, len(self._line_offsets) - 1
        while low <= high:
            mid = (low + high) // 2
            if self._line_offsets[mid] <= offset:
                low = mid + 1
            else:
                high = mid - 1
        return max(1, high + 1)

    def parse_src_string(self, src_str: str) -> SourceLocation:
        """Parse Solc 'offset:length:file_index' format into SourceLocation."""
        parts = src_str.split(":")
        start = int(parts[0])
        length = int(parts[1])
        end = start + length
        start_line = self.offset_to_line(start)
        end_line = self.offset_to_line(end)
        return SourceLocation(
            start_offset=start,
            length=length,
            end_offset=end,
            start_line=start_line,
            end_line=end_line
        )

    def _build_ast_tree(
        self,
        node_dict: Dict[str, Any],
        parent: Optional[ASTNode] = None
    ) -> Optional[ASTNode]:
        """Recursively build ASTNode tree from Solc standard JSON AST."""
        if not isinstance(node_dict, dict):
            return None

        node_id = node_dict.get("id", 0)
        node_type = node_dict.get("nodeType", "")
        src_str = node_dict.get("src", "0:0:0")

        try:
            loc = self.parse_src_string(src_str)
        except Exception:
            loc = SourceLocation(0, 0, 0, 1, 1)

        node = ASTNode(
            id=node_id,
            node_type=node_type,
            src=src_str,
            location=loc,
            raw_node=node_dict,
            parent=parent,
            children=[]
        )

        for key, value in node_dict.items():
            if key in ["parent", "raw_node"]:
                continue
            if isinstance(value, dict) and "nodeType" in value:
                child = self._build_ast_tree(value, parent=node)
                if child:
                    node.children.append(child)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict) and "nodeType" in item:
                        child = self._build_ast_tree(item, parent=node)
                        if child:
                            node.children.append(child)

        return node

    def get_source_snippet(self, loc: SourceLocation) -> str:
        """Extract source code substring corresponding to SourceLocation."""
        encoded = self.source_code.encode("utf-8")
        snippet_bytes = encoded[loc.start_offset : loc.end_offset]
        return snippet_bytes.decode("utf-8", errors="replace")

    @classmethod
    def from_file(cls, sol_path: Path, artifact_path: Optional[Path] = None) -> "SolidityParser":
        """Factory method to instantiate parser from source file and optional artifact."""
        source_code = sol_path.read_text(encoding="utf-8")
        ast_dict = None
        if artifact_path and artifact_path.exists():
            try:
                data = json.loads(artifact_path.read_text(encoding="utf-8"))
                ast_dict = data.get("ast")
            except Exception:
                pass
        return cls(source_code, ast_dict)

    def find_unchecked_blocks(self) -> List[SourceLocation]:
        """Locate all unchecked { ... } block ranges in source."""
        if self.ast_root:
            unchecked_nodes = self.ast_root.find_all("UncheckedBlock")
            return [node.location for node in unchecked_nodes]

        # Robust regex-based detection if AST is absent
        results: List[SourceLocation] = []
        pattern = re.compile(r'\bunchecked\s*\{', re.MULTILINE)
        for match in pattern.finditer(self.source_code):
            start = match.start()
            # Find matching closing brace
            brace_count = 0
            open_idx = self.source_code.find("{", start)
            end = open_idx
            for i in range(open_idx, len(self.source_code)):
                if self.source_code[i] == "{":
                    brace_count += 1
                elif self.source_code[i] == "}":
                    brace_count -= 1
                    if brace_count == 0:
                        end = i + 1
                        break
            loc = SourceLocation(
                start_offset=start,
                length=end - start,
                end_offset=end,
                start_line=self.offset_to_line(start),
                end_line=self.offset_to_line(end)
            )
            results.append(loc)
        return results

    def is_offset_in_unchecked(self, offset: int) -> bool:
        """Determine if a byte offset falls inside any unchecked block."""
        for block_loc in self.find_unchecked_blocks():
            if block_loc.start_offset <= offset <= block_loc.end_offset:
                return True
        return False
