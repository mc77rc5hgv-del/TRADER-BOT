"use client";

import { use, useEffect, useState } from "react";

import { Chart } from "@/components/Chart";
import { ApiError, getMarketState } from "@/lib/api";
import { ALLOWED_TIMEFRAMES, DEFAULT_TIMEFRAME, type MarketState, type Timeframe } from "@/lib/types";

type LoadState =
  | { status: "loading" }
  | { status: "ready"; data: MarketState }
  | { status: "error"; message: string };

export default function MarketSymbolPage(props: PageProps<"/market/[symbol]">) {
  const { symbol } = use(props.params);

  const [tf, setTf] = useState<Timeframe>(DEFAULT_TIMEFRAME);
  const [load, setLoad] = useState<LoadState>({ status: "loading" });

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

  const state = load.status === "ready" ? load.data : null;
  const isUp = (state?.ticker.price_change_percent_24h ?? 0) >= 0;

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
      {state && <Chart candles={state.candles} />}
    </div>
  );
}
