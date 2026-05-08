"use client";

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { fetchSectorHeatmap, type HeatmapItem } from "@/lib/api/sectors";
import { fetchSectors } from "@/lib/api/securities";
import { formatMarketCap, formatPercent } from "@/lib/utils/format";

export default function SectorsPage() {
  const [sectorFilter, setSectorFilter] = useState<string>("");

  const { data: sectors } = useQuery({
    queryKey: ["sectors"],
    queryFn: fetchSectors,
    staleTime: 86_400_000,
  });

  const { data: items, isLoading } = useQuery({
    queryKey: ["sector-heatmap", sectorFilter],
    queryFn: () => fetchSectorHeatmap(sectorFilter || undefined),
    staleTime: 60_000,
    refetchInterval: 60_000,
  });

  const grouped = useMemo(() => groupBySector(items ?? []), [items]);

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Sector heatmap</h1>
          <p className="mt-1 text-sm text-gray-500">
            Each rectangle is a stock, sized by market cap, colored by today&apos;s change.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <label className="text-sm text-gray-600">Filter:</label>
          <select
            value={sectorFilter}
            onChange={(e) => setSectorFilter(e.target.value)}
            className="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-600"
          >
            <option value="">All sectors</option>
            {(sectors ?? []).map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </div>
      </div>

      {isLoading || !items ? (
        <div className="h-96 animate-pulse rounded-lg bg-gray-100" />
      ) : items.length === 0 ? (
        <p className="text-sm text-gray-500">No stocks to display.</p>
      ) : (
        <div className="space-y-4">
          {grouped.map(({ sector, stocks, sectorTotal }) => (
            <SectorRow
              key={sector}
              sector={sector}
              stocks={stocks}
              sectorTotal={sectorTotal}
            />
          ))}
        </div>
      )}

      <Legend />
    </div>
  );
}

// ── Subcomponents ──────────────────────────────────────────────────────

interface SectorGroup {
  sector: string;
  stocks: HeatmapItem[];
  sectorTotal: number;
}

function groupBySector(items: HeatmapItem[]): SectorGroup[] {
  const map = new Map<string, HeatmapItem[]>();
  for (const it of items) {
    const arr = map.get(it.sector) ?? [];
    arr.push(it);
    map.set(it.sector, arr);
  }
  return Array.from(map.entries())
    .map(([sector, stocks]) => ({
      sector,
      stocks: stocks.sort((a, b) => (b.market_cap_pkr ?? 0) - (a.market_cap_pkr ?? 0)),
      sectorTotal: stocks.reduce((acc, s) => acc + (s.market_cap_pkr ?? 0), 0),
    }))
    .sort((a, b) => b.sectorTotal - a.sectorTotal);
}

function SectorRow({ sector, stocks, sectorTotal }: SectorGroup) {
  return (
    <section className="rounded-lg border border-gray-200 bg-white p-3 shadow-sm">
      <div className="mb-2 flex items-center justify-between">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-700">
          {sector}
        </h2>
        <span className="text-xs text-gray-500">
          {stocks.length} stocks · {formatMarketCap(sectorTotal)}
        </span>
      </div>
      <div className="flex flex-wrap gap-1">
        {stocks.map((s) => (
          <Tile key={s.symbol} item={s} sectorTotal={sectorTotal} />
        ))}
      </div>
    </section>
  );
}

function Tile({ item, sectorTotal }: { item: HeatmapItem; sectorTotal: number }) {
  const share = sectorTotal > 0 ? (item.market_cap_pkr ?? 0) / sectorTotal : 0;
  // Convert mcap share into a flex grow + min-width so big stocks take more
  // visual real estate while tiny stocks remain readable.
  const grow = Math.max(share * 100, 0.5);
  const minWidth = Math.max(60, Math.min(200, 80 + share * 800));
  return (
    <Link
      href={`/app/stocks/${item.symbol}`}
      style={{
        flexGrow: grow,
        minWidth: `${minWidth}px`,
        backgroundColor: changeColor(item.day_change_pct),
      }}
      className="group flex h-20 flex-col justify-between rounded p-1.5 text-white transition hover:ring-2 hover:ring-blue-500"
      title={`${item.symbol} · ${item.company_name} · ${formatMarketCap(item.market_cap_pkr ?? 0)}`}
    >
      <span className="font-mono text-[11px] font-bold drop-shadow-sm">
        {item.symbol}
      </span>
      <span className="text-[10px] font-medium drop-shadow-sm">
        {item.day_change_pct == null ? "—" : formatPercent(item.day_change_pct)}
      </span>
    </Link>
  );
}

function changeColor(pct: number | null): string {
  if (pct == null) return "rgb(156,163,175)"; // gray
  // Clamp to ±5% for color saturation
  const clamped = Math.max(-5, Math.min(5, pct));
  if (clamped >= 0) {
    // 0..5  → light green to deep green
    const intensity = 0.3 + (clamped / 5) * 0.7;
    return `rgba(22,163,74,${intensity})`;
  }
  const intensity = 0.3 + (Math.abs(clamped) / 5) * 0.7;
  return `rgba(220,38,38,${intensity})`;
}

function Legend() {
  return (
    <div className="flex items-center gap-3 text-xs text-gray-500">
      <span>Day change:</span>
      <span className="flex items-center gap-1">
        <span className="h-3 w-3 rounded" style={{ backgroundColor: "rgba(220,38,38,0.9)" }} />
        ≤ -5%
      </span>
      <span className="flex items-center gap-1">
        <span className="h-3 w-3 rounded" style={{ backgroundColor: "rgba(220,38,38,0.4)" }} />
        -1%
      </span>
      <span className="flex items-center gap-1">
        <span className="h-3 w-3 rounded bg-gray-400" />
        flat
      </span>
      <span className="flex items-center gap-1">
        <span className="h-3 w-3 rounded" style={{ backgroundColor: "rgba(22,163,74,0.4)" }} />
        +1%
      </span>
      <span className="flex items-center gap-1">
        <span className="h-3 w-3 rounded" style={{ backgroundColor: "rgba(22,163,74,0.9)" }} />
        ≥ +5%
      </span>
    </div>
  );
}
