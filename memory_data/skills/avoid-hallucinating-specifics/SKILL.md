---
name: avoid-hallucinating-specifics
description: "Use this skill when you are about to state a specific API endpoint, library version, function signature, file path, or configuration value that you are not certain about. Prevents confident hallucination by requiring explicit uncertainty flags and placeholder values instead of guesses."
---

# Avoid Hallucinating Specifics

**High-risk categories for hallucination:**
- Specific API endpoint URLs or request/response schemas.
- Library version numbers and feature availability per version.
- Names of real people, organizations, or publications.
- File paths and environment-specific configuration.

**Prevention:**
- If unsure of a specific value, say so explicitly.
- Recommend the user verify against official documentation.
- Use `<version>` or `<your-endpoint>` as placeholders rather than guessing.

**Anti-pattern:** Confidently stating a URL or function signature that sounds right but does not exist.
