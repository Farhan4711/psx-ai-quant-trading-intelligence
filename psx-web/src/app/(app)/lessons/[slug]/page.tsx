"use client";

import { useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { fetchLesson, submitQuiz, type QuizResult } from "@/lib/api/community";
import { Button } from "@/components/ui/button";
import { ArrowLeft, CheckCircle2, XCircle } from "lucide-react";

export default function LessonPage() {
  const params = useParams<{ slug: string }>();
  const slug = params.slug;
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ["lesson", slug],
    queryFn: () => fetchLesson(slug),
    retry: false,
  });

  const [answers, setAnswers] = useState<number[]>([]);
  const [result, setResult] = useState<QuizResult | null>(null);

  const submit = useMutation({
    mutationFn: (a: number[]) => submitQuiz(slug, a),
    onSuccess: (r) => {
      setResult(r);
      queryClient.invalidateQueries({ queryKey: ["lessons"] });
      queryClient.invalidateQueries({ queryKey: ["lesson", slug] });
    },
  });

  if (isLoading || !data) {
    return <div className="h-48 animate-pulse rounded-lg bg-gray-100" />;
  }

  const allAnswered =
    data.quiz.length > 0 && answers.length === data.quiz.length && answers.every((a) => a != null);

  return (
    <div className="space-y-6">
      <Link
        href="/lessons"
        className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700"
      >
        <ArrowLeft className="h-4 w-4" />
        All lessons
      </Link>

      <article className="prose prose-sm max-w-none">
        <h1 className="text-2xl font-bold text-gray-900">{data.title}</h1>
        <p className="mt-1 text-xs uppercase tracking-wider text-gray-400">
          {data.category} · Level {data.difficulty}
        </p>
        <Markdown text={data.body_md} />
      </article>

      <section className="space-y-4 rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
        <h2 className="text-base font-semibold text-gray-900">Quick check</h2>

        {data.quiz.map((q, qi) => (
          <fieldset key={qi} className="space-y-2 border-b border-gray-100 pb-4 last:border-0 last:pb-0">
            <legend className="text-sm font-medium text-gray-900">
              {qi + 1}. {q.question}
            </legend>
            <div className="space-y-1.5">
              {q.options.map((opt, oi) => {
                const selected = answers[qi] === oi;
                const correctIdx = result?.correct_indices?.[qi];
                const isCorrect = result && correctIdx === oi;
                const isWrongPick = result && selected && correctIdx !== oi;

                return (
                  <label
                    key={oi}
                    className={
                      "flex cursor-pointer items-center gap-2 rounded-md border px-3 py-2 text-sm transition " +
                      (isCorrect
                        ? "border-emerald-500 bg-emerald-50"
                        : isWrongPick
                        ? "border-red-500 bg-red-50"
                        : selected
                        ? "border-blue-500 bg-blue-50"
                        : "border-gray-200 hover:bg-gray-50")
                    }
                  >
                    <input
                      type="radio"
                      name={`q${qi}`}
                      value={oi}
                      checked={selected}
                      onChange={() => {
                        const next = [...answers];
                        next[qi] = oi;
                        setAnswers(next);
                      }}
                      disabled={!!result}
                      className="h-4 w-4"
                    />
                    <span className="flex-1">{opt.text}</span>
                    {isCorrect && <CheckCircle2 className="h-4 w-4 text-emerald-600" />}
                    {isWrongPick && <XCircle className="h-4 w-4 text-red-600" />}
                  </label>
                );
              })}
            </div>
          </fieldset>
        ))}

        {result ? (
          <div
            className={
              "rounded-md border p-3 text-sm " +
              (result.completed
                ? "border-emerald-300 bg-emerald-50 text-emerald-900"
                : "border-amber-300 bg-amber-50 text-amber-900")
            }
          >
            <p className="font-semibold">
              You scored {result.score}% — {result.completed ? "passed!" : "below 70% needed to pass."}
            </p>
            {!result.completed && (
              <p className="mt-1">
                Review the lesson and try again. Highest score is kept.
              </p>
            )}
            <div className="mt-3 flex gap-2">
              {!result.completed && (
                <Button
                  variant="outline"
                  onClick={() => {
                    setResult(null);
                    setAnswers([]);
                  }}
                >
                  Retry
                </Button>
              )}
              <Link href="/lessons">
                <Button>{result.completed ? "Next lesson →" : "Back to skill tree"}</Button>
              </Link>
            </div>
          </div>
        ) : (
          <Button
            disabled={!allAnswered || submit.isPending}
            onClick={() => submit.mutate(answers)}
          >
            {submit.isPending ? "Grading…" : "Submit quiz"}
          </Button>
        )}
      </section>
    </div>
  );
}

/** Tiny Markdown — only **bold**, headings (#), and paragraph breaks. */
function Markdown({ text }: { text: string }) {
  const blocks = text.split(/\n\n+/);
  return (
    <>
      {blocks.map((block, i) => {
        if (block.startsWith("### ")) {
          return <h3 key={i}>{block.slice(4)}</h3>;
        }
        const parts = block.split(/(\*\*[^*]+\*\*)/g);
        return (
          <p key={i}>
            {parts.map((p, j) =>
              p.startsWith("**") && p.endsWith("**") ? (
                <strong key={j}>{p.slice(2, -2)}</strong>
              ) : (
                <span key={j}>{p}</span>
              ),
            )}
          </p>
        );
      })}
    </>
  );
}
