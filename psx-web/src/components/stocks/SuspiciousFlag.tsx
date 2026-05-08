"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchSuspiciousState } from "@/lib/api/alerts";
import { AlertTriangle } from "lucide-react";

const SEVERITY_TONE: Record<string, string> = {
  high: "border-red-300 bg-red-50 text-red-900",
  medium: "border-amber-300 bg-amber-50 text-amber-900",
  low: "border-yellow-200 bg-yellow-50 text-yellow-900",
};

/**
 * Compact pump-and-dump warning surfaced on the stock detail header.
 * Renders nothing when there's no active flag.
 */
export function SuspiciousFlag({ symbol }: { symbol: string }) {
  const { data } = useQuery({
    queryKey: ["suspicious-state", symbol],
    queryFn: () => fetchSuspiciousState(symbol),
    staleTime: 5 * 60_000,
    retry: false,
  });

  if (!data?.has_active_alert || !data.latest) return null;
  const a = data.latest;

  return (
    <div
      className={`mt-3 flex items-start gap-2 rounded-md border px-3 py-2 text-sm ${SEVERITY_TONE[a.severity] ?? SEVERITY_TONE.low}`}
      role="alert"
    >
      <AlertTriangle className="mt-0.5 h-4 w-4 flex-shrink-0" />
      <div>
        <p className="font-medium">
          {a.alert_type === "pump" ? "Possible pump pattern" : "Possible dump pattern"}
          {" · "}
          <span className="text-xs uppercase tracking-wider">{a.severity}</span>
        </p>
        <p className="mt-0.5 text-xs">{a.explanation}</p>
        <p className="mt-1 text-[10px] text-gray-500">
          Detected {a.alert_date}. Be cautious — confirm with announcements before acting.
        </p>
      </div>
    </div>
  );
}
