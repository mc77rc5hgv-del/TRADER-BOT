"""Renders an AnalysisResult into the fixed bot/Mini App text format from
TZ section 4.3. Purely presentational — every number here already came from
app/ta, app/probability, or app/risk."""

from __future__ import annotations

from app.ai.schemas import AnalysisResult


def render_text(result: AnalysisResult) -> str:
    lines = [
        f"{result.symbol} · {result.tf}",
        f"Структура: {result.structure_bias.capitalize()}",
        "",
    ]

    if result.scenarios is None:
        lines.append(
            "⚪ Явного направленного перевеса нет — боковик, недостаточно данных для сделки."
        )
    else:
        lines.extend(_render_scenarios(result))

    lines.append("")
    lines.append("Почему (WHY):")
    for bullet in result.why:
        lines.append(f"{bullet.sign} {bullet.text}")

    lines.append("")
    lines.append(result.disclaimer)
    return "\n".join(lines)


def _render_scenarios(result: AnalysisResult) -> list[str]:
    scenarios = result.scenarios
    assert scenarios is not None

    is_long = scenarios.primary_direction == "long"
    primary_emoji = "🟢" if is_long else "🔴"
    primary_label = "LONG" if is_long else "SHORT"
    opposite_emoji = "🔴" if is_long else "🟢"
    opposite_label = "SHORT" if is_long else "LONG"

    return [
        f"{primary_emoji} ОСНОВНОЙ СЦЕНАРИЙ — {primary_label}",
        f"Вероятность: {scenarios.primary_confidence:.0f}%",
        f"Entry: {result.entry_low:g}–{result.entry_high:g}",
        "Targets: " + " → ".join(f"{t:g}" for t in (result.targets or [])),
        f"Invalidation: {result.invalidation:g}",
        f"Risk/Reward: 1:{result.risk_reward:g}",
        "",
        f"{opposite_emoji} Альтернатива — {opposite_label} ({scenarios.opposite_confidence:.0f}%)",
        f"⚪ Нейтральный сценарий ({scenarios.neutral_confidence:.0f}%): боковик",
    ]
