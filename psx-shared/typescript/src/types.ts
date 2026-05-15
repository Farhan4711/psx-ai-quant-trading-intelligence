/**
 * Canonical shared types — the contract between psx-web (TS) and
 * psx-api (Python).
 *
 * **Do not import anything from psx-web here.** This module must be
 * usable from any TS environment (Node, browser, edge, Deno) so we
 * keep zero runtime dependencies.
 *
 * Naming convention
 * -----------------
 * Field names match the Python Pydantic schemas verbatim
 * (`full_name`, `price_pkr_monthly`) so a frontend can `JSON.parse`
 * a backend response without any field renaming. This is a deliberate
 * trade-off vs JS-idiomatic camelCase — drift between FE/BE is more
 * expensive than the cosmetic mismatch.
 *
 * Refreshing from the live API
 * ----------------------------
 * Once an API is reachable, run `pnpm --filter @psx/shared gen` to
 * regenerate `generated.ts` from `/openapi.json`. The hand-written
 * types here remain — they're the curated, documented surface that
 * the rest of the app imports. `generated.ts` is the verbose source
 * of truth for less-used DTOs.
 */

// ── Primitives / discriminators ─────────────────────────────────

export type UUID = string;
export type ISODate = string;      // "YYYY-MM-DD"
export type ISODateTime = string;  // ISO 8601 with offset

/** Decimals are serialised as strings to preserve precision over JSON. */
export type DecimalString = string;

// ── Auth / user ─────────────────────────────────────────────────

export interface CurrentUser {
  id: UUID;
  email: string;
  full_name: string | null;
  phone: string | null;
  date_of_birth: ISODate | null;
  email_verified: boolean;
  is_filer: boolean;
  shariah_mode: boolean;
  share_anonymously: boolean;
  totp_enabled: boolean;
  created_at: ISODateTime;
}

export interface UserSettingsUpdate {
  full_name?: string;
  phone?: string;
  date_of_birth?: ISODate;
  is_filer?: boolean;
  shariah_mode?: boolean;
  share_anonymously?: boolean;
}

// ── Securities ──────────────────────────────────────────────────

export interface Security {
  symbol: string;
  company_name: string;
  sector: string | null;
  is_kse100: boolean;
  is_kse30: boolean;
  is_kmi_compliant: boolean;
  market_cap_pkr: DecimalString | null;
  is_active: boolean;
}

export interface OhlcvBar {
  symbol: string;
  date: ISODate;
  open: DecimalString;
  high: DecimalString;
  low: DecimalString;
  close: DecimalString;
  volume: number;
  adjusted_close: DecimalString | null;
}

// ── Portfolio ───────────────────────────────────────────────────

export type TransactionType = "buy" | "sell" | "dividend" | "bonus" | "rights";

export interface Transaction {
  id: UUID;
  portfolio_id: UUID;
  symbol: string;
  transaction_type: TransactionType;
  trade_date: ISODate;
  quantity: number;
  price_pkr: DecimalString;
  fees_pkr: DecimalString;
  notes: string | null;
  created_at: ISODateTime;
}

export interface HoldingDashboardRow {
  symbol: string;
  company_name: string;
  sector: string | null;
  quantity: number;
  avg_cost_pkr: DecimalString;
  current_price_pkr: DecimalString | null;
  invested_pkr: DecimalString;
  market_value_pkr: DecimalString | null;
  unrealized_gross_pkr: DecimalString | null;
  unrealized_after_tax_pkr: DecimalString | null;
  day_change_pct: DecimalString | null;
  is_kmi_compliant: boolean;
}

export interface PortfolioSummary {
  portfolio_id: UUID;
  name: string;
  total_invested_pkr: DecimalString;
  current_value_pkr: DecimalString;
  unrealized_gross_pkr: DecimalString;
  unrealized_after_tax_pkr: DecimalString;
  realized_ytd_pkr: DecimalString;
  dividends_ytd_pkr: DecimalString;
  fees_ytd_pkr: DecimalString;
  holdings: HoldingDashboardRow[];
  sector_allocation: SectorAllocationRow[];
}

export interface SectorAllocationRow {
  sector: string;
  weight_pct: DecimalString;
  market_value_pkr: DecimalString;
}

