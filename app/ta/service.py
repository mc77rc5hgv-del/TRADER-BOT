from __future__ import annotations

from app.market.schemas import Candle
from app.ta.indicators import atr_latest, ema_latest, rsi_latest, volume_trend
from app.ta.schemas import TechnicalSnapshot
from app.ta.structure import classify_structure, nearest_levels


def analyze(candles: list[Candle]) -> TechnicalSnapshot:
    if not candles:
        raise ValueError("Cannot analyze an empty candle series")

    closes = [c.close for c in candles]
    current_price = closes[-1]
    support, resistance = nearest_levels(candles, current_price)

    return TechnicalSnapshot(
        price=current_price,
        rsi=rsi_latest(closes),
        ema20=ema_latest(closes, 20),
        ema50=ema_latest(closes, 50),
        ema200=ema_latest(closes, 200),
        atr=atr_latest(candles),
        volume_trend=volume_trend(candles),
        structure_bias=classify_structure(candles),
        nearest_support=support,
        nearest_resistance=resistance,
    )
