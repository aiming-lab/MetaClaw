"""Checker: validates all_tests.json top-level and test array structure."""

from __future__ import annotations

from typing import Any

from .base import BaseChecker, CheckResult


class AllTestsStructureChecker(BaseChecker):
    """Validates all_tests.json structural requirements for MetaClaw bench."""

    @property
    def name(self) -> str:
        return "AllTests Structure"

    @property
    def description(self) -> str:
        return "Validates all_tests.json top-level fields and test array structure"

    def check(self, test_data: dict[str, Any]) -> CheckResult:
        result = CheckResult(name=self.name, passed=True)
        errors = result.errors
        warnings = result.warnings

        # Required top-level fields
        required_top = ["name", "openclaw_state_dir", "eval_dir", "workspace_src", "test"]
        for field in required_top:
            if field not in test_data:
                errors.append(f"all_tests.json missing required top-level field '{field}'")

        tests = test_data.get("test", [])
        if not isinstance(tests, list) or len(tests) == 0:
            errors.append("all_tests.json 'test' must be a non-empty array")
            result.passed = len(errors) == 0
            return result

        # Per-test required fields
        required_test_fields = ["id", "desc", "agent", "session", "eval"]
        seen_ids: set[str] = set()
        agent_ids: set[str] = set()

        for test in tests:
            test_id = test.get("id", "<unknown>")

            for field in required_test_fields:
                if field not in test:
                    errors.append(f"test '{test_id}': missing required field '{field}'")

            # Unique test ids
            if test_id in seen_ids:
                errors.append(f"duplicate test id: '{test_id}'")
            seen_ids.add(test_id)

            if "agent" in test:
                agent_ids.add(test["agent"])

            # Optional but recommended fields
            if "arc" not in test:
                warnings.append(f"test '{test_id}': missing recommended field 'arc'")
            if "preference_tags" not in test:
                warnings.append(f"test '{test_id}': missing recommended field 'preference_tags'")

        # All tests should share the same agent
        if len(agent_ids) > 1:
            errors.append(
                f"all tests must use the same agent id, found multiple: {sorted(agent_ids)}"
            )

        result.passed = len(errors) == 0
        result.details["tests_checked"] = len(tests)
        return result
