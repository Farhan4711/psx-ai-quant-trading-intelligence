import { createApiClient } from "@psx/shared";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const api = createApiClient({ baseUrl: API_URL });

// ── Alerts ─────────────────────────────────────────────────────────────
// `SuspiciousDay` here is the UI-side extended view; the curated
// `@psx/shared` version is the narrow shape stable enough to be public.

export interface SuspiciousDay {
  id: string;
  symbol: string;
  alert_date: string;
  alert_type: "pump" | "dump";
  severity: "low" | "medium" | "high";
  vol_spike: string;
  price_change_pct: string;
  anomaly_score: string | null;
  has_news_context: boolean;
  explanation: string;
  created_at: string;
}

export interface SuspiciousState {
  has_active_alert: boolean;
  latest: SuspiciousDay | null;
}

export const fetchAlertsForUser = (limit = 50) =>
  api.get<SuspiciousDay[]>(`/api/v1/alerts?limit=${limit}`);

export const fetchSuspiciousState = (symbol: string) =>
  api.get<SuspiciousState>(`/api/v1/securities/${symbol}/suspicious-state`);

// ── News pulse ─────────────────────────────────────────────────────────

export interface ArticleWithSentiment {
  id: string;
  source: string;
  url: string;
  headline: string;
  published_at: string;
  polarity: string | null;
  event_type: string | null;
}

export interface NewsPulse {
  symbol: string;
  as_of_date: string;
  score: number;
  article_count: number;
  weighted_count: number;
  top_articles: ArticleWithSentiment[];
  explainer: string;
}

export const fetchNewsPulse = (symbol: string) =>
  api.get<NewsPulse>(`/api/v1/securities/${symbol}/news/pulse`);

// ── Tax simulator ─────────────────────────────────────────────────────

export interface TaxSimulatorResult {
  date_from: string;
  date_to: string;
  sells_processed: number;
  total_gross_gain_pkr: string;
  total_brokerage_pkr: string;
  total_fed_pkr: string;
  total_cvt_pkr: string;
  filer: { cgt_pkr: string; net_realised_pkr: string };
  non_filer: { cgt_pkr: string; net_realised_pkr: string };
  filer_savings_pkr: string;
  filer_savings_pct: string;
  narrative: string;
}

export const fetchTaxSimulation = (dateFrom?: string, dateTo?: string) => {
  const qs = new URLSearchParams();
  if (dateFrom) qs.set("date_from", dateFrom);
  if (dateTo) qs.set("date_to", dateTo);
  const suffix = qs.toString() ? `?${qs.toString()}` : "";
  return api.get<TaxSimulatorResult>(`/api/v1/tax-simulator${suffix}`);
};
