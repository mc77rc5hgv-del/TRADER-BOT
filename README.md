# TRADE AI

AI-платформа для трейдинга внутри Telegram (бот + Mini App). Продуктовое и
техническое ТЗ MVP — в [`docs/TZ_MVP.md`](docs/TZ_MVP.md).

Текущий этап: **Phase 1, шаг 9 — Alerts v0** (см. раздел 13 ТЗ).

## Стек

- Backend/API: FastAPI
- Bot: aiogram 3
- DB: PostgreSQL (async, SQLAlchemy 2.0) + Alembic
- Cache/queues: Redis
- LLM: Anthropic Claude (`claude-opus-5` по умолчанию) через provider-agnostic интерфейс
- Mini App frontend: Next.js (App Router) + TypeScript + Tailwind, `webapp/`

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

# Доставка алертов (в отдельном терминале)
python -m app.alerts.worker

# Mini App (в отдельном терминале)
cd webapp
cp .env.local.example .env.local
npm install
npm run dev
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

## Mini App shell (`webapp/`)

Next.js App Router + TypeScript + Tailwind, авторизация через Telegram
WebApp `initData` (TZ раздел 10), два рабочих таба — Home и Market (AI и
Profile в нижней навигации показаны как «скоро», под них ничего не построено).

**Backend (`app/webapp/`):**
- `app/webapp/auth.py:validate_init_data()` — проверка HMAC-подписи
  `initData` по алгоритму Telegram (`secret = HMAC-SHA256("WebAppData",
  bot_token)`, затем `HMAC-SHA256(secret, data_check_string)`), плюс проверка
  свежести `auth_date`. Никогда не доверяет `user.id` без этой проверки.
- `POST /webapp/auth` — валидирует `Authorization: tma <initData>`,
  создаёт/находит пользователя, возвращает профиль. Дальнейшие защищённые
  эндпоинты переиспользуют `get_validated_init_data` как FastAPI-зависимость.
- CORS настроен через `CORS_ALLOW_ORIGINS` в `.env` (по умолчанию
  `http://localhost:3000`; `MINI_APP_URL`, если задан, добавляется
  автоматически).

**Frontend (`webapp/src/`):**
- `lib/telegram.ts` — обёртка над `window.Telegram.WebApp` (SDK грузится
  напрямую скриптом `telegram-web-app.js` в `app/layout.tsx`, без отдельного
  npm-пакета — так он всегда обновлён на стороне Telegram).
- `lib/api.ts` — fetch-клиент, добавляет `Authorization: tma <initData>` к
  каждому запросу к backend.
- `app/page.tsx` (Home) — Market Pulse: цена + суточное изменение по топ-5
  ликвидных активов (тот же список, что в `ws_worker.TRACKED_SYMBOLS`).
- `app/market/page.tsx` + `app/market/[symbol]/page.tsx` — поиск/быстрые
  ссылки на активы и экран инструмента: переключатель TF (1m/5m/15m/1h/4h/1d)
  и свечной график на `lightweight-charts` v5 (`chart.addSeries(CandlestickSeries,
  …)` — актуальный API для этой мажорной версии, отличается от v4).

Прогон через реальный браузер (Playwright, headless Chromium) подтвердил:
рендер всех трёх экранов, переключение TF, и сам свечной график — на
синтетических данных, так как исходящий IP этого dev-окружения
геоблокируется Binance (HTTP 451); в проде/на обычном хостинге это
ограничение отсутствует.

## AI-таб в Mini App

Тот же пайплайн, что и в боте (`app/ai/pipeline.py:run_chat_analysis`) — не
отдельная реализация (TZ раздел 8: «тот же ответ, что в боте»).

- `POST /webapp/analyze` (`app/webapp/router.py`) — принимает `{symbol, tf}`,
  требует `Authorization: tma <initData>`, отдаёт `AnalysisResult` целиком
  как JSON. И DB-сессия, и валидация initData внедряются через
  `Depends(...)`, поэтому в тестах переопределяются независимо друг от
  друга, без обращения к реальному Postgres.
- `app/ai` (`/ai`) — ввод тикера, переключатель TF, быстрые чипы по топ-5
  активам, карточка результата (`AnalysisCard`): основной сценарий
  (LONG/SHORT + confidence), альтернатива/нейтральный %, entry/targets/
  invalidation/R:R, WHY-буллеты, дисклеймер — один и тот же компонент
  переиспользуется на экране инструмента.
- `app/market/[symbol]` — кнопка «✨ AI ANALYSIS» вызывает тот же
  `/webapp/analyze` и рисует entry/stop/targets прямо на свечном графике
  через `series.createPriceLine()` (TZ раздел 9: «AI прямо рисует анализ на
  графике»). Устаревший результат (от предыдущего тикера/TF) не показывается:
  он помечается тем `symbol`/`tf`, для которого был получен, и на рендере
  просто не совпадает с текущими — без лишнего `setState` внутри эффекта.
- Проверено в браузере (см. выше про геоблок Binance): ввод BTC на `/ai`
  выдаёт корректно оформленную карточку, кнопка на экране инструмента рисует
  четыре линии уровней (Entry/Stop/TP1/TP2) с подписями цен на графике.

## Alerts v0 (ценовые алерты)

Только ценовые условия («выше/ниже X») — TZ раздел 13, шаг 9. Более сложные
условия (RSI, breakout, on-chain и т.д. из раздела 68 ТЗ) — задел на будущее,
`AlertType` в модели уже их предусматривает.

- `app/alerts/schemas.py` — `PriceAlertCondition` (`operator: above|below`,
  `price`), единственная форма условия в v0.
- `app/alerts/service.py` — `evaluate_alert()` (чистая функция, без I/O) и
  `describe_condition()` для человекочитаемого текста; лимит Free-тарифа
  (`FREE_TIER_ACTIVE_ALERT_LIMIT = 3`, TZ раздел 8) — единственное место,
  где он захардкожен, до полноценного биллинга (шаг 11).
- `app/bot/handlers/alerts.py` — FSM-диалог создания алерта (тикер →
  выше/ниже → цена), с кнопкой «Отмена» на каждом шаге и проверкой лимита
  перед стартом. Список алертов (кнопка «🔔 АЛЕРТЫ» в главном меню) показывает
  активные алерты и кнопку создания нового.
- `app/alerts/worker.py` — отдельный процесс: раз в
  `POLL_INTERVAL_SECONDS` (30с) проверяет все активные price-алерты через
  `MarketDataEngine` (переиспользует тот же Redis-кэш, что и остальной
  продукт — без лишних запросов к Binance) и присылает уведомление в
  Telegram при срабатывании. Алерт помечается `TRIGGERED` до отправки
  сообщения, чтобы неудачная доставка не приводила к повторному спаму на
  следующем цикле.

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
  webapp/              # Telegram WebApp initData validation, /webapp/auth
migrations/            # Alembic
webapp/                # Mini App: Next.js + TypeScript + Tailwind (отдельный npm-проект)
docs/TZ_MVP.md          # полное ТЗ
```

Границы модулей (`market/`, `ai/`, `alerts/`, `billing/`, `users/`) —
задел на будущее выделение в отдельные сервисы (Phase 5 ТЗ), в MVP это
единый modular monolith.
