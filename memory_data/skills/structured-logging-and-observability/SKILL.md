---
name: structured-logging-and-observability
description: "Use this skill when adding logging, monitoring, or observability to a production service, API, pipeline, or background worker. Use when someone asks to 'add logging', 'set up monitoring', 'make this debuggable', or 'add a health check'. Configures structured JSON logs with correct log levels, exposes key metrics (rate/error/latency), and adds a /health endpoint."
---

# Structured Logging and Observability

**Log levels:**
- `DEBUG`: detailed diagnostic (off in production)
- `INFO`: normal operation milestones
- `WARNING`: recoverable unexpected state
- `ERROR`: operation failed, action needed

**Structured logs (JSON) over free-form text:**
```python
import structlog
log = structlog.get_logger()
log.info("request_complete", method="POST", path="/api/data", status=200, latency_ms=42)
```

**Metrics to expose:** request rate, error rate, latency (p50/p95/p99), queue depth.

**Health check endpoint:** `/health` returning `{"status": "ok"}` — required for load balancers.

**Anti-pattern:** Logging only on error; you can't diagnose what you didn't observe.
