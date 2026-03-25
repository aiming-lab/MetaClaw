from __future__ import annotations

import logging
import re

LINE_PREFIX_RE = re.compile(r"^(.*?\|\s+(INFO|WARNING|ERROR|DEBUG)\s+\|\s+([^|]+)\|\s+)(.*)$")
POST_OK_RE = re.compile(r'"POST /v1/chat/completions HTTP/1\.1"\s+200 OK')
TOKENIZATION_KIMI_PLAIN_RE = re.compile(r"Calling super\(\)\.encode")
TOKENIZATION_KIMI_WORDS_PLAIN_RE = re.compile(r"^#words:\s+\d+\s+-\s+BOS ID:\s+\d+\s+-\s+EOS ID:\s+\d+")
TOKENIZATION_KIMI_RELOADED_RE = re.compile(r"^Reloaded tiktoken model from ")
HF_HUB_UNAUTH_PLAIN_RE = re.compile(r"unauthenticated requests to the HF Hub")
TINKER_CLIENT_INIT_PLAIN_RE = re.compile(
    r"^(TrainingClient initialized for model |ServiceClient initialized for session )"
)
TINKER_TELEMETRY_EXCEPTION_PLAIN_RE = re.compile(r"^Exception logged for session ID:\s+")
OPENCLAW_PLAIN_RE = re.compile(
    r"^(system prompt cached len=\d+|context truncated:|_forward_to_tinker msgs=\d+|_forward_to_llm msgs=\d+)"
)

ANSI_RESET = "\033[0m"
ANSI_BOLD = "\033[1m"
ANSI_BLUE = "\033[34m"
ANSI_CYAN = "\033[36m"
ANSI_GREEN = "\033[32m"
ANSI_YELLOW = "\033[33m"
ANSI_RED = "\033[31m"
ANSI_MAGENTA = "\033[35m"
ANSI_ORANGE = "\033[38;5;208m"  # orange (256-color)


def _info_color_for_logger(logger_name: str) -> str:
    name = logger_name.lower()
    if "metaclaw.api_server" in name:
        return ANSI_GREEN
    if "metaclaw.trainer" in name:
        return ANSI_BLUE
    if "metaclaw.launcher" in name:
        return ANSI_CYAN
    if "metaclaw.skill_manager" in name:
        return ANSI_MAGENTA
    if "metaclaw.skill_evolver" in name:
        return ANSI_YELLOW
    if "metaclaw.prm_scorer" in name:
        return ANSI_RED
    if "httpx" in name:
        return ANSI_CYAN
    if "transformers" in name or "huggingface" in name:
        return ANSI_YELLOW
    if "tinker" in name:
        return ANSI_MAGENTA
    return ANSI_BLUE


