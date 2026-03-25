"""Checker: validates initial session file format for MetaClaw bench."""

from __future__ import annotations

import json
from typing import Any

from src.utils import resolve_path
from .base import BaseChecker, CheckResult


class SessionFormatChecker(BaseChecker):
    """Validates session JSONL files contain valid initial context lines."""

    @property
    def name(self) -> str:
        return "Session Format"

    @property
    def description(self) -> str:
        return "Validates session files are valid JSONL with correct role structure"

    def check(self, test_data: dict[str, Any]) -> CheckResult:
        result = CheckResult(name=self.name, passed=True)
        tests = test_data.get("test", [])

        try:
            openclaw_state_dir = resolve_path(test_data.get("openclaw_state_dir", ""))
        except Exception:
            openclaw_state_dir = None

        for test in tests:
            errs, warns = self._check_test(test, openclaw_state_dir)
            result.errors.extend(errs)
            result.warnings.extend(warns)

        result.passed = len(result.errors) == 0
        result.details["tests_checked"] = len(tests)
        return result

    def _check_test(
        self,
        test: dict[str, Any],
        openclaw_state_dir,
    ) -> tuple[list[str], list[str]]:
        errors: list[str] = []
        warnings: list[str] = []
        test_id = test.get("id", "<unknown>")
        agent_id = test.get("agent", "")
        session_id = test.get("session", "")

        if not openclaw_state_dir or not agent_id or not session_id:
            return errors, warnings

        session_file = openclaw_state_dir / "agents" / agent_id / "sessions" / f"{session_id}.jsonl"
        if not session_file.exists():
            return errors, warnings  # BasicIntegrityChecker already reports missing files

        # Parse all non-empty lines
        try:
            lines = []
            with open(session_file, encoding="utf-8") as f:
                for raw in f:
                    raw = raw.strip()
                    if raw:
                        lines.append(json.loads(raw))
        except json.JSONDecodeError as e:
            errors.append(f"test '{test_id}': {session_id}.jsonl has invalid JSON: {e}")
            return errors, warnings
        except Exception as e:
            errors.append(f"test '{test_id}': error reading {session_id}.jsonl: {e}")
            return errors, warnings

        if len(lines) == 0:
            # Empty session file is allowed (will be populated at runtime)
            return errors, warnings

        # --- Detect format ---
        # New openclaw format: first line has type="session" (4 metadata + message lines)
        # Old simple format:   first line has "role" key directly
        if lines[0].get("type") == "session":
            errs, warns = self._check_openclaw_format(test_id, session_id, lines)
        else:
            errs, warns = self._check_simple_format(test_id, session_id, lines)
        errors.extend(errs)
        warnings.extend(warns)

        return errors, warnings

    _META_TYPES = ["session", "model_change", "thinking_level_change", "custom"]

    def _check_openclaw_format(
        self, test_id: str, session_id: str, lines: list
    ) -> tuple[list[str], list[str]]:
        """Validate new openclaw JSONL format (4 metadata + typed message lines)."""
        errors: list[str] = []
        warnings: list[str] = []

        # Check the 4 mandatory metadata lines
        for i, expected_type in enumerate(self._META_TYPES):
            if i >= len(lines):
                errors.append(
                    f"test '{test_id}': {session_id}.jsonl missing metadata line {i + 1} "
                    f"(expected type='{expected_type}')"
                )
                continue
            actual_type = lines[i].get("type")
            if actual_type != expected_type:
                errors.append(
                    f"test '{test_id}': {session_id}.jsonl line {i + 1} must have "
                    f"type='{expected_type}', got '{actual_type}'"
                )

        # Extract message lines and validate role order
        msg_lines = [l for l in lines if l.get("type") == "message"]
        if not msg_lines:
            # No messages yet — fine, will be populated at runtime
            return errors, warnings

        first_role = msg_lines[0].get("message", {}).get("role")
        if first_role != "user":
            errors.append(
                f"test '{test_id}': {session_id}.jsonl first message must have "
                f"role='user', got '{first_role}'"
            )

        if len(msg_lines) >= 2:
            second_role = msg_lines[1].get("message", {}).get("role")
            if second_role != "assistant":
                errors.append(
                    f"test '{test_id}': {session_id}.jsonl second message must have "
                    f"role='assistant', got '{second_role}'"
                )

        return errors, warnings

    def _check_simple_format(
        self, test_id: str, session_id: str, lines: list
    ) -> tuple[list[str], list[str]]:
        """Validate legacy simple format (bare role/content lines)."""
        errors: list[str] = []
        warnings: list[str] = []

        if len(lines) > 4:
            warnings.append(
                f"test '{test_id}': {session_id}.jsonl has {len(lines)} lines "
                f"(> 4; expected 2-4 for initial context)"
            )

        first_role = lines[0].get("role")
        if first_role != "user":
            errors.append(
                f"test '{test_id}': {session_id}.jsonl first line must have role='user', "
                f"got '{first_role}'"
            )

        if len(lines) >= 2:
            second_role = lines[1].get("role")
            if second_role != "assistant":
                errors.append(
                    f"test '{test_id}': {session_id}.jsonl second line must have "
                    f"role='assistant', got '{second_role}'"
                )

        return errors, warnings
