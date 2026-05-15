import {
  createApiClient,
  type CurrentUser,
  type UserSettingsUpdate,
} from "@psx/shared";

// Re-export so existing callers (`import { CurrentUser } from "@/lib/api/auth"`)
// keep working during the migration. New code should import from
// `@psx/shared` directly.
export type { CurrentUser, UserSettingsUpdate };

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const api = createApiClient({ baseUrl: API_URL });

export async function apiSignup(data: {
  email: string;
  password: string;
  fullName?: string;
}): Promise<{ message: string; user_id: string }> {
  return api.post("/api/v1/auth/signup", {
    email: data.email,
    password: data.password,
    full_name: data.fullName ?? null,
  });
}

export async function apiForgotPassword(email: string): Promise<{ message: string }> {
  return api.post("/api/v1/auth/forgot-password", { email });
}

export async function apiResetPassword(data: {
  token: string;
  newPassword: string;
}): Promise<{ message: string }> {
  return api.post("/api/v1/auth/reset-password", {
    token: data.token,
    new_password: data.newPassword,
  });
}

export async function apiVerifyEmail(token: string): Promise<{ message: string }> {
  return api.post("/api/v1/auth/verify-email", { token });
}

export const fetchCurrentUser = () => api.get<CurrentUser>("/api/v1/auth/me");

export const updateCurrentUser = (body: UserSettingsUpdate) =>
  api.patch<CurrentUser>("/api/v1/auth/me", body);
