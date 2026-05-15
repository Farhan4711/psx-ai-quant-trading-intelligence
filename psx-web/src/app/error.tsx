"use client";

import * as Sentry from "@sentry/nextjs";
import { useEffect } from "react";
import Link from "next/link";

export default function ErrorBoundary({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    Sentry.captureException(error);
  }, [error]);

  return (
    <div className="flex min-h-[60vh] items-center justify-center px-4">
      <div className="max-w-md text-center">
        <h1 className="text-2xl font-bold text-gray-900">Something went wrong</h1>
        <p className="mt-2 text-sm text-gray-600">
          We&apos;ve been notified and we&apos;re looking into it. You can try
          again or head back to the dashboard.
        </p>
        {error.digest && (
          <p className="mt-2 text-xs text-gray-400">Reference: {error.digest}</p>
        )}
        <div className="mt-6 flex justify-center gap-2">
          <button
            onClick={reset}
            className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
          >
            Try again
          </button>
          <Link
            href="/dashboard"
            className="rounded-md border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            Go home
          </Link>
        </div>
      </div>
    </div>
  );
}
