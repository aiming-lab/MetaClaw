---
name: secure-code-review
description: "Use this skill when reviewing or auditing code for security issues — especially code that handles user input, authentication, SQL queries, file I/O, or HTTP requests. Use when someone asks to 'review this for security', 'check for vulnerabilities', or 'is this code safe'. Checks for SQL injection, XSS, hardcoded secrets, missing auth checks, and insecure dependencies."
---

# Secure Code Review Checklist

**Input Validation:**
- Never trust user-supplied input; validate type, length, and format at boundaries.
- Use parameterized queries — never string-interpolate SQL.
- Sanitize before rendering HTML to prevent XSS.

**Secrets & Credentials:**
- No hardcoded passwords, API keys, or tokens in source code.
- Use environment variables or a secrets manager.
- Check `.gitignore` before adding any config files.

**Dependencies:**
- Pin dependency versions; audit with `pip audit` or `npm audit`.
- Minimize surface area: remove unused packages.

**Auth:**
- Verify authorization on every protected endpoint, not just at login.
- Use short-lived tokens; implement refresh flows.
