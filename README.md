# VRAV AI Monorepo

Суверенная архитектура VRAV AI с независимой реализацией ядра и агентного контура.

## Структура

- `core/engine.py` — оркестрация сообщений, валидация входа, tool-вызовы, replay и потоковые события.
- `core/server.py` — встроенный HTTP/SSE слой (`/health`, `/stream`, `/replay`, `/tools`, `/stats`, `/snapshot`, `/restore`).
- `core/cli.py` — локальный CLI для быстрого запуска сценариев `chat` и `stream`.
- `core/modules/schemas` — внутренние модели данных и валидаторы.
- `core/modules/protocol` — протокол потоковой передачи сообщений.
- `core/modules/agent` — runtime логики агента и реестр инструментов.
- `core/modules/bus` — событийная шина между модулями.
- `core/modules/registry` — хранилище сессионных состояний и event log.
- `core/modules/streaming` — утилиты чанкинга и поточной выдачи.

## Что уже реализовано

- Контракт `Envelope` + событийная таксономия для core/agent коммуникации.
- Monotonic `sequence_id` по каждой сессии.
- SSE-совместимый стриминг (`event/id/data`).
- Реплей потока в байтах через `VravEngine.stream_bytes()`.
- Internal tool protocol: `/tool <name> <arg>` с событиями `tool.call` и `tool.result`.
- In-memory event sourcing: `EventLog` + `VravEngine.replay()`.
- Snapshot/restore event log в JSON (`EventLog.snapshot(path)` / `EventLog.restore(path)`).
- Built-in tools: `echo`, `upper`.
- Валидация user input с отдельным `ValidationError` и error-event fallback.
- HTTP POST endpoints возвращают `400 {"error": "invalid_json"}` при некорректном JSON body.
- HTTP интерфейс для интеграции: POST `/stream`, POST `/restore`, POST `/tools/register`, POST `/admin/reset`, DELETE `/tools/unregister`, DELETE `/sessions`, GET `/replay`, GET `/events`, GET `/tools`, GET `/sessions`, GET `/sessions/export`, GET `/sessions/count`, GET `/stats`, GET `/config`, GET `/diagnostics`, GET `/slo`, GET `/metrics`, GET `/readiness`, GET `/version`, GET `/build`, GET `/capabilities`, GET `/schema/events`, GET `/schema/events-query`, GET `/schema/tools`, GET `/schema/tools-admin`, GET `/schema/tools-list`, GET `/schema/sessions`, GET `/schema/session-ops`, GET `/schema/system`, GET `/schema/runtime`, GET `/schema/http`, GET `/schema/auth`, GET `/schema/errors`, GET `/schema/rate-limit`, GET `/schema/snapshot`, GET `/schema/diagnostics`, GET `/schema/config`, GET `/schema/capabilities`, GET `/schema/readiness`, GET `/schema/slo`, GET `/schema/liveness`, GET `/schema/build`, GET `/schema/routes`, GET `/schema/openapi`, GET `/schema/stats`, GET `/schema/cli`, GET `/schema/index`, GET `/schema/discovery`, GET `/schema/version`, GET `/schema/health`, GET `/schema/status`, GET `/schema/stream`, GET `/schema/stream-request`, GET `/schema/replay`, GET `/schema/admin`, GET `/schema/admin-reset`, GET `/schema/metrics`, GET `/status`, GET `/whoami`, GET `/ping`, GET `/time`, GET `/routes`, GET `/openapi.json`, GET `/snapshot`.
- Опциональная авторизация по Bearer token через `VRAV_API_TOKEN`.
- CLI интерфейс: `python -m core.cli chat --text ...`, `python -m core.cli replay --session ...`.

## Запуск

```bash
python -m pytest -q
python -m core.server
python -m core.cli chat --text "привет"
```


## CI

- GitHub Actions workflow: `.github/workflows/ci.yml` запускает `pytest -q` на push/pull_request.
- Локальные команды через `Makefile`: `make test`, `make run-server`, `make run-cli`, `make lint`.

- Операционные метрики через `GET /stats` (sessions/tools/subscribers).

- Базовая защита от перегрузки: in-memory rate limiter по `session_id`.

- `GET /health` возвращает `status`, `service`, `uptime_seconds`.

- Production gap roadmap: `docs/PRODUCTION_READINESS.md`.

- Настройка rate-limit через env: `VRAV_RATE_LIMIT_REQUESTS`, `VRAV_RATE_LIMIT_WINDOW_SEC`.

- Самодокументирование API: `GET /routes` возвращает список поддерживаемых маршрутов.

- OpenAPI-совместимый базовый spec доступен через `GET /openapi.json`.

- Correlation: сервер поддерживает `X-Request-ID` (возвращается в ответах).

- Административный сброс in-memory состояния: `POST /admin/reset`.

- `GET /sessions` возвращает список активных in-memory сессий.

- Удаление сессии: `DELETE /sessions?session_id=...`.

