"use client";

import {
  CandlestickSeries,
  createChart,
  LineStyle,
  type IChartApi,
  type IPriceLine,
  type ISeriesApi,
} from "lightweight-charts";
import { useEffect, useRef } from "react";

import type { Candle } from "@/lib/types";

export interface ChartLevels {
  entryLow?: number | null;
  entryHigh?: number | null;
  invalidation?: number | null;
  targets?: number[] | null;
}

function toChartData(candles: Candle[]) {
  return candles.map((c) => ({
    time: Math.floor(new Date(c.open_time).getTime() / 1000) as import("lightweight-charts").UTCTimestamp,
    open: c.open,
    high: c.high,
    low: c.low,
    close: c.close,
  }));
}

export function Chart({ candles, levels }: { candles: Candle[]; levels?: ChartLevels }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const chart = createChart(containerRef.current, {
      autoSize: true,
      layout: {
        background: { color: "transparent" },
        textColor: "#a1a1aa",
      },
      grid: {
        vertLines: { color: "#27272a" },
        horzLines: { color: "#27272a" },
      },
      timeScale: { timeVisible: true },
    });
    const series = chart.addSeries(CandlestickSeries, {
      upColor: "#34d399",
      downColor: "#f87171",
      borderVisible: false,
      wickUpColor: "#34d399",
      wickDownColor: "#f87171",
    });

    chartRef.current = chart;
    seriesRef.current = series;

    return () => {
      chart.remove();
      chartRef.current = null;
      seriesRef.current = null;
    };
  }, []);

  useEffect(() => {
    seriesRef.current?.setData(toChartData(candles));
    chartRef.current?.timeScale().fitContent();
  }, [candles]);

  // Draws the AI setup (entry/invalidation/targets) as horizontal price
  // lines directly on the chart (TZ section 9: "AI прямо рисует анализ на
  // графике") — every value here comes from the Risk Engine, this component
  // never computes one itself.
  useEffect(() => {
    const series = seriesRef.current;
    if (!series) return;

    const lines: IPriceLine[] = [];

    if (levels?.entryLow != null) {
      lines.push(
        series.createPriceLine({
          price: levels.entryLow,
          color: "#60a5fa",
          lineWidth: 1,
          lineStyle: LineStyle.Dashed,
          title: "Entry",
        }),
      );
    }
    if (levels?.entryHigh != null && levels.entryHigh !== levels?.entryLow) {
      lines.push(
        series.createPriceLine({
          price: levels.entryHigh,
          color: "#60a5fa",
          lineWidth: 1,
          lineStyle: LineStyle.Dashed,
          title: "Entry",
        }),
      );
    }
    if (levels?.invalidation != null) {
      lines.push(
        series.createPriceLine({
          price: levels.invalidation,
          color: "#f87171",
          lineWidth: 1,
          lineStyle: LineStyle.Dashed,
          title: "Stop",
        }),
      );
    }
    levels?.targets?.forEach((target, i) => {
      lines.push(
        series.createPriceLine({
          price: target,
          color: "#34d399",
          lineWidth: 1,
          lineStyle: LineStyle.Dashed,
          title: `TP${i + 1}`,
        }),
      );
    });

    return () => {
      lines.forEach((line) => series.removePriceLine(line));
    };
  }, [levels]);

  return <div ref={containerRef} className="h-72 w-full" />;
}
