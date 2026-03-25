"""
Memory Ablation — Direct Test (no proxy, minimal API calls).

Bypasses the full MetaClaw proxy to avoid rate limiting and skill injection overhead.
Tests the memory module directly: ingest → retrieve → inject → compare.

Total API calls: ~6 (3 LLM + 3 PRM judge).

Usage:
    python scripts/run_memory_ablation_direct.py
"""

import asyncio
import json
import logging
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

import httpx

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("ablation")

# ------------------------------------------------------------------ #
# Config                                                              #
# ------------------------------------------------------------------ #
API_BASE = os.environ.get("AZURE_OPENAI_BASE_URL", "https://huaxi-mlg4x1rk-eastus2.services.ai.azure.com/openai/v1")
API_KEY = os.environ["AZURE_OPENAI_API_KEY"]
MODEL = "gpt-5.4"
MEMORY_DIR = Path("/tmp/metaclaw_ablation_memory")
RESULTS_FILE = Path("records/ablation_results/direct_analysis.json")
DELAY = 12  # seconds between API calls to avoid rate limits


# ------------------------------------------------------------------ #
# LLM call helper                                                     #
# ------------------------------------------------------------------ #
async def call_llm(messages: list[dict], retries=4) -> str:
    """Call Azure OpenAI directly, with retry on rate limit."""
    for attempt in range(retries):
        try:
            async with httpx.AsyncClient(timeout=90.0) as client:
                resp = await client.post(
                    f"{API_BASE}/chat/completions",
                    json={
                        "model": MODEL,
                        "messages": messages,
                        "temperature": 0.7,
                        "max_completion_tokens": 1024,
                    },
                    headers={
                        "Authorization": f"Bearer {API_KEY}",
                        "Content-Type": "application/json",
                    },
                )
                resp.raise_for_status()
                return resp.json()["choices"][0]["message"]["content"]
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                wait = 20 * (attempt + 1)
                logger.warning("  Rate limited, waiting %ds (attempt %d)...", wait, attempt + 1)
                await asyncio.sleep(wait)
                continue
            raise
    raise RuntimeError("Rate limited after all retries")


async def prm_judge(question: str, response: str, context: str = "") -> float:
    """Quick LLM-as-judge score (0-1)."""
    prompt = f"""Rate this AI response 0-10. Consider relevance, context awareness, helpfulness.
Previous context: {context or 'None'}
User question: {question}
Response: {response[:600]}
Reply ONLY with JSON: {{"score": <0-10>}}"""
    try:
        text = await call_llm([{"role": "user", "content": prompt}])
        if "```" in text:
            text = text.split("```")[1].lstrip("json\n")
        return float(json.loads(text)["score"]) / 10.0
    except Exception as e:
        logger.warning("  PRM parse error: %s", e)
        return 0.5


def recall_score(response: str, keywords: list[str]) -> float:
    if not keywords:
        return 1.0
    lower = response.lower()
    return sum(1 for k in keywords if k.lower() in lower) / len(keywords)


# ------------------------------------------------------------------ #
# Test scenarios                                                      #
# ------------------------------------------------------------------ #
SCENARIOS = [
    {
        "name": "User Context Recall",
        "session1_user": "Hi, my name is Alice Chen. I'm a senior Python developer at TechCorp. I work with FastAPI and PostgreSQL. We use Docker for deployment.",
        "session2_user": "What web framework and database am I using for my work? And what is my name?",
        "recall_keywords": ["fastapi", "postgresql", "alice"],
        "context_for_judge": "User previously said: name is Alice Chen, Python dev at TechCorp, uses FastAPI + PostgreSQL + Docker.",
    },
    {
        "name": "Project Continuity",
        "session1_user": "I'm building an e-commerce platform called ShopEase. Frontend is React, backend is Django, database is MySQL, deployed on AWS ECS.",
        "session2_user": "I need to add user authentication to my project. What approach would you recommend given my tech stack?",
        "recall_keywords": ["django", "react", "shopease", "mysql"],
        "context_for_judge": "User previously said: building ShopEase e-commerce with React + Django + MySQL on AWS ECS.",
    },
]


