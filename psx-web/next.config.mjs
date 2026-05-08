import { withSentryConfig } from "@sentry/nextjs";

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,

  // Standalone output is friendlier to Docker — keeps the runtime image tiny
  output: "standalone",

  // Headers applied to every response
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "X-Frame-Options", value: "DENY" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          {
            key: "Permissions-Policy",
            value: "geolocation=(), microphone=(), camera=()",
          },
        ],
      },
    ];
  },
};

// Sentry only wraps the config when its env vars are set; in dev/CI without
// SENTRY_AUTH_TOKEN it falls back to the bare config.
const sentryConfig = {
  silent: !process.env.SENTRY_AUTH_TOKEN,
  org: process.env.SENTRY_ORG,
  project: process.env.SENTRY_PROJECT,
  authToken: process.env.SENTRY_AUTH_TOKEN,
  hideSourceMaps: true,
  disableLogger: true,
  // Tunnel client errors through our origin so ad-blockers don't drop them
  tunnelRoute: "/monitoring",
};

export default process.env.SENTRY_AUTH_TOKEN
  ? withSentryConfig(nextConfig, sentryConfig)
  : nextConfig;
