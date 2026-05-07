import NextAuth from "next-auth";
import Credentials from "next-auth/providers/credentials";
import { z } from "zod";

const loginSchema = z.object({
  email: z.string().email(),
  password: z.string().min(1),
  totpCode: z.string().length(6).optional(),
});

export const { handlers, signIn, signOut, auth } = NextAuth({
  providers: [
    Credentials({
      credentials: {
        email: { label: "Email", type: "email" },
        password: { label: "Password", type: "password" },
        totpCode: { label: "2FA Code", type: "text" },
      },
      async authorize(credentials) {
        const parsed = loginSchema.safeParse(credentials);
        if (!parsed.success) return null;

        const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
        const res = await fetch(`${apiUrl}/api/v1/auth/login`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            email: parsed.data.email,
            password: parsed.data.password,
            totp_code: parsed.data.totpCode ?? null,
          }),
          credentials: "include",
        });

        if (!res.ok) return null;

        const user = (await res.json()) as {
          user_id: string;
          email: string;
          full_name: string | null;
          email_verified: boolean;
          shariah_mode: boolean;
        };

        return {
          id: user.user_id,
          email: user.email,
          name: user.full_name,
          emailVerified: user.email_verified,
          shariahMode: user.shariah_mode,
        };
      },
    }),
  ],
  callbacks: {
    async jwt({ token, user }) {
      if (user) {
        token.userId = user.id;
        token.emailVerified = (user as { emailVerified?: boolean }).emailVerified;
        token.shariahMode = (user as { shariahMode?: boolean }).shariahMode;
      }
      return token;
    },
    async session({ session, token }) {
      if (token) {
        session.user.id = token.userId as string;
        (session as { emailVerified?: boolean }).emailVerified =
          token.emailVerified as boolean;
        (session as { shariahMode?: boolean }).shariahMode =
          token.shariahMode as boolean;
      }
      return session;
    },
  },
  pages: {
    signIn: "/login",
    error: "/login",
  },
  session: { strategy: "jwt" },
});