# ------------------------------------------------------------------ #
# Main experiment                                                     #
# ------------------------------------------------------------------ #
async def main():
    RESULTS_FILE.parent.mkdir(parents=True, exist_ok=True)

    logger.info("=" * 60)
    logger.info("  MEMORY ABLATION — Direct Test")
    logger.info("  %d scenarios, ~%d API calls total", len(SCENARIOS), len(SCENARIOS) * 3)
    logger.info("=" * 60)

    results = []

    for i, sc in enumerate(SCENARIOS):
        logger.info("\n--- Scenario %d/%d: %s ---", i + 1, len(SCENARIOS), sc["name"])

        # ============================================================ #
        # BASELINE: Call LLM for session2 WITHOUT any memory context    #
        # ============================================================ #
        logger.info("  [Baseline] Calling LLM without memory...")
        baseline_messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": sc["session2_user"]},
        ]
        baseline_response = await call_llm(baseline_messages)
        baseline_recall = recall_score(baseline_response, sc["recall_keywords"])
        logger.info("  [Baseline] recall=%.2f response=%s", baseline_recall, baseline_response[:150])

        await asyncio.sleep(DELAY)

        # ============================================================ #
        # TREATMENT: Ingest session1 into memory, retrieve for session2 #
        # ============================================================ #

        # 1) Set up a fresh MemoryManager
        mem_dir = MEMORY_DIR / f"scenario_{i}"
        if mem_dir.exists():
            shutil.rmtree(mem_dir)
        mem_dir.mkdir(parents=True, exist_ok=True)

        from metaclaw.memory.manager import MemoryManager
        from metaclaw.memory.store import MemoryStore

        store = MemoryStore(str(mem_dir / "memory.db"))
        mm = MemoryManager(
            store=store,
            scope_id="default",
            retrieval_mode="keyword",
            use_embeddings=False,
            auto_consolidate=True,
        )

        # 2) Simulate session 1: call LLM and ingest the conversation
        logger.info("  [Treatment] Session 1: establishing context...")
        s1_messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": sc["session1_user"]},
        ]
        s1_response = await call_llm(s1_messages)
        logger.info("  [Treatment] Session 1 response: %s", s1_response[:120])

        # Ingest session turns into memory (format: prompt_text + response_text)
        session_turns = [
            {
                "prompt_text": sc["session1_user"],
                "response_text": s1_response,
            }
        ]
        added = mm.ingest_session_turns(f"session_{i}_1", session_turns)
        stats = mm.get_scope_stats()
        logger.info("  [Treatment] Ingested %d memory units (active=%d, types=%s)",
                     added, stats.get("active", 0), stats.get("active_by_type", {}))

        await asyncio.sleep(DELAY)

        # 3) Session 2: retrieve memories and inject into prompt
        logger.info("  [Treatment] Session 2: querying with memory...")
        memories = mm.retrieve_for_prompt(sc["session2_user"])
        memory_text = mm.render_for_prompt(memories) if memories else ""
        logger.info("  [Treatment] Retrieved %d memories, %d chars", len(memories), len(memory_text))
        if memory_text:
            logger.info("  [Treatment] Memory text preview: %s", memory_text[:300])

        # Build treatment prompt with memory injected
        treatment_system = "You are a helpful assistant."
        if memory_text:
            treatment_system = f"{memory_text}\n\n{treatment_system}"

        treatment_messages = [
            {"role": "system", "content": treatment_system},
            {"role": "user", "content": sc["session2_user"]},
        ]
        treatment_response = await call_llm(treatment_messages)
        treatment_recall = recall_score(treatment_response, sc["recall_keywords"])
        logger.info("  [Treatment] recall=%.2f response=%s", treatment_recall, treatment_response[:150])

        await asyncio.sleep(DELAY)

        # ============================================================ #
        # PRM Judge: score both responses                               #
        # ============================================================ #
        logger.info("  Scoring with PRM judge...")
        baseline_prm = await prm_judge(
            sc["session2_user"], baseline_response, sc["context_for_judge"]
        )
        await asyncio.sleep(DELAY)
        treatment_prm = await prm_judge(
            sc["session2_user"], treatment_response, sc["context_for_judge"]
        )

        result = {
            "name": sc["name"],
            "baseline_recall": baseline_recall,
            "treatment_recall": treatment_recall,
            "recall_delta": treatment_recall - baseline_recall,
            "baseline_prm": baseline_prm,
            "treatment_prm": treatment_prm,
            "prm_delta": treatment_prm - baseline_prm,
            "baseline_response": baseline_response[:500],
            "treatment_response": treatment_response[:500],
            "memory_units_ingested": added,
            "memories_retrieved": len(memories),
            "memory_text": memory_text[:500],
        }
        results.append(result)
        logger.info("  recall: %.2f → %.2f (Δ%+.2f)  prm: %.2f → %.2f (Δ%+.2f)",
                     baseline_recall, treatment_recall, treatment_recall - baseline_recall,
                     baseline_prm, treatment_prm, treatment_prm - baseline_prm)

        await asyncio.sleep(DELAY)

    # ------------------------------------------------------------------ #
    # Summary                                                            #
    # ------------------------------------------------------------------ #
    n = len(results)
    avg_br = sum(r["baseline_recall"] for r in results) / n
    avg_tr = sum(r["treatment_recall"] for r in results) / n
    avg_bp = sum(r["baseline_prm"] for r in results) / n
    avg_tp = sum(r["treatment_prm"] for r in results) / n

    analysis = {
        "timestamp": datetime.now().isoformat(),
        "model": MODEL,
        "scenarios": results,
        "summary": {
            "n": n,
            "baseline_recall": round(avg_br, 4),
            "treatment_recall": round(avg_tr, 4),
            "recall_delta": round(avg_tr - avg_br, 4),
            "baseline_prm": round(avg_bp, 4),
            "treatment_prm": round(avg_tp, 4),
            "prm_delta": round(avg_tp - avg_bp, 4),
            "memory_helps": avg_tr > avg_br or (avg_tr == avg_br and avg_tp > avg_bp),
        },
    }

    with open(RESULTS_FILE, "w") as f:
        json.dump(analysis, f, indent=2, ensure_ascii=False)

    s = analysis["summary"]
    print("\n" + "=" * 60)
    print("  MEMORY ABLATION — RESULTS")
    print("=" * 60)
    print(f"\n  RECALL (cross-session keyword match):")
    print(f"    Baseline:  {s['baseline_recall']:.2f}")
    print(f"    Memory ON: {s['treatment_recall']:.2f}")
    print(f"    Delta:     {s['recall_delta']:+.2f}")
    print(f"\n  PRM QUALITY (LLM-as-judge 0-1):")
    print(f"    Baseline:  {s['baseline_prm']:.2f}")
    print(f"    Memory ON: {s['treatment_prm']:.2f}")
    print(f"    Delta:     {s['prm_delta']:+.2f}")
    print(f"\n  VERDICT: Memory {'IMPROVES' if s['memory_helps'] else 'does NOT improve'} performance")

    for r in results:
        print(f"\n  {r['name']}:")
        print(f"    Recall: {r['baseline_recall']:.2f} → {r['treatment_recall']:.2f} (Δ{r['recall_delta']:+.2f})")
        print(f"    PRM:    {r['baseline_prm']:.2f} → {r['treatment_prm']:.2f} (Δ{r['prm_delta']:+.2f})")
        print(f"    [baseline] {r['baseline_response'][:120]}")
        print(f"    [memory]   {r['treatment_response'][:120]}")

    print("\n" + "=" * 60)
    return analysis


if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result["summary"]["memory_helps"] else 1)
