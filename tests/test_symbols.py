import pytest

from app.market.symbols import normalize_symbol, split_canonical_symbol, suggest_symbols


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("BTC", "BTCUSDT@binance"),
        ("btc", "BTCUSDT@binance"),
        ("$BTC", "BTCUSDT@binance"),
        ("BTC/USDT", "BTCUSDT@binance"),
        ("btc-usdt", "BTCUSDT@binance"),
        ("btc usdt", "BTCUSDT@binance"),
        ("BTCUSDT", "BTCUSDT@binance"),
        ("bitcoin", "BTCUSDT@binance"),
        ("биткоин", "BTCUSDT@binance"),
        ("эфир", "ETHUSDT@binance"),
        ("solana", "SOLUSDT@binance"),
        ("ripple", "XRPUSDT@binance"),
    ],
)
def test_normalize_known_symbols(raw: str, expected: str) -> None:
    assert normalize_symbol(raw) == expected


@pytest.mark.parametrize("raw", ["", "   ", "not a real asset", "xyzabc123"])
def test_normalize_unknown_returns_none(raw: str) -> None:
    assert normalize_symbol(raw) is None


def test_split_canonical_symbol() -> None:
    assert split_canonical_symbol("BTCUSDT@binance") == ("BTCUSDT", "binance")
    assert split_canonical_symbol("BTCUSDT@bybit") == ("BTCUSDT", "bybit")


def test_suggest_symbols_close_typo() -> None:
    suggestions = suggest_symbols("BTX")
    assert "BTCUSDT@binance" in suggestions


def test_suggest_symbols_strips_quote_suffix() -> None:
    suggestions = suggest_symbols("BTCUSDT")
    assert suggestions[0] == "BTCUSDT@binance"


def test_suggest_symbols_empty_input() -> None:
    assert suggest_symbols(None) == []
    assert suggest_symbols("") == []


def test_suggest_symbols_no_close_match() -> None:
    assert suggest_symbols("zzzzzzzzzz") == []
