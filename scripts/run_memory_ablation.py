"""
Memory Ablation Experiment (minimal version).

Compares MetaClaw with memory OFF vs ON using 2 task sequences.
Minimizes API calls to stay within budget.

Usage:
    python scripts/run_memory_ablation.py
"""

import asyncio
import json
import logging
import os
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

import httpx

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("memory_ablation")

# ------------------------------------------------------------------ #
# Config                                                              #
# ------------------------------------------------------------------ #
AZURE_API_BASE = os.environ.get("AZURE_OPENAI_BASE_URL", "https://huaxi-mlg4x1rk-eastus2.services.ai.azure.com/openai/v1")
AZURE_API_KEY = os.environ["AZURE_OPENAI_API_KEY"]
AZURE_MODEL = "gpt-5.4"
PROXY_PORT = 30000
PROXY_URL = f"http://127.0.0.1:{PROXY_PORT}/v1/chat/completions"
MEMORY_DIR = Path.home() / ".metaclaw" / "memory_ablation"
RESULTS_DIR = Path("records/ablation_results")

os.environ["OPENAI_API_KEY"] = AZURE_API_KEY
os.environ["OPENAI_BASE_URL"] = AZURE_API_BASE
os.environ["SKILL_EVOLVER_MODEL"] = AZURE_MODEL

# Rate limit: seconds to wait between API calls
DELAY_BETWEEN_CALLS = 8

# ------------------------------------------------------------------ #
# 2 Task Sequences (minimal set)                                     #
# ------------------------------------------------------------------ #
TASK_SEQUENCES = [
    {
        "name": "User_Context_Recall",
        "sessions": [
            {
                "id": "s1",
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": "Hi, my name is Alice Chen. I'm a senior Python developer at TechCorp. I work with FastAPI and PostgreSQL. We use Docker for deployment."},
                ],
                "session_done": True,
                "recall_keywords": [],
            },
            {
                "id": "s2",
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": "What web framework and database am I using for my work? And what is my name?"},
                ],
                "session_done": True,
                "recall_keywords": ["fastapi", "postgresql", "alice"],
            },
        ],
    },
    {
        "name": "Project_Continuity",
        "sessions": [
            {
                "id": "s1",
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": "I'm building an e-commerce platform called ShopEase. Frontend is React, backend is Django, database is MySQL, deployed on AWS ECS."},
                ],
                "session_done": True,
                "recall_keywords": [],
            },
            {
                "id": "s2",
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": "I need to add user authentication to my project. What approach would you recommend given my tech stack?"},
                ],
                "session_done": True,
                "recall_keywords": ["django", "react", "shopease", "mysql", "aws"],
            },
        ],
    },
]


# ------------------------------------------------------------------ #
# PRM Judge (single call per response, no max_tokens)                #
# ------------------------------------------------------------------ #
async def prm_judge(context: str, question: str, response: str) -> dict:
    """Rate response quality 0-10 via LLM-as-judge."""
    prompt = f"""Rate this AI response on a scale of 0 to 10.
Context from previous sessions: {context}
User question: {question}
Response: {response[:800]}
Reply ONLY with JSON: {{"score": <0-10>, "reasoning": "<brief>"}}"""

    for attempt in range(3):
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    f"{AZURE_API_BASE}/chat/completions",
                    json={
                        "model": AZURE_MODEL,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.1,
                        "max_completion_tokens": 150,
                    },
                    headers={
                        "Authorization": f"Bearer {AZURE_API_KEY}",
                        "Content-Type": "application/json",
                    },
                )
                resp.raise_for_status()
                text = resp.json()["choices"][0]["message"]["content"].strip()
                if "```" in text:
                    text = text.split("```")[1]
                    if text.startswith("json"):
                        text = text[4:]
                result = json.loads(text)
                return {"score": float(result.get("score", 5)) / 10.0, "reasoning": result.get("reasoning", "")}
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                wait = 15 * (attempt + 1)
                logger.warning("  PRM judge rate limited, waiting %ds...", wait)
                await asyncio.sleep(wait)
                continue
            logger.warning("  PRM judge HTTP error: %s", e)
            return {"score": 0.5, "reasoning": f"http_error_{e.response.status_code}"}
        except Exception as e:
            logger.warning("  PRM judge error: %s", e)
            return {"score": 0.5, "reasoning": "parse_error"}

    return {"score": 0.5, "reasoning": "rate_limited"}


