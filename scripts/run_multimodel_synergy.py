#!/usr/bin/env python3
"""
run_multimodel_synergy.py — Large-scale Skill-Memory synergy experiment.

Tests synergy across multiple models (strong → weak) to find where
the 1+1>2 effect is most pronounced.

Models tested:
  - gpt-5.4       (strong, uses reasoning tokens → max_completion_tokens=4096)
  - gpt-4.1-mini  (medium)
  - gpt-4o-mini   (weak)
  - gpt-4.1-nano  (very weak)

Modes per model:
  1. baseline    — no augmentation
  2. memory_only — memory injection only
  3. synergy     — template-only synergy (memory + skill hints)
  (skill-only skipped: proven useless in earlier experiments)

5 scenarios × 3 modes × 4 models × 2 trials = 120 API calls + 120 PRM judge calls

Evaluation:
  - Keyword recall (0-1)
  - Multi-criteria PRM score (0-10)
"""

import json
import os
import re
import sys
import time
import tempfile
import traceback
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field, asdict

# Insert project root into path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from metaclaw.memory.store import MemoryStore
from metaclaw.memory.manager import MemoryManager
from metaclaw.memory.models import MemoryUnit, MemoryType, MemoryStatus
from metaclaw.skill_manager import SkillManager

# ===================== API Configuration =====================
API_BASE = os.environ.get("AZURE_OPENAI_BASE_URL", "https://huaxi-mlg4x1rk-eastus2.services.ai.azure.com/openai/v1")
API_KEY = os.environ["AZURE_OPENAI_API_KEY"]

# PRM judge always uses gpt-5.4 for consistency
JUDGE_MODEL = "gpt-5.4"
JUDGE_MAX_TOKENS = 4096

# Models to test: (display_name, model_id, max_completion_tokens)
# All models to test
MODELS = [
    ("gpt-5.4",      "gpt-5.4",             4096),   # strong (reasoning tokens)
    # ("gpt-4o",       "gpt-4o",              2048),   # medium-strong (already tested)
    # ("gpt-4o-mini",  "gpt-4o-mini",         2048),   # weak (already tested)
    # ("gpt-4.1-nano", "gpt-4.1-nano",        2048),   # very weak (already tested)
]

# Set to True to skip gpt-5.4 (already tested in previous runs)
SKIP_GPT54 = False

TRIALS = 2  # runs per (model, scenario, mode)


