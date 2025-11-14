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
- `BACKEND/TESTS/conftest.py` — общие фикстуры (event loop, test settings, test БД, FastAPI app, HTTP-клиент).
- `BACKEND/TESTS/unit/` — unit-тесты без реальной БД и сети.
  - `unit/test_llm_service_unit.py` — проверки LlmService в режиме `mock`.
  - `unit/test_document_generator_unit.py` — поведение DocumentGenerator при разных registry/doc_type.
  - `unit/test_converters_unit.py` — низкоуровневые конвертеры из `CONVERT/converters.py`.
- `BACKEND/TESTS/integration/` — интеграционные тесты с тестовой БД.
  - `integration/test_database_models_integration.py` — базовая проверка моделей `User/File/Operation/Format`.
  - `integration/test_convert_routes_integration.py` — `POST /convert`, `GET /operations/{id}`, работа с `run_file_conversion` и `generate_graph_for_operation`.
  - `integration/test_files_routes_integration.py` — `POST /upload`, `GET /files`, `DELETE /files/{id}`.
  - `integration/test_websites_integration.py` — `POST /convert/website`, `POST /upload/website`, `GET /websites/*` с заглушкой WebParser.
- `BACKEND/TESTS/e2e/` — end-to-end/flow тесты ключевых сценариев.
  - `e2e/test_flow_file_to_pdf_e2e.py` — полный сценарий: upload DOCX → convert to PDF → download.
  - `e2e/test_flow_file_to_graph_e2e.py` — upload DOCX/PDF → convert to graph → скачать JSON-граф.
  - `e2e/test_flow_website_to_pdf_e2e.py` — website-конвертация с заглушкой webparser.

Фактическое наличие файлов/папок не обязательно прямо сейчас — это **целевое** разбиение для постепенного наполнения.

## 3. Базовые фикстуры (conftest.py)

Рекомендуется создать `BACKEND/TESTS/conftest.py` со следующими группами фикстур:

- **event_loop**
  - Общий асинхронный event loop для pytest (`pytest-asyncio` / встроенный режим asyncio).
- **settings_override**
  - Подменяет `FAST_API/config.settings` для тестов (отдельная БД, путь к storage_dir в tmp-директории, отключение внешних вызовов).
- **test_engine / test_session_maker / test_db**
  - Создаёт отдельный SQLite (в памяти или временный файл).
  - Прогоняет модели из `DATABASE/models.py` и, при необходимости, миграции.
  - Даёт фикстуру `async_session` для тестов.
- **fastapi_app**
  - Инициализирует `app` из `FAST_API/fast_api.py` с тестовыми настройками.
- **http_client**
  - Предоставляет `httpx.AsyncClient` c `app` как ASGI-приложением.

Эти фикстуры используются во всех подпапках, поэтому `conftest.py` живёт на верхнем уровне `BACKEND/TESTS`.

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
