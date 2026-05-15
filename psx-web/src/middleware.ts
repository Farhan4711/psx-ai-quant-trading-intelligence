export { auth as middleware } from "@/lib/auth";

export const config = {
  // Protect all authenticated app routes (route group `(app)` has no URL prefix,
  // so pages resolve directly — dashboard, stocks, watchlist, portfolio, etc.)
  matcher: [
    "/dashboard/:path*",
    "/stocks/:path*",
    "/watchlist/:path*",
    "/portfolio/:path*",
    "/goals/:path*",
    "/backtest/:path*",
    "/sectors/:path*",
    "/alerts/:path*",
    "/tax-simulator/:path*",
    "/settings/:path*",
    "/risk-profile/:path*",
    "/lessons/:path*",
    "/purification/:path*",
    "/strategies/:path*",
    "/checkout/:path*",
  ],
};
