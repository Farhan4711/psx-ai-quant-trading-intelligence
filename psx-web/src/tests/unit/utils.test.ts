import { describe, expect, it } from "vitest";
import { formatCurrency, formatPercent } from "@/lib/utils/format";

describe("formatCurrency", () => {
  it("formats PKR amounts with thousand separators", () => {
    expect(formatCurrency(1234567.89)).toBe("PKR 1,234,567.89");
  });

  it("formats zero correctly", () => {
    expect(formatCurrency(0)).toBe("PKR 0.00");
  });

  it("formats negative amounts", () => {
    expect(formatCurrency(-5000)).toBe("-PKR 5,000.00");
  });
});

describe("formatPercent", () => {
  it("formats a positive percent with + sign", () => {
    expect(formatPercent(12.34)).toBe("+12.34%");
  });

  it("formats a negative percent", () => {
    expect(formatPercent(-5.6)).toBe("-5.60%");
  });

  it("formats zero", () => {
    expect(formatPercent(0)).toBe("0.00%");
  });
});
