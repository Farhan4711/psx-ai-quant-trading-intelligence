/**
 * `@psx/shared` — single source of truth for the FE↔BE contract.
 *
 * Usage from psx-web:
 *
 *   import {
 *     createApiClient,
 *     ApiError,
 *     type CurrentUser,
 *     type PortfolioSummary,
 *   } from "@psx/shared";
 *
 *   const api = createApiClient({ baseUrl: process.env.NEXT_PUBLIC_API_URL });
 *   const me = await api.get<CurrentUser>("/api/v1/auth/me");
 */

export * from "./types";
export * from "./client";
