#!/usr/bin/env python3
"""
test_synergy.py — Direct test of Skill-Memory synergy improvements.

Tests four modes:
  1. baseline     — no memory, no skills
  2. memory_only  — memory injection only
  3. skill_only   — skill injection only
  4. synergy      — coordinated memory + skill injection (new pipeline)

Uses the Azure GPT-5.4 API directly (bypasses proxy) to minimize complexity.
Targets ~12 API calls total (3 scenarios × 4 modes).

Evaluation:
  - Keyword recall: does the response contain expected keywords?
  - PRM score: LLM-as-judge quality rating (0-10)
"""

import json
import os
import re
import sys
import time
import tempfile
from pathlib import Path
from datetime import datetime

# Insert project root into path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from metaclaw.memory.store import MemoryStore
from metaclaw.memory.manager import MemoryManager
from metaclaw.memory.models import MemoryUnit, MemoryType, MemoryStatus
from metaclaw.skill_manager import SkillManager
from metaclaw.config import MetaClawConfig


# ===================== API Configuration =====================
API_BASE = os.environ.get("AZURE_OPENAI_BASE_URL", "https://huaxi-mlg4x1rk-eastus2.services.ai.azure.com/openai/v1")
API_KEY = os.environ["AZURE_OPENAI_API_KEY"]
MODEL = "gpt-5.4"
MAX_TOKENS = 4096  # GPT-5.x uses reasoning tokens internally, need headroom


def call_llm(messages: list[dict], retries: int = 4) -> str:
    """Call Azure OpenAI API with retry logic and empty-response retry."""
    import urllib.request
    import urllib.error

    url = f"{API_BASE}/chat/completions"
    body = {
        "model": MODEL,
        "messages": messages,
        "max_completion_tokens": MAX_TOKENS,
        "temperature": 0.3,
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}",
    }

    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(body).encode(),
                headers=headers,
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=90) as resp:
                result = json.loads(resp.read().decode())
                content = result["choices"][0]["message"].get("content") or ""
                finish_reason = result["choices"][0].get("finish_reason", "")
                # Retry on empty content (might be rate-limited or filtered)
                if not content.strip() and attempt < retries - 1:
                    print(f"  Empty response (finish_reason={finish_reason}), retry {attempt+1}...")
                    time.sleep(8 * (attempt + 1))
                    continue
                return content
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = 15 * (attempt + 1)
                print(f"  Rate limited (429), waiting {wait}s...")
                time.sleep(wait)
            else:
                body_text = e.read().decode() if hasattr(e, "read") else ""
                print(f"  HTTP {e.code}: {body_text[:200]}")
                if attempt == retries - 1:
                    return ""
                time.sleep(8)
        except Exception as e:
            print(f"  Error: {e}")
            if attempt == retries - 1:
                return ""
            time.sleep(8)
    return ""


# ===================== Test Scenarios =====================
# Each scenario has:
# - session1: prior interaction that generates memories
# - session2: current task that should benefit from memory + skills
# - expected_keywords: what a good response should contain
# - eval_criteria: what the PRM judge should look for

