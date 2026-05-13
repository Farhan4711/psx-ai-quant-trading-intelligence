import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Terms of Service | PSX AI",
  description: "Terms governing use of PSX AI.",
};

export default function TermsPage() {
  return (
    <article className="mx-auto max-w-3xl px-4 py-16 sm:px-6 prose prose-gray">
      <div className="not-prose rounded-md border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
        <p className="font-semibold">⚠ Draft pending lawyer review</p>
        <p className="mt-1">
          This page reflects our current intentions but has not been
          reviewed by Pakistani counsel. Items marked{" "}
          <code className="rounded bg-amber-100 px-1">[BRACKETS]</code> in
          the source will be finalised before public launch. Until then,
          treat this as informational.
        </p>
      </div>

      <h1>Terms of Service</h1>
      <p>
        <em>Last updated: 2026-05-08 (draft)</em>
      </p>

      <h2>1. What PSX AI is and is not</h2>
      <p>
        PSX AI is a portfolio-tracking and analytics tool for Pakistan
        Stock Exchange investors. It provides tax-aware portfolio
        tracking, technical-indicator computation with educational
        interpretation, probabilistic signals with confidence labels,
        news sentiment, pump-and-dump anomaly flags, and educational
        content.
      </p>
      <p>
        <strong>PSX AI is NOT</strong> a SECP-registered investment
        advisor, broker-dealer, custodian, or asset manager. We do not
        give personalised investment recommendations. All analytical
        outputs are educational tools. You remain responsible for your
        own investment decisions.
      </p>

      <h2>2. Account responsibilities</h2>
      <p>
        You must be 18+. Keep your password confidential, enable 2FA, and
        notify us at <a href="mailto:hello@psxai.example">hello@psxai.example</a>{" "}
        if you suspect unauthorised access. Don&apos;t use the Service
        for insider trading, market manipulation, or any unlawful
        purpose.
      </p>

      <h2>3. Subscriptions</h2>
      <p>
        Free is genuinely free, no card required. Paid tiers (Pro, Pro+)
        are billed monthly or annually in PKR. Cancel any time —
        cancellation takes effect at the end of the current billing
        period. We may change pricing with advance notice to active
        subscribers.
      </p>

      <h2>4. Predictions and signals</h2>
      <p>
        Signals shown in the Service are probabilistic model outputs.
        Every signal carries a confidence label; signals where the
        underlying model fails validation are explicitly marked
        &quot;predictions disabled.&quot; <strong>We provide no
        warranty</strong> on accuracy. Use signals as inputs to your own
        analysis, not as direct trade instructions.
      </p>

      <h2>5. Data ownership</h2>
      <p>
        You own the data you enter (portfolios, trades, watchlists,
        notes). We process this data per our{" "}
        <a href="/privacy">Privacy Policy</a>. We own the Service
        software, models, content, and brand. You may export your own
        data any time.
      </p>

      <h2>6. Liability</h2>
      <p>
        To the maximum extent permitted by Pakistani law, our total
        liability for any claim is limited to fees you paid in the 12
        months preceding the claim. We are not liable for investment
        losses, missed opportunities, or third-party data errors.
      </p>

      <h2>7. Termination</h2>
      <p>
        You may close your account any time in Settings. We may suspend
        accounts violating these Terms.
      </p>

      <h2>8. Governing law</h2>
      <p>
        Pakistani law. Disputes go to courts in the jurisdiction
        specified in the finalised version of these Terms.
      </p>

      <h2>9. Contact</h2>
      <p>
        Legal notices and questions:{" "}
        <a href="mailto:hello@psxai.example">hello@psxai.example</a>.
      </p>
    </article>
  );
}
