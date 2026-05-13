import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { POSTS } from "../posts";

interface Props {
  params: { slug: string };
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const post = POSTS.find((p) => p.slug === params.slug);
  if (!post) return { title: "Not found" };
  return {
    title: `${post.title} | PSX AI`,
    description: post.description,
    openGraph: { title: post.title, description: post.description },
  };
}

export function generateStaticParams() {
  return POSTS.map((p) => ({ slug: p.slug }));
}

export default function BlogPost({ params }: Props) {
  const post = POSTS.find((p) => p.slug === params.slug);
  if (!post) notFound();

  return (
    <article className="mx-auto max-w-3xl px-4 py-16 sm:px-6">
      <Link
        href="/blog"
        className="text-sm text-blue-700 hover:underline"
      >
        ← All posts
      </Link>

      <h1 className="mt-4 text-3xl font-bold tracking-tight text-gray-900 sm:text-4xl">
        {post.title}
      </h1>
      <p className="mt-3 text-xs text-gray-500">
        {new Date(post.published_at).toLocaleDateString("en-PK", {
          year: "numeric",
          month: "long",
          day: "numeric",
        })}
        {" · "}
        {post.read_minutes} min read
      </p>

      <div className="prose prose-gray mt-8 max-w-none">
        <Markdown text={post.body} />
      </div>

      <div className="mt-12 rounded-lg border border-blue-200 bg-blue-50 p-5 text-sm text-blue-900">
        <p className="font-semibold">Want to put this into practice?</p>
        <p className="mt-1">
          The free tier covers everything you need to start tracking trades
          with full tax-aware portfolio math.
        </p>
        <Link
          href="/signup"
          className="mt-2 inline-block font-medium text-blue-700 underline"
        >
          Sign up free →
        </Link>
      </div>
    </article>
  );
}

/**
 * Minimal markdown — handles `## H2`, paragraphs, and **bold**. Avoids a
 * full MDX dep for three starter posts; if blog volume grows we'll move
 * to MDX or a CMS.
 */
function Markdown({ text }: { text: string }) {
  const blocks = text.split(/\n\n+/);
  return (
    <>
      {blocks.map((block, i) => {
        const stripped = block.trimStart();
        if (stripped.startsWith("## ")) {
          return <h2 key={i}>{stripped.slice(3)}</h2>;
        }
        if (stripped.startsWith("- ")) {
          const items = stripped.split(/\n- /).map((l) => l.replace(/^- /, ""));
          return (
            <ul key={i}>
              {items.map((item, j) => (
                <li key={j}>
                  <Inline text={item} />
                </li>
              ))}
            </ul>
          );
        }
        return (
          <p key={i}>
            <Inline text={block} />
          </p>
        );
      })}
    </>
  );
}

function Inline({ text }: { text: string }) {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return (
    <>
      {parts.map((p, i) =>
        p.startsWith("**") && p.endsWith("**") ? (
          <strong key={i}>{p.slice(2, -2)}</strong>
        ) : (
          <span key={i}>{p}</span>
        ),
      )}
    </>
  );
}