SCENARIOS = [
    {
        "id": "debug_test_failure",
        "description": "Debugging a test failure: memory has project context, skill has debugging methodology",
        "memories": [
            MemoryUnit(
                memory_id="mem_db_1",
                scope_id="default",
                memory_type=MemoryType.PROJECT_STATE,
                status=MemoryStatus.ACTIVE,
                content="The project uses PostgreSQL 16 with connection pooling via pgbouncer (max 50 connections). "
                        "The test suite runs with a separate test database 'myapp_test' on port 5433. "
                        "Tests use pytest with the pytest-asyncio plugin.",
                summary="PostgreSQL 16 + pgbouncer, test DB on port 5433, pytest-asyncio",
                entities=["PostgreSQL", "pgbouncer", "pytest", "myapp_test"],
                topics=["database", "testing", "infrastructure"],
                importance=0.9,
                confidence=0.95,
                source_session_id="day03",
            ),
            MemoryUnit(
                memory_id="mem_db_2",
                scope_id="default",
                memory_type=MemoryType.EPISODIC,
                status=MemoryStatus.ACTIVE,
                content="In day04, test_user_registration was failing intermittently. "
                        "Root cause: pgbouncer connection pool exhaustion when tests run in parallel. "
                        "Fix was to set max_connections=10 in conftest.py and use 'session' scope fixtures.",
                summary="Day04: intermittent test failure due to pgbouncer pool exhaustion, fixed with session scope",
                entities=["test_user_registration", "pgbouncer", "conftest.py"],
                topics=["test failure", "connection pool", "debugging"],
                importance=0.85,
                confidence=0.9,
                source_session_id="day04",
            ),
            MemoryUnit(
                memory_id="mem_db_3",
                scope_id="default",
                memory_type=MemoryType.SEMANTIC,
                status=MemoryStatus.ACTIVE,
                content="The project's test configuration is in tests/conftest.py. Database fixtures use "
                        "async context managers. The DB URL pattern is: "
                        "postgresql+asyncpg://test_user:test_pass@localhost:5433/myapp_test",
                summary="Test DB config in conftest.py, async fixtures, port 5433",
                entities=["conftest.py", "asyncpg", "test_user"],
                topics=["test configuration", "database", "async"],
                importance=0.8,
                confidence=0.95,
                source_session_id="day03",
            ),
        ],
        "task": "The test_order_processing test is failing intermittently with "
                "'asyncpg.exceptions.TooManyConnectionsError'. This just started happening "
                "after we added 5 new test files. Help me debug and fix this systematically.",
        "expected_keywords": ["pgbouncer", "connection", "conftest", "session", "scope", "pool", "5433"],
        "eval_criteria": "A good response should: "
                         "1) Follow systematic debugging steps (reproduce, isolate, hypothesize, fix), "
                         "2) Reference project-specific context (pgbouncer, port 5433, conftest.py), "
                         "3) Connect to the prior similar issue (day04 pool exhaustion), "
                         "4) Suggest concrete fix (session scope fixtures, connection limits). "
                         "Memory-only might miss the methodology, skill-only might miss the project context. "
                         "Synergy should combine both for the best answer.",
    },
    {
        "id": "experiment_design",
        "description": "Designing an ML experiment: memory has project specifics, skill has methodology",
        "memories": [
            MemoryUnit(
                memory_id="mem_exp_1",
                scope_id="default",
                memory_type=MemoryType.PROJECT_STATE,
                status=MemoryStatus.ACTIVE,
                content="Current model: fine-tuned Qwen3-8B with LoRA rank 32. "
                        "Training data: 12,000 instruction-response pairs from customer support logs. "
                        "Current accuracy on held-out set: 72.3% (measured with exact match). "
                        "Training runs on 2× A100 GPUs, takes ~4 hours per run.",
                summary="Qwen3-8B LoRA, 12K training samples, 72.3% accuracy, 2xA100",
                entities=["Qwen3-8B", "LoRA", "A100"],
                topics=["model training", "accuracy", "compute"],
                importance=0.9,
                confidence=0.9,
                source_session_id="day07",
            ),
            MemoryUnit(
                memory_id="mem_exp_2",
                scope_id="default",
                memory_type=MemoryType.EPISODIC,
                status=MemoryStatus.ACTIVE,
                content="In day06, we tried increasing LoRA rank to 64 but accuracy only improved to 73.1% "
                        "(+0.8%) while training time doubled to 8 hours. The team decided the compute cost "
                        "was not worth the marginal improvement. Better to focus on data quality.",
                summary="Day06: LoRA rank 64 → only +0.8% accuracy, 2x compute cost, not worth it",
                entities=["LoRA rank 64", "accuracy improvement"],
                topics=["experiment results", "compute efficiency"],
                importance=0.85,
                confidence=0.95,
                source_session_id="day06",
            ),
            MemoryUnit(
                memory_id="mem_exp_3",
                scope_id="default",
                memory_type=MemoryType.SEMANTIC,
                status=MemoryStatus.ACTIVE,
                content="The evaluation pipeline uses 3 metrics: exact match accuracy, F1 score, "
                        "and response latency (p95). The test set has 2,000 samples stratified by "
                        "5 categories (billing, returns, shipping, account, technical).",
                summary="Eval: exact match + F1 + latency, 2K test set, 5 categories",
                entities=["F1 score", "latency", "test set"],
                topics=["evaluation", "metrics", "categories"],
                importance=0.8,
                confidence=0.9,
                source_session_id="day05",
            ),
        ],
        "task": "We want to try data augmentation to improve our model's accuracy. "
                "Please design a rigorous experiment plan to test whether augmenting "
                "our training data with synthetic examples improves performance.",
        "expected_keywords": ["baseline", "ablation", "seeds", "Qwen3", "72.3", "F1", "exact match"],
        "eval_criteria": "A good response should: "
                         "1) Include proper experimental design (baselines, ablations, multiple seeds), "
                         "2) Reference the current model specifics (Qwen3-8B, LoRA rank 32, 72.3% baseline), "
                         "3) Use the existing evaluation metrics (exact match, F1, latency), "
                         "4) Consider compute budget (2xA100, ~4h per run), "
                         "5) Learn from past experiment (LoRA rank 64 was not worth compute cost). "
                         "Memory provides project context, skill provides methodology. Both are needed.",
    },
    {
        "id": "write_test_for_feature",
        "description": "Writing tests for new feature: memory has project patterns, skill has testing methodology",
        "memories": [
            MemoryUnit(
                memory_id="mem_test_1",
                scope_id="default",
                memory_type=MemoryType.SEMANTIC,
                status=MemoryStatus.ACTIVE,
                content="The project uses pytest with fixtures defined in tests/conftest.py. "
                        "All API tests inherit from BaseAPITest which provides a test client. "
                        "Database fixtures use factory_boy for generating test data. "
                        "The test naming convention is test_<feature>_<scenario>.",
                summary="pytest + factory_boy fixtures, BaseAPITest, naming: test_feature_scenario",
                entities=["pytest", "factory_boy", "BaseAPITest", "conftest.py"],
                topics=["testing", "fixtures", "conventions"],
                importance=0.9,
                confidence=0.95,
                source_session_id="day02",
            ),
            MemoryUnit(
                memory_id="mem_test_2",
                scope_id="default",
                memory_type=MemoryType.PREFERENCE,
                status=MemoryStatus.ACTIVE,
                content="The team requires at least 80% test coverage for new features. "
                        "Each test file should test one module. Use parametrize for testing "
                        "multiple inputs. Always test both happy path and error cases.",
                summary="Team requirement: 80% coverage, parametrize, happy path + error cases",
                entities=["test coverage", "parametrize"],
                topics=["testing requirements", "code quality"],
                importance=0.85,
                confidence=0.9,
                source_session_id="day01",
            ),
            MemoryUnit(
                memory_id="mem_test_3",
                scope_id="default",
                memory_type=MemoryType.EPISODIC,
                status=MemoryStatus.ACTIVE,
                content="In day03, a test for the payment module was rejected in code review "
                        "because it only tested the happy path. Reviewer asked for tests covering: "
                        "invalid card number, expired card, insufficient funds, and network timeout.",
                summary="Day03: payment test rejected — need error case coverage",
                entities=["payment module", "code review"],
                topics=["test review", "error cases"],
                importance=0.7,
                confidence=0.9,
                source_session_id="day03",
            ),
        ],
        "task": "I just implemented a new user notification feature in src/notifications/sender.py. "
                "It sends email and SMS notifications. Please write comprehensive tests for this module.",
        "expected_keywords": ["pytest", "factory_boy", "parametrize", "BaseAPITest", "error", "happy path", "conftest"],
        "eval_criteria": "A good response should: "
                         "1) Follow the project's testing conventions (pytest, factory_boy, BaseAPITest), "
                         "2) Use parametrize for multiple scenarios, "
                         "3) Cover both happy path AND error cases (learned from day03 code review), "
                         "4) Follow proper test structure (arrange-act-assert), "
                         "5) Include test naming convention: test_feature_scenario. "
                         "Memory provides project-specific patterns, skill provides testing methodology.",
    },
]


