# RL-only+Memory Benchmark Report

Generated: 2026-03-18 09:30:45
Benchmark duration: 26726.4s (445.4min)

## Overview

| Metric | Value |
|--------|-------|
| Active memories | 71 |
| Total memories | 676 |
| Scope | default |

## Memory Type Distribution

| Type | Count | Ratio |
|------|-------|-------|
| procedural_observation | 43 | 60.6% |
| semantic | 20 | 28.2% |
| preference | 5 | 7.0% |
| project_state | 2 | 2.8% |
| working_summary | 1 | 1.4% |

## Health Check

- **scope_id**: default
- **passed**: True
- **checks**:
  - integrity: {'passed': True, 'issues': []}
  - health_score: {'passed': True, 'score': 79.3}
  - staleness: {'passed': True, 'stale_count': 0}
  - duplicates: {'passed': True, 'duplicate_pairs': 0}
  - db_size: {'passed': True, 'size_mb': 0.0}
- **issues**:
- **summary**: All checks passed

## System Summary

- **schema_version**: 6
- **scopes**:
  - {"scope_id": "default", "active": 71, "total": 676}
- **scope_count**: 1
- **total_active_memories**: 71
- **embedder**:
  - enabled: True
  - mode: semantic
  - type: SentenceTransformerEmbedder
  - dimensions: 384
  - model: all-MiniLM-L6-v2
  - available: True
- **policy**:
  - retrieval_mode: hybrid
  - max_injected_units: 10
  - max_injected_tokens: 1500
- **db**:
  - size_bytes: 7098368
  - size_mb: 6.77
  - page_count: 1740
  - page_size: 4096
  - freelist_pages: 3
  - freelist_ratio: 0.0017
- **integrity**:
  - valid: True
  - issues: []
  - orphaned_links: 0
  - orphaned_watches: 0
  - orphaned_annotations: 0
  - dangling_superseded: 0

