"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchNewsPulse } from "@/lib/api/alerts";
import { Newspaper, ExternalLink } from "lucide-react";

export function NewsPulse({ symbol }: { symbol: string }) {
  const { data, isLoading } = useQuery({
    queryKey: ["news-pulse", symbol],
    queryFn: () => fetchNewsPulse(symbol),
    staleTime: 30 * 60_000,
    retry: false,
  });

  if (isLoading) {
    return <div className="h-32 animate-pulse rounded-lg bg-gray-100" />;
  }
  if (!data) return null;

  // Map score [-100..+100] → 0..100% bar position
  const center = 50 + data.score / 2;
  const barColor =
    data.score >= 30
      ? "bg-green-500"
      : data.score >= 0
      ? "bg-emerald-400"
      : data.score >= -30
      ? "bg-amber-400"
      : "bg-red-500";

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
      <div className="flex items-center gap-2">
        <Newspaper className="h-4 w-4 text-gray-500" />
        <h3 className="text-sm font-semibold uppercase tracking-wider text-gray-700">
          News Pulse (5-day)
        </h3>
      </div>

      {/* Score bar — from -100 (left) to +100 (right) */}
      <div className="mt-3">
        <div className="flex items-baseline justify-between text-xs">
          <span className="text-red-600">−100</span>
          <span
            className={`text-base font-bold tabular-nums ${
              data.score >= 0 ? "text-green-700" : "text-red-700"
            }`}
          >
            {data.score >= 0 ? "+" : ""}
            {data.score.toFixed(0)}
          </span>
          <span className="text-green-600">+100</span>
        </div>
        <div className="relative mt-1 h-2 overflow-hidden rounded-full bg-gray-100">
          <div className="absolute left-1/2 top-0 h-full w-px bg-gray-300" />
          <div
            className={`absolute top-0 h-full ${barColor}`}
            style={{
              left: `${Math.min(50, center)}%`,
              right: `${Math.max(0, 100 - center)}%`,
            }}
          />
        </div>
      </div>

      <p className="mt-2 text-sm text-gray-700">{data.explainer}</p>

      {data.top_articles.length > 0 && (
        <ul className="mt-3 space-y-2 border-t border-gray-100 pt-3">
          {data.top_articles.map((a) => {
            const polarity = a.polarity ? parseFloat(a.polarity) : 0;
            const tone =
              polarity > 0.2
                ? "text-green-700"
                : polarity < -0.2
                ? "text-red-700"
                : "text-gray-500";
            return (
              <li key={a.id} className="text-xs">
                <a
                  href={a.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="group flex items-start gap-1.5"
                >
                  <span className={`flex-shrink-0 ${tone}`}>
                    {polarity > 0.2 ? "▲" : polarity < -0.2 ? "▼" : "•"}
                  </span>
                  <span className="flex-1 text-gray-800 group-hover:underline">
                    {a.headline}
                  </span>
                  <ExternalLink className="mt-0.5 h-3 w-3 flex-shrink-0 text-gray-300 group-hover:text-gray-500" />
                </a>
                <p className="ml-3.5 mt-0.5 text-[10px] text-gray-400">
                  {a.source} · {new Date(a.published_at).toLocaleDateString()}
                </p>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
