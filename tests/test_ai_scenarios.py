from app.ai.scenarios import split_scenarios
from app.probability.schemas import ProbabilityResult


def test_neutral_direction_has_no_scenario_split() -> None:
    result = ProbabilityResult(direction="neutral", confidence=35.0, factors={})
    assert split_scenarios(result) is None


def test_long_scenarios_sum_to_100() -> None:
    result = ProbabilityResult(direction="long", confidence=64.0, factors={})
    scenarios = split_scenarios(result)

    assert scenarios is not None
    assert scenarios.primary_direction == "long"
    assert scenarios.primary_confidence == 64.0
    total = scenarios.primary_confidence + scenarios.opposite_confidence + scenarios.neutral_confidence
    assert round(total, 1) == 100.0


def test_matches_tz_worked_example() -> None:
    # TZ section 4.3's worked example: 64% / 27% / 9%.
    result = ProbabilityResult(direction="long", confidence=64.0, factors={})
    scenarios = split_scenarios(result)

    assert scenarios is not None
    assert scenarios.opposite_confidence == 27.0
    assert scenarios.neutral_confidence == 9.0


def test_short_direction_preserved() -> None:
    result = ProbabilityResult(direction="short", confidence=58.0, factors={})
    scenarios = split_scenarios(result)

    assert scenarios is not None
    assert scenarios.primary_direction == "short"
