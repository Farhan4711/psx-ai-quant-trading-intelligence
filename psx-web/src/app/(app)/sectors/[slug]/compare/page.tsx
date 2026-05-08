"use client";

import { useMemo, useState } from "react";
import { useParams, useSearchParams, useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { fetchSecurities } from "@/lib/api/securities";
import {
  fetchSectorCompare,
  type CompareItem,
  type MetricDef,
} from "@/lib/api/sectors";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  formatCurrency,
  formatDecimal,
  formatMarketCap,
  formatPercent,
  formatPrice,
} from "@/lib/utils/format";
import { X } from "lucide-react";

export default function SectorComparePage() {
  const params = useParams<{ slug: string }>();
  const router = useRouter();
  const searchParams = useSearchParams();
  const sector = decodeURIComponent(params.slug);

  const initial = (searchParams.get("symbols") ?? "")
    .split(",")
    .filter(Boolean)
    .map((s) => s.toUpperCase());
  const [picks, setPicks] = useState<string[]>(initial);

  const { data: comparison, isLoading } = useQuery({
    queryKey: ["sector-compare", sector, picks.join(",")],
    queryFn: () => fetchSectorCompare(sector, picks),
    enabled: picks.length >= 2,
    staleTime: 300_000,
  });

  // Sector universe for the picker
  const { data: universe } = useQuery({
    queryKey: ["securities", "by-sector", sector],
    queryFn: () => fetchSecurities({ sector, page_size: 200 }),
    staleTime: 300_000,
  });

  function togglePick(sym: string) {
    setPicks((prev) => {
      if (prev.includes(sym)) return prev.filter((s) => s !== sym);
      if (prev.length >= 4) return prev;
      const next = [...prev, sym];
      const qs = new URLSearchParams({ symbols: next.join(",") });
      router.replace(`?${qs.toString()}`, { scroll: false });
      return next;
    });
  }

  const items = comparison?.items ?? [];
  const metrics = comparison?.metric_definitions ?? [];

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">
          Compare — {sector}
        </h1>
        <p className="mt-1 text-sm text-gray-500">
          Pick 2–4 stocks. Each metric is ranked against the entire {sector} sector.
        </p>
      </div>

      {/* Picker */}
      <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
        <div className="mb-2 flex flex-wrap gap-2">
          {picks.length === 0 ? (
            <p className="text-sm text-gray-500">Select 2–4 stocks below to compare.</p>
          ) : (
            picks.map((sym) => (
              <span
                key={sym}
                className="inline-flex items-center gap-1 rounded-full bg-blue-100 px-3 py-0.5 text-sm font-medium text-blue-800"
              >
                {sym}
                <button
                  onClick={() => togglePick(sym)}
                  className="rounded-full hover:bg-blue-200"
                  aria-label={`Remove ${sym}`}
                >
                  <X className="h-3 w-3" />
                </button>
              </span>
            ))
          )}
        </div>
        <div className="flex flex-wrap gap-1.5">
          {(universe?.items ?? []).map((s) => {
            const selected = picks.includes(s.symbol);
            const disabled = !selected && picks.length >= 4;
            return (
              <button
                key={s.symbol}
                onClick={() => togglePick(s.symbol)}
                disabled={disabled}
                className={
                  "rounded-md border px-2.5 py-1 text-xs transition " +
                  (selected
                    ? "border-blue-600 bg-blue-50 text-blue-700"
                    : "border-gray-200 bg-white text-gray-700 hover:bg-gray-50 disabled:opacity-40")
                }
              >
                {s.symbol}
              </button>
            );
          })}
        </div>
      </div>

      {picks.length < 2 ? (
        <p className="text-sm text-gray-500">Pick at least two stocks.</p>
      ) : isLoading || !comparison ? (
        <div className="h-48 animate-pulse rounded-lg bg-gray-100" />
      ) : (
        <CompareTable items={items} metrics={metrics} />
      )}
    </div>
  );
}

function CompareTable({ items, metrics }: { items: CompareItem[]; metrics: MetricDef[] }) {
  return (
    <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white shadow-sm">
      <table className="min-w-full divide-y divide-gray-200 text-sm">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-4 py-2 text-left text-xs font-medium uppercase tracking-wide text-gray-500">
              Metric
            </th>
            {items.map((it) => (
              <th
                key={it.symbol}
                className="px-4 py-2 text-right text-xs font-medium uppercase tracking-wide text-gray-500"
              >
                <span className="font-mono font-semibold text-blue-700">
                  {it.symbol}
                </span>
                {it.is_kmi_compliant && <Badge variant="kmi" className="ml-1">KMI</Badge>}
                {it.company_name && (
                  <p className="mt-0.5 truncate text-[10px] font-normal text-gray-500">
                    {it.company_name}
                  </p>
                )}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {metrics.map((m) => (
            <tr key={m.key}>
              <td className="px-4 py-2.5 text-left font-medium text-gray-700">
                {m.label}
              </td>
              {items.map((it) => {
                if (it.missing) {
                  return (
                    <td key={it.symbol} className="px-4 py-2.5 text-right text-xs text-red-500">
                      {it.reason ?? "—"}
                    </td>
                  );
                }
                const raw = it.metrics?.[m.key];
                const rank = it.ranks?.[m.key.replace("_pkr", "")];
                return (
                  <td
                    key={it.symbol}
                    className="px-4 py-2.5 text-right tabular-nums"
                  >
                    {formatMetric(raw, m)}
                    {rank != null && (
                      <p className="mt-0.5 text-[10px] text-gray-500">
                        better than {rank}% of sector
                      </p>
                    )}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function formatMetric(value: string | number | null | undefined, m: MetricDef): string {
  if (value == null || value === "") return "—";
  const n = typeof value === "string" ? parseFloat(value) : Number(value);
  if (Number.isNaN(n)) return "—";
  switch (m.format) {
    case "mcap":
      return formatMarketCap(n);
    case "price":
      return formatPrice(n);
    case "pct":
      return formatPercent(n);
    case "decimal":
      return formatDecimal(String(n));
    default:
      return String(value);
  }
}
