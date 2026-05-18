"use client";

import { useState } from "react";
import Link from "next/link";
import {
  Bell,
  BookOpen,
  Briefcase,
  Calculator,
  FlaskConical,
  Grid3x3,
  GraduationCap,
  LayoutDashboard,
  Menu,
  Moon,
  Search,
  Settings,
  Sparkles,
  Target,
  UserCheck,
  X,
} from "lucide-react";

const ITEMS = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/stocks", label: "Stocks", icon: Search },
  { href: "/watchlist", label: "Watchlist", icon: BookOpen },
  { href: "/portfolio", label: "Portfolio", icon: Briefcase },
  { href: "/goals", label: "Goals", icon: Target },
  { href: "/backtest", label: "Backtest", icon: FlaskConical },
  { href: "/strategies", label: "Strategies", icon: Sparkles },
  { href: "/sectors", label: "Sectors", icon: Grid3x3 },
  { href: "/alerts", label: "Alerts", icon: Bell },
  { href: "/tax-simulator", label: "Tax simulator", icon: Calculator },
  { href: "/purification", label: "Purification", icon: Moon },
  { href: "/lessons", label: "Lessons", icon: GraduationCap },
  { href: "/risk-profile", label: "Risk Profile", icon: UserCheck },
  { href: "/settings", label: "Settings", icon: Settings },
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
        aria-label="Open navigation menu"
        aria-expanded={open}
        aria-controls="mobile-nav-drawer"
        className="rounded-md p-1.5 text-gray-700 hover:bg-gray-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-300 sm:hidden"
      >
        <Menu className="h-5 w-5" aria-hidden="true" />
      </button>

      {open && (
        <>
          <div
            className="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm sm:hidden"
            onClick={() => setOpen(false)}
            aria-hidden
          />
          <div
            id="mobile-nav-drawer"
            role="dialog"
            aria-label="Navigation menu"
            aria-modal="true"
            className="fixed inset-y-0 left-0 z-50 flex w-72 max-w-[80vw] flex-col bg-white shadow-xl sm:hidden"
          >
            <div className="flex items-center justify-between border-b border-gray-200 px-4 py-3">
              <span className="text-base font-bold text-blue-700">PSX AI</span>
              <button
                onClick={() => setOpen(false)}
                aria-label="Close navigation menu"
                className="rounded-md p-1 text-gray-500 hover:bg-gray-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-300"
              >
                <X className="h-5 w-5" aria-hidden="true" />
              </button>
            </div>
            <nav
              aria-label="Primary mobile"
              className="flex-1 overflow-y-auto p-2"
            >
              {ITEMS.map((it) => (
                <Link
                  key={it.href}
                  href={it.href}
                  onClick={() => setOpen(false)}
                  className="flex items-center gap-3 rounded-md px-3 py-2.5 text-sm font-medium text-gray-700 hover:bg-gray-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-300"
                >
                  <it.icon className="h-4 w-4" aria-hidden="true" />
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
