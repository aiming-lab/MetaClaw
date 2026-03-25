"""MetaClaw Benchmark CLI — entry point for metaclaw-bench tools.

Commands:
  infer         Run batch inference on a test dataset
  scoring       Score infer results against correct answers
  report        Generate accuracy and token-usage report
  report-ratio  Compute compaction ratios between base and compaction reports
  run           Run infer → scoring → report pipeline end-to-end
  check         Validate data integrity of benchmark dataset
  clean         Remove work/ isolation directories created by infer

Usage examples:
  metaclaw-bench infer -i data/metaclaw-bench/all_tests.json \\
      -o /tmp/infer_out -n 1

  metaclaw-bench scoring -i data/metaclaw-bench/all_tests.json \\
      -r /tmp/infer_out

  metaclaw-bench report -r /tmp/infer_out \\
      -o /tmp/report_out

  metaclaw-bench run -i data/metaclaw-bench/all_tests.json \\
      -o /tmp/run_out
"""

from __future__ import annotations

import argparse
import sys


# ---------------------------------------------------------------------------
# infer
# ---------------------------------------------------------------------------


def cmd_infer(args: argparse.Namespace) -> None:
    from src.infer.infer_cmd import run_infer
    run_infer(
        input_arg=args.input,
        output_arg=args.output,
        workers=args.workers,
        retry=args.retry,
        scene_per_train=args.scene_per_train,
        memory=args.memory,
        memory_proxy_port=args.memory_proxy_port,
    )


# ---------------------------------------------------------------------------
# scoring
# ---------------------------------------------------------------------------


def cmd_scoring(args: argparse.Namespace) -> None:
    from src.scoring.scoring_cmd import run_scoring
    run_scoring(
        input_path=args.input,
        result_dir=args.result,
    )


# ---------------------------------------------------------------------------
# report
# ---------------------------------------------------------------------------


def cmd_report(args: argparse.Namespace) -> None:
    from src.report.report_cmd import run_report
    run_report(
        result_dir=args.result,
        compaction_path=args.compaction,
        output_dir=args.output,
    )


# ---------------------------------------------------------------------------
# report-ratio
# ---------------------------------------------------------------------------


def cmd_report_ratio(args: argparse.Namespace) -> None:
    from src.report.ratio_cmd import run_report_ratio
    run_report_ratio(
        base_path=args.base,
        compaction_paths=args.compactions,
        output_dir=args.output,
    )


# ---------------------------------------------------------------------------
# run
# ---------------------------------------------------------------------------


def cmd_run(args: argparse.Namespace) -> None:
    from src.run.run_cmd import run_run
    run_run(
        input_arg=args.input,
        output_arg=args.output,
        workers=args.workers,
        retry=args.retry,
        scene_per_train=args.scene_per_train,
        memory=args.memory,
        memory_proxy_port=args.memory_proxy_port,
    )


# ---------------------------------------------------------------------------
# check
# ---------------------------------------------------------------------------


def cmd_check(args: argparse.Namespace) -> None:
    from src.check.check_cmd import run_check
    run_check(path_arg=args.path)


# ---------------------------------------------------------------------------
# clean
# ---------------------------------------------------------------------------


