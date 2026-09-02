"use client";

import { useEffect, useState } from "react";

import { getMarketState } from "@/lib/api";
import { PriceCard } from "@/components/PriceCard";
import { DEFAULT_TIMEFRAME, TRACKED_SYMBOLS } from "@/lib/types";
import type { Ticker } from "@/lib/types";

type LoadState =
  | { status: "loading" }
  | { status: "ready"; tickers: Record<string, Ticker> }
  | { status: "error" };

export default function HomePage() {
  const [load, setLoad] = useState<LoadState>({ status: "loading" });

  useEffect(() => {
    let cancelled = false;

    Promise.allSettled(TRACKED_SYMBOLS.map((symbol) => getMarketState(symbol, DEFAULT_TIMEFRAME))).then(
      (results) => {
        if (cancelled) return;

        const tickers: Record<string, Ticker> = {};
        results.forEach((result, i) => {
          if (result.status === "fulfilled") {
            tickers[TRACKED_SYMBOLS[i]] = result.value.ticker;
          }
        });

        setLoad(Object.keys(tickers).length > 0 ? { status: "ready", tickers } : { status: "error" });
      },
    );

    return () => {
      cancelled = true;
    };
  }, []);

  const tickers = load.status === "ready" ? load.tickers : {};

  return (
    <div className="mx-auto max-w-md px-4 py-6">
      <h1 className="mb-1 text-2xl font-semibold">🤖 TRADE AI</h1>
      <p className="mb-6 text-sm text-zinc-400">Market Pulse</p>

      {load.status === "loading" && <p className="text-sm text-zinc-500">Загрузка цен…</p>}
      {load.status === "error" && (
        <p className="text-sm text-red-400">
          Не удалось загрузить данные. Проверьте, что backend запущен и доступен.
        </p>
      )}

      <div className="flex flex-col gap-2">
        {TRACKED_SYMBOLS.filter((symbol) => tickers[symbol]).map((symbol) => (
          <PriceCard key={symbol} symbol={symbol} ticker={tickers[symbol]} />
        ))}
      </div>
    </div>
  );
}
