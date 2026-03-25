"""Query reader abstraction for benchmark inference.

Defines the :class:`QueryReader` interface, the :class:`EvalFlowQueryReader`
implementation (reads from ``eval_flow.json``), and the
:class:`QuestionsJsonQueryReader` implementation (reads from
``questions.json`` with fallback to ``eval_flow.json``).
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, TypedDict


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


class RoundRecord(TypedDict, total=False):
    id: str
    type: str               # "multi_choice" | "file_check"
    question: str           # question text, injected as-is into agent message
    eval: dict              # type-specific eval config: {options, answer} or {command, ...}
    feedback: dict          # {"correct": str, "incorrect": str}
    update: list            # list of update actions to apply before this round


class GroupRecord(TypedDict, total=False):
    id: str
    desc: str
    rounds: list            # list of RoundRecord


# ---------------------------------------------------------------------------
# Abstract interface
# ---------------------------------------------------------------------------


class QueryReader(ABC):
    """Abstract interface for reading evaluation queries."""

    @abstractmethod
    def read_queries(self, eval_dir: Path, eval_name: str) -> list[GroupRecord]:
        """Return a list of GroupRecord for a given eval scenario.

        Each GroupRecord contains:
          - ``id`` (str): unique identifier for this group
          - ``desc`` (str, optional): description of the group
          - ``rounds`` (list of RoundRecord): the questions in this group

        Each RoundRecord contains:
          - ``id`` (str): unique identifier for this round
          - ``type`` (str): question type, e.g. "multi_choice" or "file_check"
          - ``question`` (str): the question text injected verbatim into the agent
          - ``eval`` (dict, optional): type-specific eval config
          - ``feedback`` (dict, optional): {"correct": str, "incorrect": str}
          - ``update`` (list, optional): update actions to apply before this round
        """


# ---------------------------------------------------------------------------
# EvalFlowQueryReader
# ---------------------------------------------------------------------------


class EvalFlowQueryReader(QueryReader):
    """Reads from ``eval_flow.json`` (legacy format).

    Each qa_annotation is wrapped into its own GroupRecord containing a
    single RoundRecord.
    """

    def read_queries(self, eval_dir: Path, eval_name: str) -> list[GroupRecord]:
        eval_flow_path = eval_dir / eval_name / "eval_flow.json"
        if not eval_flow_path.exists():
            return []

        data = json.loads(eval_flow_path.read_text(encoding="utf-8"))
        annotations = data.get("qa_annotations", [])

        groups: list[GroupRecord] = []
        for i, item in enumerate(annotations):
            if "qa_id" not in item or "question" not in item:
                continue
            group = GroupRecord(
                id=f"g{i + 1}",
                desc=item.get("type", ""),
                rounds=[RoundRecord(
                    id=item["qa_id"],
                    type="multi_choice",
                    question=item["question"],
                )],
            )
            groups.append(group)
        return groups


# ---------------------------------------------------------------------------
# QuestionsJsonQueryReader
# ---------------------------------------------------------------------------


class QuestionsJsonQueryReader(QueryReader):
    """Reads from ``questions.json``, falling back to ``eval_flow.json``.

    Expects ``{eval_dir}/{eval_name}/questions.json`` to exist and contain a
    single GroupRecord-shaped dict (or a list for legacy format).
    """

    def __init__(self) -> None:
        self._fallback = EvalFlowQueryReader()

    def read_queries(self, eval_dir: Path, eval_name: str) -> list[GroupRecord]:
        questions_path = eval_dir / eval_name / "questions.json"
        if not questions_path.exists():
            return self._fallback.read_queries(eval_dir, eval_name)

        data = json.loads(questions_path.read_text(encoding="utf-8"))
        # Support both single-dict format (MetaClaw) and legacy list format
        if isinstance(data, dict):
            data = [data]

        groups: list[GroupRecord] = []
        for item in data:
            rounds = []
            for r in item.get("rounds", []):
                rec: RoundRecord = RoundRecord(
                    id=r["id"],
                    type=r.get("type", "multi_choice"),
                    question=r["question"],
                )
                if "eval" in r:
                    rec["eval"] = r["eval"]
                if "feedback" in r:
                    rec["feedback"] = r["feedback"]
                if "update" in r:
                    rec["update"] = r["update"]
                rounds.append(rec)
            group = GroupRecord(
                id=item["id"],
                desc=item.get("desc", ""),
                rounds=rounds,
            )
            groups.append(group)
        return groups


# ---------------------------------------------------------------------------
# Default factory
# ---------------------------------------------------------------------------


def get_default_query_reader() -> QueryReader:
    """Return the default query reader (QuestionsJsonQueryReader with fallback)."""
    return QuestionsJsonQueryReader()
