import pytest

from app.alerts.models import Alert, AlertType
from app.alerts.service import describe_condition, evaluate_alert, evaluate_price_condition


def _price_alert(**overrides) -> Alert:
    defaults = {
        "id": 1,
        "user_id": 1,
        "symbol": "BTC",
        "type": AlertType.PRICE,
        "condition": {"operator": "above", "price": 100.0},
    }
    defaults.update(overrides)
    return Alert(**defaults)


def test_above_triggers_when_price_reaches_or_exceeds() -> None:
    condition = {"operator": "above", "price": 100.0}
    assert evaluate_price_condition(condition, 100.0) is True
    assert evaluate_price_condition(condition, 101.0) is True
    assert evaluate_price_condition(condition, 99.9) is False


def test_below_triggers_when_price_reaches_or_drops_under() -> None:
    condition = {"operator": "below", "price": 100.0}
    assert evaluate_price_condition(condition, 100.0) is True
    assert evaluate_price_condition(condition, 99.0) is True
    assert evaluate_price_condition(condition, 100.1) is False


def test_evaluate_alert_delegates_to_price_condition() -> None:
    alert = _price_alert(condition={"operator": "above", "price": 50.0})
    assert evaluate_alert(alert, 60.0) is True
    assert evaluate_alert(alert, 40.0) is False


def test_evaluate_alert_rejects_non_price_types() -> None:
    alert = _price_alert(type=AlertType.RSI, condition={"operator": "above", "price": 50.0})
    with pytest.raises(ValueError, match="price alerts"):
        evaluate_alert(alert, 60.0)


def test_describe_condition() -> None:
    assert describe_condition({"operator": "above", "price": 111800}) == "цена выше 111800"
    assert describe_condition({"operator": "below", "price": 95.5}) == "цена ниже 95.5"
