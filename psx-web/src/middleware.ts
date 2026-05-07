export { auth as middleware } from "@/lib/auth";

export const config = {
  // Protect all /app/* routes; allow auth routes and public pages through
  matcher: ["/app/:path*"],
};
