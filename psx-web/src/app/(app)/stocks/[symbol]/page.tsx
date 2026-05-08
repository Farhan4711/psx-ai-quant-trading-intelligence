"use client";

import { useQuery } from "@tanstack/react-query";
import { useParams } from "next/navigation";
import {
  fetchAnnouncements,
  fetchFundamentals,
  fetchOhlcv,
  fetchSecurity,
} from "@/lib/api/securities";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Tooltip } from "@/components/ui/tooltip";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { PriceChart } from "@/components/stocks/PriceChart";
import { WatchlistButton } from "@/components/stocks/WatchlistButton";
import { TradeEntryModal } from "@/components/portfolios/TradeEntryModal";
import { IndicatorPanel } from "@/components/stocks/IndicatorPanel";
import { Button } from "@/components/ui/button";
import {
  formatDecimal,
  formatMarketCap,
  formatPrice,
  formatVolume,
} from "@/lib/utils/format";
import { ArrowLeft, Info } from "lucide-react";
import Link from "next/link";

export default function StockDetailPage() {
  const params = useParams<{ symbol: string }>();
  const symbol = params.symbol.toUpperCase();

  const { data: security, isLoading, isError } = useQuery({
    queryKey: ["security", symbol],
    queryFn: () => fetchSecurity(symbol),
    staleTime: 300_000,
  });

  const { data: fundamentals } = useQuery({
    queryKey: ["fundamentals", symbol],
    queryFn: () => fetchFundamentals(symbol),
    staleTime: 3_600_000,
  });

  const { data: announcements } = useQuery({
    queryKey: ["announcements", symbol],
    queryFn: () => fetchAnnouncements(symbol, 50),
    staleTime: 3_600_000,
  });

  // Grab the latest close from OHLCV for the price header
  const { data: latestOhlcv } = useQuery({
    queryKey: ["ohlcv-latest", symbol],
    queryFn: () => fetchOhlcv(symbol, { limit: 2, adjusted: false }),
    staleTime: 300_000,
  });

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center text-sm text-gray-500">
        Loading…
      </div>
    );
  }

  if (isError || !security) {
    return (
      <div className="flex h-64 flex-col items-center justify-center gap-3">
        <p className="text-sm text-red-500">Symbol &ldquo;{symbol}&rdquo; not found.</p>
        <Link href="/app/stocks" className="text-sm text-blue-600 hover:underline">
          ← Back to Stocks
        </Link>
      </div>
    );
  }

  const latest = latestOhlcv?.items[0];
  const prev = latestOhlcv?.items[1];
  const latestClose = latest?.close ? parseFloat(latest.close) : null;
  const prevClose = prev?.close ? parseFloat(prev.close) : null;
  const dayChange = latestClose != null && prevClose != null ? latestClose - prevClose : null;
  const dayChangePct =
    dayChange != null && prevClose ? (dayChange / prevClose) * 100 : null;
  const isPositive = dayChange != null && dayChange >= 0;

  return (
    <div className="space-y-5">
      {/* Back link */}
      <Link
        href="/app/stocks"
        className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700"
      >
        <ArrowLeft className="h-4 w-4" />
        All Stocks
      </Link>

      {/* ── Header ───────────────────────────────────────────────────── */}
      <div className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="space-y-1">
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="font-mono text-2xl font-bold text-gray-900">{symbol}</h1>
              {security.is_kmi_compliant && <Badge variant="kmi">KMI Halal</Badge>}
              {security.is_kse100 && <Badge variant="default">KSE-100</Badge>}
              {security.is_kse30 && <Badge variant="outline">KSE-30</Badge>}
            </div>
            <p className="text-gray-700">{security.company_name}</p>
            <p className="text-sm text-gray-500">{security.sector}</p>
          </div>

          <div className="flex flex-col items-end gap-2">
            {latestClose != null ? (
              <div className="text-right">
                <p className="text-2xl font-bold text-gray-900">
                  PKR {formatPrice(latestClose)}
                </p>
                {dayChange != null && dayChangePct != null && (
                  <p className={`text-sm font-medium ${isPositive ? "text-green-600" : "text-red-600"}`}>
                    {isPositive ? "+" : ""}{dayChange.toFixed(2)} ({isPositive ? "+" : ""}{dayChangePct.toFixed(2)}%)
                    <span className="ml-1 text-xs font-normal text-gray-400">1D</span>
                  </p>
                )}
                {latest?.date && (
                  <p className="text-xs text-gray-400">As of {latest.date}</p>
                )}
              </div>
            ) : (
              <p className="text-sm text-gray-400">Price unavailable</p>
            )}
            <div className="flex flex-wrap gap-2">
              <WatchlistButton symbol={symbol} />
              <TradeEntryModal
                trigger={<Button variant="outline">+ Record trade</Button>}
                defaultSymbol={symbol}
                defaultPrice={latest?.close ?? undefined}
              />
            </div>
          </div>
        </div>
      </div>

      {/* ── Price Chart ───────────────────────────────────────────────── */}
      <div className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
        <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-gray-500">
          Price History
        </h2>
        <PriceChart symbol={symbol} />
      </div>

      {/* ── Quick Stats Grid ─────────────────────────────────────────── */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatCard
          label="Market Cap"
          value={formatMarketCap(
            fundamentals?.market_cap_pkr ?? security.market_cap_pkr,
          )}
          tooltip="Total market value of all shares outstanding. Larger market cap generally means more established company."
        />
        <StatCard
          label="P/E Ratio"
          value={formatDecimal(fundamentals?.pe_ratio)}
          tooltip="Price-to-Earnings: how much investors pay per PKR 1 of annual earnings. A P/E of 10 means investors pay PKR 10 for every PKR 1 the company earns per year."
        />
        <StatCard
          label="P/B Ratio"
          value={formatDecimal(fundamentals?.pb_ratio)}
          tooltip="Price-to-Book: share price divided by book value per share. Below 1 may indicate undervaluation relative to assets."
        />
        <StatCard
          label="Dividend Yield"
          value={
            fundamentals?.dividend_yield
              ? `${formatDecimal(fundamentals.dividend_yield)}%`
              : "—"
          }
          tooltip="Annual dividend payments as a percentage of the current share price. Higher yield means more income per rupee invested."
        />
        <StatCard
          label="EPS"
          value={
            fundamentals?.eps ? `PKR ${formatDecimal(fundamentals.eps)}` : "—"
          }
          tooltip="Earnings Per Share: company's net profit divided by number of shares. A key measure of profitability."
        />
        <StatCard
          label="ROE"
          value={
            fundamentals?.roe ? `${formatDecimal(fundamentals.roe)}%` : "—"
          }
          tooltip="Return on Equity: how much profit is generated per rupee of shareholder equity. Higher ROE generally indicates a more efficient business."
        />
        <StatCard
          label="52-Week Range"
          value={
            fundamentals?.week_52_high && fundamentals?.week_52_low
              ? `${formatPrice(fundamentals.week_52_low)} – ${formatPrice(fundamentals.week_52_high)}`
              : "—"
          }
          tooltip="The lowest and highest closing prices over the past 52 weeks. Useful for judging current price relative to recent history."
        />
        <StatCard
          label="Avg Volume (30D)"
          value={formatVolume(fundamentals?.avg_volume_30d)}
          tooltip="Average number of shares traded per day over the past 30 days. Higher volume generally means easier to buy or sell without moving the price."
        />
      </div>

      {/* ── Tabs ─────────────────────────────────────────────────────── */}
      <Tabs defaultValue="overview">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="indicators">Indicators</TabsTrigger>
          <TabsTrigger value="announcements">Announcements</TabsTrigger>
        </TabsList>

        <TabsContent value="indicators">
          <IndicatorPanel symbol={symbol} />
        </TabsContent>

        <TabsContent value="overview">
          <Card>
            <CardHeader>
              <CardTitle>Company Overview</CardTitle>
            </CardHeader>
            <CardContent>
              <dl className="grid grid-cols-2 gap-x-6 gap-y-3 text-sm sm:grid-cols-3">
                <OverviewRow label="Symbol" value={security.symbol} />
                <OverviewRow label="Company" value={security.company_name} />
                <OverviewRow label="Sector" value={security.sector} />
                <OverviewRow
                  label="Shares Outstanding"
                  value={
                    security.shares_outstanding
                      ? formatVolume(security.shares_outstanding)
                      : "—"
                  }
                />
                <OverviewRow
                  label="KSE-100"
                  value={security.is_kse100 ? "Yes" : "No"}
                />
                <OverviewRow
                  label="KSE-30"
                  value={security.is_kse30 ? "Yes" : "No"}
                />
                <OverviewRow
                  label="KMI-30 Halal"
                  value={security.is_kmi_compliant ? "Yes" : "No"}
                />
              </dl>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="announcements">
          <Card>
            <CardHeader>
              <CardTitle>Corporate Actions</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              {!announcements || announcements.items.length === 0 ? (
                <p className="px-4 py-6 text-center text-sm text-gray-500">
                  No announcements on record.
                </p>
              ) : (
                <table className="w-full text-sm">
                  <thead className="border-b border-gray-200 bg-gray-50 text-xs font-medium uppercase tracking-wide text-gray-500">
                    <tr>
                      <th className="px-4 py-3 text-left">Type</th>
                      <th className="px-4 py-3 text-left">Announced</th>
                      <th className="px-4 py-3 text-left">Ex-Date</th>
                      <th className="px-4 py-3 text-right">Amount / Ratio</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {announcements.items.map((a) => (
                      <tr key={a.id} className="hover:bg-gray-50">
                        <td className="px-4 py-2.5 font-medium text-gray-800">
                          {a.action_type}
                        </td>
                        <td className="px-4 py-2.5 text-gray-600">
                          {a.announcement_date}
                        </td>
                        <td className="px-4 py-2.5 text-gray-600">
                          {a.ex_date ?? "—"}
                        </td>
                        <td className="px-4 py-2.5 text-right text-gray-800">
                          {a.amount_per_share
                            ? `PKR ${formatDecimal(a.amount_per_share)}`
                            : a.ratio_numerator != null && a.ratio_denominator != null
                            ? `${a.ratio_numerator}:${a.ratio_denominator}`
                            : "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}

// ── Local sub-components ────────────────────────────────────────────────────

function StatCard({
  label,
  value,
  tooltip,
}: {
  label: string;
  value: string;
  tooltip: string;
}) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
      <div className="flex items-center gap-1 text-xs font-medium uppercase tracking-wide text-gray-500">
        {label}
        <Tooltip content={tooltip}>
          <Info className="h-3.5 w-3.5 cursor-help text-gray-400 hover:text-gray-600" />
        </Tooltip>
      </div>
      <p className="mt-1.5 text-base font-semibold text-gray-900">{value}</p>
    </div>
  );
}

function OverviewRow({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs font-medium text-gray-500">{label}</dt>
      <dd className="mt-0.5 text-gray-900">{value}</dd>
    </div>
  );
}
