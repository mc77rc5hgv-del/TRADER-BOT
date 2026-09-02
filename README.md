# TRADE AI

AI-платформа для трейдинга внутри Telegram (бот + Mini App). Продуктовое и
техническое ТЗ MVP — в [`docs/TZ_MVP.md`](docs/TZ_MVP.md).

Текущий этап: **Phase 1 завершена (13 из 13 шагов)** (см. раздел 13 ТЗ).

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

## Scanner v0

Раз в `SCAN_INTERVAL_SECONDS` (10 мин) — не по запросу пользователя (TZ раздел
3.4) — считается по всему пулу поддерживаемых активов, результат кэшируется
в Redis.

- `app/scanner/service.py` — `run_scan()` прогоняет каждый символ из пула
  (`SCANNER_SYMBOL_POOL` = все базовые тикеры, которые распознаёт
  `app/market/symbols.py`, сейчас 22 актива) через **тот же** детерминированный
  пайплайн TA → Probability → Risk, что и текстовый/скриншот-анализ — но
  **без вызова LLM**: сканировать весь пул через AI обошлось бы слишком
  дорого (TZ раздел 95), а для списка сетапов не нужен текстовый WHY.
- `app/scanner/worker.py` — отдельный процесс (`python -m app.scanner.worker`),
  пересчитывает пул и кладёт в Redis (`scanner:top_setups`, TTL 15 мин —
  верхняя граница интервала пересчёта из ТЗ).
- `GET /scanner?direction=long&risk=low` — отдаёт закэшированный список,
  отсортированный по confidence, с опциональными фильтрами по направлению
  и риску (TF в v0 фиксирован — 1h; мульти-TF сканирование утроило бы нагрузку
  фоновой джобы и оставлено на будущее).
- В боте: `/scanner` и кнопка «🔥 ЛУЧШИЕ СЕТАПЫ» показывают дайджест топ-5
  направленных сетапов — тоже читают кэш напрямую, без пересчёта на клик.
- В Mini App: `/scanner` — фильтры по направлению (Все/Long/Short) и риску
  (Все/Low/Medium/High), карточки со ссылкой на `/market/[symbol]`; кнопка
  на экране Market ведёт туда же. Проверено в браузере: список сортируется
  по confidence, фильтр по направлению корректно скрывает лишние карточки.

## Billing v0

Two tiers, FREE and PRO (TZ раздел 8/9), с оплатой через Telegram Stars —
единственный платёжный метод, который не требует юрлица/эквайринга для MVP.

- `app/billing/models.py` — `Subscription` (`tier`, `status`, `started_at`,
  `expires_at`, `payment_provider`, `external_payment_id`). Каждая покупка —
  **новая** строка, а не обновление старой: дёшево хранить историю покупок,
  а `get_active_tier()`/`get_active_subscription()` всегда берут последнюю
  ACTIVE и не истёкшую.
