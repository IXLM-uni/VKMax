# Руководство к каталогу BACKEND/FAST_API

## 1. Назначение

Каталог `BACKEND/FAST_API` содержит HTTP‑слой VKMax:

- конфигурацию приложения и хранилищ;
- инициализацию FastAPI‑приложения;
- REST‑роуты (`/users`, `/files`, `/convert`, `/download`, `/formats`, `/system`, `/websites`);
- pydantic‑схемы запросов/ответов.

FastAPI не содержит тяжёлой бизнес‑логики: она вынесена в `DATABASE`, `SEVICES`,
`CONVERT`, `LLM_SERVICE`.

## 2. Основные файлы

- `config.py`
  - Класс `Settings` (на базе `pydantic_settings.BaseSettings`) с префиксом `VKMAX_`.
  - Ключевые поля:
    - `base_dir` — базовая директория проекта;
    - `storage_dir`, `tmp_dir`, `logs_dir` — каталоги для файлов/временных файлов/логов;
    - `max_upload_mb` — лимит размера загружаемого файла (по умолчанию 40 МБ);
    - `cors_origins` — список разрешённых Origin;
    - `llm_provider` — историческое поле, для фактического LLM используется `LLM_SERVICE`.
  - При инициализации создаёт каталоги хранения.

- `fast_api.py`
  - Точка сборки FastAPI‑приложения:
    - вызывает `SEVICES.setup_logging()` **до** создания `FastAPI()`;
    - инициализирует `app`, подключает роутеры из `ROUTES`;
    - настраивает CORS и базовые middleware/exception‑handlers.
  - Импортируется в тестах (`TESTS/conftest.py`) для поднятия приложения в памяти.

- `ROUTES/` — папка с роутерами по функциональным областям:
  - `user.py` — CRUD по пользователям и связанные списки файлов/операций;
  - `files.py` — загрузка/просмотр/удаление файлов, `POST /upload`, `POST /upload/website`;
  - `convert.py` — создание операций конвертации, статусы и история `/operations` и `/websites/*`;
  - `download.py` — скачивание/preview файлов по `file_id`;
  - `format.py` — список форматов и матрица поддерживаемых конвертаций;
  - `system.py` — `/health`, `/stats`, `/webhook/conversion-complete`.

- `schemas.py`
  - Pydantic‑модели запросов/ответов для всех REST‑методов.
  - Используются и в FastAPI, и в тестах для валидации структуры.

- `run_app.py`
  - Точка входа для `uvicorn` в разработке.
  - Пример: `python -m uvicorn BACKEND.FAST_API.run_app:app --reload`.

## 3. Связь с БД и сервисным слоем

- `DATABASE/session.py`
  - Определяет `async_session_factory` и `get_db_session` (Depends) для `AsyncSession`.
  - Во всех роутерах БД‑сессия прокидывается через `Depends(get_db_session)`.

- `DATABASE/CACHE_MANAGER/*`
  - Менеджеры (`UserManager`, `FilesManager`, `ConvertManager`, `FormatManager`, `SystemManager`)
    инкапсулируют запросы к БД.

- `SEVICES/*`
  - `conversion_service`, `graph_service`, `webparser_service` реализуют оркестрацию
    конвертаций, генерации графов и работы с сайтами.
  - `logging_config.setup_logging()` задаёт общий стиль логирования.

- `CONVERT/*`
  - Низкоуровневые конвертеры DOCX/PDF и извлечение plain‑текста.

- `LLM_SERVICE/*`
  - LLM‑клиент DeepSeek через OpenRouter и оркестратор `DocumentGenerator`.

Роуты не должны напрямую обращаться к внешним API: вместо этого они вызывают
сервисный слой и менеджеры БД.

## 4. LLM и конвертация

- `ROUTES/convert.py`:
  - создаёт операции конвертации через `ConvertManager`;
  - для файловых операций вызывает:
    - `CONVERT.run_file_conversion` для `pdf/docx`;
    - `CONVERT.generate_graph_for_operation` для `target_format="graph"`;
  - для website‑операций вызывает `CONVERT.enqueue_website_job` и оставляет статус `queued`.

- `ROUTES/files.py`:
  - `POST /upload` — принимает файл, создаёт запись `File` и исходную операцию;
  - `POST /upload/website` — создаёт website‑операцию и ставит её в очередь.

- `ROUTES/system.py`:
  - `/stats` — агрегирует метрики через `SystemManager` (users/files/operations, website‑конверсии);
  - `/webhook/conversion-complete` — обновляет статус операции по callback‑запросу.

## 5. Тестирование HTTP‑слоя

Основные тесты лежат в `BACKEND/TESTS`:

- Интеграционные тесты роутеров (`TESTS/integration`):
  - `test_user_routes_integration.py` — CRUD по `/users` и связанные списки;
  - `test_files_routes_integration.py` — загрузка/список/удаление файлов;
  - `test_convert_routes_integration.py` — `/convert`, `/convert/website`, `/operations`, `/websites/*`;
  - `test_download_routes_integration.py` — `/download/{id}` и preview;
  - `test_format_routes_integration.py` — `/formats`, `/formats/input`, `/formats/output`, `/supported-conversions`;
  - `test_system_routes_integration.py` — `/stats`, `/webhook/conversion-complete`;
  - `test_llm_openrouter_integration.py` — отдельный тест реального LLM (через `LlmService`).

- E2E‑тесты (`TESTS/e2e`):
  - `test_flow_file_to_pdf_e2e.py` — `upload → convert(pdf) → download`;
  - `test_flow_file_to_graph_e2e.py` — `upload → convert(graph) → download graph JSON`;
  - `test_flow_website_convert_e2e.py` — `convert/website → status → history`;
  - `test_flow_root_health_e2e.py` — базовый health‑чек.

Запуск всех тестов:

```bash
python -m pytest BACKEND/TESTS -q