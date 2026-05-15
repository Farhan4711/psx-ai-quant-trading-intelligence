"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { Check } from "lucide-react";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface Plan {
  id: number;
  slug: string;
  name: string;
  tagline: string;
  price_pkr_monthly: string;
  price_pkr_annual: string | null;
  features: string[];
  display_order: number;
}

async function fetchPlans(): Promise<Plan[]> {
  const res = await fetch(`${API_URL}/api/v1/billing/plans`);
  if (!res.ok) throw new Error("Failed to load plans");
  return res.json();
}

export default function PricingPage() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["billing-plans-public"],
    queryFn: fetchPlans,
    staleTime: 24 * 60 * 60_000,
    retry: false,
  });

  return (
    <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6">
      <div className="text-center">
        <h1 className="text-3xl font-bold tracking-tight text-gray-900 sm:text-4xl">
          Honest pricing
        </h1>
        <p className="mx-auto mt-3 max-w-2xl text-base text-gray-600">
          Free forever for 90% of users. Pro for the engaged minority who
          want predictions and sentiment. Pro+ for API access and
          institutional desks.
        </p>
      </div>

      {isLoading ? (
        <div className="mt-12 grid gap-6 lg:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-96 animate-pulse rounded-xl bg-gray-100" />
          ))}
        </div>
      ) : isError || !data ? (
        <p className="mt-12 text-center text-sm text-red-600">
          Couldn&apos;t load plans. Try again in a moment.
        </p>
      ) : (
        <div className="mt-12 grid gap-6 lg:grid-cols-3">
          {data.map((plan, i) => (
            <PlanCard key={plan.id} plan={plan} highlighted={i === 1} />
          ))}
        </div>
      )}

      <div className="mt-16 rounded-lg border border-emerald-200 bg-emerald-50 p-6 text-sm text-emerald-900">
        <h2 className="font-semibold">Pay with what you already use</h2>
        <p className="mt-2">
          We support JazzCash, Easypaisa, Meezan Bank IPG, 1LINK PayFast
          (Allied / HBL / UBL / Alfalah / MCB and other 1LINK-enabled banks),
          SafePay (Visa / Mastercard), NayaPay wallet, and manual bank
          transfer to a Meezan account if you prefer the traditional route.
          Card and wallet data go directly to the gateway — we never see
          or store it.
        </p>
        <p className="mt-3 text-xs text-emerald-800">
          Shariah-conscious investors: Meezan IPG settles through Meezan
          Bank&apos;s Islamic banking treasury.
        </p>
      </div>
    </div>
  );
}

function PlanCard({ plan, highlighted }: { plan: Plan; highlighted: boolean }) {
  const monthly = parseFloat(plan.price_pkr_monthly);
  const annual = plan.price_pkr_annual ? parseFloat(plan.price_pkr_annual) : null;
  const isFree = monthly === 0;
  const annualSavings =
    annual && monthly > 0
      ? Math.max(0, Math.round((1 - annual / (monthly * 12)) * 100))
      : 0;

  return (
    <div
      className={
        "flex flex-col rounded-xl border p-6 shadow-sm " +
        (highlighted
          ? "border-blue-600 bg-blue-50 ring-1 ring-blue-600"
          : "border-gray-200 bg-white")
      }
    >
      {highlighted && (
        <p className="mb-2 inline-block self-start rounded-full bg-blue-600 px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-white">
          Most popular
        </p>
      )}
      <h2 className="text-xl font-bold text-gray-900">{plan.name}</h2>
      <p className="mt-1 text-sm text-gray-600">{plan.tagline}</p>

      <div className="mt-5">
        {isFree ? (
          <p className="text-3xl font-bold tabular-nums text-gray-900">
            Free
          </p>
        ) : (
          <>
            <p className="text-3xl font-bold tabular-nums text-gray-900">
              PKR {monthly.toLocaleString("en-PK")}
              <span className="text-base font-normal text-gray-500">/mo</span>
            </p>
            {annual && annualSavings > 0 && (
              <p className="mt-1 text-xs text-gray-500">
                or PKR {annual.toLocaleString("en-PK")}/year (save {annualSavings}%)
              </p>
            )}
          </>
        )}
      </div>

      <Link
        href={isFree ? "/signup" : `/checkout?plan=${plan.slug}`}
        className={
          "mt-5 block rounded-md px-4 py-2 text-center text-sm font-semibold " +
          (highlighted
            ? "bg-blue-600 text-white hover:bg-blue-700"
            : "border border-gray-300 bg-white text-gray-800 hover:bg-gray-50")
        }
      >
        {isFree ? "Start free" : `Subscribe — PKR ${monthly.toLocaleString("en-PK")}/mo`}
      </Link>

      <ul className="mt-6 space-y-2 text-sm text-gray-700">
        {plan.features.map((f) => (
          <li key={f} className="flex items-start gap-2">
            <Check className="mt-0.5 h-4 w-4 flex-shrink-0 text-emerald-600" />
            <span>{f}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
