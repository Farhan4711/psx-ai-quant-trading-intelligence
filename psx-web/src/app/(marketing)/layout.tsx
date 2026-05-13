import Link from "next/link";
import { BarChart2 } from "lucide-react";

const NAV = [
  { href: "/features", label: "Features" },
  { href: "/pricing", label: "Pricing" },
  { href: "/blog", label: "Blog" },
  { href: "/about", label: "About" },
];

export default function MarketingLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-screen flex-col bg-white">
      <header className="sticky top-0 z-40 border-b border-gray-200 bg-white/95 backdrop-blur">
        <div className="mx-auto flex h-14 max-w-6xl items-center gap-6 px-4 sm:px-6">
          <Link
            href="/"
            className="flex items-center gap-2 text-lg font-bold text-blue-700"
          >
            <BarChart2 className="h-5 w-5" />
            PSX AI
          </Link>
          <nav className="hidden items-center gap-1 sm:flex">
            {NAV.map((n) => (
              <Link
                key={n.href}
                href={n.href}
                className="rounded-md px-3 py-1.5 text-sm font-medium text-gray-600 hover:bg-gray-100 hover:text-gray-900"
              >
                {n.label}
              </Link>
            ))}
          </nav>
          <div className="ml-auto flex items-center gap-2">
            <Link
              href="/login"
              className="hidden text-sm font-medium text-gray-600 hover:text-gray-900 sm:block"
            >
              Log in
            </Link>
            <Link
              href="/signup"
              className="rounded-md bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700"
            >
              Sign up
            </Link>
          </div>
        </div>
      </header>

      <main className="flex-1">{children}</main>

      <footer className="border-t border-gray-200 bg-gray-50">
        <div className="mx-auto grid max-w-6xl gap-8 px-4 py-10 sm:grid-cols-4 sm:px-6">
          <div>
            <Link
              href="/"
              className="flex items-center gap-2 text-base font-bold text-blue-700"
            >
              <BarChart2 className="h-5 w-5" />
              PSX AI
            </Link>
            <p className="mt-2 max-w-xs text-xs text-gray-500">
              Honest analytics for Pakistani retail investors.
            </p>
          </div>
          <FooterCol
            title="Product"
            links={[
              ["/features", "Features"],
              ["/pricing", "Pricing"],
              ["/blog", "Blog"],
            ]}
          />
          <FooterCol
            title="Company"
            links={[
              ["/about", "About"],
              ["mailto:hello@psxai.example", "Contact"],
            ]}
          />
          <FooterCol
            title="Legal"
            links={[
              ["/terms", "Terms of Service"],
              ["/privacy", "Privacy"],
            ]}
          />
        </div>
        <div className="border-t border-gray-200">
          <div className="mx-auto max-w-6xl px-4 py-4 text-xs text-gray-500 sm:px-6">
            © {new Date().getFullYear()} PSX AI. Not a SECP-registered
            investment advisor. Predictions and signals are educational, not
            financial advice.
          </div>
        </div>
      </footer>
    </div>
  );
}

function FooterCol({ title, links }: { title: string; links: [string, string][] }) {
  return (
    <div>
      <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-500">
        {title}
      </h3>
      <ul className="mt-2 space-y-1.5">
        {links.map(([href, label]) => (
          <li key={href}>
            <Link
              href={href}
              className="text-sm text-gray-600 hover:text-gray-900"
            >
              {label}
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
