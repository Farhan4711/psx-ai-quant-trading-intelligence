import { Metadata } from "next";
import Link from "next/link";
import { ArrowRight, BarChart2, BookOpen, TrendingUp } from "lucide-react";

export const metadata: Metadata = { title: "Dashboard" };

export default function DashboardPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="mt-1 text-sm text-gray-500">Phase 1 — Stock Browser & Watchlist in progress.</p>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <Link
          href="/app/stocks"
          className="group flex flex-col gap-3 rounded-lg border border-gray-200 bg-white p-5 shadow-sm transition hover:border-blue-300 hover:shadow-md"
        >
          <div className="flex items-center justify-between">
            <BarChart2 className="h-6 w-6 text-blue-600" />
            <ArrowRight className="h-4 w-4 text-gray-400 transition group-hover:translate-x-1 group-hover:text-blue-600" />
          </div>
          <div>
            <h2 className="font-semibold text-gray-900">Stock Browser</h2>
            <p className="mt-0.5 text-sm text-gray-500">Browse all PSX-listed securities with filters.</p>
          </div>
        </Link>

        <Link
          href="/app/watchlist"
          className="group flex flex-col gap-3 rounded-lg border border-gray-200 bg-white p-5 shadow-sm transition hover:border-blue-300 hover:shadow-md"
        >
          <div className="flex items-center justify-between">
            <BookOpen className="h-6 w-6 text-emerald-600" />
            <ArrowRight className="h-4 w-4 text-gray-400 transition group-hover:translate-x-1 group-hover:text-emerald-600" />
          </div>
          <div>
            <h2 className="font-semibold text-gray-900">Watchlist</h2>
            <p className="mt-0.5 text-sm text-gray-500">Track your favourite stocks at a glance.</p>
          </div>
        </Link>

        <div className="flex flex-col gap-3 rounded-lg border border-dashed border-gray-300 bg-gray-50 p-5">
          <TrendingUp className="h-6 w-6 text-gray-400" />
          <div>
            <h2 className="font-semibold text-gray-500">Portfolio</h2>
            <p className="mt-0.5 text-sm text-gray-400">Coming in Phase 1 — CGT-aware tracking.</p>
          </div>
        </div>
      </div>
    </div>
  );
}
