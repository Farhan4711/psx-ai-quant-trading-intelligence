import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "About | PSX AI",
  description:
    "Why PSX AI exists, who built it, what we believe about Pakistani retail investing.",
};

export default function AboutPage() {
  return (
    <article className="mx-auto max-w-3xl px-4 py-16 sm:px-6 prose prose-gray">
      <h1>About PSX AI</h1>

      <h2>Why this exists</h2>
      <p>
        Pakistani retail investors don&apos;t lack ambition — they lack tools.
        Every other equity-tracking app on the App Store treats PSX as an
        afterthought, shows gross numbers without CGT, ignores filer status
        entirely, and offers no honest signal about which moves are
        legitimate vs which are coordinated manipulation.
      </p>
      <p>
        Meanwhile the public-research literature has been clear for years
        that the variables that matter — Williams %R, momentum, disparity,
        volume spikes — can be turned into useful (not perfect) signals on
        PSX names. The math has existed. The product hasn&apos;t.
      </p>

      <h2>What we believe</h2>
      <ul>
        <li>
          <strong>Honest predictions beat impressive predictions.</strong>{" "}
          A signal with a confidence label and an audit trail is worth ten
          black-box &quot;buy now&quot; alerts.
        </li>
        <li>
          <strong>The free tier should be genuinely useful.</strong> If you
          can&apos;t track a portfolio with tax-aware after-PnL on the free
          tier, the free tier is bait. We don&apos;t do bait.
        </li>
        <li>
          <strong>Show the math.</strong> Trade narration, per-lot CGT
          breakdown, top contributing features — users learn the moment we
          stop hiding the work.
        </li>
        <li>
          <strong>Shariah investing isn&apos;t a checkbox.</strong> It&apos;s
          a constraint that touches search, trade entry, portfolio display,
          and an annual purification report. We built it as a first-class
          mode, not a filter.
        </li>
      </ul>

      <h2>What we&apos;re not</h2>
      <p>
        PSX AI is <strong>not a SECP-registered investment advisor</strong>.
        We don&apos;t make personalised buy/sell recommendations.
        Predictions and signals are educational. Always combine with your
        own analysis, and consult a qualified advisor before significant
        moves.
      </p>

      <h2>Where we are</h2>
      <p>
        Phase 4 complete. The free tier is fully built — sign up and run it.
        Paid plans are wired in the codebase but card-payment integration
        for Pakistani retail isn&apos;t live yet (Stripe doesn&apos;t serve
        Pakistan natively; JazzCash/Easypaisa integration in flight). Early
        adopters get 6 months Pro free when payment launches.
      </p>

      <h2>Get in touch</h2>
      <p>
        Bug reports, feature requests, philosophical disagreements with our
        approach: <a href="mailto:hello@psxai.example">hello@psxai.example</a>.
        We read everything.
      </p>

      <p className="not-prose mt-10 rounded-md bg-blue-50 p-4 text-sm text-blue-900">
        <strong>Ready to try it?</strong>{" "}
        <Link href="/signup" className="underline">
          Sign up free →
        </Link>
      </p>
    </article>
  );
}
