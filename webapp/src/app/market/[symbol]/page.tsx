"use client";

import { use, useEffect, useState } from "react";

import { AnalysisCard } from "@/components/AnalysisCard";
import { Chart, type ChartLevels } from "@/components/Chart";
import { analyzeSymbol, ApiError, getMarketState } from "@/lib/api";
import { ALLOWED_TIMEFRAMES, DEFAULT_TIMEFRAME, type AnalysisResult, type MarketState, type Timeframe } from "@/lib/types";

type LoadState =
  | { status: "loading" }
  | { status: "ready"; data: MarketState }
  | { status: "error"; message: string };

type AnalysisState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "ready"; data: AnalysisResult; symbol: string; tf: Timeframe }
  | { status: "error"; message: string };

export default function MarketSymbolPage(props: PageProps<"/market/[symbol]">) {
  const { symbol } = use(props.params);

  const [tf, setTf] = useState<Timeframe>(DEFAULT_TIMEFRAME);
  const [load, setLoad] = useState<LoadState>({ status: "loading" });
  const [analysis, setAnalysis] = useState<AnalysisState>({ status: "idle" });

  useEffect(() => {
    let cancelled = false;

    getMarketState(symbol, tf)
      .then((data) => {
        if (!cancelled) setLoad({ status: "ready", data });
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        const message =
          err instanceof ApiError && err.status === 404
            ? `Актив «${symbol}» не распознан.`
            : "Не удалось загрузить данные — проверьте backend.";
        setLoad({ status: "error", message });
      });

    return () => {
      cancelled = true;
    };
  }, [symbol, tf]);

  function runAnalysis() {
    setAnalysis({ status: "loading" });
    analyzeSymbol(symbol, tf)
      .then((data) => setAnalysis({ status: "ready", data, symbol, tf }))
      .catch(() => setAnalysis({ status: "error", message: "Не удалось получить анализ." }));
  }

  const state = load.status === "ready" ? load.data : null;
  const isUp = (state?.ticker.price_change_percent_24h ?? 0) >= 0;
  // Stale results (from before a symbol/TF change) are dropped at render
  // time rather than reset via an effect — simpler and avoids an extra
  // render pass.
  const result =
    analysis.status === "ready" && analysis.symbol === symbol && analysis.tf === tf ? analysis.data : null;
  const levels: ChartLevels | undefined = result
    ? {
        entryLow: result.entry_low,
        entryHigh: result.entry_high,
        invalidation: result.invalidation,
        targets: result.targets,
      }
    : undefined;

  return (
    <div className="mx-auto max-w-md px-4 py-6">
      <h1 className="mb-1 text-xl font-semibold">{symbol.toUpperCase()}/USDT</h1>

      {state && (
        <div className="mb-4 flex items-baseline gap-2">
          <span className="text-2xl font-semibold">
            $
            {state.ticker.price.toLocaleString("en-US", {
              maximumFractionDigits: state.ticker.price < 10 ? 4 : 2,
            })}
          </span>
          <span className={isUp ? "text-emerald-400" : "text-red-400"}>
            {isUp ? "+" : ""}
            {state.ticker.price_change_percent_24h.toFixed(2)}%
          </span>
        </div>
      )}

      <div className="mb-4 flex flex-wrap gap-2">
        {ALLOWED_TIMEFRAMES.map((option) => (
          <button
            key={option}
            type="button"
            onClick={() => setTf(option)}
            className={`rounded-lg px-3 py-1.5 text-sm ${
              option === tf ? "bg-blue-600 text-white" : "bg-zinc-900 text-zinc-300"
            }`}
          >
            {option.toUpperCase()}
          </button>
        ))}
      </div>

      {load.status === "error" && <p className="text-sm text-red-400">{load.message}</p>}
      {load.status === "loading" && <p className="text-sm text-zinc-500">Загрузка графика…</p>}
      {state && <Chart candles={state.candles} levels={levels} />}

      {state && (
        <button
          type="button"
          onClick={runAnalysis}
          disabled={analysis.status === "loading"}
          className="mt-4 w-full rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-blue-500 disabled:opacity-60"
        >
          {analysis.status === "loading" ? "⏳ Анализирую…" : "✨ AI ANALYSIS"}
        </button>
      )}

      {analysis.status === "error" && <p className="mt-3 text-sm text-red-400">{analysis.message}</p>}
      {result && (
        <div className="mt-4">
          <AnalysisCard result={result} />
        </div>
      )}
    </div>
  );
}
