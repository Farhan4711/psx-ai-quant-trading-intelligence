"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { fetchIntentStatus, type IntentStatus } from "@/lib/api/billing";
import { CheckCircle2, XCircle, Loader2 } from "lucide-react";

/**
 * Lands here after the gateway round-trip. Polls /billing/intent/:id
 * for up to ~30s so we cover the gateway-callback timing race (the
 * user usually beats the webhook by a few hundred ms). After 30s of
 * still-pending we tell them to check email — the callback may have
 * landed and we just couldn't observe it (e.g., bank-sync delay).
 */
export default function CheckoutReturnPage() {
  const params = useSearchParams();
  const intentId = params.get("intent_id") ?? params.get("ref") ?? "";
  const canceled = params.get("canceled") === "1";

  const [polls, setPolls] = useState(0);
  const { data, error, refetch } = useQuery<IntentStatus>({
    queryKey: ["billing-intent", intentId],
    queryFn: () => fetchIntentStatus(intentId),
    enabled: !!intentId,
    refetchInterval: (q) => {
      const s = q.state.data?.status;
      return s === "paid" || s === "failed" || s === "canceled" ? false : 3000;
    },
  });

  useEffect(() => {
    if (!data) return;
    if (data.status === "paid" || data.status === "failed" || data.status === "canceled") {
      return;
    }
    setPolls((p) => p + 1);
  }, [data]);

  if (canceled) {
    return (
      <Layout>
        <Header
          icon={<XCircle className="h-10 w-10 text-gray-500" />}
          title="Payment canceled"
          subtitle="No charge was made. You can try a different payment method any time."
        />
        <Link
          href="/checkout"
          className="mt-6 inline-block rounded-md bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700"
        >
          Back to checkout
        </Link>
      </Layout>
    );
  }

  if (!intentId) {
    return (
      <Layout>
        <p className="text-sm text-red-600">Missing intent reference.</p>
      </Layout>
    );
  }

  if (error) {
    return (
      <Layout>
        <p className="text-sm text-red-600">
          We couldn&apos;t look up your transaction. Email
          {" "}hello@psxai.example with reference{" "}
          <code>{intentId}</code> and we&apos;ll sort it out.
        </p>
      </Layout>
    );
  }

  if (!data || (data.status !== "paid" && data.status !== "failed" && data.status !== "canceled" && polls < 10)) {
    return (
      <Layout>
        <Header
          icon={<Loader2 className="h-10 w-10 animate-spin text-blue-600" />}
          title="Confirming your payment…"
          subtitle="Hang tight — your gateway is sending us the receipt."
        />
      </Layout>
    );
  }

  if (data.status === "paid") {
    return (
      <Layout>
        <Header
          icon={<CheckCircle2 className="h-10 w-10 text-emerald-600" />}
          title={`You're on ${data.plan_slug.toUpperCase()}`}
          subtitle={`PKR ${parseFloat(data.amount_pkr).toLocaleString("en-PK")} received via ${data.provider}. Welcome aboard.`}
        />
        <Link
          href="/dashboard"
          className="mt-6 inline-block rounded-md bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700"
        >
          Go to dashboard
        </Link>
      </Layout>
    );
  }

  if (data.status === "failed" || data.status === "canceled") {
    return (
      <Layout>
        <Header
          icon={<XCircle className="h-10 w-10 text-red-600" />}
          title={data.status === "canceled" ? "Payment canceled" : "Payment failed"}
          subtitle={
            data.failure_reason ??
            "Your gateway didn't complete the transaction. No money was taken."
          }
        />
        <Link
          href="/checkout"
          className="mt-6 inline-block rounded-md bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700"
        >
          Try another method
        </Link>
      </Layout>
    );
  }

  // > 10 polls = ~30s and still pending. Tell the user what to do.
  return (
    <Layout>
      <Header
        icon={<Loader2 className="h-10 w-10 text-amber-600" />}
        title="Still confirming…"
        subtitle="The gateway hasn't sent us the receipt yet. This sometimes happens during peak times — we'll email you the moment it lands."
      />
      <button
        onClick={() => refetch()}
        className="mt-4 text-sm text-blue-700 underline"
      >
        Check again
      </button>
      <p className="mt-4 text-xs text-gray-500">Reference: <code>{intentId}</code></p>
    </Layout>
  );
}

function Layout({ children }: { children: React.ReactNode }) {
  return (
    <div className="mx-auto max-w-md py-12 text-center">
      <div className="rounded-lg border border-gray-200 bg-white p-8 shadow-sm">
        {children}
      </div>
    </div>
  );
}

function Header({
  icon,
  title,
  subtitle,
}: {
  icon: React.ReactNode;
  title: React.ReactNode;
  subtitle: string;
}) {
  return (
    <>
      <div className="flex justify-center">{icon}</div>
      <h1 className="mt-4 text-xl font-bold text-gray-900">{title}</h1>
      <p className="mt-2 text-sm text-gray-600">{subtitle}</p>
    </>
  );
}
