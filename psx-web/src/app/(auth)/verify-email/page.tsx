"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { apiVerifyEmail } from "@/lib/api/auth";

type Status = "verifying" | "success" | "error";

export default function VerifyEmailPage() {
  const params = useSearchParams();
  const token = params.get("token");
  const [status, setStatus] = useState<Status>("verifying");
  const [message, setMessage] = useState<string>("");

  useEffect(() => {
    if (!token) {
      setStatus("error");
      setMessage("No verification token found. Check your email link.");
      return;
    }

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

      {status === "error" && (
        <>
          <div className="mb-4 text-4xl">❌</div>
          <h2 className="mb-2 text-lg font-semibold text-gray-900">Verification failed</h2>
          <p className="mb-6 text-sm text-gray-500">{message}</p>
          <Link href="/login" className="text-sm text-blue-600 hover:underline">
            Back to sign in
          </Link>
        </>
      )}
    </div>
  );
}
