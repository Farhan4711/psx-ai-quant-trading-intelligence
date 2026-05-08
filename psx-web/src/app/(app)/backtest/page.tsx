"use client";

import { useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import {
  fetchBacktestStrategies,
  runBacktest,
  type BacktestResult,
  type StrategyMeta,
  type TradeOut,
} from "@/lib/api/backtest";
import { fetchSecurities } from "@/lib/api/securities";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { EquityChart } from "@/components/backtest/EquityChart";
import { formatCurrency, formatPercent } from "@/lib/utils/format";
import { ArrowRight, Lightbulb, RotateCcw } from "lucide-react";

type WizardStep = "stock" | "strategy" | "range" | "review" | "result";

function fiveYearsAgo(): string {
  const d = new Date();
  d.setFullYear(d.getFullYear() - 5);
  return d.toISOString().slice(0, 10);
}

function today(): string {
  return new Date().toISOString().slice(0, 10);
}

export default function BacktestPage() {
  const [step, setStep] = useState<WizardStep>("stock");

  // Inputs
  const [symbol, setSymbol] = useState("");
  const [symbolQuery, setSymbolQuery] = useState("");
  const [strategyKey, setStrategyKey] = useState<string>("sma_crossover");
  const [startDate, setStartDate] = useState(fiveYearsAgo());
  const [endDate, setEndDate] = useState(today());
  const [capital, setCapital] = useState("100000");
  const [commission, setCommission] = useState(0.15);

  const { data: strategies } = useQuery({
    queryKey: ["backtest-strategies"],
    queryFn: fetchBacktestStrategies,
    staleTime: 86_400_000,
  });

  const { data: symbolMatches } = useQuery({
    queryKey: ["securities", "autocomplete", symbolQuery],
    queryFn: () => fetchSecurities({ search: symbolQuery, page_size: 8 }),
    enabled: symbolQuery.length >= 1,
    staleTime: 60_000,
  });

  const selectedStrategy: StrategyMeta | undefined = useMemo(
    () => strategies?.find((s) => s.key === strategyKey),
    [strategies, strategyKey],
  );

  const mut = useMutation({
    mutationFn: () =>
      runBacktest({
        symbol,
        strategy: strategyKey,
        start_date: startDate,
        end_date: endDate,
        initial_capital_pkr: capital,
        commission_per_side_pct: commission,
      }),
    onSuccess: () => setStep("result"),
  });

  function reset() {
    setStep("stock");
    setSymbol("");
    setSymbolQuery("");
    mut.reset();
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Backtest</h1>
          <p className="mt-1 text-sm text-gray-500">
            Run a strategy on real PSX history. Adjusted prices, retail
            commission, no look-ahead. Educational, not advice.
          </p>
        </div>
        {step === "result" && (
          <Button variant="outline" onClick={reset} className="gap-2">
            <RotateCcw className="h-4 w-4" /> New backtest
          </Button>
        )}
      </div>

      {step !== "result" && (
        <Stepper current={step} />
      )}

      {step === "stock" && (
        <StepCard title="1. Pick a stock" subtitle="Liquid PSX names give the cleanest backtests.">
          <div className="space-y-1.5">
            <Label htmlFor="bt-symbol">Symbol</Label>
            <Input
              id="bt-symbol"
              value={symbol}
              onChange={(e) => {
                setSymbol(e.target.value.toUpperCase());
                setSymbolQuery(e.target.value);
              }}
              placeholder="ENGRO"
              autoComplete="off"
            />
            {symbol.length >= 1 && symbolMatches?.items?.length ? (
              <ul className="rounded-md border border-gray-200 bg-white shadow-sm">
                {symbolMatches.items.slice(0, 6).map((s) => (
                  <li key={s.symbol}>
                    <button
                      type="button"
                      onClick={() => {
                        setSymbol(s.symbol);
                        setSymbolQuery("");
                      }}
                      className="block w-full px-3 py-1.5 text-left text-sm hover:bg-gray-50"
                    >
                      <span className="font-mono font-semibold">{s.symbol}</span>
                      <span className="ml-2 truncate text-gray-500">{s.company_name}</span>
                    </button>
                  </li>
                ))}
              </ul>
            ) : null}
          </div>
          <div className="flex justify-end">
            <Button disabled={symbol.length === 0} onClick={() => setStep("strategy")}>
              Next <ArrowRight className="h-4 w-4" />
            </Button>
          </div>
        </StepCard>
      )}

      {step === "strategy" && (
        <StepCard
          title="2. Pick a strategy"
          subtitle="Single-indicator strategies for teaching. No optimisation."
        >
          <div className="space-y-2">
            {(strategies ?? []).map((s) => (
              <button
                key={s.key}
                type="button"
                onClick={() => setStrategyKey(s.key)}
                className={
                  "block w-full rounded-md border px-4 py-3 text-left transition " +
                  (strategyKey === s.key
                    ? "border-blue-600 bg-blue-50"
                    : "border-gray-200 bg-white hover:bg-gray-50")
                }
              >
                <p className="text-sm font-semibold text-gray-900">{s.label}</p>
                <p className="mt-0.5 text-xs text-gray-500">
                  Defaults: {Object.entries(s.default_params).map(([k, v]) => `${k}=${v}`).join(", ") || "no parameters"}
                </p>
              </button>
            ))}
          </div>
          <div className="flex justify-between">
            <Button variant="outline" onClick={() => setStep("stock")}>← Back</Button>
            <Button disabled={!selectedStrategy} onClick={() => setStep("range")}>
              Next <ArrowRight className="h-4 w-4" />
            </Button>
          </div>
        </StepCard>
      )}

      {step === "range" && (
        <StepCard title="3. Date range + capital" subtitle="Default = last 5 years, PKR 100,000 starting capital, 0.15% commission per side.">
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label htmlFor="bt-start">From</Label>
              <Input id="bt-start" type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="bt-end">To</Label>
              <Input id="bt-end" type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label htmlFor="bt-capital">Initial capital (PKR)</Label>
              <Input id="bt-capital" type="number" min="0" value={capital} onChange={(e) => setCapital(e.target.value)} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="bt-commish">Commission per side (%)</Label>
              <Input
                id="bt-commish"
                type="number"
                min="0"
                step="0.01"
                value={commission}
                onChange={(e) => setCommission(parseFloat(e.target.value) || 0)}
              />
            </div>
          </div>
          <div className="flex justify-between">
            <Button variant="outline" onClick={() => setStep("strategy")}>← Back</Button>
            <Button onClick={() => setStep("review")}>Next <ArrowRight className="h-4 w-4" /></Button>
          </div>
        </StepCard>
      )}

      {step === "review" && (
        <StepCard title="4. Review and run" subtitle="">
          <dl className="space-y-1.5 text-sm">
            <Row k="Symbol" v={symbol} />
            <Row k="Strategy" v={selectedStrategy?.label ?? strategyKey} />
            <Row k="Range" v={`${startDate} → ${endDate}`} />
            <Row k="Initial capital" v={formatCurrency(parseFloat(capital))} />
            <Row k="Commission" v={`${commission}% per side`} />
          </dl>
          {mut.isError && (
            <p className="text-sm text-red-600">{(mut.error as Error).message}</p>
          )}
          <div className="flex justify-between">
            <Button variant="outline" onClick={() => setStep("range")}>← Back</Button>
            <Button onClick={() => mut.mutate()} disabled={mut.isPending}>
              {mut.isPending ? "Running…" : "Run backtest"}
            </Button>
          </div>
        </StepCard>
      )}

      {step === "result" && mut.data && <ResultView result={mut.data} />}
    </div>
  );
}

// ── Subcomponents ──────────────────────────────────────────────────────

function Stepper({ current }: { current: WizardStep }) {
  const order: WizardStep[] = ["stock", "strategy", "range", "review"];
  const idx = order.indexOf(current);
  return (
    <ol className="flex flex-wrap gap-2 text-xs text-gray-500">
      {order.map((s, i) => (
        <li
          key={s}
          className={
            "rounded-full border px-3 py-1 " +
            (i < idx
              ? "border-blue-200 bg-blue-50 text-blue-700"
              : i === idx
              ? "border-blue-600 bg-blue-600 text-white"
              : "border-gray-200 text-gray-500")
          }
        >
          {i + 1}. {s.charAt(0).toUpperCase() + s.slice(1)}
        </li>
      ))}
    </ol>
  );
}

function StepCard({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-4 rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
      <div>
        <h2 className="text-base font-semibold text-gray-900">{title}</h2>
        {subtitle && <p className="mt-0.5 text-sm text-gray-500">{subtitle}</p>}
      </div>
      {children}
    </div>
  );
}

function Row({ k, v }: { k: string; v: string }) {
  return (
    <div className="flex items-center justify-between border-b border-gray-100 py-1.5 last:border-0">
      <dt className="text-gray-500">{k}</dt>
      <dd className="font-medium text-gray-900">{v}</dd>
    </div>
  );
}

function ResultView({ result }: { result: BacktestResult }) {
  const beat = result.excess_return_pct;
  return (
    <div className="space-y-5">
      {/* Hero summary */}
      <div className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
        <div className="flex flex-wrap items-baseline justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">
              {result.strategy.replaceAll("_", " ")} on {result.symbol}
            </h2>
            <p className="text-xs text-gray-500">
              {result.start_date} → {result.end_date}
            </p>
          </div>
          <div className="text-right">
            <p className="text-2xl font-bold tabular-nums text-gray-900">
              {formatCurrency(result.final_value_pkr)}
            </p>
            <p className={`text-sm font-medium ${result.total_return_pct >= 0 ? "text-green-700" : "text-red-700"}`}>
              {formatPercent(result.total_return_pct)} total
            </p>
          </div>
        </div>

        {/* Stats grid */}
        <div className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Stat label="CAGR" value={formatPercent(result.cagr_pct)} />
          <Stat label="Sharpe" value={result.sharpe_ratio.toFixed(2)} />
          <Stat label="Max drawdown" value={formatPercent(-result.max_drawdown_pct)} valueClass="text-red-700" />
          <Stat label="Trades" value={String(result.num_trades)} />
          <Stat label="Win rate" value={result.num_trades ? `${result.win_rate_pct.toFixed(0)}%` : "—"} />
          <Stat label="Avg win" value={result.num_trades ? `+${result.avg_winning_trade_pct.toFixed(1)}%` : "—"} />
          <Stat label="Avg loss" value={result.num_trades ? `${result.avg_losing_trade_pct.toFixed(1)}%` : "—"} />
          <Stat label="Total commish" value={formatCurrency(result.total_commissions_pkr)} />
        </div>

        {/* Benchmark comparison */}
        <div className="mt-5 rounded-md border border-blue-100 bg-blue-50 p-3 text-sm text-blue-900">
          Buy-and-hold over the same window would have returned{" "}
          <strong>{formatPercent(result.benchmark_return_pct)}</strong>. Strategy{" "}
          <strong className={beat >= 0 ? "text-green-700" : "text-red-700"}>
            {beat >= 0 ? "beat" : "trailed"} buy-and-hold by {formatPercent(Math.abs(beat))}
          </strong>
          .
        </div>
      </div>

      {/* Equity chart */}
      <div className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-gray-500">
          Equity curve
        </h2>
        <EquityChart
          curve={result.equity_curve}
          initialCapital={result.initial_capital_pkr}
          benchmarkReturnPct={result.benchmark_return_pct}
        />
      </div>

      {/* Lessons */}
      {result.lessons.length > 0 && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-4">
          <h3 className="mb-2 flex items-center gap-1.5 text-sm font-semibold uppercase tracking-wider text-amber-900">
            <Lightbulb className="h-4 w-4" />
            Lessons
          </h3>
          <ul className="space-y-2 text-sm text-amber-900">
            {result.lessons.map((l, i) => (
              <li key={i} className="flex gap-2">
                <span aria-hidden>•</span>
                <span dangerouslySetInnerHTML={{ __html: l.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>") }} />
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Trades */}
      {result.trades.length > 0 && (
        <div className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-gray-500">
            Trade log ({result.trades.length})
          </h2>
          <ul className="space-y-3">
            {result.trades.map((t, i) => (
              <TradeItem key={i} trade={t} />
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function Stat({ label, value, valueClass }: { label: string; value: string; valueClass?: string }) {
  return (
    <div className="rounded-md border border-gray-100 bg-gray-50 p-2">
      <p className="text-xs uppercase tracking-wider text-gray-500">{label}</p>
      <p className={`mt-0.5 text-sm font-semibold tabular-nums ${valueClass ?? "text-gray-900"}`}>{value}</p>
    </div>
  );
}

function TradeItem({ trade }: { trade: TradeOut }) {
  const win = trade.net_pnl_pkr >= 0;
  return (
    <li className="rounded-md border border-gray-100 p-3">
      <div className="flex items-baseline justify-between gap-2">
        <span className="text-xs text-gray-500">
          {trade.entry_date} → {trade.exit_date} · {trade.holding_days} day{trade.holding_days !== 1 ? "s" : ""}
        </span>
        <span className={`text-sm font-semibold ${win ? "text-green-700" : "text-red-700"}`}>
          {win ? "+" : ""}{trade.return_pct.toFixed(2)}%
        </span>
      </div>
      <p className="mt-1.5 text-sm text-gray-700">{trade.narration}</p>
    </li>
  );
}
