# Project Risk Register - Orion Tech Platform

**Last Updated**: April 13, 2026

## Active Risks

### R-001: Third-party API Dependency Stability
- **Category**: Technical
- **Probability**: Medium
- **Impact**: High
- **Description**: Our integration with external payment gateway has experienced intermittent outages in the past month. This could affect checkout functionality during peak traffic periods.
- **Mitigation**: Implementing circuit breaker pattern and fallback to secondary payment provider.
- **Owner**: Marcus Liu
- **Status**: Active - mitigation in progress

### R-002: Database Migration Complexity
- **Category**: Technical
- **Probability**: Low
- **Impact**: Critical
- **Description**: Planned migration from PostgreSQL 12 to 14 involves schema changes that could cause downtime or data inconsistencies if not executed properly.
- **Mitigation**: Full rehearsal in staging environment, scheduled during low-traffic window, comprehensive rollback plan prepared.
- **Owner**: Sarah Chen
- **Status**: Active - migration scheduled for April 20

### R-003: Key Developer Availability
- **Category**: Resource
- **Probability**: Medium
- **Impact**: Medium
- **Description**: Lead backend developer (James Park) has upcoming medical leave for 2 weeks starting April 28. This overlaps with critical Q2 feature delivery.
- **Mitigation**: Knowledge transfer sessions scheduled, documentation updates in progress, backup developer (Marcus Liu) designated.
- **Owner**: Project Manager
- **Status**: Active - mitigation underway

### R-004: Regulatory Compliance Deadline
- **Category**: Legal/Compliance
- **Probability**: Low
- **Impact**: High
- **Description**: New data privacy regulations come into effect May 15. Our current data retention policies may not be fully compliant.
- **Mitigation**: Legal team reviewing requirements, engineering to implement automated data purging by May 1.
- **Owner**: Legal + Engineering
- **Status**: Active - on track for May 1 completion

## Closed Risks

### R-005: Authentication Service Scalability
- **Category**: Technical
- **Probability**: High (at time of identification)
- **Impact**: Critical
- **Description**: Load testing revealed authentication service could not handle expected Q2 traffic surge.
- **Resolution**: Implemented horizontal scaling and connection pooling. Load tests now show 3x capacity margin.
- **Closed Date**: April 10, 2026
