/**
 * Billing + Pakistani payment-gateway client.
 *
 * The flow:
 *   1. /pricing  → public, lists plans + payment methods (no auth needed)
 *   2. /checkout?plan=pro&cycle=monthly  → authed, user picks a gateway
 *   3. POST /api/v1/billing/checkout returns the gateway URL + signed
 *      request_payload to hidden-form-POST (for redirect gateways) or
 *      a URL to window.location to (for API gateways) or text
 *      instructions to render inline (for `manual`).
 *   4. After gateway round-trip the user lands on /checkout/return
 *      which polls /api/v1/billing/intent/:id until activation.
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    credentials: "include",
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!res.ok) {
    const err = (await res.json().catch(() => ({ detail: res.statusText }))) as {
      detail?: string;
    };
    throw new Error(err.detail ?? "Request failed");
  }
  return res.json() as Promise<T>;
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

export interface PaymentMethod {
  slug: PaymentProvider;
  name: string;
  category: "wallet" | "bank" | "card" | "manual";
  description: string;
  logo_hint: string;
}

export interface PlanRow {
  id: number;
  slug: string;
  name: string;
  tagline: string;
  price_pkr_monthly: string;
  price_pkr_annual: string | null;
  features: string[];
  display_order: number;
}

export interface CheckoutResponse {
  intent_id: string;
  provider: PaymentProvider;
  checkout_url: string;
  is_sandbox: boolean;
  instructions: string | null;
  request_payload: Record<string, string>;
  amount_pkr: string;
  expires_at: string | null;
}

export interface IntentStatus {
  id: string;
  provider: PaymentProvider;
  status: "pending" | "redirected" | "paid" | "failed" | "canceled" | "expired";
  amount_pkr: string;
  billing_cycle: BillingCycle;
  plan_slug: string;
  failure_reason: string | null;
  created_at: string;
  returned_at: string | null;
}

export async function fetchPlans(): Promise<PlanRow[]> {
  return api("/api/v1/billing/plans");
}

export async function fetchPaymentMethods(): Promise<PaymentMethod[]> {
  return api("/api/v1/billing/payment-methods");
}

export async function startCheckout(input: {
  plan_slug: string;
  provider: PaymentProvider;
  billing_cycle: BillingCycle;
}): Promise<CheckoutResponse> {
  return api("/api/v1/billing/checkout", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export async function fetchIntentStatus(intentId: string): Promise<IntentStatus> {
  return api(`/api/v1/billing/intent/${intentId}`);
}

export async function sandboxConfirm(intentId: string): Promise<{
  ok: boolean;
  intent_id: string;
  status: string;
}> {
  return api(`/api/v1/billing/sandbox-confirm/${intentId}`, { method: "POST" });
}

/**
 * Submit the signed form payload to a redirect gateway. JazzCash,
 * Easypaisa, Meezan, and PayFast all expect a browser-driven form POST
 * (not an XHR) so the user lands on the gateway's hosted page with
 * full session cookies. We synthesise + auto-submit the form here.
 */
export function postToGateway(
  checkoutUrl: string,
  fields: Record<string, string>,
): void {
  const form = document.createElement("form");
  form.method = "POST";
  form.action = checkoutUrl;
  form.style.display = "none";
  for (const [key, value] of Object.entries(fields)) {
    if (value === undefined || value === null) continue;
    const input = document.createElement("input");
    input.type = "hidden";
    input.name = key;
    input.value = String(value);
    form.appendChild(input);
  }
  document.body.appendChild(form);
  form.submit();
}
