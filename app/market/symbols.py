"""Symbol normalization (TZ section 6.5).

Maps human-readable aliases ("btc", "биткоин", "BTC/USDT") to a canonical
internal symbol of the form "{BASE}{QUOTE}@{EXCHANGE}", e.g. "BTCUSDT@binance".
Used by both the vision pipeline (screenshot analysis) and the text intent
router so the rest of the system only ever deals with canonical symbols.
"""

from __future__ import annotations

import difflib

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

# Canonical base tickers only (dedup of _BASE_ALIASES' values), used to
# suggest close matches when a raw guess doesn't resolve confidently -
# e.g. a noisy vision-extracted ticker (TZ section 2.1, step 4).
KNOWN_BASE_TICKERS: frozenset[str] = frozenset(_BASE_ALIASES.values())

# Every canonical "{BASE}{QUOTE}" pair this function can produce - used to
# recognize a string that's already in canonical form (see the "@" branch
# below), since DEFAULT_QUOTE is the only quote currency the canonical form
# ever uses.
_KNOWN_CANONICAL_PAIRS: frozenset[str] = frozenset(
    f"{base}{DEFAULT_QUOTE}" for base in KNOWN_BASE_TICKERS
)


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

    if "@" in text:
        # Idempotency: a string already in this function's own canonical
        # form ("BTCUSDT@binance") passes through unchanged instead of
        # falling through to the alias lookups below, which don't recognize
        # it. Needed by callers that only have a previously-canonicalized
        # symbol on hand (e.g. the accuracy evaluation job re-fetching
        # market state for a stored Prediction).
        pair, _, exchange = text.partition("@")
        if exchange == DEFAULT_EXCHANGE and pair.upper() in _KNOWN_CANONICAL_PAIRS:
            return f"{pair.upper()}@{exchange}"
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


def suggest_symbols(raw: str | None, limit: int = 3) -> list[str]:
    """Close-match suggestions for a raw guess that didn't resolve
    confidently — used for the "did you mean" buttons after a screenshot's
    ticker can't be read exactly (TZ section 2.1, step 4)."""
    if not raw:
        return []

    token = raw.strip().upper().split("/")[0].split("-")[0].split(" ")[0]
    for quote in ("USDT", "USDC", "USD"):
        if token.endswith(quote) and len(token) > len(quote):
            token = token[: -len(quote)]
            break

    matches = difflib.get_close_matches(token, KNOWN_BASE_TICKERS, n=limit, cutoff=0.4)
    return [f"{base}{DEFAULT_QUOTE}@{DEFAULT_EXCHANGE}" for base in matches]
