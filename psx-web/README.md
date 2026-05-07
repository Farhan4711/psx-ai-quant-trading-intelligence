# psx-web — Next.js Frontend

Next.js 14+ App Router frontend for the PSX AI Trading Intelligence platform.

## Tech Stack

- **Framework:** Next.js 14+ (App Router)
- **Language:** TypeScript (strict mode)
- **Styling:** TailwindCSS + shadcn/ui
- **Charts:** TradingView Lightweight Charts (price), Apache ECharts (dashboards)
- **State:** TanStack Query (server state), Zustand (client state)
- **Forms:** React Hook Form + Zod
- **Auth:** Auth.js v5
- **Testing:** Vitest (unit), Playwright (E2E)
- **Linting:** ESLint, tsc strict

## Prerequisites

- Node.js 20+
- pnpm 9+ (`npm install -g pnpm`)
- Running `psx-api` backend (see `../psx-api/README.md`)

## Local Setup

```bash
cd psx-web
cp .env.example .env.local
pnpm install
pnpm dev
```

App runs at http://localhost:3000

## Environment Variables

See `.env.example` for all required variables. Never commit `.env.local`.

## Scripts

| Command | Description |
|---|---|
| `pnpm dev` | Start dev server with hot reload |
| `pnpm build` | Production build |
| `pnpm lint` | ESLint check |
| `pnpm type-check` | tsc strict check (no emit) |
| `pnpm test` | Vitest unit tests |
| `pnpm test:e2e` | Playwright E2E suite |
| `pnpm test:coverage` | Unit tests with coverage report |

## Directory Structure (to be created in Phase 1)

```
psx-web/
├── app/                    # Next.js App Router pages and layouts
│   ├── (auth)/             # Auth pages: login, signup, verify-email
│   ├── (app)/              # Protected app pages
│   │   ├── dashboard/
│   │   ├── stocks/[symbol]/
│   │   ├── portfolio/
│   │   ├── watchlist/
│   │   └── sectors/
│   └── api/                # Next.js API routes (auth callbacks only)
├── components/
│   ├── ui/                 # shadcn/ui base components
│   ├── charts/             # TradingView and ECharts wrappers
│   ├── portfolio/
│   ├── stocks/
│   └── layout/
├── lib/
│   ├── api/                # TanStack Query hooks + fetch wrappers
│   ├── auth/               # Auth.js config
│   ├── store/              # Zustand stores
│   └── utils/
├── types/                  # TypeScript types (shared from psx-shared)
└── tests/
    ├── unit/
    └── e2e/
```
