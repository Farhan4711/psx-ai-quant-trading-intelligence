/**
 * Billing + Pakistani payment-gateway client.
 *
 * All types come from `@psx/shared` so the contract with the FastAPI
 * backend is enforced at the type level. Hidden-form POST helper is
 * here because it's a browser-only DOM API and `@psx/shared` is
 * environment-agnostic.
 */

import {
  createApiClient,
  type BillingCycle,
  type CheckoutRequest,
  type CheckoutResponse,
  type CurrentSubscription,
  type PaymentIntentStatus,
  type PaymentMethodOption,
  type PaymentProvider,
  type SubscriptionPlan,
} from "@psx/shared";

// Re-export for legacy callers; new code should use `@psx/shared` directly.
export type {
  BillingCycle,
  CheckoutRequest,
  CheckoutResponse,
  CurrentSubscription,
  PaymentIntentStatus,
  PaymentMethodOption,
  PaymentProvider,
  SubscriptionPlan,
};
// Aliases kept for source-compat with existing imports in pages built
// before psx-shared was wired.
export type PlanRow = SubscriptionPlan;
export type PaymentMethod = PaymentMethodOption;
export type IntentStatus = PaymentIntentStatus;

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const api = createApiClient({ baseUrl: API_URL });

export async function fetchPlans(): Promise<SubscriptionPlan[]> {
  return api.get("/api/v1/billing/plans");
}

export async function fetchPaymentMethods(): Promise<PaymentMethodOption[]> {
  return api.get("/api/v1/billing/payment-methods");
}

export async function fetchCurrentSubscription(): Promise<CurrentSubscription> {
  return api.get("/api/v1/billing/me");
}

export async function startCheckout(input: CheckoutRequest): Promise<CheckoutResponse> {
  return api.post("/api/v1/billing/checkout", input);
}

export async function fetchIntentStatus(intentId: string): Promise<PaymentIntentStatus> {
  return api.get(`/api/v1/billing/intent/${intentId}`);
}

export async function sandboxConfirm(intentId: string): Promise<{
  ok: boolean;
  intent_id: string;
  status: string;
}> {
  return api.post(`/api/v1/billing/sandbox-confirm/${intentId}`);
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
