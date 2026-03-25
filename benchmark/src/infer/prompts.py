"""Prompt templates used by infer_cmd to communicate with the benchmark agent."""

# Appended to every error feedback so the agent moves on rather than retrying.
CONTINUE_REMINDER = "Keep this in mind as you continue with the next task."

# ── multi_choice: missing \bbox{} format ──────────────────────────────────
FORMAT_ERROR = (
    r"Note: your previous response did not include a \bbox{X} answer "
    r"(e.g. \bbox{A} for a single option, or \bbox{A,B} for multiple options). "
    + CONTINUE_REMINDER
)

# ── multi_choice: per-option error lines ──────────────────────────────────

def missed_option(opt: str, explanation: str) -> str:
    return f"You missed option {opt}: {explanation}"


def wrong_option(opt: str, explanation: str) -> str:
    return f"You incorrectly selected option {opt}: {explanation}"


# ── file_check: suffix appended to incorrect feedback ─────────────────────
FILE_CHECK_INCORRECT_SUFFIX = CONTINUE_REMINDER

# ── Message wrappers ──────────────────────────────────────────────────────
_FEEDBACK_MARKER = "[Previous Feedback]"


def with_feedback(feedback_text: str, question_text: str) -> str:
    return f"{_FEEDBACK_MARKER} {feedback_text}\n\n{question_text}"


def standalone_feedback(feedback_text: str) -> str:
    return f"{_FEEDBACK_MARKER} {feedback_text}"
