"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { fetchCurrentUser, updateCurrentUser, type CurrentUser } from "@/lib/api/auth";
import { Sparkles } from "lucide-react";

export default function SettingsPage() {
  const queryClient = useQueryClient();

  const { data: user, isLoading } = useQuery({
    queryKey: ["current-user"],
    queryFn: fetchCurrentUser,
  });

  const update = useMutation({
    mutationFn: updateCurrentUser,
    onSuccess: (data) => {
      queryClient.setQueryData(["current-user"], data);
    },
  });

  if (isLoading || !user) {
    return <div className="h-48 animate-pulse rounded-lg bg-gray-100" />;
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
        <p className="mt-1 text-sm text-gray-500">{user.email}</p>
      </div>

      {/* Shariah Mode */}
      <ToggleCard
        icon={<Sparkles className="h-5 w-5 text-emerald-600" />}
        title="Shariah Mode"
        description={
          <>
            Filter stock searches and screens to <strong>KMI-compliant</strong>{" "}
            stocks only. You&apos;ll see a green badge in the header, and trade
            entries for non-compliant stocks will warn you.
          </>
        }
        enabled={user.shariah_mode}
        onChange={(v) => update.mutate({ shariah_mode: v })}
        loading={update.isPending}
      />

      {/* Filer status */}
      <ToggleCard
        title="I'm a tax filer"
        description={
          <>
            Pakistan applies different CGT rates for filers vs non-filers. We
            use this flag every time we compute capital gains tax in your
            portfolio (currently <strong>{user.is_filer ? "filer (15%)" : "non-filer (45%)"}</strong>{" "}
            under the Finance Act 2024).
          </>
        }
        enabled={user.is_filer}
        onChange={(v) => update.mutate({ is_filer: v })}
        loading={update.isPending}
      />
    </div>
  );
}

function ToggleCard({
  icon,
  title,
  description,
  enabled,
  onChange,
  loading,
}: {
  icon?: React.ReactNode;
  title: string;
  description: React.ReactNode;
  enabled: boolean;
  onChange: (v: boolean) => void;
  loading: boolean;
}) {
  return (
    <div className="flex items-start gap-4 rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
      {icon && <div className="mt-0.5">{icon}</div>}
      <div className="flex-1">
        <h2 className="text-base font-semibold text-gray-900">{title}</h2>
        <p className="mt-1 text-sm text-gray-600">{description}</p>
      </div>
      <button
        type="button"
        role="switch"
        aria-checked={enabled}
        disabled={loading}
        onClick={() => onChange(!enabled)}
        className={
          "relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors disabled:opacity-50 " +
          (enabled ? "bg-emerald-500" : "bg-gray-200")
        }
      >
        <span
          className={
            "pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition " +
            (enabled ? "translate-x-5" : "translate-x-0")
          }
        />
      </button>
    </div>
  );
}
