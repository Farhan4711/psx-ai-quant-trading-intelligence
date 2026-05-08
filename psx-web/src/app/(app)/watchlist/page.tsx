"use client";

import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  fetchQuotes,
  fetchWatchlist,
  removeFromWatchlist,
  reorderWatchlist,
  type Quote,
  type WatchlistItem,
} from "@/lib/api/securities";
import { Badge } from "@/components/ui/badge";
import Link from "next/link";
import { GripVertical, Trash2 } from "lucide-react";
import { formatPrice } from "@/lib/utils/format";
import {
  DndContext,
  PointerSensor,
  KeyboardSensor,
  closestCenter,
  useSensor,
  useSensors,
  type DragEndEvent,
} from "@dnd-kit/core";
import {
  SortableContext,
  arrayMove,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";

export default function WatchlistPage() {
  const queryClient = useQueryClient();

  const { data, isLoading, isError } = useQuery({
    queryKey: ["watchlist"],
    queryFn: fetchWatchlist,
    staleTime: 60_000,
  });

  // Local order — synced from server data, mutated optimistically on drag-end
  const [order, setOrder] = useState<WatchlistItem[]>([]);
  useEffect(() => {
    if (data) setOrder(data);
  }, [data]);

  const symbols = order.map((i) => i.symbol);

  const { data: quotes } = useQuery({
    queryKey: ["quotes", symbols.join(",")],
    queryFn: () => fetchQuotes(symbols),
    enabled: symbols.length > 0,
    staleTime: 60_000,
    refetchInterval: 60_000,
  });

  const quoteMap = new Map<string, Quote>(
    quotes?.items.map((q) => [q.symbol, q]) ?? [],
  );

  const remove = useMutation({
    mutationFn: (symbol: string) => removeFromWatchlist(symbol),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["watchlist"] }),
  });

  const reorder = useMutation({
    mutationFn: (newOrder: string[]) => reorderWatchlist(newOrder),
    onSuccess: (updated) => {
      queryClient.setQueryData(["watchlist"], updated);
    },
  });

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );

  function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event;
    if (!over || active.id === over.id) return;
    const oldIndex = order.findIndex((i) => i.symbol === active.id);
    const newIndex = order.findIndex((i) => i.symbol === over.id);
    if (oldIndex === -1 || newIndex === -1) return;
    const next = arrayMove(order, oldIndex, newIndex);
    setOrder(next);
    reorder.mutate(next.map((i) => i.symbol));
  }

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Watchlist</h1>
        <p className="mt-1 text-sm text-gray-500">
          Drag rows to reorder. Quotes refresh every minute.
        </p>
      </div>

      {isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="h-12 animate-pulse rounded-md bg-gray-100" />
          ))}
        </div>
      ) : isError ? (
        <div className="flex h-48 items-center justify-center text-sm text-red-500">
          Failed to load watchlist.
        </div>
      ) : order.length === 0 ? (
        <div className="flex h-48 flex-col items-center justify-center gap-2 rounded-lg border border-dashed border-gray-300 bg-white text-center">
          <p className="text-sm text-gray-500">Your watchlist is empty.</p>
          <Link href="/app/stocks" className="text-sm text-blue-600 hover:underline">
            Browse stocks →
          </Link>
        </div>
      ) : (
        <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
          <SortableContext items={symbols} strategy={verticalListSortingStrategy}>
            {/* Desktop: table */}
            <div className="hidden overflow-hidden rounded-lg border border-gray-200 bg-white shadow-sm md:block">
              <div className="grid grid-cols-[36px_120px_minmax(0,1fr)_140px_140px_120px_40px] gap-3 border-b border-gray-200 bg-gray-50 px-4 py-3 text-xs font-medium uppercase tracking-wide text-gray-500">
                <span />
                <span>Symbol</span>
                <span>Company</span>
                <span className="text-right">Last</span>
                <span className="text-right">Day Change</span>
                <span>Note</span>
                <span />
              </div>
              <ul className="divide-y divide-gray-100">
                {order.map((item) => (
                  <SortableRow
                    key={item.symbol}
                    item={item}
                    quote={quoteMap.get(item.symbol)}
                    onRemove={() => remove.mutate(item.symbol)}
                    isRemoving={remove.isPending}
                  />
                ))}
              </ul>
            </div>

            {/* Mobile: cards */}
            <ul className="space-y-2 md:hidden">
              {order.map((item) => (
                <SortableCard
                  key={item.symbol}
                  item={item}
                  quote={quoteMap.get(item.symbol)}
                  onRemove={() => remove.mutate(item.symbol)}
                  isRemoving={remove.isPending}
                />
              ))}
            </ul>
          </SortableContext>
        </DndContext>
      )}
    </div>
  );
}