- `app/billing/service.py` — `TIER_LIMITS`: FREE = 5 AI-анализов/день, 3
  активных алерта; PRO = 50 AI-анализов/день, 20 активных алертов.
  `PRO_PRICE_STARS = 300` (⭐/мес) — стартовая оценка (TZ: "$9-15/мес
  эквивалент"), у Stars нет фиксированного курса к USD, править по факту.
- **Дневная квота на AI-анализы** проверяется в
  `app/ai/pipeline.py::run_chat_analysis()` **до** вызова LLM (`chat_analysis`
  + `screenshot_analysis` из `ai_requests` за сегодня, `vision_extraction` не
  считается — это внутренняя бухгалтерия скриншот-флоу, а не второй анализ
  поверх него). Для скриншот-сценария квота проверяется **ещё раньше**, в
  `app/ai/screenshot_pipeline.py::run_screenshot_analysis()`, до самого
  дорогого шага (vision-извлечение тикера с картинки) — иначе пользователь
  сверх квоты всё равно сжигал бы платный vision-запрос перед отказом.
  Превышение — `QuotaExceededError`, боты (`analyze.py`, `screenshot.py`)
  ловят её и показывают предложение оформить PRO.
- **Лимит активных алертов** (`app/bot/handlers/alerts.py::on_alert_new`)
  берётся из `billing.service.get_tier_limits()`, а не захардкожен — PRO
  реально получает более высокий лимит.
- `app/bot/handlers/billing.py` — экран «💳 Подписка» (кнопка в главном
  меню): показывает текущий тариф и, для FREE, кнопку «⭐ Купить PRO»,
  которая шлёт `bot.send_invoice(currency="XTR", ...)`. Провайдер-токен для
  Stars — пустая строка (так требует Bot API). `pre_checkout_query`
  подтверждается сразу (`ok=True`) — проверять тут нечего, товар один и с
  фиксированной ценой. `successful_payment` вызывает
  `activate_pro_subscription()` и подтверждает активацию сообщением.

## AI Accuracy v0

Публичная статистика по Prediction Ledger (TZ раздел 3.6) — сколько прогнозов
дали результат и с каким win rate, обновляется раз в сутки фоновой джобой,
не в реальном времени.

- `app/ai/accuracy.py` — `run_evaluation()` сверяет каждый ещё не оценённый
  `Prediction` с реальными свечами (через тот же Market Data Engine) и
  выставляет `outcome`: `tp1_reached` / `tp2_reached` / `stop_hit` /
  `expired_no_hit` (после `EXPIRY_CANDLE_HORIZON` = 100 свечей без касания
  цели или стопа). Свеча, чей диапазон захватывает и цель, и инвалидацию
  одновременно, засчитывается в пользу стопа — консервативное допущение,
  когда порядок касаний внутри свечи неизвестен. `outcome`/
  `outcome_evaluated_at` — единственные поля `Prediction`, которые разрешено
  менять после создания (см. immutability-guard в `app/ai/models.py`).
- `compute_accuracy_report()` агрегирует за последние 30 дней: всего
  прогнозов, win rate, средний реализованный R (по `TARGET_R_MULTIPLES` из
  risk-движка), разбивку по топ-5 активам и по TF.
- `app/ai/accuracy_worker.py` (`python -m app.ai.accuracy_worker`, раз в
  сутки) оценивает исходы и кладёт отчёт в Redis (`accuracy:report`,
  TTL 2 дня) — ни бот, ни Mini App отчёт не пересчитывают на лету.
- `GET /webapp/accuracy` — публичный эндпоинт (initData не требуется, как и
  у Scanner), отдаёт закэшированный отчёт с фоллбеком на живой расчёт, если
  джоба ещё не отработала. Экран `/accuracy` в Mini App (карточки метрик +
  разбивки), ссылка с экрана Market. В боте — кнопка «📊 Точность AI» в
  главном меню.
- Для сопоставления уже-канонического символа `Prediction.symbol`
  (например `"BTCUSDT@binance"`) обратно в Market Data Engine
  `normalize_symbol()` (`app/market/symbols.py`) сделан идемпотентным —
  раньше он принимал только «сырые» пользовательские строки и не узнавал
  собственный же canonical-вывод.

## Внутренняя аналитика (админ)

Минимум для MVP из TZ раздела 11 — не веб-дашборд, а скрипт с прямым
доступом к БД (веб-админки/авторизации в v0 ещё нет):

```bash
python -m app.admin.report_cli
```

- `app/admin/analytics.py` — `compute_cost_report()` (стоимость AI-запросов
  по дням, топ пользователей по затратам, latency p50/p95 — всё из
  `ai_requests`), `compute_activity_report()` (DAU/WAU по
  `User.last_active_at`), `compute_conversion_report()` (Free→Pro conversion
  rate и churn за последние 30 дней).
- `User.last_active_at` — новое поле, обновляется на каждый вызов
  `get_or_create_user()` (`app/bot/repository.py`), то есть почти на любое
  взаимодействие с ботом или Mini App — самый дешёвый достаточный сигнал
  активности без отдельного трекинга событий.
- Churn считается через `expires_at`, а не через `Subscription.status`:
  каждая покупка — новая строка в статусе ACTIVE (см. Billing v0 выше),
  поэтому `status` в этой системе никогда не переходит в EXPIRED/CANCELED
  сам по себе. «Churn» — это последняя подписка пользователя истекла в
  пределах окна и с тех пор не продлевалась.

## Нагрузка и graceful degradation

- `MarketDataEngine` использует single-flight для одновременных одинаковых
  cache miss: 100 параллельных запросов одного символа/TF внутри процесса
  разделяют один вызов Binance, после чего результат лежит в Redis.
- Redis-backed rate limiter защищает HTTP API по Telegram authorization или
  IP (`RATE_LIMIT_REQUESTS` запросов за `RATE_LIMIT_WINDOW_SECONDS`). При
  недоступном Redis limiter fail-open, а платные AI-вызовы всё равно защищены
  дневной тарифной квотой.
- Если LLM недоступен или вернул невалидную структуру, пользователь получает
  детерминированные probability/risk/entry/targets и явную пометку, что
  текстовое AI-пояснение временно недоступно, вместо общей ошибки.
- `railway.json` запускает миграции и Telegram polling worker одной командой;
  токен и подключения к Postgres/Redis задаются только переменными Railway.

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
