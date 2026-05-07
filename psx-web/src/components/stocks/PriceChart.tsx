"use client";

import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { createChart, ColorType, IChartApi, ISeriesApi } from "lightweight-charts";
import { fetchOhlcv } from "@/lib/api/securities";

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
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);

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

  return (
    <div>
      {/* Timeframe selector */}
      <div className="mb-3 flex items-center gap-1">
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

      {/* Chart container */}
      <div ref={containerRef} className="w-full" />
    </div>
  );
}
