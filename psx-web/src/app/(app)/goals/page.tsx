"use client";

import { useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createGoal,
  deleteGoal,
  fetchGoals,
  fetchRiskProfile,
  type AllocationResponse,
  type Goal,
  type GoalAnalysisResponse,
  type GoalRating,
  type GoalType,
} from "@/lib/api/planning";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { formatCurrency } from "@/lib/utils/format";
import { Trash2 } from "lucide-react";

const GOAL_TYPES: { value: GoalType; label: string; emoji: string }[] = [
  { value: "retirement", label: "Retirement", emoji: "🌅" },
  { value: "hajj", label: "Hajj", emoji: "🕋" },
  { value: "education", label: "Education", emoji: "🎓" },
  { value: "home", label: "Home", emoji: "🏡" },
  { value: "marriage", label: "Marriage", emoji: "💍" },
  { value: "emergency_fund", label: "Emergency Fund", emoji: "🚨" },
  { value: "custom", label: "Custom", emoji: "🎯" },
];

const RATING_COLOR: Record<GoalRating, string> = {
  feasible: "bg-green-100 text-green-800",
  stretch: "bg-blue-100 text-blue-800",
  aggressive: "bg-amber-100 text-amber-800",
  unrealistic: "bg-red-100 text-red-800",
  already_funded: "bg-emerald-100 text-emerald-800",
};

export default function GoalsPage() {
  const queryClient = useQueryClient();

  const { data: profile } = useQuery({
    queryKey: ["risk-profile"],
    queryFn: fetchRiskProfile,
  });

  const { data: goals, isLoading } = useQuery({
    queryKey: ["goals"],
    queryFn: fetchGoals,
  });

  const remove = useMutation({
    mutationFn: (id: string) => deleteGoal(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["goals"] }),
  });

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Goals</h1>
          <p className="mt-1 text-sm text-gray-500">
            Tell us the target and the deadline — we&apos;ll do the time-value
            math and tell you if it&apos;s realistic.
          </p>
        </div>
        <NewGoalModal trigger={<Button>+ Add goal</Button>} />
      </div>

      {!profile && (
        <div className="rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
          ⚠ You haven&apos;t taken the{" "}
          <Link href="/app/risk-profile" className="font-semibold underline">
            risk profile
          </Link>{" "}
          yet. Allocations will fall back to a balanced default until you do.
        </div>
      )}

      {isLoading ? (
        <div className="h-48 animate-pulse rounded-lg bg-gray-100" />
      ) : !goals || goals.length === 0 ? (
        <EmptyState />
      ) : (
        <div className="space-y-3">
          {goals.map((g) => (
            <GoalCard
              key={g.id}
              goal={g}
              onDelete={() => remove.mutate(g.id)}
              deleting={remove.isPending}
            />
          ))}
        </div>
      )}
    </div>
  );
}

// ── GoalCard ───────────────────────────────────────────────────────────