# ------------------------------------------------------------------ #
# Proxy helpers                                                       #
# ------------------------------------------------------------------ #
async def wait_for_proxy(timeout_s=90):
    url = f"http://127.0.0.1:{PROXY_PORT}/docs"
    start = time.monotonic()
    while True:
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(url)
                if resp.status_code < 500:
                    return
        except Exception:
            pass
        if time.monotonic() - start > timeout_s:
            raise TimeoutError("Proxy did not start in time")
        await asyncio.sleep(1.0)


async def send_chat(messages, session_id, session_done=False, retries=3):
    body = {
        "model": AZURE_MODEL,
        "messages": messages,
        "session_id": session_id,
        "turn_type": "main",
        "session_done": session_done,
        "max_completion_tokens": 1024,
    }
    for attempt in range(retries):
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(
                    PROXY_URL,
                    json=body,
                    headers={
                        "Authorization": f"Bearer {AZURE_API_KEY}",
                        "Content-Type": "application/json",
                    },
                )
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code in (429, 502):
                wait = 15 * (attempt + 1)
                logger.warning("  Rate limited/502, retrying in %ds (attempt %d/%d)...", wait, attempt+1, retries)
                await asyncio.sleep(wait)
                continue
            raise
    raise RuntimeError(f"Failed after {retries} retries")


def compute_recall(response_text: str, keywords: list[str]) -> float:
    if not keywords:
        return 1.0
    text_lower = response_text.lower()
    hits = sum(1 for kw in keywords if kw.lower() in text_lower)
    return hits / len(keywords)


