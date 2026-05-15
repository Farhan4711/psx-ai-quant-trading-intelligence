"use client";

import { useMemo, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { useQuery, useMutation } from "@tanstack/react-query";
import {
  fetchPlans,
  fetchPaymentMethods,
  postToGateway,
  startCheckout,
  type BillingCycle,
  type PaymentMethod,
  type PaymentProvider,
  type PlanRow,
} from "@/lib/api/billing";
import { Check, CreditCard, Landmark, Smartphone, Wallet } from "lucide-react";

const CATEGORY_ICON: Record<PaymentMethod["category"], typeof Wallet> = {
  wallet: Smartphone,
  bank: Landmark,
  card: CreditCard,
  manual: Wallet,
};

export default function CheckoutPage() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const planSlug = searchParams.get("plan") ?? "pro";
  const cycleParam = (searchParams.get("cycle") as BillingCycle | null) ?? "monthly";

  const [billingCycle, setBillingCycle] = useState<BillingCycle>(cycleParam);
  const [provider, setProvider] = useState<PaymentProvider | null>(null);
  const [bankInstructions, setBankInstructions] = useState<string | null>(null);

  const plans = useQuery({ queryKey: ["billing-plans"], queryFn: fetchPlans });
  const methods = useQuery({
    queryKey: ["billing-payment-methods"],
    queryFn: fetchPaymentMethods,
  });

  const plan = useMemo<PlanRow | undefined>(
    () => plans.data?.find((p) => p.slug === planSlug),
    [plans.data, planSlug],
  );

  const checkout = useMutation({
    mutationFn: () =>
      startCheckout({
        plan_slug: planSlug,
        provider: provider!,
        billing_cycle: billingCycle,
      }),
    onSuccess: (data) => {
      if (data.provider === "manual") {
        setBankInstructions(data.instructions ?? "");
        return;
      }
      // Sandbox stub (no merchant creds): /checkout/sandbox handles
      // simulating a paid callback. Otherwise we redirect to the
      // gateway — using a hidden-form POST for the four redirect
      // gateways and window.location for the REST ones.
      if (data.is_sandbox) {
        router.push(
          `/checkout/sandbox?intent_id=${data.intent_id}` +
            `&provider=${data.provider}` +
            `&amount=${encodeURIComponent(data.amount_pkr)}`,
        );
        return;
      }
      const usesForm =
        data.provider === "jazzcash" ||
        data.provider === "easypaisa" ||
        data.provider === "meezan" ||
        data.provider === "allied_payfast";
      if (usesForm) {
        postToGateway(data.checkout_url, data.request_payload);
      } else {
        window.location.href = data.checkout_url;
      }
    },
  });

  if (plans.isLoading || methods.isLoading) {
    return (
      <div className="mx-auto max-w-3xl py-10">
        <div className="h-64 animate-pulse rounded-lg bg-gray-100" />
      </div>
    );
  }
  if (!plan) {
    return (
      <div className="mx-auto max-w-3xl py-10 text-center">
        <p className="text-sm text-red-600">
          Unknown plan &ldquo;{planSlug}&rdquo;. Pick one from{" "}
          <a className="underline" href="/pricing">/pricing</a>.
        </p>
      </div>
    );
  }

  const monthly = parseFloat(plan.price_pkr_monthly);
  const annual = plan.price_pkr_annual ? parseFloat(plan.price_pkr_annual) : null;
  const amount = billingCycle === "annual" && annual ? annual : monthly;

  // Group payment methods by category for the picker.
  const grouped = (methods.data ?? []).reduce<
    Record<PaymentMethod["category"], PaymentMethod[]>
  >((acc, m) => {
    (acc[m.category] ??= []).push(m);
    return acc;
  }, { wallet: [], bank: [], card: [], manual: [] });

  return (
    <div className="mx-auto max-w-3xl space-y-6 py-6">
      <header>
        <h1 className="text-2xl font-bold text-gray-900">Subscribe to {plan.name}</h1>
        <p className="mt-1 text-sm text-gray-500">{plan.tagline}</p>
      </header>

      {/* Billing cycle toggle */}
      <section className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-500">
          Billing cycle
        </h2>
        <div className="mt-3 grid gap-3 sm:grid-cols-2">
          {(["monthly", "annual"] as const).map((c) => {
            const showAmount = c === "annual" && annual ? annual : monthly * (c === "annual" ? 12 : 1);
            const isActive = billingCycle === c;
            const isDisabled = c === "annual" && !annual;
            return (
              <button
                key={c}
                disabled={isDisabled}
                onClick={() => setBillingCycle(c)}
                className={
                  "rounded-md border px-4 py-3 text-left text-sm transition " +
                  (isActive
                    ? "border-blue-600 bg-blue-50 ring-1 ring-blue-600"
                    : "border-gray-200 hover:border-gray-300") +
                  (isDisabled ? " opacity-40" : "")
                }
              >
                <div className="font-semibold capitalize text-gray-900">{c}</div>
                <div className="text-xs text-gray-500">
                  {isDisabled
                    ? "Not available on this plan"
                    : c === "annual" && annual && monthly > 0
                      ? `PKR ${annual.toLocaleString("en-PK")}/yr — save ${Math.max(0, Math.round((1 - annual / (monthly * 12)) * 100))}%`
                      : `PKR ${(c === "monthly" ? monthly : showAmount).toLocaleString("en-PK")}/${c === "monthly" ? "mo" : "yr"}`}
                </div>
              </button>
            );
          })}
        </div>
      </section>

      {/* Payment method picker */}
      <section className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-500">
          Choose payment method
        </h2>
        {(Object.entries(grouped) as [PaymentMethod["category"], PaymentMethod[]][])
          .filter(([, list]) => list.length > 0)
          .map(([cat, list]) => (
            <div key={cat} className="mt-4">
              <h3 className="mb-2 text-xs font-medium uppercase tracking-wider text-gray-400">
                {CATEGORY_LABEL[cat]}
              </h3>
              <div className="grid gap-2 sm:grid-cols-2">
                {list.map((m) => {
                  const Icon = CATEGORY_ICON[m.category];
                  const active = provider === m.slug;
                  return (
                    <button
                      key={m.slug}
                      onClick={() => {
                        setProvider(m.slug);
                        setBankInstructions(null);
                      }}
                      className={
                        "flex items-start gap-3 rounded-md border px-4 py-3 text-left transition " +
                        (active
                          ? "border-blue-600 bg-blue-50 ring-1 ring-blue-600"
                          : "border-gray-200 hover:border-gray-300")
                      }
                    >
                      <Icon className="mt-0.5 h-5 w-5 flex-shrink-0 text-gray-500" />
                      <div className="min-w-0">
                        <div className="font-semibold text-gray-900">{m.name}</div>
                        <div className="text-xs text-gray-500">{m.description}</div>
                      </div>
                      {active && (
                        <Check className="ml-auto mt-0.5 h-4 w-4 text-blue-600" />
                      )}
                    </button>
                  );
                })}
              </div>
            </div>
          ))}
      </section>

      {/* Summary + CTA */}
      <section className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
        <div className="flex items-center justify-between text-sm">
          <span className="text-gray-600">{plan.name} — {billingCycle}</span>
          <span className="font-mono text-base font-bold text-gray-900">
            PKR {amount.toLocaleString("en-PK")}
          </span>
        </div>
        <button
          disabled={!provider || checkout.isPending}
          onClick={() => checkout.mutate()}
          className="mt-5 w-full rounded-md bg-blue-600 px-4 py-3 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-40"
        >
          {checkout.isPending
            ? "Starting checkout…"
            : provider
              ? `Continue with ${methods.data?.find((m) => m.slug === provider)?.name}`
              : "Select a payment method"}
        </button>
        {checkout.isError && (
          <p className="mt-3 text-xs text-red-600">
            {(checkout.error as Error).message}
          </p>
        )}
        {bankInstructions && (
          <pre className="mt-4 overflow-x-auto whitespace-pre-wrap rounded-md bg-gray-50 p-4 text-xs leading-relaxed text-gray-800">
            {bankInstructions}
          </pre>
        )}
        <p className="mt-4 text-xs text-gray-500">
          By continuing you agree to the{" "}
          <a className="underline" href="/terms">Terms</a> and{" "}
          <a className="underline" href="/privacy">Privacy Policy</a>. We never
          store your card or wallet credentials — those go directly to the
          gateway.
        </p>
      </section>
    </div>
  );
}

const CATEGORY_LABEL: Record<PaymentMethod["category"], string> = {
  wallet: "Mobile wallets",
  bank: "Bank accounts",
  card: "Cards",
  manual: "Bank transfer (manual)",
};