function GoalCard({
  goal,
  onDelete,
  deleting,
}: {
  goal: Goal;
  onDelete: () => void;
  deleting: boolean;
}) {
  const target = parseFloat(goal.target_amount_pkr);
  const current = parseFloat(goal.current_amount_pkr);
  const progress = target > 0 ? Math.min(100, (current / target) * 100) : 0;
  const a = goal.analysis;
  const typeMeta = GOAL_TYPES.find((t) => t.value === goal.goal_type);

  return (
    <article className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <span className="text-2xl" aria-hidden>
            {typeMeta?.emoji ?? "🎯"}
          </span>
          <div>
            <h2 className="text-base font-semibold text-gray-900">{goal.name}</h2>
            <p className="mt-0.5 text-xs text-gray-500">
              By {new Date(goal.target_date).toLocaleDateString()} ·{" "}
              {a.years_remaining.toFixed(1)} yr{a.years_remaining !== 1 ? "s" : ""}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span
            className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${RATING_COLOR[a.rating]}`}
          >
            {a.rating.replace("_", " ")}
          </span>
          <button
            onClick={onDelete}
            disabled={deleting}
            aria-label={`Delete ${goal.name}`}
            className="rounded p-1 text-gray-400 hover:bg-red-50 hover:text-red-500 disabled:opacity-50"
          >
            <Trash2 className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Progress */}
      <div className="mt-3">
        <div className="flex items-center justify-between text-xs text-gray-500">
          <span>
            {formatCurrency(current)} of {formatCurrency(target)}
          </span>
          <span className="tabular-nums">{progress.toFixed(1)}%</span>
        </div>
        <div className="mt-1 h-2 overflow-hidden rounded-full bg-gray-100">
          <div
            className="h-full bg-blue-500 transition-all"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      {/* TVM analysis */}
      <p className="mt-3 text-sm text-gray-700">{a.summary}</p>

      {/* Suggestions */}
      {(a.suggested_monthly_contribution_pkr || a.suggested_extension_months) && (
        <ul className="mt-2 list-disc pl-5 text-xs text-gray-600">
          {a.suggested_monthly_contribution_pkr && (
            <li>
              Try a monthly contribution of{" "}
              <strong>
                {formatCurrency(parseFloat(a.suggested_monthly_contribution_pkr))}
              </strong>
              .
            </li>
          )}
          {a.suggested_extension_months !== null &&
            a.suggested_extension_months > 0 && (
              <li>
                Or extend the deadline by{" "}
                <strong>{a.suggested_extension_months} months</strong> to drop
                the required CAGR to a feasible level.
              </li>
            )}
        </ul>
      )}

      {/* Allocation */}
      <AllocationStrip allocation={a.allocation} />
    </article>
  );
}

function AllocationStrip({ allocation }: { allocation: AllocationResponse }) {
  return (
    <div className="mt-4 rounded-md border border-gray-100 bg-gray-50 p-3">
      <p className="text-xs font-semibold uppercase tracking-wider text-gray-500">
        Recommended allocation
      </p>
      <div className="mt-2 flex h-3 overflow-hidden rounded">
        {allocation.equity_pct > 0 && (
          <div
            className="bg-blue-500"
            style={{ width: `${allocation.equity_pct}%` }}
            title={`Equity ${allocation.equity_pct}%`}
          />
        )}
        {allocation.tbills_pct > 0 && (
          <div
            className="bg-emerald-500"
            style={{ width: `${allocation.tbills_pct}%` }}
            title={`T-Bills/Sukuk ${allocation.tbills_pct}%`}
          />
        )}
        {allocation.cash_pct > 0 && (
          <div
            className="bg-gray-400"
            style={{ width: `${allocation.cash_pct}%` }}
            title={`Cash ${allocation.cash_pct}%`}
          />
        )}
      </div>
      <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-gray-600">
        <span>
          <span className="mr-1 inline-block h-2 w-2 rounded-sm bg-blue-500" />
          Equity {allocation.equity_pct}%
        </span>
        <span>
          <span className="mr-1 inline-block h-2 w-2 rounded-sm bg-emerald-500" />
          T-Bills/Sukuk {allocation.tbills_pct}%
        </span>
        <span>
          <span className="mr-1 inline-block h-2 w-2 rounded-sm bg-gray-400" />
          Cash {allocation.cash_pct}%
        </span>
      </div>
      <p className="mt-2 text-xs text-gray-500">{allocation.rationale}</p>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-lg border border-dashed border-gray-300 bg-white py-16 text-center">
      <div className="text-3xl">🎯</div>
      <h2 className="text-lg font-semibold text-gray-900">No goals yet</h2>
      <p className="max-w-sm text-sm text-gray-500">
        Add a Hajj fund, retirement target, or down-payment goal — we&apos;ll
        compute the required CAGR and suggest a realistic allocation.
      </p>
      <NewGoalModal trigger={<Button className="mt-2">Add your first goal</Button>} />
    </div>
  );
}

// ── New goal modal ─────────────────────────────────────────────────────

function NewGoalModal({ trigger }: { trigger: React.ReactNode }) {
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [type, setType] = useState<GoalType>("retirement");
  const [target, setTarget] = useState("");
  const [date, setDate] = useState("");
  const [current, setCurrent] = useState("0");
  const [monthly, setMonthly] = useState("0");

  const create = useMutation({
    mutationFn: () =>
      createGoal({
        name,
        goal_type: type,
        target_amount_pkr: target,
        target_date: date,
        current_amount_pkr: current,
        monthly_contribution_pkr: monthly,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["goals"] });
      setOpen(false);
      setName("");
      setTarget("");
      setDate("");
      setCurrent("0");
      setMonthly("0");
    },
  });

  const valid = name.trim() && parseFloat(target) > 0 && date;

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>{trigger}</DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Add goal</DialogTitle>
          <DialogDescription>
            We&apos;ll calculate required CAGR and recommended allocation.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-3">
          <div className="space-y-1.5">
            <Label htmlFor="g-name">Name</Label>
            <Input
              id="g-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Hajj 2030"
            />
          </div>

          <div className="space-y-1.5">
            <Label>Type</Label>
            <div className="flex flex-wrap gap-1.5">
              {GOAL_TYPES.map((t) => (
                <button
                  key={t.value}
                  type="button"
                  onClick={() => setType(t.value)}
                  className={
                    "rounded-md border px-2.5 py-1 text-xs transition " +
                    (type === t.value
                      ? "border-blue-600 bg-blue-50 text-blue-700"
                      : "border-gray-200 bg-white text-gray-700 hover:bg-gray-50")
                  }
                >
                  {t.emoji} {t.label}
                </button>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label htmlFor="g-target">Target (PKR)</Label>
              <Input
                id="g-target"
                type="number"
                min="0"
                value={target}
                onChange={(e) => setTarget(e.target.value)}
                placeholder="2000000"
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="g-date">By</Label>
              <Input
                id="g-date"
                type="date"
                value={date}
                onChange={(e) => setDate(e.target.value)}
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label htmlFor="g-current">Current savings (PKR)</Label>
              <Input
                id="g-current"
                type="number"
                min="0"
                value={current}
                onChange={(e) => setCurrent(e.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="g-monthly">Monthly contribution</Label>
              <Input
                id="g-monthly"
                type="number"
                min="0"
                value={monthly}
                onChange={(e) => setMonthly(e.target.value)}
              />
            </div>
          </div>

          {create.isError && (
            <p className="text-sm text-red-600">
              {(create.error as Error).message}
            </p>
          )}

          <div className="flex justify-end gap-2 pt-2">
            <Button
              disabled={!valid || create.isPending}
              onClick={() => create.mutate()}
            >
              {create.isPending ? "Creating…" : "Create"}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

// Re-export so the page can fetch the profile in one place — simpler than
// importing from two locations.
function fetchRiskProfileLocal() {
  return fetchRiskProfile();
}
void fetchRiskProfileLocal;
