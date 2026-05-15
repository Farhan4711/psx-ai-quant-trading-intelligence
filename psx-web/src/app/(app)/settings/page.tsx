"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  fetchActiveSessions,
  fetchCurrentUser,
  resendVerificationEmail,
  revokeOtherSessions,
  revokeSession,
  updateCurrentUser,
  type CurrentUser,
  type SessionInfo,
} from "@/lib/api/auth";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import {
  AlertCircle,
  CheckCircle2,
  Laptop,
  ShieldCheck,
  Smartphone,
  Sparkles,
} from "lucide-react";

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

      <Tabs defaultValue="profile" className="w-full">
        <TabsList>
          <TabsTrigger value="profile">Profile</TabsTrigger>
          <TabsTrigger value="security">Security</TabsTrigger>
          <TabsTrigger value="notifications">Notifications</TabsTrigger>
        </TabsList>

        <TabsContent value="profile" className="mt-6 space-y-4">
          <ProfileTab
            user={user}
            onChange={(patch) => update.mutate(patch)}
            saving={update.isPending}
          />
        </TabsContent>

        <TabsContent value="security" className="mt-6 space-y-4">
          <SecurityTab user={user} />
        </TabsContent>

        <TabsContent value="notifications" className="mt-6 space-y-4">
          <div className="rounded-lg border border-gray-200 bg-white p-5 text-sm text-gray-500 shadow-sm">
            Per-channel notification preferences are coming soon. Today every
            user receives in-app notifications for pump/dump alerts, KMI
            changes, and payment events.
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}

// ── Profile tab ───────────────────────────────────────────────────────

function ProfileTab({
  user,
  onChange,
  saving,
}: {
  user: CurrentUser;
  onChange: (patch: { shariah_mode?: boolean; is_filer?: boolean }) => void;
  saving: boolean;
}) {
  return (
    <>
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
        onChange={(v) => onChange({ shariah_mode: v })}
        loading={saving}
      />
      <ToggleCard
        title="I'm a tax filer"
        description={
          <>
            Pakistan applies different CGT rates for filers vs non-filers. We
            use this flag every time we compute capital gains tax in your
            portfolio (currently{" "}
            <strong>{user.is_filer ? "filer (15%)" : "non-filer (45%)"}</strong>{" "}
            under the Finance Act 2024).
          </>
        }
        enabled={user.is_filer}
        onChange={(v) => onChange({ is_filer: v })}
        loading={saving}
      />
    </>
  );
}

// ── Security tab ──────────────────────────────────────────────────────

function SecurityTab({ user }: { user: CurrentUser }) {
  return (
    <>
      <EmailVerificationCard user={user} />
      <TotpStatusCard user={user} />
      <SessionsCard />
    </>
  );
}

function EmailVerificationCard({ user }: { user: CurrentUser }) {
  const resend = useMutation({ mutationFn: resendVerificationEmail });
  if (user.email_verified) {
    return (
      <div className="flex items-center gap-3 rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-900">
        <CheckCircle2 className="h-5 w-5 flex-shrink-0" />
        <span>Email verified.</span>
      </div>
    );
  }
  return (
    <div className="rounded-lg border border-amber-300 bg-amber-50 p-4 shadow-sm">
      <div className="flex items-start gap-3">
        <AlertCircle className="mt-0.5 h-5 w-5 flex-shrink-0 text-amber-800" />
        <div className="flex-1">
          <p className="text-sm font-medium text-amber-900">
            Your email isn&apos;t verified yet.
          </p>
          <p className="mt-1 text-xs text-amber-800">
            We sent a link to <strong>{user.email}</strong> when you signed up.
            Can&apos;t find it? Check spam, or resend below (limited to one
            per 5 minutes).
          </p>
        </div>
      </div>
      <Button
        size="sm"
        disabled={resend.isPending}
        onClick={() => resend.mutate()}
        className="mt-3"
      >
        {resend.isPending
          ? "Sending…"
          : resend.isSuccess
            ? "Email sent ✓"
            : "Resend verification email"}
      </Button>
      {resend.isError && (
        <p className="mt-2 text-xs text-red-700">
          {(resend.error as Error).message}
        </p>
      )}
    </div>
  );
}

function TotpStatusCard({ user }: { user: CurrentUser }) {
  return (
    <div className="flex items-start gap-4 rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
      <ShieldCheck className="mt-0.5 h-5 w-5 text-blue-600" />
      <div className="flex-1">
        <h3 className="text-base font-semibold text-gray-900">
          Two-factor authentication
        </h3>
        <p className="mt-1 text-sm text-gray-600">
          {user.totp_enabled
            ? "TOTP is enabled on your account. Each login requires a 6-digit code from your authenticator app."
            : "TOTP isn't enabled. Add an authenticator app (Authy, Google Authenticator) so a leaked password alone can't get into your account."}
        </p>
        <p className="mt-2 text-xs text-gray-400">
          Setup/disable flow is currently in the auth API (POST
          /auth/totp/setup, /confirm, /disable); the in-page modal lands
          in the next iteration.
        </p>
      </div>
      <span
        className={
          "rounded-full px-2 py-0.5 text-[10px] font-semibold " +
          (user.totp_enabled
            ? "bg-emerald-100 text-emerald-700"
            : "bg-gray-100 text-gray-600")
        }
      >
        {user.totp_enabled ? "ON" : "OFF"}
      </span>
    </div>
  );
}

