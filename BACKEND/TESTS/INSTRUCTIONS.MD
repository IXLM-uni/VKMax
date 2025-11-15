<!-- Руководство к файлу (BACKEND/TESTS/INSTRUCTIONS.MD)
Назначение:
- Описывает архитектуру тестов backend VKMax.
- Помогает понять, какие части системы покрыты тестами, а какие нет.
-->

# Архитектура каталога BACKEND/TESTS

## 1. Общие принципы

- Используем **pytest** как основной тестовый фреймворк.
- Все тесты — асинхронные там, где это имеет смысл (FastAPI, AsyncSession, LLM).
- Три уровня тестов:
  - unit-тесты: быстро, без реальной БД и внешних сервисов;
  - integration-тесты: FastAPI + БД + сервисный слой;
  - e2e/flow-тесты: полный путь `upload -> convert -> download / graph`.
- Каждая тестовая папка должна содержать понятные имена файлов и минимум магии.

Именование файлов:
- Unit: `test_<module>_unit.py`.
- Integration: `test_<feature>_integration.py`.
- E2E: `test_<flow>_e2e.py`.

## 2. Структура каталогов

Предлагаемая структура `BACKEND/TESTS` (папки создаются по мере появления тестов):

- `BACKEND/TESTS/INSTRUCTIONS.MD` — этот файл с описанием архитектуры.
- `BACKEND/TESTS/conftest.py` — общие фикстуры (event loop, инициализация тестовой БД, FastAPI‑приложение, HTTP‑клиент).
- `BACKEND/TESTS/unit/` — unit‑тесты без реального LLM/внешних сервисов.
  - `unit/test_cleaner_unit.py` — сценарии очистки JSON/HTML/Mermaid/plain для `CleanerService`.
  - `unit/test_validator_unit.py` — регистрация схем и асинхронная валидация в `ValidatorService`.
  - `unit/test_converters_unit.py` — базовые сценарии для `CONVERT/converters.py` (`_normalize_fmt`, `_limit_words`, `extract_plain_text`).
- `BACKEND/TESTS/integration/` — интеграционные тесты с тестовой БД и FastAPI.
  - `integration/test_user_routes_integration.py` — CRUD по `/users` и связанные списки файлов/операций.
  - `integration/test_files_routes_integration.py` — `POST /upload`, `GET /files`, `DELETE /files/{id}`.
  - `integration/test_convert_routes_integration.py` — `POST /convert`, website‑потоки, статусы `/operations` и `/websites/*`, заглушка граф‑генератора.
  - `integration/test_download_routes_integration.py` — `GET /download/{id}` и preview.
  - `integration/test_format_routes_integration.py` — `/formats`, `/formats/input`, `/formats/output`, `/supported-conversions`.
  - `integration/test_system_routes_integration.py` — `/stats`, `/webhook/conversion-complete`.
  - `integration/test_llm_openrouter_integration.py` — реальный вызов `LlmService` через OpenRouter/DeepSeek (при наличии ключа).
  - `integration/test_health_integration.py` — базовый health‑чек корня приложения.
- `BACKEND/TESTS/e2e/` — end‑to‑end/flow тесты ключевых сценариев.
  - `e2e/test_flow_file_to_pdf_e2e.py` — upload PDF → convert(pdf) → download (быстрый stub‑PDF, не для визуального просмотра).
  - `e2e/test_flow_file_to_graph_e2e.py` — upload PDF → convert(graph) с заглушенным граф‑генератором → download JSON‑граф.
  - `e2e/test_flow_website_convert_e2e.py` — website‑конвертация `/convert/website` → статус → история.
  - `e2e/test_flow_root_health_e2e.py` — базовый health‑чек корня приложения.
  - `e2e/test_flow_assets_files_e2e.py` — сценарии с реальными файлами из `TESTS/assets/files` (DOCX/PDF), проверка устойчивости API к реальным документам.
  - `e2e/test_flow_real_conversions_e2e.py` — **реальные** цепочки DOCX↔PDF и DOCX/PDF→Graph через LLM (OpenRouter/DeepSeek) с `skipif`, если зависимости/ключи не настроены.

