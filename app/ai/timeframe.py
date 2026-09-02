"""Free-text timeframe labels (as read off a chart screenshot, e.g. "15M",
"M15", "1H") mapped to the canonical timeframe vocabulary in
app.market.schemas.ALLOWED_TIMEFRAMES."""

from __future__ import annotations

DEFAULT_TF = "1h"

_TF_ALIASES: dict[str, str] = {
    "1m": "1m",
    "m1": "1m",
    "5m": "5m",
    "m5": "5m",
    "15m": "15m",
    "m15": "15m",
    "1h": "1h",
    "h1": "1h",
    "60m": "1h",
    "4h": "4h",
    "h4": "4h",
    "240m": "4h",
    "1d": "1d",
    "d1": "1d",
    "daily": "1d",
    "1day": "1d",
}


def normalize_tf_guess(raw: str | None) -> str | None:
    """None when the guess can't be confidently mapped — callers should
    fall back to DEFAULT_TF rather than guess further."""
    if not raw:
        return None
    key = raw.strip().lower().replace(" ", "")
    return _TF_ALIASES.get(key)