# ------------------------------------------------------------------ #
# Run one condition                                                   #
# ------------------------------------------------------------------ #
async def run_condition(condition_name: str, memory_enabled: bool) -> dict:
    from metaclaw.config import MetaClawConfig
    from metaclaw.rollout import AsyncRolloutWorker
    from metaclaw.skill_manager import SkillManager

    logger.info("=" * 60)
    logger.info("  CONDITION: %s (memory=%s)", condition_name, memory_enabled)
    logger.info("=" * 60)

    mem_dir = MEMORY_DIR / condition_name
    if mem_dir.exists():
        shutil.rmtree(mem_dir)
    mem_dir.mkdir(parents=True, exist_ok=True)

    config = MetaClawConfig(
        mode="skills_only",
        llm_api_base=AZURE_API_BASE,
        llm_api_key=AZURE_API_KEY,
        llm_model_id=AZURE_MODEL,
        served_model_name=AZURE_MODEL,
        proxy_port=PROXY_PORT,
        proxy_host="127.0.0.1",
        use_skills=True,
        skills_dir=os.path.expanduser("~/.metaclaw/skills"),
        retrieval_mode="template",
        skill_top_k=6,
        task_specific_top_k=10,
        enable_skill_evolution=False,
        memory_enabled=memory_enabled,
        memory_dir=str(mem_dir),
        memory_store_path=str(mem_dir / "memory.db"),
        memory_scope="default",
        memory_retrieval_mode="keyword",
        memory_auto_extract=True,
        memory_auto_consolidate=True,
        memory_max_injected_units=6,
        memory_max_injected_tokens=800,
        memory_auto_upgrade_enabled=False,
        record_enabled=True,
        record_dir=str(RESULTS_DIR / condition_name),
    )

    skill_manager = None
    if config.use_skills:
        Path(config.skills_dir).mkdir(parents=True, exist_ok=True)
        skill_manager = SkillManager(
            skills_dir=config.skills_dir,
            retrieval_mode=config.retrieval_mode,
            embedding_model_path=config.embedding_model_path,
            task_specific_top_k=config.task_specific_top_k,
        )

    memory_manager = None
    if config.memory_enabled:
        from metaclaw.memory.manager import MemoryManager
        try:
            memory_manager = MemoryManager.from_config(config)
            logger.info("  MemoryManager ready: %s", config.memory_store_path)
        except Exception as e:
            logger.error("  MemoryManager init failed: %s", e)

    worker = AsyncRolloutWorker(
        config=config,
        sampling_client=None,
        skill_manager=skill_manager,
        memory_manager=memory_manager,
        prm_scorer=None,
        skill_evolver=None,
    )
    worker.resume_submission()
    worker.start()

    try:
        await wait_for_proxy()
        await asyncio.sleep(3)

        results = []

        for seq_idx, seq in enumerate(TASK_SEQUENCES):
            logger.info("\n--- Sequence %d/%d: %s ---", seq_idx + 1, len(TASK_SEQUENCES), seq["name"])
            seq_results = {"name": seq["name"], "sessions": []}
            context_summary = ""

            for sess_idx, sess in enumerate(seq["sessions"]):
                session_id = f"{condition_name}_{seq['name']}_{sess['id']}"
                logger.info("  Session %d/%d: %s", sess_idx + 1, len(seq["sessions"]), session_id)

                try:
                    data = await send_chat(
                        sess["messages"],
                        session_id=session_id,
                        session_done=sess.get("session_done", False),
                    )
                    # Extract reply from response
                    reply = ""
                    if "choices" in data:
                        reply = data["choices"][0].get("message", {}).get("content", "")
                    elif "response" in data:
                        resp_data = data["response"]
                        if "choices" in resp_data:
                            reply = resp_data["choices"][0].get("message", {}).get("content", "")

                    user_msg = sess["messages"][-1]["content"]
                    recall = compute_recall(reply, sess.get("recall_keywords", []))

                    # Wait before PRM call to avoid rate limits
                    await asyncio.sleep(DELAY_BETWEEN_CALLS)

                    prm = await prm_judge(
                        context=context_summary or "No previous context",
                        question=user_msg,
                        response=reply,
                    )

                    sess_result = {
                        "session_id": session_id,
                        "user_message": user_msg[:200],
                        "response": reply[:500],
                        "recall_keywords": sess.get("recall_keywords", []),
                        "recall_score": recall,
                        "prm_score": prm["score"],
                        "prm_reasoning": prm["reasoning"],
                    }
                    seq_results["sessions"].append(sess_result)
                    logger.info("    recall=%.2f prm=%.2f reply=%s", recall, prm["score"], reply[:150])
                    context_summary += f"\n{user_msg[:200]}"

                except Exception as e:
                    logger.error("    FAILED: %s", e)
                    seq_results["sessions"].append({
                        "session_id": session_id,
                        "error": str(e),
                        "recall_score": 0.0,
                        "prm_score": 0.0,
                    })

                # Wait for memory extraction + rate limit
                if sess.get("session_done") and memory_enabled:
                    logger.info("    Waiting 18s for memory extraction + rate limit...")
                    await asyncio.sleep(18)
                else:
                    await asyncio.sleep(DELAY_BETWEEN_CALLS)

            results.append(seq_results)

    finally:
        worker.stop()
        await asyncio.sleep(2)

    return {"condition": condition_name, "memory_enabled": memory_enabled, "sequences": results}


