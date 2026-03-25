"""FastAPI sidecar wrapping the MetaClaw Memory system."""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel, Field

from metaclaw.memory.consolidator import MemoryConsolidator
from metaclaw.memory.manager import MemoryManager
from metaclaw.memory.models import MemoryStatus, MemoryType, MemoryUnit, utc_now_iso
from metaclaw.memory.upgrade_worker import MemoryUpgradeWorker

from .config import SidecarConfig

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------


class RetrieveRequest(BaseModel):
    task_description: str
    scope_id: str | None = None


class RetrieveResponse(BaseModel):
    rendered_prompt: str
    unit_count: int


class TurnInput(BaseModel):
    prompt_text: str
    response_text: str


class IngestRequest(BaseModel):
    session_id: str
    turns: list[TurnInput]
    scope_id: str | None = None


class IngestResponse(BaseModel):
    added: int


class SearchRequest(BaseModel):
    query: str
    scope_id: str | None = None
    limit: int = 10


class SearchResponse(BaseModel):
    results: list[dict[str, Any]]


class StoreRequest(BaseModel):
    content: str
    memory_type: str
    scope_id: str | None = None
    tags: list[str] = Field(default_factory=list)
    importance: float = 0.5


class StoreResponse(BaseModel):
    memory_id: str


class ForgetRequest(BaseModel):
    memory_id: str


class ForgetResponse(BaseModel):
    ok: bool = True


class ConsolidateRequest(BaseModel):
    scope_id: str | None = None


class HealthResponse(BaseModel):
    status: str
    memories: int
    scope: str


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------


def create_app(config: SidecarConfig) -> FastAPI:
    """Build and return the configured FastAPI application."""

    mcfg = config.to_metaclaw_config()

    # Shared state attached to app.
    state: dict[str, Any] = {
        "manager": None,
        "upgrade_worker": None,
        "upgrade_task": None,
        "config": config,
        "mcfg": mcfg,
    }

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Ensure memory directory exists
        Path(config.memory_dir).expanduser().mkdir(parents=True, exist_ok=True)
        # Startup
        mgr = MemoryManager.from_config(mcfg)
        state["manager"] = mgr
        logger.info(
            "Memory sidecar started scope=%s dir=%s",
            config.memory_scope,
            config.memory_dir,
        )

        if config.auto_upgrade_enabled:
            worker = MemoryUpgradeWorker(mcfg)
            state["upgrade_worker"] = worker
            state["upgrade_task"] = asyncio.create_task(worker.run())
            logger.info("Upgrade worker started interval=%ds", config.auto_upgrade_interval)

        yield

        # Shutdown
        if state["upgrade_worker"] is not None:
            state["upgrade_worker"].stop()
            if state["upgrade_task"] is not None:
                state["upgrade_task"].cancel()
                try:
                    await state["upgrade_task"]
                except (asyncio.CancelledError, Exception):
                    pass
        if state["manager"] is not None:
            state["manager"].close()
        logger.info("Memory sidecar stopped")

    app = FastAPI(
        title="MetaClaw Memory Sidecar",
        version="0.1.0",
        lifespan=lifespan,
    )

    # -- helpers --

    def _mgr() -> MemoryManager:
        return state["manager"]

    def _scope(override: str | None) -> str:
        return override or config.memory_scope

    # ---------------------------------------------------------------
    # Endpoints
    # ---------------------------------------------------------------

    @app.get("/health", response_model=HealthResponse)
    def health():
        mgr = _mgr()
        stats = mgr.get_scope_stats()
        return HealthResponse(
            status="ok",
            memories=stats.get("active", 0),
            scope=config.memory_scope,
        )

    @app.post("/retrieve", response_model=RetrieveResponse)
    def retrieve(req: RetrieveRequest):
        mgr = _mgr()
        scope = _scope(req.scope_id)
        units = mgr.retrieve_for_prompt(req.task_description, scope_id=scope)
        rendered = mgr.render_for_prompt(units)
        return RetrieveResponse(rendered_prompt=rendered, unit_count=len(units))

    @app.post("/ingest", response_model=IngestResponse)
    def ingest(req: IngestRequest):
        mgr = _mgr()
        scope = _scope(req.scope_id)
        turns = [{"prompt_text": t.prompt_text, "response_text": t.response_text} for t in req.turns]
        added = mgr.ingest_session_turns(req.session_id, turns, scope_id=scope)
        return IngestResponse(added=added)

    @app.post("/search", response_model=SearchResponse)
    def search(req: SearchRequest):
        mgr = _mgr()
        scope = _scope(req.scope_id)
        results = mgr.search_memories(req.query, scope_id=scope, limit=req.limit)
        return SearchResponse(results=results)

    @app.post("/store", response_model=StoreResponse)
    def store_memory(req: StoreRequest):
        mgr = _mgr()
        scope = _scope(req.scope_id)
        try:
            mem_type = MemoryType(req.memory_type)
        except ValueError:
            mem_type = MemoryType.SEMANTIC

        now = utc_now_iso()
        memory_id = str(uuid.uuid4())
        unit = MemoryUnit(
            memory_id=memory_id,
            scope_id=scope,
            memory_type=mem_type,
            content=req.content,
            tags=req.tags,
            importance=req.importance,
            created_at=now,
            updated_at=now,
        )
        mgr.store.add_memories([unit])
        return StoreResponse(memory_id=memory_id)

    @app.post("/forget", response_model=ForgetResponse)
    def forget(req: ForgetRequest):
        mgr = _mgr()
        mgr.store.bulk_archive([req.memory_id])
        return ForgetResponse(ok=True)

    @app.get("/stats")
    def stats():
        mgr = _mgr()
        return mgr.get_scope_stats()

    @app.post("/consolidate")
    def consolidate(req: ConsolidateRequest):
        mgr = _mgr()
        scope = _scope(req.scope_id)
        consolidator = MemoryConsolidator(store=mgr.store)
        result = consolidator.consolidate(scope)
        return result

    @app.get("/upgrade/status")
    def upgrade_status():
        state_path = Path(config.memory_dir).expanduser() / "upgrade_worker_state.json"
        if not state_path.exists():
            return {"state": "not_configured", "detail": "no upgrade state file"}
        try:
            return json.loads(state_path.read_text(encoding="utf-8"))
        except Exception as exc:
            return {"state": "error", "detail": str(exc)}

    @app.post("/upgrade/trigger")
    async def upgrade_trigger():
        worker = state.get("upgrade_worker")
        if worker is None:
            # Create a one-shot worker if none is running.
            worker = MemoryUpgradeWorker(mcfg)
            ran = await worker.run_once()
            return {"triggered": True, "ran": ran}
        ran = await worker.run_once()
        return {"triggered": True, "ran": ran}

    return app
