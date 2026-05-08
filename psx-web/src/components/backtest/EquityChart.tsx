"use client";

import { useEffect, useRef } from "react";
import { createChart, ColorType, IChartApi } from "lightweight-charts";
import type { EquityPointOut } from "@/lib/api/backtest";

interface Props {
  curve: EquityPointOut[];
  initialCapital: number;
  benchmarkReturnPct: number;
}

/**
 * Two-line area chart: strategy equity vs synthetic buy-and-hold curve
 * scaled to the same starting capital. The benchmark line lets the user
 * see at a glance whether the strategy beat the passive comparison.
 */
export function EquityChart({ curve, initialCapital, benchmarkReturnPct }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);

  useEffect(() => {
    if (!containerRef.current || curve.length === 0) return;

    const chart = createChart(containerRef.current, {
      width: containerRef.current.clientWidth,
      height: 320,
      layout: {
        background: { type: ColorType.Solid, color: "white" },
        textColor: "#374151",
      },
      grid: {
        horzLines: { color: "#f3f4f6" },
        vertLines: { color: "#f3f4f6" },
      },
      rightPriceScale: { borderColor: "#e5e7eb" },
      timeScale: { borderColor: "#e5e7eb", timeVisible: false },
    });
    chartRef.current = chart;

    // Strategy equity (blue line)
    const strategySeries = chart.addLineSeries({
      color: "#2563eb",
      lineWidth: 2,
      title: "Strategy",
    });
    strategySeries.setData(
      curve.map((p) => ({ time: p.date, value: p.equity_pkr })),
    );

    // Benchmark line — interpolated linearly from initial capital to final
    // benchmark value. Not a per-day mark-to-market (we don't have the
    // unaltered close series here), but for a glance at "did you beat
    // passive?" the linear approximation is plenty.
    const finalBench = initialCapital * (1 + benchmarkReturnPct / 100);
    const benchmarkSeries = chart.addLineSeries({
      color: "#9ca3af",
      lineWidth: 1,
      lineStyle: 2, // dashed
      title: "Buy & hold",
    });
    benchmarkSeries.setData(
      curve.map((p, i) => ({
        time: p.date,
        value:
          initialCapital +
          ((finalBench - initialCapital) * i) / Math.max(curve.length - 1, 1),
      })),
    );

    chart.timeScale().fitContent();

    const ro = new ResizeObserver(() => {
      if (containerRef.current) {
        chart.applyOptions({ width: containerRef.current.clientWidth });
      }
    });
    ro.observe(containerRef.current);

    return () => {
      ro.disconnect();
      chart.remove();
    };
  }, [curve, initialCapital, benchmarkReturnPct]);

  return (
    <div className="space-y-2">
      <div ref={containerRef} className="w-full" />
      <div className="flex flex-wrap gap-4 text-xs text-gray-500">
        <span className="flex items-center gap-1.5">
          <span className="h-0.5 w-4 bg-blue-600" />
          Strategy
        </span>
        <span className="flex items-center gap-1.5">
          <span
            className="h-0.5 w-4"
            style={{
              backgroundImage:
                "linear-gradient(to right, #9ca3af 50%, transparent 50%)",
              backgroundSize: "8px 100%",
            }}
          />
          Buy &amp; hold (linear approximation)
        </span>
      </div>
    </div>
  );
}
