"""Checker: validates ID consistency within each test scenario."""

from __future__ import annotations

import json
from typing import Any

from src.utils import resolve_path
from .base import BaseChecker, CheckResult


class IdConsistencyChecker(BaseChecker):
    """Checks that agent, session, and eval IDs are internally consistent."""

    @property
    def name(self) -> str:
        return "ID Consistency"

    @property
    def description(self) -> str:
        return "Validates agent/session/eval IDs are consistent within each test"

    def check(self, test_data: dict[str, Any]) -> CheckResult:
        result = CheckResult(name=self.name, passed=True)
        tests = test_data.get("test", [])

        openclaw_state_dir_str = test_data.get("openclaw_state_dir", "")
        try:
            openclaw_state_dir = resolve_path(openclaw_state_dir_str)
        except Exception:
            openclaw_state_dir = None

        seen_session_ids: set[str] = set()

        for test in tests:
            errs, warns = self._check_test(test, openclaw_state_dir, seen_session_ids)
            result.errors.extend(errs)
            result.warnings.extend(warns)

        result.passed = len(result.errors) == 0
        result.details["tests_checked"] = len(tests)
        return result

    def _check_test(
        self,
        test: dict[str, Any],
        openclaw_state_dir,
        seen_session_ids: set[str],
    ) -> tuple[list[str], list[str]]:
        errors: list[str] = []
        warnings: list[str] = []
        test_id = test.get("id", "<unknown>")
        agent_id = test.get("agent", "")
        session_id = test.get("session", "")
        eval_name = test.get("eval", "")

        # Session ID uniqueness across tests
        if session_id:
            if session_id in seen_session_ids:
                errors.append(
                    f"test '{test_id}': duplicate session id '{session_id}' across tests"
                )
            seen_session_ids.add(session_id)

        # Check that session file's first line internal ID matches the filename
        if openclaw_state_dir and agent_id and session_id:
            sessions_dir = openclaw_state_dir / "agents" / agent_id / "sessions"
            session_file = sessions_dir / f"{session_id}.jsonl"
            if session_file.exists():
                try:
                    with open(session_file, encoding="utf-8") as f:
                        first_line = f.readline().strip()
                    if first_line:
                        data = json.loads(first_line)
                        if data.get("role") not in ("user", "assistant"):
                            # Might be legacy openclaw session format with type/id
                            internal_id = data.get("id")
                            if internal_id and internal_id != session_id:
                                errors.append(
                                    f"test '{test_id}': session file {session_id}.jsonl "
                                    f"has mismatched internal ID '{internal_id}'"
                                )
                except Exception as e:
                    errors.append(
                        f"test '{test_id}': error reading {session_id}.jsonl: {e}"
                    )

        # eval name should match test id (warning if different)
        if eval_name and eval_name != test_id:
            warnings.append(
                f"test '{test_id}': eval field '{eval_name}' differs from test id"
            )

        return errors, warnings
