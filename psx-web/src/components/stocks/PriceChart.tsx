"use client";

import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { createChart, ColorType, IChartApi, ISeriesApi } from "lightweight-charts";
import { fetchOhlcv } from "@/lib/api/securities";
import { fetchMacroIndicators, fetchMacroSeries } from "@/lib/api/macro";

type Timeframe = "1W" | "1M" | "3M" | "1Y" | "5Y" | "All";

const TIMEFRAME_LIMITS: Record<Timeframe, number> = {
  "1W": 7,
  "1M": 30,
  "3M": 90,
  "1Y": 252,
  "5Y": 1260,
  All: 2000,
};

const TIMEFRAMES: Timeframe[] = ["1W", "1M", "3M", "1Y", "5Y", "All"];

export function PriceChart({ symbol }: { symbol: string }) {
  const [timeframe, setTimeframe] = useState<Timeframe>("1Y");
  const [overlay, setOverlay] = useState<string>("");
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const overlaySeriesRef = useRef<ISeriesApi<"Line"> | null>(null);

  const { data: macroIndicators } = useQuery({
    queryKey: ["macro-indicators"],
    queryFn: fetchMacroIndicators,
    staleTime: 86_400_000,
  });

  const { data: macroSeries } = useQuery({
    queryKey: ["macro-series", overlay, timeframe],
    queryFn: () => fetchMacroSeries(overlay),
    enabled: !!overlay,
    staleTime: 3_600_000,
  });

  const { data, isLoading } = useQuery({
    queryKey: ["ohlcv", symbol, timeframe],
    queryFn: () => fetchOhlcv(symbol, { limit: TIMEFRAME_LIMITS[timeframe], adjusted: true }),
    staleTime: 300_000,
  });

  // Initialise chart once
  useEffect(() => {
    if (!containerRef.current) return;

    const chart = createChart(containerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: "#ffffff" },
        textColor: "#374151",
      },
      grid: {
        vertLines: { color: "#f3f4f6" },
        horzLines: { color: "#f3f4f6" },
      },
      crosshair: { mode: 0 },
      rightPriceScale: {
        borderColor: "#e5e7eb",
        scaleMargins: { top: 0.1, bottom: 0.1 },
      },
      timeScale: {
        borderColor: "#e5e7eb",
        timeVisible: true,
        secondsVisible: false,
      },
      width: containerRef.current.clientWidth,
      height: 360,
    });

    const series = chart.addCandlestickSeries({
      upColor: "#16a34a",
      downColor: "#dc2626",
      borderUpColor: "#16a34a",
      borderDownColor: "#dc2626",
      wickUpColor: "#16a34a",
      wickDownColor: "#dc2626",
    });

    chartRef.current = chart;
    seriesRef.current = series;

    const handleResize = () => {
      if (containerRef.current) chart.applyOptions({ width: containerRef.current.clientWidth });
    };
    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      chart.remove();
    };
  }, []);

  // Update data when query result changes
  useEffect(() => {
    if (!seriesRef.current || !data?.items) return;

    const chartData = [...data.items]
      .reverse()
      .filter(
        (item) => item.open != null && item.high != null && item.low != null && item.close != null,
      )
      .map((item) => ({
        time: item.date as unknown as import("lightweight-charts").Time,
        open: parseFloat(item.open!),
        high: parseFloat(item.high!),
        low: parseFloat(item.low!),
        close: parseFloat(item.close!),
      }));

    seriesRef.current.setData(chartData);
    chartRef.current?.timeScale().fitContent();
  }, [data]);

  // Macro overlay — second price scale on the left
  useEffect(() => {
    const chart = chartRef.current;
    if (!chart) return;

    // Drop any prior overlay
    if (overlaySeriesRef.current) {
      try {
        chart.removeSeries(overlaySeriesRef.current);
      } catch {
        // already removed
      }
      overlaySeriesRef.current = null;
    }

    if (!overlay || !macroSeries || macroSeries.length === 0) return;

    const series = chart.addLineSeries({
      color: "#a855f7",
      lineWidth: 2,
      priceScaleId: "macro",
      title: macroIndicators?.find((i) => i.key === overlay)?.label ?? overlay,
    });
    chart.priceScale("macro").applyOptions({
      scaleMargins: { top: 0.1, bottom: 0.1 },
      visible: true,
      borderColor: "#e5e7eb",
    });
    series.setData(
      macroSeries.map((p) => ({
        time: p.date as unknown as import("lightweight-charts").Time,
        value: p.value,
      })),
    );
    overlaySeriesRef.current = series;
  }, [overlay, macroSeries, macroIndicators]);

  return (
    <div>
      {/* Timeframe + macro overlay */}
      <div className="mb-3 flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-1">
          {TIMEFRAMES.map((tf) => (
            <button
              key={tf}
              onClick={() => setTimeframe(tf)}
              className={`rounded-md px-2.5 py-1 text-xs font-medium transition-colors ${
                timeframe === tf
                  ? "bg-blue-100 text-blue-700"
                  : "text-gray-500 hover:bg-gray-100 hover:text-gray-700"
              }`}
            >
              {tf}
            </button>
          ))}
          {isLoading && (
            <span className="ml-2 text-xs text-gray-400">Loading…</span>
          )}
        </div>

        <div className="ml-auto flex items-center gap-2">
          <label className="text-xs text-gray-500">Overlay:</label>
          <select
            value={overlay}
            onChange={(e) => setOverlay(e.target.value)}
            className="rounded-md border border-gray-300 bg-white px-2 py-1 text-xs focus:outline-none focus:ring-2 focus:ring-blue-600"
          >
            <option value="">None</option>
            {(macroIndicators ?? []).map((i) => (
              <option key={i.key} value={i.key}>
                {i.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Chart container */}
      <div ref={containerRef} className="w-full" />
    </div>
  );
}
