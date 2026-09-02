from app.ai.models import Prediction
from app.alerts.models import Alert
from app.billing.models import Subscription
from app.users.models import User


def test_orm_enum_values_match_lowercase_postgres_schema() -> None:
    expected = {
        Subscription.__table__.c.tier.type: ["free", "pro"],
        Subscription.__table__.c.status.type: ["active", "expired", "canceled"],
        Alert.__table__.c.status.type: ["active", "triggered", "expired"],
        Prediction.__table__.c.direction.type: ["long", "short", "neutral"],
        User.__table__.c.trading_style.type: ["scalping", "intraday", "swing", "investing"],
    }

    for enum_type, values in expected.items():
        assert enum_type.enums == values
