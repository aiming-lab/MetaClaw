"""Checker: validates MetaClaw benchmark directory structure."""

from __future__ import annotations

from typing import Any

from src.utils import resolve_path
from .base import BaseChecker, CheckResult


class DirectoryStructureChecker(BaseChecker):
    """Checks that all required directories exist with correct layout."""

    @property
    def name(self) -> str:
        return "Directory Structure"

    @property
    def description(self) -> str:
        return "Validates workspace_src, eval/dayXX, and openclaw_state directory structure"

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
            errs = self._check_test(test, openclaw_state_dir, eval_dir)
            result.errors.extend(errs)

        result.passed = len(result.errors) == 0
        result.details["tests_checked"] = len(tests)
        return result

    def _check_test(
        self,
        test: dict[str, Any],
        openclaw_state_dir,
        eval_dir,
    ) -> list[str]:
        errors: list[str] = []
        test_id = test.get("id", "<unknown>")
        agent_id = test.get("agent", "")
        eval_name = test.get("eval", "")

        # Check eval/<eval_name>/ directory
        if eval_dir and eval_name:
            eval_scenario_dir = eval_dir / eval_name
            if not eval_scenario_dir.exists():
                errors.append(f"test '{test_id}': eval directory not found: {eval_scenario_dir}")
            elif not eval_scenario_dir.is_dir():
                errors.append(f"test '{test_id}': eval path is not a directory: {eval_scenario_dir}")

        # Check openclaw_state/agents/<agent>/sessions/ directory
        if openclaw_state_dir and agent_id:
            sessions_dir = openclaw_state_dir / "agents" / agent_id / "sessions"
            if not sessions_dir.exists():
                errors.append(
                    f"test '{test_id}': sessions directory not found: "
                    f"agents/{agent_id}/sessions/"
                )
            elif not sessions_dir.is_dir():
                errors.append(
                    f"test '{test_id}': sessions path is not a directory"
                )

        return errors
