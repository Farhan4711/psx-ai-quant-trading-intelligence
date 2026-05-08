"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchPrediction, type KeyFeature } from "@/lib/api/predictions";
import { ChevronDown, AlertTriangle, Sparkles } from "lucide-react";

interface Props {
  symbol: string;
}

const FEATURE_LABEL: Record<string, string> = {
  log_return_5d: "5-day log return",
  log_return_10d: "10-day log return",
  momentum_10: "10-day momentum",
  disparity_5: "Disparity vs 5-day SMA",
  disparity_10: "Disparity vs 10-day SMA",
  rsi_14: "RSI (14)",
  williams_r_14: "Williams %R",
  macd_histogram: "MACD histogram",
  bollinger_pct_b: "Bollinger %B",
  kse100_return_pct: "KSE-100 same-day return",
  volume_z_20: "Volume Z-score (20-day)",
};

const CONTRIB_TONE: Record<string, string> = {
  positive: "text-green-700",
  negative: "text-red-700",
  neutral: "text-gray-500",
};

export function SignalPanel({ symbol }: Props) {
  const [explainerOpen, setExplainerOpen] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ["prediction", symbol],
    queryFn: () => fetchPrediction(symbol, 1),
    staleTime: 3_600_000, // 1h
    retry: false,
  });

  if (isLoading || !data) {
    return <div className="h-48 animate-pulse rounded-lg bg-gray-100" />;
  }

  // Disabled state — model unreliable / not enough history
  if (data.predictions_disabled) {
    return (
      <div className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
        <div className="flex items-center gap-2 text-gray-500">
          <AlertTriangle className="h-5 w-5" />
          <h3 className="text-sm font-semibold uppercase tracking-wider">
            Predictions disabled for this stock
          </h3>
        </div>
        <p className="mt-2 text-sm text-gray-600">
          {data.reason ??
            "Model performance on this symbol failed validation. We never show predictions when we don't trust them."}
        </p>
      </div>
    );
  }

  const prob = data.probability_up ?? 0.5;
  const probPct = Math.round(prob * 100);
  const direction = prob >= 0.5 ? "up" : "down";
  const directionWord = direction === "up" ? "upward" : "downward";
  const directionPct = direction === "up" ? probPct : 100 - probPct;
  const confidenceColor =
    data.confidence === "high"
      ? "bg-green-100 text-green-800"
      : data.confidence === "medium"
      ? "bg-yellow-100 text-yellow-800"
      : "bg-gray-100 text-gray-700";

  return (
    <div className="space-y-4 rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Sparkles className="h-5 w-5 text-blue-600" />
          <h3 className="text-sm font-semibold uppercase tracking-wider text-gray-700">
            Next-day signal
          </h3>
        </div>
        {data.as_of_date && (
          <span className="text-xs text-gray-400">As of {data.as_of_date}</span>
        )}
      </div>

      {/* Probability gauge */}
      <div>
        <div className="flex items-baseline justify-between">
          <p className="text-3xl font-bold tabular-nums text-gray-900">
            {directionPct}%
          </p>
          <span
            className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${confidenceColor}`}
          >
            {data.confidence ?? "—"} confidence
          </span>
        </div>
        <p className="mt-1 text-sm text-gray-600">
          chance of <strong>{directionWord}</strong> close tomorrow
        </p>
        <div className="mt-3 h-2 overflow-hidden rounded-full bg-gray-100">
          <div
            className={
              direction === "up" ? "h-full bg-green-500" : "h-full bg-red-500"
            }
            style={{ width: `${probPct}%` }}
          />
        </div>
        <div className="mt-1 flex justify-between text-[10px] uppercase tracking-wider text-gray-400">
          <span>Down</span>
          <span>50/50</span>
          <span>Up</span>
        </div>
      </div>

      {/* Key features */}
      {data.key_features && data.key_features.length > 0 && (
        <div>
          <h4 className="text-xs font-semibold uppercase tracking-wider text-gray-500">
            Top contributing features
          </h4>
          <ul className="mt-2 space-y-1.5">
            {data.key_features.map((f) => (
              <FeatureRow key={f.name} feature={f} />
            ))}
          </ul>
        </div>
      )}

      {/* Live accuracy */}
      {data.live_accuracy_pct != null && (
        <p className="text-xs text-gray-500">
          Past 30-day live accuracy on this stock:{" "}
          <strong>{data.live_accuracy_pct.toFixed(1)}%</strong>
        </p>
      )}

      {/* Disclaimer + explainer */}
      <div className="space-y-2 border-t border-gray-100 pt-3">
        <p className="text-xs text-gray-500">
          This is a probabilistic signal, not a guarantee or buy/sell
          instruction. Always combine with your own analysis.
        </p>
        <button
          onClick={() => setExplainerOpen((o) => !o)}
          className="flex items-center gap-1 text-xs font-medium text-blue-700 hover:underline"
        >
          <ChevronDown
            className={
              "h-3 w-3 transition-transform " + (explainerOpen ? "rotate-180" : "")
            }
          />
          How does this work?
        </button>
        {explainerOpen && (
          <div className="rounded-md border border-blue-100 bg-blue-50 p-3 text-xs leading-relaxed text-blue-900">
            <p>
              We compute a 23-feature daily snapshot for this stock — log
              returns, RSI, MACD, Bollinger %B, momentum, volume Z-score,
              and macro context (KSE-100, KIBOR, PKR/USD). Three sub-models
              with different biases (momentum / mean-reversion / trend) score
              the snapshot independently. A stacking layer combines them; the
              spread between sub-models drives confidence — the more they
              agree, the higher the confidence label.
            </p>
            <p className="mt-1.5">
              Model version: <code className="text-[10px]">{data.model_version}</code>.
              When real LSTM + XGBoost + RandomForest models replace the
              v0.1 heuristic, the signal API and this panel stay the same —
              only the underlying weights change.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

function FeatureRow({ feature }: { feature: KeyFeature }) {
  const label = FEATURE_LABEL[feature.name] ?? feature.name;
  const tone = CONTRIB_TONE[feature.contribution] ?? "text-gray-500";
  const formatted =
    feature.value == null
      ? "—"
      : Math.abs(feature.value) > 100
      ? feature.value.toFixed(0)
      : Math.abs(feature.value) > 1
      ? feature.value.toFixed(2)
      : feature.value.toFixed(4);
  return (
    <li className="flex items-center justify-between gap-2 text-xs">
      <span className="text-gray-700">{label}</span>
      <span className="flex items-center gap-2">
        <span className="font-mono text-gray-900">{formatted}</span>
        <span
          className={
            "rounded-full px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wider " +
            tone +
            " " +
            (feature.contribution === "positive"
              ? "bg-green-50"
              : feature.contribution === "negative"
              ? "bg-red-50"
              : "bg-gray-100")
          }
        >
          {feature.contribution}
        </span>
      </span>
    </li>
  );
}