def setup_memory_store(memories: list[MemoryUnit]) -> MemoryManager:
    """Create an in-memory MemoryStore and MemoryManager with pre-loaded memories."""
    tmp_dir = tempfile.mkdtemp(prefix="synergy_test_")
    db_path = os.path.join(tmp_dir, "memory.db")
    store = MemoryStore(db_path)
    mm = MemoryManager(
        store=store,
        scope_id="default",
        retrieval_mode="keyword",
        use_embeddings=False,
        auto_consolidate=False,
    )
    if memories:
        store.add_memories(memories)
    return mm


def setup_skill_manager() -> SkillManager:
    """Load skills from the default skill directory."""
    skills_dir = os.path.expanduser("~/.metaclaw/skills")
    if not os.path.isdir(skills_dir):
        # Fallback to project skills
        skills_dir = "memory_data/skills"
    sm = SkillManager(
        skills_dir=skills_dir,
        retrieval_mode="template",
    )
    return sm


def compute_keyword_recall(response: str, expected: list[str]) -> float:
    """Fraction of expected keywords found in response (case-insensitive)."""
    if not expected:
        return 1.0
    response_lower = response.lower()
    found = sum(1 for kw in expected if kw.lower() in response_lower)
    return found / len(expected)


def prm_score(task: str, response: str, criteria: str) -> float:
    """Multi-criteria LLM-as-judge evaluation (0-10).

    Scores on 4 dimensions to better discriminate subtle quality differences:
    1. Methodology — Is the approach systematic and well-structured?
    2. Specificity — Does it reference concrete project details?
    3. Completeness — Does it address all key aspects of the task?
    4. Actionability — Are suggestions concrete and immediately usable?
    """
    if not response.strip():
        return 0.0

    judge_prompt = f"""You are a senior engineer evaluating an AI assistant's response.
Score it on FOUR dimensions (each 0-10), then compute a weighted average.

TASK: {task}

RESPONSE (first 3000 chars):
{response[:3000]}

EVALUATION CRITERIA:
{criteria}

DIMENSIONS (score each independently):
1. METHODOLOGY (weight 0.20): Is the approach systematic, well-structured, and follows best practices?
2. SPECIFICITY (weight 0.35): Does it reference concrete, project-specific details (names, numbers, prior experiences)?
   - Score 9-10 only if it references MULTIPLE specific project details (e.g. exact tool names, config values, past incidents)
   - Score 5-6 if it gives generic advice that could apply to any project
3. COMPLETENESS (weight 0.25): Does it cover all key aspects of the task? Are any important areas missing?
4. ACTIONABILITY (weight 0.20): Are the suggestions concrete, step-by-step, and immediately implementable?

IMPORTANT: Be precise with scores. Use half-points (e.g. 7.5) if needed. Do NOT default to 8 for everything.
A response that gives good generic advice but lacks project-specific details should score low on SPECIFICITY.

OUTPUT FORMAT (exactly):
Methodology: X/10
Specificity: X/10
Completeness: X/10
Actionability: X/10
Weighted: X/10"""

    result = call_llm([
        {"role": "system", "content": "You are a precise evaluator. Follow the output format exactly."},
        {"role": "user", "content": judge_prompt},
    ])

    # Parse multi-dimensional scores
    dimensions = {}
    for dim in ["Methodology", "Specificity", "Completeness", "Actionability", "Weighted"]:
        match = re.search(rf'{dim}:\s*(\d+(?:\.\d+)?)\s*/\s*10', result)
        if match:
            dimensions[dim.lower()] = min(float(match.group(1)), 10.0)

    # Use the weighted score if parsed, otherwise compute from dimensions
    if "weighted" in dimensions:
        return dimensions["weighted"]

    weights = {"methodology": 0.20, "specificity": 0.35, "completeness": 0.25, "actionability": 0.20}
    if len(dimensions) >= 3:
        total = sum(dimensions.get(d, 5.0) * w for d, w in weights.items())
        return round(total, 1)

    # Fallback: try to extract any single score
    match = re.search(r'(\d+(?:\.\d+)?)\s*/\s*10', result)
    if match:
        return min(float(match.group(1)), 10.0)
    return 5.0


