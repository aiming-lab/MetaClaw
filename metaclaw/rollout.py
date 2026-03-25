"""
Rollout worker for MetaClaw.

Mirrors OpenClaw-RL/openclaw-rl/openclaw_rollout.py exactly.
Key differences vs. the original:
  - MetaClawAPIServer forwards to Tinker instead of SGLang
  - ConversationSample used instead of slime.utils.types.Sample
  - No eval_rollout (Tinker training loop handles evaluation separately)
"""

import asyncio
import atexit
import queue
import threading
import time

from .api_server import MetaClawAPIServer
from .config import MetaClawConfig
from .data_formatter import ConversationSample

_global_worker = None
_worker_lock = threading.Lock()


def get_global_worker(
    config: MetaClawConfig,
    sampling_client=None,
    skill_manager=None,
    memory_manager=None,
    prm_scorer=None,
    skill_evolver=None,
):
    global _global_worker
    with _worker_lock:
        if _global_worker is None or not _global_worker.worker_thread.is_alive():
            _global_worker = AsyncRolloutWorker(
                config, sampling_client, skill_manager, memory_manager, prm_scorer, skill_evolver
            )
            _global_worker.start()
        return _global_worker


def stop_global_worker():
    global _global_worker
    with _worker_lock:
        if _global_worker is not None:
            _global_worker.stop()
            _global_worker = None


class AsyncRolloutWorker:
    def __init__(
        self,
        config: MetaClawConfig,
        sampling_client=None,
        skill_manager=None,
        memory_manager=None,
        prm_scorer=None,
        skill_evolver=None,
        last_request_tracker=None,
    ):
        self.config = config
        self.running = True
        self.output_queue = queue.Queue(maxsize=100000)
        self.worker_thread = None
        self._submission_enabled = threading.Event()
        self._server = MetaClawAPIServer(
            config=config,
            output_queue=self.output_queue,
            submission_enabled=self._submission_enabled,
            sampling_client=sampling_client,
            skill_manager=skill_manager,
            prm_scorer=prm_scorer,
            skill_evolver=skill_evolver,
            last_request_tracker=last_request_tracker,
            memory_manager=memory_manager,
        )

    async def continuous_worker_loop(self):
        # Keepalive loop. Data production is request-driven in FastAPI handlers.
        while self.running:
            await asyncio.sleep(1.0)

    def worker_thread_func(self):
        asyncio.run(self.continuous_worker_loop())

    def start(self):
        self._server.start()
        if self.worker_thread is None or not self.worker_thread.is_alive():
            self.worker_thread = threading.Thread(
                target=self.worker_thread_func, daemon=True
            )
            self.worker_thread.start()

    def stop(self):
        self.running = False
        self._submission_enabled.clear()
        self._server.stop()
        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=5)

    def pause_submission(self):
        if self._submission_enabled.is_set():
            self._submission_enabled.clear()
            print("[RolloutWorker] submission paused")

    def resume_submission(self):
        if not self._submission_enabled.is_set():
            self._submission_enabled.set()
            print("[RolloutWorker] submission resumed")

    def update_sampling_client(self, client):
        """Hot-swap the Tinker sampling client after a weight update."""
        self._server.update_sampling_client(client)

    def get_completed_groups(self) -> list[tuple]:
        completed = []
        while True:
            try:
                completed.append(self.output_queue.get_nowait())
            except queue.Empty:
                break
        return completed

    def get_queue_size(self) -> int:
        return self.output_queue.qsize()

    def clear_output_queue(self) -> int:
        """Drain and discard all pending samples from the output queue.

        Called by the trainer after a skill generation bump to prevent
        pre-evolution samples from entering the RL training batch
        (MAML support/query set separation).

        Returns the number of discarded items.
        """
        discarded = 0
        while True:
            try:
                self.output_queue.get_nowait()
                discarded += 1
            except queue.Empty:
                break
        if discarded:
            print(
                f"[RolloutWorker] cleared {discarded} stale samples from output queue "
                f"(skill generation bumped)",
                flush=True,
            )
        return discarded


async def _drain_output_queue(
    batch_size: int, worker: AsyncRolloutWorker
) -> list[list[ConversationSample]]:
    data: list[list[ConversationSample]] = []
    completed_groups: dict[int, list[ConversationSample]] = {}
    start = time.time()
    last_progress = start

    while len(data) < batch_size:
        completed = worker.get_completed_groups()
        if completed:
            last_progress = time.time()
            for group_id, group in completed:
                completed_groups[group_id] = group

        for group_id in sorted(list(completed_groups.keys())):
            if len(data) >= batch_size:
                break
            group = completed_groups.pop(group_id)
            data.append(group)

        if time.time() - last_progress > 30:
            print(
                f"[RolloutWorker] waiting for API-produced samples: {len(data)}/{batch_size}, "
                f"queue={worker.get_queue_size()}",
                flush=True,
            )
            last_progress = time.time()

        if len(data) < batch_size:
            await asyncio.sleep(0.05)

    print(
        f"[RolloutWorker] drained {len(data)} groups in {time.time() - start:.2f}s",
        flush=True,
    )
    return data


atexit.register(stop_global_worker)
