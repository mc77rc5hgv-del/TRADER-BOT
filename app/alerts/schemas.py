from typing import Literal

from pydantic import BaseModel


class PriceAlertCondition(BaseModel):
    """The only alert condition shape in v0 (TZ section 13 step 9:
    "ценовые алерты (простое условие)"). Stored verbatim in Alert.condition."""

    operator: Literal["above", "below"]
    price: float
