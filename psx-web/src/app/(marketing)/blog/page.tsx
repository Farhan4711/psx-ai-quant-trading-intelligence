import type { Metadata } from "next";
import Link from "next/link";
import { POSTS } from "./posts";

export const metadata: Metadata = {
  title: "Blog | PSX AI",
  description:
    "Articles on PSX investing, tax, technical analysis, Shariah finance, and more.",
};

export default function BlogIndex() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-16 sm:px-6">
      <h1 className="text-3xl font-bold tracking-tight text-gray-900 sm:text-4xl">
        Blog
      </h1>
      <p className="mt-3 text-base text-gray-600">
        Practical articles on PSX investing — the kind we wish existed when we
        started.
      </p>

      <ul className="mt-10 space-y-8">
        {POSTS.map((p) => (
          <li
            key={p.slug}
            className="border-b border-gray-100 pb-8 last:border-0"
          >
            <Link href={`/blog/${p.slug}`} className="group block">
              <h2 className="text-xl font-bold text-gray-900 group-hover:text-blue-700">
                {p.title}
              </h2>
              <p className="mt-1 text-xs text-gray-500">
                {new Date(p.published_at).toLocaleDateString("en-PK", {
                  year: "numeric",
                  month: "long",
                  day: "numeric",
                })}
                {" · "}
                {p.read_minutes} min read
              </p>
              <p className="mt-2 text-sm text-gray-700">{p.description}</p>
              <p className="mt-2 text-sm font-medium text-blue-700 group-hover:underline">
                Read →
              </p>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
