"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { signIn } from "next-auth/react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

const schema = z.object({
  email: z.string().email("Enter a valid email"),
  password: z.string().min(1, "Password is required"),
  totpCode: z.string().length(6, "Enter your 6-digit code").optional().or(z.literal("")),
});

type FormData = z.infer<typeof schema>;

export default function LoginPage() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [showTotp, setShowTotp] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({ resolver: zodResolver(schema) });

  async function onSubmit(data: FormData) {
    setError(null);
    const result = await signIn("credentials", {
      email: data.email,
      password: data.password,
      totpCode: data.totpCode ?? "",
      redirect: false,
    });

    if (result?.error) {
      if (result.error.includes("TOTP")) {
        setShowTotp(true);
        setError("Enter your 6-digit authenticator code.");
      } else {
        setError("Invalid email or password.");
      }
      return;
    }
    router.push("/dashboard");
    router.refresh();
  }

  return (
    <>
      <h2 className="mb-6 text-center text-xl font-semibold text-gray-900">Sign in</h2>

      {error && (
        <div className="mb-4 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>
      )}

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <div className="space-y-1">
          <Label htmlFor="email">Email</Label>
          <Input
            id="email"
            type="email"
            autoComplete="email"
            placeholder="you@example.com"
            {...register("email")}
          />
          {errors.email && <p className="text-xs text-red-600">{errors.email.message}</p>}
        </div>

        <div className="space-y-1">
          <Label htmlFor="password">Password</Label>
          <Input
            id="password"
            type="password"
            autoComplete="current-password"
            {...register("password")}
          />
          {errors.password && (
            <p className="text-xs text-red-600">{errors.password.message}</p>
          )}
        </div>

        {showTotp && (
          <div className="space-y-1">
            <Label htmlFor="totpCode">Authenticator code</Label>
            <Input
              id="totpCode"
              type="text"
              inputMode="numeric"
              maxLength={6}
              placeholder="000000"
              autoComplete="one-time-code"
              {...register("totpCode")}
            />
            {errors.totpCode && (
              <p className="text-xs text-red-600">{errors.totpCode.message}</p>
            )}
          </div>
        )}

        <Button type="submit" className="w-full" disabled={isSubmitting}>
          {isSubmitting ? "Signing in…" : "Sign in"}
        </Button>
      </form>

      <div className="mt-4 flex flex-col gap-2 text-center text-sm text-gray-500">
        <Link href="/forgot-password" className="hover:text-blue-600 hover:underline">
          Forgot password?
        </Link>
        <span>
          No account?{" "}
          <Link href="/signup" className="font-medium text-blue-600 hover:underline">
            Create one
          </Link>
        </span>
      </div>
    </>
  );
}
