---
name: input-validation-and-sanitization
description: "Use this skill when building API endpoints, form handlers, CLI tools, or any function that accepts user-supplied data. Validate type, range, length, and format at the system boundary; prevent SQL injection with parameterized queries; prevent XSS with HTML escaping; prevent path traversal with canonical path checks."
---

# Input Validation and Sanitization

**Validation principles:**
- Validate at the system boundary (API layer, form handler) — not deep in business logic.
- Validate type, range, length, and format explicitly.
- Reject unexpected input by default (allowlist > denylist).

**SQL injection prevention:** Always use parameterized queries or an ORM.

**XSS prevention:** Escape HTML output; use Content-Security-Policy headers; avoid `innerHTML` with user data.

**Path traversal prevention:** Resolve paths to canonical form and verify they are under the expected directory.

```python
import os
base = '/allowed/dir'
canonical = os.path.realpath(os.path.join(base, user_input))
assert canonical.startswith(base + os.sep)
```
