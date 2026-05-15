import { createApiClient } from "@psx/shared";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const api = createApiClient({ baseUrl: API_URL });

// Local extension: psx-shared exposes a narrow curated `PredictionResponse`,
// but this UI also reads sub-model probabilities + horizon for the
// "How does this work?" explainer. Once those become part of the public
// contract (Step 105 swap to real models), we'll fold them into shared.

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
  api.get<Prediction>(
    `/api/v1/securities/${symbol}/prediction?horizon_days=${horizon}`,
  );
