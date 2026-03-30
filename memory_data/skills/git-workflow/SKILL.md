---
name: git-workflow
description: "Use this skill when making commits, creating branches, opening pull requests, resolving merge conflicts, or reviewing diffs. Enforces imperative commit messages, focused single-purpose PRs, and safe staging practices — never force-pushing to shared branches or skipping hooks."
---

# Git Workflow Best Practices

**Commits:**
- Write commit messages in imperative mood: `Add feature X`, not `Added feature X`.
- One logical change per commit. Do not bundle unrelated changes.
- Stage specific files (`git add <file>`), not `git add .` blindly.

**Branches:**
- Branch from the latest main/master: `git checkout -b feature/my-change`.
- Keep branches short-lived; merge or rebase frequently.

**Pull Requests:**
- Include a short description of *why*, not just *what*.
- Reference related issues (`Closes #123`).
- Keep PRs focused — one feature or fix per PR.

**Never:** force-push to shared branches, skip hooks with `--no-verify`, or commit secrets.
