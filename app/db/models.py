"""Import hub so that Base.metadata is aware of every table before Alembic
autogenerate or create_all() runs. Import this module (not the individual
per-domain model modules) wherever the full schema needs to be registered."""

from app.ai.models import AIRequest, Prediction, Screenshot  # noqa: F401
from app.alerts.models import Alert  # noqa: F401
from app.billing.models import Subscription  # noqa: F401
from app.db.base import Base  # noqa: F401
from app.users.models import User, WatchlistItem  # noqa: F401
