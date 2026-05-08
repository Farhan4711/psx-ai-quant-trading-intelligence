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

// ── Benchmark ──────────────────────────────────────────────────────────

export interface BenchmarkPanel {
  available: boolean;
  bucket_label: string | null;
  sample_count: number;
  user_ytd_return_pct: number | null;
  median_ytd_return_pct: number | null;
  percentile_rank: number | null;
  user_top_sector: string | null;
  user_top_sector_pct: number | null;
  peer_top_sector: string | null;
  peer_top_sector_pct: number | null;
  peer_top_holdings: Array<Record<string, unknown>>;
  message: string | null;
}

export const fetchBenchmarkPanel = () =>
  apiFetch<BenchmarkPanel>("/api/v1/benchmark/me");

// ── Strategies ─────────────────────────────────────────────────────────

export interface StrategyRule {
  entry: Record<string, unknown>;
  exit?: Record<string, unknown>;
}

export interface UserStrategy {
  id: string;
  user_id: string;
  name: string;
  description: string | null;
  rules: StrategyRule;
  is_public: boolean;
  forked_from: string | null;
  created_at: string;
  updated_at: string;
}

export const fetchMyStrategies = () =>
  apiFetch<UserStrategy[]>("/api/v1/strategies");
export const fetchPublicStrategies = () =>
  apiFetch<UserStrategy[]>("/api/v1/strategies/public");
export const createStrategy = (body: {
  name: string;
  description?: string;
  rules: StrategyRule;
  is_public?: boolean;
}) =>
  apiFetch<UserStrategy>("/api/v1/strategies", {
    method: "POST",
    body: JSON.stringify(body),
  });
export const deleteStrategy = (id: string) =>
  apiFetch<void>(`/api/v1/strategies/${id}`, { method: "DELETE" });
export const forkStrategy = (id: string) =>
  apiFetch<UserStrategy>(`/api/v1/strategies/${id}/fork`, { method: "POST" });

// ── Notifications ──────────────────────────────────────────────────────

export interface NotificationItem {
  id: string;
  kind: string;
  title: string;
  body: string;
  link_path: string | null;
  read_at: string | null;
  created_at: string;
}

export const fetchNotifications = (limit = 50) =>
  apiFetch<NotificationItem[]>(`/api/v1/notifications?limit=${limit}`);
export const fetchUnreadCount = () =>
  apiFetch<{ unread: number }>("/api/v1/notifications/unread");
export const markNotificationRead = (id: string) =>
  apiFetch<void>(`/api/v1/notifications/${id}/read`, { method: "POST" });
export const markAllNotificationsRead = () =>
  apiFetch<{ marked: number }>("/api/v1/notifications/mark-all-read", {
    method: "POST",
  });

// ── Purification ───────────────────────────────────────────────────────

export interface PurificationLine {
  symbol: string;
  dividends_pkr: string;
  purification_pct: string;
  purification_amount_pkr: string;
  marked_donated: boolean;
}

export interface PurificationReport {
  fiscal_year: number;
  purification_pct: string;
  total_dividends_pkr: string;
  total_purification_pkr: string;
  lines: PurificationLine[];
}

export const fetchPurificationReport = (fiscalYear?: number) => {
  const qs = fiscalYear ? `?fiscal_year=${fiscalYear}` : "";
  return apiFetch<PurificationReport>(`/api/v1/purification/report${qs}`);
};

export const markPurificationDonated = (
  fiscalYear: number,
  symbol: string,
  donated: boolean,
) =>
  apiFetch<void>(
    `/api/v1/purification/${fiscalYear}/${symbol}/mark-donated?donated=${donated}`,
    { method: "POST" },
  );

// ── Lessons ────────────────────────────────────────────────────────────

export interface LessonSummary {
  id: number;
  slug: string;
  title: string;
  category: string;
  difficulty: number;
  started: boolean;
  completed: boolean;
  quiz_score: number | null;
}

export interface LessonDetail {
  id: number;
  slug: string;
  title: string;
  category: string;
  difficulty: number;
  body_md: string;
  quiz: Array<{ question: string; options: Array<{ text: string }> }>;
  progress: {
    started_at: string | null;
    completed_at: string | null;
    quiz_score: number | null;
  } | null;
}

export interface QuizResult {
  score: number;
  completed: boolean;
  correct_indices: number[];
}

export const fetchLessons = () => apiFetch<LessonSummary[]>("/api/v1/lessons");
export const fetchLesson = (slug: string) =>
  apiFetch<LessonDetail>(`/api/v1/lessons/${slug}`);
export const submitQuiz = (slug: string, answers: number[]) =>
  apiFetch<QuizResult>(`/api/v1/lessons/${slug}/quiz`, {
    method: "POST",
    body: JSON.stringify({ answers }),
  });
