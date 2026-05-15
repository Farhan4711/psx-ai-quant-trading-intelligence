"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { fetchCurrentUser } from "@/lib/api/auth";
import { Sparkles } from "lucide-react";

/**
 * Persistent header badge shown when the user has Shariah Mode enabled.
 * Renders nothing otherwise. Backed by the `users.shariah_mode` flag.
 */
export function ShariahBadge() {
  const { data: user } = useQuery({
    queryKey: ["current-user"],
    queryFn: fetchCurrentUser,
    staleTime: 5 * 60_000,
    retry: false,
  });

  if (!user?.shariah_mode) return null;

  return (
    <Link
      href="/settings"
      className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-800 ring-1 ring-emerald-200 hover:bg-emerald-100"
      title="Shariah Mode is on — non-compliant stocks are filtered or warned"
    >
      <Sparkles className="h-3 w-3" />
      Shariah Mode
    </Link>
  );
}