def build_synergy_prompt(
    memory_text: str,
    skills: list[dict],
) -> str:
    """Build skill-aware structured template with actionable tips.

    Extracts 1-line actionable summaries from matched skills, then
    wraps memories with structured labels.  No full skill content injection.
    """
    skill_steps = []
    for s in skills[:3]:
        content = s.get("content", "")
        bold_actions = re.findall(r'\d+\.\s+\*\*([^*]+)\*\*', content)
        name = s.get("name", "").replace("-", " ")
        if bold_actions:
            steps = " → ".join(a.strip() for a in bold_actions[:5])
            skill_steps.append(f"{steps}")
        else:
            skill_steps.append(name)
    methodology = "; ".join(skill_steps)

    parts = [
        "## Augmented Context",
        "",
        f"Recommended approach: {methodology}.",
        "Use the project-specific experience below to inform your response.",
        "",
        "### Memories (Project-Specific Experience — WHAT worked/failed before)",
        "",
        memory_text,
    ]

    return "\n".join(parts)


def run_scenario(scenario: dict, skill_manager: SkillManager) -> dict:
    """Run one scenario across all 4 modes."""
    print(f"\n{'='*60}")
    print(f"Scenario: {scenario['id']} — {scenario['description']}")
    print(f"{'='*60}")

    task = scenario["task"]
    expected_kw = scenario["expected_keywords"]
    eval_criteria = scenario["eval_criteria"]
    memories = scenario["memories"]

    results = {}

    # --- Mode 1: Baseline (no memory, no skills) ---
    print("\n[1/4] Baseline (no augmentation)...")
    baseline_resp = call_llm([
        {"role": "system", "content": "You are a helpful software engineer assistant."},
        {"role": "user", "content": task},
    ])
    results["baseline"] = {
        "response": baseline_resp,
        "recall": compute_keyword_recall(baseline_resp, expected_kw),
        "response_len": len(baseline_resp),
    }
    print(f"  Recall: {results['baseline']['recall']:.2f}, len={len(baseline_resp)}")
    time.sleep(5)

    # --- Mode 2: Memory-only ---
    print("[2/4] Memory-only...")
    mm = setup_memory_store(memories)
    mem_units = mm.retrieve_for_prompt(task, scope_id="default")
    memory_text = mm.render_for_prompt(mem_units) if mem_units else ""
    print(f"  Retrieved {len(mem_units)} memories, ~{len(memory_text.split())} tokens")

    memory_system = f"You are a helpful assistant.\n\n{memory_text}" if memory_text else "You are a helpful assistant."
    memory_resp = call_llm([
        {"role": "system", "content": memory_system},
        {"role": "user", "content": task},
    ])
    results["memory_only"] = {
        "response": memory_resp,
        "recall": compute_keyword_recall(memory_resp, expected_kw),
        "memory_count": len(mem_units),
        "memory_tokens": len(memory_text.split()),
        "response_len": len(memory_resp),
    }
    print(f"  Recall: {results['memory_only']['recall']:.2f}, len={len(memory_resp)}")
    time.sleep(5)

    # --- Mode 3: Skill-only (same retrieval as before — shows the problem) ---
    print("[3/4] Skill-only...")
    skills = skill_manager.retrieve(task, top_k=6)
    # Apply budget to avoid overwhelming the model
    skill_text = skill_manager.format_for_conversation_budgeted(skills, max_tokens=500)
    skill_names = [s.get("name", "?") for s in skills]
    print(f"  Retrieved {len(skills)} skills: {', '.join(skill_names[:5])}")
    print(f"  Skill tokens: ~{len(skill_text.split())}")

    skill_system = f"You are a helpful assistant.\n\n{skill_text}" if skill_text else "You are a helpful assistant."
    skill_resp = call_llm([
        {"role": "system", "content": skill_system},
        {"role": "user", "content": task},
    ])
    results["skill_only"] = {
        "response": skill_resp,
        "recall": compute_keyword_recall(skill_resp, expected_kw),
        "skill_count": len(skills),
        "skill_tokens": len(skill_text.split()),
        "response_len": len(skill_resp),
    }
    print(f"  Recall: {results['skill_only']['recall']:.2f}, len={len(skill_resp)}")
    time.sleep(5)

    # --- Mode 4: Synergy (template-only, no skill content injection) ---
    print("[4/4] Synergy (template-only)...")
    # Retrieve RELEVANT skills (used for template customization only)
    relevant_skills = skill_manager.retrieve_relevant(task, top_k=5, min_relevance=0.08)
    relevant_skill_names = [s.get("name", "?") for s in relevant_skills]
    print(f"  Relevant skills: {len(relevant_skills)} ({', '.join(relevant_skill_names[:5])})")

    mm2 = setup_memory_store(memories)

    if len(relevant_skills) < 2:
        # < 2 relevant skills → plain memory injection (= memory-only)
        print(f"  {len(relevant_skills)} relevant skills (< 2) → plain memory injection")
        synergy_mem_units = mm2.retrieve_for_prompt(task, scope_id="default")
        synergy_memory_text = mm2.render_for_prompt(synergy_mem_units) if synergy_mem_units else ""
        synergy_system = f"You are a helpful assistant.\n\n{synergy_memory_text}" if synergy_memory_text else "You are a helpful assistant."
        total_tokens = len(synergy_memory_text.split())
    else:
        # Skills found → structured template with skill-name hints (no content)
        synergy_mem_units = mm2.retrieve_for_prompt(task, scope_id="default")
        synergy_memory_text = mm2.render_for_prompt(synergy_mem_units) if synergy_mem_units else ""

        synergy_prompt = build_synergy_prompt(synergy_memory_text, relevant_skills)
        synergy_system = f"You are a helpful assistant.\n\n{synergy_prompt}"
        total_tokens = len(synergy_prompt.split())

    print(f"  Memories: {len(synergy_mem_units)}, total augmentation: ~{total_tokens} tokens")

    synergy_resp = call_llm([
        {"role": "system", "content": synergy_system},
        {"role": "user", "content": task},
    ])
    results["synergy"] = {
        "response": synergy_resp,
        "recall": compute_keyword_recall(synergy_resp, expected_kw),
        "memory_count": len(synergy_mem_units),
        "memory_deduped": 0,
        "skill_count": len(relevant_skills),
        "total_aug_tokens": total_tokens,
        "response_len": len(synergy_resp),
    }
    print(f"  Recall: {results['synergy']['recall']:.2f}, len={len(synergy_resp)}")

    return results


