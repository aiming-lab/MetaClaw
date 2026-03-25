"""Checker: validates JSON and JSONL file formatting."""

from __future__ import annotations

import json
from typing import Any

from src.utils import resolve_path
from .base import BaseChecker, CheckResult


class FileFormatChecker(BaseChecker):
    """Checks file format correctness (JSON, JSONL, empty files)."""

    @property
    def name(self) -> str:
        return "File Format"

    @property
    def description(self) -> str:
        return "Validates JSON/JSONL files are correctly formatted"

    def check(self, test_data: dict[str, Any]) -> CheckResult:
        result = CheckResult(name=self.name, passed=True)
        tests = test_data.get("test", [])

        try:
            openclaw_state_dir = resolve_path(test_data.get("openclaw_state_dir", ""))
        except Exception:
            openclaw_state_dir = None

        try:
            eval_dir = resolve_path(test_data.get("eval_dir", ""))
        except Exception:
            eval_dir = None

        for test in tests:
            errs, warns = self._check_test(test, openclaw_state_dir, eval_dir)
            result.errors.extend(errs)
            result.warnings.extend(warns)

        result.passed = len(result.errors) == 0
        result.details["tests_checked"] = len(tests)
        return result

    def _check_test(
        self,
        test: dict[str, Any],
        openclaw_state_dir,
        eval_dir,
    ) -> tuple[list[str], list[str]]:
        errors: list[str] = []
        warnings: list[str] = []
        test_id = test.get("id", "<unknown>")
        agent_id = test.get("agent", "")
        eval_name = test.get("eval", "")

        # Check JSONL session files
        if openclaw_state_dir and agent_id:
            sessions_dir = openclaw_state_dir / "agents" / agent_id / "sessions"
            if sessions_dir.exists():
                for sess_file in sessions_dir.glob("*.jsonl"):
                    errs2 = self._check_jsonl(sess_file, test_id)
                    errors.extend(errs2)

        # Check questions.json is valid JSON
        if eval_dir and eval_name:
            questions_path = eval_dir / eval_name / "questions.json"
            if questions_path.exists():
                try:
                    json.loads(questions_path.read_text(encoding="utf-8"))
                except json.JSONDecodeError as e:
                    errors.append(
                        f"test '{test_id}': questions.json has invalid JSON: {e}"
                    )

        return errors, warnings

    def _check_jsonl(self, path, test_id: str) -> list[str]:
        errors: list[str] = []
        if path.stat().st_size == 0:
            # Empty session files are allowed (created by _prepare_session)
            return errors
        try:
            with open(path, encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    if line.strip():
                        try:
                            json.loads(line)
                        except json.JSONDecodeError as e:
                            errors.append(
                                f"test '{test_id}': {path.name} line {line_num} "
                                f"has invalid JSON: {e}"
                            )
                            break
        except Exception as e:
            errors.append(f"test '{test_id}': error reading {path.name}: {e}")
        return errors
