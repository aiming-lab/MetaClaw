---
name: secrets-management
description: "Use this skill when handling API keys, passwords, tokens, private keys, or any sensitive credential. Trigger on the words 'key', 'token', 'password', 'secret', 'credential', or 'env var' in the task. Prevents hardcoding secrets, configures .gitignore, sets up environment variable loading, and recommends secrets managers for production."
---

# Secrets Management

**Rules:**
1. **Never** hardcode secrets in source files, configs committed to git, or logs.
2. Use environment variables for local development (`python-dotenv`).
3. Use a secrets manager (AWS Secrets Manager, HashiCorp Vault, 1Password CLI) in production.
4. Add `.env` and `*.pem` to `.gitignore` before the first commit.
5. Rotate secrets immediately if they are exposed (leaked in a commit, log, or error message).

**Scanning:** Use `ggshield`, `truffleHog`, or `git-secrets` in CI to block secret commits.

**Anti-patterns:**
- `os.environ.get('KEY', 'hardcoded_default')` in production code.
- Logging full request/response bodies that may contain tokens.
