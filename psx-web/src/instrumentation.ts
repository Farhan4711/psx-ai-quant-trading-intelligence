// Next.js calls this file's `register()` once at server start.
// We use it to load the appropriate Sentry config based on runtime.

export async function register() {
  if (process.env.NEXT_RUNTIME === "nodejs") {
    await import("../sentry.server.config");
  }
}
