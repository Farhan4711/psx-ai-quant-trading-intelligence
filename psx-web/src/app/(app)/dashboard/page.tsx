"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowRight,
  BarChart2,
  Bell,
  Calculator,
  ExternalLink,
  FlaskConical,
  Grid3x3,
  TrendingDown,
  TrendingUp,
} from "lucide-react";
import {
  fetchPortfolios,
  fetchPortfolioSummary,
  type Portfolio,
  type PortfolioSummary,
} from "@/lib/api/portfolios";
import {
  fetchWatchlist,
  type WatchlistItem,
} from "@/lib/api/securities";
import { fetchAlertsForUser, type SuspiciousDay } from "@/lib/api/alerts";

/**
 * Dashboard — Phase 10 Step 94.
 *
 * Replaces the 4-tile placeholder with four live widgets:
 *   1. Portfolio snapshot — value + gross/after-tax unrealised P&L
 *   2. Watchlist snapshot — top 5 rows by sort order
 *   3. Recent alerts — last 5 pump/dump flags on the user's universe
 *   4. Quick-action tiles — keeps the navigation affordance the old
 *      tile grid provided
 *
 * Each widget owns its own loading state so a slow tail-end query
 * never blocks the rest of the page.
 */
export default function DashboardPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="mt-1 text-sm text-gray-500">
          Pakistani equities, with the tax math built in.
        </p>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <PortfolioSnapshot />
        </div>
        <RecentAlerts />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <WatchlistSnapshot />
        <QuickTiles />
      </div>
    </div>
  );
}

// ── Portfolio snapshot ────────────────────────────────────────────────

function PortfolioSnapshot() {
  const portfolios = useQuery({
    queryKey: ["portfolios"],
    queryFn: fetchPortfolios,
  });
  const defaultPortfolio = pickDefault(portfolios.data);
  const summary = useQuery<PortfolioSummary>({
    queryKey: ["portfolio-summary", defaultPortfolio?.id],
    queryFn: () => fetchPortfolioSummary(defaultPortfolio!.id),
    enabled: !!defaultPortfolio,
  });

  if (portfolios.isLoading) return <CardSkeleton />;
  if (!defaultPortfolio) {
    return (
      <Card title="Portfolio">
        <EmptyHint
          message="No portfolio yet. Record your first trade and we'll do the tax math."
          cta={{ href: "/portfolio", label: "Open portfolio" }}
        />
      </Card>
    );
  }
  if (summary.isLoading || !summary.data) return <CardSkeleton />;

  const s = summary.data;
  const invested = parseNum(s.total_invested_pkr);
  const current = parseNum(s.current_value_pkr);
  const grossPnl = parseNum(s.unrealized_pnl_pkr);
  const afterTaxPnl = parseNum(s.unrealized_pnl_after_tax_pkr);
  const pct = invested > 0 ? (grossPnl / invested) * 100 : 0;
  const taxDrag = grossPnl - afterTaxPnl;

  return (
    <Card
      title="Portfolio"
      actions={
        <Link
          href="/portfolio"
          className="inline-flex items-center gap-1 text-xs font-medium text-blue-600 hover:underline"
        >
          Open <ExternalLink className="h-3 w-3" />
        </Link>
      }
    >
      <div className="grid gap-4 sm:grid-cols-3">
        <StatCell
          label="Current value"
          value={`PKR ${formatPkr(current)}`}
          sub={`Invested ${formatPkr(invested)}`}
        />
        <StatCell
          label="Unrealised P&L"
          value={`${grossPnl >= 0 ? "+" : ""}PKR ${formatPkr(Math.abs(grossPnl))}`}
          sub={`${pct >= 0 ? "+" : ""}${pct.toFixed(2)}% gross`}
          tone={grossPnl >= 0 ? "positive" : "negative"}
        />
        <StatCell
          label="After tax"
          value={`PKR ${formatPkr(afterTaxPnl)}`}
          sub={
            taxDrag > 0
              ? `−PKR ${formatPkr(taxDrag)} CGT if sold today`
              : "No CGT drag yet"
          }
          tone={afterTaxPnl >= 0 ? "positive" : "negative"}
        />
      </div>
      {s.holdings.length > 0 && (
        <div className="mt-5 text-xs text-gray-500">
          {s.holdings.length} holding{s.holdings.length === 1 ? "" : "s"} · {" "}
          {s.sector_allocation.length} sector
          {s.sector_allocation.length === 1 ? "" : "s"}
        </div>
      )}
    </Card>
  );
}

function pickDefault(portfolios: Portfolio[] | undefined): Portfolio | undefined {
  if (!portfolios?.length) return undefined;
  // The dashboard list endpoint doesn't expose `is_default` directly;
  // first row is the auto-created default for a new account.
  return portfolios[0];
}

// ── Watchlist snapshot ────────────────────────────────────────────────

