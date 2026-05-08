"use client";

import * as Sentry from "@sentry/nextjs";
import { useEffect } from "react";

export default function GlobalError({
  error,
}: {
  error: Error & { digest?: string };
}) {
  useEffect(() => {
    Sentry.captureException(error);
  }, [error]);

  return (
    <html lang="en">
      <body>
        <div style={{ padding: "2rem", fontFamily: "system-ui, sans-serif" }}>
          <h1>Application error</h1>
          <p>
            Something went wrong loading the application. Please refresh the
            page.
          </p>
        </div>
      </body>
    </html>
  );
}
