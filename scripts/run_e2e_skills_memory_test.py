"""
End-to-end test: skills_only mode with memory system enabled.

Exercises:
  1. MetaClaw proxy startup (skills_only)
  2. Skills injection into prompts
  3. Multi-turn conversation through proxy
  4. Memory extraction from sessions
  5. Memory retrieval for subsequent sessions
  6. Memory consolidation
  7. Skill evolution (auto-summarize)

Usage:
    python scripts/run_e2e_skills_memory_test.py
"""

import asyncio
import json
import logging
import os
import sys
import time
from pathlib import Path

import httpx

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("e2e_test")

# Azure OpenAI config
API_BASE = "https://huaxi-mlg4x1rk-eastus2.services.ai.azure.com/openai/v1"
API_KEY = os.environ.get("AZURE_API_KEY", "")
MODEL = "gpt-5.1"
PROXY_PORT = 30000
PROXY_URL = f"http://127.0.0.1:{PROXY_PORT}/v1/chat/completions"

# Ensure all LLM calls route to Azure, not default openai.com
os.environ["OPENAI_API_KEY"] = API_KEY
os.environ["OPENAI_BASE_URL"] = API_BASE
os.environ["SKILL_EVOLVER_MODEL"] = MODEL


async def wait_for_proxy(timeout_s=60):
    """Wait until the proxy is ready."""
    url = f"http://127.0.0.1:{PROXY_PORT}/docs"
    start = time.monotonic()
    while True:
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(url)
                if resp.status_code < 500:
                    logger.info("Proxy ready (status=%d)", resp.status_code)
                    return
        except Exception:
            pass
        if time.monotonic() - start > timeout_s:
            raise TimeoutError("Proxy did not start in time")
        await asyncio.sleep(1.0)


