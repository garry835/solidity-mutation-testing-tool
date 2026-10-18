"""Unit tests for Solidity AST and source parser."""

from pathlib import Path
from src.solidity_parser import SolidityParser, SourceLocation


def test_line_offset_mapping():
    """Verify offset to line conversion."""
    source = "line 1\nline 2\nline 3\nline 4\n"
    parser = SolidityParser(source)
    assert parser.offset_to_line(0) == 1
    assert parser.offset_to_line(7) == 2
    assert parser.offset_to_line(14) == 3


def test_unchecked_block_detection():
    """Verify detection of unchecked blocks and nested offset queries."""
    source = """
pragma solidity ^0.8.0;

contract Math {
    function safeAdd(uint256 a, uint256 b) public returns (uint256) {
        return a + b;
    }

    function unsafeAdd(uint256 a, uint256 b) public returns (uint256) {
        unchecked {
            return a + b;
        }
    }
}
"""
    parser = SolidityParser(source)
    blocks = parser.find_unchecked_blocks()
    assert len(blocks) == 1

    unchecked_offset = source.find("return a + b;", source.find("unchecked"))
    safe_offset = source.find("return a + b;")

    assert parser.is_offset_in_unchecked(unchecked_offset) is True
    assert parser.is_offset_in_unchecked(safe_offset) is False


def test_source_snippet_extraction():
    """Verify accurate extraction of source code snippets using SourceLocation."""
    source = "contract Test { uint256 count; }"
    parser = SolidityParser(source)
    loc = SourceLocation(start_offset=0, length=13, end_offset=13, start_line=1, end_line=1)
    snippet = parser.get_source_snippet(loc)
    assert snippet == "contract Test"
