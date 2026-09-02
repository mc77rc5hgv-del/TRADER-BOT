"use client";

import { useState } from "react";

import { AnalysisCard } from "@/components/AnalysisCard";
import { analyzeSymbol, ApiError } from "@/lib/api";
import { ALLOWED_TIMEFRAMES, DEFAULT_TIMEFRAME, TRACKED_SYMBOLS, type AnalysisResult, type Timeframe } from "@/lib/types";

type LoadState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "ready"; data: AnalysisResult }
  | { status: "error"; message: string };

export default function AiPage() {
  const [symbol, setSymbol] = useState("");
  const [tf, setTf] = useState<Timeframe>(DEFAULT_TIMEFRAME);
  const [load, setLoad] = useState<LoadState>({ status: "idle" });

  function runAnalysis(targetSymbol: string) {
    const trimmed = targetSymbol.trim();
    if (!trimmed) return;

    setLoad({ status: "loading" });
    analyzeSymbol(trimmed, tf)
      .then((data) => setLoad({ status: "ready", data }))
      .catch((err: unknown) => {
        const message =
          err instanceof ApiError && err.status === 404
            ? `Актив «${trimmed}» не распознан.`
            : "Не удалось получить анализ — проверьте backend.";
        setLoad({ status: "error", message });
      });
  }

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    runAnalysis(symbol);
  }

  return (
    <div className="mx-auto max-w-md px-4 py-6">
      <h1 className="mb-4 text-xl font-semibold">✨ AI Анализ</h1>

      <form onSubmit={handleSubmit} className="mb-3 flex gap-2">
        <input
          value={symbol}
          onChange={(e) => setSymbol(e.target.value)}
          placeholder="Тикер, например BTC"
          className="flex-1 rounded-lg bg-zinc-900 px-3 py-2 text-sm text-zinc-100 placeholder-zinc-500 outline-none focus:ring-1 focus:ring-blue-500"
        />
        <button
          type="submit"
          className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-500"
        >
          Спросить
        </button>
      </form>

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

      <div className="mb-6 flex flex-wrap gap-2">
        {TRACKED_SYMBOLS.map((quick) => (
          <button
            key={quick}
            type="button"
            onClick={() => {
              setSymbol(quick);
              runAnalysis(quick);
            }}
            className="rounded-full bg-zinc-900 px-4 py-2 text-sm text-zinc-200 hover:bg-zinc-800"
          >
            {quick}
          </button>
        ))}
      </div>

      {load.status === "loading" && <p className="text-sm text-zinc-500">⏳ Анализирую…</p>}
      {load.status === "error" && <p className="text-sm text-red-400">{load.message}</p>}
      {load.status === "ready" && <AnalysisCard result={load.data} />}
    </div>
  );
}
