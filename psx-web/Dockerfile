# PSX Web — Multi-stage Dockerfile (Next.js standalone output)
# Build context is the repo ROOT (not psx-web/), because psx-web depends on
# the @psx/shared workspace package at psx-shared/typescript and the pnpm
# lockfile lives at the workspace root. See docker-compose.prod.yml.
# Stage 1: deps — install pnpm + node_modules for the whole workspace
# Stage 2: builder — build the app
# Stage 3: runtime — minimal image with only the standalone server
#
# Next.js infers the output-tracing root from the pnpm workspace above
# psx-web/, so `output: standalone` nests its build output under
# psx-web/.next/standalone/psx-web/ instead of psx-web/.next/standalone/.

FROM node:20-alpine AS base
RUN corepack enable && corepack prepare pnpm@9.15.2 --activate

# ─── deps ─────────────────────────────────────────────────────────────────────
FROM base AS deps
WORKDIR /app
COPY pnpm-workspace.yaml pnpm-lock.yaml ./
COPY psx-web/package.json ./psx-web/package.json
COPY psx-shared/typescript/package.json ./psx-shared/typescript/package.json
RUN pnpm install --frozen-lockfile

# ─── builder ──────────────────────────────────────────────────────────────────
FROM base AS builder
WORKDIR /app
COPY --from=deps /app ./
COPY . .

# Sentry source-map upload runs only if SENTRY_AUTH_TOKEN is provided at build time
ARG NEXT_PUBLIC_API_URL
ARG NEXT_PUBLIC_SENTRY_DSN
ARG SENTRY_AUTH_TOKEN
ARG SENTRY_ORG
ARG SENTRY_PROJECT
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL \
    NEXT_PUBLIC_SENTRY_DSN=$NEXT_PUBLIC_SENTRY_DSN \
    SENTRY_AUTH_TOKEN=$SENTRY_AUTH_TOKEN \
    SENTRY_ORG=$SENTRY_ORG \
    SENTRY_PROJECT=$SENTRY_PROJECT \
    NEXT_TELEMETRY_DISABLED=1

RUN pnpm --filter psx-web build

# ─── runtime ──────────────────────────────────────────────────────────────────
FROM node:20-alpine AS runtime
WORKDIR /app

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME=0.0.0.0

# Non-root user
RUN addgroup -g 1001 -S nodejs && adduser -S -u 1001 -G nodejs nextjs

# Standalone output ships only the runtime files Next needs
COPY --from=builder --chown=nextjs:nodejs /app/psx-web/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/psx-web/.next/static ./psx-web/.next/static
COPY --from=builder --chown=nextjs:nodejs /app/psx-web/public ./psx-web/public

USER nextjs

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost:3000/ || exit 1

CMD ["node", "psx-web/server.js"]
