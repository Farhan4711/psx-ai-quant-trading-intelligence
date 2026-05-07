# ADR-001: Why Next.js + FastAPI Split (Not a Monolith)

**Date:** 2026-05-07
**Status:** Accepted

---

## Context

The application needs a web frontend and an API backend. The options were:

1. **Full-stack Next.js** — API routes inside the Next.js app, no separate backend
2. **Next.js frontend + FastAPI backend (chosen)**
3. **Django or Flask instead of FastAPI**

## Decision

Separate Next.js frontend from a Python FastAPI backend.

## Rationale

| Concern | Full-stack Next.js | Next.js + FastAPI |
|---|---|---|
| ML model serving | Forces Node.js ML stack (inferior) | Python is the ML ecosystem |
| Data ingestion workers | Would need a separate Python process anyway | Celery workers co-located with API |
| Type safety across boundary | Next.js API routes share types natively | Shared types via psx-shared — explicit but safe |
| Deployment flexibility | Vercel handles frontend; backend needs separate infra | Clean separation: Vercel for frontend, Hetzner for backend |
| Team split | N/A (solo founder) | Frontend/backend work streams are independent |

The deciding factor: **the ML and data pipeline is irreducibly Python**. Forcing a Node.js API layer on top would create an impedance mismatch between the API and every background worker, training script, and indicator computation.

## Consequences

- **psx-web** is a pure frontend — no database connections, no ML code, no secrets beyond the API URL and Auth.js secret
- **psx-api** is the only service that connects to Postgres/Redis directly
- Type safety at the API boundary is enforced via `psx-shared/` types
- CORS must be configured correctly in production (API allows only the frontend's domain)
- Two CI/CD pipelines to maintain instead of one
