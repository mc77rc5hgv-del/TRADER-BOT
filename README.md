# TRADE AI

AI-платформа для трейдинга внутри Telegram (бот + Mini App). Продуктовое и
техническое ТЗ MVP — в [`docs/TZ_MVP.md`](docs/TZ_MVP.md).

Текущий этап: **Phase 1, шаг 6 — скриншот-сценарий (Vision Extractor)** (см. раздел 13 ТЗ).

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

## End-to-end текстовый сценарий (бот)

`app/ai/pipeline.py:run_chat_analysis()` — единая точка входа, которая
связывает все движки: Market Data Engine → Technical Analysis → Probability
→ Risk (если есть направленный сетап) → AI Reasoning Layer. Для long/short
сетапа результат сохраняется в Prediction Ledger (immutable, `source=chat`);
для нейтрального сценария Prediction не создаётся, но запрос в `ai_requests`
пишется всегда.

В боте (`app/bot/handlers/analyze.py`):
- `/analyze <тикер> [tf]` — явная команда (по умолчанию `tf=1h`);
- любое обычное текстовое сообщение (не команда) — тоже уходит в пайплайн
  (TZ 4.2: "без обязательной команды"); если тикер не распознан, бот молчит
  об этом конкретном сообщении, чтобы не превращать обычную переписку в
  поток ошибок.

`classify_risk_level()` в `app/risk/service.py` добавляет грубую метку
Low/Medium/High по отношению ATR к цене — используется и в `RiskLevels`, и
при записи в Prediction Ledger.

## Скриншот-сценарий (Vision Extractor)

Скриншот используется **только** для определения тикера/таймфрейма/биржи —
никогда как источник цифр (TZ раздел 2.1). Как только символ распознан,
дальше работает тот же пайплайн, что и в текстовом сценарии.

- `LLMProvider.extract_chart_info()` (`app/ai/provider.py`) — vision-запрос
  со structured output (`VisionExtraction`); системный промпт
  (`app/ai/vision_prompt.py`) прямым текстом запрещает модели читать цены
  или уровни с картинки.
- `app/ai/image_utils.py` — валидация + пересжатие в JPEG, которое отбрасывает
  EXIF/ICC-метаданные (TZ раздел 91).
- `app/ai/screenshot_storage.py` — `ScreenshotStorage` (provider-agnostic,
  как `LLMProvider`); `LocalFilesystemStorage` — dev-реализация, в проде
  заменяется на S3-совместимое хранилище без изменения вызывающего кода.
  Запись `screenshots` с `expires_at` (TZ раздел 6.4) создаётся всегда,
  даже если тикер не распознан — ретеншн чистит её позже фоновой джобой
  (сама джоба — отдельный будущий шаг).
- `app/ai/screenshot_pipeline.py:run_screenshot_analysis()` — оркестратор:
  снять метаданные → сохранить → распознать → нормализовать тикер/TF →
  делегировать в `run_chat_analysis(..., source=SCREENSHOT)`. Если тикер не
  распознан уверенно, `app/market/symbols.py:suggest_symbols()`
  (`difflib`) предлагает до 3 похожих активов.
- В боте (`app/bot/handlers/screenshot.py`): хендлер на `F.photo` с проверкой
  размера файла (`SCREENSHOT_MAX_BYTES`), плюс callback-кнопки для выбора
  одного из предложенных тикеров при неуверенном распознавании.

Не входит в этот шаг (сознательно, см. TZ раздел 91): сканирование на
вредоносное содержимое — для MVP не реализовано.

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
