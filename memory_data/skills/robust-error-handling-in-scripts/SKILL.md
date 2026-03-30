---
name: robust-error-handling-in-scripts
description: "Use this skill when writing or reviewing shell scripts, Python automation scripts, cron jobs, or any unattended batch process. Apply when someone asks to 'add error handling', 'make this script fail safely', or 'handle failures in my automation'. Ensures failures are detected with set -euo pipefail, logged with tracebacks, and retried where appropriate."
---

# Robust Error Handling in Scripts

**Shell scripts:**
```bash
set -euo pipefail  # Exit on error, undefined var, pipe failure
trap 'echo "Failed at line $LINENO"' ERR
```

**Python scripts:**
```python
import logging, sys
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
try:
    main()
except Exception as e:
    logging.exception("Unhandled error: %s", e)
    sys.exit(1)
```

**Retry with backoff** for transient network/API failures:
```python
from tenacity import retry, stop_after_attempt, wait_exponential
@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
def call_api(): ...
```
