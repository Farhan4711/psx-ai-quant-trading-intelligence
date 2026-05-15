"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { fetchBenchmarkPanel } from "@/lib/api/community";
import { Users } from "lucide-react";
import { formatPercent } from "@/lib/utils/format";

export function BenchmarkPanel() {
  const { data, isLoading } = useQuery({
    queryKey: ["benchmark"],
    queryFn: fetchBenchmarkPanel,
    staleTime: 5 * 60_000,
    retry: false,
  });

  if (isLoading || !data) {
    return <div className="h-32 animate-pulse rounded-lg bg-gray-100" />;
  }

  if (!data.available) {
    return (
      <div className="rounded-lg border border-gray-200 bg-gray-50 p-4">
        <div className="mb-2 flex items-center gap-2 text-gray-700">
          <Users className="h-4 w-4" />
          <h3 className="text-sm font-semibold uppercase tracking-wider">
            How I compare
          </h3>
        </div>
        <p className="text-sm text-gray-600">
          {data.message ??
            "Benchmark not available yet — opt in to anonymized data sharing in Settings."}
        </p>
        <Link
          href="/settings"
          className="mt-2 inline-block text-xs text-blue-600 hover:underline"
        >
          Manage in Settings →
        </Link>
      </div>
    );
  }

  const userYtd = data.user_ytd_return_pct ?? 0;
  const peerYtd = data.median_ytd_return_pct ?? 0;
  const beat = userYtd > peerYtd;

  return (
    <div className="rounded-lg border border-blue-200 bg-blue-50 p-4">
      <div className="mb-2 flex items-center gap-2 text-blue-900">
        <Users className="h-4 w-4" />
        <h3 className="text-sm font-semibold uppercase tracking-wider">
          How I compare
        </h3>
      </div>
      <p className="text-xs text-blue-700">
        {data.bucket_label} · n = {data.sample_count}
      </p>

      <div className="mt-3 space-y-2 text-sm">
        <div className="flex items-baseline justify-between">
          <span className="text-blue-900">Your YTD return:</span>
          <span
            className={
              "font-semibold tabular-nums " +
              (userYtd >= 0 ? "text-green-700" : "text-red-700")
            }
          >
            {formatPercent(userYtd)}
          </span>
        </div>
        <div className="flex items-baseline justify-between">
          <span className="text-blue-900">Peer median:</span>
          <span className="font-semibold tabular-nums text-blue-900">
            {formatPercent(peerYtd)}
          </span>
        </div>
        {data.percentile_rank != null && (
          <div className="flex items-baseline justify-between">
            <span className="text-blue-900">Your percentile:</span>
            <span className="font-semibold tabular-nums text-blue-900">
              {data.percentile_rank}th
            </span>
          </div>
        )}
      </div>

      {data.user_top_sector && data.peer_top_sector && (
        <p className="mt-3 text-xs text-blue-800">
          Your top sector: <strong>{data.user_top_sector}</strong>{" "}
          ({data.user_top_sector_pct?.toFixed(0)}%). Peers&apos; top:{" "}
          <strong>{data.peer_top_sector}</strong>{" "}
          ({data.peer_top_sector_pct?.toFixed(0)}%).
        </p>
      )}

      <p className="mt-3 text-xs text-blue-700">
        {beat
          ? "You're outpacing peers in your bucket — keep an eye on whether you're taking on more risk to do it."
          : "Peers in your bucket are doing better on average. Compare top holdings or sector tilt to see what's different."}
      </p>
    </div>
  );
}
