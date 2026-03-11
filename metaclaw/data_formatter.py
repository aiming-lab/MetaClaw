"""
Data formatter: converts ConversationSample → tinker.Datum.

The Datum structure follows the tinker-cookbook RL convention
(see tinker-cookbook/tinker_cookbook/rl/data_processing.py):

  model_input  – the input tokens (all but the last token of the full sequence)
  loss_fn_inputs:
    target_tokens – full sequence left-shifted by 1  (shape T)
    logprobs      – prompt positions = 0.0, response positions = sampled logprob (T)
    advantages    – prompt = 0.0, response = advantage * loss_mask[i]  (T)
    mask          – prompt = 0.0, response = float(loss_mask[i])  (T)

where T = len(prompt_tokens) + len(response_tokens) - 1.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Optional

import torch

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------ #
# ConversationSample dataclass                                         #
# ------------------------------------------------------------------ #

@dataclass
class ConversationSample:
    """One training example collected from the API proxy."""

    session_id: str
    turn_num: int
    prompt_tokens: list[int]
    response_tokens: list[int]
    response_logprobs: list[float]    # per-token log-probs from sampling
    loss_mask: list[int]              # 0 = exclude from loss, 1 = include
    reward: float                     # PRM score  {-1.0, 0.0, 1.0}
    prompt_text: str = ""             # for logging / skill evolution
    response_text: str = ""           # for logging / skill evolution
    teacher_logprobs: Optional[list[float]] = None  # OPD only


# ------------------------------------------------------------------ #
# sample_to_datum                                                      #
# ------------------------------------------------------------------ #

def sample_to_datum(
    sample: ConversationSample,
    advantage: float,
    kl_penalty_coef: float = 0.0,
):
    """
    Convert one ConversationSample + scalar advantage into a ``tinker.Datum``.

    When ``sample.teacher_logprobs`` is present and *kl_penalty_coef* > 0,
    a reverse-KL penalty (``-coef * (log p_student - log p_teacher)``) is
    added to the per-token advantages, matching the tinker-cookbook OPD
    convention (see ``tinker_cookbook/distillation/train_on_policy.py``).

    Returns
    -------
    tinker.Datum
    """
    try:
        import tinker
        from tinker import TensorData
    except ImportError as e:
        raise ImportError(
            "tinker SDK is required for data formatting. "
            "Install via: pip install tinker  (or the appropriate private package)"
        ) from e

    prompt_len = len(sample.prompt_tokens)
    all_tokens = sample.prompt_tokens + sample.response_tokens
    # T: number of (input, target) pairs = len(all_tokens) - 1
    T = len(all_tokens) - 1

    if T <= 0:
        raise ValueError(
            f"[data_formatter] Empty sequence for session={sample.session_id} "
            f"turn={sample.turn_num}: prompt_len={prompt_len} "
            f"response_len={len(sample.response_tokens)}"
        )

    target_tokens: list[int] = all_tokens[1:]           # left-shift

    # logprobs: 0 for prompt positions, sampled logprob for response
    logprobs: list[float] = (
        [0.0] * (prompt_len - 1) + list(sample.response_logprobs)
    )

    # advantages: 0 for prompt, advantage * loss_mask for response
    resp_advantages = [advantage * float(m) for m in sample.loss_mask]

    # OPD: add reverse-KL penalty to response advantages.
    # KL[student||teacher] = log p_student - log p_teacher
    # We penalise divergence by subtracting coef * KL from the advantages.
    if sample.teacher_logprobs is not None and kl_penalty_coef > 0:
        for i in range(min(len(resp_advantages), len(sample.teacher_logprobs))):
            student_lp = sample.response_logprobs[i] if i < len(sample.response_logprobs) else 0.0
            teacher_lp = sample.teacher_logprobs[i]
            kl_i = student_lp - teacher_lp
            resp_advantages[i] += -kl_penalty_coef * kl_i * float(sample.loss_mask[i])

    advantages: list[float] = [0.0] * (prompt_len - 1) + resp_advantages

    # mask: 0 for prompt, loss_mask value for response
    mask: list[float] = (
        [0.0] * (prompt_len - 1) + [float(m) for m in sample.loss_mask]
    )

    # Truncate / pad logprobs and advantages to exactly T
    def _fit(lst: list[float], length: int) -> list[float]:
        if len(lst) > length:
            return lst[:length]
        if len(lst) < length:
            return lst + [0.0] * (length - len(lst))
        return lst

    logprobs = _fit(logprobs, T)
    advantages = _fit(advantages, T)
    mask = _fit(mask, T)

    # Service-side array-record conversion is strict about shape and numeric values.
    # Validate/clean here to avoid opaque 400 errors from the training endpoint.
    def _sanitize_floats(lst: list[float], name: str) -> list[float]:
        bad_idx = [i for i, v in enumerate(lst) if not math.isfinite(v)]
        if bad_idx:
            logger.warning(
                "[data_formatter] non-finite %s values for session=%s turn=%d count=%d; replacing with 0.0",
                name, sample.session_id, sample.turn_num, len(bad_idx),
            )
            for i in bad_idx:
                lst[i] = 0.0
        return lst

    logprobs = _sanitize_floats(logprobs, "logprobs")
    advantages = _sanitize_floats(advantages, "advantages")
    mask = _sanitize_floats(mask, "mask")

    if not (
        len(target_tokens) == T
        and len(logprobs) == T
        and len(advantages) == T
        and len(mask) == T
    ):
        raise ValueError(
            "[data_formatter] length mismatch "
            f"session={sample.session_id} turn={sample.turn_num} "
            f"T={T} target={len(target_tokens)} logprobs={len(logprobs)} "
            f"advantages={len(advantages)} mask={len(mask)}"
        )

    # Build model input from all tokens except the last
    model_input = tinker.ModelInput.from_ints(all_tokens[:-1])

    # Note: "mask" is NOT included in loss_fn_inputs.  The Tinker server
    # rejects unknown keys (only target_tokens, logprobs, advantages, weights,
    # clip_*_threshold are accepted).  The mask information is already encoded
    # in the advantages (0.0 for prompt / masked positions).  The cookbook
    # likewise strips mask via remove_mask() before calling forward_backward.
    return tinker.Datum(
        model_input=model_input,
        loss_fn_inputs={
            "target_tokens": TensorData.from_torch(
                torch.tensor(target_tokens, dtype=torch.long)
            ),
            "logprobs": TensorData.from_torch(
                torch.tensor(logprobs, dtype=torch.float32)
            ),
            "advantages": TensorData.from_torch(
                torch.tensor(advantages, dtype=torch.float32)
            ),
        },
    )


# ------------------------------------------------------------------ #
# batch_to_datums                                                      #
# ------------------------------------------------------------------ #

def batch_to_datums(
    batch: list[ConversationSample],
    advantages: list[float],
    kl_penalty_coef: float = 0.0,
) -> list:
    """
    Convert a batch of samples + per-sample advantages to a list of Datums.

    Samples that fail conversion are skipped with a warning.
    """
    datums = []
    for sample, adv in zip(batch, advantages):
        try:
            datums.append(sample_to_datum(sample, adv, kl_penalty_coef=kl_penalty_coef))
        except Exception as e:
            logger.warning(
                "[data_formatter] skipping sample session=%s turn=%d: %s",
                sample.session_id, sample.turn_num, e,
            )
    return datums


# ------------------------------------------------------------------ #
# Advantage computation (GRPO-style group normalization)              #
# ------------------------------------------------------------------ #

def compute_advantages(batch: list[ConversationSample]) -> list[float]:
    """
    Centre-and-scale rewards within the batch (GRPO style: (r - mean) / (std + eps)).

    Returns a list of float advantages, one per sample.
    """
    if not batch:
        return []
    rewards = [s.reward for s in batch]
    mean_r = sum(rewards) / len(rewards)
    variance = sum((r - mean_r) ** 2 for r in rewards) / len(rewards)
    std_r = variance ** 0.5
    eps = 1e-8
    return [(r - mean_r) / (std_r + eps) for r in rewards]
