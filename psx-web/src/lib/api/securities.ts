const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    credentials: "include",
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });
  if (!res.ok) {
    const err = (await res.json().catch(() => ({ detail: res.statusText }))) as { detail?: string };
    throw new Error(err.detail ?? "Request failed");
  }
  return res.json() as Promise<T>;
}

export interface Security {
  id: number;
  symbol: string;
  company_name: string;
  sector: string;
  is_kmi_compliant: boolean;
  is_kse100: boolean;
  is_kse30: boolean;
  market_cap_pkr: number | null;
  shares_outstanding: number | null;
  is_active: boolean;
  updated_at: string;
}

export interface SecuritiesListResponse {
  items: Security[];
  total: number;
  page: number;
  page_size: number;
  has_next: boolean;
}

export interface OhlcvItem {
  symbol: string;
  date: string;
  open: string | null;
  high: string | null;
  low: string | null;
  close: string | null;
  volume: number | null;
  value_pkr: string | null;
  adjusted_close: string | null;
}

export interface OhlcvResponse {
  symbol: string;
  interval: string;
  items: OhlcvItem[];
  total: number;
}

export interface Fundamentals {
  symbol: string;
  week_52_high: string | null;
  week_52_low: string | null;
  avg_volume_30d: number | null;
  market_cap_pkr: number | null;
  shares_outstanding: number | null;
  pe_ratio: string | null;
  pb_ratio: string | null;
  eps: string | null;
  roe: string | null;
  dividend_yield: string | null;
}

export interface Announcement {
  id: number;
  symbol: string;
  action_type: string;
  announcement_date: string;
  ex_date: string | null;
  record_date: string | null;
  payment_date: string | null;
  amount_per_share: string | null;
  ratio_numerator: number | null;
  ratio_denominator: number | null;
}

export interface IndexPerformance {
  name: string;
  constituent_count: number;
  last_close_date: string | null;
  change_1d_pct: string | null;
  change_1w_pct: string | null;
  change_1m_pct: string | null;
  change_ytd_pct: string | null;
}

export interface WatchlistItem {
  symbol: string;
  company_name: string;
  sector: string;
  is_kmi_compliant: boolean;
  note: string | null;
  sort_order: number;
  added_at: string;
}

export interface Quote {
  symbol: string;
  last_close: string | null;
  prev_close: string | null;
  last_date: string | null;
  change: string | null;
  change_pct: string | null;
}

export interface QuotesResponse {
  items: Quote[];
}

// -- Fetchers ---------------------------------------------------------------

export const fetchSecurities = (params?: {
  page?: number;
  page_size?: number;
  sector?: string;
  kmi_only?: boolean;
  kse100_only?: boolean;
  search?: string;
}) => {
  const qs = new URLSearchParams();
  if (params?.page) qs.set("page", String(params.page));
  if (params?.page_size) qs.set("page_size", String(params.page_size));
  if (params?.sector) qs.set("sector", params.sector);
  if (params?.kmi_only) qs.set("kmi_only", "true");
  if (params?.kse100_only) qs.set("kse100_only", "true");
  if (params?.search) qs.set("search", params.search);
  return apiFetch<SecuritiesListResponse>(`/api/v1/securities?${qs}`);
};

export const fetchSecurity = (symbol: string) =>
  apiFetch<Security>(`/api/v1/securities/${symbol}`);

export const fetchOhlcv = (
  symbol: string,
  params?: { date_from?: string; date_to?: string; limit?: number; adjusted?: boolean },
) => {
  const qs = new URLSearchParams();
  if (params?.date_from) qs.set("date_from", params.date_from);
  if (params?.date_to) qs.set("date_to", params.date_to);
  if (params?.limit) qs.set("limit", String(params.limit));
  if (params?.adjusted !== undefined) qs.set("adjusted", String(params.adjusted));
  return apiFetch<OhlcvResponse>(`/api/v1/securities/${symbol}/ohlcv?${qs}`);
};

export const fetchFundamentals = (symbol: string) =>
  apiFetch<Fundamentals>(`/api/v1/securities/${symbol}/fundamentals`);

export const fetchAnnouncements = (symbol: string, limit = 50) =>
  apiFetch<{ symbol: string; items: Announcement[]; total: number }>(
    `/api/v1/securities/${symbol}/announcements?limit=${limit}`,
  );

export const fetchIndices = () => apiFetch<IndexPerformance[]>("/api/v1/indices");
export const fetchSectors = () => apiFetch<string[]>("/api/v1/sectors");

export const fetchWatchlist = () => apiFetch<WatchlistItem[]>("/api/v1/watchlist");
export const addToWatchlist = (symbol: string, note?: string) =>
  apiFetch<WatchlistItem>("/api/v1/watchlist", {
    method: "POST",
    body: JSON.stringify({ symbol, note }),
  });
export const removeFromWatchlist = (symbol: string) =>
  apiFetch<void>(`/api/v1/watchlist/${symbol}`, { method: "DELETE" });

export const reorderWatchlist = (symbols: string[]) =>
  apiFetch<WatchlistItem[]>("/api/v1/watchlist/reorder", {
    method: "PUT",
    body: JSON.stringify({ symbols }),
  });

export const fetchQuotes = (symbols: string[]) => {
  if (symbols.length === 0) return Promise.resolve<QuotesResponse>({ items: [] });
  const qs = new URLSearchParams({ symbols: symbols.join(",") });
  return apiFetch<QuotesResponse>(`/api/v1/quotes?${qs}`);
};
