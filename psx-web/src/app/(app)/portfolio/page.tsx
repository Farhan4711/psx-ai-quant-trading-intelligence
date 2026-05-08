"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import {
  fetchPortfolioSummary,
  fetchPortfolios,
  type HoldingDashboardRow,
} from "@/lib/api/portfolios";
import { fetchCurrentUser } from "@/lib/api/auth";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { TradeEntryModal } from "@/components/portfolios/TradeEntryModal";
import { BenchmarkPanel } from "@/components/portfolios/BenchmarkPanel";
import { formatCurrency, formatPercent, formatPrice } from "@/lib/utils/format";
import { AlertTriangle } from "lucide-react";

export default function PortfolioDashboardPage() {
  const { data: portfolios } = useQuery({
    queryKey: ["portfolios"],
    queryFn: fetchPortfolios,
    staleTime: 60_000,
  });

  const { data: currentUser } = useQuery({
    queryKey: ["current-user"],
    queryFn: fetchCurrentUser,
    staleTime: 5 * 60_000,
    retry: false,
  });
  const shariahMode = !!currentUser?.shariah_mode;

  // Default portfolio (auto-created by backend on first list call)
  const portfolioId = portfolios?.find((p) => p.is_default)?.id ?? portfolios?.[0]?.id;

  const { data: summary, isLoading, isError } = useQuery({
    queryKey: ["portfolio-summary", portfolioId],
    queryFn: () => fetchPortfolioSummary(portfolioId!),
    enabled: !!portfolioId,
    staleTime: 60_000,
    refetchInterval: 60_000,
  });

  if (isLoading || !summary) {
    return (
      <div className="space-y-5">
        <SkeletonCard />
        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <SkeletonCard key={i} />
          ))}
        </div>
      </div>
    );
  }

  if (isError) {
    return (
      <p className="text-sm text-red-600">Failed to load portfolio summary.</p>
    );
  }

  const invested = parseFloat(summary.total_invested_pkr);
  const current = parseFloat(summary.current_value_pkr);
  const unrealized = parseFloat(summary.unrealized_pnl_pkr);
  const unrealizedPct = parseFloat(summary.unrealized_pnl_pct);
  const afterTax = parseFloat(summary.unrealized_pnl_after_tax_pkr);
  const cgtIfSold = parseFloat(summary.estimated_liquidation_cgt_pkr);
  const realizedYtd = parseFloat(summary.realized_pnl_ytd_pkr);
  const divsYtd = parseFloat(summary.dividends_ytd_pkr);
  const feesYtd = parseFloat(summary.fees_ytd_pkr);
  const empty = summary.holdings.length === 0;

  return (
    <div className="space-y-6">
      {/* ── Header + after-tax framing ───────────────────────────── */}
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Portfolio</h1>
          <p className="mt-1 text-sm text-gray-500">
            {summary.holding_count} holding{summary.holding_count === 1 ? "" : "s"} · refreshes every minute
          </p>
        </div>
        <TradeEntryModal trigger={<Button>+ Record trade</Button>} />
      </div>

      {empty ? (
        <EmptyState />
      ) : (
        <>
          {/* The differentiator — after-tax narrative */}
          <div className="rounded-lg border border-blue-200 bg-blue-50 p-4 text-sm">
            <p className="font-medium text-blue-900">
              Your portfolio is up{" "}
              <span
                className={
                  unrealized >= 0 ? "text-green-700" : "text-red-700"
                }
              >
                {formatCurrency(unrealized)} ({formatPercent(unrealizedPct)})
              </span>
              .
            </p>
            <p className="mt-1 text-blue-800">
              If you sold today you&apos;d net{" "}
              <strong>{formatCurrency(afterTax)}</strong> after CGT of {formatCurrency(cgtIfSold)}.
            </p>
          </div>

          {/* Top KPIs */}
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            <StatCard label="Invested" value={formatCurrency(invested)} />
            <StatCard label="Current value" value={formatCurrency(current)} />
            <StatCard
              label="Unrealized P&L (gross)"
              value={formatCurrency(unrealized)}
              valueClass={unrealized >= 0 ? "text-green-700" : "text-red-700"}
              hint={formatPercent(unrealizedPct)}
            />
            <StatCard
              label="Unrealized P&L (after-tax)"
              value={formatCurrency(afterTax)}
              valueClass={afterTax >= 0 ? "text-green-700" : "text-red-700"}
              hint={`CGT: ${formatCurrency(cgtIfSold)}`}
            />
          </div>

          {/* YTD strip */}
          <div className="grid grid-cols-3 gap-3">
            <StatCard
              label="Realized P&L YTD"
              value={formatCurrency(realizedYtd)}
              valueClass={realizedYtd >= 0 ? "text-green-700" : "text-red-700"}
            />
            <StatCard label="Dividends YTD" value={formatCurrency(divsYtd)} />
            <StatCard
              label="Fees + tax YTD"
              value={formatCurrency(feesYtd)}
              valueClass="text-gray-700"
            />
          </div>

          {/* How I compare (Phase 4) */}
          <BenchmarkPanel />

          {/* Sector allocation */}
          <SectorAllocation rows={summary.sector_allocation} />

          {/* Holdings */}
          <HoldingsTable rows={summary.holdings} shariahMode={shariahMode} />
        </>
      )}
    </div>
  );
}

