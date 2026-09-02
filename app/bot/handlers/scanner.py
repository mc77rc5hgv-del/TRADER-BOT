"""Scanner digest (TZ sections 4.2, 13 step 10): reads the cached results
the background job (app/scanner/worker.py) computed — never scans on
demand, so this handler is cheap regardless of how many users hit it at
once."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards import CB_SCANNER
from app.core.redis import get_redis
from app.scanner.schemas import ScannerEntry
from app.scanner.service import get_cached_scan_results

router = Router(name="scanner")

TOP_N = 5
NOT_READY_TEXT = (
    "🔥 Scanner ещё не успел посчитать сетапы — фоновая джоба обновляет их "
    "каждые 10 минут, зайдите чуть позже."
)


def _direction_label(entry: ScannerEntry) -> str:
    if entry.direction == "long":
        return "LONG"
    if entry.direction == "short":
        return "SHORT"
    return "NEUTRAL"


def _format_entry(entry: ScannerEntry) -> str:
    base_symbol = entry.symbol.split("USDT")[0]
    rr = f"R:R 1:{entry.risk_reward:g}" if entry.risk_reward else ""
    return f"{base_symbol}   {_direction_label(entry)}   {entry.confidence:.0f}%   {rr}".rstrip()


async def _render_digest() -> str:
    redis = get_redis()
    entries, _updated_at = await get_cached_scan_results(redis)
    if not entries:
        return NOT_READY_TEXT

    directional = [e for e in entries if e.direction in ("long", "short")]
    directional.sort(key=lambda e: e.confidence, reverse=True)
    top = directional[:TOP_N]

    if not top:
        return "🔥 Сейчас нет активов с явным направленным перевесом."

    lines = [f"{i}. {_format_entry(e)}" for i, e in enumerate(top, start=1)]
    return "🔥 Лучшие сетапы сейчас:\n" + "\n".join(lines)


@router.message(Command("scanner"))
async def cmd_scanner(message: Message) -> None:
    await message.answer(await _render_digest())


@router.callback_query(F.data == CB_SCANNER)
async def on_scanner(callback: CallbackQuery) -> None:
    await callback.message.answer(await _render_digest())
    await callback.answer()