# ------------------------------------------------------------------ #
# Analysis                                                            #
# ------------------------------------------------------------------ #
def analyze_results(baseline: dict, treatment: dict) -> dict:
    analysis = {"timestamp": datetime.now().isoformat(), "summary": {}, "per_sequence": []}
    b_recalls, t_recalls, b_prms, t_prms = [], [], [], []

    for b_seq, t_seq in zip(baseline["sequences"], treatment["sequences"]):
        seq_a = {"name": b_seq["name"], "sessions": []}
        for b_s, t_s in zip(b_seq["sessions"], t_seq["sessions"]):
            br, tr = b_s.get("recall_score", 0), t_s.get("recall_score", 0)
            bp, tp = b_s.get("prm_score", 0), t_s.get("prm_score", 0)
            if b_s.get("recall_keywords"):
                b_recalls.append(br); t_recalls.append(tr)
                b_prms.append(bp); t_prms.append(tp)
            seq_a["sessions"].append({
                "baseline_recall": br, "treatment_recall": tr, "recall_delta": tr - br,
                "baseline_prm": bp, "treatment_prm": tp, "prm_delta": tp - bp,
                "baseline_response": b_s.get("response", "")[:300],
                "treatment_response": t_s.get("response", "")[:300],
            })
        analysis["per_sequence"].append(seq_a)

    n = len(b_recalls)
    avg_br = sum(b_recalls) / n if n else 0
    avg_tr = sum(t_recalls) / n if n else 0
    avg_bp = sum(b_prms) / n if n else 0
    avg_tp = sum(t_prms) / n if n else 0

    analysis["summary"] = {
        "n_eval": n,
        "baseline_recall": round(avg_br, 4), "treatment_recall": round(avg_tr, 4),
        "recall_delta": round(avg_tr - avg_br, 4),
        "baseline_prm": round(avg_bp, 4), "treatment_prm": round(avg_tp, 4),
        "prm_delta": round(avg_tp - avg_bp, 4),
        "memory_helps": avg_tr > avg_br,
    }
    return analysis


# ------------------------------------------------------------------ #
# Main                                                                #
# ------------------------------------------------------------------ #
async def main():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    logger.info("=" * 60)
    logger.info("  MEMORY ABLATION EXPERIMENT (minimal)")
    logger.info("  %d sequences x 2 conditions", len(TASK_SEQUENCES))
    logger.info("=" * 60)

    # Condition A: Baseline
    baseline = await run_condition("baseline", memory_enabled=False)
    with open(RESULTS_DIR / "baseline_raw.json", "w") as f:
        json.dump(baseline, f, indent=2, ensure_ascii=False)

    await asyncio.sleep(5)

    # Condition B: Treatment
    treatment = await run_condition("treatment", memory_enabled=True)
    with open(RESULTS_DIR / "treatment_raw.json", "w") as f:
        json.dump(treatment, f, indent=2, ensure_ascii=False)

    # Analyze
    analysis = analyze_results(baseline, treatment)
    with open(RESULTS_DIR / "analysis.json", "w") as f:
        json.dump(analysis, f, indent=2, ensure_ascii=False)

    # Report
    s = analysis["summary"]
    print("\n" + "=" * 60)
    print("  MEMORY ABLATION — RESULTS")
    print("=" * 60)
    print(f"  Eval sessions: {s['n_eval']}")
    print(f"\n  RECALL (cross-session keyword match):")
    print(f"    Baseline:  {s['baseline_recall']:.4f}")
    print(f"    Memory ON: {s['treatment_recall']:.4f}")
    print(f"    Delta:     {s['recall_delta']:+.4f}")
    print(f"\n  PRM QUALITY (LLM-as-judge 0-1):")
    print(f"    Baseline:  {s['baseline_prm']:.4f}")
    print(f"    Memory ON: {s['treatment_prm']:.4f}")
    print(f"    Delta:     {s['prm_delta']:+.4f}")
    print(f"\n  VERDICT: Memory {'IMPROVES' if s['memory_helps'] else 'does NOT improve'} cross-session recall")
    print("=" * 60)

    # Per-sequence detail
    for seq in analysis["per_sequence"]:
        print(f"\n  {seq['name']}:")
        for i, sess in enumerate(seq["sessions"]):
            print(f"    Session {i+1}: recall {sess['baseline_recall']:.2f}->{sess['treatment_recall']:.2f} (Δ{sess['recall_delta']:+.2f})  prm {sess['baseline_prm']:.2f}->{sess['treatment_prm']:.2f} (Δ{sess['prm_delta']:+.2f})")
            if sess.get("baseline_response"):
                print(f"      [baseline] {sess['baseline_response'][:150]}")
            if sess.get("treatment_response"):
                print(f"      [memory]   {sess['treatment_response'][:150]}")

    print("\n  Full results: " + str(RESULTS_DIR / "analysis.json"))
    return analysis


if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result["summary"].get("memory_helps", False) else 1)
