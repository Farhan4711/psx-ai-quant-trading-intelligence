"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { fetchAlertsForUser, type SuspiciousDay } from "@/lib/api/alerts";
import { AlertTriangle, Newspaper } from "lucide-react";

const SEVERITY_TONE: Record<string, string> = {
  high: "border-red-300 bg-red-50",
  medium: "border-amber-300 bg-amber-50",
  low: "border-yellow-200 bg-yellow-50",
};

const SEVERITY_LABEL: Record<string, string> = {
  high: "text-red-800",
  medium: "text-amber-800",
  low: "text-yellow-800",
};

export default function AlertsPage() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["alerts"],
    queryFn: () => fetchAlertsForUser(50),
    staleTime: 60_000,
    refetchInterval: 5 * 60_000,
  });

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Alerts</h1>
        <p className="mt-1 text-sm text-gray-500">
          Pump-and-dump warnings for stocks you hold or watch. Severity reflects
          how much of the move can be explained by announced news.
        </p>
      </div>

      {isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-20 animate-pulse rounded-md bg-gray-100" />
          ))}
        </div>
      ) : isError ? (
        <p className="text-sm text-red-600">Failed to load alerts.</p>
      ) : !data || data.length === 0 ? (
        <EmptyState />
      ) : (
        <ul className="space-y-3">
          {data.map((a) => (
            <AlertCard key={a.id} alert={a} />
          ))}
        </ul>
      )}
    </div>
  );
}

function AlertCard({ alert }: { alert: SuspiciousDay }) {
  return (
    <li
      className={`rounded-lg border p-4 ${SEVERITY_TONE[alert.severity] ?? SEVERITY_TONE.low}`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-2">
          <AlertTriangle className="mt-0.5 h-5 w-5 text-gray-700" />
          <div>
            <div className="flex flex-wrap items-baseline gap-2">
              <Link
                href={`/app/stocks/${alert.symbol}`}
                className="font-mono text-base font-semibold text-blue-700 hover:underline"
              >
                {alert.symbol}
              </Link>
              <span className="text-xs font-medium uppercase tracking-wider text-gray-700">
                {alert.alert_type}
              </span>
              <span
                className={`rounded-full bg-white px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider ${SEVERITY_LABEL[alert.severity] ?? SEVERITY_LABEL.low}`}
              >
                {alert.severity}
              </span>
            </div>
            <p className="mt-1 text-sm text-gray-800">{alert.explanation}</p>
            <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-gray-600">
              <span>Date: {alert.alert_date}</span>
              <span>Vol spike: {parseFloat(alert.vol_spike).toFixed(2)}×</span>
              <span>
                Price: {parseFloat(alert.price_change_pct) >= 0 ? "+" : ""}
                {parseFloat(alert.price_change_pct).toFixed(2)}%
              </span>
              {alert.anomaly_score && (
                <span>Anomaly: {parseFloat(alert.anomaly_score).toFixed(2)}σ</span>
              )}
              {alert.has_news_context && (
                <span className="inline-flex items-center gap-1 text-emerald-700">
                  <Newspaper className="h-3 w-3" />
                  News context
                </span>
              )}
            </div>
          </div>
        </div>
      </div>
    </li>
  );
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-lg border border-dashed border-gray-300 bg-white py-16 text-center">
      <div className="text-3xl">🛡️</div>
      <h2 className="text-lg font-semibold text-gray-900">All clear</h2>
      <p className="max-w-sm text-sm text-gray-500">
        No pump/dump alerts on stocks you hold or watch right now. We re-check
        every 5 minutes during market hours.
      </p>
    </div>
  );
}
