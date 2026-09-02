"""Telegram Mini App initData validation, per Telegram's documented
algorithm: https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app

The Mini App must never trust a client-supplied user id without this check —
initData is the only proof that a request actually came from Telegram."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl


class InvalidInitDataError(Exception):
    """initData failed validation - callers must not proceed with it."""


def validate_init_data(init_data: str, bot_token: str, max_age_seconds: int = 86400) -> dict:
    """Returns the parsed initData fields (with "user" JSON-decoded) once
    the HMAC signature and freshness check both pass. Raises
    InvalidInitDataError otherwise."""
    if not init_data:
        raise InvalidInitDataError("empty initData")

    data = dict(parse_qsl(init_data, keep_blank_values=True))

    received_hash = data.pop("hash", None)
    if not received_hash:
        raise InvalidInitDataError("missing hash")

    data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(data.items()))

    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    computed_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(computed_hash, received_hash):
        raise InvalidInitDataError("hash mismatch")

    auth_date = data.get("auth_date")
    if auth_date is None:
        raise InvalidInitDataError("missing auth_date")
    try:
        age_seconds = time.time() - int(auth_date)
    except ValueError as exc:
        raise InvalidInitDataError("invalid auth_date") from exc
    if age_seconds > max_age_seconds:
        raise InvalidInitDataError("initData expired")

    if "user" in data:
        try:
            data["user"] = json.loads(data["user"])
        except json.JSONDecodeError as exc:
            raise InvalidInitDataError("invalid user JSON") from exc

    return data
