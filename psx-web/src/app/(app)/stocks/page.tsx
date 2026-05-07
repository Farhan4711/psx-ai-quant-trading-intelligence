"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchSecurities, fetchSectors } from "@/lib/api/securities";
import { Badge } from "@/components/ui/badge";
import Link from "next/link";
import { useState } from "react";
import { Search } from "lucide-react";

export default function StocksPage() {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [sector, setSector] = useState("");
  const [kmiOnly, setKmiOnly] = useState(false);
  const [kse100Only, setKse100Only] = useState(false);

  const { data, isLoading, isError } = useQuery({
    queryKey: ["securities", page, debouncedSearch, sector, kmiOnly, kse100Only],
    queryFn: () =>
      fetchSecurities({
        page,
        page_size: 50,
        search: debouncedSearch || undefined,
        sector: sector || undefined,
        kmi_only: kmiOnly || undefined,
        kse100_only: kse100Only || undefined,
      }),
  });

  const { data: sectors } = useQuery({
    queryKey: ["sectors"],
    queryFn: fetchSectors,
    staleTime: 3_600_000,
  });

  function handleSearchChange(val: string) {
    setSearch(val);
    clearTimeout((window as unknown as { _searchTimer?: ReturnType<typeof setTimeout> })._searchTimer);
    (window as unknown as { _searchTimer?: ReturnType<typeof setTimeout> })._searchTimer = setTimeout(() => {
      setDebouncedSearch(val);
      setPage(1);
    }, 300);
  }

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Stocks</h1>
        <p className="mt-1 text-sm text-gray-500">Browse and search all PSX-listed securities.</p>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-48 max-w-xs">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Search symbol or company…"
            value={search}
            onChange={(e) => handleSearchChange(e.target.value)}
            className="w-full rounded-md border border-gray-300 py-2 pl-9 pr-3 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>

        <select
          value={sector}
          onChange={(e) => { setSector(e.target.value); setPage(1); }}
          className="rounded-md border border-gray-300 py-2 pl-3 pr-8 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        >
          <option value="">All Sectors</option>
          {sectors?.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>

        <label className="flex cursor-pointer items-center gap-1.5 text-sm text-gray-700">
          <input
            type="checkbox"
            checked={kmiOnly}
            onChange={(e) => { setKmiOnly(e.target.checked); setPage(1); }}
            className="h-4 w-4 rounded border-gray-300 text-blue-600"
          />
          KMI Only
        </label>

        <label className="flex cursor-pointer items-center gap-1.5 text-sm text-gray-700">
          <input
            type="checkbox"
            checked={kse100Only}
            onChange={(e) => { setKse100Only(e.target.checked); setPage(1); }}
            className="h-4 w-4 rounded border-gray-300 text-blue-600"
          />
          KSE-100 Only
        </label>
      </div>

      {/* Table */}
      <div className="overflow-hidden rounded-lg border border-gray-200 bg-white shadow-sm">
        {isLoading ? (
          <div className="flex h-48 items-center justify-center text-sm text-gray-500">Loading…</div>
        ) : isError ? (
          <div className="flex h-48 items-center justify-center text-sm text-red-500">Failed to load securities.</div>
        ) : (
          <>
            <table className="w-full text-sm">
              <thead className="border-b border-gray-200 bg-gray-50 text-xs font-medium uppercase tracking-wide text-gray-500">
                <tr>
                  <th className="px-4 py-3 text-left">Symbol</th>
                  <th className="px-4 py-3 text-left">Company</th>
                  <th className="hidden px-4 py-3 text-left md:table-cell">Sector</th>
                  <th className="px-4 py-3 text-center">Indices</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {data?.items.map((s) => (
                  <tr
                    key={s.symbol}
                    className="transition-colors hover:bg-blue-50"
                  >
                    <td className="px-4 py-3 font-mono font-semibold">
                      <Link href={`/app/stocks/${s.symbol}`} className="text-blue-700 hover:underline">
                        {s.symbol}
                      </Link>
                    </td>
                    <td className="px-4 py-3 text-gray-800">
                      <Link href={`/app/stocks/${s.symbol}`} className="hover:text-blue-700">
                        {s.company_name}
                      </Link>
                    </td>
                    <td className="hidden px-4 py-3 text-gray-600 md:table-cell">{s.sector}</td>
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap justify-center gap-1">
                        {s.is_kmi_compliant && <Badge variant="kmi">KMI</Badge>}
                        {s.is_kse100 && <Badge variant="default">KSE-100</Badge>}
                        {s.is_kse30 && <Badge variant="outline">KSE-30</Badge>}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {/* Pagination */}
            <div className="flex items-center justify-between border-t border-gray-200 bg-gray-50 px-4 py-3 text-sm text-gray-600">
              <span>
                {data ? `${(page - 1) * 50 + 1}–${Math.min(page * 50, data.total)} of ${data.total}` : ""}
              </span>
              <div className="flex gap-2">
                <button
                  disabled={page === 1}
                  onClick={() => setPage((p) => p - 1)}
                  className="rounded-md border border-gray-300 px-3 py-1 text-xs hover:bg-white disabled:cursor-not-allowed disabled:opacity-50"
                >
                  Previous
                </button>
                <button
                  disabled={!data?.has_next}
                  onClick={() => setPage((p) => p + 1)}
                  className="rounded-md border border-gray-300 px-3 py-1 text-xs hover:bg-white disabled:cursor-not-allowed disabled:opacity-50"
                >
                  Next
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
