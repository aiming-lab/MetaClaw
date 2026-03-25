"""Benchmark check command — validate MetaClaw benchmark data integrity."""

from __future__ import annotations

import json
from pathlib import Path

from src.utils import resolve_path

from .all_tests_structure import AllTestsStructureChecker
from .basic_integrity import BasicIntegrityChecker
from .id_consistency import IdConsistencyChecker
from .file_format import FileFormatChecker
from .directory_structure import DirectoryStructureChecker
from .workspace_integrity import WorkspaceIntegrityChecker
from .session_format import SessionFormatChecker
from .questions_integrity import QuestionsIntegrityChecker


def run_check(path_arg: str) -> None:
    """Run comprehensive data integrity checks on a MetaClaw benchmark dataset.

    Validates:
    1. AllTests Structure     — all_tests.json top-level fields and test array
    2. Basic Integrity        — referenced files exist on disk
    3. ID Consistency         — agent/session/eval IDs are internally consistent
    4. File Format            — JSON/JSONL files are correctly formatted
    5. Directory Structure    — required directories exist
    6. Workspace Integrity    — workspace_src has required identity files
    7. Session Format         — session JSONL files have correct role structure
    8. Questions Integrity    — questions.json content and eval field validation

    Args:
        path_arg: Path to all_tests.json file.
    """
    all_tests_path = resolve_path(path_arg)
    if not all_tests_path.exists():
        raise FileNotFoundError(f"File not found: {all_tests_path}")
    if not all_tests_path.is_file():
        raise ValueError(f"Not a file: {all_tests_path}")

    print(f"Loading test data from: {all_tests_path}")
    print()
    with open(all_tests_path, encoding="utf-8") as f:
        test_data = json.load(f)

    tests = test_data.get("test", [])
    if not tests:
        print("No tests found in all_tests.json")
        return

    base_dir = all_tests_path.parent
    print(f"Base directory: {base_dir}")
    print(f"Total scenarios: {len(tests)}")
    print()
    print("=" * 70)
    print("Running Data Integrity Checks")
    print("=" * 70)
    print()

    checkers = [
        AllTestsStructureChecker(base_dir, test_data),
        BasicIntegrityChecker(base_dir, test_data),
        IdConsistencyChecker(base_dir, test_data),
        FileFormatChecker(base_dir, test_data),
        DirectoryStructureChecker(base_dir, test_data),
        WorkspaceIntegrityChecker(base_dir, test_data),
        SessionFormatChecker(base_dir, test_data),
        QuestionsIntegrityChecker(base_dir, test_data),
    ]

    results = []
    for checker in checkers:
        print(f"[{checker.name}] {checker.description}")
        result = checker.check(test_data)
        results.append(result)

        if result.passed:
            print(f"  PASSED")
        else:
            print(f"  FAILED ({len(result.errors)} errors)")

        if result.warnings:
            print(f"  {len(result.warnings)} warning(s)")

        print()

    # Summary
    print("=" * 70)
    print("Summary")
    print("=" * 70)
    print()

    total_errors = sum(len(r.errors) for r in results)
    total_warnings = sum(len(r.warnings) for r in results)
    passed_count = sum(1 for r in results if r.passed)
    failed_count = len(results) - passed_count

    print(f"Checks run: {len(results)}")
    print(f"  Passed: {passed_count}")
    print(f"  Failed: {failed_count}")
    print(f"  Total errors: {total_errors}")
    print(f"  Total warnings: {total_warnings}")
    print()

    if total_errors > 0:
        print("=" * 70)
        print("Errors")
        print("=" * 70)
        print()
        for result in results:
            if result.errors:
                print(f"[{result.name}]")
                for i, error in enumerate(result.errors, 1):
                    print(f"  {i}. {error}")
                print()

    if total_warnings > 0:
        print("=" * 70)
        print("Warnings")
        print("=" * 70)
        print()
        warning_count = 0
        for result in results:
            if result.warnings:
                print(f"[{result.name}]")
                for warning in result.warnings:
                    warning_count += 1
                    print(f"  {warning_count}. {warning}")
                    if warning_count >= 50:
                        remaining = total_warnings - 50
                        if remaining > 0:
                            print(f"  ... and {remaining} more warnings")
                        break
                print()
                if warning_count >= 50:
                    break

    print("=" * 70)
    if total_errors == 0:
        if total_warnings == 0:
            print("All checks passed. No errors or warnings.")
        else:
            print("All checks passed with warnings.")
    else:
        print("Some checks failed. Please fix the errors above.")
    print("=" * 70)