// ── Subcomponents ──────────────────────────────────────────────────────

function priceChangeClass(quote: Quote | undefined): string {
  if (!quote?.change) return "text-gray-500";
  return parseFloat(quote.change) >= 0 ? "text-green-600" : "text-red-600";
}

function formatChangeCell(quote: Quote | undefined): string {
  if (!quote || quote.change == null || quote.change_pct == null) return "—";
  const change = parseFloat(quote.change);
  const pct = parseFloat(quote.change_pct);
  const sign = change >= 0 ? "+" : "";
  return `${sign}${change.toFixed(2)} (${sign}${pct.toFixed(2)}%)`;
}

function SortableRow({
  item,
  quote,
  onRemove,
  isRemoving,
}: {
  item: WatchlistItem;
  quote: Quote | undefined;
  onRemove: () => void;
  isRemoving: boolean;
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: item.symbol,
  });
  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };
  return (
    <li
      ref={setNodeRef}
      style={style}
      className="grid grid-cols-[36px_120px_minmax(0,1fr)_140px_140px_120px_40px] items-center gap-3 px-4 py-3 text-sm hover:bg-gray-50"
    >
      <button
        {...attributes}
        {...listeners}
        className="cursor-grab text-gray-300 hover:text-gray-500 active:cursor-grabbing"
        aria-label={`Drag to reorder ${item.symbol}`}
      >
        <GripVertical className="h-4 w-4" />
      </button>
      <Link href={`/app/stocks/${item.symbol}`} className="font-mono font-semibold text-blue-700 hover:underline">
        {item.symbol}
      </Link>
      <span className="truncate text-gray-800">
        {item.company_name}
        {item.is_kmi_compliant && <Badge variant="kmi" className="ml-2">KMI</Badge>}
      </span>
      <span className="text-right font-medium text-gray-900">
        {quote?.last_close ? `PKR ${formatPrice(quote.last_close)}` : "—"}
      </span>
      <span className={`text-right font-medium ${priceChangeClass(quote)}`}>
        {formatChangeCell(quote)}
      </span>
      <span className="truncate text-gray-500">{item.note ?? "—"}</span>
      <button
        onClick={onRemove}
        disabled={isRemoving}
        className="rounded p-1 text-gray-400 hover:bg-red-50 hover:text-red-500 disabled:opacity-50"
        aria-label={`Remove ${item.symbol} from watchlist`}
      >
        <Trash2 className="h-4 w-4" />
      </button>
    </li>
  );
}

function SortableCard({
  item,
  quote,
  onRemove,
  isRemoving,
}: {
  item: WatchlistItem;
  quote: Quote | undefined;
  onRemove: () => void;
  isRemoving: boolean;
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: item.symbol,
  });
  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };
  return (
    <li
      ref={setNodeRef}
      style={style}
      className="rounded-lg border border-gray-200 bg-white p-3 shadow-sm"
    >
      <div className="flex items-start gap-2">
        <button
          {...attributes}
          {...listeners}
          className="mt-1 cursor-grab text-gray-300 hover:text-gray-500 active:cursor-grabbing"
          aria-label={`Drag to reorder ${item.symbol}`}
        >
          <GripVertical className="h-4 w-4" />
        </button>

        <div className="min-w-0 flex-1">
          <div className="flex items-center justify-between gap-2">
            <Link
              href={`/app/stocks/${item.symbol}`}
              className="font-mono text-sm font-semibold text-blue-700 hover:underline"
            >
              {item.symbol}
            </Link>
            <span className="text-sm font-medium text-gray-900">
              {quote?.last_close ? `PKR ${formatPrice(quote.last_close)}` : "—"}
            </span>
          </div>
          <div className="mt-0.5 flex items-center justify-between gap-2">
            <span className="truncate text-xs text-gray-500">{item.company_name}</span>
            <span className={`text-xs font-medium ${priceChangeClass(quote)}`}>
              {formatChangeCell(quote)}
            </span>
          </div>
          {item.note && (
            <p className="mt-1.5 truncate text-xs italic text-gray-500">{item.note}</p>
          )}
        </div>

        <button
          onClick={onRemove}
          disabled={isRemoving}
          className="rounded p-1 text-gray-400 hover:bg-red-50 hover:text-red-500 disabled:opacity-50"
          aria-label={`Remove ${item.symbol} from watchlist`}
        >
          <Trash2 className="h-4 w-4" />
        </button>
      </div>
    </li>
  );
}
