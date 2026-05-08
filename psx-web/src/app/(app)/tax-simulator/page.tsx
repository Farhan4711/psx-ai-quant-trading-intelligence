"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchTaxSimulation, type TaxSimulatorResult } from "@/lib/api/alerts";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { formatCurrency } from "@/lib/utils/format";
import { ArrowRight, ExternalLink, Sparkles } from "lucide-react";

function defaultFrom(): string {
  const d = new Date();
  d.setFullYear(d.getFullYear() - 1);
  return d.toISOString().slice(0, 10);
}
function defaultTo(): string {
  return new Date().toISOString().slice(0, 10);
}

export default function TaxSimulatorPage() {
  const [from, setFrom] = useState(defaultFrom());
  const [to, setTo] = useState(defaultTo());

  const { data, isLoading, isError, refetch, isFetching } = useQuery({
    queryKey: ["tax-simulator", from, to],
    queryFn: () => fetchTaxSimulation(from, to),
    staleTime: 60_000,
  });

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">
          Filer vs Non-Filer simulator
        </h1>
        <p className="mt-1 text-sm text-gray-500">
          Run your actual transactions through the SECP rules twice — once as
          a filer, once as a non-filer. See exactly how much filer status is
          worth.
        </p>
      </div>

      {/* Date range */}
      <div className="flex flex-wrap items-end gap-3 rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
        <div className="space-y-1.5">
          <Label htmlFor="ts-from">From</Label>
          <Input
            id="ts-from"
            type="date"
            value={from}
            onChange={(e) => setFrom(e.target.value)}
            className="w-44"
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="ts-to">To</Label>
          <Input
            id="ts-to"
            type="date"
            value={to}
            onChange={(e) => setTo(e.target.value)}
            className="w-44"
          />
        </div>
        <Button onClick={() => refetch()} disabled={isFetching}>
          {isFetching ? "Computing…" : "Run"}
        </Button>
      </div>

      {isLoading ? (
        <div className="h-48 animate-pulse rounded-lg bg-gray-100" />
      ) : isError ? (
        <p className="text-sm text-red-600">Failed to compute simulation.</p>
      ) : data ? (
        <Result data={data} />
      ) : null}
    </div>
  );
}

function Result({ data }: { data: TaxSimulatorResult }) {
  const savings = parseFloat(data.filer_savings_pkr);
  const cgtFiler = parseFloat(data.filer.cgt_pkr);
  const cgtNonfiler = parseFloat(data.non_filer.cgt_pkr);
  const netFiler = parseFloat(data.filer.net_realised_pkr);
  const netNonfiler = parseFloat(data.non_filer.net_realised_pkr);

  return (
    <div className="space-y-5">
      {/* Hero savings callout */}
      {savings > 0 ? (
        <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-5 text-center">
          <Sparkles className="mx-auto h-6 w-6 text-emerald-600" />
          <p className="mt-2 text-sm uppercase tracking-wider text-emerald-700">
            Filer status would have saved you
          </p>
          <p className="mt-1 text-3xl font-bold tabular-nums text-emerald-900">
            {formatCurrency(savings)}
          </p>
          <p className="mt-1 text-xs text-emerald-700">{data.narrative}</p>
        </div>
      ) : (
        <div className="rounded-lg border border-gray-200 bg-gray-50 p-4 text-center">
          <p className="text-sm text-gray-700">{data.narrative}</p>
        </div>
      )}

      {/* Side-by-side comparison */}
      <div className="grid gap-4 md:grid-cols-2">
        <ScenarioCard
          title="As Filer"
          tone="emerald"
          cgt={cgtFiler}
          netRealised={netFiler}
        />
        <ScenarioCard
          title="As Non-Filer"
          tone="red"
          cgt={cgtNonfiler}
          netRealised={netNonfiler}
        />
      </div>

      {/* Common cost line items */}
      <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-gray-500">
          Common to both scenarios
        </h2>
        <dl className="grid grid-cols-2 gap-3 text-sm">
          <Row label="Sells processed" value={String(data.sells_processed)} />
          <Row
            label="Gross realised gain"
            value={formatCurrency(parseFloat(data.total_gross_gain_pkr))}
          />
          <Row
            label="Brokerage paid"
            value={formatCurrency(parseFloat(data.total_brokerage_pkr))}
          />
          <Row
            label="FED + CVT"
            value={formatCurrency(
              parseFloat(data.total_fed_pkr) + parseFloat(data.total_cvt_pkr),
            )}
          />
        </dl>
      </div>

      {/* CTA: file your taxes */}
      {savings > 0 && (
        <div className="rounded-lg border border-blue-200 bg-blue-50 p-4">
          <h3 className="text-sm font-semibold text-blue-900">
            How to become a filer
          </h3>
          <ol className="mt-2 list-decimal space-y-1 pl-5 text-sm text-blue-900">
            <li>
              Get your NTN (National Tax Number) from{" "}
              <a
                className="inline-flex items-center gap-0.5 underline hover:no-underline"
                href="https://iris.fbr.gov.pk"
                target="_blank"
                rel="noreferrer noopener"
              >
                FBR&apos;s IRIS portal
                <ExternalLink className="h-3 w-3" />
              </a>
              .
            </li>
            <li>
              File your annual income tax return (typically by Sep 30 each year).
            </li>
            <li>
              Wait for FBR to publish the next ATL (Active Taxpayer List). You
              appear as a filer once you&apos;re on it.
            </li>
            <li>
              Once on the ATL, NCCPL automatically deducts CGT at filer rates
              going forward.
            </li>
          </ol>
          <p className="mt-2 text-xs text-blue-800">
            Read the full filer-status guide on{" "}
            <a
              className="underline"
              href="https://www.fbr.gov.pk/active-taxpayer-list-atl/51149/131220"
              target="_blank"
              rel="noreferrer noopener"
            >
              fbr.gov.pk
            </a>
            .
          </p>
        </div>
      )}
    </div>
  );
}

function ScenarioCard({
  title,
  tone,
  cgt,
  netRealised,
}: {
  title: string;
  tone: "emerald" | "red";
  cgt: number;
  netRealised: number;
}) {
  const headerClass =
    tone === "emerald"
      ? "border-emerald-200 bg-emerald-50 text-emerald-900"
      : "border-red-200 bg-red-50 text-red-900";
  return (
    <div className="overflow-hidden rounded-lg border border-gray-200 bg-white shadow-sm">
      <div className={`border-b px-4 py-2 text-sm font-semibold ${headerClass}`}>
        {title}
      </div>
      <dl className="space-y-1.5 p-4 text-sm">
        <Row label="CGT owed" value={formatCurrency(cgt)} bold />
        <Row label="Net realised (after all charges)" value={formatCurrency(netRealised)} />
      </dl>
    </div>
  );
}

function Row({
  label,
  value,
  bold,
}: {
  label: string;
  value: string;
  bold?: boolean;
}) {
  return (
    <div className="flex items-center justify-between border-b border-gray-100 py-1.5 last:border-0">
      <dt className="text-gray-500">{label}</dt>
      <dd className={bold ? "font-semibold text-gray-900" : "text-gray-700"}>
        {value}
      </dd>
    </div>
  );
}

