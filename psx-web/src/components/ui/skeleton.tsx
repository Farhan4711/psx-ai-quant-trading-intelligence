import { cn } from "@/lib/utils/cn";

/**
 * Generic loading shimmer. Prefer this over spinners — readers can already
 * tell *where* content will appear, which feels faster than an indeterminate
 * spinner. Compose into table-row, card-row, and chart skeletons as needed.
 */
export function Skeleton({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("animate-pulse rounded-md bg-gray-200", className)}
      {...props}
    />
  );
}

export function SkeletonRow({ cols = 4 }: { cols?: number }) {
  return (
    <div className="flex items-center gap-3 px-4 py-3">
      {Array.from({ length: cols }).map((_, i) => (
        <Skeleton
          key={i}
          className="h-4"
          style={{ flexBasis: `${100 / cols}%` }}
        />
      ))}
    </div>
  );
}

export function SkeletonCard({ className }: { className?: string }) {
  return <Skeleton className={cn("h-24", className)} />;
}
