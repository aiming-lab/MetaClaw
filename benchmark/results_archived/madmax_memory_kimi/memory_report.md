# Madmax (RL+Skills+Memory) Benchmark Report

Generated: 2026-03-17 19:13:13
Benchmark duration: 24472.1s (407.9min)

## Overview

| Metric | Value |
|--------|-------|
| Active memories | 15 |
| Total memories | 210 |
| Scope | default |

## Memory Type Distribution

| Type | Count | Ratio |
|------|-------|-------|
| procedural_observation | 11 | 73.3% |
| project_state | 2 | 13.3% |
| preference | 1 | 6.7% |
| working_summary | 1 | 6.7% |

## Health Check

- **scope_id**: default
- **passed**: True
- **checks**:
  - integrity: {'passed': True, 'issues': []}
  - health_score: {'passed': True, 'score': 78.9}
  - staleness: {'passed': True, 'stale_count': 0}
  - duplicates: {'passed': True, 'duplicate_pairs': 0}
  - db_size: {'passed': True, 'size_mb': 0.0}
- **issues**:
- **summary**: All checks passed

## System Summary

- **schema_version**: 6
- **scopes**:
  - {"scope_id": "default", "active": 15, "total": 210}
- **scope_count**: 1
- **total_active_memories**: 15
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
  - size_bytes: 2314240
  - size_mb: 2.21
  - page_count: 570
  - page_size: 4096
  - freelist_pages: 3
  - freelist_ratio: 0.0053
- **integrity**:
  - valid: True
  - issues: []
  - orphaned_links: 0
  - orphaned_watches: 0
  - orphaned_annotations: 0
  - dangling_superseded: 0