async def send_chat(messages, session_id="test_session_001", session_done=False):
    """Send a chat request through the MetaClaw proxy."""
    body = {
        "model": MODEL,
        "messages": messages,
        "session_id": session_id,
        "turn_type": "main",
        "session_done": session_done,
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            PROXY_URL,
            json=body,
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json",
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return data


async def run_test():
    from metaclaw.config_store import ConfigStore
    from metaclaw.launcher import MetaClawLauncher

    logger.info("=" * 60)
    logger.info("  MetaClaw E2E Test: skills_only + memory")
    logger.info("=" * 60)

    # ------------------------------------------------------------------ #
    # Step 0: Start the proxy                                             #
    # ------------------------------------------------------------------ #
    cs = ConfigStore()
    launcher = MetaClawLauncher(cs)
    launcher_task = asyncio.create_task(launcher.start())

    await wait_for_proxy()
    await asyncio.sleep(2)  # extra settle time

    results = {"tests": [], "passed": 0, "failed": 0}

    def record(name, passed, detail=""):
        results["tests"].append({"name": name, "passed": passed, "detail": detail})
        if passed:
            results["passed"] += 1
            logger.info("  PASS: %s %s", name, f"— {detail}" if detail else "")
        else:
            results["failed"] += 1
            logger.error("  FAIL: %s %s", name, f"— {detail}" if detail else "")

    try:
        # ------------------------------------------------------------------ #
        # Test 1: Basic proxy forwarding                                      #
        # ------------------------------------------------------------------ #
        logger.info("\n--- Test 1: Basic proxy forwarding ---")
        try:
            data = await send_chat([
                {"role": "user", "content": "What is 2+2? Reply with just the number."}
            ])
            reply = data["choices"][0]["message"]["content"]
            record("Basic proxy forwarding", bool(reply), f"reply={reply[:100]}")
        except Exception as e:
            record("Basic proxy forwarding", False, str(e))

        # ------------------------------------------------------------------ #
        # Test 2: Multi-turn conversation (Session 1)                         #
        # ------------------------------------------------------------------ #
        logger.info("\n--- Test 2: Multi-turn session 1 (build context) ---")
        session1_messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "My name is Alice and I'm a software engineer at TechCorp. I mainly work with Python and FastAPI."},
        ]
        try:
            data = await send_chat(session1_messages, session_id="session_mem_001")
            reply1 = data["choices"][0]["message"]["content"]
            record("Session 1 turn 1", bool(reply1), f"reply={reply1[:120]}")

            # Turn 2
            session1_messages.append({"role": "assistant", "content": reply1})
            session1_messages.append(
                {"role": "user", "content": "I'm currently building a REST API for our inventory management system. The database is PostgreSQL."}
            )
            data = await send_chat(session1_messages, session_id="session_mem_001")
            reply2 = data["choices"][0]["message"]["content"]
            record("Session 1 turn 2", bool(reply2), f"reply={reply2[:120]}")

            # Turn 3 — end session
            session1_messages.append({"role": "assistant", "content": reply2})
            session1_messages.append(
                {"role": "user", "content": "Thanks! I'll also need to add authentication with JWT tokens later. That's all for now."}
            )
            data = await send_chat(
                session1_messages,
                session_id="session_mem_001",
                session_done=True,
            )
            reply3 = data["choices"][0]["message"]["content"]
            record("Session 1 turn 3 (session_done)", bool(reply3), f"reply={reply3[:120]}")
        except Exception as e:
            record("Session 1 multi-turn", False, str(e))

        # Give memory extraction time to run (async task needs time)
        logger.info("  Waiting 20s for async memory extraction...")
        await asyncio.sleep(20)

        # ------------------------------------------------------------------ #
        # Test 3: Memory retrieval in Session 2                               #
        # ------------------------------------------------------------------ #
        logger.info("\n--- Test 3: Session 2 (test memory retrieval) ---")
        try:
            data = await send_chat(
                [
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": "What database and framework am I using for my current project?"},
                ],
                session_id="session_mem_002",
            )
            reply = data["choices"][0]["message"]["content"]
            # Check if the model recalls project context
            has_context = any(
                kw in reply.lower()
                for kw in ["postgres", "fastapi", "inventory", "alice", "techcorp"]
            )
            record(
                "Memory retrieval in session 2",
                has_context,
                f"Context recalled={'yes' if has_context else 'no'}, reply={reply[:200]}",
            )
        except Exception as e:
            record("Memory retrieval in session 2", False, str(e))

        # ------------------------------------------------------------------ #
        # Test 4: Another multi-turn session with different topic             #
        # ------------------------------------------------------------------ #
        logger.info("\n--- Test 4: Session 3 (different topic) ---")
        try:
            data = await send_chat(
                [
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": "Help me write a Python function that validates email addresses using regex."},
                ],
                session_id="session_mem_003",
                session_done=True,
            )
            reply = data["choices"][0]["message"]["content"]
            has_code = "def " in reply or "import re" in reply or "regex" in reply.lower()
            record("Session 3 code generation", has_code, f"Contains code={has_code}")
        except Exception as e:
            record("Session 3 code generation", False, str(e))

        # ------------------------------------------------------------------ #
        # Test 5: Health / status endpoint                                    #
        # ------------------------------------------------------------------ #
        logger.info("\n--- Test 5: Health check ---")
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"http://127.0.0.1:{PROXY_PORT}/v1/memory/health")
                record("Memory health endpoint", resp.status_code == 200, f"status={resp.status_code}, body={resp.text[:200]}")
        except Exception as e:
            record("Health endpoint", False, str(e))

        # ------------------------------------------------------------------ #
        # Test 6: Memory store inspection                                     #
        # ------------------------------------------------------------------ #
        logger.info("\n--- Test 6: Memory store inspection ---")
        try:
            from metaclaw.memory.store import MemoryStore
            store_path = Path.home() / ".metaclaw" / "memory" / "memory.db"
            if store_path.exists():
                store = MemoryStore(str(store_path))
                # After fix: memories are stored under base scope "default"
                stats = store.get_stats("default")
                total_active = stats.get("active", 0)
                record(
                    "Memory store has entries",
                    total_active > 0,
                    f"active_memories={total_active}, scope=default",
                )
                # Search under the base scope
                hits = store.search_keyword("default", "Python", limit=5)
                if not hits:
                    hits = store.search_keyword("default", "FastAPI PostgreSQL", limit=5)
                if not hits:
                    hits = store.search_keyword("default", "email regex", limit=5)
                record(
                    "Memory keyword search",
                    len(hits) > 0,
                    f"hits={len(hits)}, scope=default, top={hits[0].unit.summary[:80] if hits else 'none'}",
                )
                store.close()
            else:
                record("Memory store has entries", False, "memory.db not found")
        except Exception as e:
            record("Memory store inspection", False, str(e))

        # ------------------------------------------------------------------ #
        # Test 7: Streaming response                                          #
        # ------------------------------------------------------------------ #
        logger.info("\n--- Test 7: Streaming response ---")
        try:
            body = {
                "model": MODEL,
                "messages": [{"role": "user", "content": "Count from 1 to 5."}],
                "stream": True,
                "session_id": "session_stream",
            }
            chunks = []
            async with httpx.AsyncClient(timeout=30.0) as client:
                async with client.stream(
                    "POST",
                    PROXY_URL,
                    json=body,
                    headers={
                        "Authorization": f"Bearer {API_KEY}",
                        "Content-Type": "application/json",
                    },
                ) as resp:
                    async for line in resp.aiter_lines():
                        if line.startswith("data: ") and line != "data: [DONE]":
                            chunks.append(line)
            record("Streaming response", len(chunks) > 1, f"chunks={len(chunks)}")
        except Exception as e:
            record("Streaming response", False, str(e))

    finally:
        # ------------------------------------------------------------------ #
        # Shutdown                                                            #
        # ------------------------------------------------------------------ #
        logger.info("\n--- Shutting down ---")
        launcher.stop()
        launcher_task.cancel()
        try:
            await launcher_task
        except asyncio.CancelledError:
            pass

    # ------------------------------------------------------------------ #
    # Summary                                                              #
    # ------------------------------------------------------------------ #
    logger.info("\n" + "=" * 60)
    logger.info("  E2E TEST RESULTS")
    logger.info("=" * 60)
    for t in results["tests"]:
        status = "PASS" if t["passed"] else "FAIL"
        logger.info("  [%s] %s", status, t["name"])
        if t["detail"]:
            logger.info("         %s", t["detail"][:200])
    logger.info("-" * 60)
    logger.info(
        "  Total: %d | Passed: %d | Failed: %d",
        len(results["tests"]),
        results["passed"],
        results["failed"],
    )
    logger.info("=" * 60)

    # Save results
    results_file = Path("records/e2e_test_results.json")
    results_file.parent.mkdir(parents=True, exist_ok=True)
    with open(results_file, "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    logger.info("Results saved to %s", results_file)

    return results


if __name__ == "__main__":
    results = asyncio.run(run_test())
    sys.exit(0 if results["failed"] == 0 else 1)
