# TRADE AI

AI-платформа для трейдинга внутри Telegram (бот + Mini App). Продуктовое и
техническое ТЗ MVP — в [`docs/TZ_MVP.md`](docs/TZ_MVP.md).

Текущий этап: **Phase 1, шаг 4 — AI Reasoning Layer** (см. раздел 13 ТЗ).

## Стек

- Backend/API: FastAPI
- Bot: aiogram 3
- DB: PostgreSQL (async, SQLAlchemy 2.0) + Alembic
- Cache/queues: Redis
- LLM: Anthropic Claude (`claude-opus-5` по умолчанию) через provider-agnostic интерфейс
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

# Live-цены через WS (в отдельном терминале, опционально для dev)
python -m app.market.ws_worker
```

## Market Data Engine

`GET /market/{symbol}/state?tf=1h` — вернёт нормализованный `MarketState`
(тикер + свечи) для распознанного символа. `symbol` принимает любой алиас,
который понимает `app/market/symbols.py` (`BTC`, `btc/usdt`, `биткоин`, ...).
Результат кэшируется в Redis на `MARKET_CACHE_TTL_SECONDS` (по умолчанию 60с)
— параллельные запросы разных пользователей по одному символу переиспользуют
один и тот же fetch к Binance (TZ раздел 5.3).

`app/market/ws_worker.py` — отдельный процесс с одним общим WS-соединением к
Binance (topN ликвидных символов), который пишет live-цены в Redis-хэш
`ticker:live`. Это не блокирует HTTP API и не открывает соединение на
каждого пользователя (TZ разделы 5.1, 54).

## Technical Analysis / Probability / Risk engines

Три чистых, детерминированных модуля без единого обращения к LLM (TZ раздел
48 — "AI не должен придумывать рынок"):

- `app/ta/` — индикаторы (RSI, EMA20/50/200, ATR, тренд объёма) и структура
  рынка (свинг-хаи/лоу, HH/HL/LH/LL, ближайшие support/resistance) поверх
  списка свечей из Market Data Engine. `app/ta/service.py:analyze()` собирает
  всё в один `TechnicalSnapshot`.
- `app/probability/` — взвешенная сумма факторов (структура 30%, моментум
  20%, объём 15%, S/R 20%, funding/OI 15% когда доступен — веса и границы
  confidence вынесены в `app/probability/weights.py`) с sigmoid-калибровкой
  в диапазон 35–85% confidence (TZ раздел 2.4).
- `app/risk/` — на основе `TechnicalSnapshot` и выбранного направления
  считает entry zone, invalidation (ATR-фолбэк или ближайший
  support/resistance — берётся более тесный вариант) и 2 таргета на 1.5R/3R.

Все три модуля покрыты unit-тестами на синтетических сериях свечей
(zigzag-тренды и боковик из `tests/factories.py`), без обращения к сети или БД.

## AI Reasoning Layer

LLM подключается последним звеном и никогда не считает цифры сам (TZ раздел 7):

- `app/ai/provider.py` — `LLMProvider` — provider-agnostic интерфейс
  (`generate_structured(system, user, response_model) -> (parsed, usage)`);
  `AnthropicProvider` — реализация на `AsyncAnthropic().messages.parse()` со
  structured output. Второй провайдер подключается без изменения остального кода.
- `app/ai/scenarios.py` — детерминированный (не LLM) сплит вероятности на
  основной/альтернативный/нейтральный сценарий, сумма всегда 100% (TZ 4.3).
- `app/ai/context.py` — собирает сжатый JSON (`AnalysisContext`) из
  `TechnicalSnapshot` + `ProbabilityResult` + `RiskLevels` — без сырых свечей.
- `app/ai/prompt.py` — системный промпт прямым текстом запрещает модели
  вводить любые числа, которых нет во входном JSON, и менять
  direction/confidence/entry/targets/invalidation.
- `app/ai/reasoning.py` — оркестратор: LLM отвечает только за `why`
  (текстовые буллеты), все числа в итоговом `AnalysisResult` — из
  детерминированных движков.
- `app/ai/render.py` — форматирует `AnalysisResult` в текст по шаблону TZ
  4.3, дисклеймер добавляется всегда, без исключений.
- `app/ai/pricing.py` + `app/ai/usage.py` — оценка стоимости запроса и запись
  в `ai_requests` для cost/DAU-дашборда (TZ раздел 11).

Тесты используют `FakeLLMProvider`/фейковый Anthropic-клиент — реальных
сетевых вызовов в тестовом наборе нет.

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
