import type { AnalysisResult } from "@/lib/types";

const STRUCTURE_LABEL: Record<AnalysisResult["structure_bias"], string> = {
  bullish: "Bullish",
  bearish: "Bearish",
  neutral: "Neutral",
};

function fmt(value: number): string {
  return value.toLocaleString("en-US", { maximumFractionDigits: value < 10 ? 4 : 2 });
}

export function AnalysisCard({ result }: { result: AnalysisResult }) {
  const scenarios = result.scenarios;

  return (
    <div className="flex flex-col gap-4 rounded-xl bg-zinc-900 p-4">
      <div>
        <p className="text-sm text-zinc-400">
          {result.symbol} · {result.tf}
        </p>
        <p className="text-sm text-zinc-400">Структура: {STRUCTURE_LABEL[result.structure_bias]}</p>
      </div>

      {scenarios ? (
        <>
          <div
            className={`rounded-lg p-3 ${
              scenarios.primary_direction === "long" ? "bg-emerald-950/60" : "bg-red-950/60"
            }`}
          >
            <p
              className={`mb-1 font-semibold ${
                scenarios.primary_direction === "long" ? "text-emerald-400" : "text-red-400"
              }`}
            >
              {scenarios.primary_direction === "long" ? "🟢 LONG" : "🔴 SHORT"} · Вероятность{" "}
              {scenarios.primary_confidence.toFixed(0)}%
            </p>
            {result.entry_low !== null && result.entry_high !== null && (
              <p className="text-sm text-zinc-300">
                Entry: {fmt(result.entry_low)}–{fmt(result.entry_high)}
              </p>
            )}
            {result.targets && result.targets.length > 0 && (
              <p className="text-sm text-zinc-300">
                Targets: {result.targets.map(fmt).join(" → ")}
              </p>
            )}
            {result.invalidation !== null && (
              <p className="text-sm text-zinc-300">Invalidation: {fmt(result.invalidation)}</p>
            )}
            {result.risk_reward !== null && (
              <p className="text-sm text-zinc-300">Risk/Reward: 1:{fmt(result.risk_reward)}</p>
            )}
          </div>

          <p className="text-sm text-zinc-500">
            {scenarios.primary_direction === "long" ? "🔴 Альтернатива — SHORT" : "🟢 Альтернатива — LONG"} (
            {scenarios.opposite_confidence.toFixed(0)}%) · ⚪ Нейтральный сценарий (
            {scenarios.neutral_confidence.toFixed(0)}%)
          </p>
        </>
      ) : (
        <p className="text-sm text-zinc-400">
          ⚪ Явного направленного перевеса нет — боковик, недостаточно данных для сделки.
        </p>
      )}

      <div>
        <p className="mb-1 text-sm font-medium text-zinc-300">Почему (WHY)</p>
        <ul className="flex flex-col gap-1">
          {result.why.map((bullet, i) => (
            <li
              key={i}
              className={`text-sm ${bullet.sign === "+" ? "text-emerald-400" : "text-red-400"}`}
            >
              {bullet.sign} {bullet.text}
            </li>
          ))}
        </ul>
      </div>

      <p className="text-xs text-zinc-500">{result.disclaimer}</p>
    </div>
  );
}
