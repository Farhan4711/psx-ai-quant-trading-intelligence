# Security

How PSX AI protects user data and what we do when something goes wrong.

## Reporting a vulnerability

**Email:** security@psxai.example
**Encrypt with:** [PGP_FINGERPRINT_PLACEHOLDER]

Please **do not** open public GitHub issues for security vulnerabilities.
We respond within **72 hours** to confirmed-real reports. Critical
issues are patched within 7 days; lower-severity within 30. We don't
yet run a paid bug bounty, but valid reports get public acknowledgement
(with permission) and a swag bundle once we have swag.

---

## What we promise

### Authentication

- **Argon2id** password hashing with sensible cost params (m=64MiB, t=3, p=4)
- Session tokens are 256-bit URL-safe random; we store the SHA-256
  hash, the raw token only ever exists in an HTTP-only `Secure`
  `SameSite=Lax` cookie
- Optional **TOTP 2FA** with a 6-digit verification code on a 30s window
- Login rate limiting: 5 attempts per 15 min per (IP × email), surfaced
  as a 429 with a clear retry-after

### Transport + headers

- TLS-only in production (Caddy auto-provisions Let's Encrypt)
- `Strict-Transport-Security` with includeSubDomains
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Permissions-Policy: geolocation=(), microphone=(), camera=()`

### Application

- All DB queries are parameterised via SQLAlchemy (no string concat)
- CORS allow-list narrowed to the production domain (`ALLOWED_ORIGINS`)
- Request bodies validated by Pydantic v2 with strict field types
- Path-param routing means no query-string injection vectors on
  endpoints that take user IDs / portfolio IDs
- Every per-user table query is filtered by `user_id` from the session;
  spot-checks documented in [TESTING.md](TESTING.md)

### Storage

- Postgres in a private network, no public IP
- Backups encrypted at rest, retained 30 days, rotated to Hetzner
  Storage Box for off-site
- Sensitive columns (`password_hash`, `token_hash`) never leave the API
- Redis used for **ephemeral** state only (rate limits, cache); never
  for primary data

### Operational

- Sentry alerts on every unhandled exception
- `/health/sentry-check` endpoint deliberately raises (non-prod only)
  so we can verify the alert pipeline
- Structured JSON logs forwarded to **[LOG_AGGREGATION_SERVICE]**
- Quarterly backup-restore drill

---

## SOC 2 readiness (not certified)

We're tracking SOC 2 Type II controls because investors and B2B
customers ask. We're not certified yet. Current state of the relevant
control families:

| Control family | Status |
|---|---|
| Access control (least-privilege roles, MFA on admin) | In place for engineering |
| Change management (PR review, CI gates) | In place — see web-ci.yml + api-ci.yml |
| Risk assessment | Documented annually; next review **[NEXT_RISK_REVIEW_DATE]** |
| Vendor risk (subprocessors) | Tracked in `legal/SUBPROCESSORS.md` (TODO) |
| Logging + monitoring | Sentry + JSON logs; SIEM not yet in place |
| Incident response | Playbook drafted; needs tabletop exercise |
| Backup + DR | Postgres dumps nightly; restore tested quarterly |
| Encryption | TLS in transit; AES-256 at rest on Postgres + backups |

Honest gap list:

- No formal **SIEM** yet (only Sentry + JSON logs)
- No **vulnerability-management program** (scanning is ad-hoc until
  scripts/security-scan.sh runs in CI)
- No **third-party pentest** report yet (planned for v1 launch)
- No **vendor risk-assessment** documents on subprocessors
- No **employee security training** records (small team)

---

## Automated scans

We don't run scheduled CI for the security scan — the project is on
the GitHub free tier and we'd rather have one well-rehearsed local
flow than a half-trusted automated one. Run the scan manually before
each release:

```bash
# Unix / macOS
./scripts/security-scan.sh

# Windows
.\scripts\security-scan.ps1
```

Both scripts execute the same four checks with matching exit codes:

1. **pip-audit** — Python dependencies for known CVEs
2. **pnpm audit** — Node dependencies (high+ severity)
3. **ruff bandit lint** — flag dangerous Python patterns (eval,
   subprocess shell=True, hardcoded passwords). Already integrated as
   the `S` rule set in `pyproject.toml`.
4. **basic header checks** — verify the production endpoint returns
   the expected security headers (set `PROD_URL` env var).

For the smaller, faster checks that should run **every commit**, we
ship `.pre-commit-config.yaml`. Install once:

```bash
pip install pre-commit
pre-commit install
```

The hook runs ruff + ruff-format + detect-secrets + private-key
detection + large-file blocker on every `git commit`. Bypass with
`--no-verify` only when you've manually verified the failing files
are safe.

---

## What we'd do in an incident

1. **Triage** (within 1 hour of detection)
   - Acknowledge the report internally
   - Estimate blast radius (affected users, data types, time window)
   - Decide: contain, mitigate, or eradicate
2. **Contain** (within 4 hours)
   - Rotate compromised credentials (DB users, API tokens, session
     secret keys)
   - Lock affected accounts or trigger forced password reset
   - Disable affected endpoints if needed
3. **Notify** (within 72 hours of confirmed scope per Pakistani data
   protection guidance)
   - Affected users, by email, with concrete facts and next steps
   - Internal Slack #incidents channel for active updates
4. **Eradicate + recover** (within 7 days)
   - Patch the root cause
   - Verify no persistence
   - Restore from clean backups if data integrity was compromised
5. **Post-mortem** (within 14 days)
   - Blameless review; write up in `legal/INCIDENTS.md`
   - Publish public version if user data was affected