// ── Predictions ─────────────────────────────────────────────────

export interface PredictionResponse {
  symbol: string;
  model_version: string;
  as_of_date: ISODate;
  prob_up: DecimalString;
  confidence: "low" | "medium" | "high";
  key_features: Array<{ feature: string; direction: "positive" | "negative" | "neutral" }>;
  live_accuracy_pct: DecimalString | null;
  predictions_disabled: boolean;
  disabled_reason: string | null;
}

// ── Goals ───────────────────────────────────────────────────────

export type GoalType =
  | "retirement"
  | "education"
  | "hajj"
  | "house"
  | "emergency_fund"
  | "wealth"
  | "custom";

export interface Goal {
  id: UUID;
  user_id: UUID;
  name: string;
  goal_type: GoalType;
  target_amount_pkr: DecimalString;
  current_amount_pkr: DecimalString;
  monthly_contribution_pkr: DecimalString;
  target_date: ISODate;
  created_at: ISODateTime;
}

export type GoalRating = "feasible" | "stretch" | "aggressive" | "unrealistic";

export interface GoalAnalysis {
  required_cagr_pct: DecimalString;
  rating: GoalRating;
  rationale: string;
  suggested_pmt_pkr: DecimalString | null;
  suggested_extension_months: number | null;
}

export interface GoalWithAnalysis extends Goal {
  analysis: GoalAnalysis;
}

// ── Billing / subscription ──────────────────────────────────────

export interface SubscriptionPlan {
  id: number;
  slug: string;
  name: string;
  tagline: string;
  price_pkr_monthly: DecimalString;
  price_pkr_annual: DecimalString | null;
  features: string[];
  display_order: number;
}

export type SubscriptionStatus =
  | "active"
  | "past_due"
  | "canceled"
  | "trialing"
  | "incomplete"
  | "implicit_free";

export interface CurrentSubscription {
  plan: SubscriptionPlan;
  status: SubscriptionStatus;
  period_start: ISODate | null;
  period_end: ISODate | null;
  cancel_at_period_end: boolean;
}

export type PaymentProvider =
  | "jazzcash"
  | "easypaisa"
  | "meezan"
  | "allied_payfast"
  | "safepay"
  | "nayapay"
  | "manual";

export type BillingCycle = "monthly" | "annual";

export interface PaymentMethodOption {
  slug: PaymentProvider;
  name: string;
  category: "wallet" | "bank" | "card" | "manual";
  description: string;
  logo_hint: string;
}

export interface CheckoutRequest {
  plan_slug: string;
  provider: PaymentProvider;
  billing_cycle: BillingCycle;
}

export interface CheckoutResponse {
  intent_id: UUID;
  provider: PaymentProvider;
  checkout_url: string;
  is_sandbox: boolean;
  instructions: string | null;
  request_payload: Record<string, string>;
  amount_pkr: DecimalString;
  expires_at: ISODateTime | null;
}

export type PaymentIntentState =
  | "pending"
  | "redirected"
  | "paid"
  | "failed"
  | "canceled"
  | "expired";

export interface PaymentIntentStatus {
  id: UUID;
  provider: PaymentProvider;
  status: PaymentIntentState;
  amount_pkr: DecimalString;
  billing_cycle: BillingCycle;
  plan_slug: string;
  failure_reason: string | null;
  created_at: ISODateTime;
  returned_at: ISODateTime | null;
}

// ── News + sentiment ────────────────────────────────────────────

export interface NewsArticleListItem {
  id: UUID;
  source: string;
  url: string;
  headline: string;
  published_at: ISODateTime;
  polarity: DecimalString | null;
}

export interface NewsPulse {
  symbol: string;
  score: number;          // -100..+100
  article_count: number;
  top_articles: NewsArticleListItem[];
}

// ── Alerts ──────────────────────────────────────────────────────

export type AlertSeverity = "low" | "medium" | "high";

export interface SuspiciousDay {
  symbol: string;
  alert_date: ISODate;
  alert_type: string;
  severity: AlertSeverity;
  explanation: string;
  has_announcement: boolean;
  sentiment_pulse: DecimalString | null;
}

// ── Generic API error ───────────────────────────────────────────

export interface ApiErrorBody {
  detail: string;
}
