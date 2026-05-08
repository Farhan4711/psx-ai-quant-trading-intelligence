"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  fetchRiskProfile,
  fetchRiskQuestionnaire,
  submitRiskAnswers,
  type RiskProfileResult,
} from "@/lib/api/planning";
import { Button } from "@/components/ui/button";
import { CheckCircle2, RotateCcw } from "lucide-react";

const AXIS_LABELS: Record<string, string> = {
  risk_tolerance: "Risk Tolerance",
  time_horizon: "Time Horizon",
  knowledge: "Knowledge",
};

export default function RiskProfilePage() {
  const queryClient = useQueryClient();
  const [retaking, setRetaking] = useState(false);

  const { data: profile, isLoading: profileLoading } = useQuery({
    queryKey: ["risk-profile"],
    queryFn: fetchRiskProfile,
  });

  const { data: questionnaire } = useQuery({
    queryKey: ["risk-questionnaire"],
    queryFn: fetchRiskQuestionnaire,
    enabled: retaking || !profile,
    staleTime: 86_400_000,
  });

  const [answers, setAnswers] = useState<Record<string, string>>({});

  const submit = useMutation({
    mutationFn: submitRiskAnswers,
    onSuccess: (data) => {
      queryClient.setQueryData(["risk-profile"], data);
      setAnswers({});
      setRetaking(false);
    },
  });

  if (profileLoading) {
    return <div className="h-48 animate-pulse rounded-lg bg-gray-100" />;
  }

  // Show existing profile if user has one and isn't retaking
  if (profile && !retaking) {
    return <ProfileSummary profile={profile} onRetake={() => setRetaking(true)} />;
  }

  if (!questionnaire) {
    return <div className="h-48 animate-pulse rounded-lg bg-gray-100" />;
  }

  const allAnswered = questionnaire.questions.every((q) => answers[q.id]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Risk Profile</h1>
        <p className="mt-1 text-sm text-gray-500">
          12 questions, ~3 minutes. The result drives recommended allocation
          per goal — no judgement, just match the strategy to your reality.
        </p>
      </div>

      <div className="space-y-4">
        {questionnaire.questions.map((q, i) => (
          <fieldset
            key={q.id}
            className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm"
          >
            <legend className="mb-2 px-1 text-xs font-semibold uppercase tracking-wider text-gray-500">
              {i + 1} of {questionnaire.questions.length} · {AXIS_LABELS[q.axis]}
            </legend>
            <p className="mb-3 text-sm font-medium text-gray-900">{q.prompt}</p>
            <div className="space-y-1.5">
              {q.options.map((opt) => {
                const selected = answers[q.id] === opt.value;
                return (
                  <label
                    key={opt.value}
                    className={
                      "flex cursor-pointer items-center gap-3 rounded-md border px-3 py-2 text-sm transition " +
                      (selected
                        ? "border-blue-600 bg-blue-50"
                        : "border-gray-200 bg-white hover:bg-gray-50")
                    }
                  >
                    <input
                      type="radio"
                      name={q.id}
                      value={opt.value}
                      checked={selected}
                      onChange={() =>
                        setAnswers((a) => ({ ...a, [q.id]: opt.value }))
                      }
                      className="h-4 w-4 text-blue-600"
                    />
                    <span className={selected ? "text-blue-900" : "text-gray-700"}>
                      {opt.label}
                    </span>
                  </label>
                );
              })}
            </div>
          </fieldset>
        ))}
      </div>

      {submit.isError && (
        <p className="text-sm text-red-600">{(submit.error as Error).message}</p>
      )}

      <div className="flex justify-end gap-2">
        {retaking && (
          <Button variant="outline" onClick={() => setRetaking(false)}>
            Cancel
          </Button>
        )}
        <Button
          disabled={!allAnswered || submit.isPending}
          onClick={() => submit.mutate(answers)}
        >
          {submit.isPending ? "Calculating…" : "Submit"}
        </Button>
      </div>
    </div>
  );
}

function ProfileSummary({
  profile,
  onRetake,
}: {
  profile: RiskProfileResult;
  onRetake: () => void;
}) {
  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Risk Profile</h1>
        <p className="mt-1 text-sm text-gray-500">
          Completed{" "}
          {profile.completed_at
            ? new Date(profile.completed_at).toLocaleDateString()
            : "—"}
          . Retake every 6 months — your appetite changes with life events.
        </p>
      </div>

      <div className="rounded-lg border border-blue-200 bg-blue-50 p-5">
        <div className="flex items-center gap-2">
          <CheckCircle2 className="h-5 w-5 text-blue-600" />
          <h2 className="text-xl font-bold text-blue-900">{profile.label}</h2>
        </div>
        <p className="mt-2 text-sm text-blue-800">{profile.description}</p>
      </div>

      <div className="grid grid-cols-3 gap-3">
        <ScoreBar label="Risk Tolerance" score={profile.scores.risk_tolerance} />
        <ScoreBar label="Time Horizon" score={profile.scores.time_horizon} />
        <ScoreBar label="Knowledge" score={profile.scores.knowledge} />
      </div>

      <Button variant="outline" onClick={onRetake} className="gap-2">
        <RotateCcw className="h-4 w-4" />
        Retake quiz
      </Button>
    </div>
  );
}

function ScoreBar({ label, score }: { label: string; score: number }) {
  const pct = (score / 5) * 100;
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-3 shadow-sm">
      <p className="text-xs font-medium uppercase tracking-wider text-gray-500">
        {label}
      </p>
      <p className="mt-1 text-lg font-semibold text-gray-900">{score} / 5</p>
      <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-gray-100">
        <div className="h-full bg-blue-500" style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}
