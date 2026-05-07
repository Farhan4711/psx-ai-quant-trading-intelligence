"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { addToWatchlist, fetchWatchlist, removeFromWatchlist } from "@/lib/api/securities";
import { Bookmark, BookmarkCheck } from "lucide-react";

export function WatchlistButton({ symbol }: { symbol: string }) {
  const queryClient = useQueryClient();
  const [optimistic, setOptimistic] = useState<boolean | null>(null);

  const { data: watchlist } = useQuery({
    queryKey: ["watchlist"],
    queryFn: fetchWatchlist,
    staleTime: 60_000,
  });

  const isWatched = optimistic ?? watchlist?.some((w) => w.symbol === symbol) ?? false;

  const add = useMutation({
    mutationFn: () => addToWatchlist(symbol),
    onMutate: () => setOptimistic(true),
    onSettled: () => {
      setOptimistic(null);
      void queryClient.invalidateQueries({ queryKey: ["watchlist"] });
    },
  });

  const remove = useMutation({
    mutationFn: () => removeFromWatchlist(symbol),
    onMutate: () => setOptimistic(false),
    onSettled: () => {
      setOptimistic(null);
      void queryClient.invalidateQueries({ queryKey: ["watchlist"] });
    },
  });

  const isPending = add.isPending || remove.isPending;

  return (
    <button
      onClick={() => (isWatched ? remove.mutate() : add.mutate())}
      disabled={isPending}
      className={`flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-sm font-medium transition-colors disabled:opacity-60 ${
        isWatched
          ? "border-emerald-300 bg-emerald-50 text-emerald-700 hover:bg-emerald-100"
          : "border-gray-300 bg-white text-gray-700 hover:bg-gray-50"
      }`}
    >
      {isWatched ? (
        <BookmarkCheck className="h-4 w-4" />
      ) : (
        <Bookmark className="h-4 w-4" />
      )}
      {isWatched ? "Watching" : "Watch"}
    </button>
  );
}
