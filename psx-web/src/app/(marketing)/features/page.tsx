import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Features | PSX AI",
  description:
    "Everything PSX AI does — tax engine, predictions, sentiment, backtesting, Shariah tools, goals planner, and more.",
};

const SECTIONS: { title: string; body: string; bullets: string[] }[] = [
  {
    title: "Tax-aware portfolio tracking",
    body:
      "Every buy, sell, dividend, bonus, and rights issue gets matched through SECP CGT rules. FIFO lot matching, filer-vs-non-filer rates, NCCPL deductions at source — all of it baked in. The dashboard shows both gross and after-tax P&L so you know what you'd actually keep if you sold today.",
    bullets: [
      "Pre-Finance-Act-2024 progressive holding-period rates",
      "Post-Finance-Act-2024 flat 15% filer / 45% non-filer",
      "Per-trade matched-lots breakdown with explanation",
      "Filer-vs-non-filer simulator across your trade history",
    ],
  },
  {
    title: "Predictions with honest confidence",
    body:
      "A three-model ensemble (LSTM proxy + XGBoost proxy + Random Forest proxy in v1) scores each stock daily. High model agreement = high confidence. Stocks where the model fails validation explicitly say 'predictions disabled' — we never show a number we don't trust.",
    bullets: [
      "23-feature daily snapshot per stock",
      "Top 3 contributing features highlighted",
      "Rolling 30-day live accuracy on every prediction page",
      "Honest 'disabled' state for stocks the model can't handle",
    ],
  },
  {
    title: "Pump-and-dump anomaly detection",
    body:
      "A daily after-close worker flags suspicious days. Rule layer: 4× volume + 3% price move. Statistical layer: 6-feature z-score anomaly. Context layer: news + announcement check. A pure spike with no news context gets high severity; the same spike on earnings day gets downgraded.",
    bullets: [
      "Rule + anomaly + news-context filter",
      "Severity coloured by news justification",
      "Alerts inbox filtered to symbols you hold or watch",
      "On-stock warning banner with full explanation",
    ],
  },
  {
    title: "News Pulse + sentiment",
    body:
      "Per-symbol rolling 5-day sentiment with exponential time decay. Top 3 driving headlines surfaced. Event-type classification (earnings, guidance, regulatory, M&A, scandal, macro) so you know why the pulse moved.",
    bullets: [
      "Lexicon scorer in v1, FinBERT interface ready",
      "Negation handling baked in",
      "Source attribution + direct article links",
      "Plugs into the prediction feature pipeline",
    ],
  },
  {
    title: "Shariah tools end-to-end",
    body:
      "Toggle Shariah Mode and every screen filters to KMI-compliant stocks. Trade entries warn before recording non-compliant trades. Annual dividend purification calculator with mark-as-donated tracking. KMI delisting notifications.",
    bullets: [
      "Persistent header badge when active",
      "Non-compliant holdings grayed out in portfolio",
      "5% default purification rate (configurable)",
      "Mark-donated tracking + year-over-year reports",
    ],
  },
  {
    title: "Backtesting that teaches",
    body:
      "Five preset strategies on real PSX adjusted prices with retail commission modelling. Trade-by-trade narration explains exactly what triggered each entry and exit. Lessons panel frames the result against buy-and-hold so you see whether active strategies actually beat the passive bar.",
    bullets: [
      "SMA crossover, RSI, MACD, Bollinger revert, buy-and-hold",
      "Adjusted prices (split/dividend stable)",
      "Plain-English trade narration",
      "Custom no-code strategy builder for power users",
    ],
  },
  {
    title: "Goals + risk profile",
    body:
      "12-question quiz scores three axes (risk tolerance, time horizon, knowledge) → one of five archetypes. Goal planner computes the required CAGR for any target + deadline, rates it (feasible/stretch/aggressive/unrealistic), and suggests remediation when it's too aggressive.",
    bullets: [
      "5 archetypes mapped to recommended allocations",
      "Time-value-of-money solver, no approximations",
      "PKR-context realism thresholds (8/14/20% CAGR)",
      "Suggested-contribution or suggested-extension remediation",
    ],
  },
  {
    title: "Sector tools + macro overlays",
    body:
      "Treemap heatmap sized by market cap, coloured by day change. Compare 2-4 stocks within a sector with percentile-ranked metrics. Overlay any of 8 macro indicators (KIBOR, PKR/USD, Brent, gold) on any price chart — a beginner immediately sees that OGDC tracks oil and banks rally on rate decisions.",
    bullets: [
      "Pure-CSS treemap (no heavy charting deps)",
      "Side-by-side comparison with sector-percentile ranks",
      "Macro overlay on lightweight-charts dual scale",
      "KIBOR / SBP rate / FX / commodities all there",
    ],
  },
];

export default function FeaturesPage() {
  return (
    <div className="mx-auto max-w-4xl px-4 py-16 sm:px-6">
      <h1 className="text-3xl font-bold tracking-tight text-gray-900 sm:text-4xl">
        Everything PSX AI does
      </h1>
      <p className="mt-3 text-base text-gray-600">
        Most apps stop at &quot;here&apos;s a price chart.&quot; We go further
        — tax math, honest predictions, pump-and-dump alerts, Shariah
        purification — because Pakistani retail investors deserve the
        analyst layer.
      </p>

      <div className="mt-12 space-y-12">
        {SECTIONS.map((s) => (
          <section
            key={s.title}
            className="border-l-2 border-blue-200 pl-5 sm:pl-6"
          >
            <h2 className="text-xl font-bold text-gray-900">{s.title}</h2>
            <p className="mt-2 text-base text-gray-700">{s.body}</p>
            <ul className="mt-3 space-y-1.5 text-sm text-gray-700">
              {s.bullets.map((b) => (
                <li key={b}>✓ {b}</li>
              ))}
            </ul>
          </section>
        ))}
      </div>

      <div className="mt-16 rounded-lg bg-blue-700 p-6 text-center text-white">
        <h2 className="text-xl font-bold">Try it free</h2>
        <p className="mt-1 text-sm text-blue-100">
          No card. Forever-free tier covers most users.
        </p>
        <Link
          href="/signup"
          className="mt-4 inline-block rounded-md bg-white px-5 py-2 text-sm font-semibold text-blue-700 hover:bg-blue-50"
        >
          Sign up →
        </Link>
      </div>
    </div>
  );
}
