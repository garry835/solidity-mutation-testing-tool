"""Command Line Interface for the Solidity Mutation Testing Framework."""

import argparse
import logging
import sys
from pathlib import Path
from typing import List, Optional

from operators import get_available_operators
from src import __version__
from src.exceptions import BaselineVerificationError, MutationToolError
from src.logging_config import setup_logger
from src.mutation_engine import MutationEngine


def parse_args(args: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        prog="solidity-mutate",
        description="Solidity Mutation Testing Framework — Injects context-aware bug operators to measure test effectiveness."
    )

    parser.add_argument(
        "--project", "-p",
        type=str,
        help="Path to the Solidity project directory (containing foundry.toml or contracts)."
    )
    parser.add_argument(
        "--operators", "-o",
        type=str,
        help="Comma-separated list of mutation operators to apply (e.g. 'unchecked_math,reentrancy')."
    )
    parser.add_argument(
        "--timeout", "-t",
        type=int,
        default=60,
        help="Timeout in seconds for compilation and test execution (default: 60)."
    )
    parser.add_argument(
        "--output",
        type=str,
        default="./reports",
        help="Directory where JSON and HTML reports will be saved (default: ./reports)."
    )
    parser.add_argument(
        "--list-operators",
        action="store_true",
        help="List all registered mutation operators and exit."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Scan and list eligible candidate mutation sites without executing tests."
    )
    parser.add_argument(
        "--forge-bin",
        type=str,
        default=None,
        help="Explicit path to the 'forge' executable."
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable detailed debug logging."
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}"
    )

    return parser.parse_args(args)


def main(cli_args: Optional[List[str]] = None) -> int:
    """CLI main execution entry point."""
    args = parse_args(cli_args)

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logger = setup_logger(level=log_level)

    # Handle --list-operators
    if args.list_operators:
        print("\nRegistered Solidity Mutation Operators:")
        print("=" * 60)
        for op in get_available_operators():
            print(f"- {op.operator_id}:")
            print(f"    {op.description}\n")
        return 0

    if not args.project:
        print("Error: --project path is required. Use --help for usage instructions.", file=sys.stderr)
        return 1

    project_path = Path(args.project).resolve()
    if not project_path.exists():
        print(f"Error: Project path '{project_path}' does not exist.", file=sys.stderr)
        return 1

    # Parse operator list
    operator_list = None
    if args.operators:
        operator_list = [op.strip() for op in args.operators.split(",") if op.strip()]

    output_dir = Path(args.output).resolve()
    cmd_str = " ".join(sys.argv)

    try:
        engine = MutationEngine(
            project_path=project_path,
            operator_names=operator_list,
            timeout_seconds=args.timeout,
            forge_bin_path=args.forge_bin,
            output_dir=output_dir,
            logger=logger
        )

        if args.dry_run:
            logger.info("Running in DRY-RUN mode (discovery only)...")
            candidates = engine.discover_candidates()
            print("\nDiscovered Mutation Candidates:")
            print("=" * 80)
            for c in candidates:
                print(f"[{c.operator_id}] {c.file_path}:{c.start_line} -> {c.description}")
            print(f"\nTotal eligible candidates: {len(candidates)}")
            print(f"Total rejected candidates: {len(engine.rejected_candidates)}")
            return 0

        # Execute campaign
        logger.info(f"Starting mutation campaign on: {project_path.name}")
        mutants, metrics = engine.run_campaign()
        json_path, html_path = engine.generate_reports(command_line=cmd_str)

        # Print concise terminal summary
        print("\n" + "=" * 65)
        print("           MUTATION TESTING CAMPAIGN SUMMARY")
        print("=" * 65)
        print(f" Target Project:           {project_path.name}")
        print(f" Overall Mutation Score:   {metrics.mutation_score}%")
        print(f" Total Mutants Generated:  {metrics.total_mutants}")
        print(f" Killed Mutants:           {metrics.killed}")
        print(f" Surviving Mutants:        {metrics.survived}")
        print(f" Invalid / Compile Errors: {metrics.invalid}")
        print(f" Equivalent / Suspected:   {metrics.equivalent}")
        print(f" Timeouts:                 {metrics.timeout}")
        print(f" Unresolved:               {metrics.unresolved}")
        print(f" Compilation Rate:         {metrics.compilation_success_rate}%")
        print(f" Total Execution Time:     {metrics.total_execution_time_seconds:.2f}s")
        print("-" * 65)
        print(" OPERATOR BREAKDOWN:")
        for op_name, op in metrics.operator_scores.items():
            print(f"  * {op_name:<20} Score: {op.mutation_score:>6.2f}% (Killed: {op.killed}/{op.total_mutants})")
        print("=" * 65)
        print(f" JSON Report: {json_path}")
        print(f" HTML Report: {html_path}")
        print("=" * 65 + "\n")

        return 0

    except BaselineVerificationError as e:
        logger.error(f"Baseline validation failed: {e}")
        return 2
    except MutationToolError as e:
        logger.error(f"Mutation tool error: {e}")
        return 1
    except Exception as e:
        logger.exception(f"Unexpected fatal error: {e}")
        return 3


if __name__ == "__main__":
    sys.exit(main())
