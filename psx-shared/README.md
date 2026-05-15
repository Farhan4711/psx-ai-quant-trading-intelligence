# psx-shared — Shared types & API client

Single source of truth for the data contract between `psx-web`
(TypeScript) and `psx-api` (Python FastAPI).

## Layout

```
psx-shared/
├── typescript/
│   ├── src/
│   │   ├── types.ts          # Curated, hand-written types (the contract)
│   │   ├── client.ts         # createApiClient() + ApiError
│   │   ├── generated.ts      # Auto-generated from OpenAPI (refresh with `pnpm gen`)
│   │   └── index.ts          # Public surface
│   ├── scripts/
│   │   └── generate.mjs      # Pulls /openapi.json from a running API
│   ├── package.json          # Workspace package `@psx/shared`
│   └── tsconfig.json
└── python/                   # (Future) Pydantic mirrors of the curated types
```

## Usage from psx-web

```ts
import {
  createApiClient,
  ApiError,
  type CurrentUser,
  type PortfolioSummary,
} from "@psx/shared";

const api = createApiClient({ baseUrl: process.env.NEXT_PUBLIC_API_URL! });

const me = await api.get<CurrentUser>("/api/v1/auth/me");
```

## Regenerating from a running API

```bash
# 1. Start the API in one shell
cd psx-api
uvicorn psx_api.main:app --reload --port 8000

# 2. In another shell
pnpm --filter @psx/shared gen

# Commits the diff in psx-shared/typescript/src/generated.ts —
# code review surfaces "the BillingService schema changed" naturally.
```

## Principle

- **`types.ts` is canonical.** Hand-curated, documented, the surface
  the rest of the codebase imports.
- **`generated.ts` is verbose.** Covers every DTO in the OpenAPI
  surface; useful for less-trafficked endpoints. Don't import it
  directly unless `types.ts` doesn't already cover the type.
- **Python side is deferred.** Once `psx-ingest` and `psx-api`
  genuinely need to share Python code (today they duplicate
  `news/extract.py` and `news/sentiment.py`), we'll add a
  `psx-shared/python/` package and wire path deps in their
  `pyproject.toml` files.
