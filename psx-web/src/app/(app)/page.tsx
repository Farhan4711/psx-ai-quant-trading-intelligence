import { Metadata } from "next";
import Link from "next/link";
import {
  ArrowRight,
  BarChart2,
  BookOpen,
  Briefcase,
  Grid3x3,
} from "lucide-react";

export const metadata: Metadata = { title: "Dashboard" };

const tiles = [
  {
    href: "/app/stocks",
    icon: BarChart2,
    iconClass: "text-blue-600",
    arrowClass: "group-hover:text-blue-600",
    title: "Stock Browser",
    blurb: "Browse all PSX-listed securities with filters and quotes.",
  },
  {
    href: "/app/watchlist",
    icon: BookOpen,
    iconClass: "text-emerald-600",
    arrowClass: "group-hover:text-emerald-600",
    title: "Watchlist",
    blurb: "Drag-to-reorder, live quotes, mobile-friendly cards.",
  },
  {
    href: "/app/portfolio",
    icon: Briefcase,
    iconClass: "text-violet-600",
    arrowClass: "group-hover:text-violet-600",
    title: "Portfolio",
    blurb: "After-tax P&L. Knows what you'd actually net if you sold today.",
  },
  {
    href: "/app/sectors",
    icon: Grid3x3,
    iconClass: "text-amber-600",
    arrowClass: "group-hover:text-amber-600",
    title: "Sectors",
    blurb: "Heatmap by market cap and day change. Compare 2–4 within a sector.",
  },
];

export default function DashboardPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="mt-1 text-sm text-gray-500">
          Pakistani equities, with the tax math built in.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {tiles.map((t) => (
          <Link
            key={t.href}
            href={t.href}
            className="group flex flex-col gap-3 rounded-lg border border-gray-200 bg-white p-5 shadow-sm transition hover:border-blue-300 hover:shadow-md"
          >
            <div className="flex items-center justify-between">
              <t.icon className={`h-6 w-6 ${t.iconClass}`} />
              <ArrowRight
                className={`h-4 w-4 text-gray-400 transition group-hover:translate-x-1 ${t.arrowClass}`}
              />
            </div>
            <div>
              <h2 className="font-semibold text-gray-900">{t.title}</h2>
              <p className="mt-0.5 text-sm text-gray-500">{t.blurb}</p>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
