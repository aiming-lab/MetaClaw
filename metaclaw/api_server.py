"""
FastAPI proxy server for OpenClaw RL training data collection.

Adapted from OpenClaw-RL/openclaw-rl/openclaw_api_server.py.
Key changes vs. the original:
  - SGLang HTTP forward replaced with Tinker SamplingClient.sample_async
  - slime.utils.types.Sample replaced with ConversationSample
  - Skills injection via SkillManager
  - update_sampling_client() for hot-swapping after weight updates

Architecture mirrors OpenClaw-RL exactly:
  - threading.Event for submission gating (passed in from rollout worker)
  - queue.Queue for output (passed in from rollout worker)
  - start() / stop() threading lifecycle
  - Data production is request-driven in FastAPI handlers
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import queue
import re
import threading
import time
from itertools import count
from typing import Any, Optional

import uvicorn
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from openai import OpenAI

from .config import MetaClawConfig
from .data_formatter import ConversationSample
from .prm_scorer import PRMScorer
from .skill_manager import SkillManager
from .utils import run_llm

logger = logging.getLogger(__name__)

_GREEN = "\033[32m"
_YELLOW = "\033[33m"
_RED = "\033[31m"
_CYAN = "\033[36m"
_RESET = "\033[0m"

_NON_STANDARD_BODY_KEYS = {"session_id", "session_done", "turn_type"}


# ------------------------------------------------------------------ #
# Helper utilities                                                     #
# ------------------------------------------------------------------ #

def _flatten_message_content(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = [
            item.get("text", "")
            for item in content
            if isinstance(item, dict) and item.get("type") == "text"
        ]
        return " ".join(parts) if parts else ""
    return str(content) if content is not None else ""


def _normalize_assistant_content_parts(content: list[dict]) -> tuple[str, list[dict]]:
    """Extract plain text and OpenAI-style tool_calls from assistant content parts."""
    text_parts: list[str] = []
    tool_calls: list[dict] = []
    for i, item in enumerate(content):
        if not isinstance(item, dict):
            continue
        item_type = item.get("type")
        if item_type == "text":
            text = item.get("text")
            if isinstance(text, str) and text:
                text_parts.append(text)
        elif item_type == "toolCall":
            name = item.get("name")
            args = item.get("arguments", {})
            if not isinstance(args, str):
                try:
                    args = json.dumps(args, ensure_ascii=False)
                except Exception:
                    args = "{}"
            tc_id = item.get("id") or f"call_{i}"
            tool_calls.append(
                {
                    "id": tc_id,
                    "type": "function",
                    "function": {
                        "name": name or "unknown_tool",
                        "arguments": args,
                    },
                }
            )
    return (" ".join(text_parts).strip(), tool_calls)


_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)
_TOOL_HANDLE_RE = re.compile(r"^call_(?:kimi|xml)_\d+$")
_KIMI_TOOL_CALL_RE = re.compile(
    r"<\|tool_call_begin\|>\s*([a-zA-Z0-9_.-]+)(?::\d+)?\s*"
    r"<\|tool_call_argument_begin\|>\s*(\{.*?\})\s*"
    r"<\|tool_call_end\|>",
    re.DOTALL,
)
_QWEN_TOOL_CALL_RE = re.compile(r"<tool_call>\s*(.*?)\s*</tool_call>", re.DOTALL)

def _normalize_tool_name(raw_name: str, args_raw: str) -> str:
    """
    Normalize tool names from model output.
    Fixes common drift where a call handle (e.g. call_kimi_0) is emitted as
    function name instead of the actual tool name.
    """
    name = (raw_name or "").strip()
    if name.startswith("functions."):
        name = name.split(".", 1)[1]
    if not _TOOL_HANDLE_RE.fullmatch(name):
        return name or "unknown_tool"

    try:
        args_obj = json.loads(args_raw or "{}")
    except Exception:
        args_obj = {}
    if isinstance(args_obj, dict):
        if isinstance(args_obj.get("command"), str) and args_obj.get("command"):
            return "exec"
        if isinstance(args_obj.get("sessionId"), str) and args_obj.get("sessionId"):
            return "process"
    return "unknown_tool"

def _extract_tool_calls_from_text(text: str) -> tuple[str, list[dict]]:
    """
    Parse tool-call tags embedded in assistant text into OpenAI-style tool_calls.
    Supports Kimi markers and Qwen <tool_call> wrappers.
    """
    if not text:
        return "", []

    tool_calls: list[dict] = []

    for i, m in enumerate(_KIMI_TOOL_CALL_RE.finditer(text)):
        raw_name = (m.group(1) or "").strip()
        args_raw = (m.group(2) or "{}").strip()
        tool_name = _normalize_tool_name(raw_name, args_raw)
        try:
            args_obj = json.loads(args_raw)
            args_str = json.dumps(args_obj, ensure_ascii=False)
        except Exception:
            args_str = args_raw if args_raw else "{}"
        tool_calls.append(
            {
                "id": f"call_kimi_{i}",
                "type": "function",
                "function": {"name": tool_name or "unknown_tool", "arguments": args_str},
            }
        )

    for i, m in enumerate(_QWEN_TOOL_CALL_RE.finditer(text), start=len(tool_calls)):
        payload_raw = (m.group(1) or "").strip()
        try:
            payload = json.loads(payload_raw)
        except Exception:
            continue
        name = (
            payload.get("name")
            or payload.get("tool_name")
            or payload.get("function", {}).get("name")
            or "unknown_tool"
        )
        args = payload.get("arguments") or payload.get("function", {}).get("arguments") or {}
        if not isinstance(args, str):
            try:
                args = json.dumps(args, ensure_ascii=False)
            except Exception:
                args = "{}"
        name = _normalize_tool_name(str(name), args)
        tool_calls.append(
            {
                "id": f"call_xml_{i}",
                "type": "function",
                "function": {"name": name, "arguments": args},
            }
        )

    clean = text
    clean = _THINK_RE.sub("", clean)
    clean = clean.replace("</think>", "")
    # Keep tool call data only in structured field; strip markup from plain text.
    clean = re.sub(r"<\|tool_call_begin\|>.*?<\|tool_call_end\|>", "", clean, flags=re.DOTALL)
    clean = re.sub(r"<\|tool_calls_section_begin\|>.*?<\|tool_calls_section_end\|>", "", clean, flags=re.DOTALL)
    clean = _QWEN_TOOL_CALL_RE.sub("", clean)
    clean = clean.strip()
    return clean, tool_calls


def _normalize_messages_for_template(messages: list[dict]) -> list[dict]:
    """Normalize OpenClaw-style messages into chat-template-compatible format."""
    out = []
    for msg in messages:
        m = dict(msg)
        role = m.get("role")

        if role == "developer":
            m["role"] = "system"
            role = "system"

        # OpenClaw tool result message → OpenAI tool message
        if role == "toolResult":
            tool_msg: dict[str, Any] = {
                "role": "tool",
                "content": _flatten_message_content(m.get("content")),
            }
            tc_id = m.get("toolCallId") or m.get("tool_call_id")
            if tc_id:
                tool_msg["tool_call_id"] = tc_id
            tool_name = m.get("toolName") or m.get("name")
            if tool_name:
                tool_msg["name"] = tool_name
            out.append(tool_msg)
            continue

        # assistant content parts may contain text + toolCall blocks
        raw = m.get("content")
        if role == "assistant" and isinstance(raw, list):
            text, tool_calls = _normalize_assistant_content_parts(raw)
            m["content"] = text
            if tool_calls:
                m["tool_calls"] = tool_calls
        elif not isinstance(raw, str) and raw is not None:
            m["content"] = _flatten_message_content(raw)

        out.append(m)
    return out


def _extract_last_user_instruction(messages: list[dict]) -> str:
    """Return the most recent user message text from the current turn context."""
    for msg in reversed(messages):
        if isinstance(msg, dict) and msg.get("role") == "user":
            text = _flatten_message_content(msg.get("content"))
            if text:
                return text
    return ""


def _extract_logprobs_from_chat_response(choice: dict[str, Any]) -> list[float]:
    logprobs_obj = choice.get("logprobs")
    if not isinstance(logprobs_obj, dict):
        return []
    content = logprobs_obj.get("content")
    if not isinstance(content, list):
        return []
    return [float(item.get("logprob", 0.0)) for item in content if isinstance(item, dict)]


def _rewrite_new_session_bootstrap_prompt(messages: list[dict]) -> tuple[list[dict], int]:
    """Rewrite OpenClaw /new bootstrap user prompt to a safer variant.

    Some upstream providers over-trigger policy filters on the stock bootstrap
    text ("A new session was started via /new or /reset ..."). This keeps
    behavior while avoiding brittle phrasing.
    """
    rewritten = 0
    out: list[dict] = []
    for msg in messages:
        if not isinstance(msg, dict):
            out.append(msg)
            continue
        if msg.get("role") != "user":
            out.append(msg)
            continue
        text = _flatten_message_content(msg.get("content"))
        lowered = text.lower()
        if "a new session was started via /new or /reset" in lowered:
            out.append(
                {
                    **msg,
                    "content": (
                        "A new chat session just started. "
                        "Greet the user briefly in 1-3 sentences and ask what they want to do."
                    ),
                }
            )
            rewritten += 1
            continue
        out.append(msg)
    return out, rewritten


# ------------------------------------------------------------------ #
# MetaClawAPIServer                                                    #
# ------------------------------------------------------------------ #

class MetaClawAPIServer:
    """Proxy between OpenClaw and Tinker for RL training data collection.

    OpenClaw sends ``X-Session-Id`` and ``X-Turn-Type`` headers with every
    request.  The proxy forwards to Tinker SamplingClient, and when
    ``turn_type`` is ``"main"`` it tokenises the full prompt+response and
    submits a training sample.  Side tasks (``turn_type != "main"``) are
    forwarded but produce no training data.

    Parameters
    ----------
    config:
        MetaClawConfig instance.
    output_queue:
        Thread-safe queue for (group_index, [ConversationSample]) tuples.
        Created and owned by the rollout worker.
    submission_enabled:
        threading.Event that gates sample submission.
        Set = accepting samples; clear = paused for weight update.
    sampling_client:
        Tinker SamplingClient. Can be None and set later via
        update_sampling_client().
    skill_manager:
        Optional SkillManager for injecting skills into system prompts.
    prm_scorer:
        Optional PRMScorer. If None, all samples get reward=0.
    """

    def __init__(
        self,
        config: MetaClawConfig,
        output_queue: queue.Queue,
        submission_enabled: threading.Event,
        sampling_client=None,
        skill_manager: Optional[SkillManager] = None,
        prm_scorer: Optional[PRMScorer] = None,
        skill_evolver=None,
        last_request_tracker=None,
    ):
        self.config = config
        self.output_queue = output_queue
        self.submission_enabled = submission_enabled
        self._sampling_client = sampling_client
        self.skill_manager = skill_manager
        self.prm_scorer = prm_scorer
        self.skill_evolver = skill_evolver
        # Optional LastRequestTracker for scheduler idle detection
        self._last_request_tracker = last_request_tracker

        self._served_model = config.served_model_name
        self._expected_api_key = config.api_key
        os.makedirs(config.record_dir, exist_ok=True)
        self._system_prompt_cache_file = os.path.join(
            config.record_dir, "system_prompt_cache.json"
        )

        # State machines
        self._index_counter = count(0)
        self._group_counter = count(0)
        self._turn_counts: dict[str, int] = {}
        self._pending_turn_data: dict[str, dict[int, dict]] = {}  # session → {turn → data}
        self._prm_tasks: dict[str, dict[int, asyncio.Task]] = {}  # session → {turn → task}
        self._teacher_tasks: dict[str, dict[int, asyncio.Task]] = {}  # session → {turn → task} (OPD)
        self._pending_records: dict[str, dict] = {}               # for record logging
        self._session_effective: dict[str, int] = {}              # at-least-one guarantee
        # skills_only: buffer turns per session for skill evolution
        self._session_turns: dict[str, list] = {}

        # OPD teacher model client
        self._teacher_client: Optional[OpenAI] = None
        if config.use_opd and config.teacher_url:
            self._teacher_client = OpenAI(
                base_url=config.teacher_url,
                api_key=config.teacher_api_key or "unused",
            )
            logger.info("[OpenClaw] OPD teacher client ready: url=%s model=%s",
                        config.teacher_url, config.teacher_model)
        elif config.use_opd and not config.teacher_url:
            logger.warning("[OpenClaw] use_opd=True but teacher_url is empty — teacher logprobs disabled")

        # Record files
        self._record_file = ""
        self._prm_record_file = ""
        if config.record_enabled:
            os.makedirs(config.record_dir, exist_ok=True)
            self._record_file = os.path.join(config.record_dir, "conversations.jsonl")
            self._prm_record_file = os.path.join(config.record_dir, "prm_scores.jsonl")
            with open(self._record_file, "w"):
                pass
            with open(self._prm_record_file, "w"):
                pass

        # Tokenizer is used in both modes for prompt length accounting/truncation,
        # and in RL mode additionally for training sample tokenization.
        self._tokenizer = self._load_tokenizer()
        self.app = self._build_app()

        # Threading lifecycle (set by start())
        self._server: Optional[uvicorn.Server] = None
        self._thread: Optional[threading.Thread] = None

    # ------------------------------------------------------------------ #
    # Tokenizer                                                            #
    # ------------------------------------------------------------------ #

    def _load_tokenizer(self):
        try:
            from transformers import AutoTokenizer
            return AutoTokenizer.from_pretrained(
                self.config.model_name, trust_remote_code=True
            )
        except Exception as e:
            logger.warning("[OpenClaw] could not load tokenizer: %s", e)
            return None

    # ------------------------------------------------------------------ #
    # FastAPI app                                                          #
    # ------------------------------------------------------------------ #

    def _build_app(self) -> FastAPI:
        app = FastAPI(title="MetaClaw Proxy")
        app.state.owner = self

        @app.get("/healthz")
        async def healthz():
            return {"ok": True}

        @app.post("/v1/chat/completions")
        async def chat_completions(
            request: Request,
            authorization: Optional[str] = Header(default=None),
            x_session_id: Optional[str] = Header(default=None),
            x_turn_type: Optional[str] = Header(default=None),
            x_session_done: Optional[str] = Header(default=None),
        ):
            owner: MetaClawAPIServer = request.app.state.owner
            # Update idle tracker so the scheduler knows the user is active
            if owner._last_request_tracker is not None:
                owner._last_request_tracker.touch()
            await owner._check_auth(authorization)
            if not owner.submission_enabled.is_set():
                # Queue requests while submission is paused instead of returning 503.
                # Use a bounded wait so clients don't hang forever on abnormal stalls.
                resumed = await asyncio.to_thread(owner.submission_enabled.wait, 300.0)
                if not resumed:
                    raise HTTPException(
                        status_code=503,
                        detail="submission paused for weight update (wait timeout)",
                    )

            body = await request.json()
            incoming_messages = body.get("messages", [])
            if isinstance(incoming_messages, list):
                rewritten_messages, rewritten = _rewrite_new_session_bootstrap_prompt(
                    incoming_messages
                )
                body["messages"] = rewritten_messages
            else:
                rewritten = 0
            _raw_sid = x_session_id or body.get("session_id") or ""
            # TUI mode: OpenClaw does not send X-Session-Id/X-Turn-Type.
            # Fall back to a model-derived session ID and treat as "main" so
            # TUI conversations are collected as training data.
            if _raw_sid:
                session_id = _raw_sid
                turn_type = (x_turn_type or body.get("turn_type") or "side").strip().lower()
            else:
                session_id = f"tui-{body.get('model', 'default')}"
                turn_type = (x_turn_type or body.get("turn_type") or "main").strip().lower()
            session_done = (
                (x_session_done and x_session_done.strip().lower() in {"1", "true", "yes", "on"})
                or str(body.get("session_done", "")).strip().lower() in {"1", "true", "yes", "on"}
            )
            # Do not infer session_done from bootstrap text — only explicit X-Session-Done or body session_done trigger evolution.

            stream = bool(body.get("stream", False))
            result = await owner._handle_request(
                body,
                session_id=session_id,
                turn_type=turn_type,
                session_done=session_done,
            )
            if stream:
                return StreamingResponse(
                    owner._stream_response(result), media_type="text/event-stream"
                )
            return JSONResponse(content=result["response"])

        return app

    async def _check_auth(self, authorization: Optional[str]):
        if not self._expected_api_key:
            return
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="missing bearer token")
        token = authorization.split(" ", 1)[1].strip()
        if token != self._expected_api_key:
            raise HTTPException(status_code=401, detail="invalid api key")

    # ------------------------------------------------------------------ #
    # Record helpers                                                       #
    # ------------------------------------------------------------------ #

    def _flush_pending_record(self, session_id: str, next_state):
        """Write out the buffered record for *session_id* and fire PRM."""
        rec = self._pending_records.pop(session_id, None)
        if rec is None:
            return
        rec["next_state"] = next_state
        if next_state:
            ns_role = next_state.get("role", "?")
            ns_content = _flatten_message_content(next_state.get("content"))
            logger.info(
                f"{_GREEN}[OpenClaw] session={session_id} turn={rec['turn']} "
                f"next_state role={ns_role} len={len(ns_content)}: "
                f"{ns_content[:200]}{_RESET}"
            )
            self._fire_prm_scoring(
                session_id,
                rec["turn"],
                rec["response_text"],
                rec.get("instruction_text", ""),
                next_state,
            )
        if self._record_file:
            try:
                with open(self._record_file, "a", encoding="utf-8") as f:
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            except OSError as e:
                logger.warning("[OpenClaw] failed to write record: %s", e)

    def _buffer_record(self, session_id: str, turn_num: int, messages: list,
                       prompt_text: str, response_text: str, tool_calls: list):
        if not self._record_file:
            return
        instruction_text = _extract_last_user_instruction(messages)
        self._pending_records[session_id] = {
            "session_id": session_id,
            "turn": turn_num,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "messages": messages,
            "instruction_text": instruction_text,
            "prompt_text": prompt_text,
            "response_text": response_text,
            "tool_calls": tool_calls or None,
        }

    def _append_prm_record(self, session_id: str, turn_num: int,
                           score: float, votes: list):
        if not self._prm_record_file:
            return
        try:
            with open(self._prm_record_file, "a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "session_id": session_id,
                    "turn": turn_num,
                    "score": score,
                    "votes": votes,
                }, ensure_ascii=False) + "\n")
        except OSError as e:
            logger.warning("[OpenClaw] failed to write PRM record: %s", e)

    def purge_record_files(self):
        """Clear all record JSONL files. Called when training starts."""
        for path, label in [
            (self._record_file, "record"),
            (self._prm_record_file, "PRM record"),
        ]:
            if not path:
                continue
            try:
                open(path, "w").close()
                logger.info("[OpenClaw] %s file purged: %s", label, path)
            except OSError as e:
                logger.warning("[OpenClaw] failed to purge %s file: %s", label, e)

    # ------------------------------------------------------------------ #
    # PRM scoring                                                          #
    # ------------------------------------------------------------------ #

    def _fire_prm_scoring(self, session_id: str, turn_num: int,
                          response_text: str, instruction_text: str, next_state):
        if not self.prm_scorer or not next_state:
            return
        inst_text = instruction_text or ""
        task = asyncio.create_task(
            self.prm_scorer.evaluate(
                response_text, inst_text, session_id=session_id, turn_num=turn_num
            )
        )
        task.add_done_callback(self._task_done_cb)
        task.add_done_callback(
            lambda _t: self._maybe_submit_ready_samples(session_id)
        )
        self._prm_tasks.setdefault(session_id, {})[turn_num] = task
        td = self._pending_turn_data.get(session_id, {}).get(turn_num)
        if td is not None:
            td["has_next_state"] = True

    # ------------------------------------------------------------------ #
    # OPD teacher logprobs                                                 #
    # ------------------------------------------------------------------ #

    async def _query_teacher_logprobs(
        self, prompt_text: str, response_text: str, num_response_tokens: int
    ) -> list[float]:
        """Query teacher model for per-token logprobs on the student's response.

        Uses the OpenAI-compatible ``/v1/completions`` endpoint with ``echo=True``
        and ``max_tokens=0`` to obtain the teacher's log-probabilities for each
        token of the student's generated response without producing new tokens.
        """
        full_text = prompt_text + response_text

        response = await asyncio.to_thread(
            self._teacher_client.completions.create,
            model=self.config.teacher_model,
            prompt=full_text,
            echo=True,
            logprobs=1,
            max_tokens=0,
        )

        choice = response.choices[0]
        token_logprobs = choice.logprobs.token_logprobs or []

        # Find where response tokens start (use student tokenizer as reference)
        prompt_token_count = len(
            self._tokenizer(prompt_text, add_special_tokens=False)["input_ids"]
        )

        teacher_lps = [
            float(lp) if lp is not None else 0.0
            for lp in token_logprobs[prompt_token_count:]
        ]

        # Align to student's response token count
        if len(teacher_lps) > num_response_tokens:
            teacher_lps = teacher_lps[:num_response_tokens]
        elif len(teacher_lps) < num_response_tokens:
            teacher_lps = teacher_lps + [0.0] * (num_response_tokens - len(teacher_lps))

        return teacher_lps

    def _fire_teacher_query(
        self, session_id: str, turn_num: int,
        prompt_text: str, response_text: str, num_response_tokens: int,
    ):
        """Fire an async teacher-logprobs query (OPD mode)."""
        task = asyncio.create_task(
            self._query_teacher_logprobs(prompt_text, response_text, num_response_tokens)
        )
        task.add_done_callback(self._task_done_cb)
        task.add_done_callback(
            lambda _t: self._maybe_submit_ready_samples(session_id)
        )
        self._teacher_tasks.setdefault(session_id, {})[turn_num] = task

    # ------------------------------------------------------------------ #
    # Request handling                                                     #
    # ------------------------------------------------------------------ #

    def _read_cached_system_prompt(self) -> str:
        try:
            with open(self._system_prompt_cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            cached = data.get("compressed_system_prompt", "")
            return cached if isinstance(cached, str) else ""
        except Exception:
            return ""

    def _write_cached_system_prompt(self, prompt: str):
        try:
            with open(self._system_prompt_cache_file, "w", encoding="utf-8") as f:
                json.dump({"compressed_system_prompt": prompt}, f, ensure_ascii=False)
        except Exception as e:
            logger.warning("[OpenClaw] failed to write system prompt cache: %s", e)

    async def _handle_request(
        self,
        body: dict[str, Any],
        session_id: str,
        turn_type: str,
        session_done: bool,
    ) -> dict[str, Any]:
        messages = body.get("messages")
        if not isinstance(messages, list) or not messages:
            raise HTTPException(status_code=400, detail="messages must be a non-empty list")
        rewritten = 0
        for msg in messages:
            if (
                isinstance(msg, dict)
                and msg.get("role") == "user"
                and isinstance(msg.get("content"), str)
                and msg.get("content", "").startswith("A new chat session just started.")
            ):
                rewritten += 1
        if rewritten:
            logger.info("[OpenClaw] rewrote %d /new bootstrap user prompt(s) for provider safety", rewritten)

        def _prompt_len(msgs):
            try:
                norm_msgs = _normalize_messages_for_template(msgs)
                text = self._tokenizer.apply_chat_template(
                    norm_msgs, tools=body.get("tools"), tokenize=False, add_generation_prompt=True,
                )
                return len(self._tokenizer(text, add_special_tokens=False)["input_ids"])
            except Exception:
                return 0

        cached_system = self._read_cached_system_prompt()
        if not cached_system:
            raw_system = ""
            for m in messages:
                if isinstance(m, dict) and m.get("role") == "system":
                    raw_system = _flatten_message_content(m.get("content"))
                    break
            if raw_system:
                cached_system = await asyncio.to_thread(
                    run_llm,
                    [{"role": "user", "content": raw_system}],
                )
                cached_system = (cached_system or raw_system).strip()
                self._write_cached_system_prompt(cached_system)

        if cached_system:
            for m in messages:
                if isinstance(m, dict) and m.get("role") == "system":
                    m["content"] = cached_system

        tools = body.get("tools")

        # Inject skills into system message for main turns
        if self.skill_manager and turn_type == "main":
            messages = self._inject_skills(messages)
        logger.info(
            "[OpenClaw] system prompt cached len=%d",
            _prompt_len([{"role": "system", "content": cached_system}]),
        )

        # Truncate to fit within max_context_tokens (keep system + most-recent messages)
        max_prompt = self.config.max_context_tokens - int(body.get("max_tokens") or 2048)
        if max_prompt > 0:
            messages = self._truncate_messages(messages, tools, max_prompt)

        forward_body = {k: v for k, v in body.items() if k not in _NON_STANDARD_BODY_KEYS}
        forward_body["stream"] = False
        forward_body.pop("stream_options", None)
        forward_body["logprobs"] = True
        forward_body["top_logprobs"] = 1
        if "model" not in forward_body:
            forward_body["model"] = self._served_model
        forward_body["messages"] = messages  # potentially skill-injected

        if self.config.mode == "skills_only":
            output = await self._forward_to_llm(forward_body)
        else:
            output = await self._forward_to_tinker(forward_body)

        choice = output.get("choices", [{}])[0]
        assistant_msg = choice.get("message", {})
        tool_calls = assistant_msg.get("tool_calls") or []
        content = assistant_msg.get("content") or ""
        reasoning = assistant_msg.get("reasoning_content") or ""

        logger.info(
            f"{_YELLOW}[OpenClaw] [{turn_type}] session={session_id} "
            f"prompt_msgs={len(messages)}{_RESET}"
        )
        logger.info(
            f"{_RED}[OpenClaw] [{turn_type}] session={session_id} "
            f"thinking={len(reasoning)} chars, response:\n{content}{_RESET}"
        )
        if tool_calls:
            logger.info("[OpenClaw] tool_calls: %s", json.dumps(tool_calls, ensure_ascii=False)[:500])

        if turn_type == "main":
            if session_id in self._pending_records and messages:
                self._flush_pending_record(session_id, messages[-1])

            response_msg = dict(assistant_msg)
            if response_msg.get("content") is None:
                response_msg["content"] = ""

            norm_msgs = _normalize_messages_for_template(messages)
            norm_resp = _normalize_messages_for_template([response_msg])[0]
            full_norm = norm_msgs + [norm_resp]

            if self._tokenizer is None:
                # skills_only mode: record conversation and buffer for skill evolution
                self._turn_counts[session_id] = self._turn_counts.get(session_id, 0) + 1
                turn_num = self._turn_counts[session_id]
                prompt_text_simple = "\n".join(
                    f"{m.get('role', '?')}: {_flatten_message_content(m.get('content', ''))}"
                    for m in messages
                )
                response_text_simple = content or (
                    json.dumps(tool_calls, ensure_ascii=False) if tool_calls else ""
                )
                self._buffer_record(
                    session_id, turn_num, messages,
                    prompt_text_simple, response_text_simple, tool_calls,
                )
                if self.skill_evolver and self.config.enable_skill_evolution:
                    self._session_turns.setdefault(session_id, []).append({
                        "prompt_text": prompt_text_simple,
                        "response_text": response_text_simple,
                    })
                output["session_id"] = session_id
                return {"response": output}

            prompt_text = self._tokenizer.apply_chat_template(
                norm_msgs, tools=tools, tokenize=False, add_generation_prompt=True,
            )
            full_text = self._tokenizer.apply_chat_template(
                full_norm, tools=tools, tokenize=False, add_generation_prompt=False,
            )

            if full_text.startswith(prompt_text):
                response_text = full_text[len(prompt_text):]
            else:
                logger.warning("[OpenClaw] prompt_text not prefix of full_text, using full_text as response")
                response_text = full_text

            prompt_ids = self._tokenizer(prompt_text, add_special_tokens=False)["input_ids"]
            response_ids = self._tokenizer(response_text, add_special_tokens=False)["input_ids"]

            if not response_ids and not response_text.strip() and not tool_calls:
                logger.info("[OpenClaw] MAIN session=%s → empty response, skipping", session_id)
                output["session_id"] = session_id
                return {"response": output}

            response_logprobs = _extract_logprobs_from_chat_response(choice)
            if len(response_logprobs) > len(response_ids):
                response_logprobs = response_logprobs[: len(response_ids)]
            elif len(response_logprobs) < len(response_ids):
                response_logprobs = response_logprobs + [0.0] * (len(response_ids) - len(response_logprobs))

            turn_data = {
                "prompt_ids": prompt_ids,
                "response_ids": response_ids,
                "response_logprobs": response_logprobs,
                "prompt_text": prompt_text,
                "response_text": response_text,
            }

            self._turn_counts[session_id] = self._turn_counts.get(session_id, 0) + 1
            turn_num = self._turn_counts[session_id]

            logger.info(
                "[OpenClaw] MAIN session=%s turn=%d prompt_tokens=%d response_tokens=%d",
                session_id, turn_num, len(prompt_ids), len(response_ids),
            )
            self._buffer_record(session_id, turn_num, messages, prompt_text, response_text, tool_calls)
            # Keep skills_only auto-summarization working even when tokenizer is loaded.
            if (
                self.config.mode == "skills_only"
                and self.skill_evolver
                and self.config.enable_skill_evolution
            ):
                self._session_turns.setdefault(session_id, []).append(
                    {
                        "prompt_text": prompt_text,
                        "response_text": response_text,
                    }
                )
            self._pending_turn_data.setdefault(session_id, {})[turn_num] = turn_data
            if self.config.use_opd and self._teacher_client:
                self._fire_teacher_query(
                    session_id, turn_num, prompt_text, response_text, len(response_ids),
                )
            self._maybe_submit_ready_samples(session_id)
        else:
            logger.info("[OpenClaw] SIDE session=%s → skipped (no training data)", session_id)

        if session_done:
            self._flush_pending_record(session_id, None)
            self._maybe_submit_ready_samples(session_id, force_no_prm=True)
            eff = self._session_effective.pop(session_id, 0)
            self._turn_counts.pop(session_id, None)
            self._teacher_tasks.pop(session_id, None)
            logger.info("[OpenClaw] session=%s done → cleaned up (effective_samples=%d)", session_id, eff)
            # skills_only: trigger async skill evolution from this session's turns
            turns = self._session_turns.pop(session_id, [])
            if turns and self.skill_evolver and self.config.enable_skill_evolution:
                self._safe_create_task(self._evolve_skills_for_session(turns))

        output["session_id"] = session_id
        return {"response": output}

    # ------------------------------------------------------------------ #
    # Tinker forwarding                                                    #
    # ------------------------------------------------------------------ #

    async def _forward_to_tinker(self, body: dict[str, Any]) -> dict[str, Any]:
        """Forward the request to Tinker via SamplingClient.sample_async."""
        import tinker

        if self._sampling_client is None:
            raise HTTPException(status_code=503, detail="no Tinker sampling client available")
        if self._tokenizer is None:
            raise HTTPException(status_code=503, detail="no tokenizer available")

        try:
            messages = body.get("messages", [])
            norm_msgs = _normalize_messages_for_template(messages)
            tools = body.get("tools")
            temperature = float(body.get("temperature", 0.7))
            max_tokens = int(body.get("max_tokens") or 2048)
            stop = body.get("stop")

            logger.info("[OpenClaw] _forward_to_tinker msgs=%d max_tokens=%d", len(norm_msgs), max_tokens)

            # Apply chat template using the full conversation history.
            # Use tokenize=False then encode() to always get a plain list of ints.
            prompt_text = self._tokenizer.apply_chat_template(
                norm_msgs,
                tools=tools,
                tokenize=False,
                add_generation_prompt=True,
            )
            prompt_ids = self._tokenizer.encode(prompt_text, add_special_tokens=False)

            # Build Tinker ModelInput
            chunk = tinker.EncodedTextChunk(tokens=list(prompt_ids), type="encoded_text")
            model_input = tinker.ModelInput(chunks=[chunk])

            # Build SamplingParams
            sp_kwargs: dict[str, Any] = dict(
                temperature=temperature,
                max_tokens=max_tokens,
                top_k=50,
                top_p=0.95,
            )
            if stop is not None:
                sp_kwargs["stop"] = stop
            sampling_params = tinker.SamplingParams(**sp_kwargs)

            # Call Tinker
            response = await self._sampling_client.sample_async(
                prompt=model_input,
                num_samples=1,
                sampling_params=sampling_params,
                include_prompt_logprobs=False,
                topk_prompt_logprobs=0,
            )

            # Decode response tokens → text
            seq = response.sequences[0]
            response_text = self._tokenizer.decode(seq.tokens, skip_special_tokens=True)
            normalized_text, parsed_tool_calls = _extract_tool_calls_from_text(response_text)
            logprobs_list = seq.logprobs or []
            if parsed_tool_calls:
                logger.info(
                    "[OpenClaw] parsed tool_calls after extract: %s",
                    json.dumps(parsed_tool_calls, ensure_ascii=False)[:800],
                )
            logger.info(
                "[OpenClaw] Tinker tokens=%d stop=%s decoded=%r",
                len(seq.tokens), seq.stop_reason, response_text[:200],
            )

            # Build OpenAI-compatible response
            lp_content = [
                {"token": "", "logprob": float(lp), "top_logprobs": []}
                for lp in logprobs_list
            ]
            assistant_message: dict[str, Any] = {"role": "assistant", "content": normalized_text}
            if parsed_tool_calls:
                assistant_message["tool_calls"] = parsed_tool_calls
            return {
                "id": f"chatcmpl-tinker-{int(time.time())}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": body.get("model", self._served_model),
                "choices": [{
                    "index": 0,
                    "message": assistant_message,
                    "finish_reason": "tool_calls" if parsed_tool_calls else (seq.stop_reason or "stop"),
                    "logprobs": {"content": lp_content},
                }],
                "usage": {
                    "prompt_tokens": len(prompt_ids),
                    "completion_tokens": len(seq.tokens),
                    "total_tokens": len(prompt_ids) + len(seq.tokens),
                },
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error("[OpenClaw] Tinker sample_async failed: %s", e, exc_info=True)
            raise HTTPException(status_code=502, detail=f"Tinker inference error: {e}") from e

    # ------------------------------------------------------------------ #
    # LLM forwarding (skills_only mode)                                   #
    # ------------------------------------------------------------------ #

    async def _forward_to_llm(self, body: dict[str, Any]) -> dict[str, Any]:
        """Forward to a real OpenAI-compatible API (skills_only mode)."""
        import httpx

        api_base = self.config.llm_api_base.rstrip("/")
        if not api_base:
            raise HTTPException(
                status_code=503,
                detail="llm_api_base is not configured. Run 'metaclaw setup' first.",
            )

        # Strip Tinker-specific fields not supported by standard OpenAI APIs
        send_body = {
            k: v for k, v in body.items()
            if k not in {"logprobs", "top_logprobs", "stream_options"}
        }
        send_body["model"] = self.config.llm_model_id or body.get("model", "")
        send_body["stream"] = False

        headers: dict[str, str] = {}
        if self.config.llm_api_key:
            headers["Authorization"] = f"Bearer {self.config.llm_api_key}"

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(
                    f"{api_base}/chat/completions",
                    json=send_body,
                    headers=headers,
                )
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPStatusError as e:
            logger.error("[OpenClaw] upstream LLM error: %s %s", e.response.status_code, e.response.text[:200])
            raise HTTPException(status_code=502, detail=f"Upstream LLM error: {e}") from e
        except Exception as e:
            logger.error("[OpenClaw] LLM forward failed: %s", e, exc_info=True)
            raise HTTPException(status_code=502, detail=f"LLM forward error: {e}") from e

    # ------------------------------------------------------------------ #
    # Skill evolution (skills_only mode)                                  #
    # ------------------------------------------------------------------ #

    async def _evolve_skills_for_session(self, turns: list[dict]):
        """Analyze session turns and generate new skills (skills_only mode)."""
        from types import SimpleNamespace

        samples = [
            SimpleNamespace(
                prompt_text=t["prompt_text"],
                response_text=t["response_text"],
                reward=0.0,  # no RL reward; evolver analyzes patterns
            )
            for t in turns
        ]
        existing = self.skill_manager.skills if self.skill_manager else {}
        try:
            new_skills = await self.skill_evolver.evolve(samples, existing)
        except Exception as e:
            logger.error("[SkillEvolver] evolve failed: %s", e, exc_info=True)
            return
        if new_skills and self.skill_manager:
            added = 0
            for skill in new_skills:
                category = skill.get("category", "general")
                added += self.skill_manager.add_skills([skill], category=category)
            logger.info("[SkillEvolver] session analysis added %d new skills", added)

    # ------------------------------------------------------------------ #
    # Skill injection                                                      #
    # ------------------------------------------------------------------ #

    def _truncate_messages(
        self,
        messages: list[dict],
        tools,
        max_prompt_tokens: int,
    ) -> list[dict]:
        """
        Drop oldest non-system messages until the tokenized prompt fits within
        max_prompt_tokens.  The system message (if any) is always kept.
        At least one user message is always kept even if it alone exceeds the limit.
        """
        if self._tokenizer is None:
            return messages

        def _prompt_len(msgs):
            try:
                norm_msgs = _normalize_messages_for_template(msgs)
                text = self._tokenizer.apply_chat_template(
                    norm_msgs, tools=tools, tokenize=False, add_generation_prompt=True,
                )
                return len(self._tokenizer(text, add_special_tokens=False)["input_ids"])
            except Exception:
                return 0

        if _prompt_len(messages) <= max_prompt_tokens:
            return messages

        # Split into system and non-system messages
        sys_msgs = [m for m in messages if m.get("role") == "system"]
        non_sys = [m for m in messages if m.get("role") != "system"]

        # Greedily keep most-recent messages
        kept = []
        for msg in reversed(non_sys):
            candidate = sys_msgs + list(reversed(kept + [msg]))
            if _prompt_len(candidate) <= max_prompt_tokens:
                kept.append(msg)
            elif not kept:
                kept.append(msg)  # keep at least one user message
                break
            else:
                break

        result = sys_msgs + list(reversed(kept))
        dropped = len(messages) - len(result)
        if dropped > 0:
            logger.warning(
                "[OpenClaw] context truncated: dropped %d oldest messages "
                "(%d → %d tokens, limit=%d)",
                dropped,
                _prompt_len(messages),
                _prompt_len(result),
                max_prompt_tokens,
            )
        return result

    def _inject_skills(self, messages: list[dict]) -> list[dict]:
        """Prepend skill guidance to the system message."""
        if not self.skill_manager:
            return messages

        user_msgs = [m for m in messages if m.get("role") == "user"]
        task_desc = _flatten_message_content(user_msgs[-1].get("content", "")) if user_msgs else ""
        if not task_desc:
            return messages

        skills = self.skill_manager.retrieve(task_desc, top_k=self.config.skill_top_k)
        if not skills:
            return messages

        skill_names = [
            s.get("name", s.get("id", "unknown_skill"))
            for s in skills
            if isinstance(s, dict)
        ]
        logger.info(
            "[SkillManager] injecting %d skills: %s",
            len(skill_names),
            ", ".join(skill_names)[:400],
        )

        skill_text = self.skill_manager.format_for_conversation(skills)
        messages = list(messages)

        sys_indices = [i for i, m in enumerate(messages) if m.get("role") == "system"]
        if sys_indices:
            idx = sys_indices[0]
            existing = _flatten_message_content(messages[idx].get("content", ""))
            messages[idx] = {**messages[idx], "content": existing + "\n\n" + skill_text}
        else:
            messages.insert(0, {"role": "system", "content": skill_text})

        return messages

    # ------------------------------------------------------------------ #
    # Sample submission                                                    #
    # ------------------------------------------------------------------ #

    def _maybe_submit_ready_samples(
        self, session_id: str, force_no_prm: bool = False
    ):
        """Submit turns whose PRM and teacher queries are done.

        force_no_prm: also submit turns that have no PRM task yet (used at
        session end for the last turn which will never get a next_state).
        When force is active, pending teacher tasks are also skipped.
        """
        prm_tasks = self._prm_tasks.get(session_id, {})
        teacher_tasks = self._teacher_tasks.get(session_id, {})
        pending = self._pending_turn_data.get(session_id, {})
        for turn_num in sorted(list(pending.keys())):
            # --- PRM readiness ---
            prm_task = prm_tasks.get(turn_num)
            if not self.config.use_prm or not self.prm_scorer:
                pass  # no PRM → submit immediately
            elif prm_task is not None and not prm_task.done():
                continue  # PRM still running
            elif prm_task is None and not force_no_prm:
                continue  # waiting for next_state to fire PRM

            # --- Teacher readiness (OPD) ---
            teacher_task = teacher_tasks.get(turn_num)
            if (self.config.use_opd and teacher_task is not None
                    and not teacher_task.done() and not force_no_prm):
                continue  # teacher logprobs still running

            turn_data = pending.pop(turn_num)
            prm_result = None
            if prm_task is not None and prm_task.done():
                try:
                    prm_result = prm_task.result()
                except Exception:
                    pass
                prm_tasks.pop(turn_num, None)

            teacher_logprobs = None
            if teacher_task is not None and teacher_task.done():
                try:
                    teacher_logprobs = teacher_task.result()
                except Exception:
                    pass
                teacher_tasks.pop(turn_num, None)

            self._safe_create_task(
                self._submit_turn_sample(turn_data, session_id, prm_result, teacher_logprobs)
            )

    async def _submit_turn_sample(
        self,
        turn_data: dict[str, Any],
        session_id: str,
        prm_result: Optional[dict],
        teacher_logprobs: Optional[list[float]] = None,
    ):
        prompt_ids = turn_data["prompt_ids"]
        response_ids = turn_data["response_ids"]

        has_next_state = turn_data.get("has_next_state", False)
        score = prm_result["score"] if prm_result else 0.0

        exclude = not has_next_state or score == 0.0
        # Guarantee at least one sample per session contributes to training.
        if exclude and has_next_state and self._session_effective.get(session_id, 0) == 0:
            exclude = False
            logger.info(
                "[OpenClaw] promoting session=%s turn with score=0 → loss_mask=1 (at-least-one guarantee)",
                session_id,
            )

        loss_mask = [0] * len(response_ids) if exclude else [1] * len(response_ids)
        sample = ConversationSample(
            session_id=session_id,
            turn_num=self._turn_counts.get(session_id, 0),
            prompt_tokens=prompt_ids,
            response_tokens=response_ids,
            response_logprobs=turn_data["response_logprobs"],
            loss_mask=loss_mask,
            reward=score,
            prompt_text=turn_data.get("prompt_text", ""),
            response_text=turn_data.get("response_text", ""),
            teacher_logprobs=teacher_logprobs,
            # Tag with current skill generation so the trainer can discard
            # pre-evolution samples (MAML support/query set separation).
            skill_generation=self.skill_manager.generation if self.skill_manager else 0,
        )

        if not exclude:
            self._session_effective[session_id] = (
                self._session_effective.get(session_id, 0) + 1
            )

        index = next(self._index_counter)
        group_index = next(self._group_counter)

        if prm_result:
            self._append_prm_record(
                session_id, sample.turn_num, score, prm_result.get("votes", [])
            )

        logger.info(
            "[OpenClaw] submitted sample session=%s index=%d score=%.1f exclude=%s "
            "prompt_len=%d response_len=%d",
            session_id, index, score, exclude, len(prompt_ids), len(response_ids),
        )
        await asyncio.to_thread(self.output_queue.put, (group_index, [sample]))

    # ------------------------------------------------------------------ #
    # Streaming                                                            #
    # ------------------------------------------------------------------ #

    async def _stream_response(self, result: dict[str, Any]):
        payload = result["response"]
        choice = payload.get("choices", [{}])[0]
        message = choice.get("message", {})
        delta = {"role": "assistant", "content": message.get("content", "") or ""}
        if message.get("tool_calls"):
            delta["tool_calls"] = message["tool_calls"]
        chunk_base = {
            "id": payload.get("id", ""),
            "object": "chat.completion.chunk",
            "created": payload.get("created", int(time.time())),
            "model": payload.get("model", ""),
            "session_id": payload.get("session_id", ""),
        }
        first = {**chunk_base, "choices": [{"index": 0, "delta": delta, "finish_reason": None}]}
        final = {
            **chunk_base,
            "choices": [{"index": 0, "delta": {}, "finish_reason": choice.get("finish_reason", "stop")}],
        }
        yield f"data: {json.dumps(first, ensure_ascii=False)}\n\n"
        yield f"data: {json.dumps(final, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    # ------------------------------------------------------------------ #
    # Lifecycle                                                            #
    # ------------------------------------------------------------------ #

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        cfg = uvicorn.Config(
            self.app,
            host=self.config.proxy_host,
            port=self.config.proxy_port,
            log_level="info",
        )
        self._server = uvicorn.Server(cfg)
        self._thread = threading.Thread(target=self._server.run, daemon=True)
        self._thread.start()
        threading.Thread(target=self._print_ready_banner, daemon=True).start()

    def _print_ready_banner(self):
        time.sleep(3)
        backend = "Tinker cloud RL" if self.config.mode in ("rl", "madmax") else f"LLM ({self.config.llm_model_id or 'upstream'})"
        banner = (
            f"\n{'=' * 70}\n"
            f"  MetaClaw proxy ready  [mode={self.config.mode}]\n"
            f"  proxy {self.config.proxy_host}:{self.config.proxy_port} → {backend}\n"
            f"  OpenClaw has been configured to use this proxy automatically.\n"
            f"{'=' * 70}\n"
        )
        logger.info(f"{_GREEN}{banner}{_RESET}")

    def stop(self):
        if self._server is not None:
            self._server.should_exit = True
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)

    # ------------------------------------------------------------------ #
    # Tinker-specific interface                                            #
    # ------------------------------------------------------------------ #

    def update_sampling_client(self, new_client):
        """Hot-swap the Tinker sampling client after a weight update."""
        self._sampling_client = new_client
        logger.info("[OpenClaw] sampling client updated")

    # ------------------------------------------------------------------ #
    # Utility                                                              #
    # ------------------------------------------------------------------ #

    def _safe_create_task(self, coro):
        task = asyncio.create_task(coro)
        task.add_done_callback(self._task_done_cb)

    @staticmethod
    def _task_done_cb(task: asyncio.Task):
        if task.cancelled():
            return
        exc = task.exception()
        if exc is not None:
            logger.error("[OpenClaw] background task failed: %s", exc, exc_info=exc)
