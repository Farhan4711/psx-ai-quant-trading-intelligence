/**
 * Typed `apiFetch` — replaces the ad-hoc copies in every
 * `psx-web/src/lib/api/*.ts` with a single shared implementation.
 *
 * Design choices:
 * - Browser-only `fetch` (we don't ship a Node polyfill — Next 14
 *   has both server-side and client-side fetch, both built-in).
 * - `credentials: "include"` is the default because every authed
 *   request needs the HTTP-only `psx_session` cookie.
 * - On non-2xx we throw `ApiError` with the structured body so
 *   callers can branch on `err.status` / `err.body.detail` instead
 *   of parsing strings.
 */

import type { ApiErrorBody } from "./types";

export class ApiError extends Error {
  status: number;
  body: ApiErrorBody;
  constructor(status: number, body: ApiErrorBody) {
    super(body.detail || `Request failed with ${status}`);
    this.name = "ApiError";
    this.status = status;
    this.body = body;
  }
}

export interface ApiClientOptions {
  /** Base URL of the FastAPI service. Required. */
  baseUrl: string;
}

export type RequestOptions = Omit<RequestInit, "body"> & {
  /** Body is auto-serialised to JSON when provided. */
  json?: unknown;
  /** Override credentials (defaults to "include"). */
  credentials?: RequestCredentials;
};

export function createApiClient({ baseUrl }: ApiClientOptions) {
  async function request<T>(path: string, opts: RequestOptions = {}): Promise<T> {
    const { json, credentials = "include", headers, ...rest } = opts;
    const init: RequestInit = {
      ...rest,
      credentials,
      headers: {
        Accept: "application/json",
        ...(json !== undefined ? { "Content-Type": "application/json" } : {}),
        ...headers,
      },
      body: json !== undefined ? JSON.stringify(json) : (rest as RequestInit).body,
    };
    const res = await fetch(`${baseUrl}${path}`, init);
    if (!res.ok) {
      let body: ApiErrorBody;
      try {
        body = (await res.json()) as ApiErrorBody;
      } catch {
        body = { detail: res.statusText };
      }
      throw new ApiError(res.status, body);
    }
    // 204 No Content
    if (res.status === 204) return undefined as T;
    return (await res.json()) as T;
  }

  return {
    request,
    get: <T>(path: string, opts?: RequestOptions) =>
      request<T>(path, { ...opts, method: "GET" }),
    post: <T>(path: string, json?: unknown, opts?: RequestOptions) =>
      request<T>(path, { ...opts, method: "POST", json }),
    patch: <T>(path: string, json?: unknown, opts?: RequestOptions) =>
      request<T>(path, { ...opts, method: "PATCH", json }),
    put: <T>(path: string, json?: unknown, opts?: RequestOptions) =>
      request<T>(path, { ...opts, method: "PUT", json }),
    delete: <T>(path: string, opts?: RequestOptions) =>
      request<T>(path, { ...opts, method: "DELETE" }),
  };
}

export type ApiClient = ReturnType<typeof createApiClient>;
