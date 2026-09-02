# TRADE AI

AI-платформа для трейдинга внутри Telegram (бот + Mini App). Продуктовое и
техническое ТЗ MVP — в [`docs/TZ_MVP.md`](docs/TZ_MVP.md).

Текущий этап: **Phase 1, шаг 1 — скелет и инфраструктура** (см. раздел 13 ТЗ).

## Стек

- Backend/API: FastAPI
- Bot: aiogram 3
- DB: PostgreSQL (async, SQLAlchemy 2.0) + Alembic
- Cache/queues: Redis
- Mini App frontend: появится на шаге 7 (пока не реализован)

## Быстрый старт (dev)

```bash
cp .env.example .env
# заполнить TELEGRAM_BOT_TOKEN в .env

docker compose up -d      # Postgres + Redis

pip install -e ".[dev]"
alembic upgrade head

# API
uvicorn app.main:app --reload

# Bot (в отдельном терминале)
python -m app.bot.main
```

## Тесты

```bash
pytest
ruff check .
```

## Структура репозитория

```
app/
  config.py          # настройки (pydantic-settings)
  main.py            # FastAPI приложение
  db/                 # Base, session, сборка всех моделей для Alembic
  market/             # Market Data Engine (нормализация символов и т.д.)
  ai/                  # Prediction Ledger, AI request accounting
  alerts/              # модель алертов
  billing/             # подписки (Free/Pro)
  users/               # пользователи, watchlist
  bot/                 # aiogram: хендлеры, клавиатуры, FSM онбординга
migrations/            # Alembic
docs/TZ_MVP.md          # полное ТЗ
```

Границы модулей (`market/`, `ai/`, `alerts/`, `billing/`, `users/`) —
задел на будущее выделение в отдельные сервисы (Phase 5 ТЗ), в MVP это
единый modular monolith.
