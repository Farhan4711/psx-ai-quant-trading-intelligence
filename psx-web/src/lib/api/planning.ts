const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    credentials: "include",
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });
  if (!res.ok) {
    const err = (await res.json().catch(() => ({ detail: res.statusText }))) as {
      detail?: string;
    };
    throw new Error(err.detail ?? "Request failed");
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

// ── Risk ───────────────────────────────────────────────────────────────

export interface RiskQuestionOption {
  value: string;
  label: string;
}

export interface RiskQuestion {
  id: string;
  axis: "risk_tolerance" | "time_horizon" | "knowledge";
  prompt: string;
  options: RiskQuestionOption[];
}

export interface RiskProfileResult {
  archetype: string;
  label: string;
  description: string;
  scores: {
    risk_tolerance: number;
    time_horizon: number;
    knowledge: number;
  };
  completed_at: string | null;
}

export const fetchRiskQuestionnaire = () =>
  apiFetch<{ questions: RiskQuestion[] }>("/api/v1/risk/questionnaire");

export const fetchRiskProfile = () =>
  apiFetch<RiskProfileResult | null>("/api/v1/risk/profile");

export const submitRiskAnswers = (answers: Record<string, string>) =>
  apiFetch<RiskProfileResult>("/api/v1/risk/submit", {
    method: "POST",
    body: JSON.stringify({ answers }),
  });

// ── Goals ──────────────────────────────────────────────────────────────

export type GoalType =
  | "retirement"
  | "hajj"
  | "education"
  | "home"
  | "marriage"
  | "emergency_fund"
  | "custom";

export type GoalRating =
  | "feasible"
  | "stretch"
  | "aggressive"
  | "unrealistic"
  | "already_funded";

export interface AllocationResponse {
  archetype: string;
  horizon_bucket: string;
  months: number;
  equity_pct: number;
  tbills_pct: number;
  cash_pct: number;
  rationale: string;
}

export interface GoalAnalysisResponse {
  months_remaining: number;
  years_remaining: number;
  required_cagr: string | null;
  rating: GoalRating;
  summary: string;
  suggested_monthly_contribution_pkr: string | null;
  suggested_extension_months: number | null;
  allocation: AllocationResponse;
}

export interface Goal {
  id: string;
  user_id: string;
  name: string;
  goal_type: GoalType;
  target_amount_pkr: string;
  target_date: string;
  current_amount_pkr: string;
  monthly_contribution_pkr: string;
  linked_portfolio_id: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
  analysis: GoalAnalysisResponse;
}

export interface GoalCreate {
  name: string;
  goal_type: GoalType;
  target_amount_pkr: string;
  target_date: string;
  current_amount_pkr?: string;
  monthly_contribution_pkr?: string;
  linked_portfolio_id?: string | null;
  notes?: string | null;
}

export const fetchGoals = () => apiFetch<Goal[]>("/api/v1/goals");
export const createGoal = (body: GoalCreate) =>
  apiFetch<Goal>("/api/v1/goals", { method: "POST", body: JSON.stringify(body) });
export const deleteGoal = (id: string) =>
  apiFetch<void>(`/api/v1/goals/${id}`, { method: "DELETE" });
