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

export interface KeyFeature {
  name: string;
  value: number | null;
  contribution: "positive" | "negative" | "neutral";
}

export interface Prediction {
  symbol: string;
  as_of_date: string | null;
  horizon_days?: number;
  probability_up?: number;
  confidence?: "high" | "medium" | "low";
  confidence_score?: number;
  model_version: string;
  sub_model_probabilities?: Record<string, number>;
  key_features?: KeyFeature[];
  live_accuracy_pct?: number | null;
  predictions_disabled: boolean;
  reason?: string;
}

export const fetchPrediction = (symbol: string, horizon = 1) =>
  apiFetch<Prediction>(
    `/api/v1/securities/${symbol}/prediction?horizon_days=${horizon}`,
  );
