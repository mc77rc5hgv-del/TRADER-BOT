"""Shared bot reply text that depends on more than one handler module
(TZ section 8) — kept here rather than duplicated in each handler."""

from __future__ import annotations


def quota_exceeded_text(limit: int) -> str:
    return (
        f"Вы использовали дневной лимит AI-анализов на бесплатном тарифе ({limit}/день). "
        "Оформите PRO (кнопка «💳 Подписка» в меню), чтобы увеличить лимит."
    )
