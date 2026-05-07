# psx-shared — Shared Types & Schemas

Single source of truth for data contracts shared between `psx-web` (TypeScript)
and `psx-api` / `psx-inference` (Python).

## Contents

| Directory | Description |
|---|---|
| `typescript/` | TypeScript interfaces and Zod schemas consumed by psx-web |
| `python/` | Pydantic v2 models mirroring the TypeScript types |

## Principle

Any type that crosses the API boundary (request/response body) is defined here
and imported by both sides. This prevents the frontend and backend from drifting
out of sync silently.

## Directory Structure (to be created in Phase 1)

```
psx-shared/
├── typescript/
│   ├── src/
│   │   ├── securities.ts       # Security, OHLCV, Sector types
│   │   ├── portfolio.ts        # Portfolio, Transaction, Holding types
│   │   ├── auth.ts             # User, Session types
│   │   └── index.ts
│   ├── package.json
│   └── tsconfig.json
└── python/
    ├── psx_shared/
    │   ├── securities.py
    │   ├── portfolio.py
    │   └── auth.py
    └── pyproject.toml
```
