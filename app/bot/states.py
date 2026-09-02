from aiogram.fsm.state import State, StatesGroup


class Onboarding(StatesGroup):
    """3-step onboarding per TZ section 4.4. Every step is skippable."""

    trading_style = State()
    risk_profile = State()
    preferred_markets = State()


class AlertCreation(StatesGroup):
    """Price alert creation flow (TZ section 13 step 9)."""

    symbol = State()
    direction = State()
    price = State()