def cmd_clean(args: argparse.Namespace) -> None:
    from src.clean.clean_cmd import run_clean
    run_clean(path_arg=args.path)


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="metaclaw-bench",
        description="MetaClaw Evolution Benchmark tools",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # ---- infer ----
    infer_parser = subparsers.add_parser(
        "infer",
        help="Run batch inference on a test dataset",
    )
    infer_parser.add_argument(
        "-i", "--input",
        required=True,
        help="Path to all_tests.json, or a directory containing all_tests.json files",
    )
    infer_parser.add_argument(
        "-o", "--output",
        required=True,
        help="Output directory path",
    )
    infer_parser.add_argument(
        "-w", "--workers",
        type=int,
        default=1,
        help="Maximum number of concurrent tests (default: 1)",
    )
    infer_parser.add_argument(
        "-n", "--retry",
        type=int,
        default=0,
        help="Number of retries per failed question (default: 0)",
    )
    infer_parser.add_argument(
        "--scene-per-train",
        type=int,
        default=None,
        help="Trigger 'metaclaw train-step' every N test scenes (default: disabled)",
    )
    infer_parser.add_argument(
        "--memory",
        action="store_true",
        default=False,
        help="Trigger memory ingestion after each test scene via POST /v1/memory/ingest",
    )
    infer_parser.add_argument(
        "--memory-proxy-port",
        type=int,
        default=30000,
        help="MetaClaw proxy port for memory ingest calls (default: 30000)",
    )

    # ---- scoring ----
    scoring_parser = subparsers.add_parser(
        "scoring",
        help="Score infer results against correct answers",
    )
    scoring_parser.add_argument(
        "-i", "--input",
        required=True,
        help="Path to all_tests.json",
    )
    scoring_parser.add_argument(
        "-r", "--result",
        required=True,
        help="Directory to recursively search for infer_result.json files",
    )

    # ---- report ----
    report_parser = subparsers.add_parser(
        "report",
        help="Generate accuracy and token-usage report from scoring results",
    )
    report_parser.add_argument(
        "-r", "--result",
        required=True,
        help="Directory containing scoring.json files",
    )
    report_parser.add_argument(
        "-c", "--compaction",
        default=None,
        help="Optional path to compaction_results.json for token aggregation",
    )
    report_parser.add_argument(
        "-o", "--output",
        default=None,
        help="Output directory for report.json and report.md (if not provided, only print to terminal)",
    )

    # ---- report-ratio ----
    ratio_parser = subparsers.add_parser(
        "report-ratio",
        help="Compute compaction ratios between base and compaction reports",
    )
    ratio_parser.add_argument(
        "-b", "--base",
        required=True,
        help="Path to baseline report.json",
    )
    ratio_parser.add_argument(
        "-c", "--compactions",
        nargs="+",
        required=True,
        help="Paths to compaction report.json files or directories",
    )
    ratio_parser.add_argument(
        "-o", "--output",
        default=None,
        help="Output directory for ratio_report.json (if not provided, only print to terminal)",
    )

    # ---- run ----
    run_parser = subparsers.add_parser(
        "run",
        help="Run infer → scoring → report pipeline end-to-end",
    )
    run_parser.add_argument(
        "-i", "--input",
        required=True,
        help="Path to all_tests.json, or a directory containing all_tests.json files",
    )
    run_parser.add_argument(
        "-o", "--output",
        required=True,
        help="Output directory path",
    )
    run_parser.add_argument(
        "-w", "--workers",
        type=int,
        default=1,
        help="Maximum number of concurrent tests (default: 1)",
    )
    run_parser.add_argument(
        "-n", "--retry",
        type=int,
        default=0,
        help="Number of retries per failed question (default: 0)",
    )
    run_parser.add_argument(
        "--scene-per-train",
        type=int,
        default=None,
        help="Trigger 'metaclaw train-step' every N test scenes (default: disabled)",
    )
    run_parser.add_argument(
        "--memory",
        action="store_true",
        default=False,
        help="Trigger memory ingestion after each test scene via POST /v1/memory/ingest",
    )
    run_parser.add_argument(
        "--memory-proxy-port",
        type=int,
        default=30000,
        help="MetaClaw proxy port for memory ingest calls (default: 30000)",
    )

    # ---- check ----
    check_parser = subparsers.add_parser(
        "check",
        help="Validate data integrity of benchmark dataset",
    )
    check_parser.add_argument(
        "-p", "--path",
        required=True,
        help="Path to all_tests.json",
    )

    # ---- clean ----
    clean_parser = subparsers.add_parser(
        "clean",
        help="Remove work/ isolation directories created by infer",
    )
    clean_parser.add_argument(
        "-p", "--path",
        required=True,
        help="Root path to search for work/ directories (recursively)",
    )

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    if args.command == "infer":
        cmd_infer(args)
    elif args.command == "scoring":
        cmd_scoring(args)
    elif args.command == "report":
        cmd_report(args)
    elif args.command == "report-ratio":
        cmd_report_ratio(args)
    elif args.command == "run":
        cmd_run(args)
    elif args.command == "check":
        cmd_check(args)
    elif args.command == "clean":
        cmd_clean(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
