import json

from app.ai.context import build_context
from app.ai.prompt import build_user_prompt
from app.probability.schemas import ProbabilityResult
from app.risk.schemas import RiskLevels
from app.ta.schemas import TechnicalSnapshot


def _snapshot() -> TechnicalSnapshot:
    return TechnicalSnapshot(
        price=111800.0,
        rsi=61.0,
        ema20=110000.0,
        ema50=108000.0,
        ema200=None,
        atr=1200.0,
        volume_trend="rising",
        structure_bias="bullish",
        nearest_support=109800.0,
        nearest_resistance=114000.0,
    )


def _probability() -> ProbabilityResult:
    return ProbabilityResult(direction="long", confidence=64.0, factors={"market_structure": 0.3})


def _risk() -> RiskLevels:
    return RiskLevels(
        direction="long",
        entry_low=111800.0,
        entry_high=112300.0,
        invalidation=110950.0,
        targets=[113600.0, 114900.0],
        risk_reward=1.5,
    )


def test_context_carries_only_deterministic_numbers() -> None:
    context = build_context("BTCUSDT@binance", "4h", _snapshot(), _probability(), _risk())

    assert context.price == 111800.0
    assert context.entry_low == 111800.0
    assert context.invalidation == 110950.0
    assert context.targets == [113600.0, 114900.0]
    assert context.scenarios is not None
    assert context.scenarios.primary_confidence == 64.0


def test_context_without_risk_has_no_trade_levels() -> None:
    neutral_probability = ProbabilityResult(direction="neutral", confidence=35.0, factors={})
    context = build_context("BTCUSDT@binance", "4h", _snapshot(), neutral_probability, None)

    assert context.entry_low is None
    assert context.invalidation is None
    assert context.targets is None
    assert context.scenarios is None


def test_user_prompt_is_valid_json_and_omits_none_fields() -> None:
    neutral_probability = ProbabilityResult(direction="neutral", confidence=35.0, factors={})
    context = build_context("BTCUSDT@binance", "4h", _snapshot(), neutral_probability, None)

    prompt = build_user_prompt(context)
    payload = json.loads(prompt)

    assert payload["symbol"] == "BTCUSDT@binance"
    assert "entry_low" not in payload
    assert "scenarios" not in payload