- Детали сессии: `GET /sessions?session_id=<id>` (messages, last_sequence).

- CLI дополнительные команды: `python -m core.cli sessions`, `python -m core.cli reset`.

- CLI детали сессии: `python -m core.cli session --id <session_id>`.

- `GET /metrics` отдает plaintext метрики (`vrav_sessions`, `vrav_tools`) в Prometheus-friendly формате.

- `GET /status` агрегирует health + runtime counters в одном ответе.

- Экспорт событий одной сессии: `GET /sessions/export?session_id=<id>` и CLI `python -m core.cli session-export --id <id>`.

- Runtime config snapshot: `GET /config` и CLI `python -m core.cli config`.

- Счётчик событий сессии: `GET /sessions/count?session_id=<id>` и CLI `python -m core.cli session-count --id <id>`.

- Runtime diagnostics: `GET /diagnostics` и CLI `python -m core.cli diagnostics`.

- `GET /slo` публикует целевые SLO метрики для планирования production readiness.

- Контекст запроса: `GET /whoami` (auth_enabled + request_id).

- Быстрый liveness ping: `GET /ping` => `{ "pong": true }`.

- Время сервера: `GET /time` (`epoch` + `iso`).

- Build metadata: `GET /build` (name/version/python/runtime).

- Матрица возможностей: `GET /capabilities` (feature flags текущего runtime).

- Контракт событий: `GET /schema/events` возвращает поля envelope/message.

- Контракт query событий: `GET /schema/events-query` (`/events` query params, defaults и response fields).

- Контракт tool-протокола: `GET /schema/tools` (формат команды и tool events).

- Контракт tool-admin API: `GET /schema/tools-admin` (register/unregister endpoints и поля payload/response).

- Контракт списка tools: `GET /schema/tools-list` (`/tools` response fields, tool fields и default tools).

- Контракт session API: `GET /schema/sessions` (overview/detail/count поля).

- Контракт session operations: `GET /schema/session-ops` (overview/detail/export/count/delete endpoints и query fields).

- Контракт системных endpoint: `GET /schema/system` (health/status/build поля).

- Контракт runtime observability: `GET /schema/runtime` (config/diagnostics/metrics/slo поля).

- Контракт HTTP-транспорта: `GET /schema/http` (headers, content-type, auth header).

- Контракт CLI: `GET /schema/cli` (список команд и entrypoint).

- Каталог схем: `GET /schema/index` возвращает список всех schema endpoints.

- Контракт авторизации: `GET /schema/auth` (режимы auth, env var, required header).

- Контракт ошибок API: `GET /schema/errors` (common error codes и примеры ответов, включая `invalid_json`).

- Контракт rate limiting: `GET /schema/rate-limit` (scope, config fields и error signal при превышении лимита).

- Контракт snapshot/restore: `GET /schema/snapshot` (query/payload поля и response-контракты).

- Контракт diagnostics: `GET /schema/diagnostics` (поля агрегированного runtime-диагностического ответа и связанные endpoints).

- Контракт runtime config: `GET /schema/config` (структура `/config`, поля engine и auth env var).

- Контракт capabilities: `GET /schema/capabilities` (feature flags и тип значений для client discovery).

- Контракт readiness: `GET /schema/readiness` (stage, production_ready, readiness score, blockers и ссылка на production checklist).

- Контракт SLO: `GET /schema/slo` (target fields и назначение pre-production targets).

- Контракт liveness/request context: `GET /schema/liveness` (`/ping`, `/time`, `/whoami` поля и request id header).

- Контракт build metadata: `GET /schema/build` (`/build` поля, runtime values и источник версии).

- Контракт routes discovery: `GET /schema/routes` (`/routes` поле и формат записей маршрутов).

- Контракт OpenAPI metadata: `GET /schema/openapi` (`/openapi.json` поля, версия spec и HTTP methods).

- Контракт stats endpoint: `GET /schema/stats` (`/stats` поля и связь с metrics/diagnostics).

- Навигация по schema-семействам: `GET /schema/discovery`.

- Контракт версионирования: `GET /schema/version` (поля и связанные endpoints).

- Контракт stream-протокола: `GET /schema/stream` (SSE frame + replay endpoints).

- Контракт stream request: `GET /schema/stream-request` (`POST /stream` request fields и SSE response headers).

- Контракт replay-потока: `GET /schema/replay` (replay/events/session-export endpoints + sequence model).

- Контракт admin-операций: `GET /schema/admin` (reset/tools/session-delete/snapshot-restore endpoints).

- Контракт admin reset: `GET /schema/admin-reset` (`POST /admin/reset` response fields и side effects).

- Контракт metrics-экспорта: `GET /schema/metrics` (content-type, линии метрик, источник данных).

- Контракт health endpoint: `GET /schema/health` (поля и допустимые status values).

- Контракт status endpoint: `GET /schema/status` (агрегированные поля runtime-status).
