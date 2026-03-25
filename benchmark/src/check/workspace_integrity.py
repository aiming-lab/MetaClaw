"""Checker: validates workspace_src directory structure and contents."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.utils import get_project_root, resolve_path
from .base import BaseChecker, CheckResult

REQUIRED_WORKSPACE_FILES = ["AGENTS.md", "IDENTITY.md", "SOUL.md", "TOOLS.md", "USER.md"]


class WorkspaceIntegrityChecker(BaseChecker):
    """Validates workspace_src directory exists with required identity files."""

    @property
    def name(self) -> str:
        return "Workspace Integrity"

    @property
    def description(self) -> str:
        return "Validates workspace_src exists with required identity files"

    def check(self, test_data: dict[str, Any]) -> CheckResult:
        result = CheckResult(name=self.name, passed=True)
        tests = test_data.get("test", [])

        # Resolve workspace_src
        workspace_src_raw = test_data.get("workspace_src", "")
        if not workspace_src_raw:
            result.errors.append("all_tests.json missing 'workspace_src' field")
            result.passed = False
            return result

        project_root = get_project_root()
        workspace_src_str = workspace_src_raw.replace("${METACLAW_ROOT}", str(project_root))
        try:
            workspace_src = resolve_path(workspace_src_str)
        except Exception as e:
            result.errors.append(f"Cannot resolve workspace_src '{workspace_src_raw}': {e}")
            result.passed = False
            return result

        if not workspace_src.exists():
            result.errors.append(f"workspace_src not found: {workspace_src}")
            result.passed = False
            return result

        if not workspace_src.is_dir():
            result.errors.append(f"workspace_src is not a directory: {workspace_src}")
            result.passed = False
            return result

        # Check required identity files
        for filename in REQUIRED_WORKSPACE_FILES:
            filepath = workspace_src / filename
            if not filepath.exists():
                result.errors.append(
                    f"workspace_src missing required file: {filename}"
                )

        # Check per-test day directories
        for test in tests:
            test_id = test.get("id", "<unknown>")
            day_dir = workspace_src / test_id
            if not day_dir.exists():
                result.warnings.append(
                    f"workspace_src/{test_id}/ directory not found "
                    f"(expected day-specific workspace content)"
                )

        result.passed = len(result.errors) == 0
        result.details["workspace_src"] = str(workspace_src)
        return result
