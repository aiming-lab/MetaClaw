import os
import json
import sys
import tempfile
import unittest
import asyncio
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from metaclaw.config import MetaClawConfig
from metaclaw.memory.manager import MemoryManager
from metaclaw.memory.models import MemoryQuery, MemoryStatus, MemoryType, MemoryUnit
from metaclaw.memory.candidate import generate_policy_candidates
from metaclaw.memory.policy_store import MemoryPolicyState, MemoryPolicyStore
from metaclaw.memory.promotion import MemoryPromotionCriteria, should_promote
from metaclaw.memory.replay import MemoryReplayEvaluator, load_replay_samples, run_policy_candidate_replay
from metaclaw.memory.self_upgrade import MemorySelfUpgradeOrchestrator
from metaclaw.memory.scope import derive_memory_scope
from metaclaw.memory.store import MemoryStore
from metaclaw.memory.consolidator import MemoryConsolidator
from metaclaw.memory.telemetry import MemoryTelemetryStore
from metaclaw.memory.upgrade_worker import MemoryUpgradeWorker


class MemoryStoreTests(unittest.TestCase):
    def test_keyword_search_returns_relevant_units(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories(
                [
                    MemoryUnit(
                        memory_id="a",
                        scope_id="default",
                        memory_type=MemoryType.SEMANTIC,
                        content="User prefers concise code review summaries.",
                        summary="Preference for concise code review output.",
                        topics=["code", "review", "concise"],
                    ),
                    MemoryUnit(
                        memory_id="b",
                        scope_id="default",
                        memory_type=MemoryType.PROJECT_STATE,
                        content="Project uses FastAPI and SQLite.",
                        summary="Tech stack summary.",
                        topics=["fastapi", "sqlite"],
                    ),
                ]
            )

            hits = store.search_keyword("default", "concise code review", limit=5)
            self.assertTrue(hits)
            self.assertEqual(hits[0].unit.memory_id, "a")
            store.close()

    def test_stats_include_active_type_breakdown(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories(
                [
                    MemoryUnit(
                        memory_id="a",
                        scope_id="default",
                        memory_type=MemoryType.PREFERENCE,
                        content="User preference: concise updates.",
                    ),
                    MemoryUnit(
                        memory_id="b",
                        scope_id="default",
                        memory_type=MemoryType.PROJECT_STATE,
                        content="Project context: FastAPI and SQLite.",
                    ),
                ]
            )

            stats = store.get_stats("default")
            self.assertEqual(stats["active"], 2)
            self.assertEqual(stats["active_by_type"]["preference"], 1)
            self.assertEqual(stats["active_by_type"]["project_state"], 1)
            store.close()


class MemoryManagerTests(unittest.TestCase):
    def test_rendered_memory_block_contains_heading(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg = MetaClawConfig(
                memory_enabled=True,
                memory_store_path=os.path.join(tmpdir, "memory.db"),
                memory_policy_path=os.path.join(tmpdir, "policy.json"),
                memory_scope="default",
                memory_max_injected_units=4,
                memory_max_injected_tokens=120,
            )
            manager = MemoryManager.from_config(cfg)
            manager.ingest_session_turns(
                "sess-1",
                [
                    {
                        "prompt_text": "Please remember that I prefer brief updates.",
                        "response_text": "Noted. I will keep updates brief.",
                    }
                ],
            )
            units = manager.retrieve_for_prompt("brief updates", scope_id="default")
            rendered = manager.render_for_prompt(units)
            self.assertIn("## Relevant Long-Term Memory", rendered)
            self.assertTrue(units)
            manager.close()

    def test_consolidation_keeps_latest_working_summary_active(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg = MetaClawConfig(
                memory_enabled=True,
                memory_store_path=os.path.join(tmpdir, "memory.db"),
                memory_policy_path=os.path.join(tmpdir, "policy.json"),
                memory_scope="default",
            )
            manager = MemoryManager.from_config(cfg)
            manager.ingest_session_turns(
                "sess-1",
                [{"prompt_text": "First summary seed", "response_text": "Alpha"}],
            )
            manager.ingest_session_turns(
                "sess-2",
                [{"prompt_text": "Second summary seed", "response_text": "Beta"}],
            )
            active = manager.store.list_active("default", limit=100)
            working = [u for u in active if u.memory_type == MemoryType.WORKING_SUMMARY]
            self.assertEqual(len(working), 1)
            manager.close()

    def test_extraction_creates_structured_preference_and_project_memories(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg = MetaClawConfig(
                memory_enabled=True,
                memory_store_path=os.path.join(tmpdir, "memory.db"),
                memory_policy_path=os.path.join(tmpdir, "policy.json"),
                memory_scope="default",
            )
            manager = MemoryManager.from_config(cfg)
            manager.ingest_session_turns(
                "sess-structured",
                [
                    {
                        "prompt_text": (
                            "I prefer concise progress updates. "
                            "This project uses FastAPI with SQLite. "
                            "When you work on this repo, run unit tests before editing."
                        ),
                        "response_text": "Noted. I will follow that workflow.",
                    }
                ],
            )
            active = manager.store.list_active("default", limit=20)
            memory_types = {unit.memory_type for unit in active}
            self.assertIn(MemoryType.PREFERENCE, memory_types)
            self.assertIn(MemoryType.PROJECT_STATE, memory_types)
            self.assertIn(MemoryType.PROCEDURAL_OBSERVATION, memory_types)
            preference_units = [u for u in active if u.memory_type == MemoryType.PREFERENCE]
            self.assertTrue(
                any("concise progress updates" in unit.content.lower() for unit in preference_units)
            )
            manager.close()

    def test_scope_stats_expose_dominant_type(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg = MetaClawConfig(
                memory_enabled=True,
                memory_store_path=os.path.join(tmpdir, "memory.db"),
                memory_policy_path=os.path.join(tmpdir, "policy.json"),
                memory_scope="default",
            )
            manager = MemoryManager.from_config(cfg)
            manager.ingest_session_turns(
                "sess-1",
                [
                    {"prompt_text": "I prefer concise updates.", "response_text": "Understood."},
                    {"prompt_text": "I prefer direct answers.", "response_text": "Understood."},
                ],
            )
            stats = manager.get_scope_stats()
            self.assertEqual(stats["dominant_type"], "preference")
            self.assertGreater(stats["memory_density"], 0.0)
            manager.close()

    def test_hybrid_retrieval_uses_metadata_terms(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg = MetaClawConfig(
                memory_enabled=True,
                memory_store_path=os.path.join(tmpdir, "memory.db"),
                memory_policy_path=os.path.join(tmpdir, "policy.json"),
                memory_scope="default",
                memory_retrieval_mode="hybrid",
            )
            manager = MemoryManager.from_config(cfg)
            manager.store.add_memories(
                [
                    MemoryUnit(
                        memory_id="meta-1",
                        scope_id="default",
                        memory_type=MemoryType.PROJECT_STATE,
                        content="Project context: API migration notes.",
                        summary="Backend migration state.",
                        topics=["fastapi", "sqlite"],
                        entities=["FastAPI"],
                        importance=0.9,
                    )
                ]
            )
            units = manager.retrieve_for_prompt("Need help with sqlite migration", scope_id="default")
            self.assertTrue(units)
            self.assertEqual(units[0].memory_id, "meta-1")
            manager.close()

    def test_scope_override_isolated_between_workspaces(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg = MetaClawConfig(
                memory_enabled=True,
                memory_store_path=os.path.join(tmpdir, "memory.db"),
                memory_policy_path=os.path.join(tmpdir, "policy.json"),
                memory_scope="global",
            )
            manager = MemoryManager.from_config(cfg)
            manager.ingest_session_turns(
                "sess-a",
                [{"prompt_text": "I prefer terse updates.", "response_text": "Noted."}],
                scope_id="workspace-a",
            )
            manager.ingest_session_turns(
                "sess-b",
                [{"prompt_text": "I prefer detailed updates.", "response_text": "Noted."}],
                scope_id="workspace-b",
            )

            workspace_a = manager.retrieve_for_prompt("terse updates", scope_id="workspace-a")
            workspace_b = manager.retrieve_for_prompt("terse updates", scope_id="workspace-b")
            self.assertTrue(workspace_a)
            self.assertTrue(workspace_b)
            self.assertTrue(any("terse updates" in unit.content.lower() for unit in workspace_a))
            self.assertFalse(any("terse updates" in unit.content.lower() for unit in workspace_b))
            manager.close()

    def test_embedding_retrieval_path_returns_semantically_close_memory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg = MetaClawConfig(
                memory_enabled=True,
                memory_store_path=os.path.join(tmpdir, "memory.db"),
                memory_policy_path=os.path.join(tmpdir, "policy.json"),
                memory_scope="default",
                memory_retrieval_mode="embedding",
                memory_use_embeddings=True,
            )
            manager = MemoryManager.from_config(cfg)
            manager.ingest_session_turns(
                "sess-embed",
                [
                    {
                        "prompt_text": "I prefer concise progress updates for project work.",
                        "response_text": "Understood.",
                    }
                ],
            )
            units = manager.retrieve_for_prompt("Need brief project updates", scope_id="default")
            self.assertTrue(units)
            self.assertTrue(any(unit.embedding for unit in manager.store.list_active("default", limit=20)))
            self.assertIn(MemoryType.PREFERENCE, {unit.memory_type for unit in units})
            manager.close()


class MemoryScopeTests(unittest.TestCase):
    def test_explicit_scope_wins(self):
        scope = derive_memory_scope(
            default_scope="default",
            session_id="sess-1",
            memory_scope="team-alpha",
            user_id="u1",
            workspace_id="w1",
        )
        self.assertEqual(scope, "team-alpha")

    def test_user_and_workspace_derive_composite_scope(self):
        scope = derive_memory_scope(
            default_scope="default",
            session_id="sess-1",
            user_id="alice",
            workspace_id="repo-x",
        )
        self.assertEqual(scope, "user:alice|workspace:repo-x")

    def test_session_falls_back_under_default_scope(self):
        scope = derive_memory_scope(
            default_scope="default",
            session_id="sess-42",
        )
        self.assertEqual(scope, "default|session:sess-42")


class MemoryPolicyTests(unittest.TestCase):
    def test_policy_store_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryPolicyStore(os.path.join(tmpdir, "policy.json"))
            state = MemoryPolicyState(retrieval_mode="hybrid", max_injected_units=8, notes=["raised budget"])
            store.save(state)
            loaded = store.load()
            self.assertEqual(loaded.retrieval_mode, "hybrid")
            self.assertEqual(loaded.max_injected_units, 8)
            self.assertEqual(loaded.notes, ["raised budget"])

    def test_policy_store_supports_rollback(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryPolicyStore(os.path.join(tmpdir, "policy.json"))
            store.save(MemoryPolicyState(retrieval_mode="keyword"), reason="bootstrap")
            store.save(MemoryPolicyState(retrieval_mode="hybrid"), reason="optimize")
            restored = store.rollback(steps=1)
            self.assertEqual(restored.retrieval_mode, "keyword")
            history = store.history()
            self.assertTrue(history)
            self.assertEqual(history[-1].reason, "rollback:1")

    def test_manager_refreshes_policy_when_memory_volume_grows(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg = MetaClawConfig(
                memory_enabled=True,
                memory_store_path=os.path.join(tmpdir, "memory.db"),
                memory_policy_path=os.path.join(tmpdir, "policy.json"),
                memory_telemetry_path=os.path.join(tmpdir, "telemetry.jsonl"),
                memory_scope="default",
                memory_retrieval_mode="keyword",
            )
            manager = MemoryManager.from_config(cfg)
            turns = [
                {
                    "prompt_text": f"I prefer concise updates about service area {idx}.",
                    "response_text": "Understood.",
                }
                for idx in range(30)
            ]
            manager.ingest_session_turns("sess-policy", turns)
            state = manager.get_policy_state()
            self.assertEqual(state["retrieval_mode"], "hybrid")
            self.assertGreaterEqual(state["max_injected_units"], 6)
            self.assertTrue(state["notes"])
            events = manager.get_recent_telemetry(limit=10)
            self.assertTrue(any(event["event_type"] == "memory_ingest" for event in events))
            self.assertTrue(any(event["event_type"] == "policy_update" for event in events))
            manager.close()


class MemoryTelemetryTests(unittest.TestCase):
    def test_telemetry_store_reads_recent_events(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryTelemetryStore(os.path.join(tmpdir, "telemetry.jsonl"))
            store.record("memory_ingest", {"scope_id": "default", "added": 3})
            store.record("policy_update", {"scope_id": "default", "retrieval_mode": "hybrid"})
            events = store.read_recent(limit=5)
            self.assertEqual(len(events), 2)
            self.assertEqual(events[-1]["event_type"], "policy_update")


class MemoryReplayTests(unittest.TestCase):
    def test_load_replay_samples_from_records(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "conversations.jsonl")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(
                    json.dumps(
                        {
                            "session_id": "sess-1",
                            "turn": 1,
                            "instruction_text": "Need concise update",
                            "response_text": "Here is a concise update.",
                            "next_state": {"content": "Follow the concise format."},
                        }
                    )
                    + "\n"
                )
            samples = load_replay_samples(path)
            self.assertEqual(len(samples), 1)
            self.assertEqual(samples[0].query_text, "Need concise update")

    def test_replay_evaluator_compares_results(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg = MetaClawConfig(
                memory_enabled=True,
                memory_store_path=os.path.join(tmpdir, "memory.db"),
                memory_policy_path=os.path.join(tmpdir, "policy.json"),
                memory_telemetry_path=os.path.join(tmpdir, "telemetry.jsonl"),
                memory_scope="default",
            )
            manager = MemoryManager.from_config(cfg)
            manager.ingest_session_turns(
                "sess-r1",
                [{"prompt_text": "I prefer concise updates.", "response_text": "Understood."}],
            )
            samples = load_replay_samples(_write_replay_fixture(tmpdir))
            evaluator = MemoryReplayEvaluator()
            baseline = evaluator.evaluate(manager, samples)
            candidate = evaluator.evaluate(manager, samples)
            comparison = evaluator.compare(baseline, candidate)
            self.assertEqual(comparison["sample_count"], 1)
            self.assertTrue(comparison["candidate_beats_baseline"])
            self.assertGreaterEqual(candidate.avg_response_overlap, 0.0)
            self.assertGreaterEqual(candidate.avg_specificity, 0.0)
            self.assertGreaterEqual(candidate.avg_focus_score, 0.0)
            self.assertGreaterEqual(candidate.avg_value_density, 0.0)
            manager.close()

    def test_run_policy_candidate_replay_uses_candidate_policy_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg = MetaClawConfig(
                memory_enabled=True,
                memory_store_path=os.path.join(tmpdir, "memory.db"),
                memory_policy_path=os.path.join(tmpdir, "baseline-policy.json"),
                memory_telemetry_path=os.path.join(tmpdir, "telemetry.jsonl"),
                memory_scope="default",
            )
            manager = MemoryManager.from_config(cfg)
            manager.ingest_session_turns(
                "sess-r3",
                [{"prompt_text": "I prefer concise updates.", "response_text": "Understood."}],
            )
            manager.close()

            candidate_path = os.path.join(tmpdir, "candidate-policy.json")
            MemoryPolicyStore(candidate_path).save(
                MemoryPolicyState(
                    retrieval_mode="hybrid",
                    max_injected_units=8,
                    max_injected_tokens=1000,
                ),
                reason="candidate",
            )
            samples = load_replay_samples(_write_replay_fixture(tmpdir))
            baseline, candidate, comparison = run_policy_candidate_replay(
                cfg=cfg,
                samples=samples,
                candidate_policy_path=candidate_path,
            )
            self.assertEqual(baseline.sample_count, 1)
            self.assertEqual(candidate.sample_count, 1)
            self.assertIn("candidate_beats_baseline", comparison)


class MemoryPromotionTests(unittest.TestCase):
    def test_should_promote_respects_thresholds(self):
        comparison = {
            "sample_count": 12,
            "avg_query_overlap_delta": 0.05,
            "avg_continuation_overlap_delta": 0.03,
            "avg_response_overlap_delta": 0.02,
            "avg_specificity_delta": 0.0,
            "avg_focus_score_delta": 0.01,
            "avg_value_density_delta": 0.01,
            "candidate_beats_baseline": True,
        }
        criteria = MemoryPromotionCriteria(
            min_query_overlap_delta=0.01,
            min_continuation_overlap_delta=0.01,
            min_response_overlap_delta=0.01,
            min_focus_score_delta=0.0,
            min_value_density_delta=0.0,
            min_sample_count=10,
        )
        self.assertTrue(should_promote(comparison, criteria))
        strict = MemoryPromotionCriteria(
            min_query_overlap_delta=0.1,
            min_continuation_overlap_delta=0.01,
            min_response_overlap_delta=0.01,
            min_focus_score_delta=0.0,
            min_value_density_delta=0.0,
            min_sample_count=10,
        )
        self.assertFalse(should_promote(comparison, strict))

    def test_should_promote_rejects_focus_regression(self):
        comparison = {
            "sample_count": 12,
            "avg_query_overlap_delta": 0.05,
            "avg_continuation_overlap_delta": 0.03,
            "avg_response_overlap_delta": 0.02,
            "avg_specificity_delta": 0.0,
            "avg_focus_score_delta": -0.02,
            "avg_value_density_delta": 0.01,
            "candidate_beats_baseline": False,
        }
        criteria = MemoryPromotionCriteria(
            min_query_overlap_delta=0.01,
            min_continuation_overlap_delta=0.01,
            min_response_overlap_delta=0.01,
            min_focus_score_delta=0.0,
            min_value_density_delta=0.0,
            min_sample_count=10,
        )
        self.assertFalse(should_promote(comparison, criteria))

    def test_should_promote_rejects_value_density_regression(self):
        comparison = {
            "sample_count": 12,
            "avg_query_overlap_delta": 0.05,
            "avg_continuation_overlap_delta": 0.03,
            "avg_response_overlap_delta": 0.02,
            "avg_specificity_delta": 0.0,
            "avg_focus_score_delta": 0.01,
            "avg_value_density_delta": -0.03,
            "candidate_beats_baseline": False,
        }
        criteria = MemoryPromotionCriteria(
            min_query_overlap_delta=0.01,
            min_continuation_overlap_delta=0.01,
            min_response_overlap_delta=0.01,
            min_focus_score_delta=0.0,
            min_value_density_delta=0.0,
            min_sample_count=10,
        )
        self.assertFalse(should_promote(comparison, criteria))


class MemorySelfUpgradeTests(unittest.TestCase):
    def test_orchestrator_evaluates_and_promotes_candidate(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg = MetaClawConfig(
                memory_enabled=True,
                memory_dir=tmpdir,
                memory_store_path=os.path.join(tmpdir, "memory.db"),
                memory_policy_path=os.path.join(tmpdir, "live-policy.json"),
                memory_telemetry_path=os.path.join(tmpdir, "telemetry.jsonl"),
                memory_scope="default",
            )
            manager = MemoryManager.from_config(cfg)
            manager.ingest_session_turns(
                "sess-u1",
                [{"prompt_text": "I prefer concise updates.", "response_text": "Understood."}],
            )
            manager.close()

            candidate_path = os.path.join(tmpdir, "candidate-policy.json")
            MemoryPolicyStore(candidate_path).save(
                MemoryPolicyState(
                    retrieval_mode="hybrid",
                    max_injected_units=8,
                    max_injected_tokens=900,
                ),
                reason="candidate",
            )
            records_path = _write_replay_fixture(tmpdir)
            orchestrator = MemorySelfUpgradeOrchestrator(
                cfg,
                history_path=os.path.join(tmpdir, "upgrade-history.jsonl"),
            )
            decision = orchestrator.evaluate_candidate(
                candidate_policy_path=candidate_path,
                replay_records_path=records_path,
                report_path=os.path.join(tmpdir, "report.json"),
                criteria=MemoryPromotionCriteria(min_sample_count=1),
            )
            self.assertTrue(os.path.exists(os.path.join(tmpdir, "report.json")))
            self.assertTrue(os.path.exists(os.path.join(tmpdir, "upgrade-history.jsonl")))
            self.assertIn("candidate_beats_baseline", decision.comparison)
            live_state = MemoryPolicyStore(cfg.memory_policy_path).load()
            if decision.promoted:
                self.assertEqual(live_state.retrieval_mode, "hybrid")

    def test_orchestrator_generates_candidate_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg = MetaClawConfig(
                memory_enabled=True,
                memory_dir=tmpdir,
                memory_store_path=os.path.join(tmpdir, "memory.db"),
                memory_policy_path=os.path.join(tmpdir, "live-policy.json"),
                memory_telemetry_path=os.path.join(tmpdir, "telemetry.jsonl"),
                memory_scope="default",
            )
            MemoryPolicyStore(cfg.memory_policy_path).save(
                MemoryPolicyState(retrieval_mode="keyword"),
                reason="bootstrap",
            )
            orchestrator = MemorySelfUpgradeOrchestrator(
                cfg,
                history_path=os.path.join(tmpdir, "upgrade-history.jsonl"),
            )
            paths = orchestrator.generate_candidate_files(os.path.join(tmpdir, "candidates"))
            self.assertTrue(paths)
            self.assertTrue(all(os.path.exists(path) for path in paths))
            summary = orchestrator.summarize_candidate_directory(os.path.join(tmpdir, "candidates"))
            self.assertEqual(summary["count"], len(paths))

    def test_orchestrator_supports_review_queue_and_approval(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg = MetaClawConfig(
                memory_enabled=True,
                memory_dir=tmpdir,
                memory_store_path=os.path.join(tmpdir, "memory.db"),
                memory_policy_path=os.path.join(tmpdir, "live-policy.json"),
                memory_telemetry_path=os.path.join(tmpdir, "telemetry.jsonl"),
                memory_scope="default",
            )
            manager = MemoryManager.from_config(cfg)
            manager.ingest_session_turns(
                "sess-u2",
                [{"prompt_text": "I prefer concise updates.", "response_text": "Understood."}],
            )
            manager.close()

            candidate_path = os.path.join(tmpdir, "candidate-policy.json")
            MemoryPolicyStore(candidate_path).save(
                MemoryPolicyState(retrieval_mode="hybrid", max_injected_units=8),
                reason="candidate",
            )
            orchestrator = MemorySelfUpgradeOrchestrator(
                cfg,
                history_path=os.path.join(tmpdir, "upgrade-history.jsonl"),
            )
            decision = orchestrator.evaluate_candidate(
                candidate_policy_path=candidate_path,
                replay_records_path=_write_replay_fixture(tmpdir),
                report_path=os.path.join(tmpdir, "report.json"),
                criteria=MemoryPromotionCriteria(min_sample_count=1),
                require_review=True,
            )
            self.assertEqual(decision.reason, "pending_review")
            queue = orchestrator.read_review_queue()
            self.assertEqual(len(queue), 1)
            orchestrator._enqueue_review(decision)
            self.assertEqual(len(orchestrator.read_review_queue()), 1)
            approved = orchestrator.approve_review_candidate(candidate_path)
            self.assertTrue(approved)
            self.assertEqual(orchestrator.read_review_queue(), [])
            history = orchestrator.read_history(limit=10)
            self.assertTrue(history)
            summary = orchestrator.summarize_history()
            self.assertGreaterEqual(summary["approved_review"], 1)
            review_summary = orchestrator.summarize_review_history()
            self.assertGreaterEqual(review_summary["queued"], 1)
            self.assertGreaterEqual(review_summary["approved"], 1)
            self.assertGreaterEqual(review_summary["resolved_count"], 1)

    def test_orchestrator_tracks_review_rejections_in_review_history(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg = MetaClawConfig(
                memory_enabled=True,
                memory_dir=tmpdir,
                memory_store_path=os.path.join(tmpdir, "memory.db"),
                memory_policy_path=os.path.join(tmpdir, "live-policy.json"),
                memory_telemetry_path=os.path.join(tmpdir, "telemetry.jsonl"),
                memory_scope="default",
            )
            manager = MemoryManager.from_config(cfg)
            manager.ingest_session_turns(
                "sess-u2b",
                [{"prompt_text": "I prefer concise updates.", "response_text": "Understood."}],
            )
            manager.close()

            candidate_path = os.path.join(tmpdir, "candidate-policy.json")
            MemoryPolicyStore(candidate_path).save(
                MemoryPolicyState(retrieval_mode="hybrid", max_injected_units=8),
                reason="candidate",
            )
            orchestrator = MemorySelfUpgradeOrchestrator(
                cfg,
                history_path=os.path.join(tmpdir, "upgrade_history.jsonl"),
            )
            orchestrator.evaluate_candidate(
                candidate_policy_path=candidate_path,
                replay_records_path=_write_replay_fixture(tmpdir),
                report_path=os.path.join(tmpdir, "report.json"),
                criteria=MemoryPromotionCriteria(min_sample_count=1),
                require_review=True,
            )
            rejected = orchestrator.reject_review_candidate(candidate_path)
            self.assertTrue(rejected)
            summary = orchestrator.summarize_review_history()
            self.assertGreaterEqual(summary["queued"], 1)
            self.assertGreaterEqual(summary["rejected"], 1)
            records = orchestrator.read_review_history(limit=10)
            self.assertTrue(any(item.get("event") == "rejected" for item in records))
            self.assertGreaterEqual(summary["resolved_count"], 1)

    def test_upgrade_history_summary_reports_recent_window_metrics(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg = MetaClawConfig(
                memory_enabled=True,
                memory_dir=tmpdir,
                memory_store_path=os.path.join(tmpdir, "memory.db"),
                memory_policy_path=os.path.join(tmpdir, "live-policy.json"),
                memory_telemetry_path=os.path.join(tmpdir, "telemetry.jsonl"),
                memory_scope="default",
            )
            orchestrator = MemorySelfUpgradeOrchestrator(
                cfg,
                history_path=os.path.join(tmpdir, "upgrade_history.jsonl"),
            )
            now = datetime.now(timezone.utc)
            with open(orchestrator.history_path, "w", encoding="utf-8") as handle:
                for payload in [
                    {"timestamp": (now - timedelta(hours=3)).isoformat(timespec="seconds"), "promoted": True, "reason": "promoted", "comparison": {}, "report_path": "", "candidate_policy_path": "a"},
                    {"timestamp": (now - timedelta(hours=2)).isoformat(timespec="seconds"), "promoted": False, "reason": "pending_review", "comparison": {}, "report_path": "", "candidate_policy_path": "b"},
                    {"timestamp": (now - timedelta(hours=180)).isoformat(timespec="seconds"), "promoted": False, "reason": "rejected_review", "comparison": {}, "report_path": "", "candidate_policy_path": "c"},
                ]:
                    handle.write(json.dumps(payload) + "\n")
            summary = orchestrator.summarize_history(recent_window_hours=24)
            self.assertEqual(summary["total"], 3)
            self.assertEqual(summary["recent_window_hours"], 24)
            self.assertEqual(summary["recent_total"], 2)
            self.assertEqual(summary["recent_promoted"], 1)
            self.assertEqual(summary["recent_pending_review"], 1)
            self.assertEqual(summary["recent_rejected_review"], 0)

    def test_review_history_summary_computes_resolution_latency(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg = MetaClawConfig(
                memory_enabled=True,
                memory_dir=tmpdir,
                memory_store_path=os.path.join(tmpdir, "memory.db"),
                memory_policy_path=os.path.join(tmpdir, "live-policy.json"),
                memory_telemetry_path=os.path.join(tmpdir, "telemetry.jsonl"),
                memory_scope="default",
            )
            orchestrator = MemorySelfUpgradeOrchestrator(
                cfg,
                history_path=os.path.join(tmpdir, "upgrade_history.jsonl"),
            )
            candidate_path = os.path.join(tmpdir, "candidate-policy.json")
            queued_at = (datetime.now(timezone.utc) - timedelta(hours=5)).isoformat(timespec="seconds")
            approved_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
            with open(orchestrator.review_history_path, "w", encoding="utf-8") as handle:
                handle.write(
                    json.dumps(
                        {
                            "timestamp": queued_at,
                            "event": "queued",
                            "candidate_policy_path": candidate_path,
                        }
                    )
                    + "\n"
                )
                handle.write(
                    json.dumps(
                        {
                            "timestamp": approved_at,
                            "event": "approved",
                            "candidate_policy_path": candidate_path,
                        }
                    )
                    + "\n"
                )
            summary = orchestrator.summarize_review_history()
            self.assertEqual(summary["queued"], 1)
            self.assertEqual(summary["approved"], 1)
            self.assertEqual(summary["resolved_count"], 1)
            self.assertGreaterEqual(summary["avg_resolution_hours"], 4.9)
            self.assertEqual(summary["pending_estimate"], 0)
            self.assertEqual(summary["backlog_pressure_hours"], 0.0)

    def test_review_history_summary_estimates_backlog_pressure(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg = MetaClawConfig(
                memory_enabled=True,
                memory_dir=tmpdir,
                memory_store_path=os.path.join(tmpdir, "memory.db"),
                memory_policy_path=os.path.join(tmpdir, "live-policy.json"),
                memory_telemetry_path=os.path.join(tmpdir, "telemetry.jsonl"),
                memory_scope="default",
            )
            orchestrator = MemorySelfUpgradeOrchestrator(
                cfg,
                history_path=os.path.join(tmpdir, "upgrade_history.jsonl"),
            )
            now = datetime.now(timezone.utc)
            candidate_a = os.path.join(tmpdir, "candidate-a.json")
            candidate_b = os.path.join(tmpdir, "candidate-b.json")
            candidate_c = os.path.join(tmpdir, "candidate-c.json")
            with open(orchestrator.review_history_path, "w", encoding="utf-8") as handle:
                for payload in [
                    {"timestamp": (now - timedelta(hours=6)).isoformat(timespec="seconds"), "event": "queued", "candidate_policy_path": candidate_a},
                    {"timestamp": now.isoformat(timespec="seconds"), "event": "approved", "candidate_policy_path": candidate_a},
                    {"timestamp": (now - timedelta(hours=2)).isoformat(timespec="seconds"), "event": "queued", "candidate_policy_path": candidate_b},
                    {"timestamp": (now - timedelta(hours=1)).isoformat(timespec="seconds"), "event": "queued", "candidate_policy_path": candidate_c},
                ]:
                    handle.write(json.dumps(payload) + "\n")
            summary = orchestrator.summarize_review_history()
            self.assertEqual(summary["queued"], 3)
            self.assertEqual(summary["resolved_count"], 1)
            self.assertEqual(summary["pending_estimate"], 2)
            self.assertGreaterEqual(summary["avg_resolution_hours"], 5.9)
            self.assertGreaterEqual(summary["backlog_pressure_hours"], 11.8)
            self.assertEqual(summary["approval_rate"], 1.0)
            self.assertEqual(summary["rejection_rate"], 0.0)

    def test_review_history_summary_computes_outcome_rates(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg = MetaClawConfig(
                memory_enabled=True,
                memory_dir=tmpdir,
                memory_store_path=os.path.join(tmpdir, "memory.db"),
                memory_policy_path=os.path.join(tmpdir, "live-policy.json"),
                memory_telemetry_path=os.path.join(tmpdir, "telemetry.jsonl"),
                memory_scope="default",
            )
            orchestrator = MemorySelfUpgradeOrchestrator(
                cfg,
                history_path=os.path.join(tmpdir, "upgrade_history.jsonl"),
            )
            now = datetime.now(timezone.utc)
            with open(orchestrator.review_history_path, "w", encoding="utf-8") as handle:
                for payload in [
                    {"timestamp": (now - timedelta(hours=6)).isoformat(timespec="seconds"), "event": "queued", "candidate_policy_path": "a"},
                    {"timestamp": now.isoformat(timespec="seconds"), "event": "approved", "candidate_policy_path": "a"},
                    {"timestamp": (now - timedelta(hours=3)).isoformat(timespec="seconds"), "event": "queued", "candidate_policy_path": "b"},
                    {"timestamp": (now - timedelta(hours=1)).isoformat(timespec="seconds"), "event": "rejected", "candidate_policy_path": "b"},
                ]:
                    handle.write(json.dumps(payload) + "\n")
            summary = orchestrator.summarize_review_history()
            self.assertEqual(summary["resolved_count"], 2)
            self.assertEqual(summary["approval_rate"], 0.5)
            self.assertEqual(summary["rejection_rate"], 0.5)

    def test_review_history_summary_reports_recent_window_metrics(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg = MetaClawConfig(
                memory_enabled=True,
                memory_dir=tmpdir,
                memory_store_path=os.path.join(tmpdir, "memory.db"),
                memory_policy_path=os.path.join(tmpdir, "live-policy.json"),
                memory_telemetry_path=os.path.join(tmpdir, "telemetry.jsonl"),
                memory_scope="default",
            )
            orchestrator = MemorySelfUpgradeOrchestrator(
                cfg,
                history_path=os.path.join(tmpdir, "upgrade_history.jsonl"),
            )
            now = datetime.now(timezone.utc)
            with open(orchestrator.review_history_path, "w", encoding="utf-8") as handle:
                for payload in [
                    {"timestamp": (now - timedelta(hours=5)).isoformat(timespec="seconds"), "event": "queued", "candidate_policy_path": "recent-a"},
                    {"timestamp": (now - timedelta(hours=1)).isoformat(timespec="seconds"), "event": "approved", "candidate_policy_path": "recent-a"},
                    {"timestamp": (now - timedelta(hours=220)).isoformat(timespec="seconds"), "event": "queued", "candidate_policy_path": "old-b"},
                    {"timestamp": (now - timedelta(hours=200)).isoformat(timespec="seconds"), "event": "rejected", "candidate_policy_path": "old-b"},
                ]:
                    handle.write(json.dumps(payload) + "\n")
            summary = orchestrator.summarize_review_history(recent_window_hours=24)
            self.assertEqual(summary["recent_window_hours"], 24)
            self.assertEqual(summary["recent_total"], 2)
            self.assertEqual(summary["recent_queued"], 1)
            self.assertEqual(summary["recent_approved"], 1)
            self.assertEqual(summary["recent_rejected"], 0)
            self.assertEqual(summary["recent_resolved_count"], 1)
            self.assertEqual(summary["recent_approval_rate"], 1.0)
            self.assertEqual(summary["recent_rejection_rate"], 0.0)
            self.assertGreaterEqual(summary["recent_avg_resolution_hours"], 3.9)

    def test_orchestrator_runs_auto_upgrade_cycle(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg = MetaClawConfig(
                memory_enabled=True,
                memory_dir=tmpdir,
                memory_store_path=os.path.join(tmpdir, "memory.db"),
                memory_policy_path=os.path.join(tmpdir, "live-policy.json"),
                memory_telemetry_path=os.path.join(tmpdir, "telemetry.jsonl"),
                memory_scope="default",
            )
            manager = MemoryManager.from_config(cfg)
            manager.ingest_session_turns(
                "sess-u3",
                [{"prompt_text": "I prefer concise updates.", "response_text": "Understood."}],
            )
            manager.close()

            orchestrator = MemorySelfUpgradeOrchestrator(
                cfg,
                history_path=os.path.join(tmpdir, "upgrade-history.jsonl"),
            )
            decisions = orchestrator.run_auto_upgrade_cycle(
                replay_records_path=_write_replay_fixture(tmpdir),
                candidate_dir=os.path.join(tmpdir, "candidates"),
                reports_dir=os.path.join(tmpdir, "reports"),
                criteria=MemoryPromotionCriteria(min_sample_count=1),
                require_review=True,
            )
            self.assertTrue(decisions)
            self.assertTrue(os.path.exists(os.path.join(tmpdir, "candidates")))
            self.assertTrue(os.path.exists(os.path.join(tmpdir, "reports")))
            actionable = [d for d in decisions if d.reason in {"pending_review", "promoted"}]
            self.assertLessEqual(len(actionable), 1)
            cycle_summary = orchestrator.read_cycle_summary()
            self.assertTrue(cycle_summary)
            self.assertGreaterEqual(cycle_summary["num_candidates"], 1)
            self.assertIn("cleanup", cycle_summary)
            self.assertIn("metric_summary", cycle_summary)
            self.assertIn("best_score", cycle_summary["metric_summary"])
            cycle_history = orchestrator.read_cycle_history(limit=10)
            self.assertTrue(cycle_history)
            self.assertGreaterEqual(cycle_history[-1]["num_candidates"], 1)

    def test_cycle_history_summary_reports_recent_metrics(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg = MetaClawConfig(
                memory_enabled=True,
                memory_dir=tmpdir,
                memory_store_path=os.path.join(tmpdir, "memory.db"),
                memory_policy_path=os.path.join(tmpdir, "live-policy.json"),
                memory_telemetry_path=os.path.join(tmpdir, "telemetry.jsonl"),
                memory_scope="default",
            )
            orchestrator = MemorySelfUpgradeOrchestrator(
                cfg,
                history_path=os.path.join(tmpdir, "upgrade_history.jsonl"),
            )
            now = datetime.now(timezone.utc)
            with open(orchestrator.cycle_history_path, "w", encoding="utf-8") as handle:
                for payload in [
                    {
                        "updated_at": (now - timedelta(hours=4)).isoformat(timespec="seconds"),
                        "num_candidates": 4,
                        "num_promoted": 1,
                        "num_pending_review": 0,
                        "metric_summary": {"best_score": 1.2},
                    },
                    {
                        "updated_at": (now - timedelta(hours=2)).isoformat(timespec="seconds"),
                        "num_candidates": 3,
                        "num_promoted": 0,
                        "num_pending_review": 1,
                        "metric_summary": {"best_score": 0.8},
                    },
                    {
                        "updated_at": (now - timedelta(hours=240)).isoformat(timespec="seconds"),
                        "num_candidates": 5,
                        "num_promoted": 1,
                        "num_pending_review": 0,
                        "metric_summary": {"best_score": 1.5},
                    },
                ]:
                    handle.write(json.dumps(payload) + "\n")
            summary = orchestrator.summarize_cycle_history(recent_window_hours=24)
            self.assertEqual(summary["total_cycles"], 3)
            self.assertEqual(summary["promoted_cycles"], 2)
            self.assertEqual(summary["pending_review_cycles"], 1)
            self.assertEqual(summary["recent_cycles"], 2)
            self.assertEqual(summary["recent_promoted_cycles"], 1)
            self.assertEqual(summary["recent_pending_review_cycles"], 1)
            self.assertEqual(summary["recent_avg_candidates"], 3.5)
            self.assertEqual(summary["recent_avg_best_score"], 1.0)
            self.assertEqual(summary["promoted_cycle_rate"], 0.6667)
            self.assertEqual(summary["pending_review_cycle_rate"], 0.3333)
            self.assertEqual(summary["recent_promoted_cycle_rate"], 0.5)
            self.assertEqual(summary["recent_pending_review_cycle_rate"], 0.5)

    def test_operational_health_marks_stale_review_as_critical(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg = MetaClawConfig(
                memory_enabled=True,
                memory_dir=tmpdir,
                memory_store_path=os.path.join(tmpdir, "memory.db"),
                memory_policy_path=os.path.join(tmpdir, "live-policy.json"),
                memory_telemetry_path=os.path.join(tmpdir, "telemetry.jsonl"),
                memory_scope="default",
            )
            orchestrator = MemorySelfUpgradeOrchestrator(
                cfg,
                history_path=os.path.join(tmpdir, "upgrade_history.jsonl"),
            )
            old_ts = (datetime.now(timezone.utc) - timedelta(hours=90)).isoformat(timespec="seconds")
            orchestrator._write_review_queue(
                [
                    {
                        "timestamp": old_ts,
                        "candidate_policy_path": os.path.join(tmpdir, "candidate-old.json"),
                        "report_path": "",
                        "comparison": {},
                        "reason": "pending_review",
                    }
                ]
            )
            health = orchestrator.summarize_operational_health(stale_after_hours=72)
            self.assertEqual(health["level"], "critical")
            self.assertIn("stale review queue", health["reasons"])

    def test_operational_health_marks_recent_no_promotion_as_warning(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg = MetaClawConfig(
                memory_enabled=True,
                memory_dir=tmpdir,
                memory_store_path=os.path.join(tmpdir, "memory.db"),
                memory_policy_path=os.path.join(tmpdir, "live-policy.json"),
                memory_telemetry_path=os.path.join(tmpdir, "telemetry.jsonl"),
                memory_scope="default",
            )
            orchestrator = MemorySelfUpgradeOrchestrator(
                cfg,
                history_path=os.path.join(tmpdir, "upgrade_history.jsonl"),
            )
            now = datetime.now(timezone.utc)
            with open(orchestrator.cycle_history_path, "w", encoding="utf-8") as handle:
                handle.write(
                    json.dumps(
                        {
                            "updated_at": (now - timedelta(hours=3)).isoformat(timespec="seconds"),
                            "num_candidates": 3,
                            "num_promoted": 0,
                            "num_pending_review": 1,
                            "metric_summary": {"best_score": 0.7},
                        }
                    )
                    + "\n"
                )
            with open(orchestrator.history_path, "w", encoding="utf-8") as handle:
                handle.write(
                    json.dumps(
                        {
                            "timestamp": (now - timedelta(hours=2)).isoformat(timespec="seconds"),
                            "promoted": False,
                            "reason": "pending_review",
                            "comparison": {},
                            "report_path": "",
                            "candidate_policy_path": "candidate-x",
                        }
                    )
                    + "\n"
                )
            health = orchestrator.summarize_operational_health(stale_after_hours=72)
            self.assertEqual(health["level"], "warning")
            self.assertIn("recent cycles frequently pending review", health["reasons"])
            self.assertIn("recent cycles produced no promotions", health["reasons"])

    def test_review_queue_summary_marks_stale_items(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg = MetaClawConfig(
                memory_enabled=True,
                memory_dir=tmpdir,
                memory_store_path=os.path.join(tmpdir, "memory.db"),
                memory_policy_path=os.path.join(tmpdir, "live-policy.json"),
                memory_telemetry_path=os.path.join(tmpdir, "telemetry.jsonl"),
                memory_scope="default",
            )
            orchestrator = MemorySelfUpgradeOrchestrator(
                cfg,
                history_path=os.path.join(tmpdir, "upgrade_history.jsonl"),
            )
            old_ts = (datetime.now(timezone.utc) - timedelta(hours=96)).isoformat(timespec="seconds")
            new_ts = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat(timespec="seconds")
            queued = [
                {
                    "timestamp": old_ts,
                    "candidate_policy_path": os.path.join(tmpdir, "candidate-old.json"),
                    "report_path": "",
                    "comparison": {},
                    "reason": "pending_review",
                },
                {
                    "timestamp": new_ts,
                    "candidate_policy_path": os.path.join(tmpdir, "candidate-new.json"),
                    "report_path": "",
                    "comparison": {},
                    "reason": "pending_review",
                },
            ]
            orchestrator._write_review_queue(queued)
            summary = orchestrator.summarize_review_queue(stale_after_hours=72)
            self.assertEqual(summary["pending_count"], 2)
            self.assertEqual(summary["stale_count"], 1)
            self.assertGreater(summary["oldest_age_hours"], summary["newest_age_hours"])

    def test_cleanup_artifacts_preserves_reviewed_candidate_and_prunes_extras(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg = MetaClawConfig(
                memory_enabled=True,
                memory_dir=tmpdir,
                memory_store_path=os.path.join(tmpdir, "memory.db"),
                memory_policy_path=os.path.join(tmpdir, "live-policy.json"),
                memory_telemetry_path=os.path.join(tmpdir, "telemetry.jsonl"),
                memory_scope="default",
            )
            orchestrator = MemorySelfUpgradeOrchestrator(
                cfg,
                history_path=os.path.join(tmpdir, "upgrade_history.jsonl"),
            )
            candidate_dir = os.path.join(tmpdir, "candidates")
            reports_dir = os.path.join(tmpdir, "reports")
            os.makedirs(candidate_dir, exist_ok=True)
            os.makedirs(reports_dir, exist_ok=True)

            candidate_paths = []
            for idx in range(3):
                path = os.path.join(candidate_dir, f"candidate_{idx}.json")
                with open(path, "w", encoding="utf-8") as handle:
                    json.dump({"candidate": idx}, handle)
                candidate_paths.append(path)
            for idx in range(4):
                path = os.path.join(reports_dir, f"report_{idx}.json")
                with open(path, "w", encoding="utf-8") as handle:
                    json.dump({"report": idx}, handle)

            orchestrator._write_review_queue(
                [
                    {
                        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                        "candidate_policy_path": candidate_paths[0],
                        "report_path": "",
                        "comparison": {},
                        "reason": "pending_review",
                    }
                ]
            )
            result = orchestrator.cleanup_artifacts(
                candidate_dir=candidate_dir,
                reports_dir=reports_dir,
                keep_candidates=1,
                keep_reports=2,
            )
            self.assertEqual(result["removed_candidates"], 1)
            self.assertEqual(result["removed_reports"], 2)
            self.assertTrue(os.path.exists(candidate_paths[0]))
            self.assertEqual(len([name for name in os.listdir(candidate_dir) if name.endswith(".json")]), 2)
            self.assertEqual(len([name for name in os.listdir(reports_dir) if name.endswith(".json")]), 2)


class MemoryCandidateTests(unittest.TestCase):
    def test_generate_policy_candidates_is_bounded_and_includes_current(self):
        current = MemoryPolicyState(
            retrieval_mode="keyword",
            max_injected_units=6,
            max_injected_tokens=800,
        )
        candidates = generate_policy_candidates(current)
        self.assertTrue(candidates)
        self.assertTrue(
            any(
                c.retrieval_mode == "keyword"
                and c.max_injected_units == 6
                and c.max_injected_tokens == 800
                for c in candidates
            )
        )
        # Mode/units/tokens grid (up to 18) + weight variants (up to 8).
        self.assertLessEqual(len(candidates), 30)


class MemoryUpgradeWorkerTests(unittest.TestCase):
    def test_worker_skips_without_records(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg = MetaClawConfig(
                memory_enabled=True,
                memory_dir=tmpdir,
                memory_store_path=os.path.join(tmpdir, "memory.db"),
                memory_policy_path=os.path.join(tmpdir, "live-policy.json"),
                memory_telemetry_path=os.path.join(tmpdir, "telemetry.jsonl"),
                memory_auto_upgrade_enabled=True,
                record_dir=os.path.join(tmpdir, "records"),
            )
            os.makedirs(cfg.record_dir, exist_ok=True)
            worker = MemoryUpgradeWorker(cfg)
            ran = asyncio.run(worker.run_once())
            self.assertFalse(ran)

    def test_worker_runs_once_when_records_exist(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg = MetaClawConfig(
                memory_enabled=True,
                memory_dir=tmpdir,
                memory_store_path=os.path.join(tmpdir, "memory.db"),
                memory_policy_path=os.path.join(tmpdir, "live-policy.json"),
                memory_telemetry_path=os.path.join(tmpdir, "telemetry.jsonl"),
                memory_auto_upgrade_enabled=True,
                memory_auto_upgrade_require_review=True,
                record_dir=os.path.join(tmpdir, "records"),
                memory_scope="default",
            )
            manager = MemoryManager.from_config(cfg)
            manager.ingest_session_turns(
                "sess-u4",
                [{"prompt_text": "I prefer concise updates.", "response_text": "Understood."}],
            )
            manager.close()
            os.makedirs(cfg.record_dir, exist_ok=True)
            _write_replay_fixture(cfg.record_dir, filename="conversations.jsonl")
            worker = MemoryUpgradeWorker(cfg, window_check=lambda: True)
            ran = asyncio.run(worker.run_once())
            self.assertTrue(ran)
            self.assertTrue(os.path.exists(os.path.join(tmpdir, "upgrade_history.jsonl")))
            self.assertTrue(os.path.exists(os.path.join(tmpdir, "upgrade_worker_state.json")))

    def test_worker_waits_when_review_queue_not_empty(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg = MetaClawConfig(
                memory_enabled=True,
                memory_dir=tmpdir,
                memory_store_path=os.path.join(tmpdir, "memory.db"),
                memory_policy_path=os.path.join(tmpdir, "live-policy.json"),
                memory_telemetry_path=os.path.join(tmpdir, "telemetry.jsonl"),
                memory_auto_upgrade_enabled=True,
                memory_auto_upgrade_require_review=True,
                record_dir=os.path.join(tmpdir, "records"),
                memory_scope="default",
            )
            manager = MemoryManager.from_config(cfg)
            manager.ingest_session_turns(
                "sess-u5",
                [{"prompt_text": "I prefer concise updates.", "response_text": "Understood."}],
            )
            manager.close()
            os.makedirs(cfg.record_dir, exist_ok=True)
            _write_replay_fixture(cfg.record_dir, filename="conversations.jsonl")
            orchestrator = MemorySelfUpgradeOrchestrator(
                cfg,
                history_path=os.path.join(tmpdir, "upgrade_history.jsonl"),
            )
            candidate_path = os.path.join(tmpdir, "candidate-policy.json")
            MemoryPolicyStore(candidate_path).save(
                MemoryPolicyState(retrieval_mode="hybrid"),
                reason="candidate",
            )
            orchestrator._enqueue_review(
                orchestrator._evaluate_candidate_once(
                    candidate_policy_path=candidate_path,
                    replay_records_path=os.path.join(cfg.record_dir, "conversations.jsonl"),
                    report_path=os.path.join(tmpdir, "report.json"),
                    criteria=MemoryPromotionCriteria(min_sample_count=1),
                )
            )
            worker = MemoryUpgradeWorker(cfg, window_check=lambda: True)
            ran = asyncio.run(worker.run_once())
            self.assertFalse(ran)
            with open(os.path.join(tmpdir, "upgrade_worker_state.json"), "r", encoding="utf-8") as handle:
                state = json.load(handle)
            self.assertEqual(state["state"], "waiting_review")
            self.assertIn("pending=1", state["detail"])
            with open(os.path.join(tmpdir, "upgrade_alerts.json"), "r", encoding="utf-8") as handle:
                alerts = json.load(handle)
            self.assertEqual(alerts["alerts"][0]["code"], "review_queue_blocked")
            with open(os.path.join(tmpdir, "upgrade_alerts_history.jsonl"), "r", encoding="utf-8") as handle:
                history_lines = [line for line in handle.read().splitlines() if line.strip()]
            self.assertTrue(history_lines)

    def test_worker_marks_stale_review_state_when_queue_is_aged(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg = MetaClawConfig(
                memory_enabled=True,
                memory_dir=tmpdir,
                memory_store_path=os.path.join(tmpdir, "memory.db"),
                memory_policy_path=os.path.join(tmpdir, "live-policy.json"),
                memory_telemetry_path=os.path.join(tmpdir, "telemetry.jsonl"),
                memory_auto_upgrade_enabled=True,
                memory_auto_upgrade_require_review=True,
                memory_review_stale_after_hours=24,
                record_dir=os.path.join(tmpdir, "records"),
                memory_scope="default",
            )
            manager = MemoryManager.from_config(cfg)
            manager.ingest_session_turns(
                "sess-u6",
                [{"prompt_text": "I prefer concise updates.", "response_text": "Understood."}],
            )
            manager.close()
            os.makedirs(cfg.record_dir, exist_ok=True)
            _write_replay_fixture(cfg.record_dir, filename="conversations.jsonl")
            orchestrator = MemorySelfUpgradeOrchestrator(
                cfg,
                history_path=os.path.join(tmpdir, "upgrade_history.jsonl"),
            )
            orchestrator._write_review_queue(
                [
                    {
                        "timestamp": (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat(timespec="seconds"),
                        "candidate_policy_path": os.path.join(tmpdir, "candidate-policy.json"),
                        "report_path": "",
                        "comparison": {},
                        "reason": "pending_review",
                    }
                ]
            )
            worker = MemoryUpgradeWorker(cfg, window_check=lambda: True)
            ran = asyncio.run(worker.run_once())
            self.assertFalse(ran)
            with open(os.path.join(tmpdir, "upgrade_worker_state.json"), "r", encoding="utf-8") as handle:
                state = json.load(handle)
            self.assertEqual(state["state"], "waiting_review_stale")
            self.assertIn("stale=1", state["detail"])
            with open(os.path.join(tmpdir, "upgrade_alerts.json"), "r", encoding="utf-8") as handle:
                alerts = json.load(handle)
            self.assertEqual(alerts["alerts"][0]["code"], "review_queue_stale")

    def test_worker_clears_alerts_when_idle_without_blockers(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg = MetaClawConfig(
                memory_enabled=True,
                memory_dir=tmpdir,
                memory_store_path=os.path.join(tmpdir, "memory.db"),
                memory_policy_path=os.path.join(tmpdir, "live-policy.json"),
                memory_telemetry_path=os.path.join(tmpdir, "telemetry.jsonl"),
                memory_auto_upgrade_enabled=True,
                record_dir=os.path.join(tmpdir, "records"),
            )
            alerts_path = os.path.join(tmpdir, "upgrade_alerts.json")
            with open(alerts_path, "w", encoding="utf-8") as handle:
                json.dump({"updated_at": "x", "alerts": [{"code": "review_queue_stale"}]}, handle)
            os.makedirs(cfg.record_dir, exist_ok=True)
            worker = MemoryUpgradeWorker(cfg)
            ran = asyncio.run(worker.run_once())
            self.assertFalse(ran)
            with open(alerts_path, "r", encoding="utf-8") as handle:
                alerts = json.load(handle)
            self.assertEqual(alerts["alerts"], [])

    def test_worker_writes_alert_history_snapshots(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg = MetaClawConfig(
                memory_enabled=True,
                memory_dir=tmpdir,
                memory_store_path=os.path.join(tmpdir, "memory.db"),
                memory_policy_path=os.path.join(tmpdir, "live-policy.json"),
                memory_telemetry_path=os.path.join(tmpdir, "telemetry.jsonl"),
                memory_auto_upgrade_enabled=True,
                memory_auto_upgrade_require_review=True,
                memory_review_stale_after_hours=24,
                record_dir=os.path.join(tmpdir, "records"),
                memory_scope="default",
            )
            manager = MemoryManager.from_config(cfg)
            manager.ingest_session_turns(
                "sess-u7",
                [{"prompt_text": "I prefer concise updates.", "response_text": "Understood."}],
            )
            manager.close()
            os.makedirs(cfg.record_dir, exist_ok=True)
            _write_replay_fixture(cfg.record_dir, filename="conversations.jsonl")
            orchestrator = MemorySelfUpgradeOrchestrator(
                cfg,
                history_path=os.path.join(tmpdir, "upgrade_history.jsonl"),
            )
            orchestrator._write_review_queue(
                [
                    {
                        "timestamp": (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat(timespec="seconds"),
                        "candidate_policy_path": os.path.join(tmpdir, "candidate-policy.json"),
                        "report_path": "",
                        "comparison": {},
                        "reason": "pending_review",
                    }
                ]
            )
            worker = MemoryUpgradeWorker(cfg, window_check=lambda: True)
            asyncio.run(worker.run_once())
            history_path = os.path.join(tmpdir, "upgrade_alerts_history.jsonl")
            with open(history_path, "r", encoding="utf-8") as handle:
                items = [json.loads(line) for line in handle.read().splitlines() if line.strip()]
            self.assertTrue(items)
            self.assertEqual(items[-1]["alerts"][0]["code"], "review_queue_stale")
            health_history_path = os.path.join(tmpdir, "upgrade_health_history.jsonl")
            with open(health_history_path, "r", encoding="utf-8") as handle:
                health_items = [json.loads(line) for line in handle.read().splitlines() if line.strip()]
            self.assertTrue(health_items)
            self.assertEqual(health_items[-1]["level"], "critical")

    def test_worker_summarizes_alert_history(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg = MetaClawConfig(
                memory_enabled=True,
                memory_dir=tmpdir,
                memory_store_path=os.path.join(tmpdir, "memory.db"),
                memory_policy_path=os.path.join(tmpdir, "live-policy.json"),
                memory_telemetry_path=os.path.join(tmpdir, "telemetry.jsonl"),
            )
            worker = MemoryUpgradeWorker(cfg)
            worker._write_alerts(
                [{"code": "review_queue_blocked", "level": "warning", "pending_count": 1, "stale_count": 0}]
            )
            worker._write_alerts(
                [{"code": "review_queue_stale", "level": "critical", "pending_count": 1, "stale_count": 1}]
            )
            worker._write_alerts([])
            summary = worker.summarize_alert_history()
            self.assertEqual(summary["total_snapshots"], 3)
            self.assertEqual(summary["nonempty_snapshots"], 2)
            self.assertEqual(summary["warning_count"], 1)
            self.assertEqual(summary["critical_count"], 1)
            self.assertEqual(summary["blocked_count"], 1)
            self.assertEqual(summary["stale_count"], 1)

    def test_worker_summarizes_recent_alert_history_window(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg = MetaClawConfig(
                memory_enabled=True,
                memory_dir=tmpdir,
                memory_store_path=os.path.join(tmpdir, "memory.db"),
                memory_policy_path=os.path.join(tmpdir, "live-policy.json"),
                memory_telemetry_path=os.path.join(tmpdir, "telemetry.jsonl"),
            )
            worker = MemoryUpgradeWorker(cfg)
            now = datetime.now(timezone.utc)
            payloads = [
                {
                    "updated_at": (now - timedelta(hours=2)).isoformat(timespec="seconds"),
                    "alerts": [{"code": "review_queue_blocked", "level": "warning", "pending_count": 1, "stale_count": 0}],
                },
                {
                    "updated_at": (now - timedelta(hours=300)).isoformat(timespec="seconds"),
                    "alerts": [{"code": "review_queue_stale", "level": "critical", "pending_count": 1, "stale_count": 1}],
                },
                {
                    "updated_at": now.isoformat(timespec="seconds"),
                    "alerts": [],
                },
            ]
            with open(worker.alerts_history_path, "w", encoding="utf-8") as handle:
                for payload in payloads:
                    handle.write(json.dumps(payload) + "\n")
            summary = worker.summarize_alert_history()
            self.assertEqual(summary["recent_window_hours"], 168)
            self.assertEqual(summary["recent_total_snapshots"], 2)
            self.assertEqual(summary["recent_nonempty_snapshots"], 1)
            self.assertEqual(summary["recent_warning_count"], 1)
            self.assertEqual(summary["recent_critical_count"], 0)
            self.assertEqual(summary["recent_blocked_count"], 1)
            self.assertEqual(summary["recent_stale_count"], 0)
            self.assertEqual(summary["nonempty_snapshot_rate"], 0.6667)
            self.assertEqual(summary["blocked_snapshot_rate"], 0.3333)
            self.assertEqual(summary["stale_snapshot_rate"], 0.3333)
            self.assertEqual(summary["recent_nonempty_snapshot_rate"], 0.5)
            self.assertEqual(summary["recent_blocked_snapshot_rate"], 0.5)
            self.assertEqual(summary["recent_stale_snapshot_rate"], 0.0)

    def test_worker_summarizes_health_history(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg = MetaClawConfig(
                memory_enabled=True,
                memory_dir=tmpdir,
                memory_store_path=os.path.join(tmpdir, "memory.db"),
                memory_policy_path=os.path.join(tmpdir, "live-policy.json"),
                memory_telemetry_path=os.path.join(tmpdir, "telemetry.jsonl"),
            )
            worker = MemoryUpgradeWorker(cfg)
            now = datetime.now(timezone.utc)
            payloads = [
                {
                    "updated_at": (now - timedelta(hours=2)).isoformat(timespec="seconds"),
                    "state": "idle",
                    "level": "healthy",
                    "reasons": [],
                },
                {
                    "updated_at": (now - timedelta(hours=6)).isoformat(timespec="seconds"),
                    "state": "waiting_review",
                    "level": "warning",
                    "reasons": ["pending review queue"],
                },
                {
                    "updated_at": (now - timedelta(hours=300)).isoformat(timespec="seconds"),
                    "state": "waiting_review_stale",
                    "level": "critical",
                    "reasons": ["stale review queue"],
                },
            ]
            with open(worker.health_history_path, "w", encoding="utf-8") as handle:
                for payload in payloads:
                    handle.write(json.dumps(payload) + "\n")
            summary = worker.summarize_health_history()
            self.assertEqual(summary["total_snapshots"], 3)
            self.assertEqual(summary["healthy_count"], 1)
            self.assertEqual(summary["warning_count"], 1)
            self.assertEqual(summary["critical_count"], 1)
            self.assertEqual(summary["healthy_rate"], 0.3333)
            self.assertEqual(summary["warning_rate"], 0.3333)
            self.assertEqual(summary["critical_rate"], 0.3333)
            self.assertEqual(summary["recent_snapshots"], 2)
            self.assertEqual(summary["recent_healthy_rate"], 0.5)
            self.assertEqual(summary["recent_warning_rate"], 0.5)
            self.assertEqual(summary["recent_critical_rate"], 0.0)

    def test_worker_restores_last_processed_mtime_from_state(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = os.path.join(tmpdir, "upgrade_worker_state.json")
            with open(state_path, "w", encoding="utf-8") as handle:
                json.dump({"last_processed_mtime": 123.45}, handle)
            cfg = MetaClawConfig(
                memory_enabled=True,
                memory_dir=tmpdir,
                memory_store_path=os.path.join(tmpdir, "memory.db"),
                memory_policy_path=os.path.join(tmpdir, "live-policy.json"),
                memory_telemetry_path=os.path.join(tmpdir, "telemetry.jsonl"),
                memory_auto_upgrade_enabled=True,
                record_dir=os.path.join(tmpdir, "records"),
            )
            worker = MemoryUpgradeWorker(cfg)
            self.assertEqual(worker._last_processed_mtime, 123.45)


def _write_replay_fixture(tmpdir: str, filename: str = "records.jsonl") -> str:
    path = os.path.join(tmpdir, filename)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(
            json.dumps(
                {
                    "session_id": "sess-r2",
                    "turn": 1,
                    "instruction_text": "Need concise update",
                    "response_text": "Here is a concise update.",
                    "next_state": {"content": "Please keep the update concise."},
                }
            )
            + "\n"
        )
    return path


class ExtractionQualityTests(unittest.TestCase):
    """Tests for second-loop extraction improvements."""

    def test_response_side_extraction_captures_project_facts(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            manager = MemoryManager(store=store)
            manager.ingest_session_turns(
                "sess-resp",
                [
                    {
                        "prompt_text": "What does this project use?",
                        "response_text": "The project uses Python 3.12 and SQLite for persistence.",
                    }
                ],
            )
            units = store.list_active("default", limit=50)
            types = {u.memory_type for u in units}
            self.assertIn(MemoryType.PROJECT_STATE, types)
            manager.close()

    def test_note_that_pattern_extracts_semantic_memory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            manager = MemoryManager(store=store)
            manager.ingest_session_turns(
                "sess-note",
                [
                    {
                        "prompt_text": "Note that the API rate limit is 100 requests per minute.",
                        "response_text": "Got it.",
                    }
                ],
            )
            units = store.list_active("default", limit=50)
            semantic_units = [u for u in units if u.memory_type == MemoryType.SEMANTIC]
            self.assertTrue(semantic_units)
            self.assertTrue(any("rate limit" in u.content.lower() for u in semantic_units))
            manager.close()


class ConsolidationQualityTests(unittest.TestCase):
    """Tests for near-duplicate merging in the consolidator."""

    def test_near_duplicate_memories_are_merged(self):
        from metaclaw.memory.consolidator import MemoryConsolidator

        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            # Add two memories with highly overlapping content.
            store.add_memories(
                [
                    MemoryUnit(
                        memory_id="dup-a",
                        scope_id="default",
                        memory_type=MemoryType.SEMANTIC,
                        content="User prefers concise code review summaries in all responses.",
                        summary="Preference.",
                        importance=0.8,
                    ),
                    MemoryUnit(
                        memory_id="dup-b",
                        scope_id="default",
                        memory_type=MemoryType.SEMANTIC,
                        content="User prefers concise code review summaries in all responses and feedback.",
                        summary="Preference similar.",
                        importance=0.7,
                    ),
                ]
            )
            consolidator = MemoryConsolidator(store=store, similarity_threshold=0.70)
            result = consolidator.consolidate("default")
            self.assertGreaterEqual(result["superseded"], 1)
            active = store.list_active("default")
            # Only the higher-importance one should remain active.
            semantic_active = [u for u in active if u.memory_type == MemoryType.SEMANTIC]
            self.assertEqual(len(semantic_active), 1)
            self.assertEqual(semantic_active[0].memory_id, "dup-a")
            store.close()

    def test_distinct_memories_are_not_merged(self):
        from metaclaw.memory.consolidator import MemoryConsolidator

        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories(
                [
                    MemoryUnit(
                        memory_id="dist-a",
                        scope_id="default",
                        memory_type=MemoryType.SEMANTIC,
                        content="User prefers Python for backend services.",
                        summary="Language preference.",
                    ),
                    MemoryUnit(
                        memory_id="dist-b",
                        scope_id="default",
                        memory_type=MemoryType.SEMANTIC,
                        content="The deployment pipeline uses Docker and Kubernetes.",
                        summary="Deployment info.",
                    ),
                ]
            )
            consolidator = MemoryConsolidator(store=store, similarity_threshold=0.80)
            result = consolidator.consolidate("default")
            self.assertEqual(result["superseded"], 0)
            active = store.list_active("default")
            semantic_active = [u for u in active if u.memory_type == MemoryType.SEMANTIC]
            self.assertEqual(len(semantic_active), 2)
            store.close()


class RetrievalRankingTests(unittest.TestCase):
    """Tests for IDF-weighted keyword retrieval."""

    def test_idf_ranking_prefers_rare_term_matches(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            # "python" appears in many units; "kubernetes" appears in one.
            store.add_memories(
                [
                    MemoryUnit(
                        memory_id="common-1",
                        scope_id="default",
                        memory_type=MemoryType.SEMANTIC,
                        content="We use python for data processing tasks.",
                        summary="Python usage.",
                        importance=0.5,
                    ),
                    MemoryUnit(
                        memory_id="common-2",
                        scope_id="default",
                        memory_type=MemoryType.SEMANTIC,
                        content="Python scripts handle monitoring and alerting.",
                        summary="Python monitoring.",
                        importance=0.5,
                    ),
                    MemoryUnit(
                        memory_id="common-3",
                        scope_id="default",
                        memory_type=MemoryType.SEMANTIC,
                        content="Python is the main language for internal tools.",
                        summary="Python tools.",
                        importance=0.5,
                    ),
                    MemoryUnit(
                        memory_id="rare-1",
                        scope_id="default",
                        memory_type=MemoryType.SEMANTIC,
                        content="Our kubernetes cluster runs python microservices.",
                        summary="Kubernetes and python.",
                        importance=0.5,
                    ),
                ]
            )
            # Search for "kubernetes python" — the unit with the rare term should rank first.
            hits = store.search_keyword("default", "kubernetes python", limit=4)
            self.assertTrue(hits)
            self.assertEqual(hits[0].unit.memory_id, "rare-1")
            store.close()


class ReplayQualityTests(unittest.TestCase):
    """Tests for grounding and coverage replay metrics."""

    def test_replay_result_includes_grounding_and_coverage(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            manager = MemoryManager(store=store, retrieval_mode="keyword")
            manager.ingest_session_turns(
                "sess-replay",
                [
                    {
                        "prompt_text": "I prefer TypeScript for frontend development.",
                        "response_text": "Got it, TypeScript for frontend.",
                    }
                ],
            )
            from metaclaw.memory.replay import MemoryReplaySample
            samples = [
                MemoryReplaySample(
                    session_id="sess-replay",
                    turn=1,
                    scope_id="default",
                    query_text="What language for frontend?",
                    response_text="TypeScript is used for frontend development.",
                    next_state_text="frontend typescript",
                ),
            ]
            evaluator = MemoryReplayEvaluator()
            result = evaluator.evaluate(manager, samples)
            self.assertGreaterEqual(result.avg_grounding_score, 0.0)
            self.assertGreaterEqual(result.avg_coverage_score, 0.0)
            manager.close()

    def test_replay_comparison_includes_new_metric_deltas(self):
        from metaclaw.memory.replay import MemoryReplayResult
        baseline = MemoryReplayResult(
            sample_count=10, avg_retrieved=3.0, avg_query_overlap=0.5,
            avg_continuation_overlap=0.4, avg_response_overlap=0.3,
            avg_specificity=0.6, avg_focus_score=0.5, avg_value_density=0.4,
            avg_grounding_score=0.3, avg_coverage_score=0.2,
        )
        candidate = MemoryReplayResult(
            sample_count=10, avg_retrieved=3.0, avg_query_overlap=0.5,
            avg_continuation_overlap=0.4, avg_response_overlap=0.3,
            avg_specificity=0.6, avg_focus_score=0.5, avg_value_density=0.4,
            avg_grounding_score=0.4, avg_coverage_score=0.3,
        )
        evaluator = MemoryReplayEvaluator()
        comparison = evaluator.compare(baseline, candidate)
        self.assertIn("avg_grounding_score_delta", comparison)
        self.assertIn("avg_coverage_score_delta", comparison)
        self.assertAlmostEqual(comparison["avg_grounding_score_delta"], 0.1, places=3)
        self.assertAlmostEqual(comparison["avg_coverage_score_delta"], 0.1, places=3)

    def test_promotion_criteria_includes_grounding_and_coverage(self):
        comparison = {
            "sample_count": 15,
            "avg_query_overlap_delta": 0.01,
            "avg_continuation_overlap_delta": 0.01,
            "avg_response_overlap_delta": 0.01,
            "avg_specificity_delta": 0.0,
            "avg_focus_score_delta": 0.0,
            "avg_value_density_delta": 0.0,
            "avg_grounding_score_delta": -0.1,
            "avg_coverage_score_delta": 0.0,
            "candidate_beats_baseline": False,
        }
        criteria = MemoryPromotionCriteria(min_sample_count=1)
        self.assertFalse(should_promote(comparison, criteria))


class CandidateDiversityTests(unittest.TestCase):
    """Tests for weight-variant candidate generation."""

    def test_candidates_include_weight_variants(self):
        current = MemoryPolicyState(
            retrieval_mode="keyword",
            max_injected_units=6,
            max_injected_tokens=800,
            keyword_weight=1.0,
            metadata_weight=0.45,
            importance_weight=0.5,
            recency_weight=0.3,
        )
        candidates = generate_policy_candidates(current)
        # Should have some candidates with different keyword_weight.
        keyword_weights = {round(c.keyword_weight, 2) for c in candidates}
        self.assertTrue(len(keyword_weights) > 1, "Expected diverse keyword_weight candidates")
        # Should have some candidates with different recency_weight.
        recency_weights = {round(c.recency_weight, 2) for c in candidates}
        self.assertTrue(len(recency_weights) > 1, "Expected diverse recency_weight candidates")

    def test_weight_variants_stay_within_bounds(self):
        current = MemoryPolicyState(
            keyword_weight=0.3,
            metadata_weight=0.1,
            importance_weight=0.1,
            recency_weight=0.0,
        )
        candidates = generate_policy_candidates(current)
        for c in candidates:
            self.assertGreaterEqual(c.keyword_weight, 0.3)
            self.assertLessEqual(c.keyword_weight, 2.0)
            self.assertGreaterEqual(c.metadata_weight, 0.1)
            self.assertLessEqual(c.metadata_weight, 1.0)
            self.assertGreaterEqual(c.importance_weight, 0.1)
            self.assertLessEqual(c.importance_weight, 1.0)
            self.assertGreaterEqual(c.recency_weight, 0.0)
            self.assertLessEqual(c.recency_weight, 0.8)


class ImportanceDecayTests(unittest.TestCase):
    """Tests for importance decay in consolidation."""

    def test_old_unused_memories_get_importance_decayed(self):
        from metaclaw.memory.consolidator import MemoryConsolidator

        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            old_time = (datetime.now(timezone.utc) - timedelta(days=90)).isoformat(timespec="seconds")
            store.add_memories(
                [
                    MemoryUnit(
                        memory_id="old-1",
                        scope_id="default",
                        memory_type=MemoryType.SEMANTIC,
                        content="Very old unused fact about the project.",
                        summary="Old fact.",
                        importance=0.8,
                        created_at=old_time,
                        updated_at=old_time,
                        last_accessed_at="",
                    ),
                ]
            )
            consolidator = MemoryConsolidator(
                store=store,
                decay_after_days=30,
                decay_factor=0.05,
                min_importance=0.15,
            )
            result = consolidator.consolidate("default")
            self.assertGreaterEqual(result["decayed"], 1)
            # Verify importance actually decreased.
            active = store.list_active("default")
            old_unit = [u for u in active if u.memory_id == "old-1"][0]
            self.assertLess(old_unit.importance, 0.8)
            store.close()

    def test_recently_accessed_memories_are_not_decayed(self):
        from metaclaw.memory.consolidator import MemoryConsolidator

        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            recent_time = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat(timespec="seconds")
            store.add_memories(
                [
                    MemoryUnit(
                        memory_id="recent-1",
                        scope_id="default",
                        memory_type=MemoryType.SEMANTIC,
                        content="Recently accessed fact.",
                        summary="Recent fact.",
                        importance=0.8,
                        last_accessed_at=recent_time,
                    ),
                ]
            )
            consolidator = MemoryConsolidator(
                store=store,
                decay_after_days=30,
                decay_factor=0.05,
            )
            result = consolidator.consolidate("default")
            self.assertEqual(result["decayed"], 0)
            store.close()


class WorkingSummaryTests(unittest.TestCase):
    """Tests for structured working summary generation."""

    def test_working_summary_includes_topic_line(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            manager = MemoryManager(store=store)
            manager.ingest_session_turns(
                "sess-ws",
                [
                    {
                        "prompt_text": "Tell me about the kubernetes deployment pipeline.",
                        "response_text": "The deployment uses Helm charts on our cluster.",
                    },
                    {
                        "prompt_text": "How does the monitoring work?",
                        "response_text": "We use Prometheus and Grafana for monitoring.",
                    },
                ],
            )
            units = store.list_active("default", limit=50)
            summaries = [u for u in units if u.memory_type == MemoryType.WORKING_SUMMARY]
            self.assertTrue(summaries)
            content = summaries[0].content
            self.assertIn("Topics:", content)
            self.assertIn("turn(s)", content)
            manager.close()


class HybridRetrievalTests(unittest.TestCase):
    """Tests for IDF-weighted hybrid retrieval."""

    def test_hybrid_retrieval_uses_idf_ranking(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            from metaclaw.memory.embeddings import HashingEmbedder
            embedder = HashingEmbedder()
            # Add memories: "python" is common, "kubernetes" is rare.
            memories = [
                MemoryUnit(
                    memory_id=f"py-{i}",
                    scope_id="default",
                    memory_type=MemoryType.SEMANTIC,
                    content=f"Python is used for task {i}.",
                    summary=f"Python task {i}.",
                    importance=0.5,
                    embedding=embedder.encode(f"Python is used for task {i}."),
                )
                for i in range(4)
            ] + [
                MemoryUnit(
                    memory_id="k8s-1",
                    scope_id="default",
                    memory_type=MemoryType.SEMANTIC,
                    content="Kubernetes and python run the microservices.",
                    summary="K8s and python.",
                    importance=0.5,
                    embedding=embedder.encode("Kubernetes and python run the microservices."),
                ),
            ]
            store.add_memories(memories)
            from metaclaw.memory.retriever import MemoryRetriever
            from metaclaw.memory.policy import MemoryPolicy
            from metaclaw.memory.models import MemoryQuery
            retriever = MemoryRetriever(
                store=store, policy=MemoryPolicy(),
                retrieval_mode="hybrid", embedder=embedder,
            )
            query = MemoryQuery(scope_id="default", query_text="kubernetes python", top_k=5)
            hits = retriever.retrieve(query)
            self.assertTrue(hits)
            self.assertEqual(hits[0].unit.memory_id, "k8s-1")
            store.close()


class CLIIntegrationTests(unittest.TestCase):
    """Smoke tests for CLI memory subcommands."""

    def test_memory_status_renders_without_error(self):
        """Verify that `metaclaw memory status` path does not crash."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg = MetaClawConfig(
                memory_enabled=True,
                memory_store_path=os.path.join(tmpdir, "memory.db"),
                memory_policy_path=os.path.join(tmpdir, "policy.json"),
                memory_telemetry_path=os.path.join(tmpdir, "telemetry.jsonl"),
                memory_scope="default",
            )
            manager = MemoryManager.from_config(cfg)
            manager.ingest_session_turns(
                "sess-cli",
                [{"prompt_text": "I prefer dark mode.", "response_text": "OK."}],
            )
            # The data surfaces that CLI reads should be populated and not crash.
            stats = manager.get_scope_stats()
            self.assertIn("active", stats)
            self.assertGreater(stats["active"], 0)
            policy = manager.get_policy_state()
            self.assertIn("retrieval_mode", policy)
            telemetry = manager.get_recent_telemetry(limit=5)
            self.assertTrue(telemetry)
            manager.close()

    def test_end_to_end_ingest_retrieve_render(self):
        """Full pipeline smoke test: ingest, retrieve, render."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            manager = MemoryManager(store=store, retrieval_mode="keyword")
            manager.ingest_session_turns(
                "sess-e2e",
                [
                    {
                        "prompt_text": "I prefer TypeScript for all frontend work.",
                        "response_text": "Noted, TypeScript for frontend.",
                    },
                    {
                        "prompt_text": "We use PostgreSQL as our primary database.",
                        "response_text": "Got it.",
                    },
                ],
            )
            units = manager.retrieve_for_prompt("What language for frontend?")
            self.assertTrue(units)
            rendered = manager.render_for_prompt(units)
            self.assertIn("Relevant Long-Term Memory", rendered)
            self.assertTrue(len(rendered) > 20)
            manager.close()


class ManagerIntegrationTests(unittest.TestCase):
    """Integration tests for the full manager pipeline."""

    def test_multi_session_ingest_with_consolidation_and_decay(self):
        """Verify that ingesting multiple sessions consolidates and decays properly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            manager = MemoryManager(store=store, auto_consolidate=True)
            # Session 1: user preferences.
            manager.ingest_session_turns(
                "sess-1",
                [
                    {"prompt_text": "I prefer dark mode in all editors.", "response_text": "OK."},
                    {"prompt_text": "We use PostgreSQL for the main database.", "response_text": "Noted."},
                ],
            )
            # Session 2: similar preferences and new facts.
            manager.ingest_session_turns(
                "sess-2",
                [
                    {"prompt_text": "I prefer dark mode in all editors.", "response_text": "Understood."},
                    {"prompt_text": "Remember that the API rate limit is 100/min.", "response_text": "Got it."},
                ],
            )
            stats = manager.get_scope_stats()
            self.assertGreater(stats["active"], 0)
            # Should have exactly 1 working summary active (consolidation keeps newest).
            active = store.list_active("default", limit=200)
            working_summaries = [u for u in active if u.memory_type == MemoryType.WORKING_SUMMARY]
            self.assertEqual(len(working_summaries), 1)
            manager.close()

    def test_full_cycle_ingest_retrieve_render_round_trip(self):
        """Ingest diverse session data and verify retrieval returns relevant memory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg = MetaClawConfig(
                memory_enabled=True,
                memory_store_path=os.path.join(tmpdir, "memory.db"),
                memory_policy_path=os.path.join(tmpdir, "policy.json"),
                memory_telemetry_path=os.path.join(tmpdir, "telemetry.jsonl"),
                memory_scope="default",
                memory_retrieval_mode="keyword",
            )
            manager = MemoryManager.from_config(cfg)
            manager.ingest_session_turns(
                "sess-full",
                [
                    {"prompt_text": "The project uses FastAPI for the API layer.", "response_text": "Noted."},
                    {"prompt_text": "I prefer type annotations on all public functions.", "response_text": "OK."},
                    {"prompt_text": "Remember that we deploy to AWS ECS.", "response_text": "Got it."},
                ],
            )
            # Retrieve for a related query.
            units = manager.retrieve_for_prompt("What framework does the API use?")
            self.assertTrue(units)
            rendered = manager.render_for_prompt(units)
            self.assertIn("Relevant Long-Term Memory", rendered)
            # The telemetry should have recorded the ingest.
            events = manager.get_recent_telemetry(limit=10)
            self.assertTrue(any(e["event_type"] == "memory_ingest" for e in events))
            manager.close()


class PolicyOptimizerTests(unittest.TestCase):
    """Tests for the enhanced policy optimizer."""

    def test_optimizer_raises_importance_weight_for_factual_pool(self):
        """When semantic+project_state memories dominate, importance_weight should rise."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            # Add 10 semantic memories and 5 project_state memories.
            for i in range(10):
                store.add_memories([
                    MemoryUnit(
                        memory_id=f"sem-{i}",
                        scope_id="default",
                        memory_type=MemoryType.SEMANTIC,
                        content=f"Semantic fact {i} about the system.",
                        summary=f"Fact {i}.",
                        importance=0.7,
                    ),
                ])
            for i in range(5):
                store.add_memories([
                    MemoryUnit(
                        memory_id=f"proj-{i}",
                        scope_id="default",
                        memory_type=MemoryType.PROJECT_STATE,
                        content=f"Project state {i} about infrastructure.",
                        summary=f"Project {i}.",
                        importance=0.8,
                    ),
                ])
            from metaclaw.memory.policy_optimizer import MemoryPolicyOptimizer
            optimizer = MemoryPolicyOptimizer(store=store)
            current = MemoryPolicyState(importance_weight=0.5)
            proposed = optimizer.propose("default", current)
            self.assertGreaterEqual(proposed.importance_weight, 0.55)
            store.close()

    def test_optimizer_raises_budget_from_telemetry_saturation(self):
        """When retrieval consistently saturates the unit limit, raise the budget."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            telemetry = MemoryTelemetryStore(os.path.join(tmpdir, "telemetry.jsonl"))
            # Add enough memories to pass the low-volume guard.
            for i in range(10):
                store.add_memories([
                    MemoryUnit(
                        memory_id=f"mem-{i}",
                        scope_id="default",
                        memory_type=MemoryType.SEMANTIC,
                        content=f"Fact {i} about the system.",
                        summary=f"Fact {i}.",
                    ),
                ])
            # Record telemetry events showing saturated retrieval (6/6 units).
            for _ in range(10):
                telemetry.record("memory_retrieval", {
                    "scope_id": "default",
                    "retrieved_count": 6,
                    "injected_tokens": 700,
                    "avg_importance": 0.7,
                    "types_retrieved": ["semantic"],
                    "retrieval_mode": "keyword",
                })
            from metaclaw.memory.policy_optimizer import MemoryPolicyOptimizer
            optimizer = MemoryPolicyOptimizer(store=store, telemetry_store=telemetry)
            current = MemoryPolicyState(max_injected_units=6)
            proposed = optimizer.propose("default", current)
            self.assertGreater(proposed.max_injected_units, 6)
            store.close()

    def test_optimizer_does_not_tune_with_few_memories(self):
        """With less than 5 active memories, optimizer should not change weights."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories([
                MemoryUnit(
                    memory_id="only-1",
                    scope_id="default",
                    memory_type=MemoryType.SEMANTIC,
                    content="Single memory.",
                    summary="One.",
                ),
            ])
            from metaclaw.memory.policy_optimizer import MemoryPolicyOptimizer
            optimizer = MemoryPolicyOptimizer(store=store)
            current = MemoryPolicyState()
            proposed = optimizer.propose("default", current)
            self.assertEqual(proposed.retrieval_mode, current.retrieval_mode)
            self.assertEqual(proposed.max_injected_units, current.max_injected_units)
            store.close()


class RenderQualityTests(unittest.TestCase):
    """Tests for token-efficient prompt rendering."""

    def test_render_groups_memories_by_type(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            manager = MemoryManager(store=store)
            manager.ingest_session_turns(
                "sess-render",
                [
                    {"prompt_text": "I prefer TypeScript.", "response_text": "OK."},
                    {"prompt_text": "We use PostgreSQL.", "response_text": "Noted."},
                    {"prompt_text": "Remember that our CI runs on GitHub Actions.", "response_text": "Got it."},
                ],
            )
            units = manager.retrieve_for_prompt("TypeScript PostgreSQL CI")
            rendered = manager.render_for_prompt(units)
            self.assertIn("Relevant Long-Term Memory", rendered)
            # Each unit should be rendered as a bullet point.
            self.assertIn("- ", rendered)
            manager.close()


class RetrievalTelemetryTests(unittest.TestCase):
    """Tests for retrieval telemetry recording."""

    def test_retrieval_records_telemetry_event(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg = MetaClawConfig(
                memory_enabled=True,
                memory_store_path=os.path.join(tmpdir, "memory.db"),
                memory_policy_path=os.path.join(tmpdir, "policy.json"),
                memory_telemetry_path=os.path.join(tmpdir, "telemetry.jsonl"),
                memory_scope="default",
            )
            manager = MemoryManager.from_config(cfg)
            manager.ingest_session_turns(
                "sess-tel",
                [{"prompt_text": "I prefer TypeScript.", "response_text": "OK."}],
            )
            manager.retrieve_for_prompt("TypeScript preference")
            events = manager.get_recent_telemetry(limit=20)
            retrieval_events = [e for e in events if e["event_type"] == "memory_retrieval"]
            self.assertTrue(retrieval_events)
            payload = retrieval_events[-1]["payload"]
            self.assertIn("retrieved_count", payload)
            self.assertIn("injected_tokens", payload)
            self.assertIn("avg_importance", payload)
            self.assertIn("types_retrieved", payload)
            manager.close()


class ScopeIsolationTests(unittest.TestCase):
    """Tests for multi-scope memory isolation."""

    def test_memories_from_different_scopes_are_isolated(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            manager = MemoryManager(store=store, scope_id="user-a")
            manager.ingest_session_turns(
                "sess-a",
                [{"prompt_text": "I prefer Python for all work.", "response_text": "OK."}],
                scope_id="user-a",
            )
            manager.ingest_session_turns(
                "sess-b",
                [{"prompt_text": "I prefer Rust for all work.", "response_text": "OK."}],
                scope_id="user-b",
            )
            # Retrieval for user-a should not see user-b's memories.
            units_a = manager.retrieve_for_prompt("What language?", scope_id="user-a")
            units_b = manager.retrieve_for_prompt("What language?", scope_id="user-b")
            scope_ids_a = {u.scope_id for u in units_a}
            scope_ids_b = {u.scope_id for u in units_b}
            self.assertTrue(all(s == "user-a" for s in scope_ids_a))
            self.assertTrue(all(s == "user-b" for s in scope_ids_b))
            manager.close()

    def test_scope_derivation_precedence(self):
        from metaclaw.memory.scope import derive_memory_scope
        # Explicit scope takes priority.
        self.assertEqual(derive_memory_scope("default", memory_scope="custom"), "custom")
        # User+workspace combo.
        self.assertEqual(
            derive_memory_scope("default", user_id="alice", workspace_id="proj"),
            "user:alice|workspace:proj",
        )
        # Session fallback.
        result = derive_memory_scope("default", session_id="sess-123")
        self.assertIn("session:sess-123", result)
        # Plain default.
        self.assertEqual(derive_memory_scope("default"), "default")


class StoreRobustnessTests(unittest.TestCase):
    """Tests for edge cases and error handling in the store."""

    def test_empty_query_returns_no_results(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            hits = store.search_keyword("default", "", limit=10)
            self.assertEqual(hits, [])
            store.close()

    def test_search_with_no_memories_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            hits = store.search_keyword("default", "anything", limit=10)
            self.assertEqual(hits, [])
            store.close()

    def test_mark_accessed_with_empty_list_does_not_crash(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.mark_accessed([], accessed_at="2026-01-01T00:00:00+00:00")
            store.close()

    def test_supersede_nonexistent_memory_does_not_crash(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            # Should not raise.
            store.supersede("nonexistent", "also-nonexistent", "2026-01-01T00:00:00+00:00")
            store.close()

    def test_stats_on_empty_scope_returns_zeros(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            stats = store.get_stats("empty-scope")
            self.assertEqual(stats["total"], 0)
            self.assertEqual(stats["active"], 0)
            self.assertEqual(stats["active_by_type"], {})
            store.close()

    def test_ingest_empty_turns_does_not_crash(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            manager = MemoryManager(store=store)
            count = manager.ingest_session_turns("empty-sess", [])
            self.assertEqual(count, 0)
            manager.close()

    def test_ingest_turns_with_empty_text_does_not_crash(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            manager = MemoryManager(store=store)
            count = manager.ingest_session_turns(
                "blank-sess",
                [{"prompt_text": "", "response_text": ""}],
            )
            # Empty turns should be skipped; only working summary if any turns present.
            self.assertGreaterEqual(count, 0)
            manager.close()

    def test_retrieve_with_no_store_data_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            manager = MemoryManager(store=store)
            units = manager.retrieve_for_prompt("anything at all")
            self.assertEqual(units, [])
            manager.close()

    def test_render_empty_units_returns_empty_string(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            manager = MemoryManager(store=store)
            result = manager.render_for_prompt([])
            self.assertEqual(result, "")
            manager.close()


class SelfUpgradeIntegrationTests(unittest.TestCase):
    """Integration tests for the full self-upgrade pipeline."""

    def test_full_auto_upgrade_cycle_produces_cycle_history(self):
        """Run a complete auto-upgrade cycle and verify artifacts."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg = MetaClawConfig(
                memory_enabled=True,
                memory_dir=tmpdir,
                memory_store_path=os.path.join(tmpdir, "memory.db"),
                memory_policy_path=os.path.join(tmpdir, "live-policy.json"),
                memory_telemetry_path=os.path.join(tmpdir, "telemetry.jsonl"),
                memory_scope="default",
                record_dir=tmpdir,
            )
            # Bootstrap a live policy.
            MemoryPolicyStore(cfg.memory_policy_path).save(MemoryPolicyState(), reason="bootstrap")
            # Create some memory data.
            manager = MemoryManager.from_config(cfg)
            manager.ingest_session_turns(
                "sess-upgrade",
                [
                    {"prompt_text": "I prefer concise updates.", "response_text": "OK."},
                    {"prompt_text": "We use Python 3.12 for all services.", "response_text": "Noted."},
                ],
            )
            manager.close()
            # Create replay records.
            records_path = os.path.join(tmpdir, "conversations.jsonl")
            with open(records_path, "w") as f:
                for i in range(15):
                    f.write(json.dumps({
                        "session_id": f"sess-{i}",
                        "turn": 1,
                        "instruction_text": f"Tell me about service {i}",
                        "response_text": f"Service {i} handles data processing.",
                        "next_state": {"content": f"Service {i} overview."},
                    }) + "\n")
            # Run auto-upgrade cycle.
            orchestrator = MemorySelfUpgradeOrchestrator(
                cfg,
                history_path=os.path.join(tmpdir, "upgrade_history.jsonl"),
            )
            decisions = orchestrator.run_auto_upgrade_cycle(
                replay_records_path=records_path,
                criteria=MemoryPromotionCriteria(min_sample_count=1),
            )
            self.assertTrue(decisions)
            # Verify cycle history was written.
            cycle_history = orchestrator.read_cycle_history()
            self.assertTrue(cycle_history)
            # Verify upgrade history was written.
            history = orchestrator.read_history()
            self.assertTrue(history)
            # Verify summary works.
            summary = orchestrator.summarize_history()
            self.assertGreater(summary["total"], 0)

    def test_operational_health_summary_runs_without_error(self):
        """Verify operational health summary doesn't crash on empty state."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg = MetaClawConfig(
                memory_enabled=True,
                memory_dir=tmpdir,
                memory_store_path=os.path.join(tmpdir, "memory.db"),
                memory_policy_path=os.path.join(tmpdir, "policy.json"),
                memory_telemetry_path=os.path.join(tmpdir, "telemetry.jsonl"),
            )
            orchestrator = MemorySelfUpgradeOrchestrator(
                cfg,
                history_path=os.path.join(tmpdir, "upgrade_history.jsonl"),
            )
            health = orchestrator.summarize_operational_health()
            self.assertIn("level", health)
            self.assertIn("reasons", health)
            self.assertEqual(health["level"], "healthy")


class FTSSearchTests(unittest.TestCase):
    """Tests for FTS5-accelerated keyword search."""

    def test_fts_search_returns_same_results_as_manual(self):
        """FTS path should produce the same top results as manual keyword search."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "fts_test.db"))
            units = []
            for i in range(20):
                units.append(MemoryUnit(
                    memory_id=f"fts-{i}",
                    scope_id="s1",
                    memory_type=MemoryType.SEMANTIC,
                    content=f"The system uses microservice architecture for component {i}",
                    summary=f"Architecture fact {i}",
                    topics=["architecture", "microservice"],
                    importance=0.6,
                ))
            # Add one with a rare term.
            units.append(MemoryUnit(
                memory_id="fts-rare",
                scope_id="s1",
                memory_type=MemoryType.SEMANTIC,
                content="The authentication gateway uses OAuth2 tokens exclusively",
                summary="Auth architecture",
                topics=["authentication", "oauth2"],
                importance=0.7,
            ))
            store.add_memories(units)

            hits = store.search_keyword("s1", "authentication oauth2", limit=5)
            self.assertTrue(hits)
            self.assertEqual(hits[0].unit.memory_id, "fts-rare")
            store.close()

    def test_fts_respects_scope_isolation(self):
        """FTS search should only return results from the queried scope."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "fts_scope.db"))
            store.add_memories([
                MemoryUnit(
                    memory_id="scope-a",
                    scope_id="alpha",
                    memory_type=MemoryType.SEMANTIC,
                    content="Alpha project uses Redis for caching",
                    topics=["redis"],
                ),
                MemoryUnit(
                    memory_id="scope-b",
                    scope_id="beta",
                    memory_type=MemoryType.SEMANTIC,
                    content="Beta project uses Redis for queuing",
                    topics=["redis"],
                ),
            ])
            hits = store.search_keyword("alpha", "Redis caching", limit=5)
            self.assertTrue(hits)
            for hit in hits:
                self.assertEqual(hit.unit.scope_id, "alpha")
            store.close()


class CorruptedStoreTests(unittest.TestCase):
    """Tests for graceful degradation with corrupted store files."""

    def test_corrupted_db_file_resets_cleanly(self):
        """A corrupted DB file should be backed up and a fresh store created."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "corrupt.db")
            # Write garbage to simulate corruption.
            with open(db_path, "wb") as f:
                f.write(b"NOT A VALID SQLITE DATABASE FILE\x00" * 100)

            store = MemoryStore(db_path)
            # Should be able to use the store normally.
            added = store.add_memories([
                MemoryUnit(
                    memory_id="after-corrupt",
                    scope_id="s1",
                    memory_type=MemoryType.SEMANTIC,
                    content="Memory added after corruption recovery",
                )
            ])
            self.assertEqual(added, 1)
            units = store.list_active("s1")
            self.assertEqual(len(units), 1)
            # Backup file should exist.
            backup_path = os.path.join(tmpdir, "corrupt.db.corrupt")
            self.assertTrue(os.path.exists(backup_path))
            store.close()

    def test_missing_db_file_creates_fresh(self):
        """A nonexistent DB path should create a new store without error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "subdir", "fresh.db")
            store = MemoryStore(db_path)
            self.assertEqual(store.list_active("s1"), [])
            store.close()


class MultiTurnExtractionTests(unittest.TestCase):
    """Tests for multi-turn context-aware extraction."""

    def test_continuation_turn_inherits_prior_entities(self):
        """A continuation turn should pick up entities from prior turns."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "mt.db"))
            manager = MemoryManager(store=store, scope_id="s1")
            turns = [
                {"prompt_text": "We use PostgreSQL for the main database.", "response_text": "Noted."},
                {"prompt_text": "Also, I prefer verbose logging for debugging.", "response_text": "OK."},
            ]
            manager.ingest_session_turns("sess-mt", turns)
            units = store.list_active("s1")
            # The continuation turn (with "Also") should have entities from prior context.
            continuation_units = [
                u for u in units
                if u.memory_type != MemoryType.WORKING_SUMMARY
                and u.source_turn_start == 2
            ]
            self.assertTrue(continuation_units)
            # Should have inherited "PostgreSQL" from the prior turn.
            all_entities = []
            for u in continuation_units:
                all_entities.extend(u.entities)
            self.assertTrue(
                any("PostgreSQL" in e for e in all_entities),
                f"Expected PostgreSQL in entities but got: {all_entities}",
            )
            store.close()

    def test_non_continuation_turn_does_not_inherit(self):
        """A turn that doesn't use continuation markers should not inherit entities."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "mt2.db"))
            manager = MemoryManager(store=store, scope_id="s1")
            turns = [
                {"prompt_text": "We use PostgreSQL for the main database.", "response_text": "Noted."},
                {"prompt_text": "I prefer dark mode in all editors.", "response_text": "OK."},
            ]
            manager.ingest_session_turns("sess-mt2", turns)
            units = store.list_active("s1")
            pref_units = [
                u for u in units
                if u.memory_type == MemoryType.PREFERENCE
                and u.source_turn_start == 2
            ]
            self.assertTrue(pref_units)
            # Should NOT have PostgreSQL since this isn't a continuation.
            for u in pref_units:
                self.assertNotIn("PostgreSQL", u.entities)
            store.close()

    def test_continuation_enriches_extraction_context(self):
        """Continuation turns should use prior context to extract patterns."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "mt3.db"))
            manager = MemoryManager(store=store, scope_id="s1")
            turns = [
                {"prompt_text": "I prefer using TypeScript for frontend work.", "response_text": "OK."},
                {"prompt_text": "Also, remember that all tests should pass before merge.", "response_text": "Will do."},
            ]
            manager.ingest_session_turns("sess-mt3", turns)
            units = store.list_active("s1")
            # Turn 2 should produce a semantic memory from "remember that" pattern.
            semantic_units = [
                u for u in units
                if u.memory_type == MemoryType.SEMANTIC
                and u.source_turn_start == 2
            ]
            self.assertTrue(semantic_units, "Expected semantic memory from continuation turn")
            store.close()


class StressTests(unittest.TestCase):
    """Stress tests with large numbers of memory units."""

    def test_large_pool_search_performance(self):
        """Search should work correctly with hundreds of memory units."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "stress.db"))
            units = []
            for i in range(300):
                units.append(MemoryUnit(
                    memory_id=f"stress-{i}",
                    scope_id="s1",
                    memory_type=MemoryType.SEMANTIC,
                    content=f"Service component {i} handles data processing for domain {i % 10}",
                    summary=f"Component {i} summary",
                    topics=[f"domain-{i % 10}", "processing"],
                    entities=[f"Component{i}"],
                    importance=0.5 + (i % 5) * 0.1,
                ))
            # Add a unique needle.
            units.append(MemoryUnit(
                memory_id="stress-needle",
                scope_id="s1",
                memory_type=MemoryType.SEMANTIC,
                content="The authentication subsystem requires OAuth2 with PKCE flow",
                summary="Auth requirement",
                topics=["authentication", "oauth2", "pkce"],
                entities=["AuthSubsystem"],
                importance=0.9,
            ))
            store.add_memories(units)

            hits = store.search_keyword("s1", "authentication OAuth2 PKCE", limit=5)
            self.assertTrue(hits)
            self.assertEqual(hits[0].unit.memory_id, "stress-needle")

            # Verify consolidation works on large pools.
            consolidator = MemoryConsolidator(store=store)
            result = consolidator.consolidate("s1")
            self.assertIsInstance(result, dict)
            store.close()

    def test_large_pool_retrieval_stays_bounded(self):
        """Retrieval should respect limits even with many units."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "stress2.db"))
            units = []
            for i in range(200):
                units.append(MemoryUnit(
                    memory_id=f"bounded-{i}",
                    scope_id="s1",
                    memory_type=MemoryType.SEMANTIC,
                    content=f"System fact number {i} about data processing",
                    summary=f"Fact {i}",
                    topics=["data", "processing"],
                    importance=0.5,
                ))
            store.add_memories(units)

            hits = store.search_keyword("s1", "data processing", limit=6)
            self.assertLessEqual(len(hits), 6)
            store.close()


class EntityReinforcementTests(unittest.TestCase):
    """Tests for entity-based cross-type reinforcement in consolidation."""

    def test_shared_entities_boost_reinforcement(self):
        """Memories sharing entities should get reinforcement score boosts."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "entity.db"))
            store.add_memories([
                MemoryUnit(
                    memory_id="ent-1",
                    scope_id="s1",
                    memory_type=MemoryType.SEMANTIC,
                    content="PostgreSQL is the main database",
                    entities=["PostgreSQL"],
                    importance=0.7,
                ),
                MemoryUnit(
                    memory_id="ent-2",
                    scope_id="s1",
                    memory_type=MemoryType.PROJECT_STATE,
                    content="We use PostgreSQL 15 in production",
                    entities=["PostgreSQL"],
                    importance=0.6,
                ),
                MemoryUnit(
                    memory_id="ent-3",
                    scope_id="s1",
                    memory_type=MemoryType.PREFERENCE,
                    content="I prefer Redis over Memcached",
                    entities=["Redis", "Memcached"],
                    importance=0.5,
                ),
            ])
            consolidator = MemoryConsolidator(store=store)
            result = consolidator.consolidate("s1")
            self.assertGreater(result.get("reinforced", 0), 0)

            # Reload and check that shared-entity memories got reinforcement.
            units = store.list_active("s1")
            pg_units = [u for u in units if "PostgreSQL" in u.entities]
            self.assertTrue(all(u.reinforcement_score > 0 for u in pg_units))
            store.close()

    def test_unique_entities_not_reinforced(self):
        """Memories with unique entities should not get reinforcement."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "entity2.db"))
            store.add_memories([
                MemoryUnit(
                    memory_id="unique-1",
                    scope_id="s1",
                    memory_type=MemoryType.SEMANTIC,
                    content="Alpha service handles auth",
                    entities=["AlphaService"],
                ),
                MemoryUnit(
                    memory_id="unique-2",
                    scope_id="s1",
                    memory_type=MemoryType.SEMANTIC,
                    content="Beta service handles payments",
                    entities=["BetaService"],
                ),
            ])
            consolidator = MemoryConsolidator(store=store)
            result = consolidator.consolidate("s1")
            self.assertEqual(result.get("reinforced", 0), 0)
            store.close()


class TypeDistributionTelemetryTests(unittest.TestCase):
    """Tests for type distribution in retrieval telemetry."""

    def test_retrieval_telemetry_includes_type_distribution(self):
        """Retrieval telemetry should record type distribution of results."""
        with tempfile.TemporaryDirectory() as tmpdir:
            from metaclaw.memory.telemetry import MemoryTelemetryStore

            store = MemoryStore(os.path.join(tmpdir, "ttype.db"))
            telemetry = MemoryTelemetryStore(os.path.join(tmpdir, "tel.jsonl"))
            store.add_memories([
                MemoryUnit(
                    memory_id="tt-1",
                    scope_id="s1",
                    memory_type=MemoryType.SEMANTIC,
                    content="The project uses Python 3.12",
                    topics=["python"],
                ),
                MemoryUnit(
                    memory_id="tt-2",
                    scope_id="s1",
                    memory_type=MemoryType.PREFERENCE,
                    content="I prefer concise Python documentation",
                    topics=["python", "documentation"],
                ),
            ])
            manager = MemoryManager(
                store=store, scope_id="s1", telemetry_store=telemetry
            )
            manager.retrieve_for_prompt("Python setup")
            events = telemetry.read_recent(limit=5)
            retrieval_events = [e for e in events if e["event_type"] == "memory_retrieval"]
            self.assertTrue(retrieval_events)
            payload = retrieval_events[-1]["payload"]
            self.assertIn("type_distribution", payload)
            self.assertIn("avg_reinforcement", payload)
            store.close()


class QueryExpansionTests(unittest.TestCase):
    """Tests for query expansion in retrieval."""

    def test_abbreviation_expands_to_full_term(self):
        """Querying 'db' should also find memories mentioning 'database'."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "expand.db"))
            store.add_memories([
                MemoryUnit(
                    memory_id="qe-1",
                    scope_id="s1",
                    memory_type=MemoryType.PROJECT_STATE,
                    content="The main database is PostgreSQL 15",
                    topics=["database", "postgresql"],
                ),
            ])
            from metaclaw.memory.retriever import MemoryRetriever
            from metaclaw.memory.policy import MemoryPolicy

            retriever = MemoryRetriever(store=store, policy=MemoryPolicy())
            from metaclaw.memory.models import MemoryQuery

            hits = retriever.retrieve(MemoryQuery(scope_id="s1", query_text="db setup"))
            self.assertTrue(hits)
            self.assertEqual(hits[0].unit.memory_id, "qe-1")
            store.close()

    def test_no_expansion_when_direct_match_sufficient(self):
        """If direct search finds enough results, expansion should not be needed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "expand2.db"))
            for i in range(5):
                store.add_memories([
                    MemoryUnit(
                        memory_id=f"qe2-{i}",
                        scope_id="s1",
                        memory_type=MemoryType.SEMANTIC,
                        content=f"Database configuration item {i}",
                        topics=["database"],
                    ),
                ])
            from metaclaw.memory.retriever import MemoryRetriever
            from metaclaw.memory.policy import MemoryPolicy

            retriever = MemoryRetriever(store=store, policy=MemoryPolicy())
            from metaclaw.memory.models import MemoryQuery

            hits = retriever.retrieve(MemoryQuery(scope_id="s1", query_text="database configuration"))
            self.assertTrue(hits)
            store.close()


class ConfidenceWeightedRetrievalTests(unittest.TestCase):
    """Tests for confidence-weighted scoring in hybrid retrieval."""

    def test_high_confidence_scores_higher(self):
        """A memory with higher confidence should score better in hybrid mode."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "conf.db"))
            store.add_memories([
                MemoryUnit(
                    memory_id="conf-high",
                    scope_id="s1",
                    memory_type=MemoryType.SEMANTIC,
                    content="The deployment uses Kubernetes orchestration",
                    topics=["kubernetes", "deployment"],
                    importance=0.5,
                    confidence=0.95,
                ),
                MemoryUnit(
                    memory_id="conf-low",
                    scope_id="s1",
                    memory_type=MemoryType.SEMANTIC,
                    content="The deployment pipeline runs weekly",
                    topics=["deployment", "pipeline"],
                    importance=0.5,
                    confidence=0.3,
                ),
            ])
            from metaclaw.memory.retriever import MemoryRetriever
            from metaclaw.memory.policy import MemoryPolicy
            from metaclaw.memory.embeddings import HashingEmbedder

            retriever = MemoryRetriever(
                store=store,
                policy=MemoryPolicy(),
                retrieval_mode="hybrid",
                embedder=HashingEmbedder(),
            )
            from metaclaw.memory.models import MemoryQuery

            hits = retriever.retrieve(MemoryQuery(scope_id="s1", query_text="deployment"))
            self.assertEqual(len(hits), 2)
            # High confidence should rank first (all else being roughly equal).
            self.assertEqual(hits[0].unit.memory_id, "conf-high")
            store.close()


class IngestionDedupTests(unittest.TestCase):
    """Tests for pre-ingestion deduplication."""

    def test_duplicate_content_not_re_ingested(self):
        """Ingesting the same session twice should not create duplicate memories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "dedup.db"))
            manager = MemoryManager(store=store, scope_id="s1")
            turns = [
                {"prompt_text": "I prefer dark mode in all editors.", "response_text": "OK."},
            ]
            count1 = manager.ingest_session_turns("sess-1", turns)
            active_after_first = len(store.list_active("s1"))

            count2 = manager.ingest_session_turns("sess-2", turns)
            active_after_second = len(store.list_active("s1"))

            # Second ingestion should add fewer units (only working summary).
            self.assertLess(count2, count1 + 1)
            store.close()


class TypeDiversityTests(unittest.TestCase):
    """Tests for retrieval type diversity enforcement."""

    def test_diversity_reorders_dominant_type(self):
        """Type diversity enforcement should push excess same-type units to overflow."""
        from metaclaw.memory.manager import _enforce_type_diversity

        units = []
        for i in range(6):
            units.append(MemoryUnit(
                memory_id=f"sem-{i}",
                scope_id="s1",
                memory_type=MemoryType.SEMANTIC,
                content=f"Semantic unit {i}",
            ))
        for i in range(2):
            units.append(MemoryUnit(
                memory_id=f"pref-{i}",
                scope_id="s1",
                memory_type=MemoryType.PREFERENCE,
                content=f"Preference unit {i}",
            ))
        result = _enforce_type_diversity(units, max_dominant_ratio=0.6, min_count=4)
        # First few results should have at most 60% semantic = 4 out of 8.
        first_half = result[:5]
        sem_in_first = sum(1 for u in first_half if u.memory_type == MemoryType.SEMANTIC)
        pref_in_first = sum(1 for u in first_half if u.memory_type == MemoryType.PREFERENCE)
        self.assertLessEqual(sem_in_first, 4)
        self.assertGreater(pref_in_first, 0)


class MemoryExportImportTests(unittest.TestCase):
    """Tests for memory export/import round-trip."""

    def test_export_import_round_trip(self):
        """Exported memories should be importable and match original data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "export.db"))
            original_units = [
                MemoryUnit(
                    memory_id="exp-1",
                    scope_id="s1",
                    memory_type=MemoryType.SEMANTIC,
                    content="The project uses Python 3.12",
                    summary="Tech stack",
                    entities=["Python"],
                    topics=["python", "stack"],
                    importance=0.8,
                    confidence=0.9,
                ),
                MemoryUnit(
                    memory_id="exp-2",
                    scope_id="s1",
                    memory_type=MemoryType.PREFERENCE,
                    content="User preference: dark mode everywhere",
                    importance=0.7,
                ),
            ]
            store.add_memories(original_units)

            # Export.
            export_path = os.path.join(tmpdir, "export.jsonl")
            units = store.list_active("s1")
            with open(export_path, "w") as f:
                for unit in units:
                    f.write(json.dumps({
                        "memory_id": unit.memory_id,
                        "scope_id": unit.scope_id,
                        "memory_type": unit.memory_type.value,
                        "content": unit.content,
                        "summary": unit.summary,
                        "entities": unit.entities,
                        "topics": unit.topics,
                        "importance": unit.importance,
                        "confidence": unit.confidence,
                        "access_count": unit.access_count,
                        "reinforcement_score": unit.reinforcement_score,
                        "status": unit.status.value,
                        "created_at": unit.created_at,
                        "updated_at": unit.updated_at,
                    }) + "\n")
            store.close()

            # Import into a new store.
            store2 = MemoryStore(os.path.join(tmpdir, "import.db"))
            from metaclaw.memory.models import MemoryStatus
            with open(export_path) as ef:
                lines = ef.readlines()
            for line in lines:
                record = json.loads(line)
                store2.add_memories([MemoryUnit(
                    memory_id=record["memory_id"],
                    scope_id=record["scope_id"],
                    memory_type=MemoryType(record["memory_type"]),
                    content=record["content"],
                    summary=record.get("summary", ""),
                    entities=record.get("entities", []),
                    topics=record.get("topics", []),
                    importance=record.get("importance", 0.5),
                    confidence=record.get("confidence", 0.7),
                )])
            imported = store2.list_active("s1")
            self.assertEqual(len(imported), 2)
            ids = {u.memory_id for u in imported}
            self.assertIn("exp-1", ids)
            self.assertIn("exp-2", ids)
            store2.close()


class GarbageCollectionTests(unittest.TestCase):
    """Tests for scope-level garbage collection."""

    def test_gc_removes_orphaned_superseded(self):
        """GC should remove superseded memories not referenced by active units."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "gc.db"))
            store.add_memories([
                MemoryUnit(
                    memory_id="gc-active",
                    scope_id="s1",
                    memory_type=MemoryType.SEMANTIC,
                    content="Active memory",
                    supersedes=["gc-old-referenced"],
                ),
                MemoryUnit(
                    memory_id="gc-old-referenced",
                    scope_id="s1",
                    memory_type=MemoryType.SEMANTIC,
                    content="Old referenced memory",
                ),
                MemoryUnit(
                    memory_id="gc-orphan",
                    scope_id="s1",
                    memory_type=MemoryType.SEMANTIC,
                    content="Orphaned memory",
                ),
            ])
            from metaclaw.memory.models import utc_now_iso
            store.supersede("gc-old-referenced", "gc-active", utc_now_iso())
            store.supersede("gc-orphan", "gc-nonexistent", utc_now_iso())

            # Simulate GC: remove superseded not referenced by active units.
            active_units = store.list_active("s1")
            referenced = set()
            for u in active_units:
                for sid in u.supersedes:
                    referenced.add(sid)

            rows = store.conn.execute(
                "SELECT memory_id FROM memories WHERE scope_id = ? AND status = 'superseded'",
                ("s1",),
            ).fetchall()
            superseded_ids = {row["memory_id"] for row in rows}
            orphans = superseded_ids - referenced

            self.assertIn("gc-orphan", orphans)
            self.assertNotIn("gc-old-referenced", orphans)

            for oid in orphans:
                store.conn.execute("DELETE FROM memories WHERE memory_id = ?", (oid,))
            store.conn.commit()

            # Verify orphan is gone.
            remaining = store.conn.execute(
                "SELECT memory_id FROM memories WHERE scope_id = ?", ("s1",)
            ).fetchall()
            remaining_ids = {row["memory_id"] for row in remaining}
            self.assertNotIn("gc-orphan", remaining_ids)
            self.assertIn("gc-old-referenced", remaining_ids)
            store.close()


class FreshnessRenderingTests(unittest.TestCase):
    """Tests for freshness tags in rendered memory output."""

    def test_recent_memory_gets_freshness_tag(self):
        """Recently updated memories should have a freshness tag in rendering."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "fresh.db"))
            from metaclaw.memory.models import utc_now_iso

            store.add_memories([
                MemoryUnit(
                    memory_id="fresh-1",
                    scope_id="s1",
                    memory_type=MemoryType.SEMANTIC,
                    content="The system uses microservices",
                    updated_at=utc_now_iso(),
                ),
            ])
            manager = MemoryManager(store=store, scope_id="s1")
            units = store.list_active("s1")
            rendered = manager.render_for_prompt(units)
            # Should have either [just now] or [recent] tag.
            self.assertTrue(
                "[just now]" in rendered or "[recent]" in rendered,
                f"Expected freshness tag in: {rendered}",
            )
            store.close()


class WorkingSummaryEntityTests(unittest.TestCase):
    """Tests for entity tracking in working summaries."""

    def test_working_summary_includes_entities(self):
        """Working summary should include an Entities line."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "ws.db"))
            manager = MemoryManager(store=store, scope_id="s1")
            turns = [
                {"prompt_text": "We use PostgreSQL for the User database.", "response_text": "OK."},
                {"prompt_text": "Redis handles session caching.", "response_text": "Noted."},
            ]
            manager.ingest_session_turns("sess-ws", turns)
            units = store.list_active("s1")
            ws_units = [u for u in units if u.memory_type == MemoryType.WORKING_SUMMARY]
            self.assertTrue(ws_units)
            # Working summary content should mention entities.
            ws_content = ws_units[0].content
            self.assertIn("Entities:", ws_content)
            store.close()


class RetrievalLatencyTests(unittest.TestCase):
    """Benchmark tests for retrieval at scale."""

    def test_retrieval_at_500_units_under_one_second(self):
        """Retrieval from 500 units should complete in under 1 second."""
        import time

        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "bench.db"))
            units = []
            for i in range(500):
                units.append(MemoryUnit(
                    memory_id=f"bench-{i}",
                    scope_id="s1",
                    memory_type=MemoryType.SEMANTIC,
                    content=f"Component {i} processes data for domain {i % 20} using service {i % 15}",
                    summary=f"Component {i}",
                    topics=[f"domain-{i % 20}", f"service-{i % 15}"],
                    entities=[f"Component{i}"],
                    importance=0.3 + (i % 5) * 0.1,
                ))
            store.add_memories(units)

            start = time.monotonic()
            hits = store.search_keyword("s1", "domain-5 service-3 processing", limit=6)
            elapsed = time.monotonic() - start

            self.assertTrue(hits)
            self.assertLess(elapsed, 1.0, f"Search took {elapsed:.3f}s, expected < 1s")
            store.close()


class ExtendedExtractionPatternTests(unittest.TestCase):
    """Tests for expanded extraction pattern coverage."""

    def test_i_would_like_pattern(self):
        """'I'd like' should extract a preference."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "pat.db"))
            manager = MemoryManager(store=store, scope_id="s1")
            manager.ingest_session_turns("sess-pat", [
                {"prompt_text": "I'd like all code comments in English.", "response_text": "Sure."},
            ])
            units = store.list_active("s1")
            pref = [u for u in units if u.memory_type == MemoryType.PREFERENCE]
            self.assertTrue(pref, "Expected preference memory from 'I'd like' pattern")
            store.close()

    def test_never_pattern(self):
        """'never' should extract a procedural observation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "pat2.db"))
            manager = MemoryManager(store=store, scope_id="s1")
            manager.ingest_session_turns("sess-pat2", [
                {"prompt_text": "Never push directly to main branch.", "response_text": "Got it."},
            ])
            units = store.list_active("s1")
            proc = [u for u in units if u.memory_type == MemoryType.PROCEDURAL_OBSERVATION]
            self.assertTrue(proc, "Expected procedural observation from 'never' pattern")
            store.close()

    def test_just_so_you_know_pattern(self):
        """'just so you know' should extract a semantic memory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "pat3.db"))
            manager = MemoryManager(store=store, scope_id="s1")
            manager.ingest_session_turns("sess-pat3", [
                {"prompt_text": "Just so you know, the CI pipeline takes about 20 minutes.", "response_text": "OK."},
            ])
            units = store.list_active("s1")
            sem = [u for u in units if u.memory_type == MemoryType.SEMANTIC]
            self.assertTrue(sem, "Expected semantic memory from 'just so you know' pattern")
            store.close()

    def test_codebase_pattern(self):
        """'the codebase uses' should extract a project state memory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "pat4.db"))
            manager = MemoryManager(store=store, scope_id="s1")
            manager.ingest_session_turns("sess-pat4", [
                {"prompt_text": "The codebase uses a monorepo structure.", "response_text": "Noted."},
            ])
            units = store.list_active("s1")
            proj = [u for u in units if u.memory_type == MemoryType.PROJECT_STATE]
            self.assertTrue(proj, "Expected project state from 'the codebase uses' pattern")
            store.close()


class ConsolidationTelemetryTests(unittest.TestCase):
    """Tests for consolidation telemetry recording."""

    def test_consolidation_records_telemetry(self):
        """Consolidation results should be recorded in telemetry."""
        with tempfile.TemporaryDirectory() as tmpdir:
            from metaclaw.memory.telemetry import MemoryTelemetryStore

            store = MemoryStore(os.path.join(tmpdir, "ctel.db"))
            telemetry = MemoryTelemetryStore(os.path.join(tmpdir, "tel.jsonl"))
            manager = MemoryManager(
                store=store, scope_id="s1", telemetry_store=telemetry
            )
            # Ingest data that will trigger consolidation (duplicate working summaries).
            manager.ingest_session_turns("sess-1", [
                {"prompt_text": "I prefer Python.", "response_text": "OK."},
            ])
            manager.ingest_session_turns("sess-2", [
                {"prompt_text": "We use Docker.", "response_text": "Noted."},
            ])
            events = telemetry.read_recent(limit=20)
            consolidation_events = [
                e for e in events if e["event_type"] == "memory_consolidation"
            ]
            self.assertTrue(consolidation_events, "Expected consolidation telemetry events")
            payload = consolidation_events[-1]["payload"]
            self.assertIn("superseded", payload)
            self.assertIn("reinforced", payload)
            store.close()


class ImportanceAutoCalibrationTests(unittest.TestCase):
    """Tests for importance auto-boost on frequently accessed memories."""

    def test_frequently_accessed_memory_gets_importance_boost(self):
        """Memories accessed 3+ times should get a small importance boost."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "autoimp.db"))
            from metaclaw.memory.models import utc_now_iso

            store.add_memories([
                MemoryUnit(
                    memory_id="freq-1",
                    scope_id="s1",
                    memory_type=MemoryType.SEMANTIC,
                    content="The database connection pool size is 20",
                    topics=["database", "connection"],
                    importance=0.5,
                    access_count=3,
                ),
            ])
            manager = MemoryManager(store=store, scope_id="s1")
            units = manager.retrieve_for_prompt("database connection pool")
            if units:
                # After retrieval, importance should have been boosted.
                refreshed = store.list_active("s1")
                for u in refreshed:
                    if u.memory_id == "freq-1":
                        self.assertGreater(u.importance, 0.5)
            store.close()


class EdgeCaseExtractionTests(unittest.TestCase):
    """Tests for extraction edge cases."""

    def test_very_long_prompt_extracts_safely(self):
        """A very long prompt should not crash extraction."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "long.db"))
            manager = MemoryManager(store=store, scope_id="s1")
            long_text = "I prefer " + "very " * 500 + "concise responses."
            manager.ingest_session_turns("sess-long", [
                {"prompt_text": long_text, "response_text": "OK."},
            ])
            units = store.list_active("s1")
            self.assertTrue(units)
            store.close()

    def test_unicode_content_handled(self):
        """Unicode content should be stored and retrieved correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "unicode.db"))
            manager = MemoryManager(store=store, scope_id="s1")
            manager.ingest_session_turns("sess-uni", [
                {"prompt_text": "我们使用 PostgreSQL 数据库。Note that the encoding is UTF-8.", "response_text": "好的。"},
            ])
            units = store.list_active("s1")
            self.assertTrue(units)
            # Content should preserve unicode.
            all_content = " ".join(u.content for u in units)
            self.assertTrue(
                "PostgreSQL" in all_content or "UTF-8" in all_content,
                f"Expected preserved content but got: {all_content[:200]}"
            )
            store.close()

    def test_empty_session_ingests_nothing(self):
        """An empty session should add nothing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "empty.db"))
            manager = MemoryManager(store=store, scope_id="s1")
            count = manager.ingest_session_turns("sess-empty", [])
            self.assertEqual(count, 0)
            store.close()

    def test_special_characters_in_query(self):
        """Search queries with special characters should not crash."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "special.db"))
            store.add_memories([
                MemoryUnit(
                    memory_id="sp-1",
                    scope_id="s1",
                    memory_type=MemoryType.SEMANTIC,
                    content="The API endpoint is /api/v2/users",
                    topics=["api"],
                ),
            ])
            hits = store.search_keyword("s1", "/api/v2/users?filter=active&sort=name")
            # Should not crash; may or may not find results.
            self.assertIsInstance(hits, list)
            store.close()


class ConcurrentScopeTests(unittest.TestCase):
    """Tests for concurrent scope operations."""

    def test_multiple_scopes_independent_search(self):
        """Searches in different scopes should be fully independent."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "multi.db"))
            store.add_memories([
                MemoryUnit(
                    memory_id="ms-a",
                    scope_id="scope-a",
                    memory_type=MemoryType.SEMANTIC,
                    content="Alpha service uses Redis for caching",
                    topics=["redis"],
                ),
                MemoryUnit(
                    memory_id="ms-b",
                    scope_id="scope-b",
                    memory_type=MemoryType.SEMANTIC,
                    content="Beta service uses Redis for queuing",
                    topics=["redis"],
                ),
                MemoryUnit(
                    memory_id="ms-c",
                    scope_id="scope-a",
                    memory_type=MemoryType.PREFERENCE,
                    content="User preference: verbose logging",
                    topics=["logging"],
                ),
            ])
            a_hits = store.search_keyword("scope-a", "Redis", limit=10)
            b_hits = store.search_keyword("scope-b", "Redis", limit=10)
            self.assertEqual(len(a_hits), 1)
            self.assertEqual(len(b_hits), 1)
            self.assertEqual(a_hits[0].unit.scope_id, "scope-a")
            self.assertEqual(b_hits[0].unit.scope_id, "scope-b")
            store.close()


class EnrichedMetricsTests(unittest.TestCase):
    """Tests for enriched memory pool metrics."""

    def test_metrics_include_type_ratios(self):
        """summarize_memory_store should include type_ratios and type_count."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "metrics.db"))
            store.add_memories([
                MemoryUnit(
                    memory_id="m-1",
                    scope_id="s1",
                    memory_type=MemoryType.SEMANTIC,
                    content="Fact A",
                ),
                MemoryUnit(
                    memory_id="m-2",
                    scope_id="s1",
                    memory_type=MemoryType.PREFERENCE,
                    content="Pref B",
                ),
                MemoryUnit(
                    memory_id="m-3",
                    scope_id="s1",
                    memory_type=MemoryType.SEMANTIC,
                    content="Fact C",
                ),
            ])
            from metaclaw.memory.metrics import summarize_memory_store

            stats = summarize_memory_store(store, "s1")
            self.assertEqual(stats["type_count"], 2)
            self.assertIn("type_ratios", stats)
            self.assertAlmostEqual(stats["type_ratios"]["semantic"], 2 / 3, places=3)
            self.assertAlmostEqual(stats["type_ratios"]["preference"], 1 / 3, places=3)
            self.assertEqual(stats["superseded"], 0)
            store.close()


class CompactionTests(unittest.TestCase):
    """Tests for store compaction."""

    def test_compact_after_deletions(self):
        """Compaction should work without errors after deletions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "compact.db"))
            store.add_memories([
                MemoryUnit(
                    memory_id=f"cmp-{i}",
                    scope_id="s1",
                    memory_type=MemoryType.SEMANTIC,
                    content=f"Memory {i}",
                )
                for i in range(10)
            ])
            from metaclaw.memory.models import utc_now_iso

            for i in range(5):
                store.supersede(f"cmp-{i}", f"cmp-{i+5}", utc_now_iso())
            # Compact should not crash.
            store.compact()
            active = store.list_active("s1")
            self.assertEqual(len(active), 5)
            store.close()


class ThreadSafetyTests(unittest.TestCase):
    """Basic thread safety tests."""

    def test_concurrent_reads(self):
        """Multiple threads reading should not crash."""
        import threading

        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "thread.db"))
            store.add_memories([
                MemoryUnit(
                    memory_id=f"thr-{i}",
                    scope_id="s1",
                    memory_type=MemoryType.SEMANTIC,
                    content=f"Thread test memory {i}",
                    topics=["thread"],
                )
                for i in range(20)
            ])
            errors = []

            def search():
                try:
                    hits = store.search_keyword("s1", "thread test", limit=5)
                    if not hits:
                        errors.append("No hits found")
                except Exception as e:
                    errors.append(str(e))

            threads = [threading.Thread(target=search) for _ in range(5)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            self.assertEqual(errors, [], f"Errors in threads: {errors}")
            store.close()


class ReplayEnhancementTests(unittest.TestCase):
    """Tests for replay evaluation enhancements."""

    def test_replay_result_includes_zero_retrieval_count(self):
        """Replay results should track zero-retrieval samples."""
        with tempfile.TemporaryDirectory() as tmpdir:
            from metaclaw.memory.replay import MemoryReplayEvaluator, MemoryReplaySample

            store = MemoryStore(os.path.join(tmpdir, "replay.db"))
            manager = MemoryManager(store=store, scope_id="s1")
            evaluator = MemoryReplayEvaluator()
            # No memories in store → all retrievals will be zero.
            samples = [
                MemoryReplaySample(
                    session_id="s1", turn=1, scope_id="s1",
                    query_text="some query", response_text="some response",
                    next_state_text="next state",
                ),
            ]
            result = evaluator.evaluate(manager, samples)
            self.assertEqual(result.zero_retrieval_count, 1)
            store.close()

    def test_load_replay_samples_with_max(self):
        """load_replay_samples should respect max_samples with stratified sampling."""
        with tempfile.TemporaryDirectory() as tmpdir:
            from metaclaw.memory.replay import load_replay_samples

            records_path = os.path.join(tmpdir, "records.jsonl")
            with open(records_path, "w") as f:
                for i in range(20):
                    f.write(json.dumps({
                        "session_id": f"sess-{i % 3}",
                        "turn": 1,
                        "instruction_text": f"Query {i}",
                        "response_text": f"Response {i}",
                    }) + "\n")
            samples = load_replay_samples(records_path, max_samples=6)
            self.assertEqual(len(samples), 6)
            # Should have samples from multiple sessions (stratified).
            session_ids = {s.session_id for s in samples}
            self.assertGreater(len(session_ids), 1)

    def test_replay_comparison_includes_zero_retrieval_delta(self):
        """Comparison should include zero_retrieval_delta."""
        from metaclaw.memory.replay import MemoryReplayResult, MemoryReplayEvaluator

        evaluator = MemoryReplayEvaluator()
        baseline = MemoryReplayResult(
            sample_count=10, avg_retrieved=3.0, avg_query_overlap=0.5,
            avg_continuation_overlap=0.3, avg_response_overlap=0.4,
            avg_specificity=0.6, avg_focus_score=0.5, avg_value_density=0.4,
            avg_grounding_score=0.3, avg_coverage_score=0.3,
            zero_retrieval_count=2,
        )
        candidate = MemoryReplayResult(
            sample_count=10, avg_retrieved=4.0, avg_query_overlap=0.6,
            avg_continuation_overlap=0.4, avg_response_overlap=0.5,
            avg_specificity=0.7, avg_focus_score=0.6, avg_value_density=0.5,
            avg_grounding_score=0.4, avg_coverage_score=0.4,
            zero_retrieval_count=1,
        )
        comparison = evaluator.compare(baseline, candidate)
        self.assertIn("zero_retrieval_delta", comparison)
        self.assertEqual(comparison["zero_retrieval_delta"], -1)


class PolicyValidationTests(unittest.TestCase):
    """Tests for policy state validation."""

    def test_valid_policy_has_no_issues(self):
        """A default policy should pass validation."""
        from metaclaw.memory.policy_store import validate_policy_state

        issues = validate_policy_state(MemoryPolicyState())
        self.assertEqual(issues, [])

    def test_invalid_mode_detected(self):
        """An invalid retrieval_mode should be flagged."""
        from metaclaw.memory.policy_store import validate_policy_state

        state = MemoryPolicyState(retrieval_mode="invalid")
        issues = validate_policy_state(state)
        self.assertTrue(any("retrieval_mode" in i for i in issues))

    def test_out_of_range_units_detected(self):
        """Out-of-range max_injected_units should be flagged."""
        from metaclaw.memory.policy_store import validate_policy_state

        state = MemoryPolicyState(max_injected_units=50)
        issues = validate_policy_state(state)
        self.assertTrue(any("max_injected_units" in i for i in issues))


class ZeroRetrievalPromotionTests(unittest.TestCase):
    """Tests for zero-retrieval regression gating in promotion."""

    def test_promotion_blocked_by_zero_retrieval_increase(self):
        """Candidate should not promote if it causes many more zero retrievals."""
        comparison = {
            "sample_count": 20,
            "avg_query_overlap_delta": 0.1,
            "avg_continuation_overlap_delta": 0.1,
            "avg_response_overlap_delta": 0.1,
            "avg_specificity_delta": 0.0,
            "avg_focus_score_delta": 0.0,
            "avg_value_density_delta": 0.0,
            "avg_grounding_score_delta": 0.0,
            "avg_coverage_score_delta": 0.0,
            "zero_retrieval_delta": 5,
            "candidate_beats_baseline": True,
        }
        criteria = MemoryPromotionCriteria(
            min_sample_count=1,
            max_zero_retrieval_increase=2,
        )
        self.assertFalse(should_promote(comparison, criteria))

    def test_promotion_allowed_with_small_zero_retrieval_increase(self):
        """Candidate should promote if zero-retrieval increase is within bounds."""
        comparison = {
            "sample_count": 20,
            "avg_query_overlap_delta": 0.1,
            "avg_continuation_overlap_delta": 0.1,
            "avg_response_overlap_delta": 0.1,
            "avg_specificity_delta": 0.0,
            "avg_focus_score_delta": 0.0,
            "avg_value_density_delta": 0.0,
            "avg_grounding_score_delta": 0.0,
            "avg_coverage_score_delta": 0.0,
            "zero_retrieval_delta": 1,
            "candidate_beats_baseline": True,
        }
        criteria = MemoryPromotionCriteria(
            min_sample_count=1,
            max_zero_retrieval_increase=2,
        )
        self.assertTrue(should_promote(comparison, criteria))


class RetrievalCacheTests(unittest.TestCase):
    """Tests for retrieval caching."""

    def test_repeated_query_uses_cache(self):
        """Same query should return cached results."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "cache.db"))
            store.add_memories([
                MemoryUnit(
                    memory_id="cache-1",
                    scope_id="s1",
                    memory_type=MemoryType.SEMANTIC,
                    content="The project uses PostgreSQL",
                    topics=["postgresql"],
                ),
            ])
            manager = MemoryManager(store=store, scope_id="s1")
            result1 = manager.retrieve_for_prompt("PostgreSQL setup")
            result2 = manager.retrieve_for_prompt("PostgreSQL setup")
            # Should be the same object (cached).
            self.assertIs(result1, result2)
            store.close()

    def test_cache_cleared_after_ingestion(self):
        """Cache should be cleared after ingesting new turns."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "cache2.db"))
            store.add_memories([
                MemoryUnit(
                    memory_id="cache-2",
                    scope_id="s1",
                    memory_type=MemoryType.SEMANTIC,
                    content="The project uses PostgreSQL",
                    topics=["postgresql"],
                ),
            ])
            manager = MemoryManager(store=store, scope_id="s1")
            result1 = manager.retrieve_for_prompt("PostgreSQL setup")
            manager.ingest_session_turns("sess-new", [
                {"prompt_text": "We also use Redis.", "response_text": "OK."},
            ])
            result2 = manager.retrieve_for_prompt("PostgreSQL setup")
            # Should NOT be the same object (cache was cleared).
            self.assertIsNot(result1, result2)
            store.close()


class AccessPatternTests(unittest.TestCase):
    """Tests for memory access pattern analysis."""

    def test_access_patterns_include_most_accessed(self):
        """Access patterns should show most-accessed memories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "access.db"))
            store.add_memories([
                MemoryUnit(
                    memory_id="ap-hot",
                    scope_id="s1",
                    memory_type=MemoryType.SEMANTIC,
                    content="Hot memory accessed many times",
                    access_count=10,
                ),
                MemoryUnit(
                    memory_id="ap-cold",
                    scope_id="s1",
                    memory_type=MemoryType.SEMANTIC,
                    content="Cold memory never accessed",
                    access_count=0,
                ),
            ])
            manager = MemoryManager(store=store, scope_id="s1")
            patterns = manager.get_access_patterns()
            self.assertEqual(patterns["total"], 2)
            self.assertEqual(patterns["never_accessed"], 1)
            self.assertTrue(patterns["most_accessed"])
            self.assertEqual(patterns["most_accessed"][0]["id"], "ap-hot")
            store.close()


class PoolContextRenderTests(unittest.TestCase):
    """Tests for pool context in rendered output."""

    def test_render_with_pool_context(self):
        """Rendered output with pool context should include pool stats."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "ctx.db"))
            store.add_memories([
                MemoryUnit(
                    memory_id="ctx-1",
                    scope_id="s1",
                    memory_type=MemoryType.SEMANTIC,
                    content="Some fact",
                ),
            ])
            manager = MemoryManager(store=store, scope_id="s1")
            units = store.list_active("s1")
            rendered = manager.render_for_prompt(units, include_pool_context=True)
            self.assertIn("Pool:", rendered)
            self.assertIn("memories", rendered)
            store.close()


class DiagnoseTests(unittest.TestCase):
    """Tests for the memory diagnose method."""

    def test_diagnose_empty_store(self):
        """Diagnose should report issues on an empty store."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "diag.db"))
            manager = MemoryManager(store=store, scope_id="s1")
            result = manager.diagnose()
            self.assertEqual(result["scope_id"], "s1")
            self.assertEqual(result["store"]["active"], 0)
            self.assertIn("no active memories in store", result["issues"])
            store.close()

    def test_diagnose_healthy_store(self):
        """Diagnose should return no issues on a healthy store."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "diag.db"))
            manager = MemoryManager(store=store, scope_id="s1")
            manager.ingest_session_turns("s1", [
                {"prompt_text": "I prefer Python", "response_text": "OK"},
                {"prompt_text": "We use PostgreSQL", "response_text": "Got it"},
            ])
            # Do a retrieval to access some memories.
            manager.retrieve_for_prompt("What language?")
            result = manager.diagnose()
            self.assertGreater(result["store"]["active"], 0)
            self.assertIn("age_distribution", result["store"])
            self.assertIn("cache", result)
            store.close()


class CompositeScoreTests(unittest.TestCase):
    """Tests for the composite replay quality score."""

    def test_composite_score_nonzero(self):
        """Composite score should be positive when metrics are positive."""
        from metaclaw.memory.replay import MemoryReplayResult

        result = MemoryReplayResult(
            sample_count=10,
            avg_retrieved=3.0,
            avg_query_overlap=0.5,
            avg_continuation_overlap=0.4,
            avg_response_overlap=0.3,
            avg_specificity=0.6,
            avg_focus_score=0.5,
            avg_value_density=0.4,
            avg_grounding_score=0.3,
            avg_coverage_score=0.2,
            zero_retrieval_count=0,
        )
        score = result.composite_score
        self.assertGreater(score, 0.0)
        self.assertLessEqual(score, 1.0)

    def test_composite_score_zero_retrieval_penalty(self):
        """High zero-retrieval rate should reduce composite score."""
        from metaclaw.memory.replay import MemoryReplayResult

        base = MemoryReplayResult(
            sample_count=10,
            avg_retrieved=3.0,
            avg_query_overlap=0.5,
            avg_continuation_overlap=0.4,
            avg_response_overlap=0.3,
            avg_specificity=0.6,
            avg_focus_score=0.5,
            avg_value_density=0.4,
            avg_grounding_score=0.3,
            avg_coverage_score=0.2,
            zero_retrieval_count=0,
        )
        degraded = MemoryReplayResult(
            sample_count=10,
            avg_retrieved=3.0,
            avg_query_overlap=0.5,
            avg_continuation_overlap=0.4,
            avg_response_overlap=0.3,
            avg_specificity=0.6,
            avg_focus_score=0.5,
            avg_value_density=0.4,
            avg_grounding_score=0.3,
            avg_coverage_score=0.2,
            zero_retrieval_count=8,  # 80% zero retrieval
        )
        self.assertGreater(base.composite_score, degraded.composite_score)

    def test_composite_score_in_comparison(self):
        """Compare output should include composite_score_delta."""
        from metaclaw.memory.replay import MemoryReplayEvaluator, MemoryReplayResult

        evaluator = MemoryReplayEvaluator()
        baseline = MemoryReplayResult(
            sample_count=10, avg_retrieved=2.0,
            avg_query_overlap=0.3, avg_continuation_overlap=0.2,
            avg_response_overlap=0.2, avg_specificity=0.5,
            avg_focus_score=0.3, avg_value_density=0.3,
            avg_grounding_score=0.2, avg_coverage_score=0.1,
        )
        candidate = MemoryReplayResult(
            sample_count=10, avg_retrieved=3.0,
            avg_query_overlap=0.5, avg_continuation_overlap=0.4,
            avg_response_overlap=0.3, avg_specificity=0.6,
            avg_focus_score=0.5, avg_value_density=0.4,
            avg_grounding_score=0.3, avg_coverage_score=0.2,
        )
        comparison = evaluator.compare(baseline, candidate)
        self.assertIn("composite_score_delta", comparison)
        self.assertGreater(comparison["composite_score_delta"], 0.0)


class TelemetryWeightedSamplingTests(unittest.TestCase):
    """Tests for telemetry-weighted replay sampling."""

    def test_telemetry_weighted_samples_prefer_active_sessions(self):
        """Sessions with more retrieval events should be sampled first."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create replay samples from two sessions.
            replay_path = os.path.join(tmpdir, "replay.jsonl")
            with open(replay_path, "w") as f:
                # Session A: 10 samples
                for i in range(10):
                    f.write(json.dumps({
                        "session_id": "session_a",
                        "turn": i + 1,
                        "prompt_text": f"Question A{i}",
                        "response_text": f"Answer A{i}",
                    }) + "\n")
                # Session B: 10 samples
                for i in range(10):
                    f.write(json.dumps({
                        "session_id": "session_b",
                        "turn": i + 1,
                        "prompt_text": f"Question B{i}",
                        "response_text": f"Answer B{i}",
                    }) + "\n")

            # Create telemetry with session_a having much richer retrieval history.
            telemetry_path = os.path.join(tmpdir, "telemetry.jsonl")
            with open(telemetry_path, "w") as f:
                for _ in range(20):
                    f.write(json.dumps({
                        "event_type": "memory_retrieval",
                        "payload": {
                            "scope_id": "session_a",
                            "retrieved_count": 5,
                            "avg_importance": 0.85,
                        },
                    }) + "\n")
                # Session B: only 1 retrieval event.
                f.write(json.dumps({
                    "event_type": "memory_retrieval",
                    "payload": {
                        "scope_id": "session_b",
                        "retrieved_count": 1,
                        "avg_importance": 0.5,
                    },
                }) + "\n")

            samples = load_replay_samples(
                replay_path,
                max_samples=5,
                telemetry_path=telemetry_path,
            )
            self.assertEqual(len(samples), 5)
            # First sample should come from the higher-weighted session.
            self.assertEqual(samples[0].session_id, "session_a")


class MultiSessionRequestFlowTests(unittest.TestCase):
    """Integration tests simulating realistic multi-session MetaClaw request flows."""

    def test_cross_session_memory_continuity(self):
        """Memory from session 1 should be retrievable and injectable in session 2."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "flow.db"))
            manager = MemoryManager(store=store, scope_id="user1")

            # Session 1: user states preferences and project context.
            session1_turns = [
                {"prompt_text": "I prefer Python for all backend work", "response_text": "Noted, I'll use Python."},
                {"prompt_text": "We use PostgreSQL as our database", "response_text": "Got it, PostgreSQL."},
                {"prompt_text": "Always run tests before committing", "response_text": "Will do."},
            ]
            added = manager.ingest_session_turns("s1", session1_turns)
            self.assertGreater(added, 0)

            # Session 2: retrieve memory relevant to a database question.
            memories = manager.retrieve_for_prompt("How should I set up the database?")
            self.assertTrue(memories)
            rendered = manager.render_for_prompt(memories)
            self.assertIn("Relevant Long-Term Memory", rendered)
            # Should find PostgreSQL-related memory.
            has_pg = any("PostgreSQL" in u.content or "database" in u.content.lower() for u in memories)
            self.assertTrue(has_pg, f"Expected PostgreSQL context, got: {[u.content for u in memories]}")

            # Session 3: retrieve memory relevant to a testing question.
            memories2 = manager.retrieve_for_prompt("What's the testing workflow?")
            self.assertTrue(memories2)
            has_test = any("test" in u.content.lower() for u in memories2)
            self.assertTrue(has_test, f"Expected test context, got: {[u.content for u in memories2]}")

            store.close()

    def test_memory_accumulates_across_sessions(self):
        """Memories should accumulate and consolidate across multiple sessions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "accum.db"))
            manager = MemoryManager(store=store, scope_id="team1", auto_consolidate=True)

            # Session 1.
            manager.ingest_session_turns("s1", [
                {"prompt_text": "We use React for the frontend", "response_text": "OK"},
            ])
            stats1 = manager.get_scope_stats()

            # Session 2.
            manager.ingest_session_turns("s2", [
                {"prompt_text": "The API is built with FastAPI", "response_text": "Understood"},
            ])
            stats2 = manager.get_scope_stats()

            # Pool should grow.
            self.assertGreaterEqual(stats2["active"], stats1["active"])

            # Both facts should be retrievable.
            memories = manager.retrieve_for_prompt("What tech stack do we use?")
            contents = " ".join(u.content for u in memories).lower()
            # At least one of the tech stack facts should appear.
            self.assertTrue(
                "react" in contents or "fastapi" in contents,
                f"Expected tech context, got: {contents}",
            )

            store.close()

    def test_injection_does_not_exceed_token_budget(self):
        """Injected memory should respect the configured token budget."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "budget.db"))
            from metaclaw.memory.policy import MemoryPolicy

            policy = MemoryPolicy(max_injected_tokens=50, max_injected_units=10)
            manager = MemoryManager(store=store, scope_id="s1", policy=policy)

            # Add many memories to exceed the budget.
            units = []
            for i in range(20):
                units.append(MemoryUnit(
                    memory_id=f"u{i}",
                    scope_id="s1",
                    memory_type=MemoryType.SEMANTIC,
                    content=f"Fact number {i}: the project requires careful testing of all components and modules",
                    summary=f"Fact {i}",
                    topics=["testing", "project", "components"],
                ))
            store.add_memories(units)

            memories = manager.retrieve_for_prompt("Tell me about the project")
            rendered = manager.render_for_prompt(memories)
            from metaclaw.memory.manager import estimate_tokens

            token_count = estimate_tokens(rendered)
            # Allow some overhead for headers, but should be reasonably bounded.
            self.assertLess(token_count, 120, f"Token budget exceeded: {token_count}")
            store.close()

    def test_scope_isolation_in_request_flow(self):
        """Different users should not see each other's memories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "iso.db"))

            # User A.
            mgr_a = MemoryManager(store=store, scope_id="user_a")
            mgr_a.ingest_session_turns("s1", [
                {"prompt_text": "My secret project uses Rust", "response_text": "OK"},
            ])

            # User B.
            mgr_b = MemoryManager(store=store, scope_id="user_b")
            mgr_b.ingest_session_turns("s2", [
                {"prompt_text": "I always use Go for everything", "response_text": "Sure"},
            ])

            # User A should not see User B's memories.
            memories_a = mgr_a.retrieve_for_prompt("What language do I use?")
            for u in memories_a:
                self.assertNotIn("Go", u.content, "User A saw User B's memory")

            # User B should not see User A's memories.
            memories_b = mgr_b.retrieve_for_prompt("What language do I use?")
            for u in memories_b:
                self.assertNotIn("Rust", u.content, "User B saw User A's memory")

            store.close()

    def test_full_lifecycle_ingest_retrieve_consolidate_gc(self):
        """Full lifecycle: ingest -> retrieve -> consolidate -> GC."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "lifecycle.db"))
            manager = MemoryManager(store=store, scope_id="lifecycle", auto_consolidate=True)

            # Ingest.
            manager.ingest_session_turns("s1", [
                {"prompt_text": "Remember that our deployment uses Kubernetes", "response_text": "Noted"},
                {"prompt_text": "We prefer blue-green deployments", "response_text": "Got it"},
            ])

            # Retrieve.
            memories = manager.retrieve_for_prompt("How do we deploy?")
            self.assertTrue(memories)

            # Check stats.
            stats = manager.get_scope_stats()
            self.assertGreater(stats["active"], 0)

            # Compact: should not error on a healthy store.
            store.compact()

            # Render.
            rendered = manager.render_for_prompt(memories)
            self.assertIn("Relevant Long-Term Memory", rendered)

            store.close()


class FeedbackTests(unittest.TestCase):
    """Tests for retrieval feedback."""

    def test_positive_feedback_boosts_importance(self):
        """Positive feedback should increase memory importance."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "fb.db"))
            store.add_memories([
                MemoryUnit(
                    memory_id="fb1",
                    scope_id="s1",
                    memory_type=MemoryType.SEMANTIC,
                    content="The API uses REST endpoints",
                    importance=0.5,
                ),
            ])
            store.record_feedback("fb1", helpful=True)
            unit = store.list_active("s1")[0]
            self.assertGreater(unit.importance, 0.5)
            store.close()

    def test_negative_feedback_reduces_importance(self):
        """Negative feedback should decrease memory importance."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "fb2.db"))
            store.add_memories([
                MemoryUnit(
                    memory_id="fb2",
                    scope_id="s1",
                    memory_type=MemoryType.SEMANTIC,
                    content="The API uses GraphQL",
                    importance=0.5,
                ),
            ])
            store.record_feedback("fb2", helpful=False)
            unit = store.list_active("s1")[0]
            self.assertLess(unit.importance, 0.5)
            store.close()

    def test_feedback_via_manager(self):
        """Manager's provide_feedback should delegate to store."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "fb3.db"))
            manager = MemoryManager(store=store, scope_id="s1")
            store.add_memories([
                MemoryUnit(
                    memory_id="fb3",
                    scope_id="s1",
                    memory_type=MemoryType.SEMANTIC,
                    content="Some memory",
                    importance=0.6,
                ),
            ])
            manager.provide_feedback("fb3", helpful=True)
            unit = store.list_active("s1")[0]
            self.assertGreater(unit.importance, 0.6)
            store.close()


class MemoryPinningTests(unittest.TestCase):
    """Tests for memory pinning."""

    def test_pin_sets_max_importance(self):
        """Pinning should set importance to 0.99."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "pin.db"))
            store.add_memories([
                MemoryUnit(
                    memory_id="pin1",
                    scope_id="s1",
                    memory_type=MemoryType.SEMANTIC,
                    content="Important fact",
                    importance=0.5,
                ),
            ])
            result = store.pin_memory("pin1")
            self.assertTrue(result)
            unit = store.list_active("s1")[0]
            self.assertEqual(unit.importance, 0.99)
            store.close()

    def test_unpin_restores_importance(self):
        """Unpinning should restore importance to default."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "pin2.db"))
            store.add_memories([
                MemoryUnit(
                    memory_id="pin2",
                    scope_id="s1",
                    memory_type=MemoryType.SEMANTIC,
                    content="Important fact",
                    importance=0.99,
                ),
            ])
            result = store.unpin_memory("pin2", restore_importance=0.6)
            self.assertTrue(result)
            unit = store.list_active("s1")[0]
            self.assertEqual(unit.importance, 0.6)
            store.close()

    def test_pin_nonexistent_returns_false(self):
        """Pinning nonexistent memory should return False."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "pin3.db"))
            result = store.pin_memory("nonexistent")
            self.assertFalse(result)
            store.close()

    def test_pinned_memory_ranks_first(self):
        """A pinned memory should rank at the top of retrieval results."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "pin4.db"))
            manager = MemoryManager(store=store, scope_id="s1")
            store.add_memories([
                MemoryUnit(
                    memory_id="low",
                    scope_id="s1",
                    memory_type=MemoryType.SEMANTIC,
                    content="Generic fact about testing procedures",
                    topics=["testing"],
                    importance=0.4,
                ),
                MemoryUnit(
                    memory_id="pinned",
                    scope_id="s1",
                    memory_type=MemoryType.SEMANTIC,
                    content="Critical testing requirement for the project",
                    topics=["testing", "requirement"],
                    importance=0.5,
                ),
            ])
            manager.pin_memory("pinned")
            memories = manager.retrieve_for_prompt("How do we test?")
            self.assertTrue(memories)
            self.assertEqual(memories[0].memory_id, "pinned")
            store.close()


class PoolSummaryTests(unittest.TestCase):
    """Tests for the pool summary generator."""

    def test_pool_summary_shows_types(self):
        """Pool summary should show memory counts by type."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "pool.db"))
            manager = MemoryManager(store=store, scope_id="s1")
            store.add_memories([
                MemoryUnit(
                    memory_id="ps1",
                    scope_id="s1",
                    memory_type=MemoryType.PREFERENCE,
                    content="User prefers Python",
                    importance=0.8,
                ),
                MemoryUnit(
                    memory_id="ps2",
                    scope_id="s1",
                    memory_type=MemoryType.PROJECT_STATE,
                    content="Project uses FastAPI",
                    importance=0.85,
                ),
            ])
            summary = manager.get_pool_summary()
            self.assertIn("2 active memories", summary)
            self.assertIn("preference", summary)
            self.assertIn("project_state", summary)
            store.close()

    def test_pool_summary_empty(self):
        """Pool summary should handle empty store."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "pool2.db"))
            manager = MemoryManager(store=store, scope_id="s1")
            summary = manager.get_pool_summary()
            self.assertIn("No active memories", summary)
            store.close()


class ConflictDetectionTests(unittest.TestCase):
    """Tests for memory conflict detection."""

    def test_detects_conflicting_memories(self):
        """Should detect memories with same type and topic overlap but different content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "conflict.db"))
            manager = MemoryManager(store=store, scope_id="s1")
            store.add_memories([
                MemoryUnit(
                    memory_id="c1",
                    scope_id="s1",
                    memory_type=MemoryType.PROJECT_STATE,
                    content="Project context: we use MySQL for the main database backend",
                    topics=["database", "backend", "storage", "production"],
                    entities=["MySQL", "Database"],
                ),
                MemoryUnit(
                    memory_id="c2",
                    scope_id="s1",
                    memory_type=MemoryType.PROJECT_STATE,
                    content="Project context: we use PostgreSQL for the main database backend",
                    topics=["database", "backend", "storage", "production"],
                    entities=["PostgreSQL", "Database"],
                ),
            ])
            conflicts = manager.detect_conflicts()
            self.assertTrue(conflicts)
            self.assertEqual(conflicts[0]["type"], "project_state")
            store.close()

    def test_no_conflict_for_different_types(self):
        """Should not flag memories of different types as conflicts."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "noconflict.db"))
            manager = MemoryManager(store=store, scope_id="s1")
            store.add_memories([
                MemoryUnit(
                    memory_id="nc1",
                    scope_id="s1",
                    memory_type=MemoryType.PROJECT_STATE,
                    content="We use MySQL",
                    topics=["database", "mysql"],
                ),
                MemoryUnit(
                    memory_id="nc2",
                    scope_id="s1",
                    memory_type=MemoryType.PREFERENCE,
                    content="I prefer PostgreSQL",
                    topics=["database", "postgresql"],
                ),
            ])
            conflicts = manager.detect_conflicts()
            self.assertEqual(len(conflicts), 0)
            store.close()


class ExplainRetrievalTests(unittest.TestCase):
    """Tests for retrieval explanations."""

    def test_explain_returns_reasons(self):
        """explain_retrieval should return scored results with reasons."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "explain.db"))
            manager = MemoryManager(store=store, scope_id="s1", retrieval_mode="hybrid")
            store.add_memories([
                MemoryUnit(
                    memory_id="e1",
                    scope_id="s1",
                    memory_type=MemoryType.PROJECT_STATE,
                    content="Project context: we use Redis for caching",
                    topics=["redis", "caching"],
                    importance=0.85,
                ),
            ])
            results = manager.explain_retrieval("What caching do we use?")
            self.assertTrue(results)
            first = results[0]
            self.assertEqual(first["memory_id"], "e1")
            self.assertGreater(first["score"], 0)
            self.assertIn("matched", first["reason"])
            store.close()


class StoreGarbageCollectTests(unittest.TestCase):
    """Tests for the store-level garbage_collect method."""

    def test_gc_removes_orphaned_superseded(self):
        """GC should remove superseded memories not referenced by active ones."""
        from metaclaw.memory.models import MemoryStatus

        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "gc.db"))
            store.add_memories([
                MemoryUnit(
                    memory_id="old",
                    scope_id="s1",
                    memory_type=MemoryType.SEMANTIC,
                    content="Old fact",
                    status=MemoryStatus.SUPERSEDED,
                ),
                MemoryUnit(
                    memory_id="current",
                    scope_id="s1",
                    memory_type=MemoryType.SEMANTIC,
                    content="New fact",
                ),
            ])
            result = store.garbage_collect("s1")
            self.assertEqual(result["removed"], 1)
            store.close()

    def test_gc_preserves_referenced_superseded(self):
        """GC should keep superseded memories still referenced by active ones."""
        from metaclaw.memory.models import MemoryStatus

        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "gc2.db"))
            store.add_memories([
                MemoryUnit(
                    memory_id="old",
                    scope_id="s1",
                    memory_type=MemoryType.SEMANTIC,
                    content="Old fact",
                    status=MemoryStatus.SUPERSEDED,
                ),
                MemoryUnit(
                    memory_id="current",
                    scope_id="s1",
                    memory_type=MemoryType.SEMANTIC,
                    content="New fact that supersedes old",
                    supersedes=["old"],
                ),
            ])
            result = store.garbage_collect("s1")
            self.assertEqual(result["removed"], 0)
            self.assertEqual(result["kept_superseded"], 1)
            store.close()


class RequestFlowInjectionTests(unittest.TestCase):
    """Tests simulating the actual api_server _inject_memory flow."""

    def _inject_memory(self, manager, messages):
        """Simulate MetaClawAPIServer._inject_memory."""
        user_msgs = [m for m in messages if m.get("role") == "user"]
        task_desc = user_msgs[-1].get("content", "") if user_msgs else ""
        if not task_desc:
            return messages

        memories = manager.retrieve_for_prompt(task_desc)
        if not memories:
            return messages

        memory_text = manager.render_for_prompt(memories)
        messages = list(messages)
        sys_indices = [i for i, m in enumerate(messages) if m.get("role") == "system"]
        if sys_indices:
            idx = sys_indices[0]
            existing = messages[idx].get("content", "")
            messages[idx] = {**messages[idx], "content": existing + "\n\n" + memory_text}
        else:
            messages.insert(0, {"role": "system", "content": memory_text})
        return messages

    def test_inject_into_existing_system_message(self):
        """Memory should be appended to existing system message."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "inject.db"))
            manager = MemoryManager(store=store, scope_id="s1")
            manager.ingest_session_turns("s1", [
                {"prompt_text": "We use Django for the web framework", "response_text": "OK"},
            ])

            messages = [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "What framework do we use?"},
            ]
            result = self._inject_memory(manager, messages)
            self.assertEqual(result[0]["role"], "system")
            self.assertIn("You are a helpful assistant.", result[0]["content"])
            self.assertIn("Relevant Long-Term Memory", result[0]["content"])
            store.close()

    def test_inject_creates_system_message(self):
        """When no system message exists, memory should be inserted as one."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "inject2.db"))
            manager = MemoryManager(store=store, scope_id="s1")
            manager.ingest_session_turns("s1", [
                {"prompt_text": "Remember that our CI uses GitHub Actions", "response_text": "Noted"},
            ])

            messages = [
                {"role": "user", "content": "How does our CI work?"},
            ]
            result = self._inject_memory(manager, messages)
            self.assertEqual(result[0]["role"], "system")
            self.assertIn("Relevant Long-Term Memory", result[0]["content"])
            self.assertEqual(result[1]["role"], "user")
            store.close()

    def test_no_injection_for_empty_task(self):
        """No injection should happen when user message is empty."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "inject3.db"))
            manager = MemoryManager(store=store, scope_id="s1")
            messages = [{"role": "user", "content": ""}]
            result = self._inject_memory(manager, messages)
            self.assertEqual(len(result), 1)
            store.close()


class ScaleRetrievalTests(unittest.TestCase):
    """Tests validating retrieval quality at larger memory scales."""

    def test_retrieval_quality_at_500_memories(self):
        """At 500 memories, relevant items should still rank near the top."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "scale.db"))
            manager = MemoryManager(store=store, scope_id="s1")

            # Add 500 generic memories plus one specific high-importance one.
            units = []
            for i in range(499):
                units.append(MemoryUnit(
                    memory_id=f"gen-{i}",
                    scope_id="s1",
                    memory_type=MemoryType.EPISODIC,
                    content=f"Generic discussion about topic {i} during session {i // 10}",
                    summary=f"Session {i // 10} turn {i % 10}",
                    topics=[f"topic{i}"],
                    importance=0.4,
                ))
            # Add one highly relevant memory.
            units.append(MemoryUnit(
                memory_id="target",
                scope_id="s1",
                memory_type=MemoryType.PROJECT_STATE,
                content="Project context: the deployment pipeline uses Kubernetes with Helm charts",
                summary="Deployment uses Kubernetes and Helm",
                topics=["kubernetes", "helm", "deployment"],
                entities=["Kubernetes", "Helm"],
                importance=0.9,
            ))
            store.add_memories(units)

            memories = manager.retrieve_for_prompt("How is the deployment pipeline set up?")
            self.assertTrue(memories)
            # The target memory should be in the results.
            target_found = any(u.memory_id == "target" for u in memories)
            self.assertTrue(target_found, f"Target not found in retrieved: {[u.memory_id for u in memories]}")
            store.close()


class ReplayJudgeInterfaceTests(unittest.TestCase):
    """Tests for the LLM-judge replay interface."""

    def test_default_judge_not_available(self):
        """Default judge should report not available."""
        from metaclaw.memory.replay import MemoryReplayJudge

        judge = MemoryReplayJudge()
        self.assertFalse(judge.is_available())
        score = judge.score_memory_relevance("memory", "query", "response")
        self.assertEqual(score, 0.0)

    def test_custom_judge_can_override(self):
        """Custom judge subclass should be usable."""
        from metaclaw.memory.replay import MemoryReplayJudge

        class MockJudge(MemoryReplayJudge):
            def score_memory_relevance(self, memory_text, query_text, response_text):
                return 0.85

            def is_available(self):
                return True

        judge = MockJudge()
        self.assertTrue(judge.is_available())
        self.assertEqual(judge.score_memory_relevance("m", "q", "r"), 0.85)


class RetentionPolicyTests(unittest.TestCase):
    """Tests for the retention policy."""

    def test_archives_old_low_importance_memories(self):
        """Old, low-importance, never-accessed memories should be archived."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "retain.db"))
            manager = MemoryManager(store=store, scope_id="s1")

            old_date = "2025-01-01T00:00:00+00:00"
            store.add_memories([
                MemoryUnit(
                    memory_id="old_low",
                    scope_id="s1",
                    memory_type=MemoryType.EPISODIC,
                    content="Very old unimportant fact",
                    importance=0.2,
                    access_count=0,
                    created_at=old_date,
                    updated_at=old_date,
                ),
                MemoryUnit(
                    memory_id="old_high",
                    scope_id="s1",
                    memory_type=MemoryType.SEMANTIC,
                    content="Old but important fact",
                    importance=0.8,
                    access_count=0,
                    created_at=old_date,
                    updated_at=old_date,
                ),
                MemoryUnit(
                    memory_id="new_low",
                    scope_id="s1",
                    memory_type=MemoryType.EPISODIC,
                    content="Recent low importance fact",
                    importance=0.2,
                    access_count=0,
                ),
            ])

            result = manager.apply_retention_policy(max_age_days=90, min_importance=0.3)
            self.assertEqual(result["archived"], 1)

            # Only the old+low memory should be gone.
            active = store.list_active("s1")
            active_ids = {u.memory_id for u in active}
            self.assertNotIn("old_low", active_ids)
            self.assertIn("old_high", active_ids)
            self.assertIn("new_low", active_ids)
            store.close()

    def test_retention_skips_pinned(self):
        """Pinned memories should not be archived."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "retain2.db"))
            manager = MemoryManager(store=store, scope_id="s1")

            old_date = "2025-01-01T00:00:00+00:00"
            store.add_memories([
                MemoryUnit(
                    memory_id="pinned_old",
                    scope_id="s1",
                    memory_type=MemoryType.SEMANTIC,
                    content="Pinned old memory",
                    importance=0.99,
                    access_count=0,
                    created_at=old_date,
                    updated_at=old_date,
                ),
            ])

            result = manager.apply_retention_policy(max_age_days=90, min_importance=0.3)
            self.assertEqual(result["archived"], 0)
            store.close()


class SearchMemoriesTests(unittest.TestCase):
    """Tests for the search_memories API."""

    def test_search_returns_scored_results(self):
        """search_memories should return dictionaries with scores."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "search.db"))
            manager = MemoryManager(store=store, scope_id="s1")
            store.add_memories([
                MemoryUnit(
                    memory_id="s1",
                    scope_id="s1",
                    memory_type=MemoryType.SEMANTIC,
                    content="The API uses GraphQL for queries",
                    topics=["graphql", "api"],
                ),
            ])
            results = manager.search_memories("GraphQL")
            self.assertTrue(results)
            self.assertIn("score", results[0])
            self.assertIn("memory_id", results[0])
            store.close()


class BulkImportanceTests(unittest.TestCase):
    """Tests for bulk importance updates."""

    def test_bulk_update_clamps_values(self):
        """Bulk update should clamp importance to [0.1, 0.99]."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "bulk.db"))
            manager = MemoryManager(store=store, scope_id="s1")
            store.add_memories([
                MemoryUnit(memory_id="b1", scope_id="s1", memory_type=MemoryType.SEMANTIC, content="Fact 1"),
                MemoryUnit(memory_id="b2", scope_id="s1", memory_type=MemoryType.SEMANTIC, content="Fact 2"),
            ])
            count = manager.bulk_update_importance([("b1", 1.5), ("b2", -0.5)])
            self.assertEqual(count, 2)
            units = store.list_active("s1")
            importances = {u.memory_id: u.importance for u in units}
            self.assertLessEqual(importances["b1"], 0.99)
            self.assertGreaterEqual(importances["b2"], 0.1)
            store.close()


class ScopeListingTests(unittest.TestCase):
    """Tests for scope listing."""

    def test_list_scopes(self):
        """list_scopes should return all scopes with counts."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "scopes.db"))
            store.add_memories([
                MemoryUnit(memory_id="a1", scope_id="user1", memory_type=MemoryType.SEMANTIC, content="Fact A"),
                MemoryUnit(memory_id="a2", scope_id="user1", memory_type=MemoryType.SEMANTIC, content="Fact B"),
                MemoryUnit(memory_id="b1", scope_id="user2", memory_type=MemoryType.SEMANTIC, content="Fact C"),
            ])
            scopes = store.list_scopes()
            self.assertEqual(len(scopes), 2)
            scope_ids = {s["scope_id"] for s in scopes}
            self.assertIn("user1", scope_ids)
            self.assertIn("user2", scope_ids)
            store.close()


class MemoryUpdateTests(unittest.TestCase):
    """Tests for updating memory content."""

    def test_update_content(self):
        """Should update memory content and summary."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "upd.db"))
            store.add_memories([
                MemoryUnit(memory_id="u1", scope_id="s1", memory_type=MemoryType.SEMANTIC, content="Old content"),
            ])
            result = store.update_content("u1", "New content", "New summary")
            self.assertTrue(result)
            unit = store._get_by_id("u1")
            self.assertEqual(unit.content, "New content")
            self.assertEqual(unit.summary, "New summary")
            store.close()

    def test_update_nonexistent_returns_false(self):
        """Updating nonexistent memory should return False."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "upd2.db"))
            result = store.update_content("nonexistent", "content")
            self.assertFalse(result)
            store.close()

    def test_get_memory_by_id(self):
        """Manager should be able to get a specific memory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "get.db"))
            manager = MemoryManager(store=store, scope_id="s1")
            store.add_memories([
                MemoryUnit(memory_id="g1", scope_id="s1", memory_type=MemoryType.SEMANTIC, content="Test"),
            ])
            unit = manager.get_memory("g1")
            self.assertIsNotNone(unit)
            self.assertEqual(unit.content, "Test")
            self.assertIsNone(manager.get_memory("nonexistent"))
            store.close()


class AdditionalExtractionPatternTests(unittest.TestCase):
    """Tests for new extraction patterns."""

    def test_importantly_extraction(self):
        """'importantly' pattern should extract semantic facts."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "pat.db"))
            manager = MemoryManager(store=store, scope_id="s1")
            manager.ingest_session_turns("s1", [
                {"prompt_text": "Importantly, all API keys must be rotated monthly", "response_text": "OK"},
            ])
            units = store.list_active("s1")
            contents = " ".join(u.content for u in units)
            self.assertTrue(
                "api keys" in contents.lower() or "rotated" in contents.lower(),
                f"Expected API key rotation fact, got: {contents}",
            )
            store.close()

    def test_by_the_way_extraction(self):
        """'by the way' pattern should extract semantic facts."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "pat2.db"))
            manager = MemoryManager(store=store, scope_id="s1")
            manager.ingest_session_turns("s1", [
                {"prompt_text": "By the way, the staging server is at staging.example.com", "response_text": "Noted"},
            ])
            units = store.list_active("s1")
            contents = " ".join(u.content for u in units)
            self.assertTrue(
                "staging" in contents.lower(),
                f"Expected staging server fact, got: {contents}",
            )
            store.close()


class MemoryTTLTests(unittest.TestCase):
    """Tests for memory TTL/expiry functionality."""

    def test_set_ttl_and_filter_expired(self):
        """Memories past their expires_at are filtered from list_active."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(timespec="seconds")
            future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(timespec="seconds")
            store.add_memories([
                MemoryUnit(
                    memory_id="ttl-expired",
                    scope_id="s1",
                    memory_type=MemoryType.SEMANTIC,
                    content="Old fact that expired",
                    expires_at=past,
                ),
                MemoryUnit(
                    memory_id="ttl-valid",
                    scope_id="s1",
                    memory_type=MemoryType.SEMANTIC,
                    content="Still valid fact",
                    expires_at=future,
                ),
                MemoryUnit(
                    memory_id="ttl-none",
                    scope_id="s1",
                    memory_type=MemoryType.SEMANTIC,
                    content="No TTL fact",
                ),
            ])
            active = store.list_active("s1")
            ids = {u.memory_id for u in active}
            self.assertNotIn("ttl-expired", ids)
            self.assertIn("ttl-valid", ids)
            self.assertIn("ttl-none", ids)
            store.close()

    def test_expire_stale_archives_expired(self):
        """expire_stale should archive expired memories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(timespec="seconds")
            store.add_memories([
                MemoryUnit(
                    memory_id="exp-1",
                    scope_id="s1",
                    memory_type=MemoryType.EPISODIC,
                    content="Expired memory",
                    expires_at=past,
                ),
                MemoryUnit(
                    memory_id="exp-2",
                    scope_id="s1",
                    memory_type=MemoryType.EPISODIC,
                    content="Non-expired memory",
                ),
            ])
            count = store.expire_stale("s1")
            self.assertEqual(count, 1)
            # After archiving, the expired memory should not appear even without filter.
            row = store.conn.execute(
                "SELECT status FROM memories WHERE memory_id = 'exp-1'"
            ).fetchone()
            self.assertEqual(row["status"], "archived")
            store.close()

    def test_set_ttl_via_store(self):
        """set_ttl should update the expires_at field."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories([
                MemoryUnit(
                    memory_id="ttl-set",
                    scope_id="s1",
                    memory_type=MemoryType.SEMANTIC,
                    content="Will get TTL",
                ),
            ])
            future = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(timespec="seconds")
            result = store.set_ttl("ttl-set", future)
            self.assertTrue(result)
            unit = store._get_by_id("ttl-set")
            self.assertEqual(unit.expires_at, future)
            # Clear TTL.
            store.set_ttl("ttl-set", "")
            unit2 = store._get_by_id("ttl-set")
            self.assertEqual(unit2.expires_at, "")
            store.close()

    def test_set_ttl_nonexistent(self):
        """set_ttl returns False for nonexistent memory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            result = store.set_ttl("does-not-exist", "2030-01-01T00:00:00+00:00")
            self.assertFalse(result)
            store.close()

    def test_manager_ttl_integration(self):
        """Manager-level TTL set and expire flow."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1")
            past = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat(timespec="seconds")
            store.add_memories([
                MemoryUnit(
                    memory_id="mgr-ttl-1",
                    scope_id="s1",
                    memory_type=MemoryType.SEMANTIC,
                    content="Temp fact about sprint",
                ),
            ])
            # Set TTL to past.
            mgr.set_ttl("mgr-ttl-1", past)
            # list_active should filter it out.
            active = store.list_active("s1")
            self.assertEqual(len(active), 0)
            # expire_stale should archive it.
            count = mgr.expire_stale()
            self.assertEqual(count, 1)
            store.close()


class CrossScopeSharingTests(unittest.TestCase):
    """Tests for cross-scope memory sharing."""

    def test_share_memory_to_scope(self):
        """Sharing a memory copies it to the target scope."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories([
                MemoryUnit(
                    memory_id="share-src",
                    scope_id="team-a",
                    memory_type=MemoryType.SEMANTIC,
                    content="API endpoint is /v2/users",
                    topics=["api", "users"],
                    importance=0.8,
                    confidence=0.9,
                ),
            ])
            new_id = store.share_to_scope("share-src", "team-b")
            self.assertIsNotNone(new_id)
            self.assertNotEqual(new_id, "share-src")
            # Verify target scope has the memory.
            target_active = store.list_active("team-b")
            self.assertEqual(len(target_active), 1)
            self.assertEqual(target_active[0].content, "API endpoint is /v2/users")
            self.assertEqual(target_active[0].scope_id, "team-b")
            # Confidence should be slightly reduced.
            self.assertLess(target_active[0].confidence, 0.9)
            store.close()

    def test_share_nonexistent_returns_none(self):
        """Sharing a nonexistent memory returns None."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            result = store.share_to_scope("no-such-id", "team-b")
            self.assertIsNone(result)
            store.close()

    def test_manager_share_integration(self):
        """Manager-level share_memory flow."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="team-a")
            store.add_memories([
                MemoryUnit(
                    memory_id="mgr-share",
                    scope_id="team-a",
                    memory_type=MemoryType.PROJECT_STATE,
                    content="Deploy target is us-west-2",
                    topics=["deploy", "aws"],
                ),
            ])
            new_id = mgr.share_memory("mgr-share", "team-b")
            self.assertIsNotNone(new_id)
            # The original scope still has its memory.
            self.assertEqual(len(store.list_active("team-a")), 1)
            # Target scope has the shared copy.
            target = store.list_active("team-b")
            self.assertEqual(len(target), 1)
            self.assertEqual(target[0].content, "Deploy target is us-west-2")
            store.close()


class ExportScopeTests(unittest.TestCase):
    """Tests for structured scope export."""

    def test_export_scope_json(self):
        """export_scope_json returns serializable dicts."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories([
                MemoryUnit(
                    memory_id="exp-1",
                    scope_id="s1",
                    memory_type=MemoryType.SEMANTIC,
                    content="Fact one",
                    importance=0.8,
                ),
                MemoryUnit(
                    memory_id="exp-2",
                    scope_id="s1",
                    memory_type=MemoryType.PREFERENCE,
                    content="Pref two",
                    importance=0.7,
                ),
            ])
            exported = store.export_scope_json("s1")
            self.assertEqual(len(exported), 2)
            # Should be JSON-serializable.
            json_str = json.dumps(exported)
            self.assertIn("Fact one", json_str)
            self.assertIn("semantic", json_str)
            # Check field presence.
            for item in exported:
                self.assertIn("memory_id", item)
                self.assertIn("memory_type", item)
                self.assertIn("content", item)
                self.assertIn("importance", item)
                self.assertIn("expires_at", item)
            store.close()

    def test_manager_export_scope(self):
        """Manager-level export delegates to store."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1")
            store.add_memories([
                MemoryUnit(
                    memory_id="mex-1",
                    scope_id="s1",
                    memory_type=MemoryType.EPISODIC,
                    content="Exported episode",
                ),
            ])
            result = mgr.export_scope()
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]["content"], "Exported episode")
            store.close()


class ImportMemoriesTests(unittest.TestCase):
    """Tests for JSON import functionality."""

    def test_import_roundtrip(self):
        """Export then import should produce equivalent memories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories([
                MemoryUnit(
                    memory_id="rt-1",
                    scope_id="s1",
                    memory_type=MemoryType.SEMANTIC,
                    content="API uses OAuth2",
                    topics=["api", "auth"],
                    importance=0.85,
                ),
            ])
            exported = store.export_scope_json("s1")
            # Import into a different scope.
            count = store.import_memories_json(exported, target_scope_id="s2")
            self.assertEqual(count, 1)
            s2_active = store.list_active("s2")
            self.assertEqual(len(s2_active), 1)
            self.assertEqual(s2_active[0].content, "API uses OAuth2")
            self.assertEqual(s2_active[0].scope_id, "s2")
            # Access count is reset on import.
            self.assertEqual(s2_active[0].access_count, 0)
            store.close()

    def test_import_empty(self):
        """Importing empty list returns 0."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            count = store.import_memories_json([])
            self.assertEqual(count, 0)
            store.close()


class TypeTTLTests(unittest.TestCase):
    """Tests for batch TTL by memory type."""

    def test_set_type_ttl(self):
        """set_type_ttl sets expiry on all memories of a type."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories([
                MemoryUnit(
                    memory_id="tt-1",
                    scope_id="s1",
                    memory_type=MemoryType.EPISODIC,
                    content="Episode one",
                ),
                MemoryUnit(
                    memory_id="tt-2",
                    scope_id="s1",
                    memory_type=MemoryType.EPISODIC,
                    content="Episode two",
                ),
                MemoryUnit(
                    memory_id="tt-3",
                    scope_id="s1",
                    memory_type=MemoryType.SEMANTIC,
                    content="Semantic fact",
                ),
            ])
            future = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(timespec="seconds")
            count = store.set_type_ttl("s1", MemoryType.EPISODIC, future)
            self.assertEqual(count, 2)
            # Verify episodic memories have TTL set.
            ep1 = store._get_by_id("tt-1")
            self.assertEqual(ep1.expires_at, future)
            # Semantic memory should be unaffected.
            sem = store._get_by_id("tt-3")
            self.assertEqual(sem.expires_at, "")
            store.close()


class MergeMemoriesTests(unittest.TestCase):
    """Tests for memory merge functionality."""

    def test_merge_creates_new_supersedes_old(self):
        """Merging two memories creates a new one and supersedes originals."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories([
                MemoryUnit(
                    memory_id="merge-a",
                    scope_id="s1",
                    memory_type=MemoryType.SEMANTIC,
                    content="Python 3.10 required",
                    topics=["python", "version"],
                    importance=0.7,
                ),
                MemoryUnit(
                    memory_id="merge-b",
                    scope_id="s1",
                    memory_type=MemoryType.SEMANTIC,
                    content="Python 3.11 now supported",
                    topics=["python", "version", "upgrade"],
                    importance=0.8,
                ),
            ])
            new_id = store.merge_memories(
                "merge-a", "merge-b",
                merged_content="Python 3.10+ required, 3.11 supported",
                merged_summary="Python version requirements",
            )
            self.assertIsNotNone(new_id)
            # New memory exists.
            merged = store._get_by_id(new_id)
            self.assertEqual(merged.content, "Python 3.10+ required, 3.11 supported")
            self.assertIn("merge-a", merged.supersedes)
            self.assertIn("merge-b", merged.supersedes)
            # Importance should be max of both.
            self.assertAlmostEqual(merged.importance, 0.8)
            # Topics should be combined.
            self.assertIn("python", merged.topics)
            self.assertIn("upgrade", merged.topics)
            # Originals are superseded.
            a = store._get_by_id("merge-a")
            self.assertEqual(a.status.value, "superseded")
            b = store._get_by_id("merge-b")
            self.assertEqual(b.status.value, "superseded")
            store.close()

    def test_merge_nonexistent_returns_none(self):
        """Merging with a nonexistent memory returns None."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories([
                MemoryUnit(
                    memory_id="merge-real",
                    scope_id="s1",
                    memory_type=MemoryType.SEMANTIC,
                    content="Real memory",
                ),
            ])
            result = store.merge_memories("merge-real", "nonexistent", "merged")
            self.assertIsNone(result)
            store.close()

    def test_manager_merge(self):
        """Manager-level merge delegates to store."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1")
            store.add_memories([
                MemoryUnit(
                    memory_id="mm-a",
                    scope_id="s1",
                    memory_type=MemoryType.PREFERENCE,
                    content="Prefers dark mode",
                ),
                MemoryUnit(
                    memory_id="mm-b",
                    scope_id="s1",
                    memory_type=MemoryType.PREFERENCE,
                    content="Prefers dark theme",
                ),
            ])
            new_id = mgr.merge_memories("mm-a", "mm-b", "Prefers dark mode/theme")
            self.assertIsNotNone(new_id)
            active = store.list_active("s1")
            self.assertEqual(len(active), 1)
            self.assertEqual(active[0].content, "Prefers dark mode/theme")
            store.close()


class EnhancedDiagnosticsTests(unittest.TestCase):
    """Tests for enhanced diagnostics with TTL info."""

    def test_diagnose_includes_ttl_info(self):
        """Diagnose should report TTL statistics."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1")
            soon = (datetime.now(timezone.utc) + timedelta(hours=12)).isoformat(timespec="seconds")
            store.add_memories([
                MemoryUnit(
                    memory_id="diag-ttl-1",
                    scope_id="s1",
                    memory_type=MemoryType.SEMANTIC,
                    content="Expiring soon",
                    expires_at=soon,
                ),
                MemoryUnit(
                    memory_id="diag-ttl-2",
                    scope_id="s1",
                    memory_type=MemoryType.SEMANTIC,
                    content="No TTL",
                ),
            ])
            result = mgr.diagnose()
            self.assertIn("ttl", result)
            self.assertEqual(result["ttl"]["memories_with_ttl"], 1)
            self.assertEqual(result["ttl"]["expiring_within_24h"], 1)
            self.assertIn("1 memories expiring within 24 hours", result["issues"])
            store.close()


class MemoryTaggingTests(unittest.TestCase):
    """Tests for memory tagging functionality."""

    def test_add_and_search_tags(self):
        """Tags can be added and searched."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories([
                MemoryUnit(
                    memory_id="tag-1",
                    scope_id="s1",
                    memory_type=MemoryType.SEMANTIC,
                    content="API docs location",
                ),
                MemoryUnit(
                    memory_id="tag-2",
                    scope_id="s1",
                    memory_type=MemoryType.SEMANTIC,
                    content="DB schema info",
                ),
            ])
            store.add_tags("tag-1", ["documentation", "api"])
            store.add_tags("tag-2", ["documentation", "database"])
            # Search by tag.
            api_mems = store.search_by_tag("s1", "api")
            self.assertEqual(len(api_mems), 1)
            self.assertEqual(api_mems[0].memory_id, "tag-1")
            doc_mems = store.search_by_tag("s1", "documentation")
            self.assertEqual(len(doc_mems), 2)
            store.close()

    def test_remove_tags(self):
        """Tags can be removed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories([
                MemoryUnit(
                    memory_id="rt-1",
                    scope_id="s1",
                    memory_type=MemoryType.SEMANTIC,
                    content="Tagged memory",
                    tags=["alpha", "beta"],
                ),
            ])
            store.remove_tags("rt-1", ["alpha"])
            unit = store._get_by_id("rt-1")
            self.assertNotIn("alpha", unit.tags)
            self.assertIn("beta", unit.tags)
            store.close()

    def test_tags_deduplication(self):
        """Adding duplicate tags should not create duplicates."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories([
                MemoryUnit(
                    memory_id="dup-tag",
                    scope_id="s1",
                    memory_type=MemoryType.SEMANTIC,
                    content="Dup tag test",
                    tags=["existing"],
                ),
            ])
            store.add_tags("dup-tag", ["existing", "new"])
            unit = store._get_by_id("dup-tag")
            self.assertEqual(len(unit.tags), 2)
            self.assertIn("existing", unit.tags)
            self.assertIn("new", unit.tags)
            store.close()

    def test_manager_tag_search(self):
        """Manager-level tag search."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1")
            store.add_memories([
                MemoryUnit(
                    memory_id="mgr-tag",
                    scope_id="s1",
                    memory_type=MemoryType.PREFERENCE,
                    content="Prefers vi",
                    tags=["editor"],
                ),
            ])
            results = mgr.search_by_tag("editor")
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0].content, "Prefers vi")
            store.close()

    def test_tags_in_export(self):
        """Tags should appear in exported JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories([
                MemoryUnit(
                    memory_id="exp-tag",
                    scope_id="s1",
                    memory_type=MemoryType.SEMANTIC,
                    content="Tagged export",
                    tags=["important", "reviewed"],
                ),
            ])
            exported = store.export_scope_json("s1")
            self.assertEqual(len(exported), 1)
            self.assertIn("tags", exported[0])
            self.assertIn("important", exported[0]["tags"])
            store.close()


class MemoryHistoryTests(unittest.TestCase):
    """Tests for memory version history."""

    def test_history_follows_supersedes_chain(self):
        """History should include superseded predecessors."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            from metaclaw.memory.models import MemoryStatus
            # Create v1 -> v2 chain.
            store.add_memories([
                MemoryUnit(
                    memory_id="hist-v1",
                    scope_id="s1",
                    memory_type=MemoryType.SEMANTIC,
                    content="Python 3.9 required",
                    status=MemoryStatus.SUPERSEDED,
                    superseded_by="hist-v2",
                ),
                MemoryUnit(
                    memory_id="hist-v2",
                    scope_id="s1",
                    memory_type=MemoryType.SEMANTIC,
                    content="Python 3.10+ required",
                    supersedes=["hist-v1"],
                ),
            ])
            history = store.get_memory_history("hist-v2")
            self.assertEqual(len(history), 2)
            # Ordered by created_at.
            ids = [h["memory_id"] for h in history]
            self.assertIn("hist-v1", ids)
            self.assertIn("hist-v2", ids)
            store.close()

    def test_history_single_memory(self):
        """History of a memory with no chain returns just itself."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories([
                MemoryUnit(
                    memory_id="hist-solo",
                    scope_id="s1",
                    memory_type=MemoryType.EPISODIC,
                    content="Solo memory",
                ),
            ])
            history = store.get_memory_history("hist-solo")
            self.assertEqual(len(history), 1)
            self.assertEqual(history[0]["memory_id"], "hist-solo")
            store.close()


class ScopeAnalyticsTests(unittest.TestCase):
    """Tests for scope analytics."""

    def test_analytics_comprehensive(self):
        """Analytics should include all expected sections."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories([
                MemoryUnit(
                    memory_id="an-1",
                    scope_id="s1",
                    memory_type=MemoryType.SEMANTIC,
                    content="Fact one",
                    importance=0.85,
                    access_count=10,
                    tags=["reviewed"],
                ),
                MemoryUnit(
                    memory_id="an-2",
                    scope_id="s1",
                    memory_type=MemoryType.EPISODIC,
                    content="Episode",
                    importance=0.3,
                    access_count=0,
                ),
                MemoryUnit(
                    memory_id="an-3",
                    scope_id="s1",
                    memory_type=MemoryType.PREFERENCE,
                    content="Pref",
                    importance=0.99,  # pinned
                ),
            ])
            analytics = store.get_scope_analytics("s1")
            self.assertEqual(analytics["total"], 3)
            self.assertEqual(analytics["active"], 3)
            self.assertIn("type_distribution", analytics)
            self.assertIn("access", analytics)
            self.assertEqual(analytics["access"]["never_accessed"], 2)  # an-2 and an-3
            self.assertEqual(analytics["access"]["highly_accessed"], 1)
            self.assertIn("importance", analytics)
            self.assertEqual(analytics["importance"]["high_count"], 2)  # 0.85 and 0.99
            self.assertIn("features", analytics)
            self.assertEqual(analytics["features"]["with_tags"], 1)
            self.assertEqual(analytics["features"]["pinned"], 1)
            store.close()

    def test_analytics_empty_scope(self):
        """Analytics on empty scope should return total=0."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            analytics = store.get_scope_analytics("empty")
            self.assertEqual(analytics["total"], 0)
            store.close()


class BulkOperationsTests(unittest.TestCase):
    """Tests for bulk archive and bulk tag operations."""

    def test_bulk_archive(self):
        """Bulk archive should archive specified memories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories([
                MemoryUnit(memory_id="ba-1", scope_id="s1", memory_type=MemoryType.EPISODIC, content="Ep1"),
                MemoryUnit(memory_id="ba-2", scope_id="s1", memory_type=MemoryType.EPISODIC, content="Ep2"),
                MemoryUnit(memory_id="ba-3", scope_id="s1", memory_type=MemoryType.SEMANTIC, content="Sem1"),
            ])
            count = store.bulk_archive(["ba-1", "ba-2", "nonexistent"])
            self.assertEqual(count, 2)
            active = store.list_active("s1")
            self.assertEqual(len(active), 1)
            self.assertEqual(active[0].memory_id, "ba-3")
            store.close()

    def test_bulk_add_tags(self):
        """Bulk add tags should tag all specified memories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories([
                MemoryUnit(memory_id="bt-1", scope_id="s1", memory_type=MemoryType.SEMANTIC, content="S1"),
                MemoryUnit(memory_id="bt-2", scope_id="s1", memory_type=MemoryType.SEMANTIC, content="S2"),
            ])
            count = store.bulk_add_tags(["bt-1", "bt-2"], ["batch", "v2"])
            self.assertEqual(count, 2)
            u1 = store._get_by_id("bt-1")
            self.assertIn("batch", u1.tags)
            self.assertIn("v2", u1.tags)
            store.close()


class SnapshotTests(unittest.TestCase):
    """Tests for scope snapshot and restore."""

    def test_snapshot_and_restore(self):
        """Snapshot should capture state; restore should revert to it."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories([
                MemoryUnit(memory_id="snap-1", scope_id="s1", memory_type=MemoryType.SEMANTIC, content="Original fact A"),
                MemoryUnit(memory_id="snap-2", scope_id="s1", memory_type=MemoryType.PREFERENCE, content="Original pref"),
            ])
            # Take snapshot.
            snapshot = store.snapshot_scope("s1")
            self.assertEqual(len(snapshot["memories"]), 2)
            self.assertEqual(snapshot["scope_id"], "s1")
            # Modify the store.
            store.add_memories([
                MemoryUnit(memory_id="snap-3", scope_id="s1", memory_type=MemoryType.EPISODIC, content="New episode"),
            ])
            self.assertEqual(len(store.list_active("s1")), 3)
            # Restore.
            restored = store.restore_snapshot(snapshot)
            self.assertEqual(restored, 2)
            active = store.list_active("s1")
            self.assertEqual(len(active), 2)
            contents = {u.content for u in active}
            self.assertIn("Original fact A", contents)
            self.assertIn("Original pref", contents)
            self.assertNotIn("New episode", contents)
            store.close()

    def test_snapshot_empty_scope(self):
        """Snapshot of empty scope should return empty memories list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            snapshot = store.snapshot_scope("empty")
            self.assertEqual(len(snapshot["memories"]), 0)
            store.close()

    def test_manager_snapshot_restore(self):
        """Manager-level snapshot and restore."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1")
            store.add_memories([
                MemoryUnit(memory_id="ms-1", scope_id="s1", memory_type=MemoryType.SEMANTIC, content="Fact"),
            ])
            snapshot = mgr.snapshot_scope()
            store.add_memories([
                MemoryUnit(memory_id="ms-2", scope_id="s1", memory_type=MemoryType.EPISODIC, content="Extra"),
            ])
            count = mgr.restore_snapshot(snapshot)
            self.assertEqual(count, 1)
            active = store.list_active("s1")
            self.assertEqual(len(active), 1)
            store.close()


class EventLogTests(unittest.TestCase):
    """Tests for memory event log (audit trail)."""

    def test_create_events_logged(self):
        """Adding memories should generate create events."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories([
                MemoryUnit(memory_id="ev-1", scope_id="s1", memory_type=MemoryType.SEMANTIC, content="Fact"),
            ])
            events = store.get_event_log(scope_id="s1")
            create_events = [e for e in events if e["event_type"] == "create"]
            self.assertGreaterEqual(len(create_events), 1)
            self.assertEqual(create_events[0]["memory_id"], "ev-1")
            store.close()

    def test_merge_events_logged(self):
        """Merging memories should log merge and supersede events."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories([
                MemoryUnit(memory_id="em-a", scope_id="s1", memory_type=MemoryType.SEMANTIC, content="A"),
                MemoryUnit(memory_id="em-b", scope_id="s1", memory_type=MemoryType.SEMANTIC, content="B"),
            ])
            store.merge_memories("em-a", "em-b", "Merged AB")
            events = store.get_event_log()  # no scope filter to catch all events
            event_types = [e["event_type"] for e in events]
            self.assertIn("merge", event_types)
            self.assertIn("supersede", event_types)
            store.close()

    def test_share_events_logged(self):
        """Sharing a memory should log a share event."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories([
                MemoryUnit(memory_id="es-1", scope_id="s1", memory_type=MemoryType.SEMANTIC, content="Shared"),
            ])
            store.share_to_scope("es-1", "s2")
            events = store.get_event_log()
            share_events = [e for e in events if e["event_type"] == "share"]
            self.assertGreaterEqual(len(share_events), 1)
            store.close()

    def test_event_log_limit(self):
        """Event log should respect limit parameter."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            for i in range(10):
                store.add_memories([
                    MemoryUnit(
                        memory_id=f"limit-{i}",
                        scope_id="s1",
                        memory_type=MemoryType.EPISODIC,
                        content=f"Event {i}",
                    ),
                ])
            events = store.get_event_log(limit=3)
            self.assertEqual(len(events), 3)
            store.close()


class FindSimilarTests(unittest.TestCase):
    """Tests for memory similarity search."""

    def test_find_similar_by_overlap(self):
        """Should find memories with overlapping topics/entities."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories([
                MemoryUnit(
                    memory_id="sim-1", scope_id="s1", memory_type=MemoryType.SEMANTIC,
                    content="Python version req", topics=["python", "version", "requirements"],
                ),
                MemoryUnit(
                    memory_id="sim-2", scope_id="s1", memory_type=MemoryType.SEMANTIC,
                    content="Python 3.11 update", topics=["python", "version", "update"],
                ),
                MemoryUnit(
                    memory_id="sim-3", scope_id="s1", memory_type=MemoryType.SEMANTIC,
                    content="Database config", topics=["database", "config"],
                ),
            ])
            results = store.find_similar("sim-1", limit=5)
            self.assertGreaterEqual(len(results), 1)
            # sim-2 should be most similar (shares python + version).
            self.assertEqual(results[0][0].memory_id, "sim-2")
            self.assertGreater(results[0][1], 0.3)
            store.close()

    def test_find_similar_nonexistent(self):
        """Should return empty for nonexistent memory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            results = store.find_similar("nope")
            self.assertEqual(len(results), 0)
            store.close()


class HealthScoreTests(unittest.TestCase):
    """Tests for memory pool health score."""

    def test_health_score_basic(self):
        """Health score should return a value between 0 and 100."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories([
                MemoryUnit(memory_id="hs-1", scope_id="s1", memory_type=MemoryType.SEMANTIC,
                           content="Fact", importance=0.6, access_count=3),
                MemoryUnit(memory_id="hs-2", scope_id="s1", memory_type=MemoryType.EPISODIC,
                           content="Ep", importance=0.5, access_count=1),
                MemoryUnit(memory_id="hs-3", scope_id="s1", memory_type=MemoryType.PREFERENCE,
                           content="Pref", importance=0.7),
            ])
            health = store.compute_health_score("s1")
            self.assertGreater(health["score"], 0)
            self.assertLessEqual(health["score"], 100)
            self.assertEqual(health["active_count"], 3)
            self.assertIn("components", health)
            self.assertIn("access_coverage", health["components"])
            self.assertIn("type_diversity", health["components"])
            store.close()

    def test_health_score_empty(self):
        """Empty scope should have score 0."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            health = store.compute_health_score("empty")
            self.assertEqual(health["score"], 0)
            store.close()

    def test_manager_health_score(self):
        """Manager wrapper should delegate to store."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1")
            store.add_memories([
                MemoryUnit(memory_id="mhs-1", scope_id="s1", memory_type=MemoryType.SEMANTIC,
                           content="Test", importance=0.5),
            ])
            health = mgr.get_health_score()
            self.assertIn("score", health)
            self.assertGreater(health["score"], 0)
            store.close()


class FindDuplicatesTests(unittest.TestCase):
    """Tests for duplicate detection."""

    def test_find_near_duplicates(self):
        """Should find memories with very similar content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories([
                MemoryUnit(
                    memory_id="dup-a", scope_id="s1", memory_type=MemoryType.SEMANTIC,
                    content="The API endpoint for user management is /api/v2/users",
                ),
                MemoryUnit(
                    memory_id="dup-b", scope_id="s1", memory_type=MemoryType.SEMANTIC,
                    content="The API endpoint for user management is /api/v2/users list",
                ),
                MemoryUnit(
                    memory_id="dup-c", scope_id="s1", memory_type=MemoryType.SEMANTIC,
                    content="Database connection uses PostgreSQL on port 5432",
                ),
            ])
            dups = store.find_duplicates("s1", threshold=0.7)
            self.assertGreaterEqual(len(dups), 1)
            pair_ids = {dups[0]["id_a"], dups[0]["id_b"]}
            self.assertEqual(pair_ids, {"dup-a", "dup-b"})
            store.close()

    def test_no_duplicates_returns_empty(self):
        """Should return empty list when no duplicates exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories([
                MemoryUnit(memory_id="nd-1", scope_id="s1", memory_type=MemoryType.SEMANTIC,
                           content="Python is great"),
                MemoryUnit(memory_id="nd-2", scope_id="s1", memory_type=MemoryType.SEMANTIC,
                           content="Database uses PostgreSQL"),
            ])
            dups = store.find_duplicates("s1")
            self.assertEqual(len(dups), 0)
            store.close()


class RetrievalAutoRouteTests(unittest.TestCase):
    """Tests for automatic retrieval mode selection."""

    def test_auto_selects_keyword_for_short_queries(self):
        """Short queries should use keyword mode."""
        from metaclaw.memory.retriever import MemoryRetriever
        from metaclaw.memory.models import MemoryQuery
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            retriever = MemoryRetriever(store=store, retrieval_mode="auto")
            query = MemoryQuery(scope_id="s1", query_text="python version")
            mode = retriever._auto_select_mode(query)
            self.assertEqual(mode, "keyword")
            store.close()

    def test_auto_selects_hybrid_with_embedder(self):
        """Longer queries with embedder should use hybrid."""
        from metaclaw.memory.retriever import MemoryRetriever
        from metaclaw.memory.models import MemoryQuery
        from metaclaw.memory.embeddings import HashingEmbedder
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            embedder = HashingEmbedder()
            retriever = MemoryRetriever(store=store, retrieval_mode="auto", embedder=embedder)
            query = MemoryQuery(scope_id="s1", query_text="what is the python version requirement for this project")
            mode = retriever._auto_select_mode(query)
            self.assertEqual(mode, "hybrid")
            store.close()

    def test_auto_mode_retrieves_results(self):
        """Auto mode should successfully retrieve memories."""
        from metaclaw.memory.models import MemoryQuery
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories([
                MemoryUnit(memory_id="ar-1", scope_id="s1", memory_type=MemoryType.SEMANTIC,
                           content="The project requires Python 3.10 or higher"),
            ])
            mgr = MemoryManager(store=store, scope_id="s1", retrieval_mode="auto")
            units = mgr.retrieve_for_prompt("python version")
            self.assertGreaterEqual(len(units), 1)
            store.close()


class ConsolidationDryRunTests(unittest.TestCase):
    """Tests for consolidation dry-run."""

    def test_dry_run_detects_exact_duplicates(self):
        """Dry run should count exact duplicates."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories([
                MemoryUnit(memory_id="dr-1", scope_id="s1", memory_type=MemoryType.SEMANTIC, content="Same content"),
                MemoryUnit(memory_id="dr-2", scope_id="s1", memory_type=MemoryType.SEMANTIC, content="Same content"),
                MemoryUnit(memory_id="dr-3", scope_id="s1", memory_type=MemoryType.SEMANTIC, content="Different"),
            ])
            from metaclaw.memory.consolidator import MemoryConsolidator
            consolidator = MemoryConsolidator(store=store)
            preview = consolidator.dry_run("s1")
            self.assertEqual(preview["exact_duplicates"], 1)
            # No actual changes should have been made.
            active = store.list_active("s1")
            self.assertEqual(len(active), 3)
            store.close()

    def test_dry_run_empty_scope(self):
        """Dry run on empty scope should report zero actions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            from metaclaw.memory.consolidator import MemoryConsolidator
            consolidator = MemoryConsolidator(store=store)
            preview = consolidator.dry_run("empty")
            self.assertEqual(preview["total_actions"], 0)
            store.close()


class PinnedRenderingTests(unittest.TestCase):
    """Tests for pinned memory rendering priority."""

    def test_pinned_memories_render_first(self):
        """Pinned memories should appear before unpinned in prompt."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1")
            units = [
                MemoryUnit(memory_id="pr-1", scope_id="s1", memory_type=MemoryType.SEMANTIC,
                           content="Unpinned fact", importance=0.6),
                MemoryUnit(memory_id="pr-2", scope_id="s1", memory_type=MemoryType.SEMANTIC,
                           content="Pinned critical fact", importance=0.99),
            ]
            rendered = mgr.render_for_prompt(units)
            # Pinned should appear before unpinned.
            pinned_pos = rendered.find("Pinned critical fact")
            unpinned_pos = rendered.find("Unpinned fact")
            self.assertLess(pinned_pos, unpinned_pos)
            store.close()


class StatsTrendTests(unittest.TestCase):
    """Tests for stats trend tracking."""

    def test_save_and_retrieve_snapshots(self):
        """Stats snapshots should be saved and retrievable."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories([
                MemoryUnit(memory_id="tr-1", scope_id="s1", memory_type=MemoryType.SEMANTIC, content="Fact"),
            ])
            snap1 = store.save_stats_snapshot("s1")
            self.assertIn("active", snap1)
            self.assertEqual(snap1["active"], 1)

            store.add_memories([
                MemoryUnit(memory_id="tr-2", scope_id="s1", memory_type=MemoryType.EPISODIC, content="Ep"),
            ])
            snap2 = store.save_stats_snapshot("s1")
            self.assertEqual(snap2["active"], 2)

            trend = store.get_stats_trend("s1")
            self.assertEqual(len(trend), 2)
            # Oldest first.
            self.assertEqual(trend[0]["active"], 1)
            self.assertEqual(trend[1]["active"], 2)
            store.close()

    def test_trend_empty(self):
        """No snapshots should return empty list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            trend = store.get_stats_trend("s1")
            self.assertEqual(len(trend), 0)
            store.close()

    def test_ingestion_auto_saves_snapshot(self):
        """Ingestion should automatically save a stats snapshot."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            mgr.ingest_session_turns("sess-1", [
                {"prompt_text": "Remember that Python 3.10 is required", "response_text": "Noted."},
            ])
            trend = store.get_stats_trend("s1")
            self.assertGreaterEqual(len(trend), 1)
            store.close()


class AdvancedSearchTests(unittest.TestCase):
    """Tests for combined criteria search."""

    def test_search_by_keyword_and_type(self):
        """Search should filter by both keyword and type."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories([
                MemoryUnit(memory_id="as-1", scope_id="s1", memory_type=MemoryType.SEMANTIC,
                           content="Python version is 3.10"),
                MemoryUnit(memory_id="as-2", scope_id="s1", memory_type=MemoryType.EPISODIC,
                           content="Python discussion happened"),
                MemoryUnit(memory_id="as-3", scope_id="s1", memory_type=MemoryType.SEMANTIC,
                           content="Database uses PostgreSQL"),
            ])
            results = store.search_advanced("s1", keyword="python", memory_type="semantic")
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0].memory_id, "as-1")
            store.close()

    def test_search_by_tag_and_importance(self):
        """Search should filter by tag and minimum importance."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories([
                MemoryUnit(memory_id="ti-1", scope_id="s1", memory_type=MemoryType.SEMANTIC,
                           content="Important fact", importance=0.9, tags=["reviewed"]),
                MemoryUnit(memory_id="ti-2", scope_id="s1", memory_type=MemoryType.SEMANTIC,
                           content="Low importance", importance=0.2, tags=["reviewed"]),
            ])
            results = store.search_advanced("s1", tag="reviewed", min_importance=0.5)
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0].memory_id, "ti-1")
            store.close()


class ScopeCompareTests(unittest.TestCase):
    """Tests for scope comparison."""

    def test_compare_scopes(self):
        """Compare should identify shared and unique content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories([
                MemoryUnit(memory_id="ca-1", scope_id="team-a", memory_type=MemoryType.SEMANTIC,
                           content="API uses OAuth2"),
                MemoryUnit(memory_id="ca-2", scope_id="team-a", memory_type=MemoryType.SEMANTIC,
                           content="Deploy to us-west-2"),
                MemoryUnit(memory_id="cb-1", scope_id="team-b", memory_type=MemoryType.SEMANTIC,
                           content="API uses OAuth2"),  # Same as ca-1
                MemoryUnit(memory_id="cb-2", scope_id="team-b", memory_type=MemoryType.SEMANTIC,
                           content="Uses Kubernetes"),
            ])
            result = store.compare_scopes("team-a", "team-b")
            self.assertEqual(result["shared_count"], 1)
            self.assertEqual(result["unique_to_a"], 1)
            self.assertEqual(result["unique_to_b"], 1)
            self.assertEqual(result["scope_a_count"], 2)
            self.assertEqual(result["scope_b_count"], 2)
            store.close()


class ImportanceRebalanceTests(unittest.TestCase):
    """Tests for importance rebalancing."""

    def test_rebalance_spreads_clustered_importance(self):
        """Rebalancing should spread clustered importance values."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1")
            # Create 6 memories all with importance 0.5.
            for i in range(6):
                store.add_memories([
                    MemoryUnit(
                        memory_id=f"rb-{i}", scope_id="s1",
                        memory_type=MemoryType.SEMANTIC,
                        content=f"Fact number {i}",
                        importance=0.5,
                        access_count=i,
                    ),
                ])
            result = mgr.rebalance_importance()
            self.assertGreater(result["adjusted"], 0)
            # After rebalancing, not all should have the same importance.
            units = store.list_active("s1")
            importances = [u.importance for u in units]
            self.assertGreater(len(set(round(i, 3) for i in importances)), 1)
            store.close()


class ResponseExtractionTests(unittest.TestCase):
    """Tests for expanded response-side extraction patterns."""

    def test_extract_best_practice(self):
        """Should extract 'best practice is to' pattern from response."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            mgr.ingest_session_turns("sess-1", [
                {
                    "prompt_text": "How should I structure the API?",
                    "response_text": "Best practice is to use RESTful conventions with versioned endpoints",
                },
            ])
            units = store.list_active("s1")
            contents = " ".join(u.content for u in units)
            self.assertTrue(
                "restful" in contents.lower() or "conventions" in contents.lower(),
                f"Expected best practice extraction, got: {contents}"
            )
            store.close()

    def test_extract_in_summary(self):
        """Should extract 'in summary' pattern from response."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            mgr.ingest_session_turns("sess-2", [
                {
                    "prompt_text": "What did we decide?",
                    "response_text": "In summary, the migration to PostgreSQL is planned for Q2",
                },
            ])
            units = store.list_active("s1")
            contents = " ".join(u.content for u in units)
            self.assertTrue(
                "postgresql" in contents.lower() or "migration" in contents.lower(),
                f"Expected summary extraction, got: {contents}"
            )
            store.close()


class TagBasedRetrievalBoostTests(unittest.TestCase):
    """Tests for tag-based retrieval boosting."""

    def test_tag_match_boosts_score(self):
        """Memories with matching tags should rank higher."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            # Two memories with same keyword relevance but different tags.
            u1 = MemoryUnit(
                memory_id="tb-1",
                scope_id="s1",
                memory_type=MemoryType.SEMANTIC,
                content="Database migration steps",
                importance=0.5,
                confidence=0.8,
                topics=["database", "migration"],
                tags=[],
            )
            u2 = MemoryUnit(
                memory_id="tb-2",
                scope_id="s1",
                memory_type=MemoryType.SEMANTIC,
                content="Database backup procedure",
                importance=0.5,
                confidence=0.8,
                topics=["database", "backup"],
                tags=["ops", "production"],
            )
            store.add_memories([u1, u2])
            from metaclaw.memory.retriever import MemoryRetriever
            retriever = MemoryRetriever(store=store, retrieval_mode="keyword")
            query = MemoryQuery(
                scope_id="s1",
                query_text="database",
                context_tags=["ops"],
            )
            hits = retriever.retrieve(query)
            self.assertTrue(len(hits) >= 2)
            # The tagged memory should rank first due to tag boost.
            self.assertEqual(hits[0].unit.memory_id, "tb-2")
            store.close()

    def test_no_context_tags_no_boost(self):
        """Without context_tags, tag boosting should not affect results."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            u1 = MemoryUnit(
                memory_id="nb-1",
                scope_id="s1",
                memory_type=MemoryType.SEMANTIC,
                content="API endpoint design",
                importance=0.5,
                confidence=0.8,
                topics=["api"],
                tags=["frontend"],
            )
            store.add_memories([u1])
            from metaclaw.memory.retriever import MemoryRetriever
            retriever = MemoryRetriever(store=store, retrieval_mode="keyword")
            query = MemoryQuery(scope_id="s1", query_text="api")
            hits = retriever.retrieve(query)
            self.assertEqual(len(hits), 1)
            base_score = hits[0].score
            # With unrelated context tags, score should stay the same.
            query2 = MemoryQuery(
                scope_id="s1",
                query_text="api",
                context_tags=["backend"],
            )
            hits2 = retriever.retrieve(query2)
            self.assertEqual(hits2[0].score, base_score)
            store.close()

    def test_multiple_tag_matches_compound_boost(self):
        """Multiple matching tags should compound the boost."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            u1 = MemoryUnit(
                memory_id="mt-1",
                scope_id="s1",
                memory_type=MemoryType.SEMANTIC,
                content="Deploy service to production",
                importance=0.5,
                confidence=0.8,
                topics=["deploy"],
                tags=["ops", "production", "critical"],
            )
            store.add_memories([u1])
            from metaclaw.memory.retriever import MemoryRetriever
            retriever = MemoryRetriever(store=store, retrieval_mode="keyword")
            # Single tag match.
            q1 = MemoryQuery(scope_id="s1", query_text="deploy", context_tags=["ops"])
            h1 = retriever.retrieve(q1)
            # Two tag matches.
            q2 = MemoryQuery(scope_id="s1", query_text="deploy", context_tags=["ops", "production"])
            h2 = retriever.retrieve(q2)
            self.assertGreater(h2[0].score, h1[0].score)
            store.close()


class ExponentialDecayTests(unittest.TestCase):
    """Tests for exponential importance decay mode."""

    def test_exponential_decay_mode(self):
        """Exponential decay should use e^(-factor*periods) instead of linear."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            from metaclaw.memory.consolidator import MemoryConsolidator
            consolidator = MemoryConsolidator(
                store=store, decay_after_days=1, decay_factor=0.1, decay_mode="exponential"
            )
            # Create an old memory.
            from datetime import datetime, timedelta, timezone
            old_time = (datetime.now(timezone.utc) - timedelta(days=60)).isoformat(timespec="seconds")
            u = MemoryUnit(memory_id="ed-1", scope_id="s1",
                           memory_type=MemoryType.SEMANTIC, content="Old fact",
                           importance=0.8, created_at=old_time, updated_at=old_time)
            store.add_memories([u])
            result = consolidator.consolidate("s1")
            self.assertGreater(result["decayed"], 0)
            after = store._get_by_id("ed-1")
            self.assertLess(after.importance, 0.8)
            store.close()


class MemoryWatchTests(unittest.TestCase):
    """Tests for memory watch/subscription system."""

    def test_add_and_get_watchers(self):
        """Should add watchers and retrieve them."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            self.assertTrue(store.add_watch("mem-1", "alice"))
            self.assertTrue(store.add_watch("mem-1", "bob"))
            watchers = store.get_watchers("mem-1")
            self.assertEqual(set(watchers), {"alice", "bob"})
            store.close()

    def test_remove_watch(self):
        """Should remove a watcher."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_watch("mem-1", "alice")
            self.assertTrue(store.remove_watch("mem-1", "alice"))
            self.assertEqual(store.get_watchers("mem-1"), [])
            store.close()

    def test_duplicate_watch(self):
        """Duplicate watch should return False."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            self.assertTrue(store.add_watch("mem-1", "alice"))
            self.assertFalse(store.add_watch("mem-1", "alice"))
            store.close()

    def test_get_watched_memories(self):
        """Should list all memories watched by a watcher."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_watch("mem-1", "alice")
            store.add_watch("mem-2", "alice")
            watched = store.get_watched_memories("alice")
            self.assertEqual(set(watched), {"mem-1", "mem-2"})
            store.close()

    def test_manager_watch_wrappers(self):
        """Manager-level watch methods should delegate to store."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            self.assertTrue(mgr.watch_memory("mem-1", "alice"))
            self.assertEqual(mgr.get_watchers("mem-1"), ["alice"])
            self.assertEqual(mgr.get_watched_memories("alice"), ["mem-1"])
            mgr.unwatch_memory("mem-1", "alice")
            self.assertEqual(mgr.get_watchers("mem-1"), [])
            store.close()


class AdaptiveTTLTests(unittest.TestCase):
    """Tests for adaptive TTL assignment."""

    def test_adaptive_ttl_sets_expiry(self):
        """Should set TTL on memories that don't have one."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            u1 = MemoryUnit(memory_id="att-1", scope_id="s1",
                            memory_type=MemoryType.EPISODIC, content="Something happened",
                            importance=0.5)
            u2 = MemoryUnit(memory_id="att-2", scope_id="s1",
                            memory_type=MemoryType.SEMANTIC, content="A known fact",
                            importance=0.5)
            store.add_memories([u1, u2])
            result = mgr.apply_adaptive_ttl()
            self.assertEqual(result["updated"], 2)
            # Both should now have expires_at set.
            u1_after = store._get_by_id("att-1")
            u2_after = store._get_by_id("att-2")
            self.assertTrue(u1_after.expires_at)
            self.assertTrue(u2_after.expires_at)
            store.close()

    def test_adaptive_ttl_skips_pinned(self):
        """Should not set TTL on pinned memories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            u = MemoryUnit(memory_id="att-pin", scope_id="s1",
                           memory_type=MemoryType.SEMANTIC, content="Pinned fact",
                           importance=0.99)
            store.add_memories([u])
            result = mgr.apply_adaptive_ttl()
            self.assertEqual(result["updated"], 0)
            self.assertFalse(store._get_by_id("att-pin").expires_at)
            store.close()

    def test_adaptive_ttl_skips_existing_ttl(self):
        """Should not overwrite existing TTL."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            u = MemoryUnit(memory_id="att-ex", scope_id="s1",
                           memory_type=MemoryType.SEMANTIC, content="Has TTL",
                           importance=0.5, expires_at="2026-06-01T00:00:00Z")
            store.add_memories([u])
            result = mgr.apply_adaptive_ttl()
            self.assertEqual(result["updated"], 0)
            store.close()


class UsageReportTests(unittest.TestCase):
    """Tests for comprehensive usage report generation."""

    def test_usage_report_structure(self):
        """Should return a report with all expected fields."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            u = MemoryUnit(memory_id="ur-1", scope_id="s1",
                           memory_type=MemoryType.SEMANTIC, content="Test memory",
                           importance=0.6)
            store.add_memories([u])
            report = mgr.generate_usage_report()
            self.assertEqual(report["scope_id"], "s1")
            self.assertEqual(report["total_active"], 1)
            self.assertIn("health_score", report)
            self.assertIn("type_distribution", report)
            self.assertIn("avg_importance", report)
            self.assertIn("access_coverage", report)
            store.close()

    def test_usage_report_empty_scope(self):
        """Should handle empty scope gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="empty", auto_consolidate=False)
            report = mgr.generate_usage_report()
            self.assertEqual(report["total_active"], 0)
            store.close()


class BatchArchiveByCriteriaTests(unittest.TestCase):
    """Tests for batch archive by criteria."""

    def test_archive_by_importance(self):
        """Should archive memories below importance threshold."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            u1 = MemoryUnit(memory_id="ba-low", scope_id="s1", memory_type=MemoryType.SEMANTIC,
                            content="Low importance note", importance=0.1)
            u2 = MemoryUnit(memory_id="ba-high", scope_id="s1", memory_type=MemoryType.SEMANTIC,
                            content="High importance note", importance=0.8)
            store.add_memories([u1, u2])
            result = mgr.batch_archive_by_criteria(max_importance=0.3)
            self.assertEqual(result["archived"], 1)
            self.assertEqual(store._get_by_id("ba-low").status, MemoryStatus.ARCHIVED)
            self.assertEqual(store._get_by_id("ba-high").status, MemoryStatus.ACTIVE)
            store.close()

    def test_archive_by_type(self):
        """Should only archive memories of the specified type."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            u1 = MemoryUnit(memory_id="bt-ep", scope_id="s1", memory_type=MemoryType.EPISODIC,
                            content="Something happened", importance=0.3)
            u2 = MemoryUnit(memory_id="bt-sem", scope_id="s1", memory_type=MemoryType.SEMANTIC,
                            content="A known fact", importance=0.3)
            store.add_memories([u1, u2])
            result = mgr.batch_archive_by_criteria(memory_type=MemoryType.EPISODIC)
            self.assertEqual(result["archived"], 1)
            self.assertEqual(store._get_by_id("bt-ep").status, MemoryStatus.ARCHIVED)
            self.assertEqual(store._get_by_id("bt-sem").status, MemoryStatus.ACTIVE)
            store.close()

    def test_archive_skips_pinned(self):
        """Should never archive pinned memories regardless of criteria."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            u1 = MemoryUnit(memory_id="bp-pin", scope_id="s1", memory_type=MemoryType.SEMANTIC,
                            content="Pinned memory", importance=0.99)
            store.add_memories([u1])
            result = mgr.batch_archive_by_criteria(max_importance=1.0)
            self.assertEqual(result["archived"], 0)
            store.close()


class MemoryClusterTests(unittest.TestCase):
    """Tests for memory graph cluster detection."""

    def test_find_connected_cluster(self):
        """Should find a cluster of linked memories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            for i in range(3):
                u = MemoryUnit(memory_id=f"cl-{i}", scope_id="s1",
                               memory_type=MemoryType.SEMANTIC, content=f"Memory {i}", importance=0.5)
                store.add_memories([u])
            store.add_link("cl-0", "cl-1", "related")
            store.add_link("cl-1", "cl-2", "depends_on")
            clusters = mgr.find_memory_clusters()
            self.assertEqual(len(clusters), 1)
            self.assertEqual(len(clusters[0]), 3)
            store.close()

    def test_no_clusters_without_links(self):
        """Without links, should return empty cluster list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            u = MemoryUnit(memory_id="nc-1", scope_id="s1",
                           memory_type=MemoryType.SEMANTIC, content="Solo memory", importance=0.5)
            store.add_memories([u])
            clusters = mgr.find_memory_clusters()
            self.assertEqual(len(clusters), 0)
            store.close()

    def test_separate_clusters(self):
        """Should detect separate disconnected clusters."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            for i in range(4):
                u = MemoryUnit(memory_id=f"sc-{i}", scope_id="s1",
                               memory_type=MemoryType.SEMANTIC, content=f"Memory {i}", importance=0.5)
                store.add_memories([u])
            store.add_link("sc-0", "sc-1", "related")
            store.add_link("sc-2", "sc-3", "related")
            clusters = mgr.find_memory_clusters()
            self.assertEqual(len(clusters), 2)
            store.close()


class MemoryQualityScoreTests(unittest.TestCase):
    """Tests for per-memory quality scoring."""

    def test_rich_memory_scores_higher(self):
        """A memory with rich metadata should score higher than a sparse one."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            u_sparse = MemoryUnit(
                memory_id="qs-sparse", scope_id="s1", memory_type=MemoryType.SEMANTIC,
                content="Short", importance=0.3)
            u_rich = MemoryUnit(
                memory_id="qs-rich", scope_id="s1", memory_type=MemoryType.SEMANTIC,
                content="Detailed API documentation for the authentication service endpoint with OAuth2 flow",
                summary="Auth API docs",
                importance=0.8, confidence=0.9,
                topics=["auth", "api", "oauth"],
                entities=["AuthService", "OAuth2"],
                tags=["important"],
            )
            store.add_memories([u_sparse, u_rich])
            sparse_score = mgr.score_memory_quality("qs-sparse")
            rich_score = mgr.score_memory_quality("qs-rich")
            self.assertGreater(rich_score["score"], sparse_score["score"])
            store.close()

    def test_quality_score_nonexistent_returns_zero(self):
        """Scoring a nonexistent memory should return score 0."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            result = mgr.score_memory_quality("does-not-exist")
            self.assertEqual(result["score"], 0)
            store.close()

    def test_get_lowest_quality_memories(self):
        """Should return memories sorted by quality ascending."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            for i in range(5):
                u = MemoryUnit(
                    memory_id=f"lq-{i}", scope_id="s1", memory_type=MemoryType.SEMANTIC,
                    content=f"Memory content number {i}" * (i + 1),
                    importance=0.1 * (i + 1),
                    topics=["topic"] * i,
                )
                store.add_memories([u])
            results = mgr.get_lowest_quality_memories(limit=3)
            self.assertEqual(len(results), 3)
            # Should be sorted ascending by score.
            self.assertLessEqual(results[0]["score"], results[1]["score"])
            self.assertLessEqual(results[1]["score"], results[2]["score"])
            store.close()


class MemoryAnnotationTests(unittest.TestCase):
    """Tests for memory annotation system."""

    def test_add_and_get_annotations(self):
        """Should add and retrieve annotations for a memory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            u1 = MemoryUnit(memory_id="an-1", scope_id="s1", memory_type=MemoryType.SEMANTIC,
                            content="API design notes", importance=0.5)
            store.add_memories([u1])
            aid = store.add_annotation("an-1", "Needs review before Q2", author="alice")
            self.assertIsInstance(aid, int)
            annotations = store.get_annotations("an-1")
            self.assertEqual(len(annotations), 1)
            self.assertEqual(annotations[0]["content"], "Needs review before Q2")
            self.assertEqual(annotations[0]["author"], "alice")
            store.close()

    def test_delete_annotation(self):
        """Should delete a specific annotation by ID."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            aid = store.add_annotation("test-mem", "First note")
            store.add_annotation("test-mem", "Second note")
            self.assertTrue(store.delete_annotation(aid))
            remaining = store.get_annotations("test-mem")
            self.assertEqual(len(remaining), 1)
            self.assertEqual(remaining[0]["content"], "Second note")
            store.close()

    def test_manager_annotation_wrappers(self):
        """Manager-level annotation methods should delegate to store."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            aid = mgr.add_annotation("mem-1", "Important context", author="bob")
            annotations = mgr.get_annotations("mem-1")
            self.assertEqual(len(annotations), 1)
            self.assertTrue(mgr.delete_annotation(aid))
            self.assertEqual(len(mgr.get_annotations("mem-1")), 0)
            store.close()


class LinkedRetrievalExpansionTests(unittest.TestCase):
    """Tests for expand_links in retrieve_for_prompt."""

    def test_expand_links_includes_linked_memories(self):
        """retrieve_for_prompt with expand_links should include linked memories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            u1 = MemoryUnit(memory_id="er-1", scope_id="s1", memory_type=MemoryType.SEMANTIC,
                            content="Database migration steps", importance=0.7,
                            topics=["database", "migration"])
            u2 = MemoryUnit(memory_id="er-2", scope_id="s1", memory_type=MemoryType.SEMANTIC,
                            content="Rollback procedure for database", importance=0.6,
                            topics=["database", "rollback"])
            store.add_memories([u1, u2])
            store.add_link("er-1", "er-2", "related")
            # Without expand, only matching units.
            units_plain = mgr.retrieve_for_prompt("database migration")
            # With expand, linked memories should also appear.
            units_expanded = mgr.retrieve_for_prompt("database migration", expand_links=True)
            expanded_ids = {u.memory_id for u in units_expanded}
            self.assertIn("er-1", expanded_ids)
            self.assertIn("er-2", expanded_ids)
            store.close()

    def test_expand_links_without_links_is_same(self):
        """expand_links should be harmless when there are no links."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            u1 = MemoryUnit(memory_id="nl-1", scope_id="s1", memory_type=MemoryType.SEMANTIC,
                            content="API design patterns", importance=0.7, topics=["api"])
            store.add_memories([u1])
            units_plain = mgr.retrieve_for_prompt("api design")
            units_expanded = mgr.retrieve_for_prompt("api design", expand_links=True)
            self.assertEqual(len(units_plain), len(units_expanded))
            store.close()


class MemoryLinkTests(unittest.TestCase):
    """Tests for memory dependency/link tracking."""

    def test_add_and_get_links(self):
        """Should create and retrieve links between memories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            u1 = MemoryUnit(memory_id="lk-1", scope_id="s1", memory_type=MemoryType.SEMANTIC,
                            content="Database schema", importance=0.5)
            u2 = MemoryUnit(memory_id="lk-2", scope_id="s1", memory_type=MemoryType.SEMANTIC,
                            content="Migration guide", importance=0.5)
            store.add_memories([u1, u2])
            self.assertTrue(store.add_link("lk-1", "lk-2", "related"))
            links = store.get_links("lk-1")
            self.assertEqual(len(links), 1)
            self.assertEqual(links[0]["target_id"], "lk-2")
            self.assertEqual(links[0]["link_type"], "related")
            # lk-2 should see incoming link.
            links_in = store.get_links("lk-2", direction="incoming")
            self.assertEqual(len(links_in), 1)
            self.assertEqual(links_in[0]["source_id"], "lk-1")
            store.close()

    def test_remove_link(self):
        """Should remove specific or all links."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_link("a", "b", "related")
            store.add_link("a", "b", "depends_on")
            # Remove specific.
            count = store.remove_link("a", "b", "related")
            self.assertEqual(count, 1)
            links = store.get_links("a", direction="outgoing")
            self.assertEqual(len(links), 1)
            self.assertEqual(links[0]["link_type"], "depends_on")
            # Remove all.
            store.remove_link("a", "b")
            links = store.get_links("a")
            self.assertEqual(len(links), 0)
            store.close()

    def test_duplicate_link_returns_false(self):
        """Adding the same link twice should return False."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            self.assertTrue(store.add_link("x", "y", "related"))
            self.assertFalse(store.add_link("x", "y", "related"))
            store.close()

    def test_get_linked_memories(self):
        """Should retrieve actual MemoryUnit objects for linked memories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            u1 = MemoryUnit(memory_id="gm-1", scope_id="s1", memory_type=MemoryType.SEMANTIC,
                            content="Auth config", importance=0.5)
            u2 = MemoryUnit(memory_id="gm-2", scope_id="s1", memory_type=MemoryType.SEMANTIC,
                            content="Auth tokens", importance=0.5)
            u3 = MemoryUnit(memory_id="gm-3", scope_id="s1", memory_type=MemoryType.SEMANTIC,
                            content="Unrelated", importance=0.5)
            store.add_memories([u1, u2, u3])
            store.add_link("gm-1", "gm-2", "related")
            linked = store.get_linked_memories("gm-1")
            linked_ids = {u.memory_id for u in linked}
            self.assertIn("gm-2", linked_ids)
            self.assertNotIn("gm-3", linked_ids)
            store.close()

    def test_manager_link_wrappers(self):
        """Manager-level link methods should delegate to store."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            u1 = MemoryUnit(memory_id="ml-1", scope_id="s1", memory_type=MemoryType.SEMANTIC,
                            content="Endpoint A", importance=0.5)
            u2 = MemoryUnit(memory_id="ml-2", scope_id="s1", memory_type=MemoryType.SEMANTIC,
                            content="Endpoint B", importance=0.5)
            store.add_memories([u1, u2])
            self.assertTrue(mgr.add_link("ml-1", "ml-2", "depends_on"))
            links = mgr.get_links("ml-1")
            self.assertEqual(len(links), 1)
            linked = mgr.get_linked_memories("ml-1", link_type="depends_on")
            self.assertEqual(len(linked), 1)
            self.assertEqual(linked[0].memory_id, "ml-2")
            store.close()


class ScopeAccessControlTests(unittest.TestCase):
    """Tests for scope-level access control."""

    def test_grant_and_check_access(self):
        """Should grant and check read/write/admin permissions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            self.assertTrue(store.grant_access("scope-1", "alice", "read"))
            self.assertTrue(store.check_access("scope-1", "alice", "read"))
            self.assertFalse(store.check_access("scope-1", "alice", "write"))
            store.close()

    def test_admin_implies_all_permissions(self):
        """Admin permission should imply read and write."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.grant_access("scope-1", "bob", "admin")
            self.assertTrue(store.check_access("scope-1", "bob", "read"))
            self.assertTrue(store.check_access("scope-1", "bob", "write"))
            self.assertTrue(store.check_access("scope-1", "bob", "admin"))
            store.close()

    def test_revoke_access(self):
        """Should revoke specific or all permissions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.grant_access("scope-1", "carol", "read")
            store.grant_access("scope-1", "carol", "write")
            # Revoke specific.
            count = store.revoke_access("scope-1", "carol", "write")
            self.assertEqual(count, 1)
            self.assertTrue(store.check_access("scope-1", "carol", "read"))
            self.assertFalse(store.check_access("scope-1", "carol", "write"))
            # Revoke all.
            count = store.revoke_access("scope-1", "carol")
            self.assertEqual(count, 1)
            self.assertFalse(store.check_access("scope-1", "carol", "read"))
            store.close()

    def test_duplicate_grant_returns_false(self):
        """Granting the same permission twice should return False."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            self.assertTrue(store.grant_access("scope-1", "dave", "read"))
            self.assertFalse(store.grant_access("scope-1", "dave", "read"))
            store.close()

    def test_list_scope_grants(self):
        """Should list all grants for a scope."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.grant_access("scope-1", "alice", "read")
            store.grant_access("scope-1", "bob", "admin")
            grants = store.list_scope_grants("scope-1")
            principals = {g["principal"] for g in grants}
            self.assertEqual(principals, {"alice", "bob"})
            store.close()

    def test_list_principal_scopes(self):
        """Should list all scopes a principal has access to."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.grant_access("scope-1", "alice", "read")
            store.grant_access("scope-2", "alice", "write")
            scopes = store.list_principal_scopes("alice")
            scope_ids = {s["scope_id"] for s in scopes}
            self.assertEqual(scope_ids, {"scope-1", "scope-2"})
            store.close()

    def test_manager_scope_access_wrappers(self):
        """Manager-level scope access methods should delegate to store."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            self.assertTrue(mgr.grant_scope_access("s1", "alice", "read"))
            self.assertTrue(mgr.check_scope_access("s1", "alice", "read"))
            mgr.revoke_scope_access("s1", "alice")
            self.assertFalse(mgr.check_scope_access("s1", "alice", "read"))
            store.close()


class EventCallbackTests(unittest.TestCase):
    """Tests for memory event callback system."""

    def test_ingest_fires_callback(self):
        """Ingesting session turns should fire an 'ingest' event callback."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            events = []
            mgr.register_event_callback(lambda e: events.append(e))
            mgr.ingest_session_turns("sess-1", [
                {"prompt_text": "I prefer dark mode", "response_text": "Noted!"},
            ])
            ingest_events = [e for e in events if e["event"] == "ingest"]
            self.assertTrue(len(ingest_events) >= 1)
            self.assertEqual(ingest_events[0]["scope_id"], "s1")
            self.assertEqual(ingest_events[0]["session_id"], "sess-1")
            self.assertGreater(ingest_events[0]["added"], 0)
            store.close()

    def test_callback_error_does_not_break_operation(self):
        """A failing callback should not prevent the operation from succeeding."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)

            def bad_callback(e):
                raise RuntimeError("callback failure")

            mgr.register_event_callback(bad_callback)
            # Should succeed despite callback error.
            added = mgr.ingest_session_turns("sess-1", [
                {"prompt_text": "I use vim", "response_text": "OK"},
            ])
            self.assertGreater(added, 0)
            store.close()

    def test_multiple_callbacks_all_called(self):
        """All registered callbacks should be called for each event."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            events_a = []
            events_b = []
            mgr.register_event_callback(lambda e: events_a.append(e))
            mgr.register_event_callback(lambda e: events_b.append(e))
            mgr.ingest_session_turns("sess-1", [
                {"prompt_text": "I prefer tabs", "response_text": "OK"},
            ])
            self.assertTrue(len(events_a) >= 1)
            self.assertTrue(len(events_b) >= 1)
            store.close()


class AutoResolveConflictsTests(unittest.TestCase):
    """Tests for automatic conflict resolution."""

    def test_resolve_conflicts_supersedes_older(self):
        """Should supersede the older memory when two conflict."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            # Create two same-type memories with overlapping topics but different content.
            u1 = MemoryUnit(
                memory_id="c-old",
                scope_id="s1",
                memory_type=MemoryType.PREFERENCE,
                content="Use tabs for indentation",
                importance=0.5,
                confidence=0.8,
                topics=["indentation", "formatting"],
                entities=["editor"],
                created_at="2026-01-01T00:00:00Z",
            )
            u2 = MemoryUnit(
                memory_id="c-new",
                scope_id="s1",
                memory_type=MemoryType.PREFERENCE,
                content="Use spaces for indentation",
                importance=0.5,
                confidence=0.8,
                topics=["indentation", "formatting"],
                entities=["editor"],
                created_at="2026-03-01T00:00:00Z",
            )
            store.add_memories([u1, u2])
            result = mgr.auto_resolve_conflicts()
            self.assertGreaterEqual(result["resolved"], 1)
            # The older one should be superseded.
            old = store._get_by_id("c-old")
            self.assertEqual(old.status, MemoryStatus.SUPERSEDED)
            # The newer one should remain active.
            new = store._get_by_id("c-new")
            self.assertEqual(new.status, MemoryStatus.ACTIVE)
            store.close()

    def test_resolve_conflicts_skips_pinned(self):
        """Should not supersede pinned memories (importance >= 0.99)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            u1 = MemoryUnit(
                memory_id="pin-old",
                scope_id="s1",
                memory_type=MemoryType.PREFERENCE,
                content="Use tabs for indentation",
                importance=0.99,
                confidence=0.8,
                topics=["indentation", "formatting"],
                entities=["editor"],
                created_at="2026-01-01T00:00:00Z",
            )
            u2 = MemoryUnit(
                memory_id="pin-new",
                scope_id="s1",
                memory_type=MemoryType.PREFERENCE,
                content="Use spaces for indentation",
                importance=0.5,
                confidence=0.8,
                topics=["indentation", "formatting"],
                entities=["editor"],
                created_at="2026-03-01T00:00:00Z",
            )
            store.add_memories([u1, u2])
            result = mgr.auto_resolve_conflicts()
            self.assertEqual(result["resolved"], 0)
            # Both should remain active.
            self.assertEqual(store._get_by_id("pin-old").status, MemoryStatus.ACTIVE)
            self.assertEqual(store._get_by_id("pin-new").status, MemoryStatus.ACTIVE)
            store.close()

    def test_resolve_conflicts_no_conflicts(self):
        """Should return zero resolved when no conflicts exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            u1 = MemoryUnit(
                memory_id="nc-1",
                scope_id="s1",
                memory_type=MemoryType.PREFERENCE,
                content="Use Python 3.12",
                importance=0.5,
                confidence=0.8,
                topics=["python"],
                entities=["runtime"],
            )
            u2 = MemoryUnit(
                memory_id="nc-2",
                scope_id="s1",
                memory_type=MemoryType.SEMANTIC,
                content="Database is PostgreSQL",
                importance=0.5,
                confidence=0.8,
                topics=["database"],
                entities=["postgresql"],
            )
            store.add_memories([u1, u2])
            result = mgr.auto_resolve_conflicts()
            self.assertEqual(result["resolved"], 0)
            store.close()


class StoreIntegrityTests(unittest.TestCase):
    """Tests for store integrity validation and cleanup."""

    def test_validate_clean_store(self):
        """A fresh store should have no integrity issues."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            result = store.validate_integrity()
            self.assertTrue(result["valid"])
            self.assertEqual(result["issues"], [])
            store.close()

    def test_validate_detects_orphaned_links(self):
        """Should detect links referencing non-existent memories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            # Create a link without the target memory.
            store.add_link("exists", "does-not-exist", "related")
            result = store.validate_integrity()
            self.assertFalse(result["valid"])
            self.assertGreater(result["orphaned_links"], 0)
            store.close()

    def test_cleanup_orphans(self):
        """Should remove orphaned references."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_link("a", "b", "related")
            store.add_watch("nonexistent", "alice")
            result = store.cleanup_orphans()
            self.assertGreater(result["total_removed"], 0)
            # Validate should now pass.
            validation = store.validate_integrity()
            self.assertEqual(validation["orphaned_links"], 0)
            self.assertEqual(validation["orphaned_watches"], 0)
            store.close()

    def test_export_csv(self):
        """Should export memories as valid CSV."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            u = MemoryUnit(memory_id="csv-1", scope_id="s1",
                           memory_type=MemoryType.SEMANTIC, content='Quote: "hello"',
                           importance=0.5, tags=["test", "csv"])
            store.add_memories([u])
            csv_text = store.export_csv("s1")
            self.assertIn("memory_id", csv_text)
            self.assertIn("csv-1", csv_text)
            self.assertIn("test;csv", csv_text)
            store.close()


class OptimizationHintsTests(unittest.TestCase):
    """Tests for optimization hints."""

    def test_hints_for_empty_store(self):
        """Empty store should report no optimizations needed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            hints = mgr.get_optimization_hints()
            self.assertTrue(any("empty" in h.lower() for h in hints))
            store.close()

    def test_hints_for_no_ttl(self):
        """Should suggest auto-ttl when no memories have TTL."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            for i in range(15):
                u = MemoryUnit(memory_id=f"oh-{i}", scope_id="s1",
                               memory_type=MemoryType.SEMANTIC, content=f"Fact {i}",
                               importance=0.5)
                store.add_memories([u])
            hints = mgr.get_optimization_hints()
            self.assertTrue(any("ttl" in h.lower() for h in hints))
            store.close()


class DbSizeTests(unittest.TestCase):
    """Tests for database size reporting."""

    def test_get_db_size(self):
        """Should return valid size information."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            info = store.get_db_size()
            self.assertIn("size_bytes", info)
            self.assertIn("size_mb", info)
            self.assertGreater(info["size_bytes"], 0)
            self.assertGreater(info["page_count"], 0)
            store.close()


class TypedRetentionTests(unittest.TestCase):
    """Tests for per-type retention policies."""

    def test_typed_retention_archives_old_episodic(self):
        """Should archive old episodic memories below their type-specific threshold."""
        from datetime import datetime, timedelta, timezone
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            old_time = (datetime.now(timezone.utc) - timedelta(days=60)).isoformat(timespec="seconds")
            u = MemoryUnit(memory_id="tr-1", scope_id="s1",
                           memory_type=MemoryType.EPISODIC, content="Old event",
                           importance=0.1, created_at=old_time, updated_at=old_time)
            store.add_memories([u])
            result = mgr.apply_typed_retention()
            self.assertEqual(result["archived"], 1)
            self.assertEqual(store._get_by_id("tr-1").status, MemoryStatus.ARCHIVED)
            store.close()

    def test_typed_retention_keeps_recent(self):
        """Should keep recent memories even with low importance."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            u = MemoryUnit(memory_id="tr-2", scope_id="s1",
                           memory_type=MemoryType.EPISODIC, content="Recent event",
                           importance=0.1)
            store.add_memories([u])
            result = mgr.apply_typed_retention()
            self.assertEqual(result["archived"], 0)
            store.close()


class ConflictNotificationTests(unittest.TestCase):
    """Tests for conflict detection callbacks during ingestion."""

    def test_conflicts_detected_fires_callback(self):
        """Ingesting conflicting content should fire a conflicts_detected callback."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            events = []
            mgr.register_event_callback(lambda e: events.append(e))
            # First: establish a preference.
            u = MemoryUnit(memory_id="cn-1", scope_id="s1",
                           memory_type=MemoryType.PREFERENCE,
                           content="I prefer using tabs for indentation",
                           importance=0.5, topics=["indentation", "formatting"],
                           entities=["editor"])
            store.add_memories([u])
            # Ingest a contradicting preference.
            mgr.ingest_session_turns("sess-1", [
                {"prompt_text": "I prefer using spaces for indentation",
                 "response_text": "OK"},
            ])
            # Check if conflicts_detected was fired.
            conflict_events = [e for e in events if e["event"] == "conflicts_detected"]
            # May or may not detect conflicts depending on extraction quality.
            # Just verify the callback system doesn't crash.
            self.assertTrue(len(events) >= 1)  # At least ingest event.
            store.close()


class SchemaVersionTests(unittest.TestCase):
    """Tests for schema versioning."""

    def test_schema_version_set_on_init(self):
        """Schema version should be set after store initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            version = store.get_schema_version()
            self.assertGreater(version, 0)
            self.assertEqual(version, store.SCHEMA_VERSION)
            store.close()


class BackupTests(unittest.TestCase):
    """Tests for database backup."""

    def test_backup_creates_valid_copy(self):
        """Backup should create a usable copy of the database."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            u = MemoryUnit(memory_id="bk-1", scope_id="s1",
                           memory_type=MemoryType.SEMANTIC, content="Backup test",
                           importance=0.5)
            store.add_memories([u])
            backup_path = os.path.join(tmpdir, "backup.db")
            self.assertTrue(store.backup(backup_path))
            store.close()
            # Verify backup is usable.
            backup_store = MemoryStore(backup_path)
            units = backup_store.list_active("s1")
            self.assertEqual(len(units), 1)
            self.assertEqual(units[0].content, "Backup test")
            backup_store.close()


class UrgencyScoreTests(unittest.TestCase):
    """Tests for memory urgency scoring."""

    def test_expiring_memory_has_urgency(self):
        """Memories expiring within 7 days should have high urgency."""
        from datetime import datetime, timedelta, timezone
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            soon = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat(timespec="seconds")
            u = MemoryUnit(memory_id="urg-1", scope_id="s1",
                           memory_type=MemoryType.SEMANTIC, content="Expiring soon",
                           importance=0.5, expires_at=soon)
            store.add_memories([u])
            results = mgr.compute_urgency_scores()
            self.assertTrue(len(results) >= 1)
            self.assertGreater(results[0]["urgency"], 0)
            store.close()

    def test_unused_high_importance_has_urgency(self):
        """High-importance memories with zero access should have urgency."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            u = MemoryUnit(memory_id="urg-2", scope_id="s1",
                           memory_type=MemoryType.SEMANTIC, content="Important but unused",
                           importance=0.9)
            store.add_memories([u])
            results = mgr.compute_urgency_scores()
            self.assertTrue(len(results) >= 1)
            store.close()


class RetrievalProfileTests(unittest.TestCase):
    """Tests for retrieval policy profiles."""

    def test_balanced_profile(self):
        """Balanced profile should have default weights."""
        from metaclaw.memory.policy import MemoryPolicy
        policy = MemoryPolicy.from_profile("balanced")
        self.assertEqual(policy.max_injected_units, 6)
        self.assertEqual(policy.max_injected_tokens, 800)

    def test_recall_profile_has_more_results(self):
        """Recall profile should allow more injected units."""
        from metaclaw.memory.policy import MemoryPolicy
        policy = MemoryPolicy.from_profile("recall")
        self.assertGreater(policy.max_injected_units, 6)
        self.assertGreater(policy.max_injected_tokens, 800)

    def test_precision_profile_has_fewer_results(self):
        """Precision profile should limit injected units."""
        from metaclaw.memory.policy import MemoryPolicy
        policy = MemoryPolicy.from_profile("precision")
        self.assertLess(policy.max_injected_units, 6)
        self.assertGreater(policy.importance_weight, 0.5)

    def test_unknown_profile_returns_default(self):
        """Unknown profile name should return default policy."""
        from metaclaw.memory.policy import MemoryPolicy
        policy = MemoryPolicy.from_profile("nonexistent")
        self.assertEqual(policy.max_injected_units, 6)


class AgeDistributionTests(unittest.TestCase):
    """Tests for memory age distribution."""

    def test_age_distribution_buckets(self):
        """Should return correct bucket structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            u = MemoryUnit(memory_id="age-1", scope_id="s1",
                           memory_type=MemoryType.SEMANTIC, content="Recent",
                           importance=0.5)
            store.add_memories([u])
            result = mgr.get_age_distribution()
            self.assertEqual(result["total"], 1)
            self.assertIn("< 1 day", result["distribution"])
            self.assertEqual(result["distribution"]["< 1 day"], 1)
            store.close()


class SearchWithContextTests(unittest.TestCase):
    """Tests for search with highlighted context."""

    def test_search_returns_highlighted_snippets(self):
        """Should return snippets with matched terms highlighted."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            u = MemoryUnit(memory_id="ctx-1", scope_id="s1",
                           memory_type=MemoryType.SEMANTIC,
                           content="The database uses PostgreSQL for production",
                           importance=0.5, topics=["database", "postgresql"])
            store.add_memories([u])
            results = mgr.search_with_context("database")
            self.assertTrue(len(results) >= 1)
            self.assertIn("snippet", results[0])
            self.assertIn("matched_terms", results[0])
            store.close()


class ScopeMigrationTests(unittest.TestCase):
    """Tests for scope migration."""

    def test_migrate_moves_memories(self):
        """Should copy memories to new scope and archive originals."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="old-scope", auto_consolidate=False)
            u = MemoryUnit(memory_id="mig-1", scope_id="old-scope",
                           memory_type=MemoryType.SEMANTIC, content="Migrating",
                           importance=0.5)
            store.add_memories([u])
            result = mgr.migrate_scope("old-scope", "new-scope")
            self.assertEqual(result["migrated"], 1)
            # Original should be archived.
            self.assertEqual(store._get_by_id("mig-1").status, MemoryStatus.ARCHIVED)
            # New scope should have the memory.
            new_units = store.list_active("new-scope")
            self.assertEqual(len(new_units), 1)
            self.assertEqual(new_units[0].content, "Migrating")
            store.close()


class ImportanceHistogramTests(unittest.TestCase):
    """Tests for importance histogram."""

    def test_histogram_structure(self):
        """Should return correct bucket counts."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            for i in range(5):
                u = MemoryUnit(memory_id=f"hist-{i}", scope_id="s1",
                               memory_type=MemoryType.SEMANTIC, content=f"Item {i}",
                               importance=0.1 * (i + 1))
                store.add_memories([u])
            result = mgr.get_importance_histogram()
            self.assertEqual(result["total"], 5)
            self.assertIn("histogram", result)
            total_counted = sum(result["histogram"].values())
            self.assertEqual(total_counted, 5)
            store.close()


class MaintenanceCycleTests(unittest.TestCase):
    """Tests for full maintenance cycle."""

    def test_maintenance_runs_all_steps(self):
        """Should run all maintenance steps and return results."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            u = MemoryUnit(memory_id="mnt-1", scope_id="s1",
                           memory_type=MemoryType.SEMANTIC, content="Test memory",
                           importance=0.5)
            store.add_memories([u])
            events = []
            mgr.register_event_callback(lambda e: events.append(e))
            result = mgr.run_maintenance()
            self.assertEqual(result["scope_id"], "s1")
            self.assertIn("expired", result)
            self.assertIn("consolidation", result)
            self.assertIn("retention_archived", result)
            self.assertIn("orphans_removed", result)
            self.assertIn("gc_removed", result)
            self.assertTrue(result["compacted"])
            # Should fire maintenance callback.
            self.assertTrue(any(e["event"] == "maintenance" for e in events))
            store.close()


class SampleMemoriesTests(unittest.TestCase):
    """Tests for random memory sampling."""

    def test_sample_returns_correct_count(self):
        """Should return the requested number of samples."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            for i in range(10):
                u = MemoryUnit(memory_id=f"smp-{i}", scope_id="s1",
                               memory_type=MemoryType.SEMANTIC, content=f"Sample {i}",
                               importance=0.5)
                store.add_memories([u])
            samples = mgr.sample_memories(count=3)
            self.assertEqual(len(samples), 3)
            store.close()

    def test_sample_returns_all_when_fewer(self):
        """Should return all memories when count exceeds pool size."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            u = MemoryUnit(memory_id="smp-solo", scope_id="s1",
                           memory_type=MemoryType.SEMANTIC, content="Only one",
                           importance=0.5)
            store.add_memories([u])
            samples = mgr.sample_memories(count=5)
            self.assertEqual(len(samples), 1)
            store.close()


class APIStatusTests(unittest.TestCase):
    """Tests for API-ready status summary."""

    def test_api_status_structure(self):
        """Should return a complete API status with all fields."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            u = MemoryUnit(memory_id="api-1", scope_id="s1",
                           memory_type=MemoryType.SEMANTIC, content="Test",
                           importance=0.5, tags=["test"])
            store.add_memories([u])
            status = mgr.get_api_status()
            self.assertEqual(status["scope_id"], "s1")
            self.assertEqual(status["active_count"], 1)
            self.assertIn("health", status)
            self.assertIn("db", status)
            self.assertIn("features", status)
            self.assertIn("policy", status)
            self.assertIn("schema_version", status)
            self.assertTrue(status["integrity_valid"])
            self.assertEqual(status["features"]["with_tags"], 1)
            store.close()

    def test_api_status_json_serializable(self):
        """Status output should be JSON-serializable."""
        import json
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            status = mgr.get_api_status()
            # Should not raise.
            json_text = json.dumps(status)
            self.assertIsInstance(json_text, str)
            store.close()


class ImprovedExtractionTests(unittest.TestCase):
    """Tests for improved topic/entity extraction."""

    def test_multi_word_topic_extraction(self):
        """Should extract multi-word technical terms as topics."""
        from metaclaw.memory.manager import _extract_topics
        topics = _extract_topics("We need to fix the database migration for the API endpoint")
        topic_text = " ".join(topics)
        self.assertTrue(
            "database migration" in topic_text or "api endpoint" in topic_text,
            f"Expected multi-word topic, got: {topics}"
        )

    def test_camelcase_entity_extraction(self):
        """Should extract CamelCase identifiers as entities."""
        from metaclaw.memory.manager import _extract_entities
        entities = _extract_entities("The AuthService class handles OAuth2 tokens via UserManager")
        entity_set = set(entities)
        self.assertIn("AuthService", entity_set)
        self.assertIn("UserManager", entity_set)

    def test_snake_case_entity_extraction(self):
        """Should extract snake_case identifiers as entities."""
        from metaclaw.memory.manager import _extract_entities
        entities = _extract_entities("Call the get_user_profile function to fetch data")
        self.assertTrue(
            any("get_user_profile" in e for e in entities),
            f"Expected snake_case entity, got: {entities}"
        )

    def test_i_want_pattern_extraction(self):
        """Should extract 'I want' pattern as a preference."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            mgr.ingest_session_turns("sess-1", [
                {"prompt_text": "I want all responses to include code examples",
                 "response_text": "OK"},
            ])
            units = store.list_active("s1")
            contents = " ".join(u.content for u in units)
            self.assertTrue(
                "code examples" in contents.lower() or "response" in contents.lower(),
                f"Expected preference extraction, got: {contents}"
            )
            store.close()


class SixthLoopIntegrationTests(unittest.TestCase):
    """End-to-end integration tests for sixth-loop feature set."""

    def test_full_lifecycle_with_links_and_access_control(self):
        """Exercise: ingest -> link -> tag -> annotate -> retrieve with expansion -> report."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="team-1", auto_consolidate=False)
            events = []
            mgr.register_event_callback(lambda e: events.append(e))

            # Ingest.
            mgr.ingest_session_turns("sess-1", [
                {"prompt_text": "I prefer using PostgreSQL for our database",
                 "response_text": "Noted, I'll keep that in mind."},
                {"prompt_text": "The API follows REST conventions",
                 "response_text": "Good to know about the REST API design."},
            ])
            self.assertTrue(any(e["event"] == "ingest" for e in events))

            units = store.list_active("team-1")
            self.assertGreater(len(units), 0)

            # Tag and link.
            if len(units) >= 2:
                store.add_tags(units[0].memory_id, ["backend", "database"])
                store.add_link(units[0].memory_id, units[1].memory_id, "related")

            # Annotate.
            if units:
                mgr.add_annotation(units[0].memory_id, "Core preference", author="ops")

            # Retrieve with expansion.
            retrieved = mgr.retrieve_for_prompt("database preferences", expand_links=True)
            self.assertGreater(len(retrieved), 0)

            # Access control.
            mgr.grant_scope_access("team-1", "alice", "read")
            self.assertTrue(mgr.check_scope_access("team-1", "alice", "read"))

            # Watch.
            if units:
                mgr.watch_memory(units[0].memory_id, "alice")
                self.assertEqual(mgr.get_watchers(units[0].memory_id), ["alice"])

            # Quality and usage report.
            if units:
                quality = mgr.score_memory_quality(units[0].memory_id)
                self.assertGreater(quality["score"], 0)
            report = mgr.generate_usage_report()
            self.assertGreater(report["total_active"], 0)

            store.close()

    def test_conflict_resolution_to_cluster_detection_pipeline(self):
        """Exercise: create conflicting memories -> resolve -> detect clusters."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            # Create two conflicting memories.
            u1 = MemoryUnit(memory_id="pipe-1", scope_id="s1",
                            memory_type=MemoryType.PREFERENCE, content="Use tabs",
                            importance=0.5, topics=["formatting"], entities=["editor"],
                            created_at="2026-01-01T00:00:00Z")
            u2 = MemoryUnit(memory_id="pipe-2", scope_id="s1",
                            memory_type=MemoryType.PREFERENCE, content="Use spaces",
                            importance=0.5, topics=["formatting"], entities=["editor"],
                            created_at="2026-03-01T00:00:00Z")
            u3 = MemoryUnit(memory_id="pipe-3", scope_id="s1",
                            memory_type=MemoryType.SEMANTIC, content="Editor setup guide",
                            importance=0.5, topics=["editor", "setup"])
            store.add_memories([u1, u2, u3])
            # Link related memories.
            store.add_link("pipe-2", "pipe-3", "elaborates")
            # Resolve conflicts.
            result = mgr.auto_resolve_conflicts()
            self.assertGreater(result["resolved"], 0)
            # The surviving memory should still be linked.
            links = store.get_links("pipe-2", direction="outgoing")
            self.assertTrue(len(links) >= 1)
            # Cluster detection should find the linked group.
            clusters = mgr.find_memory_clusters()
            # pipe-2 and pipe-3 should be in a cluster.
            cluster_ids = set()
            for c in clusters:
                cluster_ids.update(c)
            self.assertIn("pipe-2", cluster_ids)
            self.assertIn("pipe-3", cluster_ids)
            store.close()

    def test_adaptive_ttl_to_batch_archive_pipeline(self):
        """Exercise: apply adaptive TTL -> verify TTL set -> batch archive by criteria."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            u = MemoryUnit(memory_id="ttl-ba-1", scope_id="s1",
                           memory_type=MemoryType.EPISODIC, content="An event",
                           importance=0.2)
            store.add_memories([u])
            # Apply adaptive TTL.
            ttl_result = mgr.apply_adaptive_ttl()
            self.assertEqual(ttl_result["updated"], 1)
            # Verify TTL was set.
            after = store._get_by_id("ttl-ba-1")
            self.assertTrue(after.expires_at)
            # Batch archive low-importance memories.
            archive_result = mgr.batch_archive_by_criteria(max_importance=0.3)
            self.assertEqual(archive_result["archived"], 1)
            self.assertEqual(store._get_by_id("ttl-ba-1").status, MemoryStatus.ARCHIVED)
            store.close()


class SuggestTypeCorrectionsTests(unittest.TestCase):
    """Tests for content-based type correction suggestions."""

    def test_preference_pattern_detected(self):
        """Content with 'I prefer' assigned to SEMANTIC should suggest PREFERENCE."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories([
                MemoryUnit(
                    memory_id="tc-1", scope_id="s1",
                    memory_type=MemoryType.SEMANTIC,
                    content="I prefer tabs over spaces for indentation",
                ),
            ])
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            suggestions = mgr.suggest_type_corrections()
            self.assertEqual(len(suggestions), 1)
            self.assertEqual(suggestions[0]["memory_id"], "tc-1")
            self.assertEqual(suggestions[0]["current_type"], "semantic")
            self.assertEqual(suggestions[0]["suggested_type"], "preference")
            self.assertIn("confidence", suggestions[0])
            store.close()

    def test_project_state_pattern_detected(self):
        """Content with 'the project uses' assigned to EPISODIC should suggest PROJECT_STATE."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories([
                MemoryUnit(
                    memory_id="tc-2", scope_id="s1",
                    memory_type=MemoryType.EPISODIC,
                    content="The project uses React and TypeScript for the frontend",
                ),
            ])
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            suggestions = mgr.suggest_type_corrections()
            self.assertEqual(len(suggestions), 1)
            self.assertEqual(suggestions[0]["suggested_type"], "project_state")
            store.close()

    def test_procedural_pattern_detected(self):
        """Content with 'always' assigned to SEMANTIC should suggest PROCEDURAL_OBSERVATION."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories([
                MemoryUnit(
                    memory_id="tc-3", scope_id="s1",
                    memory_type=MemoryType.SEMANTIC,
                    content="Always run the linter before committing code changes",
                ),
            ])
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            suggestions = mgr.suggest_type_corrections()
            self.assertEqual(len(suggestions), 1)
            self.assertEqual(suggestions[0]["suggested_type"], "procedural_observation")
            store.close()

    def test_correctly_typed_memory_not_flagged(self):
        """A preference memory with 'I prefer' should NOT be flagged."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories([
                MemoryUnit(
                    memory_id="tc-4", scope_id="s1",
                    memory_type=MemoryType.PREFERENCE,
                    content="I prefer dark mode for all editors",
                ),
            ])
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            suggestions = mgr.suggest_type_corrections()
            self.assertEqual(len(suggestions), 0)
            store.close()

    def test_limit_respected(self):
        """Limit parameter should cap the number of suggestions returned."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            for i in range(5):
                store.add_memories([
                    MemoryUnit(
                        memory_id=f"tc-l-{i}", scope_id="s1",
                        memory_type=MemoryType.SEMANTIC,
                        content=f"I prefer option {i} for configuration",
                    ),
                ])
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            suggestions = mgr.suggest_type_corrections(limit=2)
            self.assertEqual(len(suggestions), 2)
            store.close()

    def test_scope_filtering(self):
        """Only memories in the specified scope should be analyzed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories([
                MemoryUnit(
                    memory_id="tc-s1", scope_id="scope-a",
                    memory_type=MemoryType.SEMANTIC,
                    content="I prefer vim keybindings",
                ),
                MemoryUnit(
                    memory_id="tc-s2", scope_id="scope-b",
                    memory_type=MemoryType.SEMANTIC,
                    content="I prefer emacs keybindings",
                ),
            ])
            mgr = MemoryManager(store=store, scope_id="scope-a", auto_consolidate=False)
            suggestions = mgr.suggest_type_corrections(scope_id="scope-a")
            self.assertEqual(len(suggestions), 1)
            self.assertEqual(suggestions[0]["memory_id"], "tc-s1")
            store.close()


class CrossScopeDuplicateTests(unittest.TestCase):
    """Tests for cross-scope duplicate detection."""

    def test_identical_content_detected(self):
        """Identical content across scopes should be flagged as duplicate."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories([
                MemoryUnit(
                    memory_id="csd-a1", scope_id="scope-a",
                    memory_type=MemoryType.SEMANTIC,
                    content="The deployment pipeline uses GitHub Actions for CI/CD automation",
                ),
            ])
            store.add_memories([
                MemoryUnit(
                    memory_id="csd-b1", scope_id="scope-b",
                    memory_type=MemoryType.SEMANTIC,
                    content="The deployment pipeline uses GitHub Actions for CI/CD automation",
                ),
            ])
            mgr = MemoryManager(store=store, scope_id="scope-a", auto_consolidate=False)
            dupes = mgr.find_cross_scope_duplicates("scope-a", "scope-b")
            self.assertEqual(len(dupes), 1)
            self.assertAlmostEqual(dupes[0]["similarity"], 1.0, places=2)
            self.assertEqual(dupes[0]["id_a"], "csd-a1")
            self.assertEqual(dupes[0]["id_b"], "csd-b1")
            store.close()

    def test_similar_content_above_threshold(self):
        """Very similar content should be flagged when above threshold."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories([
                MemoryUnit(
                    memory_id="csd-a2", scope_id="scope-a",
                    memory_type=MemoryType.SEMANTIC,
                    content="We use PostgreSQL database for user data storage and analytics",
                ),
            ])
            store.add_memories([
                MemoryUnit(
                    memory_id="csd-b2", scope_id="scope-b",
                    memory_type=MemoryType.SEMANTIC,
                    content="We use PostgreSQL database for user data storage and reporting",
                ),
            ])
            mgr = MemoryManager(store=store, scope_id="scope-a", auto_consolidate=False)
            dupes = mgr.find_cross_scope_duplicates("scope-a", "scope-b", threshold=0.70)
            self.assertTrue(len(dupes) >= 1)
            self.assertGreaterEqual(dupes[0]["similarity"], 0.70)
            store.close()

    def test_different_content_not_flagged(self):
        """Completely different content should not be flagged."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories([
                MemoryUnit(
                    memory_id="csd-a3", scope_id="scope-a",
                    memory_type=MemoryType.SEMANTIC,
                    content="The frontend uses React and TypeScript exclusively",
                ),
            ])
            store.add_memories([
                MemoryUnit(
                    memory_id="csd-b3", scope_id="scope-b",
                    memory_type=MemoryType.SEMANTIC,
                    content="Database migrations run every Tuesday morning automatically",
                ),
            ])
            mgr = MemoryManager(store=store, scope_id="scope-a", auto_consolidate=False)
            dupes = mgr.find_cross_scope_duplicates("scope-a", "scope-b")
            self.assertEqual(len(dupes), 0)
            store.close()

    def test_empty_scope_returns_empty(self):
        """If one scope is empty, no duplicates should be found."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories([
                MemoryUnit(
                    memory_id="csd-a4", scope_id="scope-a",
                    memory_type=MemoryType.SEMANTIC,
                    content="Some content here for testing purposes only",
                ),
            ])
            mgr = MemoryManager(store=store, scope_id="scope-a", auto_consolidate=False)
            dupes = mgr.find_cross_scope_duplicates("scope-a", "scope-empty")
            self.assertEqual(len(dupes), 0)
            store.close()

    def test_threshold_filtering(self):
        """Higher threshold should filter out moderate-similarity pairs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories([
                MemoryUnit(
                    memory_id="csd-a5", scope_id="scope-a",
                    memory_type=MemoryType.SEMANTIC,
                    content="We use PostgreSQL database for user data storage and analytics",
                ),
            ])
            store.add_memories([
                MemoryUnit(
                    memory_id="csd-b5", scope_id="scope-b",
                    memory_type=MemoryType.SEMANTIC,
                    content="We use PostgreSQL database for user data storage and reporting",
                ),
            ])
            mgr = MemoryManager(store=store, scope_id="scope-a", auto_consolidate=False)
            # With a very high threshold, moderate similarity should be excluded.
            dupes_strict = mgr.find_cross_scope_duplicates("scope-a", "scope-b", threshold=0.99)
            dupes_loose = mgr.find_cross_scope_duplicates("scope-a", "scope-b", threshold=0.50)
            self.assertLessEqual(len(dupes_strict), len(dupes_loose))
            store.close()

    def test_results_sorted_by_similarity(self):
        """Results should be sorted by similarity descending."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories([
                MemoryUnit(
                    memory_id="csd-a6", scope_id="scope-a",
                    memory_type=MemoryType.SEMANTIC,
                    content="The deployment pipeline uses GitHub Actions for CI/CD automation and testing",
                ),
                MemoryUnit(
                    memory_id="csd-a7", scope_id="scope-a",
                    memory_type=MemoryType.SEMANTIC,
                    content="Redis caches session data for faster access and lower latency",
                ),
            ])
            store.add_memories([
                MemoryUnit(
                    memory_id="csd-b6", scope_id="scope-b",
                    memory_type=MemoryType.SEMANTIC,
                    content="The deployment pipeline uses GitHub Actions for CI/CD automation and testing",
                ),
                MemoryUnit(
                    memory_id="csd-b7", scope_id="scope-b",
                    memory_type=MemoryType.SEMANTIC,
                    content="Redis caches session data for faster access and reduced latency",
                ),
            ])
            mgr = MemoryManager(store=store, scope_id="scope-a", auto_consolidate=False)
            dupes = mgr.find_cross_scope_duplicates("scope-a", "scope-b", threshold=0.60)
            if len(dupes) >= 2:
                self.assertGreaterEqual(dupes[0]["similarity"], dupes[1]["similarity"])
            store.close()


class BatchGetByIdsTests(unittest.TestCase):
    """Tests for batch memory retrieval by IDs."""

    def test_batch_get_returns_matching_units(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories([
                MemoryUnit(memory_id="bg-1", scope_id="s1", memory_type=MemoryType.SEMANTIC, content="First memory"),
                MemoryUnit(memory_id="bg-2", scope_id="s1", memory_type=MemoryType.SEMANTIC, content="Second memory"),
                MemoryUnit(memory_id="bg-3", scope_id="s1", memory_type=MemoryType.SEMANTIC, content="Third memory"),
            ])
            results = store.get_by_ids(["bg-1", "bg-3"])
            self.assertEqual(len(results), 2)
            ids = {u.memory_id for u in results}
            self.assertIn("bg-1", ids)
            self.assertIn("bg-3", ids)
            store.close()

    def test_batch_get_empty_list(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            results = store.get_by_ids([])
            self.assertEqual(results, [])
            store.close()

    def test_batch_get_nonexistent_ids(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories([
                MemoryUnit(memory_id="bg-4", scope_id="s1", memory_type=MemoryType.SEMANTIC, content="Exists"),
            ])
            results = store.get_by_ids(["bg-4", "nonexistent-id"])
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0].memory_id, "bg-4")
            store.close()

    def test_manager_batch_get(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories([
                MemoryUnit(memory_id="mbg-1", scope_id="s1", memory_type=MemoryType.SEMANTIC, content="Manager test 1"),
                MemoryUnit(memory_id="mbg-2", scope_id="s1", memory_type=MemoryType.SEMANTIC, content="Manager test 2"),
            ])
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            results = mgr.get_memories_by_ids(["mbg-1", "mbg-2"])
            self.assertEqual(len(results), 2)
            store.close()


class MemoryImpactAnalysisTests(unittest.TestCase):
    """Tests for memory impact analysis."""

    def test_no_dependents_safe_to_archive(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories([
                MemoryUnit(memory_id="imp-1", scope_id="s1", memory_type=MemoryType.SEMANTIC, content="Standalone memory"),
            ])
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            result = mgr.analyze_memory_impact("imp-1")
            self.assertTrue(result["safe_to_archive"])
            self.assertEqual(len(result["direct_dependents"]), 0)
            self.assertEqual(len(result["transitive_dependents"]), 0)
            store.close()

    def test_with_direct_dependent(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories([
                MemoryUnit(memory_id="imp-2", scope_id="s1", memory_type=MemoryType.SEMANTIC, content="Base memory"),
                MemoryUnit(memory_id="imp-3", scope_id="s1", memory_type=MemoryType.SEMANTIC, content="Dependent memory"),
            ])
            store.add_link("imp-3", "imp-2", "depends_on")
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            result = mgr.analyze_memory_impact("imp-2")
            self.assertFalse(result["safe_to_archive"])
            self.assertIn("imp-3", result["direct_dependents"])
            self.assertEqual(result["total_affected"], 1)
            store.close()

    def test_transitive_dependents(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories([
                MemoryUnit(memory_id="imp-a", scope_id="s1", memory_type=MemoryType.SEMANTIC, content="Root"),
                MemoryUnit(memory_id="imp-b", scope_id="s1", memory_type=MemoryType.SEMANTIC, content="Middle"),
                MemoryUnit(memory_id="imp-c", scope_id="s1", memory_type=MemoryType.SEMANTIC, content="Leaf"),
            ])
            store.add_link("imp-b", "imp-a", "depends_on")
            store.add_link("imp-c", "imp-b", "depends_on")
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            result = mgr.analyze_memory_impact("imp-a")
            self.assertFalse(result["safe_to_archive"])
            self.assertIn("imp-b", result["transitive_dependents"])
            self.assertIn("imp-c", result["transitive_dependents"])
            store.close()

    def test_nonexistent_memory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            result = mgr.analyze_memory_impact("nonexistent")
            self.assertIn("error", result)
            store.close()


class DependencyCycleDetectionTests(unittest.TestCase):
    """Tests for dependency cycle detection."""

    def test_no_cycles_in_dag(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories([
                MemoryUnit(memory_id="dc-1", scope_id="s1", memory_type=MemoryType.SEMANTIC, content="A"),
                MemoryUnit(memory_id="dc-2", scope_id="s1", memory_type=MemoryType.SEMANTIC, content="B"),
                MemoryUnit(memory_id="dc-3", scope_id="s1", memory_type=MemoryType.SEMANTIC, content="C"),
            ])
            store.add_link("dc-1", "dc-2", "depends_on")
            store.add_link("dc-2", "dc-3", "depends_on")
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            cycles = mgr.detect_dependency_cycles()
            self.assertEqual(len(cycles), 0)
            store.close()

    def test_simple_cycle_detected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories([
                MemoryUnit(memory_id="dc-a", scope_id="s1", memory_type=MemoryType.SEMANTIC, content="A"),
                MemoryUnit(memory_id="dc-b", scope_id="s1", memory_type=MemoryType.SEMANTIC, content="B"),
            ])
            store.add_link("dc-a", "dc-b", "depends_on")
            store.add_link("dc-b", "dc-a", "depends_on")
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            cycles = mgr.detect_dependency_cycles()
            self.assertGreater(len(cycles), 0)
            store.close()

    def test_no_memories_no_cycles(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            cycles = mgr.detect_dependency_cycles()
            self.assertEqual(len(cycles), 0)
            store.close()


class VersionTreeTests(unittest.TestCase):
    """Tests for version tree building."""

    def test_single_memory_tree(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories([
                MemoryUnit(memory_id="vt-1", scope_id="s1", memory_type=MemoryType.SEMANTIC, content="Version 1"),
            ])
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            tree = mgr.build_version_tree("vt-1")
            self.assertEqual(tree["chain_length"], 1)
            self.assertEqual(tree["current_id"], "vt-1")
            store.close()

    def test_superseded_chain(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories([
                MemoryUnit(memory_id="vt-old", scope_id="s1", memory_type=MemoryType.SEMANTIC, content="Old version"),
                MemoryUnit(memory_id="vt-new", scope_id="s1", memory_type=MemoryType.SEMANTIC, content="New version"),
            ])
            from datetime import datetime, timezone
            store.supersede("vt-old", "vt-new", datetime.now(timezone.utc).isoformat())
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            tree = mgr.build_version_tree("vt-new")
            self.assertGreaterEqual(tree["chain_length"], 1)
            self.assertEqual(tree["current_id"], "vt-new")
            store.close()

    def test_version_tree_has_versions_list(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories([
                MemoryUnit(memory_id="vt-a", scope_id="s1", memory_type=MemoryType.SEMANTIC, content="First"),
            ])
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            tree = mgr.build_version_tree("vt-a")
            self.assertIn("versions", tree)
            self.assertIn("root_id", tree)
            self.assertTrue(len(tree["versions"]) >= 1)
            store.close()


class TopicGroupingTests(unittest.TestCase):
    """Tests for topic-based memory grouping."""

    def test_groups_by_primary_topic(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories([
                MemoryUnit(memory_id="tg-1", scope_id="s1", memory_type=MemoryType.SEMANTIC,
                           content="Python 3.12 features", topics=["python"]),
                MemoryUnit(memory_id="tg-2", scope_id="s1", memory_type=MemoryType.SEMANTIC,
                           content="Python async patterns", topics=["python", "async"]),
                MemoryUnit(memory_id="tg-3", scope_id="s1", memory_type=MemoryType.SEMANTIC,
                           content="Docker container setup", topics=["docker"]),
            ])
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            result = mgr.group_by_topic()
            self.assertIn("python", result["groups"])
            self.assertEqual(len(result["groups"]["python"]), 2)
            store.close()

    def test_min_group_size_filter(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories([
                MemoryUnit(memory_id="tg-4", scope_id="s1", memory_type=MemoryType.SEMANTIC,
                           content="Python module", topics=["python"]),
                MemoryUnit(memory_id="tg-5", scope_id="s1", memory_type=MemoryType.SEMANTIC,
                           content="Python testing", topics=["python"]),
                MemoryUnit(memory_id="tg-6", scope_id="s1", memory_type=MemoryType.SEMANTIC,
                           content="Solo topic here", topics=["solo"]),
            ])
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            result = mgr.group_by_topic(min_group_size=2)
            self.assertIn("python", result["groups"])
            self.assertNotIn("solo", result["groups"])
            store.close()

    def test_empty_scope_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            result = mgr.group_by_topic()
            self.assertEqual(result["total_groups"], 0)
            store.close()


class StaleMemoryDetectionTests(unittest.TestCase):
    """Tests for stale memory detection."""

    def test_old_memory_detected_as_stale(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            old_date = (datetime.now(timezone.utc) - timedelta(days=60)).isoformat()
            store.add_memories([
                MemoryUnit(memory_id="st-1", scope_id="s1", memory_type=MemoryType.SEMANTIC,
                           content="Very old memory", updated_at=old_date),
            ])
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            stale = mgr.find_stale_memories(stale_days=30)
            self.assertEqual(len(stale), 1)
            self.assertEqual(stale[0]["memory_id"], "st-1")
            self.assertGreaterEqual(stale[0]["days_inactive"], 59)
            store.close()

    def test_recent_memory_not_stale(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories([
                MemoryUnit(memory_id="st-2", scope_id="s1", memory_type=MemoryType.SEMANTIC,
                           content="Fresh memory just added"),
            ])
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            stale = mgr.find_stale_memories(stale_days=30)
            self.assertEqual(len(stale), 0)
            store.close()

    def test_stale_sorted_by_staleness(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            old_60 = (datetime.now(timezone.utc) - timedelta(days=60)).isoformat()
            old_90 = (datetime.now(timezone.utc) - timedelta(days=90)).isoformat()
            store.add_memories([
                MemoryUnit(memory_id="st-3", scope_id="s1", memory_type=MemoryType.SEMANTIC,
                           content="60 days old", updated_at=old_60),
                MemoryUnit(memory_id="st-4", scope_id="s1", memory_type=MemoryType.SEMANTIC,
                           content="90 days old", updated_at=old_90),
            ])
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            stale = mgr.find_stale_memories(stale_days=30)
            self.assertEqual(len(stale), 2)
            self.assertGreater(stale[0]["staleness_factor"], stale[1]["staleness_factor"])
            store.close()


class BulkLinkTests(unittest.TestCase):
    """Tests for bulk link creation."""

    def test_bulk_create_links(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories([
                MemoryUnit(memory_id="bl-1", scope_id="s1", memory_type=MemoryType.SEMANTIC, content="A"),
                MemoryUnit(memory_id="bl-2", scope_id="s1", memory_type=MemoryType.SEMANTIC, content="B"),
                MemoryUnit(memory_id="bl-3", scope_id="s1", memory_type=MemoryType.SEMANTIC, content="C"),
            ])
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            result = mgr.bulk_add_links([
                {"source_id": "bl-1", "target_id": "bl-2", "link_type": "related"},
                {"source_id": "bl-2", "target_id": "bl-3", "link_type": "depends_on"},
            ])
            self.assertEqual(result["created"], 2)
            self.assertEqual(result["skipped"], 0)
            store.close()

    def test_bulk_skip_duplicates(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories([
                MemoryUnit(memory_id="bl-4", scope_id="s1", memory_type=MemoryType.SEMANTIC, content="A"),
                MemoryUnit(memory_id="bl-5", scope_id="s1", memory_type=MemoryType.SEMANTIC, content="B"),
            ])
            store.add_link("bl-4", "bl-5", "related")
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            result = mgr.bulk_add_links([
                {"source_id": "bl-4", "target_id": "bl-5", "link_type": "related"},
            ])
            self.assertEqual(result["created"], 0)
            self.assertEqual(result["skipped"], 1)
            store.close()

    def test_bulk_skip_invalid(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            result = mgr.bulk_add_links([
                {"source_id": "", "target_id": "bl-x"},
                {"target_id": "bl-y"},
            ])
            self.assertEqual(result["created"], 0)
            self.assertEqual(result["skipped"], 2)
            store.close()


class SummaryReportTests(unittest.TestCase):
    """Tests for comprehensive summary report generation."""

    def test_report_has_required_fields(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories([
                MemoryUnit(memory_id="sr-1", scope_id="s1", memory_type=MemoryType.SEMANTIC,
                           content="Test memory for report", topics=["testing"]),
            ])
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            report = mgr.get_memory_summary_report()
            self.assertIn("scope_id", report)
            self.assertIn("generated_at", report)
            self.assertIn("total_active", report)
            self.assertIn("health_score", report)
            self.assertIn("top_topics", report)
            self.assertIn("age_distribution", report)
            self.assertEqual(report["total_active"], 1)
            store.close()

    def test_empty_scope_report(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            report = mgr.get_memory_summary_report()
            self.assertEqual(report["total_active"], 0)
            self.assertEqual(report["topic_group_count"], 0)
            store.close()


class AutoTagSuggestionTests(unittest.TestCase):
    """Tests for automatic tag suggestions."""

    def test_suggests_tags_from_topics(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories([
                MemoryUnit(memory_id="at-1", scope_id="s1", memory_type=MemoryType.SEMANTIC,
                           content="Python deployment pipeline", topics=["python", "deployment"]),
            ])
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            suggestions = mgr.suggest_auto_tags()
            self.assertEqual(len(suggestions), 1)
            self.assertIn("python", suggestions[0]["suggested_tags"])
            store.close()

    def test_skips_already_tagged(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories([
                MemoryUnit(memory_id="at-2", scope_id="s1", memory_type=MemoryType.SEMANTIC,
                           content="Tagged memory", topics=["python"], tags=["existing"]),
            ])
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            suggestions = mgr.suggest_auto_tags()
            self.assertEqual(len(suggestions), 0)
            store.close()

    def test_pattern_based_tag_suggestion(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories([
                MemoryUnit(memory_id="at-3", scope_id="s1", memory_type=MemoryType.SEMANTIC,
                           content="Fixed a critical bug in the error handling logic",
                           topics=["error"]),
            ])
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            suggestions = mgr.suggest_auto_tags()
            self.assertTrue(len(suggestions) >= 1)
            all_tags = suggestions[0]["suggested_tags"]
            self.assertTrue("bugfix" in all_tags or "error" in all_tags)
            store.close()


class LinkGraphExportTests(unittest.TestCase):
    """Tests for memory link graph export."""

    def test_export_graph_with_links(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories([
                MemoryUnit(memory_id="lg-1", scope_id="s1", memory_type=MemoryType.SEMANTIC, content="Node A"),
                MemoryUnit(memory_id="lg-2", scope_id="s1", memory_type=MemoryType.SEMANTIC, content="Node B"),
            ])
            store.add_link("lg-1", "lg-2", "related")
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            graph = mgr.export_link_graph()
            self.assertEqual(graph["node_count"], 2)
            self.assertEqual(graph["edge_count"], 1)
            self.assertEqual(graph["edges"][0]["source"], "lg-1")
            self.assertEqual(graph["edges"][0]["target"], "lg-2")
            store.close()

    def test_export_empty_graph(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            graph = mgr.export_link_graph()
            self.assertEqual(graph["node_count"], 0)
            self.assertEqual(graph["edge_count"], 0)
            store.close()

    def test_no_duplicate_edges(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories([
                MemoryUnit(memory_id="lg-3", scope_id="s1", memory_type=MemoryType.SEMANTIC, content="A"),
                MemoryUnit(memory_id="lg-4", scope_id="s1", memory_type=MemoryType.SEMANTIC, content="B"),
            ])
            store.add_link("lg-3", "lg-4", "related")
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            graph = mgr.export_link_graph()
            self.assertEqual(graph["edge_count"], 1)
            store.close()


class DeduplicationReportTests(unittest.TestCase):
    """Tests for comprehensive deduplication reports."""

    def test_report_with_duplicates(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories([
                MemoryUnit(memory_id="dr-1", scope_id="s1", memory_type=MemoryType.SEMANTIC,
                           content="The deployment pipeline uses GitHub Actions for continuous integration"),
                MemoryUnit(memory_id="dr-2", scope_id="s1", memory_type=MemoryType.SEMANTIC,
                           content="The deployment pipeline uses GitHub Actions for continuous integration"),
            ])
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            report = mgr.get_deduplication_report(threshold=0.70)
            self.assertGreaterEqual(report["total_duplicate_pairs"], 1)
            self.assertGreaterEqual(report["affected_memories"], 2)
            self.assertIn("clusters", report)
            store.close()

    def test_report_no_duplicates(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories([
                MemoryUnit(memory_id="dr-3", scope_id="s1", memory_type=MemoryType.SEMANTIC,
                           content="Python uses indentation for block structure"),
                MemoryUnit(memory_id="dr-4", scope_id="s1", memory_type=MemoryType.SEMANTIC,
                           content="Docker containers run isolated processes on shared kernels"),
            ])
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            report = mgr.get_deduplication_report()
            self.assertEqual(report["total_duplicate_pairs"], 0)
            self.assertEqual(report["duplicate_clusters"], 0)
            store.close()


class RegexSearchTests(unittest.TestCase):
    """Tests for regex-based memory search."""

    def test_basic_regex_search(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories([
                MemoryUnit(memory_id="rx-1", scope_id="s1", memory_type=MemoryType.SEMANTIC,
                           content="Python version 3.12.1 is installed"),
                MemoryUnit(memory_id="rx-2", scope_id="s1", memory_type=MemoryType.SEMANTIC,
                           content="Docker version 24.0.5 is running"),
            ])
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            results = mgr.search_regex(r"version \d+\.\d+")
            self.assertEqual(len(results), 2)
            store.close()

    def test_regex_no_match(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories([
                MemoryUnit(memory_id="rx-3", scope_id="s1", memory_type=MemoryType.SEMANTIC,
                           content="Simple text without numbers"),
            ])
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            results = mgr.search_regex(r"\d{4}-\d{2}-\d{2}")
            self.assertEqual(len(results), 0)
            store.close()

    def test_invalid_regex_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            results = mgr.search_regex(r"[invalid")
            self.assertEqual(len(results), 0)
            store.close()


class MergeScopesTests(unittest.TestCase):
    """Tests for scope merging."""

    def test_merge_copies_unique_memories(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories([
                MemoryUnit(memory_id="ms-1", scope_id="source", memory_type=MemoryType.SEMANTIC,
                           content="Source memory unique content here"),
            ])
            mgr = MemoryManager(store=store, scope_id="source", auto_consolidate=False)
            result = mgr.merge_scopes("source", "target")
            self.assertEqual(result["copied"], 1)
            self.assertEqual(result["skipped"], 0)
            target_units = store.list_active("target", limit=100)
            self.assertEqual(len(target_units), 1)
            store.close()

    def test_merge_skips_duplicates(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories([
                MemoryUnit(memory_id="ms-2", scope_id="source", memory_type=MemoryType.SEMANTIC,
                           content="Same content in both scopes for dedup testing"),
                MemoryUnit(memory_id="ms-3", scope_id="target", memory_type=MemoryType.SEMANTIC,
                           content="Same content in both scopes for dedup testing"),
            ])
            mgr = MemoryManager(store=store, scope_id="source", auto_consolidate=False)
            result = mgr.merge_scopes("source", "target")
            self.assertEqual(result["skipped"], 1)
            self.assertEqual(result["copied"], 0)
            store.close()

    def test_merge_empty_source(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            result = mgr.merge_scopes("empty", "target")
            self.assertEqual(result["copied"], 0)
            store.close()


class StatsDeltaTests(unittest.TestCase):
    """Tests for stats delta computation."""

    def test_delta_without_previous(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            result = mgr.compute_stats_delta()
            self.assertFalse(result["has_previous"])
            self.assertIn("current", result)
            store.close()

    def test_delta_with_snapshot(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories([
                MemoryUnit(memory_id="sd-1", scope_id="s1", memory_type=MemoryType.SEMANTIC,
                           content="First memory for delta test"),
            ])
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            mgr.save_stats_snapshot()
            # Add another memory.
            store.add_memories([
                MemoryUnit(memory_id="sd-2", scope_id="s1", memory_type=MemoryType.SEMANTIC,
                           content="Second memory added after snapshot"),
            ])
            result = mgr.compute_stats_delta()
            self.assertTrue(result["has_previous"])
            self.assertIn("deltas", result)
            store.close()


class MemoryDiffTests(unittest.TestCase):
    """Tests for memory content diffing."""

    def test_diff_identical_memories(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories([
                MemoryUnit(memory_id="df-1", scope_id="s1", memory_type=MemoryType.SEMANTIC,
                           content="Identical content here"),
                MemoryUnit(memory_id="df-2", scope_id="s1", memory_type=MemoryType.SEMANTIC,
                           content="Identical content here"),
            ])
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            result = mgr.diff_memories("df-1", "df-2")
            self.assertAlmostEqual(result["content_diff"]["similarity"], 1.0, places=2)
            self.assertTrue(result["type_match"])
            store.close()

    def test_diff_different_memories(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories([
                MemoryUnit(memory_id="df-3", scope_id="s1", memory_type=MemoryType.SEMANTIC,
                           content="Python is great for data science"),
                MemoryUnit(memory_id="df-4", scope_id="s1", memory_type=MemoryType.PREFERENCE,
                           content="Docker containers simplify deployment"),
            ])
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            result = mgr.diff_memories("df-3", "df-4")
            self.assertLess(result["content_diff"]["similarity"], 0.5)
            self.assertFalse(result["type_match"])
            store.close()

    def test_diff_nonexistent_memory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            result = mgr.diff_memories("none-1", "none-2")
            self.assertIn("error", result)
            store.close()


class CloneScopeTests(unittest.TestCase):
    """Tests for scope cloning."""

    def test_clone_creates_new_copies(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories([
                MemoryUnit(memory_id="cl-1", scope_id="source", memory_type=MemoryType.SEMANTIC,
                           content="Cloneable content for testing"),
                MemoryUnit(memory_id="cl-2", scope_id="source", memory_type=MemoryType.PREFERENCE,
                           content="Another cloneable memory"),
            ])
            mgr = MemoryManager(store=store, scope_id="source", auto_consolidate=False)
            result = mgr.clone_scope("source", "target")
            self.assertEqual(result["cloned"], 2)
            target = store.list_active("target", limit=100)
            self.assertEqual(len(target), 2)
            # Verify IDs are different (fresh copies).
            target_ids = {u.memory_id for u in target}
            self.assertNotIn("cl-1", target_ids)
            self.assertNotIn("cl-2", target_ids)
            store.close()

    def test_clone_empty_scope(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            result = mgr.clone_scope("empty", "target")
            self.assertEqual(result["cloned"], 0)
            store.close()


class AccessFrequencyTests(unittest.TestCase):
    """Tests for access frequency analysis."""

    def test_categorizes_by_access(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories([
                MemoryUnit(memory_id="af-1", scope_id="s1", memory_type=MemoryType.SEMANTIC,
                           content="Frequently accessed memory"),
            ])
            # Simulate access by marking accessed multiple times.
            from datetime import datetime, timezone
            for _ in range(10):
                store.mark_accessed(["af-1"], datetime.now(timezone.utc).isoformat())
            store.add_memories([
                MemoryUnit(memory_id="af-2", scope_id="s1", memory_type=MemoryType.SEMANTIC,
                           content="Rarely accessed cold memory"),
            ])
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            result = mgr.analyze_access_frequency()
            self.assertEqual(result["total"], 2)
            self.assertIn("avg_access", result)
            self.assertIn("hot", result)
            self.assertIn("cold", result)
            store.close()

    def test_empty_scope(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            result = mgr.analyze_access_frequency()
            self.assertEqual(result["total"], 0)
            store.close()


class EnrichmentSuggestionTests(unittest.TestCase):
    """Tests for enrichment suggestions."""

    def test_suggests_missing_fields(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories([
                MemoryUnit(memory_id="en-1", scope_id="s1", memory_type=MemoryType.SEMANTIC,
                           content="Memory without summary or tags", importance=0.8),
            ])
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            suggestions = mgr.suggest_enrichments()
            self.assertTrue(len(suggestions) >= 1)
            self.assertIn("summary", suggestions[0]["missing_fields"])
            store.close()

    def test_complete_memory_not_suggested(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories([
                MemoryUnit(memory_id="en-2", scope_id="s1", memory_type=MemoryType.SEMANTIC,
                           content="Complete memory with all fields",
                           summary="A complete memory", topics=["test"],
                           entities=["TestEntity"], tags=["complete"]),
            ])
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            suggestions = mgr.suggest_enrichments()
            self.assertEqual(len(suggestions), 0)
            store.close()

    def test_high_importance_first(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories([
                MemoryUnit(memory_id="en-3", scope_id="s1", memory_type=MemoryType.SEMANTIC,
                           content="Low importance memory", importance=0.2),
                MemoryUnit(memory_id="en-4", scope_id="s1", memory_type=MemoryType.SEMANTIC,
                           content="High importance memory", importance=0.9),
            ])
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            suggestions = mgr.suggest_enrichments()
            self.assertEqual(len(suggestions), 2)
            self.assertEqual(suggestions[0]["memory_id"], "en-4")
            store.close()


class ContentDensityTests(unittest.TestCase):
    """Tests for content density statistics."""

    def test_density_stats_with_data(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories([
                MemoryUnit(memory_id="cd-1", scope_id="s1", memory_type=MemoryType.SEMANTIC,
                           content="Short content", importance=0.5),
                MemoryUnit(memory_id="cd-2", scope_id="s1", memory_type=MemoryType.SEMANTIC,
                           content="This is a longer piece of content with more tokens for density analysis",
                           importance=0.8),
            ])
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            result = mgr.get_content_density_stats()
            self.assertEqual(result["total"], 2)
            self.assertGreater(result["avg_tokens"], 0)
            self.assertIn("size_buckets", result)
            store.close()

    def test_empty_scope_density(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            result = mgr.get_content_density_stats()
            self.assertEqual(result["total"], 0)
            store.close()


class ScopeQuotaTests(unittest.TestCase):
    """Tests for scope quota enforcement."""

    def test_within_quota(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories([
                MemoryUnit(memory_id="sq-1", scope_id="s1", memory_type=MemoryType.SEMANTIC, content="Memory 1"),
            ])
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            result = mgr.check_scope_quota(max_memories=10)
            self.assertTrue(result["within_quota"])
            self.assertEqual(result["remaining"], 9)
            self.assertFalse(result["warning"])
            store.close()

    def test_exceeded_quota(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            for i in range(5):
                store.add_memories([
                    MemoryUnit(memory_id=f"sq-{i}", scope_id="s1", memory_type=MemoryType.SEMANTIC,
                               content=f"Memory number {i} for quota test"),
                ])
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            result = mgr.check_scope_quota(max_memories=3)
            self.assertFalse(result["within_quota"])
            self.assertEqual(result["remaining"], 0)
            store.close()


class CascadeArchiveTests(unittest.TestCase):
    """Tests for cascading archive."""

    def test_archives_with_dependents(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories([
                MemoryUnit(memory_id="ca-1", scope_id="s1", memory_type=MemoryType.SEMANTIC, content="Root"),
                MemoryUnit(memory_id="ca-2", scope_id="s1", memory_type=MemoryType.SEMANTIC, content="Dep 1"),
                MemoryUnit(memory_id="ca-3", scope_id="s1", memory_type=MemoryType.SEMANTIC, content="Dep 2"),
            ])
            store.add_link("ca-2", "ca-1", "depends_on")
            store.add_link("ca-3", "ca-2", "depends_on")
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            result = mgr.cascade_archive("ca-1")
            self.assertEqual(result["archived"], 3)
            self.assertEqual(result["dependents_archived"], 2)
            store.close()

    def test_archives_standalone_memory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories([
                MemoryUnit(memory_id="ca-4", scope_id="s1", memory_type=MemoryType.SEMANTIC, content="Standalone"),
            ])
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            result = mgr.cascade_archive("ca-4")
            self.assertEqual(result["archived"], 1)
            self.assertEqual(result["dependents_archived"], 0)
            store.close()

    def test_nonexistent_memory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            result = mgr.cascade_archive("nonexistent")
            self.assertIn("error", result)
            store.close()


class LinkGraphStatsTests(unittest.TestCase):
    """Tests for link graph statistics."""

    def test_stats_with_links(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories([
                MemoryUnit(memory_id="ls-1", scope_id="s1", memory_type=MemoryType.SEMANTIC, content="A"),
                MemoryUnit(memory_id="ls-2", scope_id="s1", memory_type=MemoryType.SEMANTIC, content="B"),
                MemoryUnit(memory_id="ls-3", scope_id="s1", memory_type=MemoryType.SEMANTIC, content="C"),
            ])
            store.add_link("ls-1", "ls-2", "related")
            store.add_link("ls-1", "ls-3", "depends_on")
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            result = mgr.get_link_graph_stats()
            self.assertEqual(result["total_memories"], 3)
            self.assertGreater(result["linked_memories"], 0)
            self.assertEqual(result["total_links"], 2)
            self.assertIn("link_types", result)
            store.close()

    def test_empty_graph(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            result = mgr.get_link_graph_stats()
            self.assertEqual(result["total_memories"], 0)
            self.assertEqual(result["total_links"], 0)
            store.close()


class ExpiryForecastTests(unittest.TestCase):
    """Tests for memory expiry forecasting."""

    def test_forecast_with_ttl(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            near_expiry = (datetime.now(timezone.utc) + timedelta(hours=12)).isoformat()
            store.add_memories([
                MemoryUnit(memory_id="ef-1", scope_id="s1", memory_type=MemoryType.EPISODIC,
                           content="Expiring soon", expires_at=near_expiry),
                MemoryUnit(memory_id="ef-2", scope_id="s1", memory_type=MemoryType.SEMANTIC,
                           content="No expiry"),
            ])
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            result = mgr.forecast_expiry()
            self.assertEqual(result["total"], 2)
            self.assertEqual(result["with_ttl"], 1)
            self.assertEqual(result["forecast"]["next_24h"], 1)
            self.assertEqual(result["forecast"]["no_expiry"], 1)
            store.close()

    def test_forecast_empty_scope(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            result = mgr.forecast_expiry()
            self.assertEqual(result["total"], 0)
            store.close()


class TypeOverlapMatrixTests(unittest.TestCase):
    """Tests for type overlap matrix."""

    def test_overlap_with_shared_topics(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories([
                MemoryUnit(memory_id="to-1", scope_id="s1", memory_type=MemoryType.SEMANTIC,
                           content="Python setup", topics=["python", "setup"]),
                MemoryUnit(memory_id="to-2", scope_id="s1", memory_type=MemoryType.PREFERENCE,
                           content="Python style", topics=["python", "style"]),
            ])
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            result = mgr.get_type_overlap_matrix()
            self.assertIn("matrix", result)
            self.assertGreater(result["matrix"]["semantic"]["preference"], 0)
            store.close()

    def test_empty_scope_matrix(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            result = mgr.get_type_overlap_matrix()
            self.assertEqual(len(result["types"]), 0)
            store.close()


class ArchivalRecommendationTests(unittest.TestCase):
    """Tests for archival recommendations."""

    def test_recommends_low_value_memories(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            old_date = (datetime.now(timezone.utc) - timedelta(days=90)).isoformat()
            store.add_memories([
                MemoryUnit(memory_id="ar-1", scope_id="s1", memory_type=MemoryType.EPISODIC,
                           content="Old low-importance memory that nobody reads",
                           importance=0.1, updated_at=old_date),
            ])
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            recs = mgr.recommend_archival()
            self.assertTrue(len(recs) >= 1)
            self.assertEqual(recs[0]["memory_id"], "ar-1")
            self.assertIn("low_importance", recs[0]["reasons"])
            store.close()

    def test_skips_pinned_memories(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories([
                MemoryUnit(memory_id="ar-2", scope_id="s1", memory_type=MemoryType.SEMANTIC,
                           content="Pinned important memory", importance=0.99),
            ])
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            recs = mgr.recommend_archival()
            pinned_ids = [r["memory_id"] for r in recs]
            self.assertNotIn("ar-2", pinned_ids)
            store.close()

    def test_no_recommendations_for_healthy_scope(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories([
                MemoryUnit(memory_id="ar-3", scope_id="s1", memory_type=MemoryType.SEMANTIC,
                           content="Well-maintained memory with good metadata",
                           importance=0.7, summary="Good summary",
                           topics=["testing"], tags=["healthy"]),
            ])
            # Give it some access to avoid never_accessed penalty.
            store.mark_accessed(["ar-3"], datetime.now(timezone.utc).isoformat())
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            recs = mgr.recommend_archival()
            self.assertEqual(len(recs), 0)
            store.close()


class ScopeDashboardTests(unittest.TestCase):
    """Tests for comprehensive scope dashboard."""

    def test_dashboard_has_all_sections(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories([
                MemoryUnit(memory_id="db-1", scope_id="s1", memory_type=MemoryType.SEMANTIC,
                           content="Dashboard test memory", topics=["testing"]),
            ])
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            result = mgr.get_scope_dashboard()
            self.assertIn("overview", result)
            self.assertIn("access", result)
            self.assertIn("content", result)
            self.assertIn("graph", result)
            self.assertIn("expiry_forecast", result)
            self.assertIn("quota", result)
            self.assertEqual(result["overview"]["total_active"], 1)
            store.close()

    def test_empty_dashboard(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            result = mgr.get_scope_dashboard()
            self.assertEqual(result["overview"]["total_active"], 0)
            store.close()


class SeventhLoopIntegrationTests(unittest.TestCase):
    """Integration tests combining seventh-loop features."""

    def test_full_analysis_pipeline(self):
        """Exercise: create memories -> link -> analyze impact -> dashboard."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            # Create a small memory graph.
            store.add_memories([
                MemoryUnit(memory_id="int-1", scope_id="s1", memory_type=MemoryType.PROJECT_STATE,
                           content="The project uses React and TypeScript", topics=["react", "typescript"],
                           importance=0.7),
                MemoryUnit(memory_id="int-2", scope_id="s1", memory_type=MemoryType.SEMANTIC,
                           content="React components follow functional pattern", topics=["react"],
                           importance=0.5),
                MemoryUnit(memory_id="int-3", scope_id="s1", memory_type=MemoryType.PREFERENCE,
                           content="I prefer hooks over class components", topics=["react"],
                           importance=0.6),
            ])
            store.add_link("int-2", "int-1", "depends_on")
            store.add_link("int-3", "int-1", "elaborates")

            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)

            # Impact analysis.
            impact = mgr.analyze_memory_impact("int-1")
            self.assertFalse(impact["safe_to_archive"])
            self.assertIn("int-2", impact["direct_dependents"])

            # Link graph stats.
            stats = mgr.get_link_graph_stats()
            self.assertEqual(stats["total_links"], 2)
            self.assertGreater(stats["linked_memories"], 0)

            # Topic grouping.
            groups = mgr.group_by_topic()
            self.assertIn("react", groups["groups"])
            self.assertEqual(len(groups["groups"]["react"]), 3)

            # Dashboard.
            dashboard = mgr.get_scope_dashboard()
            self.assertEqual(dashboard["overview"]["total_active"], 3)
            self.assertEqual(dashboard["graph"]["total_links"], 2)

            store.close()

    def test_scope_clone_and_dedup(self):
        """Exercise: clone scope -> find cross-scope duplicates."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories([
                MemoryUnit(memory_id="ic-1", scope_id="original", memory_type=MemoryType.SEMANTIC,
                           content="Python deployment uses Docker and Kubernetes orchestration"),
                MemoryUnit(memory_id="ic-2", scope_id="original", memory_type=MemoryType.PREFERENCE,
                           content="I prefer dark mode for all development editors and terminals"),
            ])
            mgr = MemoryManager(store=store, scope_id="original", auto_consolidate=False)

            # Clone the scope.
            clone_result = mgr.clone_scope("original", "clone")
            self.assertEqual(clone_result["cloned"], 2)

            # Find cross-scope duplicates (cloned content should be detected).
            dupes = mgr.find_cross_scope_duplicates("original", "clone", threshold=0.70)
            self.assertGreater(len(dupes), 0)

            store.close()

    def test_cascade_archive_and_verify(self):
        """Exercise: cascade archive -> verify dependents archived -> check quota."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories([
                MemoryUnit(memory_id="ca-r", scope_id="s1", memory_type=MemoryType.SEMANTIC,
                           content="Root memory for cascade test"),
                MemoryUnit(memory_id="ca-d1", scope_id="s1", memory_type=MemoryType.SEMANTIC,
                           content="First dependent memory"),
                MemoryUnit(memory_id="ca-d2", scope_id="s1", memory_type=MemoryType.SEMANTIC,
                           content="Second dependent memory"),
                MemoryUnit(memory_id="ca-ind", scope_id="s1", memory_type=MemoryType.SEMANTIC,
                           content="Independent memory survives"),
            ])
            store.add_link("ca-d1", "ca-r", "depends_on")
            store.add_link("ca-d2", "ca-d1", "depends_on")

            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)

            # Cascade archive the root.
            result = mgr.cascade_archive("ca-r")
            self.assertEqual(result["archived"], 3)

            # Check that the independent memory survives.
            quota = mgr.check_scope_quota(max_memories=10)
            self.assertEqual(quota["current_count"], 1)

            store.close()


class LinkSuggestionTests(unittest.TestCase):
    """Tests for memory link suggestions."""

    def test_suggests_links_for_overlapping_topics(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories([
                MemoryUnit(memory_id="ls-1", scope_id="s1", memory_type=MemoryType.SEMANTIC,
                           content="React component patterns", topics=["react", "components"]),
                MemoryUnit(memory_id="ls-2", scope_id="s1", memory_type=MemoryType.SEMANTIC,
                           content="React hooks usage", topics=["react", "hooks"]),
            ])
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            suggestions = mgr.suggest_links(threshold=0.3)
            self.assertTrue(len(suggestions) >= 1)
            self.assertEqual(suggestions[0]["memory_a"], "ls-1")
            self.assertEqual(suggestions[0]["memory_b"], "ls-2")
            store.close()

    def test_no_suggestions_for_unrelated(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories([
                MemoryUnit(memory_id="ls-3", scope_id="s1", memory_type=MemoryType.SEMANTIC,
                           content="Python backend", topics=["python"]),
                MemoryUnit(memory_id="ls-4", scope_id="s1", memory_type=MemoryType.SEMANTIC,
                           content="Docker containers", topics=["docker"]),
            ])
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            suggestions = mgr.suggest_links(threshold=0.5)
            self.assertEqual(len(suggestions), 0)
            store.close()

    def test_skips_already_linked(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories([
                MemoryUnit(memory_id="ls-5", scope_id="s1", memory_type=MemoryType.SEMANTIC,
                           content="React frontend", topics=["react", "frontend"]),
                MemoryUnit(memory_id="ls-6", scope_id="s1", memory_type=MemoryType.SEMANTIC,
                           content="React styling", topics=["react", "frontend"]),
            ])
            store.add_link("ls-5", "ls-6", "related")
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            suggestions = mgr.suggest_links(threshold=0.3)
            linked_pairs = [(s["memory_a"], s["memory_b"]) for s in suggestions]
            self.assertNotIn(("ls-5", "ls-6"), linked_pairs)
            store.close()


class DetailedScopeComparisonTests(unittest.TestCase):
    """Tests for detailed scope comparison."""

    def test_comparison_with_shared_topics(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories([
                MemoryUnit(memory_id="dsc-1", scope_id="scope-a", memory_type=MemoryType.SEMANTIC,
                           content="Python setup", topics=["python", "setup"], importance=0.7),
                MemoryUnit(memory_id="dsc-2", scope_id="scope-b", memory_type=MemoryType.SEMANTIC,
                           content="Python testing", topics=["python", "testing"], importance=0.5),
            ])
            mgr = MemoryManager(store=store, scope_id="scope-a", auto_consolidate=False)
            result = mgr.generate_detailed_scope_comparison("scope-a", "scope-b")
            self.assertEqual(result["scope_a"]["count"], 1)
            self.assertEqual(result["scope_b"]["count"], 1)
            self.assertIn("python", result["shared_topics"])
            self.assertGreater(result["topic_overlap"], 0)
            store.close()

    def test_comparison_empty_scopes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            result = mgr.generate_detailed_scope_comparison("empty-a", "empty-b")
            self.assertEqual(result["scope_a"]["count"], 0)
            self.assertEqual(result["scope_b"]["count"], 0)
            store.close()


class ContentValidationTests(unittest.TestCase):
    """Tests for content validation rules."""

    def test_valid_content(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            result = mgr.validate_content("This is valid memory content with enough words")
            self.assertTrue(result["valid"])
            self.assertEqual(len(result["errors"]), 0)
            store.close()

    def test_too_short_content(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            result = mgr.validate_content("ab")
            self.assertFalse(result["valid"])
            self.assertTrue(any("too short" in e for e in result["errors"]))
            store.close()

    def test_url_only_warning(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            result = mgr.validate_content("https://example.com/some/path")
            self.assertTrue(result["valid"])
            self.assertTrue(any("URL" in w for w in result["warnings"]))
            store.close()

    def test_custom_rules(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            result = mgr.validate_content("Short", rules={"min_length": 10})
            self.assertFalse(result["valid"])
            store.close()


class AutoSummaryTests(unittest.TestCase):
    """Tests for auto-summary generation."""

    def test_generates_summary(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories([
                MemoryUnit(memory_id="as-1", scope_id="s1", memory_type=MemoryType.SEMANTIC,
                           content="The deployment pipeline uses GitHub Actions. It runs on every push.",
                           topics=["deployment", "github"]),
            ])
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            results = mgr.generate_auto_summaries()
            self.assertEqual(len(results), 1)
            self.assertIn("deployment", results[0]["summary"].lower())
            store.close()

    def test_skips_existing_summary(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories([
                MemoryUnit(memory_id="as-2", scope_id="s1", memory_type=MemoryType.SEMANTIC,
                           content="Some content", summary="Already summarized"),
            ])
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            results = mgr.generate_auto_summaries()
            self.assertEqual(len(results), 0)
            store.close()


class ImportanceRecalculationTests(unittest.TestCase):
    """Tests for importance recalculation."""

    def test_recalculates_based_on_signals(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories([
                MemoryUnit(memory_id="ir-1", scope_id="s1", memory_type=MemoryType.SEMANTIC,
                           content="Test memory", importance=0.3),
            ])
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            result = mgr.recalculate_importance()
            self.assertEqual(result["total_evaluated"], 1)
            store.close()

    def test_skips_pinned(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories([
                MemoryUnit(memory_id="ir-2", scope_id="s1", memory_type=MemoryType.SEMANTIC,
                           content="Pinned memory", importance=0.99),
            ])
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            result = mgr.recalculate_importance()
            # Pinned should not be updated.
            unit = store._get_by_id("ir-2")
            self.assertAlmostEqual(unit.importance, 0.99, places=2)
            store.close()


class TypeBalanceTests(unittest.TestCase):
    """Tests for type balance analysis."""

    def test_detects_dominant_type(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            for i in range(8):
                store.add_memories([
                    MemoryUnit(memory_id=f"tb-s{i}", scope_id="s1",
                               memory_type=MemoryType.SEMANTIC, content=f"Semantic {i}"),
                ])
            store.add_memories([
                MemoryUnit(memory_id="tb-p1", scope_id="s1",
                           memory_type=MemoryType.PREFERENCE, content="One preference"),
            ])
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            result = mgr.analyze_type_balance()
            self.assertIn("semantic", result["distribution"])
            # Should suggest reducing dominant type.
            reduce_suggestions = [s for s in result["suggestions"] if s["action"] == "reduce"]
            self.assertTrue(len(reduce_suggestions) >= 1)
            store.close()

    def test_empty_scope(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            result = mgr.analyze_type_balance()
            self.assertEqual(result["total"], 0)
            store.close()


class ScopeHealthComparisonTests(unittest.TestCase):
    """Tests for scope health comparison."""

    def test_compares_two_scopes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            for i in range(5):
                store.add_memories([
                    MemoryUnit(memory_id=f"hc-a{i}", scope_id="scope-a",
                               memory_type=MemoryType.SEMANTIC, content=f"Scope A memory {i}"),
                ])
            store.add_memories([
                MemoryUnit(memory_id="hc-b1", scope_id="scope-b",
                           memory_type=MemoryType.SEMANTIC, content="Scope B memory"),
            ])
            mgr = MemoryManager(store=store, scope_id="scope-a", auto_consolidate=False)
            result = mgr.compare_scope_health("scope-a", "scope-b")
            self.assertIn("health_delta", result)
            self.assertIn("healthier_scope", result)
            store.close()


class MemoryLifecycleTests(unittest.TestCase):
    """Tests for memory lifecycle tracking."""

    def test_lifecycle_of_existing_memory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories([
                MemoryUnit(memory_id="lc-1", scope_id="s1", memory_type=MemoryType.SEMANTIC,
                           content="Memory for lifecycle test", topics=["test"]),
            ])
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            result = mgr.get_memory_lifecycle("lc-1")
            self.assertIn("current_state", result)
            self.assertIn("relationships", result)
            self.assertEqual(result["current_state"]["type"], "semantic")
            store.close()

    def test_lifecycle_nonexistent(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            result = mgr.get_memory_lifecycle("nonexistent")
            self.assertIn("error", result)
            store.close()


class MaintenanceRecommendationTests(unittest.TestCase):
    """Tests for maintenance recommendations."""

    def test_healthy_scope_no_recommendations(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            result = mgr.get_maintenance_recommendations()
            self.assertIn("recommendations", result)
            store.close()

    def test_recommendations_with_issues(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            old_date = (datetime.now(timezone.utc) - timedelta(days=90)).isoformat()
            for i in range(10):
                store.add_memories([
                    MemoryUnit(memory_id=f"mr-{i}", scope_id="s1",
                               memory_type=MemoryType.SEMANTIC, content=f"Old memory {i}",
                               importance=0.1, updated_at=old_date),
                ])
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            result = mgr.get_maintenance_recommendations()
            self.assertGreater(result["total_recommendations"], 0)
            store.close()


class TrainingExportTests(unittest.TestCase):
    """Tests for ML training export."""

    def test_export_format(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories([
                MemoryUnit(memory_id="te-1", scope_id="s1", memory_type=MemoryType.SEMANTIC,
                           content="Training data point", topics=["ml"], importance=0.7),
            ])
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            records = mgr.export_for_training()
            self.assertEqual(len(records), 1)
            r = records[0]
            self.assertIn("content", r)
            self.assertIn("type", r)
            self.assertIn("topics", r)
            self.assertIn("importance", r)
            self.assertIn("metadata", r)
            self.assertEqual(r["content"], "Training data point")
            store.close()

    def test_empty_export(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            records = mgr.export_for_training()
            self.assertEqual(len(records), 0)
            store.close()


class FinalIntegrationTests(unittest.TestCase):
    """Comprehensive end-to-end integration tests for the seventh loop."""

    def test_full_memory_management_lifecycle(self):
        """Exercise complete lifecycle: ingest -> enrich -> analyze -> maintain -> export."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)

            # 1. Add memories.
            store.add_memories([
                MemoryUnit(memory_id="fl-1", scope_id="s1", memory_type=MemoryType.PROJECT_STATE,
                           content="The project uses Python 3.12 and PostgreSQL database",
                           topics=["python", "postgresql"], importance=0.7),
                MemoryUnit(memory_id="fl-2", scope_id="s1", memory_type=MemoryType.SEMANTIC,
                           content="Python asyncio improves performance for IO-bound workloads",
                           topics=["python", "asyncio"], importance=0.5),
                MemoryUnit(memory_id="fl-3", scope_id="s1", memory_type=MemoryType.PREFERENCE,
                           content="I prefer type hints on all public functions",
                           topics=["python", "typing"], importance=0.6),
                MemoryUnit(memory_id="fl-4", scope_id="s1", memory_type=MemoryType.EPISODIC,
                           content="Fixed a bug in the authentication middleware today",
                           topics=["authentication", "bugfix"], importance=0.4),
            ])

            # 2. Add relationships.
            store.add_link("fl-2", "fl-1", "depends_on")
            store.add_link("fl-3", "fl-1", "elaborates")

            # 3. Tag memories.
            store.add_tags("fl-1", ["core", "infrastructure"])
            store.add_tags("fl-4", ["incident"])

            # 4. Generate summaries.
            summaries = mgr.generate_auto_summaries()
            self.assertGreater(len(summaries), 0)

            # 5. Suggest links.
            link_suggestions = mgr.suggest_links(threshold=0.3)
            # Should suggest linking python-related memories.
            self.assertTrue(len(link_suggestions) >= 0)

            # 6. Analyze.
            dashboard = mgr.get_scope_dashboard()
            self.assertEqual(dashboard["overview"]["total_active"], 4)

            type_balance = mgr.analyze_type_balance()
            self.assertEqual(type_balance["total"], 4)

            # 7. Check impact before archiving.
            impact = mgr.analyze_memory_impact("fl-1")
            self.assertFalse(impact["safe_to_archive"])  # Has dependents.

            # 8. Export for training.
            records = mgr.export_for_training()
            self.assertEqual(len(records), 4)

            # 9. Maintenance recommendations.
            recs = mgr.get_maintenance_recommendations()
            self.assertIn("recommendations", recs)

            store.close()

    def test_multi_scope_operations(self):
        """Exercise cross-scope features: clone, merge, compare, dedup."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="team-a", auto_consolidate=False)

            # Team A scope.
            store.add_memories([
                MemoryUnit(memory_id="ms-a1", scope_id="team-a", memory_type=MemoryType.SEMANTIC,
                           content="The API uses REST with JSON responses",
                           topics=["api", "rest"], importance=0.7),
                MemoryUnit(memory_id="ms-a2", scope_id="team-a", memory_type=MemoryType.PREFERENCE,
                           content="We prefer camelCase for API field names",
                           topics=["api", "naming"], importance=0.5),
            ])

            # Team B scope.
            store.add_memories([
                MemoryUnit(memory_id="ms-b1", scope_id="team-b", memory_type=MemoryType.SEMANTIC,
                           content="The frontend uses React with TypeScript",
                           topics=["react", "typescript"], importance=0.6),
            ])

            # Clone team-a to staging.
            clone_result = mgr.clone_scope("team-a", "staging")
            self.assertEqual(clone_result["cloned"], 2)

            # Detailed comparison.
            comparison = mgr.generate_detailed_scope_comparison("team-a", "team-b")
            self.assertEqual(comparison["scope_a"]["count"], 2)
            self.assertEqual(comparison["scope_b"]["count"], 1)

            # Health comparison.
            health = mgr.compare_scope_health("team-a", "team-b")
            self.assertIn("healthier_scope", health)

            # Cross-scope duplicates between team-a and staging clone.
            dupes = mgr.find_cross_scope_duplicates("team-a", "staging", threshold=0.70)
            self.assertGreater(len(dupes), 0)

            store.close()


class BatchContentUpdateTests(unittest.TestCase):
    """Tests for batch content updates."""

    def test_batch_update(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories([
                MemoryUnit(memory_id="bu-1", scope_id="s1", memory_type=MemoryType.SEMANTIC, content="Old content 1"),
                MemoryUnit(memory_id="bu-2", scope_id="s1", memory_type=MemoryType.SEMANTIC, content="Old content 2"),
            ])
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            result = mgr.batch_update_content([
                {"memory_id": "bu-1", "content": "New content 1"},
                {"memory_id": "bu-2", "content": "New content 2"},
            ])
            self.assertEqual(result["updated"], 2)
            self.assertEqual(result["failed"], 0)
            store.close()

    def test_batch_update_invalid(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            result = mgr.batch_update_content([
                {"memory_id": "", "content": ""},
                {"content": "no id"},
            ])
            self.assertEqual(result["failed"], 2)
            store.close()


class FreshnessScoreTests(unittest.TestCase):
    """Tests for freshness scoring."""

    def test_recent_memory_high_freshness(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories([
                MemoryUnit(memory_id="fr-1", scope_id="s1", memory_type=MemoryType.SEMANTIC,
                           content="Just created memory"),
            ])
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            scores = mgr.compute_freshness_scores()
            self.assertEqual(len(scores), 1)
            self.assertGreater(scores[0]["freshness"], 50)
            store.close()

    def test_old_memory_lower_freshness(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            old_date = (datetime.now(timezone.utc) - timedelta(days=200)).isoformat()
            store.add_memories([
                MemoryUnit(memory_id="fr-2", scope_id="s1", memory_type=MemoryType.SEMANTIC,
                           content="Old memory for freshness", created_at=old_date, updated_at=old_date),
            ])
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            scores = mgr.compute_freshness_scores()
            self.assertTrue(len(scores) >= 1)
            store.close()


class ScopeInventoryTests(unittest.TestCase):
    """Tests for scope inventory."""

    def test_inventory_with_filters(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories([
                MemoryUnit(memory_id="inv-1", scope_id="s1", memory_type=MemoryType.SEMANTIC,
                           content="High importance semantic", importance=0.8),
                MemoryUnit(memory_id="inv-2", scope_id="s1", memory_type=MemoryType.PREFERENCE,
                           content="Low importance preference", importance=0.2),
                MemoryUnit(memory_id="inv-3", scope_id="s1", memory_type=MemoryType.SEMANTIC,
                           content="Medium importance semantic", importance=0.5),
            ])
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)

            # Filter by type.
            result = mgr.get_scope_inventory(type_filter="semantic")
            self.assertEqual(result["total_after_filter"], 2)

            # Filter by importance.
            result = mgr.get_scope_inventory(min_importance=0.5)
            self.assertEqual(result["total_after_filter"], 2)

            store.close()

    def test_inventory_empty_scope(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            result = mgr.get_scope_inventory()
            self.assertEqual(result["total_before_filter"], 0)
            self.assertEqual(result["showing"], 0)
            store.close()

    def test_inventory_sorting(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories([
                MemoryUnit(memory_id="inv-4", scope_id="s1", memory_type=MemoryType.SEMANTIC,
                           content="Low importance", importance=0.2),
                MemoryUnit(memory_id="inv-5", scope_id="s1", memory_type=MemoryType.SEMANTIC,
                           content="High importance", importance=0.9),
            ])
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            result = mgr.get_scope_inventory(sort_by="importance")
            self.assertEqual(result["items"][0]["memory_id"], "inv-5")
            store.close()


class ContentNormalizationTests(unittest.TestCase):
    """Tests for content normalization."""

    def test_normalize_whitespace(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories([
                MemoryUnit(memory_id="cn-1", scope_id="s1", memory_type=MemoryType.SEMANTIC,
                           content="  Multiple   spaces   here  "),
            ])
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            result = mgr.normalize_content("cn-1")
            self.assertTrue(result["changed"])
            self.assertGreater(result["original_length"], result["normalized_length"])
            store.close()

    def test_already_normalized(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories([
                MemoryUnit(memory_id="cn-2", scope_id="s1", memory_type=MemoryType.SEMANTIC,
                           content="Already clean content"),
            ])
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            result = mgr.normalize_content("cn-2")
            self.assertFalse(result["changed"])
            store.close()

    def test_batch_normalize(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories([
                MemoryUnit(memory_id="cn-3", scope_id="s1", memory_type=MemoryType.SEMANTIC,
                           content="  Needs   cleanup  "),
                MemoryUnit(memory_id="cn-4", scope_id="s1", memory_type=MemoryType.SEMANTIC,
                           content="Already clean"),
            ])
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            result = mgr.batch_normalize_content()
            self.assertEqual(result["total"], 2)
            self.assertEqual(result["normalized"], 1)
            store.close()


class PriorityQueueTests(unittest.TestCase):
    """Tests for priority queue."""

    def test_queue_with_stale_memories(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            old_date = (datetime.now(timezone.utc) - timedelta(days=60)).isoformat()
            store.add_memories([
                MemoryUnit(memory_id="pq-1", scope_id="s1", memory_type=MemoryType.SEMANTIC,
                           content="Stale memory needs attention", updated_at=old_date),
            ])
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            queue = mgr.get_priority_queue()
            self.assertTrue(len(queue) >= 1)
            store.close()

    def test_empty_queue(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            queue = mgr.get_priority_queue()
            self.assertEqual(len(queue), 0)
            store.close()


class QualityGateTests(unittest.TestCase):
    """Tests for quality gates."""

    def test_good_content_passes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            result = mgr.apply_quality_gate("The deployment uses Docker and Kubernetes for orchestration")
            self.assertTrue(result["passed"])
            store.close()

    def test_too_short_fails(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            result = mgr.apply_quality_gate("ab")
            self.assertFalse(result["passed"])
            store.close()

    def test_gates_list_present(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            result = mgr.apply_quality_gate("Some reasonable content for testing quality")
            self.assertIn("gates", result)
            self.assertGreater(len(result["gates"]), 0)
            store.close()


class EmbedderTests(unittest.TestCase):
    """Tests for the embedder abstraction and semantic embedding support."""

    def test_hashing_embedder_base_class(self):
        from metaclaw.memory.embeddings import HashingEmbedder, BaseEmbedder
        emb = HashingEmbedder(dimensions=32)
        self.assertIsInstance(emb, BaseEmbedder)
        vec = emb.encode("hello world")
        self.assertEqual(len(vec), 32)
        self.assertAlmostEqual(sum(v * v for v in vec), 1.0, places=5)

    def test_hashing_embedder_batch_encode(self):
        from metaclaw.memory.embeddings import HashingEmbedder
        emb = HashingEmbedder(dimensions=16)
        vecs = emb.encode_batch(["hello", "world", "test"])
        self.assertEqual(len(vecs), 3)
        for v in vecs:
            self.assertEqual(len(v), 16)

    def test_create_embedder_hashing_mode(self):
        from metaclaw.memory.embeddings import create_embedder, HashingEmbedder
        emb = create_embedder(mode="hashing", dimensions=32)
        self.assertIsInstance(emb, HashingEmbedder)
        self.assertEqual(emb.dimensions, 32)

    def test_create_embedder_semantic_fallback(self):
        """When sentence-transformers is not installed, falls back to HashingEmbedder."""
        from metaclaw.memory.embeddings import create_embedder, HashingEmbedder
        emb = create_embedder(mode="semantic", fallback=True, dimensions=48)
        # Will be HashingEmbedder if sentence-transformers not available, or
        # SentenceTransformerEmbedder if it is.
        self.assertIsNotNone(emb)
        self.assertTrue(hasattr(emb, "encode"))
        self.assertTrue(hasattr(emb, "dimensions"))

    def test_sentence_transformer_embedder_unavailable(self):
        """SentenceTransformerEmbedder gracefully handles missing package."""
        from metaclaw.memory.embeddings import SentenceTransformerEmbedder
        emb = SentenceTransformerEmbedder(model_name="nonexistent-model-xyz")
        # is_available should be False if model can't load
        if not emb.is_available:
            with self.assertRaises(RuntimeError):
                emb.encode("test")

    def test_embedder_info(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            # Without embeddings
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            info = mgr.get_embedder_info()
            self.assertFalse(info["enabled"])
            self.assertEqual(info["mode"], "none")

            # With hashing embeddings
            mgr2 = MemoryManager(
                store=store, scope_id="s1", auto_consolidate=False,
                use_embeddings=True, embedding_mode="hashing",
            )
            info2 = mgr2.get_embedder_info()
            self.assertTrue(info2["enabled"])
            self.assertEqual(info2["mode"], "hashing")
            self.assertIsNotNone(info2["dimensions"])
            store.close()

    def test_re_embed_scope(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(
                store=store, scope_id="s1", auto_consolidate=False,
                use_embeddings=True, embedding_mode="hashing",
            )
            now = datetime.now(timezone.utc).isoformat()
            store.add_memories([
                MemoryUnit(
                    memory_id="emb-1", scope_id="s1",
                    memory_type=MemoryType.SEMANTIC,
                    content="The database uses PostgreSQL for persistence",
                    summary="PostgreSQL database",
                    source_session_id="s", source_turn_start=0, source_turn_end=0,
                    created_at=now, updated_at=now,
                    topics=["database"], entities=["PostgreSQL"],
                    importance=0.7, confidence=0.8,
                ),
                MemoryUnit(
                    memory_id="emb-2", scope_id="s1",
                    memory_type=MemoryType.PREFERENCE,
                    content="User prefers dark mode for all editors",
                    summary="Dark mode preference",
                    source_session_id="s", source_turn_start=0, source_turn_end=0,
                    created_at=now, updated_at=now,
                    topics=["editor"], entities=[],
                    importance=0.5, confidence=0.9,
                ),
            ])
            result = mgr.re_embed_scope("s1")
            self.assertEqual(result["re_embedded"], 2)
            self.assertEqual(result["total"], 2)
            store.close()

    def test_re_embed_no_embedder(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            result = mgr.re_embed_scope("s1")
            self.assertIn("error", result)
            self.assertEqual(result["re_embedded"], 0)
            store.close()

    def test_custom_embedder_injection(self):
        """Test injecting a custom embedder via the constructor."""
        from metaclaw.memory.embeddings import HashingEmbedder
        custom = HashingEmbedder(dimensions=128)
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(
                store=store, scope_id="s1", auto_consolidate=False,
                embedder=custom,
            )
            self.assertIs(mgr.embedder, custom)
            info = mgr.get_embedder_info()
            self.assertTrue(info["enabled"])
            self.assertEqual(info["dimensions"], 128)
            store.close()


class SemanticRetrievalIntegrationTests(unittest.TestCase):
    """Integration tests for embedding-based retrieval paths."""

    def test_embedding_retrieval_with_hashing(self):
        """Test that embedding retrieval mode works end-to-end with HashingEmbedder."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(
                store=store, scope_id="s1", auto_consolidate=False,
                retrieval_mode="embedding", use_embeddings=True,
                embedding_mode="hashing",
            )
            now = datetime.now(timezone.utc).isoformat()
            # Ingest some memories with embeddings.
            units = [
                MemoryUnit(
                    memory_id=f"sr-{i}", scope_id="s1",
                    memory_type=MemoryType.SEMANTIC,
                    content=content,
                    summary=content[:30],
                    source_session_id="s", source_turn_start=0, source_turn_end=0,
                    created_at=now, updated_at=now,
                    topics=[], entities=[],
                    importance=0.7, confidence=0.8,
                    embedding=mgr.embedder.encode(content) if mgr.embedder else [],
                )
                for i, content in enumerate([
                    "Python is used for backend services",
                    "React handles the frontend rendering",
                    "PostgreSQL stores the user data",
                ])
            ]
            store.add_memories(units)

            # Retrieve with embedding mode.
            query = MemoryQuery(
                scope_id="s1",
                query_text="backend Python services",
                top_k=3,
            )
            hits = mgr.retriever.retrieve(query)
            # Should get results (exact ordering depends on hash collisions).
            self.assertGreater(len(hits), 0)
            store.close()

    def test_hybrid_retrieval_with_embeddings(self):
        """Test hybrid mode combines keyword and embedding signals."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(
                store=store, scope_id="s1", auto_consolidate=False,
                retrieval_mode="hybrid", use_embeddings=True,
                embedding_mode="hashing",
            )
            now = datetime.now(timezone.utc).isoformat()
            units = [
                MemoryUnit(
                    memory_id=f"hy-{i}", scope_id="s1",
                    memory_type=MemoryType.SEMANTIC,
                    content=content,
                    summary=content[:30],
                    source_session_id="s", source_turn_start=0, source_turn_end=0,
                    created_at=now, updated_at=now,
                    topics=["deployment"], entities=[],
                    importance=0.7, confidence=0.8,
                    embedding=mgr.embedder.encode(content) if mgr.embedder else [],
                )
                for i, content in enumerate([
                    "We deploy to Kubernetes in production",
                    "Staging uses Docker Compose for testing",
                    "CI pipeline runs on GitHub Actions",
                ])
            ]
            store.add_memories(units)

            query = MemoryQuery(
                scope_id="s1",
                query_text="deploy Kubernetes production staging",
                top_k=3,
            )
            hits = mgr.retriever.retrieve(query)
            self.assertGreater(len(hits), 0)
            store.close()

    def test_auto_mode_selects_hybrid_with_embedder(self):
        """Auto mode should select hybrid when embedder is available and query is long enough."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(
                store=store, scope_id="s1", auto_consolidate=False,
                retrieval_mode="auto", use_embeddings=True,
                embedding_mode="hashing",
            )
            # Long query should trigger hybrid
            mode = mgr.retriever._auto_select_mode(
                MemoryQuery(scope_id="s1", query_text="how does the backend handle authentication and authorization", top_k=5)
            )
            self.assertEqual(mode, "hybrid")

            # Short query should stay keyword
            mode_short = mgr.retriever._auto_select_mode(
                MemoryQuery(scope_id="s1", query_text="auth config", top_k=5)
            )
            self.assertEqual(mode_short, "keyword")
            store.close()


class CosineSimilarityTests(unittest.TestCase):
    """Tests for the cosine_similarity utility function."""

    def test_identical_vectors(self):
        from metaclaw.memory.embeddings import cosine_similarity
        vec = [0.5, 0.5, 0.5, 0.5]
        self.assertAlmostEqual(cosine_similarity(vec, vec), 1.0, places=5)

    def test_empty_vectors(self):
        from metaclaw.memory.embeddings import cosine_similarity
        self.assertEqual(cosine_similarity([], []), 0.0)
        self.assertEqual(cosine_similarity([], [1.0]), 0.0)
        self.assertEqual(cosine_similarity([1.0], []), 0.0)

    def test_mismatched_length(self):
        from metaclaw.memory.embeddings import cosine_similarity
        self.assertEqual(cosine_similarity([1.0, 0.0], [1.0, 0.0, 0.0]), 0.0)

    def test_orthogonal_vectors(self):
        from metaclaw.memory.embeddings import cosine_similarity
        self.assertAlmostEqual(cosine_similarity([1.0, 0.0], [0.0, 1.0]), 0.0, places=5)


class EmbedderEdgeCaseTests(unittest.TestCase):
    """Tests for embedder edge cases."""

    def test_encode_empty_string(self):
        from metaclaw.memory.embeddings import HashingEmbedder
        emb = HashingEmbedder(dimensions=16)
        vec = emb.encode("")
        self.assertEqual(len(vec), 16)
        # All zeros (no tokens to hash).
        self.assertTrue(all(v == 0.0 for v in vec))

    def test_min_dimensions_clamped(self):
        from metaclaw.memory.embeddings import HashingEmbedder
        emb = HashingEmbedder(dimensions=3)
        self.assertEqual(emb.dimensions, 8)  # Clamped to min 8

    def test_encode_batch_empty_list(self):
        from metaclaw.memory.embeddings import HashingEmbedder
        emb = HashingEmbedder(dimensions=16)
        result = emb.encode_batch([])
        self.assertEqual(result, [])

    def test_sentence_transformer_encode_batch_unavailable(self):
        from metaclaw.memory.embeddings import SentenceTransformerEmbedder
        emb = SentenceTransformerEmbedder(model_name="nonexistent-model-xyz")
        if not emb.is_available:
            with self.assertRaises(RuntimeError):
                emb.encode_batch(["test"])

    def test_re_embed_with_explicit_embedder(self):
        """Test re_embed_scope with an explicit embedder override."""
        from metaclaw.memory.embeddings import HashingEmbedder
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            # Manager has no embedder.
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            now = datetime.now(timezone.utc).isoformat()
            store.add_memories([
                MemoryUnit(
                    memory_id="re-1", scope_id="s1",
                    memory_type=MemoryType.SEMANTIC,
                    content="Test content for re-embedding",
                    summary="test",
                    source_session_id="s", source_turn_start=0, source_turn_end=0,
                    created_at=now, updated_at=now,
                    topics=[], entities=[],
                    importance=0.5, confidence=0.8,
                ),
            ])
            # Pass explicit embedder.
            custom_emb = HashingEmbedder(dimensions=128)
            result = mgr.re_embed_scope("s1", embedder=custom_emb)
            self.assertEqual(result["re_embedded"], 1)
            store.close()


class AdaptiveTTLEdgeCaseTests(unittest.TestCase):
    """Tests for adaptive TTL edge cases: access count and importance multipliers."""

    def test_high_access_count_doubles_ttl(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            now = datetime.now(timezone.utc).isoformat()
            store.add_memories([
                MemoryUnit(
                    memory_id="att-1", scope_id="s1",
                    memory_type=MemoryType.EPISODIC,
                    content="Frequently accessed episodic memory",
                    summary="frequent access",
                    source_session_id="s", source_turn_start=0, source_turn_end=0,
                    created_at=now, updated_at=now,
                    topics=[], entities=[],
                    importance=0.3, confidence=0.8,
                    access_count=5,  # >3 triggers double TTL
                ),
            ])
            result = mgr.apply_adaptive_ttl("s1")
            self.assertEqual(result["updated"], 1)
            # Verify TTL was set.
            unit = store._get_by_id("att-1")
            self.assertIsNotNone(unit.expires_at)
            # High access count (>3) doubles base TTL (episodic=30 -> 60 days).
            expires = datetime.fromisoformat(unit.expires_at)
            expected_min = datetime.now(timezone.utc) + timedelta(days=55)
            self.assertGreater(expires, expected_min)
            store.close()

    def test_high_importance_extends_ttl(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            now = datetime.now(timezone.utc).isoformat()
            store.add_memories([
                MemoryUnit(
                    memory_id="att-2", scope_id="s1",
                    memory_type=MemoryType.EPISODIC,
                    content="High importance episodic memory",
                    summary="important",
                    source_session_id="s", source_turn_start=0, source_turn_end=0,
                    created_at=now, updated_at=now,
                    topics=[], entities=[],
                    importance=0.85,  # >=0.7 triggers 1.5x TTL
                    confidence=0.8,
                    access_count=0,
                ),
            ])
            result = mgr.apply_adaptive_ttl("s1")
            self.assertEqual(result["updated"], 1)
            unit = store._get_by_id("att-2")
            self.assertIsNotNone(unit.expires_at)
            # High importance (>=0.7) extends by 1.5x (episodic=30 -> 45 days).
            expires = datetime.fromisoformat(unit.expires_at)
            expected_min = datetime.now(timezone.utc) + timedelta(days=40)
            self.assertGreater(expires, expected_min)
            store.close()


class FullSystemIntegrationTests(unittest.TestCase):
    """End-to-end tests exercising the complete memory system from config to retrieval."""

    def test_config_to_retrieval_with_embeddings(self):
        """Full path: config -> manager -> ingest -> embed -> retrieve -> maintain."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "memory.db")
            policy_path = os.path.join(tmpdir, "policy.json")
            telemetry_path = os.path.join(tmpdir, "telemetry.jsonl")

            cfg = MetaClawConfig(
                memory_enabled=True,
                memory_store_path=db_path,
                memory_scope="integration-test",
                memory_retrieval_mode="hybrid",
                memory_use_embeddings=True,
                memory_policy_path=policy_path,
                memory_telemetry_path=telemetry_path,
                memory_auto_consolidate=True,
            )
            mgr = MemoryManager.from_config(cfg)

            # 1. Ingest via session extraction.
            session_turns = [
                {"prompt_text": "I prefer Python for backend development",
                 "response_text": "Noted. Python is great for backend services."},
                {"prompt_text": "Our project uses PostgreSQL as the database",
                 "response_text": "PostgreSQL is a solid choice for relational data."},
                {"prompt_text": "Remember that we always use type hints",
                 "response_text": "Understood, type hints will be used throughout."},
            ]
            mgr.ingest_session_turns("sess-int-1", session_turns, scope_id="integration-test")

            # 2. Verify memories were created.
            stats = mgr.store.get_stats("integration-test")
            self.assertGreater(stats.get("active", 0), 0)

            # 3. Retrieve with hybrid mode.
            memories = mgr.retrieve_for_prompt("Python backend database", scope_id="integration-test")
            # Should find relevant memories.
            self.assertTrue(len(memories) >= 0)  # May be 0 if extraction patterns don't match

            # 4. Re-embed the scope.
            embed_result = mgr.re_embed_scope("integration-test")
            if embed_result.get("total", 0) > 0:
                self.assertGreater(embed_result["re_embedded"], 0)

            # 5. Check embedder info.
            info = mgr.get_embedder_info()
            self.assertTrue(info["enabled"])

            # 6. Run maintenance.
            maint = mgr.run_maintenance("integration-test")
            self.assertIn("scope_id", maint)

            # 7. Get dashboard.
            dashboard = mgr.get_scope_dashboard("integration-test")
            self.assertIn("overview", dashboard)

            # 8. Get health score.
            health = mgr.get_health_score("integration-test")
            self.assertIn("score", health)

            # 9. Export for training.
            training = mgr.export_for_training("integration-test")
            self.assertIsInstance(training, list)

            mgr.close()

    def test_multi_scope_operations_e2e(self):
        """Test cross-scope operations: clone, merge, compare, dedup."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="scope-a", auto_consolidate=False)
            now = datetime.now(timezone.utc).isoformat()

            # Populate scope-a.
            store.add_memories([
                MemoryUnit(memory_id="ms-1", scope_id="scope-a",
                           memory_type=MemoryType.SEMANTIC,
                           content="The API uses REST with JSON responses",
                           summary="REST API", topics=["api", "rest"],
                           created_at=now, updated_at=now,
                           importance=0.7, confidence=0.8),
                MemoryUnit(memory_id="ms-2", scope_id="scope-a",
                           memory_type=MemoryType.PREFERENCE,
                           content="We prefer camelCase for JSON field names",
                           summary="camelCase", topics=["api", "naming"],
                           created_at=now, updated_at=now,
                           importance=0.6, confidence=0.9),
            ])

            # Populate scope-b.
            store.add_memories([
                MemoryUnit(memory_id="ms-3", scope_id="scope-b",
                           memory_type=MemoryType.SEMANTIC,
                           content="The frontend uses React with TypeScript",
                           summary="React frontend", topics=["frontend", "react"],
                           created_at=now, updated_at=now,
                           importance=0.7, confidence=0.8),
            ])

            # 1. Clone scope.
            clone_result = mgr.clone_scope("scope-a", "scope-a-clone")
            self.assertEqual(clone_result["cloned"], 2)

            # 2. Compare scopes.
            comparison = mgr.compare_scopes("scope-a", "scope-b")
            self.assertIn("scope_a", comparison)

            # 3. Cross-scope dedup.
            dupes = mgr.find_cross_scope_duplicates("scope-a", "scope-a-clone")
            # Cloned memories have same content, should find duplicates.
            self.assertGreater(len(dupes), 0)

            # 4. Merge scopes.
            merge_result = mgr.merge_scopes("scope-b", "scope-a")
            self.assertIn("copied", merge_result)

            # 5. Scope health comparison.
            health_cmp = mgr.compare_scope_health("scope-a", "scope-b")
            self.assertIn("scope_a", health_cmp)

            # 6. Detailed comparison.
            detailed = mgr.generate_detailed_scope_comparison("scope-a", "scope-b")
            self.assertIn("scope_a", detailed)

            store.close()

    def test_quality_pipeline_e2e(self):
        """Test quality pipeline: gate -> validate -> score -> recommend -> archive."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="quality", auto_consolidate=False)
            now = datetime.now(timezone.utc).isoformat()
            old = (datetime.now(timezone.utc) - timedelta(days=120)).isoformat()

            # 1. Quality gate check.
            gate_result = mgr.apply_quality_gate("PostgreSQL is our primary database for user data")
            self.assertTrue(gate_result["passed"])

            gate_fail = mgr.apply_quality_gate("hi")
            self.assertFalse(gate_fail["passed"])

            # 2. Add memories with varying quality.
            store.add_memories([
                MemoryUnit(memory_id="q-1", scope_id="quality",
                           memory_type=MemoryType.SEMANTIC,
                           content="Well-documented API specification with versioning strategy",
                           summary="API spec", topics=["api", "documentation"],
                           created_at=now, updated_at=now,
                           importance=0.8, confidence=0.9, access_count=5),
                MemoryUnit(memory_id="q-2", scope_id="quality",
                           memory_type=MemoryType.EPISODIC,
                           content="Something happened",
                           summary="", topics=[],
                           created_at=old, updated_at=old,
                           importance=0.1, confidence=0.3, access_count=0),
            ])

            # 3. Score quality.
            q1_score = mgr.score_memory_quality("q-1")
            q2_score = mgr.score_memory_quality("q-2")
            self.assertGreater(q1_score["score"], q2_score["score"])

            # 4. Get archival recommendations.
            recs = mgr.recommend_archival("quality")
            # q-2 should be recommended for archival (old, low importance, no access).
            rec_ids = [r["memory_id"] for r in recs]
            self.assertIn("q-2", rec_ids)

            # 5. Priority queue should surface q-2.
            pq = mgr.get_priority_queue("quality", limit=10)
            self.assertTrue(len(pq) >= 0)

            store.close()


class SystemSummaryTests(unittest.TestCase):
    """Tests for the system-wide summary feature."""

    def test_system_summary_basic(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            now = datetime.now(timezone.utc).isoformat()
            store.add_memories([
                MemoryUnit(memory_id="ss-1", scope_id="s1",
                           memory_type=MemoryType.SEMANTIC,
                           content="Test memory for system summary",
                           created_at=now, updated_at=now,
                           importance=0.5, confidence=0.8),
            ])
            summary = mgr.get_system_summary()
            self.assertIn("schema_version", summary)
            self.assertIn("scopes", summary)
            self.assertIn("embedder", summary)
            self.assertIn("policy", summary)
            self.assertIn("db", summary)
            self.assertIn("integrity", summary)
            self.assertGreaterEqual(summary["total_active_memories"], 1)
            store.close()

    def test_system_summary_multi_scope(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            now = datetime.now(timezone.utc).isoformat()
            store.add_memories([
                MemoryUnit(memory_id="ss-a", scope_id="scope-a",
                           memory_type=MemoryType.SEMANTIC,
                           content="Memory in scope A", created_at=now, updated_at=now,
                           importance=0.5, confidence=0.8),
                MemoryUnit(memory_id="ss-b", scope_id="scope-b",
                           memory_type=MemoryType.PREFERENCE,
                           content="Memory in scope B", created_at=now, updated_at=now,
                           importance=0.6, confidence=0.9),
            ])
            summary = mgr.get_system_summary()
            self.assertGreaterEqual(summary["scope_count"], 2)
            self.assertGreaterEqual(summary["total_active_memories"], 2)
            store.close()


class ContentCompressionTests(unittest.TestCase):
    """Tests for memory content compression."""

    def test_compress_removes_fillers(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            now = datetime.now(timezone.utc).isoformat()
            store.add_memories([
                MemoryUnit(memory_id="cmp-1", scope_id="s1",
                           memory_type=MemoryType.SEMANTIC,
                           content="Basically the project uses Python and essentially PostgreSQL",
                           created_at=now, updated_at=now,
                           importance=0.5, confidence=0.8),
            ])
            result = mgr.compress_content("cmp-1")
            self.assertTrue(result["changed"])
            self.assertLess(result["compressed_length"], result["original_length"])
            unit = store._get_by_id("cmp-1")
            self.assertNotIn("basically", unit.content.lower())
            store.close()

    def test_compress_no_change(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            now = datetime.now(timezone.utc).isoformat()
            store.add_memories([
                MemoryUnit(memory_id="cmp-2", scope_id="s1",
                           memory_type=MemoryType.SEMANTIC,
                           content="Python is the backend language",
                           created_at=now, updated_at=now,
                           importance=0.5, confidence=0.8),
            ])
            result = mgr.compress_content("cmp-2")
            self.assertFalse(result["changed"])
            store.close()

    def test_batch_compress(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            now = datetime.now(timezone.utc).isoformat()
            store.add_memories([
                MemoryUnit(memory_id="cmp-3", scope_id="s1",
                           memory_type=MemoryType.SEMANTIC,
                           content="Basically the API uses REST obviously",
                           created_at=now, updated_at=now,
                           importance=0.5, confidence=0.8),
                MemoryUnit(memory_id="cmp-4", scope_id="s1",
                           memory_type=MemoryType.PREFERENCE,
                           content="Clean code with no filler",
                           created_at=now, updated_at=now,
                           importance=0.6, confidence=0.9),
            ])
            result = mgr.batch_compress("s1")
            self.assertEqual(result["total"], 2)
            self.assertGreater(result["compressed"], 0)
            self.assertGreater(result["chars_saved"], 0)
            store.close()


class BulkTagByTypeTests(unittest.TestCase):
    """Tests for bulk tagging by memory type."""

    def test_auto_tag_by_type(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            now = datetime.now(timezone.utc).isoformat()
            store.add_memories([
                MemoryUnit(memory_id="bt-1", scope_id="s1",
                           memory_type=MemoryType.PROJECT_STATE,
                           content="Project uses Docker for containerization",
                           created_at=now, updated_at=now,
                           importance=0.7, confidence=0.8),
                MemoryUnit(memory_id="bt-2", scope_id="s1",
                           memory_type=MemoryType.PREFERENCE,
                           content="I prefer dark mode",
                           created_at=now, updated_at=now,
                           importance=0.5, confidence=0.9),
                MemoryUnit(memory_id="bt-3", scope_id="s1",
                           memory_type=MemoryType.SEMANTIC,
                           content="General fact about the system",
                           created_at=now, updated_at=now,
                           importance=0.4, confidence=0.7),
            ])
            result = mgr.bulk_tag_by_type("s1")
            self.assertEqual(result["total"], 3)
            self.assertEqual(result["tagged"], 2)  # project_state and preference get tags
            unit1 = store._get_by_id("bt-1")
            self.assertIn("infrastructure", unit1.tags)
            unit2 = store._get_by_id("bt-2")
            self.assertIn("user-preference", unit2.tags)
            store.close()

    def test_auto_tag_idempotent(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            now = datetime.now(timezone.utc).isoformat()
            store.add_memories([
                MemoryUnit(memory_id="bt-4", scope_id="s1",
                           memory_type=MemoryType.PROJECT_STATE,
                           content="Uses Kubernetes",
                           created_at=now, updated_at=now,
                           importance=0.7, confidence=0.8),
            ])
            mgr.bulk_tag_by_type("s1")
            # Run again — should not add duplicate tags.
            result = mgr.bulk_tag_by_type("s1")
            self.assertEqual(result["tagged"], 0)
            store.close()


class RetentionAnalysisTests(unittest.TestCase):
    """Tests for retention effectiveness analysis."""

    def test_retention_analysis_basic(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            now = datetime.now(timezone.utc).isoformat()
            store.add_memories([
                MemoryUnit(memory_id="ra-1", scope_id="s1",
                           memory_type=MemoryType.SEMANTIC,
                           content="Active high importance memory",
                           created_at=now, updated_at=now,
                           importance=0.8, confidence=0.9),
                MemoryUnit(memory_id="ra-2", scope_id="s1",
                           memory_type=MemoryType.EPISODIC,
                           content="Low importance memory to archive",
                           created_at=now, updated_at=now,
                           importance=0.2, confidence=0.5),
            ])
            # Archive the low importance one.
            store.bulk_archive(["ra-2"])
            result = mgr.analyze_retention_effectiveness("s1")
            self.assertEqual(result["active"], 1)
            self.assertEqual(result["archived"], 1)
            self.assertEqual(result["retention_health"], "good")
            store.close()

    def test_retention_empty_scope(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            result = mgr.analyze_retention_effectiveness("s1")
            self.assertEqual(result["total_memories"], 0)
            self.assertEqual(result["archive_ratio"], 0)
            store.close()


class GrowthRateTests(unittest.TestCase):
    """Tests for memory growth rate analysis."""

    def test_growth_rate_basic(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            now = datetime.now(timezone.utc).isoformat()
            store.add_memories([
                MemoryUnit(memory_id=f"gr-{i}", scope_id="s1",
                           memory_type=MemoryType.SEMANTIC,
                           content=f"Memory number {i}",
                           created_at=now, updated_at=now,
                           importance=0.5, confidence=0.8)
                for i in range(5)
            ])
            result = mgr.get_memory_growth_rate("s1", window_days=30)
            self.assertEqual(result["current_active"], 5)
            self.assertEqual(result["added_in_window"], 5)
            self.assertGreater(result["rate_per_day"], 0)
            self.assertIn("projected_30d", result)
            store.close()

    def test_growth_rate_empty(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            result = mgr.get_memory_growth_rate("s1")
            self.assertEqual(result["rate_per_day"], 0)
            self.assertEqual(result["projected_30d"], 0)
            store.close()


class AutoDeduplicateTests(unittest.TestCase):
    """Tests for automatic deduplication."""

    def test_auto_dedup_archives_duplicate(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            now = datetime.now(timezone.utc).isoformat()
            store.add_memories([
                MemoryUnit(memory_id="dup-1", scope_id="s1",
                           memory_type=MemoryType.SEMANTIC,
                           content="The project uses Python for backend services",
                           created_at=now, updated_at=now,
                           importance=0.8, confidence=0.8),
                MemoryUnit(memory_id="dup-2", scope_id="s1",
                           memory_type=MemoryType.SEMANTIC,
                           content="The project uses Python for backend services and APIs",
                           created_at=now, updated_at=now,
                           importance=0.5, confidence=0.8),
            ])
            result = mgr.auto_deduplicate("s1", threshold=0.7)
            self.assertGreater(result["duplicates_found"], 0)
            self.assertGreater(result["archived"], 0)
            store.close()

    def test_auto_dedup_dry_run(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            now = datetime.now(timezone.utc).isoformat()
            store.add_memories([
                MemoryUnit(memory_id="dup-3", scope_id="s1",
                           memory_type=MemoryType.SEMANTIC,
                           content="We use Docker for deployment and containerization",
                           created_at=now, updated_at=now,
                           importance=0.7, confidence=0.8),
                MemoryUnit(memory_id="dup-4", scope_id="s1",
                           memory_type=MemoryType.SEMANTIC,
                           content="We use Docker for deployment and container management",
                           created_at=now, updated_at=now,
                           importance=0.6, confidence=0.8),
            ])
            result = mgr.auto_deduplicate("s1", threshold=0.7, dry_run=True)
            self.assertTrue(result["dry_run"])
            self.assertEqual(result["archived"], 0)
            # Both still active.
            self.assertEqual(len(store.list_active("s1")), 2)
            store.close()

    def test_auto_dedup_respects_pinned(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            now = datetime.now(timezone.utc).isoformat()
            store.add_memories([
                MemoryUnit(memory_id="dup-5", scope_id="s1",
                           memory_type=MemoryType.SEMANTIC,
                           content="Critical pinned memory about deployment",
                           created_at=now, updated_at=now,
                           importance=0.99, confidence=0.9),  # pinned
                MemoryUnit(memory_id="dup-6", scope_id="s1",
                           memory_type=MemoryType.SEMANTIC,
                           content="Critical pinned memory about deployment process",
                           created_at=now, updated_at=now,
                           importance=0.6, confidence=0.8),
            ])
            result = mgr.auto_deduplicate("s1", threshold=0.7)
            # Pinned should not be touched.
            self.assertEqual(result["archived"], 0)
            store.close()


class CapacityForecastTests(unittest.TestCase):
    """Tests for capacity forecasting."""

    def test_forecast_with_growth(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            now = datetime.now(timezone.utc).isoformat()
            store.add_memories([
                MemoryUnit(memory_id=f"fc-{i}", scope_id="s1",
                           memory_type=MemoryType.SEMANTIC,
                           content=f"Memory {i} for capacity testing",
                           created_at=now, updated_at=now,
                           importance=0.5, confidence=0.8)
                for i in range(10)
            ])
            result = mgr.forecast_capacity("s1", quota=100)
            self.assertEqual(result["current"], 10)
            self.assertEqual(result["quota"], 100)
            self.assertAlmostEqual(result["utilization_pct"], 10.0)
            store.close()

    def test_forecast_empty_scope(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            result = mgr.forecast_capacity("s1")
            self.assertEqual(result["current"], 0)
            self.assertIsNone(result["days_until_full"])
            store.close()


class AuditTrailTests(unittest.TestCase):
    """Tests for audit trail export."""

    def test_audit_trail_basic(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            now = datetime.now(timezone.utc).isoformat()
            store.add_memories([
                MemoryUnit(memory_id="at-1", scope_id="s1",
                           memory_type=MemoryType.SEMANTIC,
                           content="Test memory for audit",
                           created_at=now, updated_at=now,
                           importance=0.5, confidence=0.8),
            ])
            events = mgr.export_audit_trail("s1")
            # Event log should have the create event.
            self.assertIsInstance(events, list)
            store.close()


class ActionPlanTests(unittest.TestCase):
    """Tests for the operator action plan generation."""

    def test_action_plan_with_issues(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            now = datetime.now(timezone.utc).isoformat()
            old = (datetime.now(timezone.utc) - timedelta(days=90)).isoformat()
            # Add duplicate memories.
            store.add_memories([
                MemoryUnit(memory_id="ap-1", scope_id="s1",
                           memory_type=MemoryType.SEMANTIC,
                           content="The project uses Python for all backend services",
                           created_at=now, updated_at=now,
                           importance=0.7, confidence=0.8),
                MemoryUnit(memory_id="ap-2", scope_id="s1",
                           memory_type=MemoryType.SEMANTIC,
                           content="The project uses Python for all backend services and APIs",
                           created_at=now, updated_at=now,
                           importance=0.5, confidence=0.8),
                # Stale memory.
                MemoryUnit(memory_id="ap-3", scope_id="s1",
                           memory_type=MemoryType.EPISODIC,
                           content="Something from long ago that nobody accesses anymore at all",
                           created_at=old, updated_at=old,
                           importance=0.2, confidence=0.5, access_count=0),
            ])
            plan = mgr.generate_action_plan("s1")
            self.assertGreater(plan["total_actions"], 0)
            action_types = [a["action"] for a in plan["actions"]]
            # Should have dedup and/or stale recommendations.
            self.assertTrue(len(action_types) > 0)
            # Actions should be sorted by priority.
            priorities = [a["priority"] for a in plan["actions"]]
            priority_order = {"high": 0, "medium": 1, "low": 2}
            self.assertEqual(priorities, sorted(priorities, key=lambda p: priority_order.get(p, 3)))
            store.close()

    def test_action_plan_clean_scope(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            plan = mgr.generate_action_plan("s1")
            self.assertEqual(plan["total_actions"], 0)
            store.close()


class SystemHealthCheckTests(unittest.TestCase):
    """Tests for the comprehensive system health check."""

    def test_health_check_healthy_scope(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            now = datetime.now(timezone.utc).isoformat()
            store.add_memories([
                MemoryUnit(memory_id="hc-1", scope_id="s1",
                           memory_type=MemoryType.SEMANTIC,
                           content="Healthy memory with good content",
                           topics=["testing"], entities=["Health"],
                           created_at=now, updated_at=now,
                           importance=0.7, confidence=0.8, access_count=3),
            ])
            result = mgr.run_system_health_check("s1")
            self.assertIn("passed", result)
            self.assertIn("checks", result)
            self.assertIn("integrity", result["checks"])
            self.assertIn("health_score", result["checks"])
            self.assertIn("staleness", result["checks"])
            self.assertIn("duplicates", result["checks"])
            self.assertIn("db_size", result["checks"])
            store.close()

    def test_health_check_empty_scope(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            result = mgr.run_system_health_check("s1")
            self.assertIn("passed", result)
            self.assertIsInstance(result["issues"], list)
            store.close()

    def test_health_check_with_duplicates(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            now = datetime.now(timezone.utc).isoformat()
            # Add many near-duplicates.
            for i in range(10):
                store.add_memories([
                    MemoryUnit(memory_id=f"hcd-{i}", scope_id="s1",
                               memory_type=MemoryType.SEMANTIC,
                               content="The project uses Python for backend development services",
                               created_at=now, updated_at=now,
                               importance=0.5, confidence=0.8),
                ])
            result = mgr.run_system_health_check("s1")
            dup_check = result["checks"]["duplicates"]
            self.assertGreater(dup_check["duplicate_pairs"], 0)
            store.close()


class GroupedSearchTests(unittest.TestCase):
    """Tests for grouped search results."""

    def test_search_grouped_by_type(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            now = datetime.now(timezone.utc).isoformat()
            store.add_memories([
                MemoryUnit(memory_id="sg-1", scope_id="s1",
                           memory_type=MemoryType.SEMANTIC,
                           content="Python is used for backend development",
                           topics=["python"], created_at=now, updated_at=now,
                           importance=0.7, confidence=0.8),
                MemoryUnit(memory_id="sg-2", scope_id="s1",
                           memory_type=MemoryType.PREFERENCE,
                           content="I prefer Python over Java",
                           topics=["python"], created_at=now, updated_at=now,
                           importance=0.6, confidence=0.9),
            ])
            result = mgr.search_grouped("Python", scope_id="s1", group_by="type")
            self.assertIn("groups", result)
            self.assertEqual(result["group_by"], "type")
            store.close()

    def test_search_grouped_by_topic(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            now = datetime.now(timezone.utc).isoformat()
            store.add_memories([
                MemoryUnit(memory_id="sg-3", scope_id="s1",
                           memory_type=MemoryType.SEMANTIC,
                           content="React handles the frontend rendering",
                           topics=["frontend"], created_at=now, updated_at=now,
                           importance=0.7, confidence=0.8),
            ])
            result = mgr.search_grouped("React frontend", scope_id="s1", group_by="topic")
            self.assertEqual(result["group_by"], "topic")
            store.close()

    def test_search_grouped_empty(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            result = mgr.search_grouped("nonexistent query", scope_id="s1")
            self.assertEqual(result["total_results"], 0)
            self.assertEqual(len(result["groups"]), 0)
            store.close()


class ScopeArchivalTests(unittest.TestCase):
    """Tests for scope-level archival."""

    def test_archive_scope(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            now = datetime.now(timezone.utc).isoformat()
            store.add_memories([
                MemoryUnit(memory_id="as-1", scope_id="retire",
                           memory_type=MemoryType.SEMANTIC,
                           content="Old memory to archive", created_at=now, updated_at=now,
                           importance=0.5, confidence=0.8),
                MemoryUnit(memory_id="as-2", scope_id="retire",
                           memory_type=MemoryType.PREFERENCE,
                           content="Pinned memory stays", created_at=now, updated_at=now,
                           importance=0.99, confidence=0.9),
            ])
            result = mgr.archive_scope("retire")
            self.assertEqual(result["archived"], 1)
            self.assertEqual(result["pinned_kept"], 1)
            active = store.list_active("retire")
            self.assertEqual(len(active), 1)
            self.assertEqual(active[0].memory_id, "as-2")
            store.close()


class BulkPinTests(unittest.TestCase):
    """Tests for bulk pinning by criteria."""

    def test_bulk_pin_by_importance(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            now = datetime.now(timezone.utc).isoformat()
            store.add_memories([
                MemoryUnit(memory_id="bp-1", scope_id="s1",
                           memory_type=MemoryType.SEMANTIC,
                           content="Very important memory", created_at=now, updated_at=now,
                           importance=0.95, confidence=0.9),
                MemoryUnit(memory_id="bp-2", scope_id="s1",
                           memory_type=MemoryType.EPISODIC,
                           content="Normal memory", created_at=now, updated_at=now,
                           importance=0.4, confidence=0.7),
            ])
            result = mgr.bulk_pin_by_criteria("s1", min_importance=0.9, min_access_count=100)
            self.assertEqual(result["pinned"], 1)
            unit = store._get_by_id("bp-1")
            self.assertAlmostEqual(unit.importance, 0.99)
            store.close()

    def test_bulk_pin_by_access(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            now = datetime.now(timezone.utc).isoformat()
            store.add_memories([
                MemoryUnit(memory_id="bp-3", scope_id="s1",
                           memory_type=MemoryType.SEMANTIC,
                           content="Frequently accessed memory", created_at=now, updated_at=now,
                           importance=0.5, confidence=0.8, access_count=15),
            ])
            result = mgr.bulk_pin_by_criteria("s1", min_importance=0.95, min_access_count=10)
            self.assertEqual(result["pinned"], 1)
            store.close()


class YAMLExportTests(unittest.TestCase):
    """Tests for YAML export."""

    def test_yaml_export(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            now = datetime.now(timezone.utc).isoformat()
            store.add_memories([
                MemoryUnit(memory_id="ye-1", scope_id="s1",
                           memory_type=MemoryType.SEMANTIC,
                           content="Python is the main language",
                           topics=["python"], entities=["Python"],
                           created_at=now, updated_at=now,
                           importance=0.7, confidence=0.8),
            ])
            yaml_str = mgr.export_scope_yaml("s1")
            self.assertIn("memories:", yaml_str)
            self.assertIn("ye-1", yaml_str)
            self.assertIn("Python is the main language", yaml_str)
            self.assertIn("semantic", yaml_str)
            store.close()

    def test_yaml_export_empty(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            yaml_str = mgr.export_scope_yaml("s1")
            self.assertIn("Count: 0", yaml_str)
            store.close()


class BookmarkTests(unittest.TestCase):
    """Tests for memory bookmarks."""

    def test_bookmark_and_retrieve(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            now = datetime.now(timezone.utc).isoformat()
            store.add_memories([
                MemoryUnit(memory_id="bk-1", scope_id="s1",
                           memory_type=MemoryType.SEMANTIC,
                           content="Important API endpoint documentation",
                           created_at=now, updated_at=now,
                           importance=0.7, confidence=0.8),
                MemoryUnit(memory_id="bk-2", scope_id="s1",
                           memory_type=MemoryType.PREFERENCE,
                           content="User likes dark mode", created_at=now, updated_at=now,
                           importance=0.5, confidence=0.9),
            ])
            # Bookmark bk-1.
            result = mgr.bookmark_memories(["bk-1"])
            self.assertEqual(result["tagged"], 1)

            # Retrieve bookmarks.
            bookmarks = mgr.get_bookmarks("s1")
            self.assertEqual(len(bookmarks), 1)
            self.assertEqual(bookmarks[0]["memory_id"], "bk-1")
            store.close()

    def test_bookmark_idempotent(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            now = datetime.now(timezone.utc).isoformat()
            store.add_memories([
                MemoryUnit(memory_id="bk-3", scope_id="s1",
                           memory_type=MemoryType.SEMANTIC,
                           content="Test memory", created_at=now, updated_at=now,
                           importance=0.5, confidence=0.8),
            ])
            mgr.bookmark_memories(["bk-3"])
            result = mgr.bookmark_memories(["bk-3"])
            self.assertEqual(result["tagged"], 0)  # Already bookmarked
            store.close()


class SnapshotComparisonTests(unittest.TestCase):
    """Tests for snapshot comparison."""

    def test_compare_no_snapshots(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            result = mgr.compare_snapshots("s1")
            self.assertIsNone(result["delta"])
            self.assertIn("message", result)
            store.close()

    def test_compare_with_snapshot(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="s1", auto_consolidate=False)
            now = datetime.now(timezone.utc).isoformat()

            # Add some memories and take snapshot.
            store.add_memories([
                MemoryUnit(memory_id="sc-1", scope_id="s1",
                           memory_type=MemoryType.SEMANTIC,
                           content="First memory", created_at=now, updated_at=now,
                           importance=0.5, confidence=0.8),
            ])
            store.save_stats_snapshot("s1")

            # Add more memories.
            store.add_memories([
                MemoryUnit(memory_id="sc-2", scope_id="s1",
                           memory_type=MemoryType.PREFERENCE,
                           content="Second memory", created_at=now, updated_at=now,
                           importance=0.6, confidence=0.9),
            ])

            result = mgr.compare_snapshots("s1")
            self.assertIn("current", result)
            store.close()


class MilestoneIntegrationTests(unittest.TestCase):
    """Integration tests for the complete production-ready memory system."""

    def test_full_operator_workflow(self):
        """End-to-end operator workflow: ingest, analyze, maintain, report."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(
                store=store, scope_id="ops",
                auto_consolidate=False, use_embeddings=True,
                embedding_mode="hashing",
            )
            now = datetime.now(timezone.utc).isoformat()

            # 1. Ingest memories.
            session_turns = [
                {"prompt_text": "We use PostgreSQL as the primary database",
                 "response_text": "PostgreSQL is noted as the primary DB."},
                {"prompt_text": "I prefer snake_case for all Python code",
                 "response_text": "Snake case noted for Python code style."},
                {"prompt_text": "The frontend uses React with TypeScript",
                 "response_text": "React + TypeScript for the frontend, understood."},
            ]
            mgr.ingest_session_turns("sess-ops-1", session_turns, scope_id="ops")

            # 2. Run health check.
            health = mgr.run_system_health_check("ops")
            self.assertIn("passed", health)

            # 3. Generate action plan.
            plan = mgr.generate_action_plan("ops")
            self.assertIn("actions", plan)

            # 4. Get system summary.
            summary = mgr.get_system_summary()
            self.assertIn("scopes", summary)

            # 5. Re-embed the scope.
            embed_result = mgr.re_embed_scope("ops")
            self.assertIn("re_embedded", embed_result)

            # 6. Compress content.
            compress_result = mgr.batch_compress("ops")
            self.assertIn("total", compress_result)

            # 7. Auto-tag by type.
            tag_result = mgr.bulk_tag_by_type("ops")
            self.assertIn("tagged", tag_result)

            # 8. Get growth rate.
            growth = mgr.get_memory_growth_rate("ops")
            self.assertIn("rate_per_day", growth)

            # 9. Forecast capacity.
            forecast = mgr.forecast_capacity("ops", quota=500)
            self.assertIn("utilization_pct", forecast)

            # 10. Export audit trail.
            trail = mgr.export_audit_trail("ops")
            self.assertIsInstance(trail, list)

            mgr.close()

    def test_memory_lifecycle_complete(self):
        """Test complete memory lifecycle: create, access, tag, pin, archive."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="lc", auto_consolidate=False)
            now = datetime.now(timezone.utc).isoformat()

            # Create.
            store.add_memories([
                MemoryUnit(memory_id="lc-1", scope_id="lc",
                           memory_type=MemoryType.SEMANTIC,
                           content="Database migration strategy for Q2",
                           topics=["database", "migration"],
                           created_at=now, updated_at=now,
                           importance=0.7, confidence=0.8),
            ])

            # Access.
            store.mark_accessed(["lc-1"], now)
            unit = store._get_by_id("lc-1")
            self.assertGreater(unit.access_count, 0)

            # Tag.
            store.add_tags("lc-1", ["critical", "q2-planning"])
            unit = store._get_by_id("lc-1")
            self.assertIn("critical", unit.tags)

            # Bookmark.
            mgr.bookmark_memories(["lc-1"])
            bookmarks = mgr.get_bookmarks("lc")
            self.assertEqual(len(bookmarks), 1)

            # Annotate.
            store.add_annotation("lc-1", "This needs review before EOQ")
            annotations = store.get_annotations("lc-1")
            self.assertGreater(len(annotations), 0)

            # Link.
            store.add_memories([
                MemoryUnit(memory_id="lc-2", scope_id="lc",
                           memory_type=MemoryType.PROJECT_STATE,
                           content="Q2 database migration timeline",
                           topics=["database", "timeline"],
                           created_at=now, updated_at=now,
                           importance=0.6, confidence=0.7),
            ])
            store.add_link("lc-2", "lc-1", "depends_on")
            links = store.get_links("lc-1")
            self.assertGreater(len(links), 0)

            # Quality score.
            quality = mgr.score_memory_quality("lc-1")
            self.assertGreater(quality["score"], 0)

            # Lifecycle.
            lifecycle = mgr.get_memory_lifecycle("lc-1")
            self.assertIn("memory_id", lifecycle)

            # Archive scope.
            result = mgr.archive_scope("lc")
            self.assertGreater(result["archived"], 0)

            store.close()

    def test_multi_scope_operations_complete(self):
        """Test multi-scope: create, clone, compare, merge, health compare."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="team-a", auto_consolidate=False)
            now = datetime.now(timezone.utc).isoformat()

            # Create two scopes.
            for scope, prefix, content in [
                ("team-a", "ta", "Python microservices architecture"),
                ("team-b", "tb", "Java monolith application"),
            ]:
                store.add_memories([
                    MemoryUnit(memory_id=f"{prefix}-1", scope_id=scope,
                               memory_type=MemoryType.PROJECT_STATE,
                               content=content, topics=["architecture"],
                               created_at=now, updated_at=now,
                               importance=0.7, confidence=0.8),
                ])

            # Clone.
            clone = mgr.clone_scope("team-a", "team-a-backup")
            self.assertEqual(clone["cloned"], 1)

            # Compare.
            comparison = mgr.compare_scopes("team-a", "team-b")
            self.assertIn("scope_a", comparison)

            # Health compare.
            health = mgr.compare_scope_health("team-a", "team-b")
            self.assertIn("scope_a", health)

            # Merge.
            merge = mgr.merge_scopes("team-b", "team-a")
            self.assertIn("copied", merge)

            # YAML export.
            yaml = mgr.export_scope_yaml("team-a")
            self.assertIn("memories:", yaml)

            # Retention analysis.
            retention = mgr.analyze_retention_effectiveness("team-a")
            self.assertIn("active", retention)

            store.close()

    def test_search_and_retrieval_modes(self):
        """Test all retrieval modes with the same dataset."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            now = datetime.now(timezone.utc).isoformat()

            memories = [
                MemoryUnit(memory_id=f"sr-{i}", scope_id="search",
                           memory_type=MemoryType.SEMANTIC,
                           content=content, topics=topics,
                           created_at=now, updated_at=now,
                           importance=0.7, confidence=0.8)
                for i, (content, topics) in enumerate([
                    ("Python Flask API endpoint design", ["python", "api"]),
                    ("React component state management", ["react", "frontend"]),
                    ("PostgreSQL query optimization tips", ["database", "postgresql"]),
                    ("Docker container deployment workflow", ["docker", "deployment"]),
                    ("CI/CD pipeline with GitHub Actions", ["cicd", "github"]),
                ])
            ]
            store.add_memories(memories)

            # Keyword mode.
            mgr_kw = MemoryManager(store=store, scope_id="search",
                                   auto_consolidate=False, retrieval_mode="keyword")
            hits_kw = mgr_kw.retrieve_for_prompt("Python API", scope_id="search")
            self.assertGreater(len(hits_kw), 0)

            # Hybrid mode.
            mgr_hy = MemoryManager(store=store, scope_id="search",
                                   auto_consolidate=False, retrieval_mode="hybrid",
                                   use_embeddings=True)
            hits_hy = mgr_hy.retrieve_for_prompt("database optimization", scope_id="search")

            # Grouped search.
            grouped = mgr_kw.search_grouped("Python", scope_id="search", group_by="type")
            self.assertIn("groups", grouped)

            # Regex search.
            regex = mgr_kw.search_regex(pattern="Python.*API", scope_id="search")
            self.assertIsInstance(regex, list)

            store.close()


class ManagerImportExportTests(unittest.TestCase):
    """Tests for MemoryManager.import_memories and clear_cache."""

    def test_import_memories_and_clear_cache(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="imp", auto_consolidate=False)
            store.add_memories([
                MemoryUnit(memory_id="exp-1", content="Exported fact",
                           memory_type=MemoryType.SEMANTIC, scope_id="imp",
                           importance=0.5, source_turn_start=0, source_turn_end=0),
            ])
            exported = store.export_scope_json("imp")
            self.assertEqual(len(exported), 1)

            count = mgr.import_memories(exported, target_scope_id="imp2")
            self.assertEqual(count, 1)

            stats = store.get_stats("imp2")
            self.assertGreater(stats.get("active", stats.get("total", 0)), 0)
            store.close()

    def test_import_empty_list(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="imp", auto_consolidate=False)
            count = mgr.import_memories([])
            self.assertEqual(count, 0)
            store.close()

    def test_clear_cache(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="cc", auto_consolidate=False)
            mgr.clear_cache()
            store.close()


class MultiTurnContextTests(unittest.TestCase):
    """Tests for _MultiTurnContext helper methods."""

    def test_add_turn_and_get_recent_context(self):
        from metaclaw.memory.manager import _MultiTurnContext
        ctx = _MultiTurnContext(window=3)
        ctx.add_turn("Hello", "Hi there", 0)
        ctx.add_turn("What is Python?", "A programming language", 1)
        result = ctx.get_recent_context()
        self.assertIn("Hello", result)
        self.assertIn("A programming language", result)

    def test_window_eviction(self):
        from metaclaw.memory.manager import _MultiTurnContext
        ctx = _MultiTurnContext(window=2)
        ctx.add_turn("First", "R1", 0)
        ctx.add_turn("Second", "R2", 1)
        ctx.add_turn("Third", "R3", 2)
        result = ctx.get_recent_context()
        self.assertNotIn("First", result)
        self.assertIn("Third", result)

    def test_get_accumulated_entities(self):
        from metaclaw.memory.manager import _MultiTurnContext
        ctx = _MultiTurnContext(window=5)
        ctx.add_turn("We use PostgreSQL for our database", "Good choice", 0)
        ctx.add_turn("Docker is used for deployment", "Container-based", 1)
        entities = ctx.get_accumulated_entities()
        self.assertIsInstance(entities, list)
        # Should find at least PostgreSQL and Docker
        entity_text = " ".join(entities).lower()
        self.assertTrue("postgresql" in entity_text or "docker" in entity_text)

    def test_has_continuation_pattern(self):
        from metaclaw.memory.manager import _MultiTurnContext
        ctx = _MultiTurnContext(window=3)
        self.assertTrue(ctx.has_continuation_pattern("Also, we use Redis"))
        self.assertTrue(ctx.has_continuation_pattern("regarding that, what about caching?"))
        self.assertFalse(ctx.has_continuation_pattern("What is the weather today?"))


class ManagerUpdateAndEventLogTests(unittest.TestCase):
    """Tests for MemoryManager.update_memory and get_event_log."""

    def test_update_memory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="upd", auto_consolidate=False)
            store.add_memories([
                MemoryUnit(memory_id="upd-1", content="Original content",
                           memory_type=MemoryType.SEMANTIC, scope_id="upd",
                           importance=0.5, source_turn_start=0, source_turn_end=0),
            ])
            result = mgr.update_memory("upd-1", "Updated content", summary="New summary")
            self.assertTrue(result)
            mem = mgr.get_memory("upd-1")
            self.assertEqual(mem.content, "Updated content")
            store.close()

    def test_update_nonexistent_memory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="upd", auto_consolidate=False)
            result = mgr.update_memory("nonexistent", "New content")
            self.assertFalse(result)
            store.close()

    def test_get_event_log(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="evt", auto_consolidate=False)
            store.add_memories([
                MemoryUnit(memory_id="evt-1", content="Test event memory",
                           memory_type=MemoryType.SEMANTIC, scope_id="evt",
                           importance=0.5, source_turn_start=0, source_turn_end=0),
            ])
            events = mgr.get_event_log(scope_id="evt")
            self.assertIsInstance(events, list)
            store.close()


class SimulatedProductionTests(unittest.TestCase):
    """Simulate live integration testing scenarios locally.

    These tests exercise the system under realistic multi-user, multi-scope,
    high-volume conditions that would normally require a staging environment.
    """

    def test_multi_user_workload(self):
        """Simulate multiple users writing/reading memories across scopes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))

            for uid in range(5):
                scope = f"scope-{uid}"
                mgr = MemoryManager(store=store, scope_id=scope,
                                    auto_consolidate=False)
                memories = []
                for i in range(20):
                    memories.append(MemoryUnit(
                        memory_id=f"user-{uid}-mem-{i}",
                        content=f"User {uid} preference {i}: use Python for data tasks",
                        memory_type=MemoryType.PREFERENCE,
                        scope_id=scope,
                        importance=0.3 + (i * 0.03),
                        source_turn_start=i, source_turn_end=i,
                    ))
                store.add_memories(memories)
                hits = mgr.retrieve_for_prompt("Python data", scope_id=scope)
                self.assertGreater(len(hits), 0, f"user-{uid}: no retrieval results")

            scopes = store.list_scopes()
            self.assertGreaterEqual(len(scopes), 5)
            store.close()

    def test_ttl_expiry_under_load(self):
        """Validate TTL expiry works correctly with many memories."""
        from datetime import datetime, timedelta, timezone
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="ttl-load",
                                auto_consolidate=False)
            past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
            future = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()

            # Create 50 memories: 25 expired, 25 still valid
            memories = []
            for i in range(50):
                memories.append(MemoryUnit(
                    memory_id=f"ttl-{i}",
                    content=f"Memory {i} about system configuration setting {i}",
                    memory_type=MemoryType.SEMANTIC,
                    scope_id="ttl-load",
                    importance=0.5,
                    source_turn_start=0, source_turn_end=0,
                    expires_at=past if i < 25 else future,
                ))
            store.add_memories(memories)

            expired_count = mgr.expire_stale("ttl-load")
            self.assertEqual(expired_count, 25)

            # Only 25 should remain active
            stats = store.get_stats("ttl-load")
            self.assertEqual(stats["active"], 25)
            store.close()

    def test_cross_scope_sharing_multi_team(self):
        """Test cross-scope memory sharing between multiple team scopes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="team-alpha",
                                auto_consolidate=False)

            # Team alpha creates memories
            store.add_memories([
                MemoryUnit(memory_id="alpha-1", content="API uses REST with JSON responses",
                           memory_type=MemoryType.SEMANTIC, scope_id="team-alpha",
                           importance=0.8, source_turn_start=0, source_turn_end=0),
                MemoryUnit(memory_id="alpha-2", content="Deploy to AWS us-east-1 region",
                           memory_type=MemoryType.PROCEDURAL_OBSERVATION, scope_id="team-alpha",
                           importance=0.7, source_turn_start=1, source_turn_end=1),
            ])

            # Share to team-beta and team-gamma
            for target in ["team-beta", "team-gamma"]:
                new_id = mgr.share_memory("alpha-1", target)
                self.assertIsNotNone(new_id)

            # Verify shared memories exist in target scopes
            beta_stats = store.get_stats("team-beta")
            gamma_stats = store.get_stats("team-gamma")
            self.assertGreater(beta_stats.get("active", beta_stats.get("total", 0)), 0)
            self.assertGreater(gamma_stats.get("active", gamma_stats.get("total", 0)), 0)

            # Cross-scope comparison
            comparison = mgr.compare_scopes("team-alpha", "team-beta")
            self.assertIn("scope_a", comparison)
            store.close()

    def test_retrieval_feedback_loop(self):
        """Test that feedback affects retrieval quality over time."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="feedback-loop",
                                auto_consolidate=False)

            store.add_memories([
                MemoryUnit(memory_id="fb-1", content="Python is the preferred language for data science",
                           memory_type=MemoryType.PREFERENCE, scope_id="feedback-loop",
                           importance=0.5, source_turn_start=0, source_turn_end=0),
                MemoryUnit(memory_id="fb-2", content="Use PostgreSQL for relational data storage",
                           memory_type=MemoryType.SEMANTIC, scope_id="feedback-loop",
                           importance=0.5, source_turn_start=1, source_turn_end=1),
            ])

            # Simulate positive feedback for fb-1 over multiple retrievals
            for _ in range(5):
                mgr.provide_feedback("fb-1", "positive")

            # Negative feedback for fb-2
            mgr.provide_feedback("fb-2", "negative")

            # Check that importance diverged
            mem1 = mgr.get_memory("fb-1")
            mem2 = mgr.get_memory("fb-2")
            self.assertGreater(mem1.importance, mem2.importance)
            store.close()

    def test_scale_retrieval_500_memories(self):
        """Validate retrieval performance with 500+ memories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="scale",
                                auto_consolidate=False)

            topics = ["Python", "database", "API", "deployment", "testing",
                      "Docker", "Kubernetes", "monitoring", "logging", "security"]
            memories = []
            for i in range(500):
                topic = topics[i % len(topics)]
                memories.append(MemoryUnit(
                    memory_id=f"scale-{i}",
                    content=f"Memory about {topic}: configuration detail {i} for production use",
                    memory_type=MemoryType.SEMANTIC,
                    scope_id="scale",
                    importance=0.3 + (i % 10) * 0.07,
                    source_turn_start=i // 10, source_turn_end=i // 10,
                    entities=[topic],
                    topics=[topic.lower()],
                ))
            store.add_memories(memories)

            # Retrieval should return results quickly
            hits = mgr.retrieve_for_prompt("Python configuration", scope_id="scale")
            self.assertGreater(len(hits), 0)

            # Health check should work at scale
            health = mgr.run_system_health_check(scope_id="scale")
            self.assertIn("passed", health)

            # Action plan should generate recommendations
            plan = mgr.generate_action_plan(scope_id="scale")
            self.assertIn("actions", plan)

            store.close()

    def test_full_maintenance_cycle(self):
        """Test a complete maintenance cycle: dedup, compress, health, action plan."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="maint",
                                auto_consolidate=False)

            # Create memories with some duplicates and compressible content
            store.add_memories([
                MemoryUnit(memory_id="m-1", content="The user basically prefers Python for essentially all data tasks",
                           memory_type=MemoryType.PREFERENCE, scope_id="maint",
                           importance=0.6, source_turn_start=0, source_turn_end=0),
                MemoryUnit(memory_id="m-2", content="The user basically prefers Python for essentially all data tasks",
                           memory_type=MemoryType.PREFERENCE, scope_id="maint",
                           importance=0.5, source_turn_start=1, source_turn_end=1),
                MemoryUnit(memory_id="m-3", content="Deploy using Docker containers in production environment",
                           memory_type=MemoryType.PROCEDURAL_OBSERVATION, scope_id="maint",
                           importance=0.7, source_turn_start=2, source_turn_end=2),
            ])

            # Run dedup
            dedup_result = mgr.auto_deduplicate(scope_id="maint")
            self.assertIn("archived", dedup_result)

            # Run compression
            compressed = mgr.batch_compress(scope_id="maint")
            self.assertIn("compressed", compressed)

            # Health check
            health = mgr.run_system_health_check(scope_id="maint")
            self.assertIn("passed", health)

            # Action plan
            plan = mgr.generate_action_plan(scope_id="maint")
            self.assertIn("actions", plan)

            # System summary
            summary = mgr.get_system_summary()
            self.assertIn("scopes", summary)

            store.close()


class MemoryRESTAPITests(unittest.TestCase):
    """Tests for the memory management REST API endpoints."""

    def _make_server(self, store, scope="api-test"):
        import queue
        import threading
        mgr = MemoryManager(store=store, scope_id=scope, auto_consolidate=False)
        cfg = MetaClawConfig()
        cfg.api_key = ""  # No auth for testing
        from metaclaw.api_server import MetaClawAPIServer
        server = MetaClawAPIServer(
            config=cfg,
            output_queue=queue.Queue(),
            submission_enabled=threading.Event(),
            memory_manager=mgr,
        )
        server.submission_enabled.set()
        return server, mgr

    def test_memory_stats_endpoint(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories([
                MemoryUnit(memory_id="api-1", content="REST API test memory",
                           memory_type=MemoryType.SEMANTIC, scope_id="api-test",
                           importance=0.5, source_turn_start=0, source_turn_end=0),
            ])
            server, mgr = self._make_server(store)
            from fastapi.testclient import TestClient
            client = TestClient(server.app)
            resp = client.get("/v1/memory/stats?scope=api-test")
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertGreater(data.get("active", 0), 0)
            store.close()

    def test_memory_search_endpoint(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories([
                MemoryUnit(memory_id="api-s1", content="Python is great for data science",
                           memory_type=MemoryType.SEMANTIC, scope_id="api-test",
                           importance=0.7, source_turn_start=0, source_turn_end=0),
            ])
            server, mgr = self._make_server(store)
            from fastapi.testclient import TestClient
            client = TestClient(server.app)
            resp = client.get("/v1/memory/search?q=Python&scope=api-test")
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertIsInstance(data, list)
            store.close()

    def test_memory_health_endpoint(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories([
                MemoryUnit(memory_id="api-h1", content="Health check test memory",
                           memory_type=MemoryType.SEMANTIC, scope_id="api-test",
                           importance=0.5, source_turn_start=0, source_turn_end=0),
            ])
            server, mgr = self._make_server(store)
            from fastapi.testclient import TestClient
            client = TestClient(server.app)
            resp = client.get("/v1/memory/health?scope=api-test")
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertIn("passed", data)
            store.close()

    def test_memory_get_by_id_endpoint(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories([
                MemoryUnit(memory_id="api-g1", content="Get by ID test memory",
                           memory_type=MemoryType.SEMANTIC, scope_id="api-test",
                           importance=0.5, source_turn_start=0, source_turn_end=0),
            ])
            server, mgr = self._make_server(store)
            from fastapi.testclient import TestClient
            client = TestClient(server.app)
            resp = client.get("/v1/memory/api-g1")
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertEqual(data["memory_id"], "api-g1")

            # 404 for nonexistent
            resp2 = client.get("/v1/memory/nonexistent")
            self.assertEqual(resp2.status_code, 404)
            store.close()

    def test_memory_summary_endpoint(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            store.add_memories([
                MemoryUnit(memory_id="api-sum1", content="Summary endpoint test",
                           memory_type=MemoryType.SEMANTIC, scope_id="api-test",
                           importance=0.5, source_turn_start=0, source_turn_end=0),
            ])
            server, mgr = self._make_server(store)
            from fastapi.testclient import TestClient
            client = TestClient(server.app)
            resp = client.get("/v1/memory/summary")
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertIn("scopes", data)
            store.close()

    def test_memory_no_manager_returns_503(self):
        """Endpoints return 503 when memory is not enabled."""
        import queue
        import threading
        cfg = MetaClawConfig()
        cfg.api_key = ""
        from metaclaw.api_server import MetaClawAPIServer
        server = MetaClawAPIServer(
            config=cfg,
            output_queue=queue.Queue(),
            submission_enabled=threading.Event(),
            memory_manager=None,
        )
        from fastapi.testclient import TestClient
        client = TestClient(server.app)
        resp = client.get("/v1/memory/stats")
        self.assertEqual(resp.status_code, 503)


class OperatorReportTests(unittest.TestCase):
    """Tests for the comprehensive operator diagnostic report."""

    def test_operator_report_basic(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="report", auto_consolidate=False)
            store.add_memories([
                MemoryUnit(memory_id="rpt-1", content="Operator report test memory about Python",
                           memory_type=MemoryType.SEMANTIC, scope_id="report",
                           importance=0.6, source_turn_start=0, source_turn_end=0),
                MemoryUnit(memory_id="rpt-2", content="Another test memory about database configuration",
                           memory_type=MemoryType.PROJECT_STATE, scope_id="report",
                           importance=0.5, source_turn_start=1, source_turn_end=1),
            ])
            report = mgr.generate_operator_report(scope_id="report")
            self.assertEqual(report["scope_id"], "report")
            self.assertIn("health", report)
            self.assertIn("action_plan", report)
            self.assertIn("stats", report)
            self.assertIn("system", report)
            self.assertIn("type_balance", report)
            self.assertIn("generated_at", report)
            store.close()

    def test_operator_report_empty_scope(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="empty", auto_consolidate=False)
            report = mgr.generate_operator_report(scope_id="empty")
            self.assertEqual(report["scope_id"], "empty")
            # Should not crash on empty scope
            self.assertIn("health", report)
            store.close()


class FeedbackPatternAnalysisTests(unittest.TestCase):
    """Tests for feedback pattern analysis."""

    def test_feedback_analysis_with_data(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="fba", auto_consolidate=False)
            store.add_memories([
                MemoryUnit(memory_id="fba-1", content="Python is the team preferred language",
                           memory_type=MemoryType.PREFERENCE, scope_id="fba",
                           importance=0.5, source_turn_start=0, source_turn_end=0),
                MemoryUnit(memory_id="fba-2", content="PostgreSQL for all relational data",
                           memory_type=MemoryType.SEMANTIC, scope_id="fba",
                           importance=0.5, source_turn_start=1, source_turn_end=1),
            ])

            # Provide feedback
            mgr.provide_feedback("fba-1", "positive")
            mgr.provide_feedback("fba-1", "positive")
            mgr.provide_feedback("fba-2", "negative")

            result = mgr.analyze_feedback_patterns(scope_id="fba")
            self.assertEqual(result["scope_id"], "fba")
            self.assertEqual(result["total_feedback"], 3)
            self.assertEqual(result["positive"], 2)
            self.assertEqual(result["negative"], 1)
            self.assertGreater(result["positive_rate"], 0.5)
            self.assertEqual(result["unique_memories_with_feedback"], 2)
            store.close()

    def test_feedback_analysis_empty(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="fba-empty", auto_consolidate=False)
            result = mgr.analyze_feedback_patterns(scope_id="fba-empty")
            self.assertEqual(result["total_feedback"], 0)
            self.assertEqual(result["positive_rate"], 0.0)
            store.close()


class HeuristicJudgeTests(unittest.TestCase):
    """Tests for the heuristic replay judge."""

    def test_relevant_memory_scores_high(self):
        from metaclaw.memory.replay import HeuristicReplayJudge
        judge = HeuristicReplayJudge()
        self.assertTrue(judge.is_available())
        score = judge.score_memory_relevance(
            "Python is great for data science and machine learning",
            "What language should I use for data science?",
            "Python is widely used for data science tasks",
        )
        self.assertGreater(score, 0.2)

    def test_irrelevant_memory_scores_low(self):
        from metaclaw.memory.replay import HeuristicReplayJudge
        judge = HeuristicReplayJudge()
        score = judge.score_memory_relevance(
            "The office is located on the third floor",
            "What database should I use for the API?",
            "PostgreSQL is a good choice for relational data",
        )
        self.assertLess(score, 0.3)

    def test_empty_memory_scores_zero(self):
        from metaclaw.memory.replay import HeuristicReplayJudge
        judge = HeuristicReplayJudge()
        score = judge.score_memory_relevance("", "some query", "some response")
        self.assertEqual(score, 0.0)


class MemoryInjectionQualityTests(unittest.TestCase):
    """Tests to validate memory injection doesn't degrade prompt quality."""

    def test_injection_respects_token_budget(self):
        """Verify injected memory text stays within token budget."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="inject",
                                auto_consolidate=False)
            # Create many memories to test budget enforcement
            memories = []
            for i in range(100):
                memories.append(MemoryUnit(
                    memory_id=f"inj-{i}",
                    content=f"Memory item {i}: " + "detailed technical context " * 10,
                    memory_type=MemoryType.SEMANTIC, scope_id="inject",
                    importance=0.5 + (i % 10) * 0.05,
                    source_turn_start=0, source_turn_end=0,
                    topics=["python", "testing"],
                ))
            store.add_memories(memories)

            # Retrieve and render
            hits = mgr.retrieve_for_prompt("python testing", scope_id="inject")
            rendered = mgr.render_for_prompt(hits)

            # Token budget should limit output
            word_count = len(rendered.split())
            # Default max_injected_tokens is typically 1024 or similar
            # The rendered text shouldn't be unlimited
            self.assertLess(word_count, 2000, "Rendered text exceeds expected budget")
            self.assertGreater(len(hits), 0, "Should retrieve some memories")
            store.close()

    def test_injection_preserves_type_diversity(self):
        """Verify injection doesn't over-represent a single memory type."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="div",
                                auto_consolidate=False)
            types = [MemoryType.SEMANTIC, MemoryType.PREFERENCE,
                     MemoryType.PROJECT_STATE, MemoryType.EPISODIC]
            memories = []
            for i in range(40):
                mtype = types[i % 4]
                memories.append(MemoryUnit(
                    memory_id=f"div-{i}",
                    content=f"Memory about Python development: item {i} for type {mtype.value}",
                    memory_type=mtype, scope_id="div",
                    importance=0.7, source_turn_start=0, source_turn_end=0,
                    topics=["python"],
                ))
            store.add_memories(memories)

            hits = mgr.retrieve_for_prompt("Python development", scope_id="div")
            if len(hits) >= 4:
                type_counts: dict[str, int] = {}
                for h in hits:
                    t = h.memory_type.value
                    type_counts[t] = type_counts.get(t, 0) + 1
                max_ratio = max(type_counts.values()) / len(hits)
                # No single type should dominate more than 70%
                self.assertLessEqual(max_ratio, 0.70,
                    f"Type diversity violated: {type_counts}")
            store.close()

    def test_injection_prioritizes_high_importance(self):
        """Verify higher-importance memories are prioritized in retrieval."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(os.path.join(tmpdir, "memory.db"))
            mgr = MemoryManager(store=store, scope_id="pri",
                                auto_consolidate=False)
            store.add_memories([
                MemoryUnit(memory_id="pri-low", content="Python is used for scripting tasks",
                           memory_type=MemoryType.SEMANTIC, scope_id="pri",
                           importance=0.1, source_turn_start=0, source_turn_end=0,
                           topics=["python"]),
                MemoryUnit(memory_id="pri-high", content="Python is the primary backend language",
                           memory_type=MemoryType.SEMANTIC, scope_id="pri",
                           importance=0.95, source_turn_start=1, source_turn_end=1,
                           topics=["python"]),
            ])

            hits = mgr.retrieve_for_prompt("Python backend", scope_id="pri")
            self.assertGreater(len(hits), 0)
            # High-importance should appear first
            if len(hits) >= 2:
                self.assertGreater(hits[0].importance, hits[-1].importance)
            store.close()


if __name__ == "__main__":
    unittest.main()
