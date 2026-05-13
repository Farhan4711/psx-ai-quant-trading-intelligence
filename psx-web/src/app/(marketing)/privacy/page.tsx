import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Privacy Policy | PSX AI",
  description: "How PSX AI handles your data.",
};

export default function PrivacyPage() {
  return (
    <article className="mx-auto max-w-3xl px-4 py-16 sm:px-6 prose prose-gray">
      <div className="not-prose rounded-md border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
        <p className="font-semibold">⚠ Draft pending lawyer review</p>
        <p className="mt-1">
          Pakistan&apos;s data-protection legislation is in active flux.
          This page describes our current practices and intent; the final
          version will be reviewed by Pakistani counsel before launch.
        </p>
      </div>

      <h1>Privacy Policy</h1>
      <p>
        <em>Last updated: 2026-05-08 (draft)</em>
      </p>

      <h2>TL;DR</h2>
      <p>
        We collect the minimum data needed to run the Service, store it
        securely, <strong>never sell it</strong>, and let you export or
        delete it on request.
      </p>

      <h2>1. What we collect</h2>
      <ul>
        <li>
          <strong>Account data</strong>: email, password (Argon2id hash
          only — never plaintext), optional full name / phone / DOB,
          filer status, Shariah Mode preference
        </li>
        <li>
          <strong>Portfolio data</strong>: trades, watchlists, notes,
          goals, risk profile, custom strategies
        </li>
        <li>
          <strong>Usage</strong>: IP address, browser, session
          timestamps, pages visited, feature usage (for product
          improvement)
        </li>
        <li>
          <strong>Cookies</strong>: one HTTP-only session cookie. Optional
          analytics cookie if you consent. No third-party advertising.
        </li>
      </ul>
      <p>
        <strong>We do not collect</strong>: bank/card numbers (handled by
        our payment provider), your broker login credentials, or anything
        from third parties without your consent.
      </p>

      <h2>2. How we use it</h2>
      <ul>
        <li>To provide the Service (portfolio math, predictions)</li>
        <li>To secure your account (anomaly detection, rate limits)</li>
        <li>To improve the product (aggregated, anonymised analysis)</li>
        <li>
          To communicate (transactional emails; marketing only with
          explicit opt-in)
        </li>
      </ul>
      <p>
        <strong>We never</strong> sell your data, trade against your
        portfolio, or share individual user data with advertisers.
      </p>

      <h2>3. Anonymized benchmarking (opt-in)</h2>
      <p>
        If you enable &quot;Share anonymously&quot; in Settings, your
        portfolio&apos;s aggregate metrics contribute to community
        benchmarks shown on the dashboard. Specific trades and identifying
        details are never shared. Aggregates with fewer than 5
        contributing peers are suppressed (k-anonymity floor). You can
        disable this any time.
      </p>

      <h2>4. Your rights</h2>
      <ul>
        <li>
          <strong>Access</strong>: export your data via Settings
        </li>
        <li>
          <strong>Correct</strong>: edit account data in Settings
        </li>
        <li>
          <strong>Delete</strong>: close your account; all personal data
          removed within 30 days
        </li>
        <li>
          <strong>Object</strong>: contact us at{" "}
          <a href="mailto:hello@psxai.example">hello@psxai.example</a>
        </li>
      </ul>

      <h2>5. Retention</h2>
      <ul>
        <li>Account + portfolio: while active, plus 30 days after deletion</li>
        <li>Logs: 90 days</li>
        <li>Billing records: as required by Pakistani tax law</li>
        <li>Anonymised aggregates: indefinitely (no longer tied to you)</li>
      </ul>

      <h2>6. Security incidents</h2>
      <p>
        We will notify affected users without undue delay if a security
        incident affects their personal data.
      </p>

      <h2>7. Contact</h2>
      <p>
        Privacy questions and data-subject requests:{" "}
        <a href="mailto:hello@psxai.example">hello@psxai.example</a>.
      </p>
    </article>
  );
}
