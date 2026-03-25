"""Checker: validates referenced files exist and metadata fields are complete."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.utils import resolve_path
from .base import BaseChecker, CheckResult


class BasicIntegrityChecker(BaseChecker):
    """Checks that all referenced files and directories exist on disk."""

    @property
    def name(self) -> str:
        return "Basic Integrity"

    @property
    def description(self) -> str:
        return "Validates that all referenced files exist and required fields are complete"

    def check(self, test_data: dict[str, Any]) -> CheckResult:
        result = CheckResult(name=self.name, passed=True)
        tests = test_data.get("test", [])

        # Resolve dirs from all_tests.json
        project_root = self.base_dir  # base_dir is where all_tests.json lives
        openclaw_state_dir = self._resolve_dir(test_data.get("openclaw_state_dir", ""))
        eval_dir = self._resolve_dir(test_data.get("eval_dir", ""))
        workspace_src = self._resolve_dir(
            test_data.get("workspace_src", "").replace("${METACLAW_ROOT}", str(project_root))
        )

        if openclaw_state_dir and not openclaw_state_dir.exists():
            result.errors.append(f"openclaw_state_dir not found: {openclaw_state_dir}")

        if eval_dir and not eval_dir.exists():
            result.errors.append(f"eval_dir not found: {eval_dir}")

        if workspace_src and not workspace_src.exists():
            result.errors.append(f"workspace_src not found: {workspace_src}")

        for test in tests:
            errs, warns = self._check_test(test, openclaw_state_dir, eval_dir)
            result.errors.extend(errs)
            result.warnings.extend(warns)

        result.passed = len(result.errors) == 0
        result.details["tests_checked"] = len(tests)
        return result

    def _resolve_dir(self, path_str: str) -> Path | None:
        if not path_str:
            return None
        try:
            return resolve_path(path_str)
        except Exception:
            return None

    def _check_test(
        self,
        test: dict[str, Any],
        openclaw_state_dir: Path | None,
        eval_dir: Path | None,
    ) -> tuple[list[str], list[str]]:
        errors: list[str] = []
        warnings: list[str] = []
        test_id = test.get("id", "<unknown>")
        agent_id = test.get("agent", "")
        session_id = test.get("session", "")
        eval_name = test.get("eval", "")

        # Check session file exists
        if openclaw_state_dir and agent_id and session_id:
            sessions_dir = openclaw_state_dir / "agents" / agent_id / "sessions"
            session_file = sessions_dir / f"{session_id}.jsonl"
            if not session_file.exists():
                errors.append(
                    f"test '{test_id}': session file not found: "
                    f"agents/{agent_id}/sessions/{session_id}.jsonl"
                )

        # Check questions.json exists and is valid
        if eval_dir and eval_name:
            questions_path = eval_dir / eval_name / "questions.json"
            if not questions_path.exists():
                errors.append(
                    f"test '{test_id}': questions.json not found at {questions_path}"
                )
            else:
                q_errs, q_warns = self._check_questions_json(test_id, questions_path)
                errors.extend(q_errs)
                warnings.extend(q_warns)

        return errors, warnings

    def _check_questions_json(
        self, test_id: str, questions_path: Path
    ) -> tuple[list[str], list[str]]:
        errors: list[str] = []
        warnings: list[str] = []
        try:
            data = json.loads(questions_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            errors.append(f"test '{test_id}': questions.json has invalid JSON: {e}")
            return errors, warnings

        for required in ("id", "rounds"):
            if required not in data:
                errors.append(
                    f"test '{test_id}': questions.json missing required field '{required}'"
                )

        rounds = data.get("rounds", [])
        if not isinstance(rounds, list) or len(rounds) == 0:
            errors.append(f"test '{test_id}': questions.json 'rounds' must be a non-empty list")

        for round_data in rounds:
            round_id = round_data.get("id", "<unknown>")
            for req in ("id", "type", "question", "feedback", "eval"):
                if req not in round_data:
                    errors.append(
                        f"test '{test_id}', round '{round_id}': "
                        f"questions.json missing required field '{req}'"
                    )

        return errors, warnings
