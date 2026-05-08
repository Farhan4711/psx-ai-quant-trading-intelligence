import * as Sentry from "@sentry/nextjs";

const dsn = process.env.NEXT_PUBLIC_SENTRY_DSN;

if (dsn) {
  Sentry.init({
    dsn,
    environment: process.env.NEXT_PUBLIC_SENTRY_ENV ?? "development",
    // Capture 10% of transactions in prod for tracing
    tracesSampleRate: process.env.NODE_ENV === "production" ? 0.1 : 1.0,
    // Replays only on errors — keeps bundle/quota down
    replaysOnErrorSampleRate: 1.0,
    replaysSessionSampleRate: 0,
    // Don't send PII
    sendDefaultPii: false,
  });
}
