# Skills+Memory Benchmark Report

Generated: 2026-03-17 12:18:55
Benchmark duration: 9143.0s (152.4min)

## Overview

| Metric | Value |
|--------|-------|
| Active memories | 19 |
| Total memories | 245 |
| Scope | default |

## Memory Type Distribution

| Type | Count | Ratio |
|------|-------|-------|
| procedural_observation | 17 | 89.5% |
| project_state | 1 | 5.3% |
| working_summary | 1 | 5.3% |

## Health Check

- **scope_id**: default
- **passed**: True
- **checks**:
  - integrity: {'passed': True, 'issues': []}
  - health_score: {'passed': True, 'score': 72.4}
  - staleness: {'passed': True, 'stale_count': 0}
  - duplicates: {'passed': True, 'duplicate_pairs': 0}
  - db_size: {'passed': True, 'size_mb': 0.0}
- **issues**: 
- **summary**: All checks passed

## System Summary

- **schema_version**: 6
- **scope_count**: 1
- **total_active_memories**: 19
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
  - size_bytes: 2580480
  - size_mb: 2.46
  - page_count: 662
  - page_size: 4096
  - freelist_pages: 3
  - freelist_ratio: 0.0045
- **integrity**:
  - valid: True
  - issues: []
  - orphaned_links: 0
  - orphaned_watches: 0
  - orphaned_annotations: 0
  - dangling_superseded: 0

