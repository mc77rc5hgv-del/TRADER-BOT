"use client";

import { useEffect, useState } from "react";

import { getAccuracyReport } from "@/lib/api";
import type { AccuracyBreakdownRow, AccuracyReport } from "@/lib/types";

type LoadState = { status: "loading" } | { status: "ready"; report: AccuracyReport } | { status: "error" };

function formatWinRate(winRate: number | null): string {
  return winRate == null ? "—" : `${winRate.toFixed(0)}%`;
}

function BreakdownTable({ title, rows }: { title: string; rows: AccuracyBreakdownRow[] }) {
  if (rows.length === 0) return null;
  return (
    <div className="mb-4">
      <p className="mb-1 text-xs text-zinc-500">{title}</p>
      <div className="flex flex-col gap-2">
        {rows.map((row) => (
          <div
            key={row.key}
            className="flex items-center justify-between rounded-xl bg-zinc-900 px-4 py-3"
          >
            <span className="font-medium text-zinc-100">{row.key}</span>
            <span className="text-sm text-zinc-400">
              {row.total_predictions} прогн. · {formatWinRate(row.win_rate)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function AccuracyPage() {
  const [load, setLoad] = useState<LoadState>({ status: "loading" });

  useEffect(() => {
    let cancelled = false;

    getAccuracyReport()
      .then((report) => {
        if (!cancelled) setLoad({ status: "ready", report });
      })
      .catch(() => {
        if (!cancelled) setLoad({ status: "error" });
      });

    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="mx-auto max-w-md px-4 py-6">
      <h1 className="mb-1 text-xl font-semibold">📊 Точность AI</h1>

      {load.status === "loading" && <p className="text-sm text-zinc-500">Загрузка…</p>}
      {load.status === "error" && (
        <p className="text-sm text-red-400">Не удалось загрузить статистику — проверьте backend.</p>
      )}

      {load.status === "ready" && (
        <>
          <p className="mb-4 text-xs text-zinc-500">За последние {load.report.window_days} дней</p>

          {load.report.total_predictions === 0 ? (
            <p className="text-sm text-zinc-500">Пока недостаточно данных для статистики.</p>
          ) : (
            <>
              <div className="mb-4 grid grid-cols-2 gap-2">
                <div className="rounded-xl bg-zinc-900 px-4 py-3">
                  <p className="text-xs text-zinc-500">Прогнозов</p>
                  <p className="text-lg text-zinc-100">{load.report.total_predictions}</p>
                  <p className="text-xs text-zinc-500">оценено: {load.report.resolved_predictions}</p>
                </div>
                <div className="rounded-xl bg-zinc-900 px-4 py-3">
                  <p className="text-xs text-zinc-500">Win rate</p>
                  <p className="text-lg text-zinc-100">{formatWinRate(load.report.win_rate)}</p>
                  {load.report.avg_realized_r != null && (
                    <p className="text-xs text-zinc-500">
                      средний R: {load.report.avg_realized_r >= 0 ? "+" : ""}
                      {load.report.avg_realized_r.toFixed(2)}
                    </p>
                  )}
                </div>
              </div>

              <BreakdownTable title="По активам" rows={load.report.by_symbol} />
              <BreakdownTable title="По таймфреймам" rows={load.report.by_tf} />
            </>
          )}

          <p className="mt-2 text-xs text-zinc-600">
            AI-прогнозы — вероятностный анализ и поддержка принятия решений, а не гарантия результата.
          </p>
        </>
      )}
    </div>
  );
}
