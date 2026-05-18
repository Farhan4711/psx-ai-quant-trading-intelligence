import Link from "next/link";
import { auth } from "@/lib/auth";
import { redirect } from "next/navigation";
import { BarChart2, Bell, BookOpen, Briefcase, Calculator, FlaskConical, Grid3x3, LayoutDashboard, Search, Target } from "lucide-react";
import { ShariahBadge } from "@/components/shariah/ShariahBadge";
import { MobileNav } from "@/components/nav/MobileNav";
import { NotificationsBell } from "@/components/nav/NotificationsBell";
import { SkipToContent } from "@/components/a11y/SkipToContent";

export default async function AppLayout({ children }: { children: React.ReactNode }) {
  const session = await auth();
  if (!session) redirect("/login");

  return (
    <div className="min-h-screen bg-gray-50">
      <SkipToContent />
      <header className="sticky top-0 z-40 border-b border-gray-200 bg-white">
        <div className="mx-auto flex h-14 max-w-7xl items-center gap-3 px-4 sm:gap-6 sm:px-6">
          <MobileNav />
          <Link
            href="/dashboard"
            aria-label="PSX AI dashboard"
            className="flex items-center gap-2 rounded-md text-lg font-bold text-blue-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-300 focus-visible:ring-offset-2"
          >
            <BarChart2 className="h-5 w-5" aria-hidden="true" />
            PSX AI
          </Link>

          <nav aria-label="Main" className="hidden items-center gap-1 sm:flex">
            <Link
              href="/dashboard"
              className="rounded-md px-3 py-1.5 text-sm font-medium text-gray-600 hover:bg-gray-100 hover:text-gray-900"
            >
              <span className="flex items-center gap-1.5">
                <LayoutDashboard className="h-4 w-4" />
                Dashboard
              </span>
            </Link>
            <Link
              href="/stocks"
              className="rounded-md px-3 py-1.5 text-sm font-medium text-gray-600 hover:bg-gray-100 hover:text-gray-900"
            >
              <span className="flex items-center gap-1.5">
                <Search className="h-4 w-4" />
                Stocks
              </span>
            </Link>
            <Link
              href="/watchlist"
              className="rounded-md px-3 py-1.5 text-sm font-medium text-gray-600 hover:bg-gray-100 hover:text-gray-900"
            >
              <span className="flex items-center gap-1.5">
                <BookOpen className="h-4 w-4" />
                Watchlist
              </span>
            </Link>
            <Link
              href="/portfolio"
              className="rounded-md px-3 py-1.5 text-sm font-medium text-gray-600 hover:bg-gray-100 hover:text-gray-900"
            >
              <span className="flex items-center gap-1.5">
                <Briefcase className="h-4 w-4" />
                Portfolio
              </span>
            </Link>
            <Link
              href="/goals"
              className="rounded-md px-3 py-1.5 text-sm font-medium text-gray-600 hover:bg-gray-100 hover:text-gray-900"
            >
              <span className="flex items-center gap-1.5">
                <Target className="h-4 w-4" />
                Goals
              </span>
            </Link>
            <Link
              href="/backtest"
              className="rounded-md px-3 py-1.5 text-sm font-medium text-gray-600 hover:bg-gray-100 hover:text-gray-900"
            >
              <span className="flex items-center gap-1.5">
                <FlaskConical className="h-4 w-4" />
                Backtest
              </span>
            </Link>
            <Link
              href="/sectors"
              className="rounded-md px-3 py-1.5 text-sm font-medium text-gray-600 hover:bg-gray-100 hover:text-gray-900"
            >
              <span className="flex items-center gap-1.5">
                <Grid3x3 className="h-4 w-4" />
                Sectors
              </span>
            </Link>
            <Link
              href="/alerts"
              className="rounded-md px-3 py-1.5 text-sm font-medium text-gray-600 hover:bg-gray-100 hover:text-gray-900"
            >
              <span className="flex items-center gap-1.5">
                <Bell className="h-4 w-4" />
                Alerts
              </span>
            </Link>
            <Link
              href="/tax-simulator"
              className="rounded-md px-3 py-1.5 text-sm font-medium text-gray-600 hover:bg-gray-100 hover:text-gray-900"
            >
              <span className="flex items-center gap-1.5">
                <Calculator className="h-4 w-4" />
                Tax sim
              </span>
            </Link>
          </nav>

          <div className="ml-auto flex items-center gap-3">
            <ShariahBadge />
            <NotificationsBell />
            <Link
              href="/settings"
              className="hidden text-sm text-gray-500 hover:text-gray-700 sm:block"
            >
              {session.user?.name ?? session.user?.email}
            </Link>
          </div>
        </div>
      </header>

      <main id="main-content" className="mx-auto max-w-7xl px-4 py-6 sm:px-6">{children}</main>
    </div>
  );
}
