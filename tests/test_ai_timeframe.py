import pytest

from app.ai.timeframe import normalize_tf_guess


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("15m", "15m"),
        ("15M", "15m"),
        ("M15", "15m"),
        ("1H", "1h"),
        ("H1", "1h"),
        ("60m", "1h"),
        ("4h", "4h"),
        ("H4", "4h"),
        ("1D", "1d"),
        ("Daily", "1d"),
        (" 1h ", "1h"),
    ],
)
def test_normalize_known_tf(raw: str, expected: str) -> None:
    assert normalize_tf_guess(raw) == expected


@pytest.mark.parametrize("raw", [None, "", "weekly", "3h", "xyz"])
def test_normalize_unknown_tf_returns_none(raw: str | None) -> None:
    assert normalize_tf_guess(raw) is None
