import Link from "next/link";

export default function NotFound() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
      <div className="max-w-md text-center">
        <p className="text-sm font-semibold uppercase tracking-wider text-blue-600">
          404
        </p>
        <h1 className="mt-2 text-3xl font-bold text-gray-900">Page not found</h1>
        <p className="mt-2 text-sm text-gray-600">
          The page you&apos;re looking for doesn&apos;t exist or has moved.
        </p>
        <Link
          href="/app"
          className="mt-6 inline-block rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
        >
          Go to dashboard
        </Link>
      </div>
    </div>
  );
}
