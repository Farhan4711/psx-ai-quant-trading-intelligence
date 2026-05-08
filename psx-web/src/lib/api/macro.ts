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

export interface MacroIndicatorMeta {
  key: string;
  label: string;
  unit: string;
  category: string;
}

export interface MacroSeriesPoint {
  date: string;
  value: number;
}

export const fetchMacroIndicators = () =>
  apiFetch<MacroIndicatorMeta[]>("/api/v1/macro/indicators");

export const fetchMacroSeries = (
  indicator: string,
  dateFrom?: string,
  dateTo?: string,
) => {
  const qs = new URLSearchParams();
  if (dateFrom) qs.set("date_from", dateFrom);
  if (dateTo) qs.set("date_to", dateTo);
  const suffix = qs.toString() ? `?${qs.toString()}` : "";
  return apiFetch<MacroSeriesPoint[]>(`/api/v1/macro/series/${indicator}${suffix}`);
};
