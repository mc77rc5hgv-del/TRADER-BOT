from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    WebAppInfo,
)

from app.config import get_settings

settings = get_settings()

# Callback data for the main menu (TZ section 4.1)
CB_AI_ANALYSIS = "menu:ai_analysis"
CB_SCANNER = "menu:scanner"
CB_ALERTS = "menu:alerts"
CB_BILLING = "menu:billing"
CB_ACCURACY = "menu:accuracy"

# Callback data for the subscription screen (TZ section 8)
CB_BILLING_BUY = "billing:buy"

# Callback data for onboarding (TZ section 4.4)
CB_STYLE_PREFIX = "onboarding:style:"
CB_RISK_PREFIX = "onboarding:risk:"
CB_MARKETS_PREFIX = "onboarding:markets:"
CB_SKIP = "onboarding:skip"

# Callback data for alert creation (TZ section 13 step 9)
CB_ALERT_NEW = "alerts:new"
CB_ALERT_DIRECTION_PREFIX = "alerts:dir:"
CB_ALERT_CANCEL = "alerts:cancel"


def main_menu_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text="✨ AI АНАЛИЗ", callback_data=CB_AI_ANALYSIS)],
    ]

    if settings.mini_app_url:
        rows.append(
            [
                InlineKeyboardButton(
                    text="📊 ОТКРЫТЬ ТЕРМИНАЛ",
                    web_app=WebAppInfo(url=settings.mini_app_url),
                )
            ]
        )

    rows.append([InlineKeyboardButton(text="🔥 ЛУЧШИЕ СЕТАПЫ", callback_data=CB_SCANNER)])
    rows.append([InlineKeyboardButton(text="🔔 АЛЕРТЫ", callback_data=CB_ALERTS)])
    rows.append([InlineKeyboardButton(text="💳 Подписка", callback_data=CB_BILLING)])
    rows.append([InlineKeyboardButton(text="📊 Точность AI", callback_data=CB_ACCURACY)])

    return InlineKeyboardMarkup(inline_keyboard=rows)


def billing_keyboard(*, show_buy_button: bool) -> InlineKeyboardMarkup:
    if not show_buy_button:
        return InlineKeyboardMarkup(inline_keyboard=[])
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="⭐ Купить PRO", callback_data=CB_BILLING_BUY)]]
    )


def alerts_list_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="+ Создать алерт", callback_data=CB_ALERT_NEW)]]
    )


def alert_direction_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Выше ⬆️", callback_data=f"{CB_ALERT_DIRECTION_PREFIX}above"
                ),
                InlineKeyboardButton(
                    text="Ниже ⬇️", callback_data=f"{CB_ALERT_DIRECTION_PREFIX}below"
                ),
            ],
            [InlineKeyboardButton(text="Отмена", callback_data=CB_ALERT_CANCEL)],
        ]
    )


def alert_cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Отмена", callback_data=CB_ALERT_CANCEL)]]
    )


def trading_style_keyboard() -> InlineKeyboardMarkup:
    options = [
        ("Scalping", "scalping"),
        ("Intraday", "intraday"),
        ("Swing", "swing"),
        ("Investing", "investing"),
    ]
    rows = [
        [InlineKeyboardButton(text=label, callback_data=f"{CB_STYLE_PREFIX}{value}")]
        for label, value in options
    ]
    rows.append([InlineKeyboardButton(text="Пропустить", callback_data=CB_SKIP)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def risk_profile_keyboard() -> InlineKeyboardMarkup:
    options = [
        ("Conservative", "conservative"),
        ("Balanced", "balanced"),
        ("Aggressive", "aggressive"),
    ]
    rows = [
        [InlineKeyboardButton(text=label, callback_data=f"{CB_RISK_PREFIX}{value}")]
        for label, value in options
    ]
    rows.append([InlineKeyboardButton(text="Пропустить", callback_data=CB_SKIP)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def preferred_markets_keyboard() -> InlineKeyboardMarkup:
    options = [
        ("BTC", "btc"),
        ("Alts", "alts"),
        ("Both", "both"),
    ]
    rows = [
        [InlineKeyboardButton(text=label, callback_data=f"{CB_MARKETS_PREFIX}{value}")]
        for label, value in options
    ]
    rows.append([InlineKeyboardButton(text="Пропустить", callback_data=CB_SKIP)])
    return InlineKeyboardMarkup(inline_keyboard=rows)
