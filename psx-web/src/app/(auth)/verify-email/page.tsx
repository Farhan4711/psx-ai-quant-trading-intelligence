"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useMutation } from "@tanstack/react-query";
import { apiVerifyEmail, resendVerificationEmail } from "@/lib/api/auth";
import { ApiError } from "@psx/shared";

type Status = "verifying" | "success" | "error" | "no-token";

export default function VerifyEmailPage() {
  const params = useSearchParams();
  const token = params.get("token");
  const [status, setStatus] = useState<Status>(token ? "verifying" : "no-token");
  const [message, setMessage] = useState<string>("");

  useEffect(() => {
    if (!token) return;
    apiVerifyEmail(token)
      .then(() => setStatus("success"))
      .catch((err: unknown) => {
        setStatus("error");
        setMessage(err instanceof Error ? err.message : "Verification failed.");
      });
  }, [token]);

  return (
    <div className="text-center">
      {status === "verifying" && (
        <>
          <div className="mb-4 text-4xl">⏳</div>
          <h2 className="text-lg font-semibold text-gray-900">Verifying…</h2>
        </>
      )}

      {status === "success" && (
        <>
          <div className="mb-4 text-4xl">✅</div>
          <h2 className="mb-2 text-lg font-semibold text-gray-900">Email verified!</h2>
          <p className="mb-6 text-sm text-gray-500">Your account is now active.</p>
          <Link
            href="/login"
            className="inline-block rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
          >
            Sign in
          </Link>
        </>
      )}

      {status === "no-token" && <ResendBlock />}

      {status === "error" && (
        <>
          <div className="mb-4 text-4xl">❌</div>
          <h2 className="mb-2 text-lg font-semibold text-gray-900">Verification failed</h2>
          <p className="mb-6 text-sm text-gray-500">{message}</p>
          <ResendBlock compact />
          <p className="mt-4 text-sm">
            <Link href="/login" className="text-blue-600 hover:underline">
              Back to sign in
            </Link>
          </p>
        </>
      )}
    </div>
  );
}

/**
 * Resend block — shown when the user lands here without a token (they
 * clicked the navbar shortcut while signed in) or when an existing
 * token failed (expired link). Both flows are authed: we need the
 * session cookie to know whose email to re-send.
 *
 * If the user isn't signed in, the API returns 401 and we tell them
 * to log in first.
 */
function ResendBlock({ compact = false }: { compact?: boolean }) {
  const [cooldown, setCooldown] = useState<number | null>(null);

  const resend = useMutation({
    mutationFn: resendVerificationEmail,
    onError: (err) => {
      if (err instanceof ApiError && err.status === 429) {
        // Backend cooldown is 5 min — surface a countdown.
        setCooldown(300);
      }
    },
  });

  useEffect(() => {
    if (cooldown === null) return;
    if (cooldown <= 0) {
      setCooldown(null);
      return;
    }
    const t = setTimeout(() => setCooldown((c) => (c == null ? null : c - 1)), 1000);
    return () => clearTimeout(t);
  }, [cooldown]);

  const disabled = resend.isPending || cooldown !== null;
  const label = cooldown
    ? `Wait ${Math.floor(cooldown / 60)}:${(cooldown % 60).toString().padStart(2, "0")}`
    : resend.isSuccess
      ? "Sent ✓ — check your inbox"
      : resend.isPending
        ? "Sending…"
        : "Resend verification email";

  return (
    <div className={compact ? "" : "py-2"}>
      {!compact && (
        <>
          <div className="mb-4 text-4xl">📧</div>
          <h2 className="mb-2 text-lg font-semibold text-gray-900">
            Need another verification email?
          </h2>
          <p className="mb-4 text-sm text-gray-500">
            Sign in first, then we can re-send the link to your inbox.
          </p>
        </>
      )}
      <button
        disabled={disabled}
        onClick={() => resend.mutate()}
        className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
      >
        {label}
      </button>
      {resend.isError && cooldown === null && (
        <p className="mt-3 text-xs text-red-600">
          {resend.error instanceof ApiError && resend.error.status === 401
            ? "You need to be signed in. "
            : "Couldn't send — "}
          {!(resend.error instanceof ApiError && resend.error.status === 401) &&
            (resend.error as Error).message}
          {resend.error instanceof ApiError && resend.error.status === 401 && (
            <Link href="/login" className="underline">
              Sign in
            </Link>
          )}
        </p>
      )}
    </div>
  );
}
