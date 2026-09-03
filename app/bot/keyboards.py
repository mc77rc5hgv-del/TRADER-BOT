from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

# Callback data kept for backward compatibility with inline buttons already
# sent to users before the persistent reply keyboard replaced them as the
# primary navigation (TZ section 4.1) — the callback handlers still work if
# someone taps an old message, they're just no longer how new messages
# reach these screens.
CB_AI_ANALYSIS = "menu:ai_analysis"
CB_SCANNER = "menu:scanner"
CB_ALERTS = "menu:alerts"
CB_BILLING = "menu:billing"
CB_ACCURACY = "menu:accuracy"

# Persistent reply-keyboard button labels (shown below the message input,
# unlike inline keyboards which scroll away with their message) - the
# primary navigation. Mini App access lives in the chat menu button instead
# (see app/bot/main.py's set_chat_menu_button), not duplicated here.
BTN_AI_ANALYSIS = "✨ AI анализ"
BTN_SCANNER = "🔥 Сетапы"
BTN_ALERTS = "🔔 Алерты"
BTN_ACCURACY = "📊 Точность AI"
BTN_BILLING = "💳 Подписка"

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


def main_reply_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_AI_ANALYSIS), KeyboardButton(text=BTN_SCANNER)],
            [KeyboardButton(text=BTN_ALERTS), KeyboardButton(text=BTN_ACCURACY)],
            [KeyboardButton(text=BTN_BILLING)],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


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