// ── Subcomponents ──────────────────────────────────────────────────────

function StatCard({
  label,
  value,
  hint,
  valueClass,
}: {
  label: string;
  value: string;
  hint?: string;
  valueClass?: string;
}) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
      <p className="text-xs font-medium uppercase tracking-wide text-gray-500">
        {label}
      </p>
      <p className={`mt-1 text-lg font-semibold ${valueClass ?? "text-gray-900"}`}>
        {value}
      </p>
      {hint && <p className="mt-0.5 text-xs text-gray-500">{hint}</p>}
    </div>
  );
}

function SkeletonCard() {
  return (
    <div className="h-24 animate-pulse rounded-lg border border-gray-200 bg-gray-100" />
  );
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-lg border border-dashed border-gray-300 bg-white py-16 text-center">
      <div className="text-3xl">📈</div>
      <h2 className="text-lg font-semibold text-gray-900">No holdings yet</h2>
      <p className="max-w-sm text-sm text-gray-500">
        You don&apos;t have any transactions yet. Log your first buy to start tracking
        gross + after-tax returns automatically.
      </p>
      <TradeEntryModal trigger={<Button className="mt-2">Record your first trade</Button>} />
    </div>
  );
}

function SectorAllocation({ rows }: { rows: { sector: string; value_pkr: string; pct: string }[] }) {
  if (rows.length === 0) return null;
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
      <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-500">
        Sector allocation
      </h2>
      <ul className="mt-3 space-y-2.5">
        {rows.map((r) => {
          const pct = parseFloat(r.pct);
          return (
            <li key={r.sector}>
              <div className="flex items-center justify-between text-sm">
                <span className="font-medium text-gray-800">{r.sector}</span>
                <span className="tabular-nums text-gray-500">
                  {formatCurrency(parseFloat(r.value_pkr))} ({pct.toFixed(1)}%)
                </span>
              </div>
              <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-gray-100">
                <div
                  className="h-full bg-blue-500"
                  style={{ width: `${Math.min(pct, 100)}%` }}
                />
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

function HoldingsTable({
  rows,
  shariahMode,
}: {
  rows: HoldingDashboardRow[];
  shariahMode: boolean;
}) {
  function dim(r: HoldingDashboardRow): string {
    return shariahMode && !r.is_kmi_compliant ? "opacity-50" : "";
  }
  function nonCompliantWarn(r: HoldingDashboardRow) {
    return shariahMode && !r.is_kmi_compliant ? (
      <span title="Non-compliant under Shariah Mode" className="ml-1 inline-flex">
        <AlertTriangle className="h-3 w-3 text-amber-500" />
      </span>
    ) : null;
  }
  return (
    <div className="overflow-hidden rounded-lg border border-gray-200 bg-white shadow-sm">
      <h2 className="border-b border-gray-200 bg-gray-50 px-4 py-3 text-sm font-semibold uppercase tracking-wide text-gray-500">
        Holdings
      </h2>
      {/* Desktop */}
      <div className="hidden md:block">
        <div className="grid grid-cols-[120px_minmax(0,1fr)_100px_120px_140px_140px_120px] gap-3 border-b border-gray-100 px-4 py-2 text-xs font-medium uppercase tracking-wide text-gray-500">
          <span>Symbol</span>
          <span>Company</span>
          <span className="text-right">Qty</span>
          <span className="text-right">Avg cost</span>
          <span className="text-right">Last</span>
          <span className="text-right">Day Δ</span>
          <span className="text-right">Total return</span>
        </div>
        <ul className="divide-y divide-gray-100">
          {rows.map((r) => (
            <li
              key={r.symbol}
              className={
                "grid grid-cols-[120px_minmax(0,1fr)_100px_120px_140px_140px_120px] gap-3 px-4 py-2.5 text-sm hover:bg-gray-50 " +
                dim(r)
              }
            >
              <Link
                href={`/app/stocks/${r.symbol}`}
                className="font-mono font-semibold text-blue-700 hover:underline"
              >
                {r.symbol}
                {nonCompliantWarn(r)}
              </Link>
              <span className="truncate text-gray-800">
                {r.company_name}
                {r.is_kmi_compliant && <Badge variant="kmi" className="ml-2">KMI</Badge>}
              </span>
              <span className="text-right tabular-nums">{r.quantity}</span>
              <span className="text-right tabular-nums">{formatPrice(r.avg_cost_pkr)}</span>
              <span className="text-right tabular-nums">{formatPrice(r.last_close)}</span>
              <span
                className={
                  "text-right tabular-nums " +
                  (r.day_change_pct == null
                    ? "text-gray-400"
                    : parseFloat(r.day_change_pct) >= 0
                    ? "text-green-700"
                    : "text-red-700")
                }
              >
                {r.day_change_pct == null ? "—" : formatPercent(parseFloat(r.day_change_pct))}
              </span>
              <span
                className={
                  "text-right tabular-nums " +
                  (r.unrealized_pnl_pct == null
                    ? "text-gray-400"
                    : parseFloat(r.unrealized_pnl_pct) >= 0
                    ? "text-green-700"
                    : "text-red-700")
                }
              >
                {r.unrealized_pnl_pct == null
                  ? "—"
                  : formatPercent(parseFloat(r.unrealized_pnl_pct))}
              </span>
            </li>
          ))}
        </ul>
      </div>
      {/* Mobile */}
      <ul className="divide-y divide-gray-100 md:hidden">
        {rows.map((r) => (
          <li key={r.symbol} className="px-4 py-3 text-sm">
            <div className="flex items-center justify-between">
              <Link
                href={`/app/stocks/${r.symbol}`}
                className="font-mono font-semibold text-blue-700"
              >
                {r.symbol}
              </Link>
              <span className="tabular-nums">
                {r.market_value_pkr ? formatCurrency(parseFloat(r.market_value_pkr)) : "—"}
              </span>
            </div>
            <div className="mt-0.5 flex items-center justify-between text-xs text-gray-500">
              <span className="truncate">
                {r.quantity} × {formatPrice(r.avg_cost_pkr)}
              </span>
              <span
                className={
                  r.unrealized_pnl_pct == null
                    ? "text-gray-400"
                    : parseFloat(r.unrealized_pnl_pct) >= 0
                    ? "text-green-700"
                    : "text-red-700"
                }
              >
                {r.unrealized_pnl_pct == null
                  ? "—"
                  : formatPercent(parseFloat(r.unrealized_pnl_pct))}
              </span>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
