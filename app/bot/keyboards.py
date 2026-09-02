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

# Callback data for onboarding (TZ section 4.4)
CB_STYLE_PREFIX = "onboarding:style:"
CB_RISK_PREFIX = "onboarding:risk:"
CB_MARKETS_PREFIX = "onboarding:markets:"
CB_SKIP = "onboarding:skip"


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

    return InlineKeyboardMarkup(inline_keyboard=rows)


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
