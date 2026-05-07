export function formatCurrency(amount: number): string {
  const abs = Math.abs(amount);
  const formatted = abs.toLocaleString("en-PK", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
  return amount < 0 ? `-PKR ${formatted}` : `PKR ${formatted}`;
}

export function formatPercent(value: number): string {
  const formatted = Math.abs(value).toFixed(2);
  if (value > 0) return `+${formatted}%`;
  if (value < 0) return `-${formatted}%`;
  return `${formatted}%`;
}

export function formatMarketCap(pkr: number | null | undefined): string {
  if (pkr == null) return "—";
  const abs = Math.abs(pkr);
  if (abs >= 1_000_000_000_000) return `PKR ${(pkr / 1_000_000_000_000).toFixed(2)}T`;
  if (abs >= 1_000_000_000) return `PKR ${(pkr / 1_000_000_000).toFixed(2)}B`;
  if (abs >= 1_000_000) return `PKR ${(pkr / 1_000_000).toFixed(2)}M`;
  return `PKR ${pkr.toLocaleString("en-PK")}`;
}

export function formatVolume(n: number | null | undefined): string {
  if (n == null) return "—";
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(2)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

export function formatDecimal(value: string | null | undefined, decimals = 2): string {
  if (value == null) return "—";
  const n = parseFloat(value);
  return isNaN(n) ? "—" : n.toFixed(decimals);
}

export function formatPrice(value: string | number | null | undefined): string {
  if (value == null) return "—";
  const n = typeof value === "string" ? parseFloat(value) : value;
  return isNaN(n)
    ? "—"
    : n.toLocaleString("en-PK", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}
