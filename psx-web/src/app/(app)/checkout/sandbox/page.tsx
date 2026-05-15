"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { sandboxConfirm } from "@/lib/api/billing";

/**
 * Sandbox stand-in for a real Pakistani gateway. Shown when the
 * backend is in sandbox mode (no merchant creds in env). Renders a
 * friendly "this is fake money" banner and a button that POSTs to the
 * sandbox-confirm endpoint to simulate a successful gateway callback,
 * so the rest of the activation flow can be tested end-to-end.
 */
export default function CheckoutSandboxPage() {
  const router = useRouter();
  const params = useSearchParams();
  const intentId = params.get("intent_id");
  const provider = params.get("provider") ?? "gateway";
  const amount = params.get("amount") ?? "0";
  const [busy, setBusy] = useState<"idle" | "running" | "done" | "fail">("idle");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!intentId) router.replace("/dashboard");
  }, [intentId, router]);

  async function simulatePay(outcome: "success" | "fail") {
    if (!intentId) return;
    setBusy("running");
    setError(null);
    if (outcome === "fail") {
      setBusy("fail");
      setTimeout(
        () => router.replace(`/checkout/return?intent_id=${intentId}&canceled=1`),
        600,
      );
      return;
    }
    try {
      await sandboxConfirm(intentId);
      setBusy("done");
      router.replace(`/checkout/return?intent_id=${intentId}`);
    } catch (err) {
      setBusy("idle");
      setError((err as Error).message);
    }
  }

  return (
    <div className="mx-auto max-w-md py-10">
      <div className="rounded-lg border border-amber-300 bg-amber-50 p-6 shadow-sm">
        <h1 className="text-lg font-bold text-amber-900">
          🧪 Sandbox: simulated {provider}
        </h1>
        <p className="mt-2 text-sm text-amber-900">
          No merchant credentials are configured for this gateway, so
          you&apos;re seeing the local sandbox screen instead of the real
          one. No money will move.
        </p>
        <p className="mt-3 text-sm text-amber-900">
          Amount: <strong>PKR {Number(amount).toLocaleString("en-PK")}</strong>
        </p>
        <div className="mt-5 flex gap-2">
          <button
            disabled={busy === "running"}
            onClick={() => simulatePay("success")}
            className="flex-1 rounded-md bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-700 disabled:opacity-40"
          >
            {busy === "running" ? "Confirming…" : "Simulate success"}
          </button>
          <button
            disabled={busy === "running"}
            onClick={() => simulatePay("fail")}
            className="flex-1 rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-semibold text-gray-800 hover:bg-gray-50 disabled:opacity-40"
          >
            Simulate cancel
          </button>
        </div>
        {error && (
          <p className="mt-3 text-xs text-red-700">{error}</p>
        )}
        <p className="mt-4 text-xs text-amber-800">
          To wire a real gateway, set the merchant credentials in{" "}
          <code>psx-api/.env</code> and restart the API.
        </p>
      </div>
    </div>
  );
}