def _colorize_message(message: str, *, level: str, logger_name: str) -> str:
    text = message
    if "tokenization_kimi" in logger_name and TOKENIZATION_KIMI_RELOADED_RE.search(text):
        return f"{ANSI_BOLD}{ANSI_BLUE}{text}{ANSI_RESET}"
    if (
        "tokenization_kimi" in logger_name
        and (TOKENIZATION_KIMI_PLAIN_RE.search(text) or TOKENIZATION_KIMI_WORDS_PLAIN_RE.search(text))
    ):
        return text
    if "huggingface_hub.utils._http" in logger_name and HF_HUB_UNAUTH_PLAIN_RE.search(text):
        return text
    if (
        "tinker.lib.public_interfaces.service_client" in logger_name
        and TINKER_CLIENT_INIT_PLAIN_RE.search(text)
    ):
        return text
    if "tinker.lib.telemetry" in logger_name and TINKER_TELEMETRY_EXCEPTION_PLAIN_RE.search(text):
        return text
    if "[OpenClaw]" in text and OPENCLAW_PLAIN_RE.search(text.replace("[OpenClaw] ", "", 1)):
        return text
    if "[SkillManager]" in text:
        return f"{ANSI_BOLD}{ANSI_MAGENTA}{text}{ANSI_RESET}"
    if "[Trainer]" in text:
        return f"{ANSI_BOLD}{ANSI_BLUE}{text}{ANSI_RESET}"
    if "[SkillEvolver]" in text:
        return f"{ANSI_BOLD}{ANSI_YELLOW}{text}{ANSI_RESET}"
    if "[Scheduler]" in text:
        return f"{ANSI_BOLD}{ANSI_ORANGE}{text}{ANSI_RESET}"
    if "[OpenClaw]" in text:
        if "context truncated" in text:
            return f"{ANSI_BOLD}{ANSI_RED}{text}{ANSI_RESET}"
        if "tool_calls:" in text or "parsed tool_calls after extract" in text:
            return f"{ANSI_BOLD}{ANSI_CYAN}{text}{ANSI_RESET}"
        if "_forward_to_tinker" in text or "_forward_to_llm" in text:
            return f"{ANSI_BOLD}{ANSI_CYAN}{text}{ANSI_RESET}"
        if "session=" in text and "done → cleaned up" in text:
            return f"{ANSI_BOLD}{ANSI_YELLOW}{text}{ANSI_RESET}"
        if "[main]" in text.lower() or " MAIN session=" in text:
            return f"{ANSI_BOLD}{ANSI_GREEN}{text}{ANSI_RESET}"
        if "[side]" in text.lower() or " SIDE session=" in text:
            return f"{ANSI_BOLD}{ANSI_BLUE}{text}{ANSI_RESET}"
        if "proxy ready" in text:
            return f"{ANSI_BOLD}{ANSI_CYAN}{text}{ANSI_RESET}"
        return f"{ANSI_GREEN}{text}{ANSI_RESET}"
    if POST_OK_RE.search(text):
        return f"{ANSI_BOLD}{ANSI_MAGENTA}{text}{ANSI_RESET}"
    if "[RolloutWorker]" in text:
        return f"{ANSI_BOLD}{ANSI_CYAN}{text}{ANSI_RESET}"
    if text.startswith("======================================================================"):
        return f"{ANSI_CYAN}{text}{ANSI_RESET}"
    if "[OpenClaw] proxy ready" in text or re.search(r"proxy 0\.0\.0\.0:\d+", text):
        return f"{ANSI_BOLD}{ANSI_CYAN}{text}{ANSI_RESET}"
    if "| __main__ | [Replay]" in text or text.startswith("[Replay][Manual]"):
        return f"{ANSI_BOLD}{ANSI_BLUE}{text}{ANSI_RESET}"
    if '"GET /docs HTTP/1.1" 200 OK' in text:
        return f"{ANSI_GREEN}{text}{ANSI_RESET}"

    if level == "INFO":
        level_color = _info_color_for_logger(logger_name)
    elif level == "WARNING":
        level_color = ANSI_YELLOW
    elif level == "ERROR":
        level_color = ANSI_RED
    elif level == "DEBUG":
        level_color = ANSI_MAGENTA
    else:
        return text
    return f"{ANSI_BOLD}{level_color}{text}{ANSI_RESET}"


class MetaClawColorFormatter(logging.Formatter):
    def __init__(self, fmt: str, *, use_color: bool):
        super().__init__(fmt=fmt)
        self.use_color = use_color

    def format(self, record: logging.LogRecord) -> str:
        rendered = super().format(record)
        if not self.use_color:
            return rendered
        match = LINE_PREFIX_RE.match(rendered)
        if not match:
            return rendered
        prefix = match.group(1)
        level = match.group(2)
        logger_name = match.group(3).strip()
        message = match.group(4)
        return f"{prefix}{_colorize_message(message, level=level, logger_name=logger_name)}"


def setup_logging() -> None:
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers.clear()
    handler = logging.StreamHandler()
    fmt = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    handler.setFormatter(MetaClawColorFormatter(fmt, use_color=handler.stream.isatty()))
    root.addHandler(handler)
