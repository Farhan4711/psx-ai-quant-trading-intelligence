"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { fetchLessons, type LessonSummary } from "@/lib/api/community";
import { Award, BookOpen, CheckCircle2, Lock } from "lucide-react";

const CATEGORY_LABEL: Record<string, string> = {
  basics: "Basics",
  analysis: "Analysis",
  tax: "Tax",
  shariah: "Shariah",
  discipline: "Discipline",
};

const CATEGORY_TONE: Record<string, string> = {
  basics: "border-blue-200 bg-blue-50",
  analysis: "border-violet-200 bg-violet-50",
  tax: "border-amber-200 bg-amber-50",
  shariah: "border-emerald-200 bg-emerald-50",
  discipline: "border-rose-200 bg-rose-50",
};

export default function LessonsPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["lessons"],
    queryFn: fetchLessons,
  });

  if (isLoading || !data) {
    return <div className="h-48 animate-pulse rounded-lg bg-gray-100" />;
  }

  const completed = data.filter((l) => l.completed).length;
  const total = data.length;
  const grouped = data.reduce<Record<string, LessonSummary[]>>((acc, l) => {
    (acc[l.category] = acc[l.category] ?? []).push(l);
    return acc;
  }, {});

  if (total === 0) {
    return <SeedingPrompt />;
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Skill Tree</h1>
        <p className="mt-1 text-sm text-gray-500">
          Short, PSX-specific lessons. Each ends in a 3-question quiz; pass at
          70%+ to mark complete.
        </p>
      </div>

      {/* Progress strip */}
      <div className="flex items-center gap-3 rounded-lg border border-gray-200 bg-white p-3 shadow-sm">
        <Award className="h-6 w-6 text-amber-500" />
        <div className="flex-1">
          <p className="text-sm font-medium text-gray-900">
            {completed} of {total} lessons completed
          </p>
          <div className="mt-1 h-2 overflow-hidden rounded-full bg-gray-100">
            <div
              className="h-full bg-amber-500 transition-all"
              style={{ width: `${(completed / total) * 100}%` }}
            />
          </div>
        </div>
      </div>

      {/* Lessons grouped by category */}
      <div className="space-y-5">
        {Object.entries(grouped).map(([cat, lessons]) => (
          <section key={cat}>
            <h2 className="mb-2 text-sm font-semibold uppercase tracking-wider text-gray-500">
              {CATEGORY_LABEL[cat] ?? cat}
            </h2>
            <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
              {lessons.map((l) => (
                <LessonTile key={l.id} lesson={l} tone={CATEGORY_TONE[cat] ?? ""} />
              ))}
            </div>
          </section>
        ))}
      </div>
    </div>
  );
}

function LessonTile({ lesson, tone }: { lesson: LessonSummary; tone: string }) {
  return (
    <Link
      href={`/app/lessons/${lesson.slug}`}
      className={`group flex flex-col gap-2 rounded-lg border p-3 shadow-sm transition hover:shadow-md ${tone}`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-1.5">
          {lesson.completed ? (
            <CheckCircle2 className="h-4 w-4 text-emerald-600" />
          ) : lesson.started ? (
            <BookOpen className="h-4 w-4 text-blue-600" />
          ) : (
            <Lock className="h-4 w-4 text-gray-400" />
          )}
          <span className="text-[10px] font-semibold uppercase tracking-wider text-gray-500">
            Level {lesson.difficulty}
          </span>
        </div>
        {lesson.quiz_score != null && (
          <span className="rounded-full bg-white px-1.5 py-0.5 text-[10px] font-semibold text-gray-700">
            {lesson.quiz_score}%
          </span>
        )}
      </div>
      <h3 className="text-sm font-semibold text-gray-900 group-hover:underline">
        {lesson.title}
      </h3>
    </Link>
  );
}

function SeedingPrompt() {
  return (
    <div className="flex flex-col items-center gap-3 rounded-lg border border-dashed border-gray-300 bg-white py-12 text-center">
      <BookOpen className="h-8 w-8 text-gray-400" />
      <h2 className="text-lg font-semibold text-gray-900">No lessons yet</h2>
      <p className="max-w-sm text-sm text-gray-500">
        The lessons table is empty. An admin should hit{" "}
        <code className="rounded bg-gray-100 px-1 py-0.5">POST /api/v1/lessons/seed</code>{" "}
        to load the starter curriculum.
      </p>
    </div>
  );
}
