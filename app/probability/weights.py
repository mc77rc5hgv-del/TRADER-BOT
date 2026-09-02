"""Factor weights for the MVP Probability Engine (TZ section 2.4). Kept as a
plain module-level dict, not hardcoded inline in the scoring logic, so it can
move to a config file and be retrospectively tuned against the Prediction
Ledger (TZ section 6.6) without touching the scoring code."""

DEFAULT_WEIGHTS: dict[str, float] = {
    "market_structure": 0.30,
    "momentum": 0.20,
    "volume": 0.15,
    "support_resistance": 0.20,
    "funding_oi": 0.15,
}

MIN_CONFIDENCE = 35.0
MAX_CONFIDENCE = 85.0
