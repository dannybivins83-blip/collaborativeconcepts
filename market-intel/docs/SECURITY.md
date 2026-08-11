# Security

## Today

- **Secrets via environment only.** No credentials in code, fixtures, tests or
  docs. `.env` is gitignored; `.env.example` carries names, never values.
- **No secret ever reaches the browser.** The web page talks only to our API.
- **Parameterised SQL everywhere.** No string-interpolated user input; table
  names in helpers are internal constants, never request data.
- **Input validation at the API boundary.** Unknown screener filters are
  rejected (400) rather than silently ignored; path params are regex-constrained.
- **Static file serving is path-traversal guarded** (resolved path must stay
  inside `apps/web`).
- **Outbound politeness is enforced**, not documented: contact User-Agent
  required, rate limiter, fail-fast on 4xx.
- **Errors do not leak internals** to clients beyond an exception type + message;
  no stack traces are returned.

## Required before any real user touches this

Authentication + session handling · password hashing (argon2id/PBKDF2 with
per-user salt) · authorization (row-level: a user sees only their watchlists) ·
API keys with scopes + revocation · rate limiting per key · CORS narrowed from
`*` · audit logging · log redaction · dependency scanning · TLS termination ·
backup/restore for the raw layer.

## Data handling

Raw source records may contain third-party content. Retention, redistribution
and per-source kill switches are governed by DATA_LICENSING.md.
