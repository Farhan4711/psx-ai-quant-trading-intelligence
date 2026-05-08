"use client";

import { useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  fetchNotifications,
  fetchUnreadCount,
  markAllNotificationsRead,
  markNotificationRead,
  type NotificationItem,
} from "@/lib/api/community";
import { Bell, Check } from "lucide-react";

/**
 * Header bell with unread count badge + dropdown panel listing
 * recent notifications. Polls unread count every 60s.
 */
export function NotificationsBell() {
  const [open, setOpen] = useState(false);
  const queryClient = useQueryClient();

  const { data: countData } = useQuery({
    queryKey: ["notifications-unread"],
    queryFn: fetchUnreadCount,
    staleTime: 30_000,
    refetchInterval: 60_000,
    retry: false,
  });
  const unread = countData?.unread ?? 0;

  const { data: items } = useQuery({
    queryKey: ["notifications"],
    queryFn: () => fetchNotifications(20),
    enabled: open,
    staleTime: 30_000,
    retry: false,
  });

  const markRead = useMutation({
    mutationFn: (id: string) => markNotificationRead(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notifications-unread"] });
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
    },
  });
  const markAll = useMutation({
    mutationFn: markAllNotificationsRead,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notifications-unread"] });
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
    },
  });

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="relative rounded-md p-1.5 text-gray-500 hover:bg-gray-100 hover:text-gray-700"
        aria-label="Notifications"
      >
        <Bell className="h-5 w-5" />
        {unread > 0 && (
          <span className="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-red-500 px-1 text-[10px] font-semibold text-white">
            {unread > 9 ? "9+" : unread}
          </span>
        )}
      </button>

      {open && (
        <>
          <div
            className="fixed inset-0 z-30"
            onClick={() => setOpen(false)}
            aria-hidden
          />
          <div className="absolute right-0 top-10 z-40 w-80 max-w-[90vw] rounded-lg border border-gray-200 bg-white shadow-xl">
            <div className="flex items-center justify-between border-b border-gray-200 px-4 py-2">
              <span className="text-sm font-semibold">Notifications</span>
              {unread > 0 && (
                <button
                  onClick={() => markAll.mutate()}
                  className="flex items-center gap-1 text-xs text-blue-600 hover:underline"
                >
                  <Check className="h-3 w-3" />
                  Mark all read
                </button>
              )}
            </div>
            <ul className="max-h-96 divide-y divide-gray-100 overflow-y-auto">
              {!items || items.length === 0 ? (
                <li className="px-4 py-6 text-center text-xs text-gray-400">
                  Nothing new.
                </li>
              ) : (
                items.map((n) => (
                  <NotificationRow
                    key={n.id}
                    n={n}
                    onClick={() => {
                      if (!n.read_at) markRead.mutate(n.id);
                      if (n.link_path) {
                        setOpen(false);
                      }
                    }}
                  />
                ))
              )}
            </ul>
          </div>
        </>
      )}
    </div>
  );
}

function NotificationRow({
  n,
  onClick,
}: {
  n: NotificationItem;
  onClick: () => void;
}) {
  const inner = (
    <div
      className={
        "px-4 py-2.5 text-sm hover:bg-gray-50 " +
        (n.read_at ? "" : "bg-blue-50/50")
      }
    >
      <p className={"font-medium " + (n.read_at ? "text-gray-700" : "text-gray-900")}>
        {n.title}
      </p>
      <p className="mt-0.5 line-clamp-2 text-xs text-gray-500">{n.body}</p>
      <p className="mt-1 text-[10px] text-gray-400">
        {new Date(n.created_at).toLocaleString()}
      </p>
    </div>
  );
  return (
    <li onClick={onClick}>
      {n.link_path ? <Link href={n.link_path}>{inner}</Link> : inner}
    </li>
  );
}