def call_llm(messages: list[dict], model: str, max_tokens: int,
             retries: int = 4, temperature: float = 0.3) -> str:
    """Call Azure OpenAI API with retry logic."""
    import urllib.request
    import urllib.error

    url = f"{API_BASE}/chat/completions"

    # GPT-5.x uses max_completion_tokens; older models use max_tokens
    token_key = "max_completion_tokens" if "5." in model else "max_tokens"
    body = {
        "model": model,
        "messages": messages,
        token_key: max_tokens,
        "temperature": temperature,
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
            with urllib.request.urlopen(req, timeout=120) as resp:
                result = json.loads(resp.read().decode())
                content = result["choices"][0]["message"].get("content") or ""
                finish_reason = result["choices"][0].get("finish_reason", "")
                if not content.strip() and attempt < retries - 1:
                    print(f"    Empty response (finish_reason={finish_reason}), retry {attempt+1}...")
                    time.sleep(8 * (attempt + 1))
                    continue
                return content
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = 15 * (attempt + 1)
                print(f"    Rate limited (429), waiting {wait}s...")
                time.sleep(wait)
            else:
                body_text = e.read().decode() if hasattr(e, "read") else ""
                print(f"    HTTP {e.code}: {body_text[:200]}")
                if attempt == retries - 1:
                    return ""
                time.sleep(8)
        except Exception as e:
            print(f"    Error: {e}")
            if attempt == retries - 1:
                return ""
            time.sleep(8)
    return ""


# ===================== Test Scenarios =====================
SCENARIOS = [
    # --- Scenario 1: Debug test failure (matches debug-systematically + experiment-debugging) ---
    {
        "id": "debug_test_failure",
        "description": "Debugging intermittent test failure with project-specific DB context",
        "memories": [
            MemoryUnit(
                memory_id="mem_db_1", scope_id="default",
                memory_type=MemoryType.PROJECT_STATE, status=MemoryStatus.ACTIVE,
                content="The project uses PostgreSQL 16 with connection pooling via pgbouncer (max 50 connections). "
                        "The test suite runs with a separate test database 'myapp_test' on port 5433. "
                        "Tests use pytest with the pytest-asyncio plugin.",
                summary="PostgreSQL 16 + pgbouncer, test DB on port 5433, pytest-asyncio",
                entities=["PostgreSQL", "pgbouncer", "pytest", "myapp_test"],
                topics=["database", "testing", "infrastructure"],
                importance=0.9, confidence=0.95, source_session_id="day03",
            ),
            MemoryUnit(
                memory_id="mem_db_2", scope_id="default",
                memory_type=MemoryType.EPISODIC, status=MemoryStatus.ACTIVE,
                content="In day04, test_user_registration was failing intermittently. "
                        "Root cause: pgbouncer connection pool exhaustion when tests run in parallel. "
                        "Fix was to set max_connections=10 in conftest.py and use 'session' scope fixtures.",
                summary="Day04: intermittent test failure due to pgbouncer pool exhaustion, fixed with session scope",
                entities=["test_user_registration", "pgbouncer", "conftest.py"],
                topics=["test failure", "connection pool", "debugging"],
                importance=0.85, confidence=0.9, source_session_id="day04",
            ),
            MemoryUnit(
                memory_id="mem_db_3", scope_id="default",
                memory_type=MemoryType.SEMANTIC, status=MemoryStatus.ACTIVE,
                content="The project's test configuration is in tests/conftest.py. Database fixtures use "
                        "async context managers. The DB URL pattern is: "
                        "postgresql+asyncpg://test_user:test_pass@localhost:5433/myapp_test",
                summary="Test DB config in conftest.py, async fixtures, port 5433",
                entities=["conftest.py", "asyncpg", "test_user"],
                topics=["test configuration", "database", "async"],
                importance=0.8, confidence=0.95, source_session_id="day03",
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
                         "4) Suggest concrete fix (session scope fixtures, connection limits).",
    },
    # --- Scenario 2: Experiment design (matches hypothesis-formulation + experiment-design-rigor) ---
    {
        "id": "experiment_design",
        "description": "Designing ML experiment with project-specific model context",
        "memories": [
            MemoryUnit(
                memory_id="mem_exp_1", scope_id="default",
                memory_type=MemoryType.PROJECT_STATE, status=MemoryStatus.ACTIVE,
                content="Current model: fine-tuned Qwen3-8B with LoRA rank 32. "
                        "Training data: 12,000 instruction-response pairs from customer support logs. "
                        "Current accuracy on held-out set: 72.3% (measured with exact match). "
                        "Training runs on 2× A100 GPUs, takes ~4 hours per run.",
                summary="Qwen3-8B LoRA, 12K training samples, 72.3% accuracy, 2xA100",
                entities=["Qwen3-8B", "LoRA", "A100"],
                topics=["model training", "accuracy", "compute"],
                importance=0.9, confidence=0.9, source_session_id="day07",
            ),
            MemoryUnit(
                memory_id="mem_exp_2", scope_id="default",
                memory_type=MemoryType.EPISODIC, status=MemoryStatus.ACTIVE,
                content="In day06, we tried increasing LoRA rank to 64 but accuracy only improved to 73.1% "
                        "(+0.8%) while training time doubled to 8 hours. The team decided the compute cost "
                        "was not worth the marginal improvement. Better to focus on data quality.",
                summary="Day06: LoRA rank 64 → only +0.8% accuracy, 2x compute cost, not worth it",
                entities=["LoRA rank 64", "accuracy improvement"],
                topics=["experiment results", "compute efficiency"],
                importance=0.85, confidence=0.95, source_session_id="day06",
            ),
            MemoryUnit(
                memory_id="mem_exp_3", scope_id="default",
                memory_type=MemoryType.SEMANTIC, status=MemoryStatus.ACTIVE,
                content="The evaluation pipeline uses 3 metrics: exact match accuracy, F1 score, "
                        "and response latency (p95). The test set has 2,000 samples stratified by "
                        "5 categories (billing, returns, shipping, account, technical).",
                summary="Eval: exact match + F1 + latency, 2K test set, 5 categories",
                entities=["F1 score", "latency", "test set"],
                topics=["evaluation", "metrics", "categories"],
                importance=0.8, confidence=0.9, source_session_id="day05",
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
                         "5) Learn from past experiment (LoRA rank 64 was not worth compute cost).",
    },
    # --- Scenario 3: Write tests (matches test-before-ship + debug-systematically) ---
    {
        "id": "write_test_for_feature",
        "description": "Writing tests using project-specific patterns and conventions",
        "memories": [
            MemoryUnit(
                memory_id="mem_test_1", scope_id="default",
                memory_type=MemoryType.SEMANTIC, status=MemoryStatus.ACTIVE,
                content="The project uses pytest with fixtures defined in tests/conftest.py. "
                        "All API tests inherit from BaseAPITest which provides a test client. "
                        "Database fixtures use factory_boy for generating test data. "
                        "The test naming convention is test_<feature>_<scenario>.",
                summary="pytest + factory_boy fixtures, BaseAPITest, naming: test_feature_scenario",
                entities=["pytest", "factory_boy", "BaseAPITest", "conftest.py"],
                topics=["testing", "fixtures", "conventions"],
                importance=0.9, confidence=0.95, source_session_id="day02",
            ),
            MemoryUnit(
                memory_id="mem_test_2", scope_id="default",
                memory_type=MemoryType.PREFERENCE, status=MemoryStatus.ACTIVE,
                content="The team requires at least 80% test coverage for new features. "
                        "Each test file should test one module. Use parametrize for testing "
                        "multiple inputs. Always test both happy path and error cases.",
                summary="Team requirement: 80% coverage, parametrize, happy path + error cases",
                entities=["test coverage", "parametrize"],
                topics=["testing requirements", "code quality"],
                importance=0.85, confidence=0.9, source_session_id="day01",
            ),
            MemoryUnit(
                memory_id="mem_test_3", scope_id="default",
                memory_type=MemoryType.EPISODIC, status=MemoryStatus.ACTIVE,
                content="In day03, a test for the payment module was rejected in code review "
                        "because it only tested the happy path. Reviewer asked for tests covering: "
                        "invalid card number, expired card, insufficient funds, and network timeout.",
                summary="Day03: payment test rejected — need error case coverage",
                entities=["payment module", "code review"],
                topics=["test review", "error cases"],
                importance=0.7, confidence=0.9, source_session_id="day03",
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
                         "5) Include test naming convention: test_feature_scenario.",
    },
    # --- Scenario 4: Data pipeline validation (matches data-validation-first + codebase-navigation) ---
    {
        "id": "data_pipeline_debug",
        "description": "Debugging data pipeline with project-specific ETL context",
        "memories": [
            MemoryUnit(
                memory_id="mem_data_1", scope_id="default",
                memory_type=MemoryType.PROJECT_STATE, status=MemoryStatus.ACTIVE,
                content="The ETL pipeline reads from 3 Parquet sources: users.parquet (500K rows), "
                        "orders.parquet (2.1M rows), and products.parquet (15K rows). "
                        "The pipeline runs nightly on Airflow at 02:00 UTC. "
                        "Output goes to the analytics.fact_orders table in Redshift.",
                summary="ETL: 3 Parquet sources → Redshift analytics.fact_orders, nightly Airflow 02:00 UTC",
                entities=["Airflow", "Redshift", "Parquet", "fact_orders"],
                topics=["ETL", "data pipeline", "infrastructure"],
                importance=0.9, confidence=0.95, source_session_id="day10",
            ),
            MemoryUnit(
                memory_id="mem_data_2", scope_id="default",
                memory_type=MemoryType.EPISODIC, status=MemoryStatus.ACTIVE,
                content="In day11, the pipeline silently dropped 12% of orders because user_id had NaN values "
                        "in the orders source. The inner join with users table eliminated these rows. "
                        "Fix: switched to left join and added a validation step to flag NaN user_ids upstream.",
                summary="Day11: 12% data loss from NaN user_ids in inner join, fixed with left join + validation",
                entities=["user_id", "NaN", "inner join", "orders"],
                topics=["data quality", "join issues", "debugging"],
                importance=0.9, confidence=0.95, source_session_id="day11",
            ),
            MemoryUnit(
                memory_id="mem_data_3", scope_id="default",
                memory_type=MemoryType.SEMANTIC, status=MemoryStatus.ACTIVE,
                content="The data team uses pandas for transformations. Key conventions: "
                        "always check df.shape before and after joins, assert no unexpected row count changes, "
                        "log null counts per column at each pipeline stage. "
                        "Config in etl/config.yaml, validation rules in etl/validators.py.",
                summary="Pandas ETL conventions: shape checks, join assertions, null logging, config in etl/",
                entities=["pandas", "etl/config.yaml", "etl/validators.py"],
                topics=["ETL conventions", "data validation", "pandas"],
                importance=0.8, confidence=0.9, source_session_id="day09",
            ),
        ],
        "task": "Our nightly data pipeline is showing a 15% row count drop in fact_orders compared to "
                "last week. The total went from 2.1M to 1.78M rows. How should I investigate and fix this?",
        "expected_keywords": ["join", "NaN", "user_id", "Parquet", "shape", "null", "validation", "Airflow"],
        "eval_criteria": "A good response should: "
                         "1) Start with data validation (check shapes, nulls, dtypes before analysis), "
                         "2) Reference the prior similar issue (day11 NaN user_ids causing join drops), "
                         "3) Suggest systematic pipeline debugging (stage-by-stage row counts), "
                         "4) Use project-specific details (Parquet sources, Redshift, Airflow, etl/validators.py), "
                         "5) Recommend preventive measures (assertions, validation rules).",
    },
    # --- Scenario 5: Research hypothesis design (matches hypothesis-formulation + experiment-design-rigor) ---
    {
        "id": "research_hypothesis",
        "description": "Formulating research hypothesis with project-specific experiment context",
        "memories": [
            MemoryUnit(
                memory_id="mem_res_1", scope_id="default",
                memory_type=MemoryType.PROJECT_STATE, status=MemoryStatus.ACTIVE,
                content="Current research: comparing RAG vs fine-tuning for domain-specific QA. "
                        "RAG baseline uses FAISS with bge-base-en embeddings, top-k=5 retrieval. "
                        "Fine-tuned model: Llama-3.1-8B on 8K domain QA pairs. "
                        "RAG accuracy: 64.2%, Fine-tuned accuracy: 71.8% on 500-sample test set.",
                summary="RAG (FAISS+bge, 64.2%) vs Fine-tuned (Llama-3.1-8B, 71.8%), 500 test samples",
                entities=["FAISS", "bge-base-en", "Llama-3.1-8B", "RAG"],
                topics=["RAG", "fine-tuning", "QA", "comparison"],
                importance=0.9, confidence=0.9, source_session_id="day15",
            ),
            MemoryUnit(
                memory_id="mem_res_2", scope_id="default",
                memory_type=MemoryType.EPISODIC, status=MemoryStatus.ACTIVE,
                content="In day14, we found that RAG retrieval quality drops significantly for "
                        "questions requiring multi-hop reasoning (accuracy drops to 38%). "
                        "The retriever only fetches the most lexically similar chunks but misses "
                        "related context needed for reasoning chains.",
                summary="Day14: RAG multi-hop accuracy only 38%, retriever misses reasoning context",
                entities=["multi-hop", "retrieval quality", "reasoning chains"],
                topics=["RAG weakness", "multi-hop reasoning", "retrieval"],
                importance=0.85, confidence=0.9, source_session_id="day14",
            ),
            MemoryUnit(
                memory_id="mem_res_3", scope_id="default",
                memory_type=MemoryType.SEMANTIC, status=MemoryStatus.ACTIVE,
                content="Evaluation framework: accuracy (exact match), F1, and human eval on 50-sample subset. "
                        "Human eval rubric: relevance (0-3), completeness (0-3), factual correctness (0-3). "
                        "Statistical significance: paired t-test, p < 0.05 across 3 random seeds.",
                summary="Eval: accuracy + F1 + human eval, paired t-test p<0.05, 3 seeds",
                entities=["human eval", "paired t-test", "F1"],
                topics=["evaluation", "statistical testing", "metrics"],
                importance=0.8, confidence=0.95, source_session_id="day13",
            ),
        ],
        "task": "We're considering combining RAG with fine-tuning (RAG-augmented fine-tuning) to get the "
                "best of both approaches. Help me formulate rigorous research hypotheses and design "
                "the experiment plan for this.",
        "expected_keywords": ["hypothesis", "null", "baseline", "RAG", "fine-tun", "64.2", "71.8", "multi-hop", "p-value", "seeds"],
        "eval_criteria": "A good response should: "
                         "1) Formulate clear, falsifiable hypotheses with null hypotheses, "
                         "2) Reference current baselines (RAG 64.2%, fine-tuned 71.8%), "
                         "3) Address the known RAG weakness (multi-hop reasoning at 38%), "
                         "4) Design proper experimental controls (ablations, multiple seeds, significance tests), "
                         "5) Use existing evaluation framework (accuracy, F1, human eval, paired t-test). "
                         "Memory provides experiment context, skill provides hypothesis methodology.",
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
        skills_dir = "memory_data/skills"
    return SkillManager(skills_dir=skills_dir, retrieval_mode="template")


def compute_keyword_recall(response: str, expected: list[str]) -> float:
    """Fraction of expected keywords found in response (case-insensitive)."""
    if not expected:
        return 1.0
    response_lower = response.lower()
    found = sum(1 for kw in expected if kw.lower() in response_lower)
    return found / len(expected)


def build_synergy_prompt(memory_text: str, skills: list[dict]) -> str:
    """Build skill-aware structured template with actionable tips.

    Extracts 1-line actionable summaries from matched skills.
    No full skill content injection.
    """
    skill_steps = []
    for s in skills[:3]:
        content = s.get("content", "")
        bold_actions = re.findall(r'\d+\.\s+\*\*([^*]+)\*\*', content)
        name = s.get("name", "").replace("-", " ")
        if bold_actions:
            steps = " → ".join(a.strip() for a in bold_actions[:5])
            skill_steps.append(steps)
        else:
            # Fall back to key questions or anti-patterns
            key_q = re.findall(r'[-*]\s+\*\*([^*]+)\*\*', content)
            if key_q:
                steps = " → ".join(a.strip() for a in key_q[:5])
                skill_steps.append(steps)
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


def prm_score(task: str, response: str, criteria: str, judge_model: str = JUDGE_MODEL) -> dict:
    """Multi-criteria LLM-as-judge evaluation (0-10).

    Returns dict with individual dimension scores and weighted average.
    """
    if not response.strip():
        return {"methodology": 0, "specificity": 0, "completeness": 0, "actionability": 0, "weighted": 0}

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

    result = call_llm(
        [
            {"role": "system", "content": "You are a precise evaluator. Follow the output format exactly."},
            {"role": "user", "content": judge_prompt},
        ],
        model=judge_model,
        max_tokens=JUDGE_MAX_TOKENS,
    )

    dimensions = {}
    for dim in ["Methodology", "Specificity", "Completeness", "Actionability", "Weighted"]:
        match = re.search(rf'{dim}:\s*(\d+(?:\.\d+)?)\s*/\s*10', result)
        if match:
            dimensions[dim.lower()] = min(float(match.group(1)), 10.0)

    if "weighted" in dimensions:
        return dimensions

    weights = {"methodology": 0.20, "specificity": 0.35, "completeness": 0.25, "actionability": 0.20}
    if len(dimensions) >= 3:
        total = sum(dimensions.get(d, 5.0) * w for d, w in weights.items())
        dimensions["weighted"] = round(total, 1)
        return dimensions

    # Fallback
    match = re.search(r'(\d+(?:\.\d+)?)\s*/\s*10', result)
    if match:
        val = min(float(match.group(1)), 10.0)
        return {"methodology": val, "specificity": val, "completeness": val, "actionability": val, "weighted": val}
    return {"methodology": 5, "specificity": 5, "completeness": 5, "actionability": 5, "weighted": 5}


def run_single_trial(
    scenario: dict,
    model_name: str,
    model_id: str,
    max_tokens: int,
    skill_manager: SkillManager,
    trial_num: int,
) -> dict:
    """Run one trial of one scenario for one model across 3 modes."""
    task = scenario["task"]
    expected_kw = scenario["expected_keywords"]
    memories = scenario["memories"]
    trial_results = {}

    # --- Mode 1: Baseline ---
    print(f"    [{model_name}][{scenario['id']}][trial {trial_num}] baseline...", end=" ", flush=True)
    resp = call_llm(
        [{"role": "system", "content": "You are a helpful software engineer assistant."},
         {"role": "user", "content": task}],
        model=model_id, max_tokens=max_tokens,
    )
    recall = compute_keyword_recall(resp, expected_kw)
    print(f"recall={recall:.2f} len={len(resp)}")
    trial_results["baseline"] = {
        "response": resp, "recall": recall, "response_len": len(resp),
    }
    time.sleep(3)

    # --- Mode 2: Memory-only ---
    print(f"    [{model_name}][{scenario['id']}][trial {trial_num}] memory_only...", end=" ", flush=True)
    mm = setup_memory_store(memories)
    mem_units = mm.retrieve_for_prompt(task, scope_id="default")
    memory_text = mm.render_for_prompt(mem_units) if mem_units else ""

    memory_system = f"You are a helpful assistant.\n\n{memory_text}" if memory_text else "You are a helpful assistant."
    resp = call_llm(
        [{"role": "system", "content": memory_system},
         {"role": "user", "content": task}],
        model=model_id, max_tokens=max_tokens,
    )
    recall = compute_keyword_recall(resp, expected_kw)
    print(f"recall={recall:.2f} len={len(resp)}")
    trial_results["memory_only"] = {
        "response": resp, "recall": recall, "response_len": len(resp),
        "memory_count": len(mem_units), "memory_tokens": len(memory_text.split()),
    }
    time.sleep(3)

    # --- Mode 3: Synergy (template-only) ---
    print(f"    [{model_name}][{scenario['id']}][trial {trial_num}] synergy...", end=" ", flush=True)
    relevant_skills = skill_manager.retrieve_relevant(task, top_k=5, min_relevance=0.07)
    relevant_skill_names = [s.get("name", "?") for s in relevant_skills]

    mm2 = setup_memory_store(memories)

    if len(relevant_skills) < 2:
        # Fallback to plain memory
        synergy_mem_units = mm2.retrieve_for_prompt(task, scope_id="default")
        synergy_memory_text = mm2.render_for_prompt(synergy_mem_units) if synergy_mem_units else ""
        synergy_system = f"You are a helpful assistant.\n\n{synergy_memory_text}" if synergy_memory_text else "You are a helpful assistant."
        total_tokens = len(synergy_memory_text.split())
        used_template = False
    else:
        synergy_mem_units = mm2.retrieve_for_prompt(task, scope_id="default")
        synergy_memory_text = mm2.render_for_prompt(synergy_mem_units) if synergy_mem_units else ""
        synergy_prompt = build_synergy_prompt(synergy_memory_text, relevant_skills)
        synergy_system = f"You are a helpful assistant.\n\n{synergy_prompt}"
        total_tokens = len(synergy_prompt.split())
        used_template = True

    resp = call_llm(
        [{"role": "system", "content": synergy_system},
         {"role": "user", "content": task}],
        model=model_id, max_tokens=max_tokens,
    )
    recall = compute_keyword_recall(resp, expected_kw)
    print(f"recall={recall:.2f} len={len(resp)} skills={relevant_skill_names[:3]} template={used_template}")
    trial_results["synergy"] = {
        "response": resp, "recall": recall, "response_len": len(resp),
        "memory_count": len(synergy_mem_units),
        "skill_count": len(relevant_skills),
        "skill_names": relevant_skill_names,
        "total_aug_tokens": total_tokens,
        "used_template": used_template,
    }
    time.sleep(3)

    return trial_results


def run_prm_for_trial(scenario: dict, trial_results: dict) -> dict:
    """Run PRM scoring for one trial's results."""
    prm_results = {}
    for mode in ["baseline", "memory_only", "synergy"]:
        resp = trial_results[mode]["response"]
        if not resp:
            prm_results[mode] = {"methodology": 0, "specificity": 0, "completeness": 0, "actionability": 0, "weighted": 0}
            continue
        scores = prm_score(scenario["task"], resp, scenario["eval_criteria"])
        prm_results[mode] = scores
        time.sleep(2)
    return prm_results


def main():
    start_time = datetime.now()
    print("=" * 70)
    print("LARGE-SCALE MULTI-MODEL SYNERGY EXPERIMENT")
    print(f"Time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Models: {', '.join(m[0] for m in MODELS)}")
    print(f"Scenarios: {len(SCENARIOS)}")
    print(f"Trials per config: {TRIALS}")
    print(f"Total API calls: ~{len(MODELS) * len(SCENARIOS) * 3 * TRIALS + len(MODELS) * len(SCENARIOS) * 3 * TRIALS}")
    print("=" * 70)

    skill_manager = setup_skill_manager()
    print(f"Skills loaded: {skill_manager.get_skill_count()}")

    # Quick check: which scenarios will get synergy template
    print("\nSkill relevance check:")
    for sc in SCENARIOS:
        relevant = skill_manager.retrieve_relevant(sc["task"], top_k=5, min_relevance=0.07)
        names = [s.get("name", "?") for s in relevant]
        template = "YES" if len(relevant) >= 2 else "NO (fallback to memory)"
        print(f"  {sc['id']}: {len(relevant)} skills {names[:3]} → template={template}")

    # Collect all results
    all_results = {}  # model → scenario → trial → mode → data

    for model_name, model_id, max_tokens in MODELS:
        if SKIP_GPT54 and model_name == "gpt-5.4":
            print(f"\n  Skipping gpt-5.4 (already tested, SKIP_GPT54=True)")
            continue

        print(f"\n{'='*70}")
        print(f"MODEL: {model_name} ({model_id})")
        print(f"{'='*70}")

        # Quick availability check
        test_resp = call_llm(
            [{"role": "user", "content": "Say OK"}],
            model=model_id, max_tokens=50, retries=2,
        )
        if not test_resp:
            print(f"  SKIPPING {model_name} — model unavailable or erroring")
            continue
        print(f"  Model verified OK")

        all_results[model_name] = {}

        for scenario in SCENARIOS:
            all_results[model_name][scenario["id"]] = {}

            for trial in range(1, TRIALS + 1):
                print(f"\n  --- {scenario['id']} trial {trial}/{TRIALS} ---")
                try:
                    trial_data = run_single_trial(
                        scenario, model_name, model_id, max_tokens,
                        skill_manager, trial,
                    )
                    # Run PRM scoring
                    prm = run_prm_for_trial(scenario, trial_data)
                    # Merge PRM into trial data
                    for mode in ["baseline", "memory_only", "synergy"]:
                        trial_data[mode]["prm"] = prm[mode]
                        trial_data[mode]["prm_weighted"] = prm[mode]["weighted"]

                    all_results[model_name][scenario["id"]][f"trial_{trial}"] = trial_data
                except Exception as e:
                    print(f"    ERROR: {e}")
                    traceback.print_exc()
                    all_results[model_name][scenario["id"]][f"trial_{trial}"] = {"error": str(e)}

    # ===================== Aggregate & Report =====================
    print(f"\n\n{'='*70}")
    print("AGGREGATED RESULTS")
    print(f"{'='*70}\n")

    # Build summary table
    summary_rows = []
    model_mode_scores = {}  # (model, mode) → list of PRM scores

    for model_name in [m[0] for m in MODELS]:
        model_data = all_results.get(model_name, {})
        for scenario in SCENARIOS:
            sc_data = model_data.get(scenario["id"], {})
            for mode in ["baseline", "memory_only", "synergy"]:
                scores = []
                recalls = []
                for trial_key, trial_data in sc_data.items():
                    if "error" in trial_data:
                        continue
                    if mode in trial_data:
                        s = trial_data[mode].get("prm_weighted", 0)
                        r = trial_data[mode].get("recall", 0)
                        scores.append(s)
                        recalls.append(r)
                if scores:
                    avg_prm = sum(scores) / len(scores)
                    avg_recall = sum(recalls) / len(recalls)
                    summary_rows.append({
                        "model": model_name,
                        "scenario": scenario["id"],
                        "mode": mode,
                        "avg_prm": avg_prm,
                        "avg_recall": avg_recall,
                        "n_trials": len(scores),
                        "individual_prm": scores,
                    })
                    key = (model_name, mode)
                    if key not in model_mode_scores:
                        model_mode_scores[key] = []
                    model_mode_scores[key].extend(scores)

    # Print per-scenario table
    print(f"{'Model':<14} {'Scenario':<25} {'Mode':<14} {'PRM':>6} {'Recall':>7} {'Trials':>6}")
    print("-" * 75)
    for row in summary_rows:
        print(f"{row['model']:<14} {row['scenario']:<25} {row['mode']:<14} "
              f"{row['avg_prm']:>6.1f} {row['avg_recall']:>7.2f} {row['n_trials']:>6}")

    # Print per-model aggregates
    print(f"\n{'='*70}")
    print("PER-MODEL AGGREGATE (across all scenarios)")
    print(f"{'='*70}")
    print(f"{'Model':<14} {'baseline':>10} {'memory':>10} {'synergy':>10} {'Δ(syn-mem)':>12} {'1+1>2?':>8}")
    print("-" * 65)

    model_summary = {}
    for model_name, _, _ in MODELS:
        base_scores = model_mode_scores.get((model_name, "baseline"), [])
        mem_scores = model_mode_scores.get((model_name, "memory_only"), [])
        syn_scores = model_mode_scores.get((model_name, "synergy"), [])

        avg_base = sum(base_scores) / len(base_scores) if base_scores else 0
        avg_mem = sum(mem_scores) / len(mem_scores) if mem_scores else 0
        avg_syn = sum(syn_scores) / len(syn_scores) if syn_scores else 0
        delta = avg_syn - avg_mem
        is_better = "YES" if avg_syn > avg_mem + 0.05 else ("TIE" if abs(delta) <= 0.05 else "NO")

        print(f"{model_name:<14} {avg_base:>10.2f} {avg_mem:>10.2f} {avg_syn:>10.2f} "
              f"{delta:>+12.2f} {is_better:>8}")

        model_summary[model_name] = {
            "avg_baseline": round(avg_base, 2),
            "avg_memory": round(avg_mem, 2),
            "avg_synergy": round(avg_syn, 2),
            "delta_synergy_vs_memory": round(delta, 2),
            "one_plus_one_gt_two": is_better,
        }

    # Find best model for synergy
    best_delta_model = max(model_summary.items(), key=lambda x: x[1]["delta_synergy_vs_memory"])
    print(f"\nBest synergy model: {best_delta_model[0]} "
          f"(Δ = {best_delta_model[1]['delta_synergy_vs_memory']:+.2f})")

    # ===================== Save Results =====================
    output_dir = Path("records/synergy_results")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save full results
    timestamp = start_time.strftime("%Y%m%d_%H%M%S")
    full_path = output_dir / f"multimodel_{timestamp}.json"

    # Strip full response text to save space (keep preview)
    save_data = {}
    for model_name in all_results:
        save_data[model_name] = {}
        for sc_id in all_results[model_name]:
            save_data[model_name][sc_id] = {}
            for trial_key in all_results[model_name][sc_id]:
                trial = all_results[model_name][sc_id][trial_key]
                if "error" in trial:
                    save_data[model_name][sc_id][trial_key] = trial
                    continue
                save_data[model_name][sc_id][trial_key] = {}
                for mode in ["baseline", "memory_only", "synergy"]:
                    if mode not in trial:
                        continue
                    d = dict(trial[mode])
                    d["response_preview"] = d.pop("response", "")[:500]
                    save_data[model_name][sc_id][trial_key][mode] = d

    report = {
        "timestamp": start_time.isoformat(),
        "duration_seconds": (datetime.now() - start_time).total_seconds(),
        "config": {
            "models": [m[0] for m in MODELS],
            "scenarios": [s["id"] for s in SCENARIOS],
            "trials": TRIALS,
            "judge_model": JUDGE_MODEL,
        },
        "model_summary": model_summary,
        "per_scenario": summary_rows,
        "raw_data": save_data,
    }

    with open(full_path, "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False, default=str)
    print(f"\nFull results saved to: {full_path}")

    elapsed = (datetime.now() - start_time).total_seconds()
    print(f"\nTotal time: {elapsed/60:.1f} minutes")

    return report


if __name__ == "__main__":
    main()
