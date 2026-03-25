"""
Process Reward Model (PRM) scorer.

Uses an OpenAI-compatible /v1/chat/completions endpoint as the judge,
so any external API (Anthropic, OpenAI, Together, etc.) works out of the box.

Public API:
    scorer = PRMScorer(
        prm_url="https://api.openai.com/v1",
        prm_model="gpt-5.2",
        api_key="sk-...",
        prm_m=3,
    )
    result = await scorer.evaluate(response_text, instruction_text)
    # result: {"score": float, "votes": list, "eval_text": str}
"""

import asyncio
import collections
import logging
import re
from typing import Any, Optional

from openai import OpenAI

logger = logging.getLogger(__name__)

_BOXED_RE = re.compile(r"\\boxed\{([-+]?\d)\}")
_SCORE_RE = re.compile(r"Score:\s*([-+]?\d)", re.IGNORECASE)

_GREEN = "\033[32m"
_CYAN = "\033[36m"
_RESET = "\033[0m"


# ------------------------------------------------------------------ #
# Pure helpers (no I/O)                                               #
# ------------------------------------------------------------------ #

def _sanitize_text(text: str) -> str:
    """Replace XML-like tags that may trigger content filters."""
    import re as _re
    # Replace <tool_call>...</tool_call> blocks with a neutral label
    text = _re.sub(r"<tool_call>.*?</tool_call>", "[tool_call block]", text, flags=_re.DOTALL)
    # Replace any remaining angle-bracket tags
    text = _re.sub(r"<[a-zA-Z_][^>]{0,80}>", "[tag]", text)
    text = _re.sub(r"</[a-zA-Z_][^>]{0,80}>", "[/tag]", text)
    return text


