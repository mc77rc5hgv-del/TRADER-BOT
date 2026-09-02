"""Symbol normalization (TZ section 6.5).

Maps human-readable aliases ("btc", "биткоин", "BTC/USDT") to a canonical
internal symbol of the form "{BASE}{QUOTE}@{EXCHANGE}", e.g. "BTCUSDT@binance".
Used by both the vision pipeline (screenshot analysis) and the text intent
router so the rest of the system only ever deals with canonical symbols.
"""

from __future__ import annotations

DEFAULT_EXCHANGE = "binance"
DEFAULT_QUOTE = "USDT"

_QUOTE_ALIASES: dict[str, str] = {
    "usdt": "USDT",
    "usd": "USDT",
    "usdc": "USDT",
    "tether": "USDT",
}

_BASE_ALIASES: dict[str, str] = {
    # canonical tickers map to themselves
    "btc": "BTC",
    "eth": "ETH",
    "sol": "SOL",
    "xrp": "XRP",
    "bnb": "BNB",
    "doge": "DOGE",
    "ada": "ADA",
    "avax": "AVAX",
    "ton": "TON",
    "trx": "TRX",
    "dot": "DOT",
    "ltc": "LTC",
    "link": "LINK",
    "matic": "MATIC",
    "atom": "ATOM",
    "near": "NEAR",
    "apt": "APT",
    "arb": "ARB",
    "op": "OP",
    "sui": "SUI",
    "pepe": "PEPE",
    "shib": "SHIB",
    # english full names
    "bitcoin": "BTC",
    "ethereum": "ETH",
    "solana": "SOL",
    "ripple": "XRP",
    "binance coin": "BNB",
    "dogecoin": "DOGE",
    "cardano": "ADA",
    "avalanche": "AVAX",
    "toncoin": "TON",
    "tron": "TRX",
    "polkadot": "DOT",
    "litecoin": "LTC",
    "chainlink": "LINK",
    "polygon": "MATIC",
    "cosmos": "ATOM",
    "aptos": "APT",
    "arbitrum": "ARB",
    "optimism": "OP",
    "shiba": "SHIB",
    "shiba inu": "SHIB",
    # informal russian names
    "биткоин": "BTC",
    "биток": "BTC",
    "битки": "BTC",
    "эфир": "ETH",
    "эфириум": "ETH",
    "солана": "SOL",
    "рипл": "XRP",
    "доге": "DOGE",
    "додж": "DOGE",
    "кардано": "ADA",
    "аваланч": "AVAX",
    "трон": "TRX",
    "полкадот": "DOT",
    "лайткоин": "LTC",
    "чейнлинк": "LINK",
    "полигон": "MATIC",
    "космос": "ATOM",
    "ниар": "NEAR",
    "аптос": "APT",
    "арбитрум": "ARB",
    "оптимизм": "OP",
    "суи": "SUI",
    "пепе": "PEPE",
    "шиба": "SHIB",
}


def normalize_symbol(raw: str) -> str | None:
    """Resolve a free-form symbol reference to its canonical form.

    Returns None when the input cannot be confidently resolved — callers
    (bot handlers, vision extractor) are expected to ask the user to
    disambiguate rather than guess (TZ section 2.1, step 4).
    """
    if not raw:
        return None

    text = raw.strip().lower().lstrip("$")
    if not text:
        return None

    for sep in ("/", "-", " "):
        if sep in text:
            parts = [p for p in text.split(sep) if p]
            if len(parts) == 2:
                base_raw, quote_raw = parts
                base = _BASE_ALIASES.get(base_raw)
                if base and quote_raw in _QUOTE_ALIASES:
                    return f"{base}{_QUOTE_ALIASES[quote_raw]}@{DEFAULT_EXCHANGE}"
            break

    if text in _BASE_ALIASES:
        return f"{_BASE_ALIASES[text]}{DEFAULT_QUOTE}@{DEFAULT_EXCHANGE}"

    for quote_alias, quote_canonical in _QUOTE_ALIASES.items():
        if text.endswith(quote_alias) and len(text) > len(quote_alias):
            base_raw = text[: -len(quote_alias)]
            base = _BASE_ALIASES.get(base_raw)
            if base:
                return f"{base}{quote_canonical}@{DEFAULT_EXCHANGE}"

    return None


def split_canonical_symbol(canonical: str) -> tuple[str, str]:
    """Split a canonical symbol ("BTCUSDT@binance") into (pair, exchange)."""
    pair, _, exchange = canonical.partition("@")
    return pair, exchange or DEFAULT_EXCHANGE
