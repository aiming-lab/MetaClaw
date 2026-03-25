"""Base checker class for data validation."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class CheckResult:
    """Result of a single check."""

    name: str
    passed: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)


class BaseChecker:
    """Base class for all data checkers."""

    def __init__(self, base_dir: Path, all_tests_data: dict | None = None):
        """Initialize the checker.

        Args:
            base_dir: Base directory containing the benchmark data
                      (directory where all_tests.json lives).
            all_tests_data: Parsed content of all_tests.json, used by checkers
                            that need to resolve paths from top-level fields
                            (e.g. workspace_src).
        """
        self.base_dir = base_dir
        self.all_tests_data = all_tests_data or {}

    def check(self, test_data: dict[str, Any]) -> CheckResult:
        """Run the check on the given test data."""
        raise NotImplementedError("Subclasses must implement check()")

    @property
    def name(self) -> str:
        raise NotImplementedError("Subclasses must implement name property")

    @property
    def description(self) -> str:
        raise NotImplementedError("Subclasses must implement description property")
