"""Checker: validates questions.json content correctness for MetaClaw bench."""

from __future__ import annotations

import json
from typing import Any

from src.utils import resolve_path
from .base import BaseChecker, CheckResult

VALID_TYPES = {"multi_choice", "file_check"}


class QuestionsIntegrityChecker(BaseChecker):
    """Validates the content of each eval/dayXX/questions.json."""

    @property
    def name(self) -> str:
        return "Questions Integrity"

    @property
    def description(self) -> str:
        return "Validates questions.json content: round types, feedback, eval fields"

    def check(self, test_data: dict[str, Any]) -> CheckResult:
        result = CheckResult(name=self.name, passed=True)
        tests = test_data.get("test", [])

        try:
            eval_dir = resolve_path(test_data.get("eval_dir", ""))
        except Exception:
            eval_dir = None

        for test in tests:
            test_id = test.get("id", "<unknown>")
            eval_name = test.get("eval", "")
            if not eval_dir or not eval_name:
                continue

            questions_path = eval_dir / eval_name / "questions.json"
            if not questions_path.exists():
                continue  # BasicIntegrityChecker already reports this

            try:
                data = json.loads(questions_path.read_text(encoding="utf-8"))
            except Exception:
                continue  # FileFormatChecker already reports JSON errors

            errs, warns = self._check_questions(test_id, data)
            result.errors.extend(errs)
            result.warnings.extend(warns)

        result.passed = len(result.errors) == 0
        result.details["tests_checked"] = len(tests)
        return result

    def _check_questions(
        self, test_id: str, data: dict
    ) -> tuple[list[str], list[str]]:
        errors: list[str] = []
        warnings: list[str] = []

        # Top-level required fields
        if "id" not in data:
            errors.append(f"test '{test_id}': questions.json missing 'id'")
        elif not isinstance(data["id"], str):
            errors.append(
                f"test '{test_id}': questions.json 'id' must be a string, "
                f"got {type(data['id']).__name__}"
            )
        if "rounds" not in data or not isinstance(data.get("rounds"), list):
            errors.append(f"test '{test_id}': questions.json missing or invalid 'rounds'")
            return errors, warnings

        rounds = data["rounds"]
        if len(rounds) == 0:
            errors.append(f"test '{test_id}': questions.json 'rounds' is empty")
            return errors, warnings

        if len(rounds) < 5:
            warnings.append(
                f"test '{test_id}': questions.json has only {len(rounds)} round(s) (< 5)"
            )
        elif len(rounds) > 20:
            warnings.append(
                f"test '{test_id}': questions.json has {len(rounds)} rounds (> 20)"
            )

        seen_round_ids: set[str] = set()
        for round_data in rounds:
            round_id = round_data.get("id", "<unknown>")

            # Round ID uniqueness
            if round_id in seen_round_ids:
                errors.append(
                    f"test '{test_id}': duplicate round id '{round_id}' in questions.json"
                )
            seen_round_ids.add(round_id)

            # Required fields
            for req in ("id", "type", "question", "feedback", "eval"):
                if req not in round_data:
                    errors.append(
                        f"test '{test_id}', round '{round_id}': missing required field '{req}'"
                    )

            # Round id must be a string
            if "id" in round_data and not isinstance(round_data["id"], str):
                errors.append(
                    f"test '{test_id}', round '{round_id}': "
                    f"round 'id' must be a string, got {type(round_data['id']).__name__}"
                )

            # Type validation
            rtype = round_data.get("type", "")
            if rtype not in VALID_TYPES:
                errors.append(
                    f"test '{test_id}', round '{round_id}': "
                    f"invalid type '{rtype}', must be one of {sorted(VALID_TYPES)}"
                )

            # Feedback validation (structure differs by type)
            feedback = round_data.get("feedback", {})
            if not isinstance(feedback, dict):
                errors.append(
                    f"test '{test_id}', round '{round_id}': 'feedback' must be a dict"
                )
            elif rtype == "multi_choice":
                errs2 = self._check_feedback_multi_choice(
                    test_id, round_id, feedback, round_data.get("eval", {})
                )
                errors.extend(errs2)
            else:
                # file_check: correct + incorrect both required
                for key in ("correct", "incorrect"):
                    val = feedback.get(key, "")
                    if not isinstance(val, str) or not val:
                        errors.append(
                            f"test '{test_id}', round '{round_id}': "
                            f"feedback.{key} must be a non-empty string"
                        )

            # Eval validation per type
            eval_cfg = round_data.get("eval", {})
            if rtype == "multi_choice":
                errs2 = self._check_eval_multi_choice(test_id, round_id, eval_cfg)
                errors.extend(errs2)
            elif rtype == "file_check":
                errs2 = self._check_eval_file_check(test_id, round_id, eval_cfg)
                errors.extend(errs2)

        return errors, warnings

    def _check_feedback_multi_choice(
        self, test_id: str, round_id: str, feedback: dict, eval_cfg: dict
    ) -> list[str]:
        errors: list[str] = []
        # correct must be a non-empty string
        correct_val = feedback.get("correct", "")
        if not isinstance(correct_val, str) or not correct_val:
            errors.append(
                f"test '{test_id}', round '{round_id}': "
                f"feedback.correct must be a non-empty string"
            )
        # options must be present and non-empty dict
        options_fb = feedback.get("options")
        if not isinstance(options_fb, dict) or not options_fb:
            errors.append(
                f"test '{test_id}', round '{round_id}': "
                f"multi_choice feedback.options must be a non-empty dict"
            )
            return errors
        # every value must be a non-empty string
        for key, val in options_fb.items():
            if not isinstance(val, str) or not val:
                errors.append(
                    f"test '{test_id}', round '{round_id}': "
                    f"feedback.options['{key}'] must be a non-empty string"
                )
        # feedback.options keys must match eval.options keys exactly
        eval_options = eval_cfg.get("options", {})
        if isinstance(eval_options, dict) and eval_options:
            fb_keys = {k.upper() for k in options_fb}
            ev_keys = {k.upper() for k in eval_options}
            if fb_keys != ev_keys:
                errors.append(
                    f"test '{test_id}', round '{round_id}': "
                    f"feedback.options keys {sorted(fb_keys)} do not match "
                    f"eval.options keys {sorted(ev_keys)}"
                )
        return errors

    def _check_eval_multi_choice(
        self, test_id: str, round_id: str, eval_cfg: dict
    ) -> list[str]:
        errors: list[str] = []
        options = eval_cfg.get("options")
        if not isinstance(options, dict) or len(options) < 2:
            errors.append(
                f"test '{test_id}', round '{round_id}': "
                f"multi_choice eval.options must be a dict with at least 2 items"
            )
        answer = eval_cfg.get("answer")
        if answer is None:
            errors.append(
                f"test '{test_id}', round '{round_id}': multi_choice eval missing 'answer'"
            )
        elif isinstance(options, dict):
            # Validate answer letters are in options keys
            import re
            if isinstance(answer, str):
                letters = re.findall(r"[A-Za-z]", answer)
            elif isinstance(answer, list):
                letters = [l for item in answer for l in re.findall(r"[A-Za-z]", str(item))]
            else:
                letters = []
            option_keys = {k.upper() for k in options.keys()}
            for letter in letters:
                if letter.upper() not in option_keys:
                    errors.append(
                        f"test '{test_id}', round '{round_id}': "
                        f"answer letter '{letter}' not in eval.options keys"
                    )
        return errors

    def _check_eval_file_check(
        self, test_id: str, round_id: str, eval_cfg: dict
    ) -> list[str]:
        errors: list[str] = []
        command = eval_cfg.get("command", "")
        if not isinstance(command, str) or not command:
            errors.append(
                f"test '{test_id}', round '{round_id}': "
                f"file_check eval.command must be a non-empty string"
            )
        expect_exit = eval_cfg.get("expect_exit")
        if expect_exit is not None and not isinstance(expect_exit, int):
            errors.append(
                f"test '{test_id}', round '{round_id}': "
                f"file_check eval.expect_exit must be an integer"
            )
        return errors