Фактическое наличие файлов/папок не обязательно прямо сейчас — это **целевое** разбиение для постепенного наполнения.

## 3. Базовые фикстуры (conftest.py)

Файл `BACKEND/TESTS/conftest.py` уже содержит базовый набор фикстур:

- **event_loop (scope="session")**
  - Общий асинхронный event loop для всех тестов.
- **init_db (scope="session", autouse=True)**
  - При старте тестовой сессии вызывает `DATABASE.alembic.create_tables()` и `seed_formats()`.
  - Гарантирует наличие таблиц и базового набора форматов (`pdf`, `docx`, `html`, `graph`, `url`).
- **http_client**
  - Создаёт `httpx.AsyncClient` с `ASGITransport(app=FAST_API.fast_api.app)`.
  - Позволяет гонять HTTP‑запросы к FastAPI‑приложению без реального сервера.

Эти фикстуры используются во всех подпапках (`unit/`, `integration/`, `e2e/`), поэтому `conftest.py` живёт на верхнем уровне `BACKEND/TESTS`.

## 4. Куда класть тесты для конкретных модулей

- **FAST_API/ROUTES/**
  - Быстрые проверки в `integration/test_*_routes_integration.py`.
  - E2E-сценарии — в `e2e/`.
- **CONVERT/**
  - Чистая логика конвертеров (`converters.py`) — в `unit/`.
  - Оркестраторы (`conversion_service.py`, `graph_service.py`, `webparser_service.py`) — в `integration/` (с тестовой БД).
- **LLM_SERVICE/**
  - `llm_service.py` — unit-тесты с провайдером `mock`.
  - `document_generator.py`, `cleaner.py`, `validator.py` — unit + лёгкие integration-тесты (без реального внешнего LLM, максимум — `mock`).
- **DATABASE/**
  - Позитивные проверки моделей и простых запросов — в `integration/test_database_models_integration.py`.

## 5. Как понять, что покрыто, а что нет

- Под "готовой" архитектурой считаем:
  - наличие `INSTRUCTIONS.MD` (этот файл);
  - наличие `conftest.py` с базовыми фикстурами;
  - наличие хотя бы одного теста в каждой из папок `unit/`, `integration/`, `e2e/` для ключевых сценариев.
- Для оценки покрытия можно использовать `pytest --cov=BACKEND --cov-report=term-missing` (после добавления `pytest-cov` в зависимости).

## 6. Порядок внедрения тестов (рекомендация)

1. Создать `conftest.py` с минимальными фикстурами (`event_loop`, тестовый `app`, `http_client`).
2. Добавить несколько unit-тестов для `CONVERT/converters.py` и `LLM_SERVICE/cleaner.py`.
3. Добавить integration-тесты для `POST /upload`, `POST /convert`, `GET /operations/{id}`, `GET /download/{id}`.
4. Добавить e2e-тесты для двух основных потоков: `file → pdf` и `file → graph`.
5. По мере эволюции backend’а дополнять тесты и эту инструкцию.

## 7. Дополнительные рекомендуемые тесты

- `unit/test_llm_service_unit.py` — сценарии для `LLM_SERVICE.llm_service.LlmService` в режиме `mock` и обработка ошибок конфигурации.
- `unit/test_document_generator_unit.py` — ретраи, registry и ошибки `CleanerService`/`ValidatorService`.
- `integration/test_website_preview_integration.py` — `/websites/preview` для валидного и невалидного URL.
- `integration/test_operations_list_integration.py` — `GET /operations` с фильтрами `user_id`, `status`, `type`.
- `e2e/test_flow_invalid_inputs_e2e.py` — негативные флоу (`upload`/`convert` с некорректными форматами, слишком большими файлами и т.п.).
