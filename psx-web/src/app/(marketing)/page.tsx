import type { Metadata } from "next";
import Link from "next/link";
import {
  ArrowRight,
  Briefcase,
  Calculator,
  FlaskConical,
  Grid3x3,
  Newspaper,
  Sparkles,
  Target,
} from "lucide-react";

export const metadata: Metadata = {
  title: "PSX AI — honest analytics for Pakistani investors",
  description:
    "Tax-aware portfolio tracking, technical analysis, predictions with confidence labels, pump-and-dump alerts, and a filer simulator. Built for Pakistani retail investors who want the analyst layer.",
  openGraph: {
    title: "PSX AI",
    description: "Honest analytics for Pakistani retail investors.",
  },
};

export default function MarketingHome() {
  return (
    <>
      {/* Hero */}
      <section className="border-b border-gray-100 bg-gradient-to-b from-blue-50 to-white">
        <div className="mx-auto max-w-5xl px-4 py-20 text-center sm:px-6 sm:py-28">
          <p className="text-xs font-semibold uppercase tracking-wider text-blue-700">
            Built for PSX retail
          </p>
          <h1 className="mt-3 text-4xl font-bold tracking-tight text-gray-900 sm:text-5xl">
            Your portfolio is up PKR 47,500.
            <br />
            <span className="text-blue-700">
              Net of tax, it&apos;s PKR 39,800.
            </span>
          </h1>
          <p className="mx-auto mt-5 max-w-2xl text-base text-gray-600 sm:text-lg">
            Every other PSX app shows gross numbers. We do the CGT math
            built-in, simulate filer-vs-non-filer, flag pump-and-dump days,
            and label every prediction with honest confidence. Free forever
            for 90% of users.
          </p>
          <div className="mt-8 flex flex-wrap justify-center gap-3">
            <Link
              href="/signup"
              className="rounded-md bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-blue-700"
            >
              Start free — no card
            </Link>
            <Link
              href="/features"
              className="rounded-md border border-gray-300 bg-white px-5 py-2.5 text-sm font-semibold text-gray-800 hover:bg-gray-50"
            >
              See features
            </Link>
          </div>
          <p className="mt-5 text-xs text-gray-500">
            Not a SECP-registered investment advisor. Educational tools only.
          </p>
        </div>
      </section>

      {/* Differentiators */}
      <section className="mx-auto max-w-6xl px-4 py-20 sm:px-6">
        <h2 className="text-center text-2xl font-bold text-gray-900 sm:text-3xl">
          What you get that no other PSX app has
        </h2>
        <div className="mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          <FeatureCard
            icon={Calculator}
            iconClass="text-emerald-600 bg-emerald-50"
            title="Tax-aware portfolio"
            blurb="Every trade runs through SECP CGT rules. Filer status, FIFO matching, NCCPL deductions baked in. After-tax P&L on the dashboard."
          />
          <FeatureCard
            icon={Briefcase}
            iconClass="text-blue-600 bg-blue-50"
            title="Filer vs non-filer simulator"
            blurb='See exactly what your filer status is worth. "By becoming a filer you would have kept an additional PKR 87,400 last year."'
          />
          <FeatureCard
            icon={Sparkles}
            iconClass="text-violet-600 bg-violet-50"
            title="Predictions with honest confidence"
            blurb="Three-model ensemble per stock. High agreement = high confidence. Stocks where the model fails validation explicitly say 'predictions disabled'."
          />
          <FeatureCard
            icon={Newspaper}
            iconClass="text-amber-600 bg-amber-50"
            title="Pump-and-dump alerts"
            blurb="Volume spike + price move + no news context = high-suspicion flag, surfaced on stock pages and pushed to your inbox."
          />
          <FeatureCard
            icon={Target}
            iconClass="text-rose-600 bg-rose-50"
            title="Goals with realism check"
            blurb="Set a Hajj or retirement target. We tell you the required CAGR and rate it: feasible, stretch, aggressive, or unrealistic. With remediation."
          />
          <FeatureCard
            icon={Grid3x3}
            iconClass="text-cyan-600 bg-cyan-50"
            title="Shariah Mode end-to-end"
            blurb="Filters every screen to KMI-compliant stocks. Dividend purification calculator built in. Warning on non-compliant trades."
          />
        </div>
      </section>

      {/* Backtest callout */}
      <section className="border-t border-gray-100 bg-gray-50">
        <div className="mx-auto max-w-6xl px-4 py-20 sm:px-6">
          <div className="grid gap-8 lg:grid-cols-2 lg:items-center">
            <div>
              <FlaskConical className="h-8 w-8 text-blue-600" />
              <h2 className="mt-3 text-2xl font-bold text-gray-900 sm:text-3xl">
                Test before you trade
              </h2>
              <p className="mt-3 text-base text-gray-600">
                Five preset strategies on real PSX adjusted prices, with
                trade-by-trade narration so you understand what the
                strategy actually did — not just the bottom-line return.
                Build your own no-code rules in the strategy editor.
              </p>
              <ul className="mt-5 space-y-2 text-sm text-gray-700">
                <li>✓ Adjusted prices (split/dividend stable)</li>
                <li>✓ Real commission + tax modelling</li>
                <li>✓ Plain-English Lessons panel: did the strategy actually beat buy-and-hold?</li>
                <li>✓ Custom rule builder using indicators you already understand</li>
              </ul>
            </div>
            <div className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
              <div className="rounded-md bg-amber-50 p-3 text-xs text-amber-900">
                <strong>Lesson:</strong> Buy-and-hold beat <em>SMA crossover</em> by
                12.3% over this period. Active strategies need to overcome both
                fees AND the high bar of just holding good companies — most of
                them don&apos;t, on most stocks.
              </div>
              <div className="mt-3 grid grid-cols-2 gap-3 text-xs text-gray-600">
                <Stat label="CAGR" value="+8.4%" />
                <Stat label="Sharpe" value="0.42" />
                <Stat label="Max DD" value="-31.2%" valueClass="text-red-700" />
                <Stat label="Trades" value="14" />
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="border-t border-gray-100 bg-blue-700 text-white">
        <div className="mx-auto max-w-3xl px-4 py-16 text-center sm:px-6">
          <h2 className="text-2xl font-bold sm:text-3xl">
            The free tier is genuinely free
          </h2>
          <p className="mt-3 text-blue-100">
            Portfolio, watchlist, indicators, sector comparison, Shariah
            tools, risk profile, goals planner. Forever. Pro is for the
            engaged minority who want predictions and sentiment.
          </p>
          <div className="mt-6 flex flex-wrap justify-center gap-3">
            <Link
              href="/signup"
              className="rounded-md bg-white px-5 py-2.5 text-sm font-semibold text-blue-700 hover:bg-blue-50"
            >
              Sign up
            </Link>
            <Link
              href="/pricing"
              className="rounded-md border border-white/30 px-5 py-2.5 text-sm font-semibold text-white hover:bg-blue-600"
            >
              See pricing
            </Link>
          </div>
        </div>
      </section>
    </>
  );
}

function FeatureCard({
  icon: Icon,
  iconClass,
  title,
  blurb,
}: {
  icon: typeof ArrowRight;
  iconClass: string;
  title: string;
  blurb: string;
}) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
      <div className={`inline-flex h-10 w-10 items-center justify-center rounded-md ${iconClass}`}>
        <Icon className="h-5 w-5" />
      </div>
      <h3 className="mt-3 text-base font-semibold text-gray-900">{title}</h3>
      <p className="mt-1 text-sm text-gray-600">{blurb}</p>
    </div>
  );
}

function Stat({
  label,
  value,
  valueClass,
}: {
  label: string;
  value: string;
  valueClass?: string;
}) {
  return (
    <div className="rounded-md border border-gray-100 bg-gray-50 p-2 text-center">
      <p className="text-[10px] uppercase tracking-wider text-gray-500">
        {label}
      </p>
      <p
        className={`mt-0.5 text-sm font-semibold tabular-nums ${valueClass ?? "text-gray-900"}`}
      >
        {value}
      </p>
    </div>
  );
}
