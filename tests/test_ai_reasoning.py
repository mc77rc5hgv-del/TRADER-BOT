from app.ai.provider import LLMProvider, LLMUsage
from app.ai.reasoning import DISCLAIMER, analyze
from app.ai.render import render_text
from app.ai.schemas import AnalysisNarrative, WhyBullet
from app.probability.schemas import ProbabilityResult
from app.risk.schemas import RiskLevels
from app.ta.schemas import TechnicalSnapshot


class FakeLLMProvider(LLMProvider):
    """No network calls — returns a canned narrative and records what it
    was asked, so tests can assert the prompt never leaks unrelated data."""

    def __init__(self, narrative: AnalysisNarrative) -> None:
        self.narrative = narrative
        self.last_system_prompt: str | None = None
        self.last_user_prompt: str | None = None

    async def generate_structured(self, system_prompt, user_prompt, response_model):
        self.last_system_prompt = system_prompt
        self.last_user_prompt = user_prompt
        assert response_model is AnalysisNarrative
        return self.narrative, LLMUsage(model="fake-model", input_tokens=120, output_tokens=40)

    async def extract_chart_info(self, image_bytes, media_type):
        raise NotImplementedError("not exercised by these tests")


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
        risk_level="medium",
    )


async def test_analyze_uses_deterministic_numbers_not_llm() -> None:
    narrative = AnalysisNarrative(
        why=[
            WhyBullet(sign="+", text="HTF структура бычья"),
            WhyBullet(sign="-", text="Рядом сопротивление"),
        ]
    )
    provider = FakeLLMProvider(narrative)

    result, usage = await analyze(
        provider, "BTCUSDT@binance", "4h", _snapshot(), _probability(), _risk()
    )

    # every number comes from risk/probability, never from the (fake) LLM
    assert result.entry_low == 111800.0
    assert result.entry_high == 112300.0
    assert result.invalidation == 110950.0
    assert result.targets == [113600.0, 114900.0]
    assert result.scenarios is not None
    assert result.scenarios.primary_confidence == 64.0
    assert result.why == narrative.why
    assert result.disclaimer == DISCLAIMER
    assert usage.model == "fake-model"


async def test_analyze_neutral_direction_has_no_trade_setup() -> None:
    neutral_probability = ProbabilityResult(direction="neutral", confidence=35.0, factors={})
    provider = FakeLLMProvider(
        AnalysisNarrative(why=[WhyBullet(sign="+", text="Без явного перевеса")])
    )

    result, _usage = await analyze(
        provider, "BTCUSDT@binance", "4h", _snapshot(), neutral_probability, None
    )

    assert result.scenarios is None
    assert result.entry_low is None
    assert result.targets is None


async def test_analyze_sends_compressed_context_not_raw_candles() -> None:
    provider = FakeLLMProvider(AnalysisNarrative(why=[WhyBullet(sign="+", text="ok")]))
    await analyze(provider, "BTCUSDT@binance", "4h", _snapshot(), _probability(), _risk())

    assert provider.last_user_prompt is not None
    assert "111800" in provider.last_user_prompt  # price is in there
    assert "candle" not in provider.last_user_prompt.lower()  # no raw OHLCV series


async def test_analyze_gracefully_degrades_when_llm_is_unavailable() -> None:
    class FailingProvider(FakeLLMProvider):
        async def generate_structured(self, system_prompt, user_prompt, response_model):
            raise RuntimeError("provider unavailable")

    result, usage = await analyze(
        FailingProvider(AnalysisNarrative(why=[])),
        "BTCUSDT@binance",
        "4h",
        _snapshot(),
        _probability(),
        _risk(),
    )

    assert result.entry_low == 111800.0
    assert result.scenarios is not None
    assert "временно недоступно" in result.why[0].text
    assert usage.model == "degraded-no-llm"
    assert usage.input_tokens == 0


def test_render_text_always_includes_disclaimer() -> None:
    narrative = [WhyBullet(sign="+", text="test")]
    from app.ai.schemas import AnalysisResult, ScenarioSplit

    result = AnalysisResult(
        symbol="BTCUSDT@binance",
        tf="4h",
        structure_bias="bullish",
        scenarios=ScenarioSplit(
            primary_direction="long",
            primary_confidence=64.0,
            opposite_confidence=27.0,
            neutral_confidence=9.0,
        ),
        entry_low=111800.0,
        entry_high=112300.0,
        invalidation=110950.0,
        targets=[113600.0, 114900.0],
        risk_reward=1.5,
        why=narrative,
        disclaimer=DISCLAIMER,
    )

    text = render_text(result)

    assert DISCLAIMER in text
    assert "LONG" in text
    assert "64%" in text
    assert "110950" in text


def test_render_text_neutral_scenario_has_no_entry() -> None:
    from app.ai.schemas import AnalysisResult

    result = AnalysisResult(
        symbol="BTCUSDT@binance",
        tf="4h",
        structure_bias="neutral",
        scenarios=None,
        entry_low=None,
        entry_high=None,
        invalidation=None,
        targets=None,
        risk_reward=None,
        why=[WhyBullet(sign="+", text="Без явного перевеса")],
        disclaimer=DISCLAIMER,
    )

    text = render_text(result)
    assert DISCLAIMER in text
    assert "LONG" not in text
    assert "SHORT" not in text