function WatchlistSnapshot() {
  const wl = useQuery<WatchlistItem[]>({
    queryKey: ["watchlist-dashboard"],
    queryFn: fetchWatchlist,
  });
  if (wl.isLoading) return <CardSkeleton />;
  const items = (wl.data ?? []).slice(0, 5);
  return (
    <Card
      title="Watchlist"
      actions={
        <Link
          href="/watchlist"
          className="inline-flex items-center gap-1 text-xs font-medium text-blue-600 hover:underline"
        >
          See all <ArrowRight className="h-3 w-3" />
        </Link>
      }
    >
      {items.length === 0 ? (
        <EmptyHint
          message="You haven't starred any stocks yet."
          cta={{ href: "/stocks", label: "Browse stocks" }}
        />
      ) : (
        <ul className="divide-y divide-gray-100">
          {items.map((it) => (
            <li key={it.symbol} className="py-2.5">
              <Link
                href={`/stocks/${it.symbol}`}
                className="-mx-2 flex items-center justify-between gap-3 rounded px-2 hover:bg-gray-50"
              >
                <div className="min-w-0">
                  <p className="font-mono text-sm font-semibold text-gray-900">
                    {it.symbol}
                  </p>
                  <p className="truncate text-xs text-gray-500">
                    {it.company_name}
                  </p>
                </div>
                <span className="rounded bg-gray-100 px-2 py-0.5 text-[10px] font-medium text-gray-600">
                  {it.sector || "—"}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

// ── Recent alerts ────────────────────────────────────────────────────

function RecentAlerts() {
  const alerts = useQuery<SuspiciousDay[]>({
    queryKey: ["alerts-dashboard"],
    queryFn: () => fetchAlertsForUser(5),
  });
  if (alerts.isLoading) return <CardSkeleton />;
  const items = alerts.data ?? [];

  return (
    <Card
      title="Recent alerts"
      actions={
        <Link
          href="/alerts"
          className="inline-flex items-center gap-1 text-xs font-medium text-blue-600 hover:underline"
        >
          All alerts <ArrowRight className="h-3 w-3" />
        </Link>
      }
    >
      {items.length === 0 ? (
        <div className="flex flex-col items-center justify-center gap-1 py-4 text-center text-xs text-gray-500">
          <Bell className="h-5 w-5 text-gray-300" />
          All clear — no pump/dump flags on stocks you watch or hold.
        </div>
      ) : (
        <ul className="space-y-2.5">
          {items.map((a) => (
            <li key={a.id}>
              <Link
                href={`/stocks/${a.symbol}`}
                className="-mx-2 flex items-start gap-3 rounded p-2 hover:bg-gray-50"
              >
                {a.alert_type === "pump" ? (
                  <TrendingUp className="mt-0.5 h-4 w-4 flex-shrink-0 text-amber-600" />
                ) : (
                  <TrendingDown className="mt-0.5 h-4 w-4 flex-shrink-0 text-red-600" />
                )}
                <div className="min-w-0 flex-1">
                  <p className="text-sm">
                    <span className="font-mono font-semibold text-gray-900">
                      {a.symbol}
                    </span>{" "}
                    <SeverityChip s={a.severity} />
                  </p>
                  <p className="line-clamp-2 text-xs text-gray-500">
                    {a.explanation}
                  </p>
                  <p className="mt-0.5 text-[10px] text-gray-400">
                    {a.alert_date}
                  </p>
                </div>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

function SeverityChip({ s }: { s: "low" | "medium" | "high" }) {
  const cls =
    s === "high"
      ? "bg-red-100 text-red-700"
      : s === "medium"
        ? "bg-amber-100 text-amber-700"
        : "bg-gray-100 text-gray-600";
  return (
    <span
      className={`rounded-full px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wider ${cls}`}
    >
      {s}
    </span>
  );
}

// ── Quick tiles ──────────────────────────────────────────────────────

function QuickTiles() {
  const tiles = [
    { href: "/stocks", icon: BarChart2, label: "Browse stocks" },
    { href: "/sectors", icon: Grid3x3, label: "Sector heatmap" },
    { href: "/backtest", icon: FlaskConical, label: "Backtest a strategy" },
    { href: "/tax-simulator", icon: Calculator, label: "Tax simulator" },
  ];
  return (
    <Card title="Quick actions">
      <div className="grid grid-cols-2 gap-3">
        {tiles.map((t) => (
          <Link
            key={t.href}
            href={t.href}
            className="group flex items-center gap-3 rounded-md border border-gray-200 bg-white p-3 transition hover:border-blue-300 hover:bg-blue-50"
          >
            <t.icon className="h-5 w-5 text-gray-500 group-hover:text-blue-600" />
            <span className="text-sm font-medium text-gray-900">{t.label}</span>
          </Link>
        ))}
      </div>
    </Card>
  );
}

// ── Atoms ────────────────────────────────────────────────────────────

function Card({
  title,
  actions,
  children,
}: {
  title: string;
  actions?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-500">
          {title}
        </h2>
        {actions}
      </div>
      {children}
    </section>
  );
}

function StatCell({
  label,
  value,
  sub,
  tone,
}: {
  label: string;
  value: string;
  sub?: string;
  tone?: "positive" | "negative";
}) {
  const valueTone =
    tone === "positive"
      ? "text-emerald-700"
      : tone === "negative"
        ? "text-red-700"
        : "text-gray-900";
  return (
    <div>
      <p className="text-[10px] font-medium uppercase tracking-wider text-gray-400">
        {label}
      </p>
      <p className={`mt-0.5 text-lg font-bold tabular-nums ${valueTone}`}>
        {value}
      </p>
      {sub && <p className="mt-0.5 text-[11px] text-gray-500">{sub}</p>}
    </div>
  );
}

function EmptyHint({
  message,
  cta,
}: {
  message: string;
  cta: { href: string; label: string };
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-4 text-center">
      <p className="text-xs text-gray-500">{message}</p>
      <Link
        href={cta.href}
        className="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-xs font-medium text-gray-800 hover:bg-gray-50"
      >
        {cta.label}
      </Link>
    </div>
  );
}

function CardSkeleton() {
  return <div className="h-48 animate-pulse rounded-lg bg-gray-100" />;
}

function parseNum(s: string | null | undefined): number {
  if (s == null) return 0;
  const n = parseFloat(s);
  return Number.isFinite(n) ? n : 0;
}

function formatPkr(value: number): string {
  return new Intl.NumberFormat("en-PK", { maximumFractionDigits: 0 }).format(value);
}
