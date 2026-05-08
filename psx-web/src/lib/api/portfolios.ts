const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    credentials: "include",
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });
  if (!res.ok) {
    const err = (await res.json().catch(() => ({ detail: res.statusText }))) as {
      detail?: string;
    };
    throw new Error(err.detail ?? "Request failed");
  }
  // 204 No Content
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

// ── Types ──────────────────────────────────────────────────────────────

export type TransactionType = "buy" | "sell" | "dividend" | "bonus" | "rights";

export interface Portfolio {
  id: string;
  user_id: string;
  name: string;
  description: string | null;
  base_currency: string;
  is_default: boolean;
  created_at: string;
}

export interface PortfolioCreate {
  name: string;
  description?: string | null;
  base_currency?: string;
  is_default?: boolean;
}

export interface Transaction {
  id: string;
  portfolio_id: string;
  symbol: string;
  transaction_type: TransactionType;
  transaction_date: string;
  quantity: string;
  price_per_share: string;
  brokerage_pkr: string;
  fed_pkr: string;
  cvt_pkr: string;
  cgt_pkr: string;
  notes: string | null;
  created_at: string;
}

export interface TransactionCreate {
  symbol: string;
  transaction_type: TransactionType;
  transaction_date: string; // YYYY-MM-DD
  quantity: string;
  price_per_share: string;
  brokerage_pkr?: string;
  fed_pkr?: string;
  cvt_pkr?: string;
  cgt_pkr?: string;
  notes?: string | null;
}

export interface MatchedLotPreview {
  transaction_id: string | null;
  buy_date: string;
  quantity: string;
  buy_price: string;
  holding_period_days: number;
  gross_gain_pkr: string;
  cgt_rate_pct: string;
  cgt_pkr: string;
}

export interface TransactionPreview {
  transaction_type: TransactionType;
  symbol: string;
  quantity: string;
  price_per_share: string;
  gross_value_pkr: string;
  brokerage_pkr: string;
  fed_pkr: string;
  cvt_pkr: string;
  cgt_pkr: string;
  total_charges_pkr: string;
  net_cash_impact_pkr: string;
  matched_lots: MatchedLotPreview[];
  warnings: string[];
}

// ── Fetchers ───────────────────────────────────────────────────────────

export interface HoldingDashboardRow {
  symbol: string;
  company_name: string;
  sector: string;
  is_kmi_compliant: boolean;
  quantity: string;
  avg_cost_pkr: string;
  total_invested_pkr: string;
  last_close: string | null;
  last_close_date: string | null;
  market_value_pkr: string | null;
  unrealized_pnl_pkr: string | null;
  unrealized_pnl_pct: string | null;
  day_change_pct: string | null;
  realized_pnl_pkr: string;
  total_dividends_received_pkr: string;
}

export interface SectorAllocationRow {
  sector: string;
  value_pkr: string;
  pct: string;
}

export interface PortfolioSummary {
  portfolio_id: string;
  total_invested_pkr: string;
  current_value_pkr: string;
  unrealized_pnl_pkr: string;
  unrealized_pnl_pct: string;
  unrealized_pnl_after_tax_pkr: string;
  estimated_liquidation_cgt_pkr: string;
  realized_pnl_ytd_pkr: string;
  dividends_ytd_pkr: string;
  fees_ytd_pkr: string;
  holding_count: number;
  holdings: HoldingDashboardRow[];
  sector_allocation: SectorAllocationRow[];
}

export const fetchPortfolios = () => apiFetch<Portfolio[]>("/api/v1/portfolios");

export const fetchPortfolioSummary = (portfolioId: string) =>
  apiFetch<PortfolioSummary>(`/api/v1/portfolios/${portfolioId}/summary`);

export const createPortfolio = (body: PortfolioCreate) =>
  apiFetch<Portfolio>("/api/v1/portfolios", {
    method: "POST",
    body: JSON.stringify(body),
  });

export const fetchTransactions = (portfolioId: string, limit = 200) =>
  apiFetch<Transaction[]>(
    `/api/v1/portfolios/${portfolioId}/transactions?limit=${limit}`,
  );

export const previewTransaction = (
  portfolioId: string,
  body: TransactionCreate,
) =>
  apiFetch<TransactionPreview>(
    `/api/v1/portfolios/${portfolioId}/transactions/preview`,
    { method: "POST", body: JSON.stringify(body) },
  );

export const createTransaction = (
  portfolioId: string,
  body: TransactionCreate,
) =>
  apiFetch<Transaction>(`/api/v1/portfolios/${portfolioId}/transactions`, {
    method: "POST",
    body: JSON.stringify(body),
  });
