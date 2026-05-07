const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
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

export async function apiSignup(data: {
  email: string;
  password: string;
  fullName?: string;
}): Promise<{ message: string; user_id: string }> {
  return apiFetch("/api/v1/auth/signup", {
    method: "POST",
    body: JSON.stringify({
      email: data.email,
      password: data.password,
      full_name: data.fullName ?? null,
    }),
  });
}

export async function apiForgotPassword(email: string): Promise<{ message: string }> {
  return apiFetch("/api/v1/auth/forgot-password", {
    method: "POST",
    body: JSON.stringify({ email }),
  });
}

export async function apiResetPassword(data: {
  token: string;
  newPassword: string;
}): Promise<{ message: string }> {
  return apiFetch("/api/v1/auth/reset-password", {
    method: "POST",
    body: JSON.stringify({ token: data.token, new_password: data.newPassword }),
  });
}

export async function apiVerifyEmail(token: string): Promise<{ message: string }> {
  return apiFetch("/api/v1/auth/verify-email", {
    method: "POST",
    body: JSON.stringify({ token }),
  });
}
