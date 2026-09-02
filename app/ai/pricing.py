"""$/1M-token pricing per model, for the internal cost/DAU dashboard (TZ
section 11). Anthropic first-party rates, cached as of the claude-api skill
(2026-06-24) — update alongside app.config.Settings.llm_model."""

from __future__ import annotations

# model -> (input $/1M tokens, output $/1M tokens)
PRICING_USD_PER_MILLION_TOKENS: dict[str, tuple[float, float]] = {
    "claude-opus-5": (5.00, 25.00),
    "claude-sonnet-5": (2.00, 10.00),
    "claude-haiku-4-5": (1.00, 5.00),
}


def estimate_cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    input_rate, output_rate = PRICING_USD_PER_MILLION_TOKENS.get(model, (0.0, 0.0))
    return (input_tokens * input_rate + output_tokens * output_rate) / 1_000_000