def run_prm_scoring(scenarios_results: dict) -> dict:
    """Run PRM scoring for all scenarios and modes."""
    print(f"\n{'='*60}")
    print("Running PRM scoring (LLM-as-judge)...")
    print(f"{'='*60}")

    prm_results = {}
    for sc_id, sc in scenarios_results.items():
        scenario = next(s for s in SCENARIOS if s["id"] == sc_id)
        prm_results[sc_id] = {}
        for mode in ["baseline", "memory_only", "skill_only", "synergy"]:
            resp = sc[mode]["response"]
            if not resp:
                prm_results[sc_id][mode] = 0.0
                continue
            score = prm_score(scenario["task"], resp, scenario["eval_criteria"])
            prm_results[sc_id][mode] = score
            print(f"  {sc_id}/{mode}: PRM={score:.1f}")
            time.sleep(1)  # Rate limit protection

    return prm_results


def main():
    print("=" * 60)
    print("Skill-Memory Synergy Validation Test")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Model: {MODEL}")
    print("=" * 60)

    # Setup skill manager
    skill_manager = setup_skill_manager()
    skill_count = skill_manager.get_skill_count()
    print(f"Skills loaded: {skill_count}")

    # Run all scenarios
    all_results = {}
    for scenario in SCENARIOS:
        results = run_scenario(scenario, skill_manager)
        all_results[scenario["id"]] = results
        time.sleep(2)  # Rate limit protection

    # Run PRM scoring
    prm_scores = run_prm_scoring(all_results)

    # Combine and summarize
    print(f"\n{'='*60}")
    print("RESULTS SUMMARY")
    print(f"{'='*60}")

    summary = {
        "timestamp": datetime.now().isoformat(),
        "model": MODEL,
        "scenarios": {},
    }

    print(f"\n{'Scenario':<25} {'Mode':<15} {'Recall':<10} {'PRM':<8} {'Tokens':<10}")
    print("-" * 70)

    mode_totals = {"baseline": [], "memory_only": [], "skill_only": [], "synergy": []}

    for sc_id in all_results:
        sc_results = all_results[sc_id]
        sc_prm = prm_scores.get(sc_id, {})
        summary["scenarios"][sc_id] = {}

        for mode in ["baseline", "memory_only", "skill_only", "synergy"]:
            recall = sc_results[mode]["recall"]
            prm = sc_prm.get(mode, 0)
            tokens = sc_results[mode].get("total_aug_tokens", sc_results[mode].get("memory_tokens", sc_results[mode].get("skill_tokens", 0)))
            mode_totals[mode].append({"recall": recall, "prm": prm})

            print(f"{sc_id:<25} {mode:<15} {recall:<10.2f} {prm:<8.1f} {tokens:<10}")

            summary["scenarios"][sc_id][mode] = {
                "recall": recall,
                "prm": prm,
                "response_len": sc_results[mode]["response_len"],
                "response_preview": sc_results[mode]["response"][:500],
            }

    # Averages
    print(f"\n{'AVERAGE':<25} {'Mode':<15} {'Recall':<10} {'PRM':<8}")
    print("-" * 55)
    for mode in ["baseline", "memory_only", "skill_only", "synergy"]:
        avg_recall = sum(m["recall"] for m in mode_totals[mode]) / len(mode_totals[mode])
        avg_prm = sum(m["prm"] for m in mode_totals[mode]) / len(mode_totals[mode])
        print(f"{'AVERAGE':<25} {mode:<15} {avg_recall:<10.2f} {avg_prm:<8.1f}")
        summary[f"avg_{mode}"] = {"recall": avg_recall, "prm": avg_prm}

    # Key comparisons
    synergy_recall = summary["avg_synergy"]["recall"]
    synergy_prm = summary["avg_synergy"]["prm"]
    mem_recall = summary["avg_memory_only"]["recall"]
    mem_prm = summary["avg_memory_only"]["prm"]
    skill_recall = summary["avg_skill_only"]["recall"]
    skill_prm = summary["avg_skill_only"]["prm"]
    best_single = max(mem_prm, skill_prm)

    print(f"\n{'='*60}")
    print("KEY METRICS")
    print(f"{'='*60}")
    print(f"Synergy PRM:        {synergy_prm:.1f}")
    print(f"Memory-only PRM:    {mem_prm:.1f}")
    print(f"Skill-only PRM:     {skill_prm:.1f}")
    print(f"Best single module: {best_single:.1f}")
    print(f"Synergy vs best:    {synergy_prm - best_single:+.1f}")
    print(f"1+1>2 achieved?     {'YES' if synergy_prm > best_single else 'NO'}")

    # Save results
    output_dir = Path("records/synergy_results")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "synergy_test_results.json"
    with open(output_path, "w") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"\nResults saved to: {output_path}")

    return summary


if __name__ == "__main__":
    main()
