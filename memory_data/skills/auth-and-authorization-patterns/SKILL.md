---
name: auth-and-authorization-patterns
description: "Use this skill when implementing login flows, JWT token issuance, OAuth2/OIDC integrations, session management, or role-based access control (RBAC). Covers password hashing, token lifetimes, PKCE, claim validation, and least-privilege enforcement."
---

# Auth & Authorization Patterns

**Authentication (who are you?):**
- Use a battle-tested library — do not roll your own crypto.
- Hash passwords with bcrypt/argon2; never MD5/SHA1 for passwords.
- Use short-lived JWTs (15–60 min) with refresh tokens; store refresh tokens securely.
- Implement MFA for sensitive operations.

**Authorization (what can you do?):**
- Check authorization on every request, not just at login.
- Enforce RBAC or ABAC at the service layer, not the UI.
- Apply principle of least privilege: grant minimal permissions needed.

**OAuth2 / OIDC:**
- Use the Authorization Code flow with PKCE for user-facing apps.
- Validate `iss`, `aud`, `exp`, and `nonce` claims on every token.

**Session management:**
- Regenerate session ID after login (session fixation prevention).
- Set `HttpOnly` and `Secure` flags on session cookies.
