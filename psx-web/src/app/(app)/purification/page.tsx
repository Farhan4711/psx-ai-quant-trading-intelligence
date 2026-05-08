"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  fetchPurificationReport,
  markPurificationDonated,
  type PurificationLine,
} from "@/lib/api/community";
import { fetchCurrentUser } from "@/lib/api/auth";
import { Sparkles } from "lucide-react";
import { formatCurrency } from "@/lib/utils/format";

export default function PurificationPage() {
  const queryClient = useQueryClient();
  const thisYear = new Date().getFullYear();
  const [year, setYear] = useState(thisYear);

  const { data: user } = useQuery({
    queryKey: ["current-user"],
    queryFn: fetchCurrentUser,
    staleTime: 5 * 60_000,
    retry: false,
  });

  const { data, isLoading } = useQuery({
    queryKey: ["purification-report", year],
    queryFn: () => fetchPurificationReport(year),
    enabled: !!user,
    retry: false,
  });

  const mark = useMutation({
    mutationFn: ({ symbol, donated }: { symbol: string; donated: boolean }) =>
      markPurificationDonated(year, symbol, donated),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["purification-report", year] });
    },
  });

  if (!user?.shariah_mode) {
    return <NotShariahMode />;
  }
  if (isLoading || !data) {
    return <div className="h-48 animate-pulse rounded-lg bg-gray-100" />;
  }

  const totalDiv = parseFloat(data.total_dividends_pkr);
  const totalPur = parseFloat(data.total_purification_pkr);

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            Dividend purification
          </h1>
          <p className="mt-1 text-sm text-gray-500">
            5% of cash dividends from KMI-compliant stocks is the standard
            purification rate used by Pakistani Shariah funds.
          </p>
        </div>
        <select
          value={year}
          onChange={(e) => setYear(parseInt(e.target.value))}
          className="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-600"
        >
          {[thisYear, thisYear - 1, thisYear - 2].map((y) => (
            <option key={y} value={y}>
              FY {y}
            </option>
          ))}
        </select>
      </div>

      {totalDiv === 0 ? (
        <EmptyState year={year} />
      ) : (
        <>
          <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-5 text-center">
            <Sparkles className="mx-auto h-6 w-6 text-emerald-600" />
            <p className="mt-2 text-xs uppercase tracking-wider text-emerald-700">
              Total purification owed for FY {data.fiscal_year}
            </p>
            <p className="mt-1 text-3xl font-bold tabular-nums text-emerald-900">
              {formatCurrency(totalPur)}
            </p>
            <p className="mt-1 text-xs text-emerald-800">
              From {formatCurrency(totalDiv)} in dividends · {data.purification_pct}% rate
            </p>
          </div>

          <div className="overflow-hidden rounded-lg border border-gray-200 bg-white shadow-sm">
            <table className="min-w-full divide-y divide-gray-200 text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-2 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                    Symbol
                  </th>
                  <th className="px-4 py-2 text-right text-xs font-medium uppercase tracking-wider text-gray-500">
                    Dividends
                  </th>
                  <th className="px-4 py-2 text-right text-xs font-medium uppercase tracking-wider text-gray-500">
                    Purification (5%)
                  </th>
                  <th className="px-4 py-2 text-right text-xs font-medium uppercase tracking-wider text-gray-500">
                    Donated
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {data.lines.map((line) => (
                  <Row
                    key={line.symbol}
                    line={line}
                    onToggle={(donated) =>
                      mark.mutate({ symbol: line.symbol, donated })
                    }
                  />
                ))}
              </tbody>
            </table>
          </div>

          <p className="text-xs text-gray-500">
            This is informational. Always verify with your local Shariah scholar
            for personal rulings, especially on edge cases like rights issues
            and bonus shares.
          </p>
        </>
      )}
    </div>
  );
}

function Row({
  line,
  onToggle,
}: {
  line: PurificationLine;
  onToggle: (donated: boolean) => void;
}) {
  return (
    <tr>
      <td className="px-4 py-2.5 font-mono font-semibold text-blue-700">
        {line.symbol}
      </td>
      <td className="px-4 py-2.5 text-right tabular-nums">
        {formatCurrency(parseFloat(line.dividends_pkr))}
      </td>
      <td className="px-4 py-2.5 text-right tabular-nums font-semibold text-emerald-700">
        {formatCurrency(parseFloat(line.purification_amount_pkr))}
      </td>
      <td className="px-4 py-2.5 text-right">
        <input
          type="checkbox"
          checked={line.marked_donated}
          onChange={(e) => onToggle(e.target.checked)}
          className="h-4 w-4 rounded text-emerald-600 focus:ring-emerald-500"
        />
      </td>
    </tr>
  );
}

function EmptyState({ year }: { year: number }) {
  return (
    <div className="flex flex-col items-center gap-3 rounded-lg border border-dashed border-gray-300 bg-white py-12 text-center">
      <div className="text-3xl">🌙</div>
      <h2 className="text-lg font-semibold text-gray-900">
        No KMI dividends in FY {year}
      </h2>
      <p className="max-w-sm text-sm text-gray-500">
        Once your portfolio receives cash dividends from KMI-compliant
        holdings, they&apos;ll appear here for purification calculation.
      </p>
    </div>
  );
}

function NotShariahMode() {
  return (
    <div className="space-y-3">
      <h1 className="text-2xl font-bold text-gray-900">Dividend purification</h1>
      <div className="rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
        Enable Shariah Mode in <a className="underline" href="/app/settings">Settings</a>{" "}
        to use the purification calculator.
      </div>
    </div>
  );
}
