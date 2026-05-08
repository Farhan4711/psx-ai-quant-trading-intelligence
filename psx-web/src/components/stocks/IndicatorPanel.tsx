"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  fetchIndicator,
  fetchIndicatorList,
  type IndicatorMeta,
} from "@/lib/api/securities";
import { ChevronDown } from "lucide-react";

interface Props {
  symbol: string;
}

const SIGNAL_COLOR = {
  bullish: { dot: "bg-green-500", text: "text-green-700", label: "Bullish" },
  bearish: { dot: "bg-red-500", text: "text-red-700", label: "Bearish" },
  neutral: { dot: "bg-yellow-400", text: "text-yellow-700", label: "Neutral" },
} as const;

export function IndicatorPanel({ symbol }: Props) {
  const { data: list } = useQuery({
    queryKey: ["indicators", "list"],
    queryFn: fetchIndicatorList,
    staleTime: 86_400_000,
  });

  const [selected, setSelected] = useState<string>("rsi");
  const [explainerOpen, setExplainerOpen] = useState(false);

  const { data: reading, isLoading } = useQuery({
    queryKey: ["indicator", symbol, selected],
    queryFn: () => fetchIndicator(symbol, selected),
    enabled: !!symbol,
    staleTime: 3_600_000,
  });

  const grouped = groupByCategory(list ?? []);

  return (
    <div className="space-y-4">
      {/* Indicator picker */}
      <div className="flex flex-wrap items-center gap-2">
        <label className="text-sm text-gray-600">Indicator:</label>
        <select
          value={selected}
          onChange={(e) => {
            setSelected(e.target.value);
            setExplainerOpen(false);
          }}
          className="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-600"
        >
          {Object.entries(grouped).map(([cat, items]) => (
            <optgroup key={cat} label={cat.charAt(0).toUpperCase() + cat.slice(1)}>
              {items.map((i) => (
                <option key={i.key} value={i.key}>
                  {i.label}
                </option>
              ))}
            </optgroup>
          ))}
        </select>
      </div>

      {/* Reading card */}
      {isLoading || !reading ? (
        <div className="h-32 animate-pulse rounded-lg bg-gray-100" />
      ) : (
        <div className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <span
                className={`h-3 w-3 rounded-full ${SIGNAL_COLOR[reading.signal].dot}`}
                aria-hidden
              />
              <span className={`text-sm font-semibold ${SIGNAL_COLOR[reading.signal].text}`}>
                {SIGNAL_COLOR[reading.signal].label}
              </span>
            </div>
            {reading.as_of && (
              <span className="text-xs text-gray-400">As of {reading.as_of}</span>
            )}
          </div>

          {/* Numeric readout */}
          <div className="mt-3 flex flex-wrap gap-4 text-sm">
            {Object.entries(reading.value).map(([k, v]) => (
              <div key={k}>
                <span className="text-gray-500">{k}: </span>
                <span className="font-mono font-medium text-gray-900">
                  {v == null ? "—" : typeof v === "number" ? v.toFixed(2) : String(v)}
                </span>
              </div>
            ))}
          </div>

          <p className="mt-3 text-sm text-gray-700">{reading.summary}</p>

          {reading.explainer && (
            <div className="mt-3">
              <button
                onClick={() => setExplainerOpen((o) => !o)}
                className="flex items-center gap-1 text-xs font-medium text-blue-700 hover:underline"
              >
                <ChevronDown
                  className={
                    "h-3 w-3 transition-transform " +
                    (explainerOpen ? "rotate-180" : "")
                  }
                />
                What is {reading.indicator.toUpperCase()}?
              </button>
              {explainerOpen && (
                <div className="mt-2 rounded-md border border-blue-100 bg-blue-50 p-3 text-xs leading-relaxed text-blue-900 prose-sm">
                  <Markdown text={reading.explainer} />
                </div>
              )}
            </div>
          )}

          <p className="mt-4 text-[10px] uppercase tracking-wide text-gray-400">
            For education only — not financial advice. Single indicators
            should never drive trade decisions.
          </p>
        </div>
      )}
    </div>
  );
}

function groupByCategory(list: IndicatorMeta[]): Record<string, IndicatorMeta[]> {
  return list.reduce<Record<string, IndicatorMeta[]>>((acc, item) => {
    (acc[item.category] = acc[item.category] ?? []).push(item);
    return acc;
  }, {});
}

// Tiny markdown renderer — handles only **bold** and paragraphs.
// Avoids pulling in a full markdown lib for this single use case.
function Markdown({ text }: { text: string }) {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return (
    <p>
      {parts.map((p, i) =>
        p.startsWith("**") && p.endsWith("**") ? (
          <strong key={i}>{p.slice(2, -2)}</strong>
        ) : (
          <span key={i}>{p}</span>
        ),
      )}
    </p>
  );
}