def _build_prm_judge_prompt(response_text: str, instruction_text: str) -> list[dict]:
    """Construct the judge messages for PRM evaluation."""
    system = (
        "You are a quality reviewer for conversational responses.\n"
        "You will be shown a user instruction and the assistant response to that instruction.\n"
        "Based on instruction alignment and task completion quality, decide whether the response was "
        "helpful (+1), unhelpful (-1), or unclear (0).\n"
        "Do NOT compare against any follow-up turn.\n"
        "Only evaluate whether the response addresses the given instruction.\n"
        "Use +1 when the response clearly follows and substantially completes the instruction.\n"
        "Use -1 when the response is off-task, wrong, or fails to complete core requirements.\n"
        "Use 0 when completion is ambiguous or evidence is insufficient.\n"
        "Think briefly, then end your reply with exactly one of: Score: 1 / Score: -1 / Score: 0"
    )
    clean_instruction = _sanitize_text(instruction_text)
    clean_response = _sanitize_text(response_text)
    user = (
        f"Instruction:\n{clean_instruction}\n\n"
        f"Response:\n{clean_response}\n\n"
        "Was the response helpful for this instruction? "
        "End with Score: 1, Score: -1, or Score: 0."
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def _build_prm_judge_prompt_followup_legacy(response_text: str, next_state_text: str) -> list[dict]:
    """Legacy follow-up-based prompt (kept only for backward compatibility/tests)."""
    system = (
        "You are a quality reviewer for conversational responses.\n"
        "You will be shown a response and the follow-up message that came after it.\n"
        "Based on the follow-up, decide whether the response was helpful (+1), unhelpful (-1), "
        "or unclear (0).\n"
        "Think briefly, then end your reply with exactly one of: Score: 1 / Score: -1 / Score: 0"
    )
    clean_next = _sanitize_text(next_state_text)
    clean_response = _sanitize_text(response_text)
    user = (
        f"Response:\n{clean_response}\n\n"
        f"Follow-up:\n{clean_next}\n\n"
        "Was the response helpful? End with Score: 1, Score: -1, or Score: 0."
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def _parse_prm_score(text: str) -> Optional[int]:
    """Parse score from model output.

    Accepts both formats:
      - "Score: 1" / "Score: -1" / "Score: 0"  (primary, avoids Azure filter)
      - "\\boxed{1}" / "\\boxed{-1}" / "\\boxed{0}"  (legacy fallback)
    """
    # Primary: "Score: N"
    matches = _SCORE_RE.findall(text)
    if matches:
        val = int(matches[-1])
        if val in (1, -1, 0):
            return val
    # Fallback: \boxed{N}
    matches = _BOXED_RE.findall(text)
    if matches:
        val = int(matches[-1])
        if val in (1, -1, 0):
            return val
    return None


def _majority_vote(scores: list[Optional[int]]) -> float:
    """Return the majority vote; ties or all-None → 0.0."""
    valid = [s for s in scores if s is not None]
    if not valid:
        return 0.0
    counter = collections.Counter(valid)
    top = counter.most_common(1)[0]
    if list(counter.values()).count(top[1]) > 1:
        return 0.0
    return float(top[0])


# ------------------------------------------------------------------ #
# PRMScorer class                                                      #
# ------------------------------------------------------------------ #

class PRMScorer:
    """
    Async PRM scorer using any OpenAI-compatible /v1/chat/completions API.

    Works with external providers (Anthropic, OpenAI, Together, Fireworks, etc.)
    or a self-hosted vLLM / LiteLLM proxy — anything that accepts
    POST /v1/chat/completions with {"model", "messages", ...}.

    Parameters
    ----------
    prm_url:
        Base URL of the API, e.g.
          - ``"https://api.anthropic.com/v1"``
          - ``"https://api.openai.com/v1"``
          - ``"http://localhost:8081/v1"``  (local vLLM)
    prm_model:
        Model name to pass in the request body.
    api_key:
        Bearer token.  If empty, no Authorization header is sent
        (useful for unauthenticated local endpoints).
    prm_m:
        Number of parallel votes for majority voting.
    temperature:
        Sampling temperature.
    max_new_tokens:
        Maximum tokens to generate per vote.
    """

    def __init__(
        self,
        prm_url: str,
        prm_model: str = "gpt-5.2",
        api_key: str = "",
        prm_m: int = 3,
        temperature: float = 0.6,
        max_new_tokens: int = 1024,
        llm_client=None,
    ):
        if llm_client is not None:
            self._client = llm_client
        else:
            base_url = prm_url.rstrip("/")
            client_kwargs: dict[str, Any] = {"api_key": api_key}
            client_kwargs["base_url"] = base_url
            self._client = OpenAI(**client_kwargs)

        self.prm_model = prm_model
        self.prm_m = prm_m
        self.temperature = temperature
        self.max_new_tokens = max_new_tokens

    async def evaluate(
        self,
        response: str,
        instruction: str,
        session_id: str = "",
        turn_num: int = 0,
    ) -> dict:
        """
        Score one assistant response against the instruction for that turn.

        Returns
        -------
        dict with keys:
            "score"     – float in {-1.0, 0.0, 1.0}
            "votes"     – list of per-vote scores (int | "fail")
            "eval_text" – representative evaluation text (non-empty when score != 0)
        """
        msgs = _build_prm_judge_prompt(response, instruction)

        results = await asyncio.gather(
            *[self._query_once(msgs, i) for i in range(self.prm_m)]
        )

        scores = [r[0] for r in results]
        final = _majority_vote(scores)

        representative = ""
        if final != 0.0:
            for s, text in results:
                if s is not None and s == int(final):
                    representative = text
                    break

        votes_display = [s if s is not None else "fail" for s in scores]
        logger.info(
            f"{_CYAN}[PRMScorer] session={session_id} turn={turn_num} "
            f"model={self.prm_model} votes={votes_display} → score={final}{_RESET}"
        )
        return {"score": final, "votes": votes_display, "eval_text": representative}

    async def _query_once(
        self, messages: list[dict], vote_id: int
    ) -> tuple[Optional[int], str]:
        try:
            completion = await asyncio.to_thread(
                self._client.chat.completions.create,
                model=self.prm_model,
                messages=messages,
                temperature=self.temperature,
                max_completion_tokens=self.max_new_tokens,
            )
            content = completion.choices[0].message.content or ""
            return _parse_prm_score(content), content
        except Exception as e:
            logger.warning("[PRMScorer] query failed (vote %d): %s", vote_id, e)
            return None, ""
