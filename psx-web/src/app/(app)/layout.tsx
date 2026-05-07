import Link from "next/link";
import { auth } from "@/lib/auth";
import { redirect } from "next/navigation";
import { BarChart2, BookOpen, LayoutDashboard, Search } from "lucide-react";

export default async function AppLayout({ children }: { children: React.ReactNode }) {
  const session = await auth();
  if (!session) redirect("/login");

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="sticky top-0 z-40 border-b border-gray-200 bg-white">
        <div className="mx-auto flex h-14 max-w-7xl items-center gap-6 px-4 sm:px-6">
          <Link href="/app" className="flex items-center gap-2 text-lg font-bold text-blue-700">
            <BarChart2 className="h-5 w-5" />
            PSX AI
          </Link>

          <nav className="hidden items-center gap-1 sm:flex">
            <Link
              href="/app"
              className="rounded-md px-3 py-1.5 text-sm font-medium text-gray-600 hover:bg-gray-100 hover:text-gray-900"
            >
              <span className="flex items-center gap-1.5">
                <LayoutDashboard className="h-4 w-4" />
                Dashboard
              </span>
            </Link>
            <Link
              href="/app/stocks"
              className="rounded-md px-3 py-1.5 text-sm font-medium text-gray-600 hover:bg-gray-100 hover:text-gray-900"
            >
              <span className="flex items-center gap-1.5">
                <Search className="h-4 w-4" />
                Stocks
              </span>
            </Link>
            <Link
              href="/app/watchlist"
              className="rounded-md px-3 py-1.5 text-sm font-medium text-gray-600 hover:bg-gray-100 hover:text-gray-900"
            >
              <span className="flex items-center gap-1.5">
                <BookOpen className="h-4 w-4" />
                Watchlist
              </span>
            </Link>
          </nav>

          <div className="ml-auto flex items-center gap-3">
            <span className="hidden text-sm text-gray-500 sm:block">{session.user?.name ?? session.user?.email}</span>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6">{children}</main>
    </div>
  );
}
