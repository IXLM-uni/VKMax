<!-- Руководство к файлу (BACKEND/system_instruction.md)
Назначение:
- Описывает архитектуру backend VKMax: FastAPI, роутеры, сервисы конвертации, LLM_SERVICE и БД.
- Служит точкой входа для понимания, как связаны слои по файлам.
-->

# Архитектура VKMax BACKEND (в разрезе файлов)

## 1. Внешний контур: FastAPI и роутеры

- **FAST_API/fast_api.py**
  - Создаёт `FastAPI`‑приложение (`app`).
  - Настраивает CORS, централизованное логирование и обработку исключений.
  - Вызывает `CONVERT.logging_config.setup_logging()` до создания `app`, чтобы инициализировать логгеры `vkmax.*`.
  - Подключает роутеры:
    - `FAST_API/ROUTES/user.py` — управление пользователями (`/users`).
    - `FAST_API/ROUTES/files.py` — загрузка/управление файлами (`/upload`, `/files`).
    - `FAST_API/ROUTES/convert.py` — создание операций конвертации и статусы (`/convert`, `/operations`, `/websites/...`).
    - `FAST_API/ROUTES/download.py` — скачивание файлов (`/download/{file_id}`).
    - `FAST_API/ROUTES/format.py` — форматы и матрица конвертаций (`/formats`, `/supported-conversions`).
    - `FAST_API/ROUTES/system.py` — системные ручки (`/health`, `/stats`, `/webhook/conversion-complete`).

Взаимодействие (высокоуровнево):

`Клиент (Mini_app / внешний) -> FAST_API/fast_api.py (FastAPI app) -> FAST_API/ROUTES/*.py (эндпоинт)`

Дальше каждый роутер работает через слой менеджеров БД (`DATABASE/CACHE_MANAGER`) и, при необходимости, сервисы `CONVERT` и `LLM_SERVICE`.

## 2. Слой БД: модели и менеджеры

- **DATABASE/models.py**
  - `User` — пользователи VKMax.
  - `File` — загруженные и сгенерированные файлы (оригинал, PDF/DOCX, graph JSON и т.п.).
  - `Format` — справочник форматов (тип, расширение, флаги input/output).
  - `Operation` — операции конвертации (файл-источник, формат до/после, статус, результат).

- **DATABASE/session.py** (по импортам из ROUTES)
  - Фабрика `get_db_session()` — создаёт `AsyncSession` для работы с БД.

