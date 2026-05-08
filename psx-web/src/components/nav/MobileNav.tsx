"use client";

import { useState } from "react";
import Link from "next/link";
import {
  BookOpen,
  Briefcase,
  Grid3x3,
  LayoutDashboard,
  Menu,
  Search,
  Settings,
  Target,
  UserCheck,
  X,
} from "lucide-react";

const ITEMS = [
  { href: "/app", label: "Dashboard", icon: LayoutDashboard },
  { href: "/app/stocks", label: "Stocks", icon: Search },
  { href: "/app/watchlist", label: "Watchlist", icon: BookOpen },
  { href: "/app/portfolio", label: "Portfolio", icon: Briefcase },
  { href: "/app/goals", label: "Goals", icon: Target },
  { href: "/app/sectors", label: "Sectors", icon: Grid3x3 },
  { href: "/app/risk-profile", label: "Risk Profile", icon: UserCheck },
  { href: "/app/settings", label: "Settings", icon: Settings },
];

/**
 * Hamburger menu + slide-in drawer for mobile (<sm). Hidden on sm+ where
 * the inline nav links take over.
 */
export function MobileNav() {
  const [open, setOpen] = useState(false);

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        aria-label="Open menu"
        className="rounded-md p-1.5 text-gray-700 hover:bg-gray-100 sm:hidden"
      >
        <Menu className="h-5 w-5" />
      </button>

      {open && (
        <>
          <div
            className="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm sm:hidden"
            onClick={() => setOpen(false)}
            aria-hidden
          />
          <div className="fixed inset-y-0 left-0 z-50 flex w-72 max-w-[80vw] flex-col bg-white shadow-xl sm:hidden">
            <div className="flex items-center justify-between border-b border-gray-200 px-4 py-3">
              <span className="text-base font-bold text-blue-700">PSX AI</span>
              <button
                onClick={() => setOpen(false)}
                aria-label="Close menu"
                className="rounded-md p-1 text-gray-500 hover:bg-gray-100"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
            <nav className="flex-1 overflow-y-auto p-2">
              {ITEMS.map((it) => (
                <Link
                  key={it.href}
                  href={it.href}
                  onClick={() => setOpen(false)}
                  className="flex items-center gap-3 rounded-md px-3 py-2.5 text-sm font-medium text-gray-700 hover:bg-gray-100"
                >
                  <it.icon className="h-4 w-4" />
                  {it.label}
                </Link>
              ))}
            </nav>
          </div>
        </>
      )}
    </>
  );
}
