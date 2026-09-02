"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { getScannerResults } from "@/lib/api";
import type { RiskLevel, ScannerDirection, ScannerEntry } from "@/lib/types";

type LoadState =
  | { status: "loading" }
  | { status: "ready"; entries: ScannerEntry[]; updatedAt: string | null }
  | { status: "error" };

const DIRECTION_FILTERS: { label: string; value: ScannerDirection | "all" }[] = [
  { label: "Все", value: "all" },
  { label: "Long", value: "long" },
  { label: "Short", value: "short" },
];

const RISK_FILTERS: { label: string; value: RiskLevel | "all" }[] = [
  { label: "Все", value: "all" },
  { label: "Low", value: "low" },
  { label: "Medium", value: "medium" },
  { label: "High", value: "high" },
];

function directionLabel(direction: ScannerDirection): string {
  if (direction === "long") return "🟢 LONG";
  if (direction === "short") return "🔴 SHORT";
  return "⚪ NEUTRAL";
}

function ScannerCard({ entry }: { entry: ScannerEntry }) {
  const baseSymbol = entry.symbol.split("USDT")[0];
  return (
    <Link
      href={`/market/${baseSymbol}`}
      className="flex items-center justify-between rounded-xl bg-zinc-900 px-4 py-3 hover:bg-zinc-800"
    >
      <div>
        <p className="font-medium text-zinc-100">{baseSymbol}/USDT</p>
        <p className="text-sm text-zinc-400">{directionLabel(entry.direction)}</p>
      </div>
      <div className="text-right text-sm">
        <p className="text-zinc-100">{entry.confidence.toFixed(0)}%</p>
        {entry.risk_reward != null && <p className="text-zinc-400">R:R 1:{entry.risk_reward.toFixed(1)}</p>}
        {entry.risk_level && <p className="text-zinc-500">Risk: {entry.risk_level}</p>}
      </div>
    </Link>
  );
}

export default function ScannerPage() {
  const [direction, setDirection] = useState<ScannerDirection | "all">("all");
  const [risk, setRisk] = useState<RiskLevel | "all">("all");
  const [load, setLoad] = useState<LoadState>({ status: "loading" });

  useEffect(() => {
    let cancelled = false;

    getScannerResults(direction === "all" ? undefined : direction, risk === "all" ? undefined : risk)
      .then((data) => {
        if (!cancelled) setLoad({ status: "ready", entries: data.entries, updatedAt: data.updated_at });
      })
      .catch(() => {
        if (!cancelled) setLoad({ status: "error" });
      });

    return () => {
      cancelled = true;
    };
  }, [direction, risk]);

  return (
    <div className="mx-auto max-w-md px-4 py-6">
      <h1 className="mb-1 text-xl font-semibold">🔥 Лучшие сетапы</h1>
      {load.status === "ready" && load.updatedAt && (
        <p className="mb-4 text-xs text-zinc-500">
          Обновлено: {new Date(load.updatedAt).toLocaleTimeString("ru-RU")}
        </p>
      )}

      <p className="mb-1 text-xs text-zinc-500">Направление</p>
      <div className="mb-3 flex flex-wrap gap-2">
        {DIRECTION_FILTERS.map((option) => (
          <button
            key={option.value}
            type="button"
            onClick={() => setDirection(option.value)}
            className={`rounded-lg px-3 py-1.5 text-sm ${
              option.value === direction ? "bg-blue-600 text-white" : "bg-zinc-900 text-zinc-300"
            }`}
          >
            {option.label}
          </button>
        ))}
      </div>

      <p className="mb-1 text-xs text-zinc-500">Риск</p>
      <div className="mb-4 flex flex-wrap gap-2">
        {RISK_FILTERS.map((option) => (
          <button
            key={option.value}
            type="button"
            onClick={() => setRisk(option.value)}
            className={`rounded-lg px-3 py-1.5 text-sm ${
              option.value === risk ? "bg-blue-600 text-white" : "bg-zinc-900 text-zinc-300"
            }`}
          >
            {option.label}
          </button>
        ))}
      </div>

      {load.status === "loading" && <p className="text-sm text-zinc-500">Загрузка…</p>}
      {load.status === "error" && (
        <p className="text-sm text-red-400">Не удалось загрузить сетапы — проверьте backend.</p>
      )}
      {load.status === "ready" && load.entries.length === 0 && (
        <p className="text-sm text-zinc-500">
          Пока нет посчитанных сетапов по этим фильтрам. Фоновая джоба обновляет список каждые 10 минут.
        </p>
      )}

      <div className="flex flex-col gap-2">
        {load.status === "ready" && load.entries.map((entry) => <ScannerCard key={entry.symbol} entry={entry} />)}
      </div>
    </div>
  );
}
