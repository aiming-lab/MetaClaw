"""
Skill Evolver for conversation-mode RL training.

Analyses failed ConversationSample objects and generates new skills in
**Claude skill format** (name / description / content) via an LLM.

Required environment variables (OpenAI-compatible):
    OPENAI_API_KEY

Optional:
    OPENAI_BASE_URL       (default: https://openai-api.shenmishajing.workers.dev/v1)
    SKILL_EVOLVER_MODEL   (default: gpt-5.2)

Alternatively, pass a custom ``llm_client`` (any object that implements
``chat_complete(prompt: str) -> str``) to the constructor for testing.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from datetime import datetime
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Slug validation: lowercase letters, digits, hyphens, starting with a letter
_SLUG_RE = re.compile(r"^[a-z][a-z0-9-]{1,}$")
# Pattern for auto-assigned dynamic names: dyn-NNN
_DYN_RE = re.compile(r"^dyn-(\d+)$")

# Task categories must match the keys used in conversation_skills.json
_DEFAULT_CATEGORIES = [
    "coding", "research", "data_analysis", "security",
    "communication", "automation", "agentic",
]


class SkillEvolver:
    """
    Analyses failed conversation samples and generates new skills via an LLM.

    Generated skills follow Claude skill format:
    ``{"name": str, "description": str, "content": str, "category": str}``

    Parameters
    ----------
    max_new_skills:
        Maximum number of new skills generated per evolution step.
    azure_deployment:
        Backward-compatible model override (default ``"o3"``). If this value is
        not ``"o3"``, it overrides ``SKILL_EVOLVER_MODEL``.
    max_completion_tokens:
        Token budget for the LLM response.
    llm_client:
        Optional drop-in replacement for the OpenAI-compatible client.
        Must implement ``chat_complete(prompt: str) -> str``.
        If supplied, ``azure_deployment`` is ignored.
    history_path:
        If set, evolution history is appended to this JSONL file so it
        persists across restarts.
    """

    def __init__(
        self,
        max_new_skills: int = 3,
        azure_deployment: str = "o3",
        max_completion_tokens: int = 3000,
        llm_client=None,
        history_path: Optional[str] = None,
    ):
        self.max_new_skills = max_new_skills
        self.max_completion_tokens = max_completion_tokens
        self.history_path = history_path
        self.update_history: list[dict] = []

        if llm_client is not None:
            self._custom_client = llm_client
            self._openai_client = None
        else:
            self._custom_client = None
            api_key = os.environ.get("OPENAI_API_KEY", "")
            base_url = os.environ.get(
                "OPENAI_BASE_URL",
                "https://openai-api.shenmishajing.workers.dev/v1",
            )
            if not api_key:
                raise EnvironmentError(
                    "SkillEvolver requires OPENAI_API_KEY environment variable, "
                    "or an explicit llm_client= argument."
                )
            from openai import OpenAI
            self._openai_client = OpenAI(
                api_key=api_key,
                base_url=base_url,
            )
            model_from_env = os.environ.get("SKILL_EVOLVER_MODEL", "gpt-5.2")
            self._openai_model = azure_deployment if azure_deployment and azure_deployment != "o3" else model_from_env

    # ------------------------------------------------------------------ #
    # Public interface                                                     #
    # ------------------------------------------------------------------ #

    def should_evolve(self, batch: list, threshold: float = 0.4) -> bool:
        """
        Return True if the batch success rate is below *threshold*.

        A sample is considered successful when its reward > 0.
        """
        if not batch:
            return False
        successes = sum(1 for s in batch if getattr(s, "reward", 0) > 0)
        rate = successes / len(batch)
        logger.info(
            "[SkillEvolver] success_rate=%.2f threshold=%.2f evolve=%s",
            rate, threshold, rate < threshold,
        )
        return rate < threshold

    async def evolve(
        self,
        failed_samples: list,
        current_skills: Dict[str, Any],
    ) -> list[dict]:
        """
        Analyse *failed_samples* and propose new skills in Claude skill format.

        Parameters
        ----------
        failed_samples:
            List of ``ConversationSample`` objects whose reward <= 0.
        current_skills:
            The full skill bank dict (``general_skills``,
            ``task_specific_skills``, ``common_mistakes``).

        Returns
        -------
        List of new skill dicts with keys:
        ``name``, ``description``, ``content``, ``category``
        Ready to be passed to ``SkillManager.add_skills()``.
        """
        if not failed_samples:
            return []

        next_dyn_idx = self._next_dyn_index(current_skills)
        prompt = self._build_analysis_prompt(failed_samples, current_skills, next_dyn_idx)

        try:
            # Synchronous LLM call run in a thread to avoid blocking the event loop
            response = await asyncio.to_thread(self._call_llm, prompt)
            raw_skills = self._parse_skills_response(response)
            skills = self._finalise_names(raw_skills, next_dyn_idx)
            skills = skills[: self.max_new_skills]

            record = {
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "num_failures_analyzed": len(failed_samples),
                "num_skills_generated": len(skills),
                "skill_names": [s.get("name") for s in skills],
                # Full skill content so the history file is self-contained
                "skills": [
                    {
                        "name": s.get("name"),
                        "category": s.get("category", "general"),
                        "description": s.get("description", ""),
                        "content": s.get("content", ""),
                    }
                    for s in skills
                ],
                # Failure summaries for traceability (first 300 chars of each)
                "failure_prompts": [
                    getattr(s, "prompt_text", "")[-300:]
                    for s in failed_samples[:6]
                ],
            }
            self.update_history.append(record)
            if self.history_path:
                self._append_history(record)

            logger.info(
                "[SkillEvolver] generated %d new skills from %d failures: %s",
                len(skills),
                len(failed_samples),
                [s.get("name") for s in skills],
            )
            return skills

        except Exception as e:
            logger.error("[SkillEvolver] LLM call failed: %s", e, exc_info=True)
            return []

    def get_update_summary(self) -> dict:
        if not self.update_history:
            return {"total_updates": 0, "total_skills_generated": 0}
        return {
            "total_updates": len(self.update_history),
            "total_skills_generated": sum(
                h["num_skills_generated"] for h in self.update_history
            ),
            "all_skill_names": [
                n for h in self.update_history for n in h.get("skill_names", [])
            ],
        }

    # ------------------------------------------------------------------ #
    # LLM call                                                            #
    # ------------------------------------------------------------------ #

    def _call_llm(self, prompt: str) -> str:
        if self._custom_client is not None:
            return self._custom_client.chat_complete(prompt)
        response = self._openai_client.chat.completions.create(
            model=self._openai_model,
            messages=[{"role": "user", "content": prompt}],
            max_completion_tokens=self.max_completion_tokens,
        )
        return response.choices[0].message.content

    # ------------------------------------------------------------------ #
    # Prompt construction                                                  #
    # ------------------------------------------------------------------ #

    def _build_analysis_prompt(
        self,
        failed_samples: list,
        current_skills: Dict[str, Any],
        next_dyn_idx: int,
    ) -> str:
        # --- Section 1: failed conversation excerpts ---
        failure_blocks = []
        for i, sample in enumerate(failed_samples[:6]):
            prompt_text = getattr(sample, "prompt_text", "")
            response_text = getattr(sample, "response_text", "")
            reward = getattr(sample, "reward", 0.0)
            failure_blocks.append(
                f"### Failure {i + 1}  (reward={reward:.1f})\n"
                f"**Conversation context (last 600 chars):**\n"
                f"```\n...{prompt_text[-600:]}\n```\n\n"
                f"**Assistant response (first 500 chars):**\n"
                f"```\n{response_text[:500]}{'...' if len(response_text) > 500 else ''}\n```"
            )

        # --- Section 2: existing skill names to avoid duplication ---
        existing = []
        for s in current_skills.get("general_skills", []):
            existing.append(s.get("name", ""))
        for tt, skills in current_skills.get("task_specific_skills", {}).items():
            for s in skills:
                existing.append(f"[{tt}] {s.get('name', '')}")
        for s in current_skills.get("common_mistakes", []):
            existing.append(f"[mistake] {s.get('name', '')}")

        # --- Section 3: available task categories ---
        available_cats = list(
            current_skills.get("task_specific_skills", {}).keys()
        ) or _DEFAULT_CATEGORIES

        example_name = f"dyn-{next_dyn_idx:03d}"

        return (
            "You are a skill engineer for an AI assistant trained with RL.\n"
            "Your job: analyze the failed conversations below and generate NEW skills "
            "that would have prevented those failures.\n\n"
            "---\n"
            "## Failed Conversations\n\n"
            + "\n\n".join(failure_blocks)
            + "\n\n---\n"
            "## Existing Skills (do NOT duplicate any of these)\n\n"
            + json.dumps(existing, indent=2)
            + "\n\n---\n"
            "## Instructions\n\n"
            f"Generate **1 to {self.max_new_skills}** new skills that directly address "
            "the failure patterns observed above. Focus on actionable, concrete guidance "
            "that the assistant can follow in future conversations.\n\n"
            "Each skill must follow **Claude skill format**:\n"
            "- `name`: a lowercase hyphenated slug (e.g. `handle-partial-input`). "
            f"Use `{example_name}` only if you can't find a descriptive name.\n"
            "- `description`: one sentence — when to trigger this skill and what it achieves. "
            "This is the primary trigger condition shown to the assistant.\n"
            "- `content`: 6–15 lines of actionable Markdown. Include: "
            "a heading, numbered steps or bullet points, a concrete example or code snippet "
            "if relevant, and an **Anti-pattern** section.\n"
            f"- `category`: one of {available_cats} or `\"general\"` or `\"common_mistakes\"`.\n\n"
            "**Output:** Return ONLY a valid JSON array. "
            "No markdown code fences, no prose outside the JSON.\n\n"
            "**Example output:**\n"
            "[\n"
            "  {\n"
            f'    "name": "{example_name}",\n'
            '    "description": "Use when the user provides a path that may not exist. '
            'Always verify file existence before reading or writing.",\n'
            '    "content": "## Verify File Existence Before Acting\\n\\n'
            "1. Check that the path exists: `os.path.exists(path)`\\n"
            "2. If it doesn't exist, tell the user and ask for the correct path.\\n"
            "3. Never assume a path is valid just because the user mentioned it.\\n\\n"
            '**Anti-pattern:** Calling `open(path)` without checking existence first.",\n'
            '    "category": "coding"\n'
            "  }\n"
            "]"
        )

    # ------------------------------------------------------------------ #
    # Response parsing                                                     #
    # ------------------------------------------------------------------ #

    def _parse_skills_response(self, response: str) -> list[dict]:
        """Extract and validate JSON skill array from LLM response."""
        raw_list = self._extract_json_array(response)
        if raw_list is None:
            logger.warning(
                "[SkillEvolver] no JSON skill array found in response:\n%s",
                response[:400],
            )
            return []

        valid = []
        for s in raw_list:
            if not isinstance(s, dict):
                continue
            missing = [k for k in ("name", "description", "content") if not s.get(k)]
            if missing:
                logger.warning("[SkillEvolver] skipping skill — missing fields %s: %s",
                               missing, str(s)[:200])
                continue
            valid.append(s)

        return valid

    @staticmethod
    def _extract_json_array(response: str) -> list[dict] | None:
        """Try progressively looser strategies to extract a JSON array of skill objects."""
        # Strategy 1: direct parse
        try:
            result = json.loads(response)
            if isinstance(result, list):
                return result
        except (json.JSONDecodeError, ValueError):
            pass

        # Strategy 2: strip markdown code fences, then direct parse
        clean = re.sub(r"```(?:json)?\s*", "", response).strip()
        try:
            result = json.loads(clean)
            if isinstance(result, list):
                return result
        except (json.JSONDecodeError, ValueError):
            pass

        # Strategy 3: locate [{ (start of a JSON array of objects) and try
        # parsing from each candidate position — avoids false positives from
        # prose brackets like "[automation] skill-name".
        start = 0
        while True:
            idx = clean.find("[{", start)
            if idx == -1:
                break
            # Try from the last ] backwards until one parses
            end = len(clean)
            while end > idx:
                end = clean.rfind("]", idx, end)
                if end == -1:
                    break
                try:
                    result = json.loads(clean[idx : end + 1])
                    if isinstance(result, list) and any(
                        isinstance(o, dict) and o.get("name") for o in result
                    ):
                        return result
                except (json.JSONDecodeError, ValueError):
                    pass  # try a shorter span
            start = idx + 1

        # Strategy 4: extract individual {...} objects that look like skills
        objects: list[dict] = []
        brace_depth = 0
        obj_start: int | None = None
        for i, ch in enumerate(clean):
            if ch == "{" and brace_depth == 0:
                obj_start = i
            if ch == "{":
                brace_depth += 1
            elif ch == "}":
                brace_depth -= 1
                if brace_depth == 0 and obj_start is not None:
                    try:
                        obj = json.loads(clean[obj_start : i + 1])
                        if isinstance(obj, dict) and obj.get("name"):
                            objects.append(obj)
                    except (json.JSONDecodeError, ValueError):
                        pass
                    obj_start = None
        if objects:
            return objects

        return None

    # ------------------------------------------------------------------ #
    # Name / slug management                                               #
    # ------------------------------------------------------------------ #

    def _next_dyn_index(self, current_skills: Dict[str, Any]) -> int:
        """Return the next available dyn-NNN index across the skill bank."""
        max_idx = 0
        for skill in current_skills.get("general_skills", []):
            m = _DYN_RE.match(skill.get("name", ""))
            if m:
                max_idx = max(max_idx, int(m.group(1)))
        for skills in current_skills.get("task_specific_skills", {}).values():
            for skill in skills:
                m = _DYN_RE.match(skill.get("name", ""))
                if m:
                    max_idx = max(max_idx, int(m.group(1)))
        return max_idx + 1

    def _finalise_names(self, skills: list[dict], start_idx: int) -> list[dict]:
        """
        Ensure every skill has a valid slug name.

        - If the LLM provided a valid lowercase-hyphenated slug, keep it.
        - Otherwise assign ``dyn-NNN``.
        - Deduplicate within this batch (the cross-bank dedup is in SkillManager).
        """
        seen: set[str] = set()
        result = []
        dyn_counter = start_idx

        for skill in skills:
            updated = dict(skill)
            name = skill.get("name", "").strip().lower()

            if _SLUG_RE.match(name) and name not in seen:
                pass  # keep as-is
            else:
                name = f"dyn-{dyn_counter:03d}"
                dyn_counter += 1

            seen.add(name)
            updated["name"] = name

            # Default category to "general" if missing or invalid
            cat = skill.get("category", "general")
            if not isinstance(cat, str) or not cat.strip():
                cat = "general"
            updated["category"] = cat.strip()

            result.append(updated)

        return result

    # ------------------------------------------------------------------ #
    # History persistence                                                  #
    # ------------------------------------------------------------------ #

    def _append_history(self, record: dict) -> None:
        try:
            os.makedirs(os.path.dirname(os.path.abspath(self.history_path)), exist_ok=True)
            with open(self.history_path, "a") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.warning("[SkillEvolver] could not write history: %s", e)
