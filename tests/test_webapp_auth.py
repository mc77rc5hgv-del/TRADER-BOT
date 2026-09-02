import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

import pytest

from app.webapp.auth import InvalidInitDataError, validate_init_data

BOT_TOKEN = "123456:FAKE_TEST_TOKEN"


def _make_init_data(bot_token: str = BOT_TOKEN, auth_date: int | None = None, **extra_fields) -> str:
    fields = {
        "query_id": "AAABBBCCC",
        "user": json.dumps({"id": 42, "first_name": "Test", "username": "tester"}),
        "auth_date": str(auth_date if auth_date is not None else int(time.time())),
    }
    fields.update(extra_fields)

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(fields.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    computed_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    fields["hash"] = computed_hash
    return urlencode(fields)


def test_valid_init_data_is_accepted() -> None:
    init_data = _make_init_data()
    result = validate_init_data(init_data, BOT_TOKEN)

    assert result["user"]["id"] == 42
    assert result["user"]["username"] == "tester"


def test_empty_init_data_rejected() -> None:
    with pytest.raises(InvalidInitDataError, match="empty"):
        validate_init_data("", BOT_TOKEN)


def test_missing_hash_rejected() -> None:
    init_data = "query_id=AAA&auth_date=123"
    with pytest.raises(InvalidInitDataError, match="hash"):
        validate_init_data(init_data, BOT_TOKEN)


def test_tampered_field_rejected() -> None:
    init_data = _make_init_data()
    tampered = init_data.replace("query_id=AAABBBCCC", "query_id=TAMPERED")
    with pytest.raises(InvalidInitDataError, match="hash mismatch"):
        validate_init_data(tampered, BOT_TOKEN)


def test_wrong_bot_token_rejected() -> None:
    init_data = _make_init_data(bot_token=BOT_TOKEN)
    with pytest.raises(InvalidInitDataError, match="hash mismatch"):
        validate_init_data(init_data, "999999:DIFFERENT_TOKEN")


def test_expired_init_data_rejected() -> None:
    old_auth_date = int(time.time()) - 100_000
    init_data = _make_init_data(auth_date=old_auth_date)
    with pytest.raises(InvalidInitDataError, match="expired"):
        validate_init_data(init_data, BOT_TOKEN, max_age_seconds=86400)


def test_fresh_init_data_within_max_age_accepted() -> None:
    recent_auth_date = int(time.time()) - 100
    init_data = _make_init_data(auth_date=recent_auth_date)
    result = validate_init_data(init_data, BOT_TOKEN, max_age_seconds=86400)
    assert result["user"]["id"] == 42