- **DATABASE/CACHE_MANAGER/** (пакет, импортируемый как `DATABASE.CACHE_MANAGER`)
  - `FilesManager` — CRUD по файлам (`create_file`, `get_file`, `list_files_page`, `patch_content`, `delete_file`).
  - `ConvertManager` — операции конвертации (`create_file_operation`, `create_website_operation`, `get_operation`, `list_operations`, `update_status`).
  - `DownloadManager` — выдача метаданных для скачивания файлов.
  - `FormatManager` — работа со справочником форматов и матрицей конвертаций.
  - `UserManager` — управление пользователями и их файлами/операциями.
  - `SystemManager` — агрегированные статистики по БД.

Типичная цепочка взаимодействия с БД:

`ROUTES/*.py -> DATABASE/session.get_db_session (AsyncSession) -> DATABASE.CACHE_MANAGER.*Manager -> DATABASE/models.py (ORM)`

## 3. Слой конвертации: пакет CONVERT

- **CONVERT/__init__.py**
  - Экспортирует основные функции и типы:
    - Базовые конвертеры документов: `convert_docx_to_pdf`, `convert_pdf_to_docx`, `extract_plain_text` и др.
    - Сервис файловой конвертации: `run_file_conversion`.
    - Сервис генерации графов: `generate_graph_for_operation`.
    - Web‑parser сервисы: `enqueue_website_job`, `get_website_status`, `build_website_preview`.

- **CONVERT/conversion_service.py**
  - Исполняет файловую конвертацию (DOCX <-> PDF, и т.п.) по операции из БД.
  - Работает поверх `AsyncSession` и менеджеров из `DATABASE.CACHE_MANAGER`.

- **CONVERT/graph_service.py**
  - `generate_graph_for_operation(session, operation_id, storage_dir)`:
    - Читает `Operation` и исходный `File` через `ConvertManager` и `FilesManager`.
    - Извлекает текст документа через `extract_plain_text(...)`.
    - Строит JSON‑граф через `LLM_SERVICE.DocumentGenerator`.
    - Сохраняет итоговый graph JSON в файловую систему и как новый `File` в БД.
    - Обновляет статус `Operation` на `completed`/`failed` через `ConvertManager.update_status(...)`.

- **CONVERT/webparser_service.py**
  - Операции по сайтам (website‑конвертация, превью сайта, статус по history).
  - Используется роутами `/convert/website`, `/websites/preview`, `/websites/history`.

Высокоуровневая связка:

`FAST_API/ROUTES/convert.py -> CONVERT (conversion_service, graph_service, webparser_service) -> DATABASE/CACHE_MANAGER -> DATABASE/models.py`

## 4. LLM слой: LLM_SERVICE

- **LLM_SERVICE/llm_service.py**
  - `LlmService` — низкоуровневый клиент LLM (DeepSeek / mock):
    - Читает настройки из окружения (`VKMAX_LLM_PROVIDER`, `VKMAX_DEEPSEEK_API_KEY`, `DEEPSEEK_BASE_URL`, и т.д.).
    - Предоставляет асинхронный метод `generate(prompt: str) -> str`.

- **LLM_SERVICE/document_generator.py**
  - `DocumentGenerator` — оркестратор поверх `LlmService`,
    - Использует `CleanerService` и `ValidatorService`.
    - По `task_id` и входным данным (например, `document_text`) строит целевой документ.
    - В контексте графа — регистрирует задачу `graph_json` и возвращает JSON‑граф (строка).

- **LLM_SERVICE/cleaner.py**
  - `CleanerService` — нормализация сырого LLM‑ответа по `doc_type` (в т.ч. `graph_json`).

- **LLM_SERVICE/validator.py**
  - `ValidatorService` — проверка и валидация структуры ответа (например, что вернулся корректный JSON).

Связка при генерации графа:

`CONVERT/graph_service.py -> LLM_SERVICE.document_generator.DocumentGenerator -> LLM_SERVICE.llm_service.LlmService -> внешний LLM (DeepSeek или mock)`

## 5. Связи "сквозного" запроса по сценариям

### 5.1. Загрузка файла и конвертация в PDF/DOCX

1. **Загрузка файла**
   - Клиент → `POST /upload`
   - Файл: `FAST_API/ROUTES/files.py:upload_file`
   - Дальше:
     - `files.py` -> `DATABASE.CACHE_MANAGER.FilesManager.create_file(...)` -> `DATABASE/models.File` + запись на диск.

2. **Создание операции конвертации**
   - Клиент → `POST /convert` (body: `ConvertRequest`)
   - Файл: `FAST_API/ROUTES/convert.py:convert`
   - Дальше:
     - `convert.py` -> `ConvertManager.create_file_operation(...)` (создаёт `Operation`).
     - Для `target_format in {"docx", "pdf"}` вызывает `CONVERT.run_file_conversion(...)`.

3. **Выполнение конвертации**
   - `CONVERT/conversion_service.py:run_file_conversion`:
     - Берёт `Operation` и исходный `File` из БД.
     - Вызывает нужный конвертер (`convert_docx_to_pdf`, `convert_pdf_to_docx`, ...).
     - Сохраняет результат как новый `File` и обновляет `Operation.result_file_id`, `status`.

4. **Получение статуса и скачивание**
   - Статус операции: `GET /operations/{operation_id}` → `FAST_API/ROUTES/convert.py:get_operation`.
   - Скачивание результата: `GET /download/{file_id}` → `FAST_API/ROUTES/download.py:download_file`.

### 5.2. Генерация JSON‑графа по документу

1. Клиент создаёт операцию:
   - `POST /convert` с `target_format="graph"`.
   - `FAST_API/ROUTES/convert.py:convert` создаёт `Operation` через `ConvertManager`.
   - Тут же вызывает `CONVERT.generate_graph_for_operation(session, operation_id, storage_dir)`.

2. `CONVERT/graph_service.py:generate_graph_for_operation`:
   - Читает `Operation` и исходный `File` через `ConvertManager` и `FilesManager`.
   - Извлекает текст документа (`extract_plain_text`).
   - Строит JSON‑граф через `DocumentGenerator.create_document(task_id="graph_from_document", document_text=...)`.
   - Сохраняет граф как новый JSON‑файл и `File` в БД.
   - Обновляет `Operation.status` и `Operation.result_file_id`.

3. Клиент периодически опрашивает статус:
   - `GET /operations/{operation_id}` → узнаёт `file_id` результата.
   - Далее может скачивать JSON‑граф через `GET /download/{file_id}`.

### 5.3. Website‑конвертация и превью

1. Клиент создаёт website‑операцию:
   - `POST /convert/website` или `POST /upload/website`.
   - Файлы: `FAST_API/ROUTES/convert.py:convert_website`, `FAST_API/ROUTES/files.py:upload_website`.
   - Оба используют `ConvertManager.create_website_operation(...)` и вызывают `CONVERT.enqueue_website_job(...)` для постановки website‑операции в очередь (MVP‑каркас).

2. Статусы и история:
   - `GET /websites/{operation_id}/status` → `CONVERT.get_website_status(...)`.
   - `GET /websites/history` → `ConvertManager.list_operations(..., type_hint='website')`.

3. Превью сайта:
   - `POST /websites/preview` → `FAST_API/ROUTES/convert.py:website_preview`.
   - Внутри: `CONVERT.build_website_preview(url)`.

## 6. Системные ручки и статистика

- `FAST_API/ROUTES/system.py`:
  - `/health` — проверка статуса приложения.
  - `/stats` — агрегированная статистика по БД через `SystemManager`.
  - `/webhook/conversion-complete` — входящий webhook, который обновляет статус `Operation` через `ConvertManager.update_status(...)`.

Связка:

`Внешние сервисы/webhook -> FAST_API/ROUTES/system.py -> DATABASE/CACHE_MANAGER.SystemManager / ConvertManager -> DATABASE/models.py`

