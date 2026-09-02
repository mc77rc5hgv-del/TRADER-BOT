"""Alert evaluation (TZ section 13 step 9). Pure functions, no I/O — the
worker (app/alerts/worker.py) supplies the current price and handles
persistence/delivery."""

from __future__ import annotations

from app.alerts.models import Alert, AlertType
from app.alerts.schemas import PriceAlertCondition

FREE_TIER_ACTIVE_ALERT_LIMIT = 3


def evaluate_price_condition(condition: dict, current_price: float) -> bool:
    parsed = PriceAlertCondition.model_validate(condition)
    if parsed.operator == "above":
        return current_price >= parsed.price
    return current_price <= parsed.price


def evaluate_alert(alert: Alert, current_price: float) -> bool:
    if alert.type != AlertType.PRICE:
        raise ValueError(f"evaluate_alert only supports price alerts in v0 (got {alert.type})")
    return evaluate_price_condition(alert.condition, current_price)


def describe_condition(condition: dict) -> str:
    parsed = PriceAlertCondition.model_validate(condition)
    direction = "выше" if parsed.operator == "above" else "ниже"
    return f"цена {direction} {parsed.price:g}"