function SessionsCard() {
  const queryClient = useQueryClient();
  const sessions = useQuery({
    queryKey: ["auth-sessions"],
    queryFn: fetchActiveSessions,
  });

  const revoke = useMutation({
    mutationFn: revokeSession,
    onSuccess: (_, sessionId) => {
      // Optimistic update: drop the revoked row immediately
      queryClient.setQueryData<SessionInfo[] | undefined>(
        ["auth-sessions"],
        (prev) => prev?.filter((s) => s.id !== sessionId),
      );
    },
  });

  const revokeOthers = useMutation({
    mutationFn: revokeOtherSessions,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["auth-sessions"] });
    },
  });

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="text-base font-semibold text-gray-900">
            Active sessions
          </h3>
          <p className="mt-1 text-sm text-gray-600">
            Every device you&apos;re signed in on. Revoke one if you don&apos;t
            recognise it.
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          disabled={
            revokeOthers.isPending ||
            !sessions.data ||
            sessions.data.filter((s) => !s.is_current).length === 0
          }
          onClick={() => revokeOthers.mutate()}
        >
          {revokeOthers.isPending
            ? "Signing out…"
            : "Sign out everywhere else"}
        </Button>
      </div>

      {sessions.isLoading && (
        <div className="mt-4 h-20 animate-pulse rounded-md bg-gray-100" />
      )}

      {sessions.data && (
        <ul className="mt-4 divide-y divide-gray-100">
          {sessions.data.map((s) => (
            <li key={s.id} className="flex items-center gap-3 py-3">
              <SessionIcon ua={s.user_agent} />
              <div className="min-w-0 flex-1 text-sm">
                <p className="truncate font-medium text-gray-900">
                  {prettyUa(s.user_agent)}
                  {s.is_current && (
                    <span className="ml-2 rounded-full bg-blue-100 px-2 py-0.5 text-[10px] font-semibold text-blue-700">
                      This device
                    </span>
                  )}
                </p>
                <p className="text-xs text-gray-500">
                  {s.ip_address ?? "Unknown IP"} ·{" "}
                  signed in {formatRelative(s.created_at)} · expires{" "}
                  {formatRelative(s.expires_at)}
                </p>
              </div>
              <Button
                variant="ghost"
                size="sm"
                disabled={revoke.isPending}
                onClick={() => {
                  if (
                    s.is_current &&
                    !confirm("This will sign you out. Continue?")
                  ) {
                    return;
                  }
                  revoke.mutate(s.id);
                }}
                className="text-red-700 hover:bg-red-50 hover:text-red-800"
              >
                Revoke
              </Button>
            </li>
          ))}
        </ul>
      )}

      {(revoke.isError || revokeOthers.isError) && (
        <p className="mt-3 text-xs text-red-700">
          Couldn&apos;t revoke — try again in a moment.
        </p>
      )}
    </div>
  );
}

function SessionIcon({ ua }: { ua: string | null }) {
  const isMobile = ua?.toLowerCase().includes("mobi");
  return isMobile ? (
    <Smartphone className="h-5 w-5 flex-shrink-0 text-gray-400" />
  ) : (
    <Laptop className="h-5 w-5 flex-shrink-0 text-gray-400" />
  );
}

/**
 * Cheap UA -> "Chrome on Mac" string. Not perfect — we trade exhaustive
 * UA parsing for predictability and zero dependencies.
 */
function prettyUa(ua: string | null): string {
  if (!ua) return "Unknown device";
  const lc = ua.toLowerCase();
  let browser = "Browser";
  if (lc.includes("edg/")) browser = "Edge";
  else if (lc.includes("chrome/")) browser = "Chrome";
  else if (lc.includes("firefox/")) browser = "Firefox";
  else if (lc.includes("safari/")) browser = "Safari";

  let os = "Unknown OS";
  if (lc.includes("windows")) os = "Windows";
  else if (lc.includes("mac os x")) os = "macOS";
  else if (lc.includes("android")) os = "Android";
  else if (lc.includes("iphone") || lc.includes("ipad")) os = "iOS";
  else if (lc.includes("linux")) os = "Linux";
  return `${browser} on ${os}`;
}

function formatRelative(iso: string): string {
  const ts = new Date(iso).getTime();
  const diff = Date.now() - ts;
  const future = diff < 0;
  const abs = Math.abs(diff);
  const minutes = Math.round(abs / 60000);
  const hours = Math.round(abs / 3_600_000);
  const days = Math.round(abs / 86_400_000);
  if (minutes < 60)
    return future ? `in ${minutes}m` : `${minutes}m ago`;
  if (hours < 24)
    return future ? `in ${hours}h` : `${hours}h ago`;
  return future ? `in ${days}d` : `${days}d ago`;
}

// ── Reusable toggle ───────────────────────────────────────────────────

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
