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
  return res.json() as Promise<T>;
}

export interface StrategyMeta {
  key: string;
  label: string;
  default_params: Record<string, number>;
}

export interface BacktestRequest {
  symbol: string;
  strategy: string;
  start_date: string; // YYYY-MM-DD
  end_date: string;
  initial_capital_pkr: string;
  commission_per_side_pct?: number;
  parameters?: Record<string, number>;
}

export interface TradeOut {
  entry_date: string;
  entry_price: number;
  exit_date: string;
  exit_price: number;
  quantity: number;
  commission_pkr: number;
  gross_pnl_pkr: number;
  net_pnl_pkr: number;
  return_pct: number;
  holding_days: number;
  reason_open: string;
  reason_close: string;
  narration: string;
}

export interface EquityPointOut {
  date: string;
  equity_pkr: number;
  drawdown_pct: number;
  in_position: boolean;
}

export interface BacktestResult {
  symbol: string;
  strategy: string;
  start_date: string;
  end_date: string;
  initial_capital_pkr: number;
  final_value_pkr: number;
  total_return_pct: number;
  cagr_pct: number;
  sharpe_ratio: number;
  max_drawdown_pct: number;
  num_trades: number;
  win_rate_pct: number;
  avg_winning_trade_pct: number;
  avg_losing_trade_pct: number;
  avg_holding_days: number;
  total_commissions_pkr: number;
  benchmark_return_pct: number;
  excess_return_pct: number;
  trades: TradeOut[];
  equity_curve: EquityPointOut[];
  lessons: string[];
}

export const fetchBacktestStrategies = () =>
  apiFetch<StrategyMeta[]>("/api/v1/backtest/strategies");

export const runBacktest = (body: BacktestRequest) =>
  apiFetch<BacktestResult>("/api/v1/backtest", {
    method: "POST",
    body: JSON.stringify(body),
  });
