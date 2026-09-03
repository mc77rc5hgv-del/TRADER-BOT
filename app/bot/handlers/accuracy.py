"""AI Accuracy public screen (TZ section 3.6) — renders the same cached
daily report the Mini App reads from GET /webapp/accuracy."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from app.ai.accuracy import compute_accuracy_report, get_cached_accuracy_report
from app.ai.schemas import AccuracyReport
from app.bot.keyboards import BTN_ACCURACY, CB_ACCURACY
from app.core.redis import get_redis
from app.db.session import async_session_factory

router = Router(name="accuracy")

NO_DATA_TEXT = "📊 Пока недостаточно данных для статистики точности AI."


def _render_report(report: AccuracyReport) -> str:
    if report.total_predictions == 0:
        return NO_DATA_TEXT

    lines = [
        f"📊 Точность AI за последние {report.window_days} дней",
        f"Прогнозов: {report.total_predictions} (оценено: {report.resolved_predictions})",
    ]

    if report.win_rate is not None:
        lines.append(f"Win rate: {report.win_rate:.0f}%")
    if report.avg_realized_r is not None:
        lines.append(f"Средний R: {report.avg_realized_r:+.2f}")

    if report.by_symbol:
        lines.append("\nПо активам:")
        lines.extend(
            f"• {row.key}: {row.total_predictions} "
            + (f"({row.win_rate:.0f}% win)" if row.win_rate is not None else "(нет оценённых)")
            for row in report.by_symbol
        )

    if report.by_tf:
        lines.append("\nПо таймфреймам:")
        lines.extend(
            f"• {row.key}: {row.total_predictions} "
            + (f"({row.win_rate:.0f}% win)" if row.win_rate is not None else "(нет оценённых)")
            for row in report.by_tf
        )

    lines.append("\nAI-прогнозы — вероятностный анализ, а не гарантия результата.")
    return "\n".join(lines)


async def _get_report() -> AccuracyReport:
    redis = get_redis()
    report = await get_cached_accuracy_report(redis)
    if report is None:
        async with async_session_factory() as session:
            report = await compute_accuracy_report(session)
    return report


@router.message(F.text == BTN_ACCURACY)
async def on_accuracy_button(message: Message) -> None:
    await message.answer(_render_report(await _get_report()))


@router.callback_query(F.data == CB_ACCURACY)
async def on_accuracy(callback: CallbackQuery) -> None:
    await callback.message.answer(_render_report(await _get_report()))
    await callback.answer()
