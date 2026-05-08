const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function apiFetch<T>(path: string): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    credentials: "include",
    headers: { "Content-Type": "application/json" },
  });
  if (!res.ok) {
    const err = (await res.json().catch(() => ({ detail: res.statusText }))) as {
      detail?: string;
    };
    throw new Error(err.detail ?? "Request failed");
  }
  return res.json() as Promise<T>;
}

export interface MetricDef {
  key: string;
  label: string;
  format: "mcap" | "price" | "pct" | "decimal";
  rankable: boolean;
  rank_higher_is_better?: boolean;
}

export interface CompareItem {
  symbol: string;
  company_name: string | null;
  is_kmi_compliant?: boolean;
  missing: boolean;
  reason?: string;
  metrics?: Record<string, string | number | null>;
  ranks?: Record<string, number | null>;
}

export interface CompareResponse {
  sector: string;
  constituent_count: number;
  items: CompareItem[];
  metric_definitions: MetricDef[];
}

export interface HeatmapItem {
  symbol: string;
  company_name: string;
  sector: string;
  is_kmi_compliant: boolean;
  market_cap_pkr: number | null;
  last_close: number | null;
  day_change_pct: number | null;
}

export const fetchSectorCompare = (sector: string, symbols: string[]) =>
  apiFetch<CompareResponse>(
    `/api/v1/sectors/${encodeURIComponent(sector)}/compare?symbols=${symbols.join(",")}`,
  );

export const fetchSectorHeatmap = (sector?: string) => {
  const qs = sector ? `?sector=${encodeURIComponent(sector)}` : "";
  return apiFetch<HeatmapItem[]>(`/api/v1/sectors/heatmap${qs}`);
};
