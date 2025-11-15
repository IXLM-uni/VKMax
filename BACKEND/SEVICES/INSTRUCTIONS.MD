# Руководство к каталогу BACKEND/SEVICES

## 1. Назначение

Каталог `SEVICES` (опечатка сохранена намеренно, изменять не будем) содержит
**сервисный слой** VKMax — прослойку между FastAPI‑роутами и низкоуровневыми
модулями:

- `DATABASE` / `CACHE_MANAGER` — работа с БД;
- `CONVERT` — конвертеры DOCX/PDF и извлечение текста;
- `LLM_SERVICE` — DeepSeek + оркестратор LLM;
- `WebParser` — скачивание/подготовка сайтов.

Сервисы **НЕ** зависят от FastAPI напрямую, но могут использовать модели БД,
конвертеры и LLM‑клиент. FastAPI вызывает только сервисы, а не низкоуровневые
слои напрямую (кроме простых GET‑роутов).

Отдельная задача сервизного слоя — **единый стиль логирования** поверх всех
операций.

---

## 2. Модули сервисного слоя

### 2.1. `conversion_service.py`

Задача: оркестрация конвертации файлов (DOCX/PDF → DOCX/PDF) и связка с БД.

Ответственность:

- Создавать/обновлять записи в таблице `OPERATIONS` через `ConvertManager`.
- Для операций файлового типа вызывать функции из `CONVERT/converters.py`:
  - `convert_docx_to_pdf`, `convert_pdf_to_docx`,
    `convert_docx_to_docx`, `convert_pdf_to_pdf`.
- После успешной конвертации создавать новую запись `File` через `FilesManager`
  и проставлять `result_file_id` в операции.
- При ошибках:
  - логировать **полный stacktrace**;
  - обновлять операцию статусом `failed` и полем `error_message`.

Публичные функции (идея, без кода):

- `async run_file_conversion(operation_id: int) -> None`
  - По `operation_id` находит операцию и исходный файл, решает, какой
    конвертер запустить, создаёт итоговый файл и обновляет операцию.
- `async enqueue_conversions_for_batch(operation_ids: list[int]) -> None`
  - Вариант для batch‑операций (по необходимости).

Вызывается из FastAPI (роут `/convert`) в фоновом режиме или воркером.

---

### 2.2. `graph_service.py`

Задача: **высокоуровневая работа с JSON‑графами по файлам VKMax**.

Важно различать два слоя:

- Низкоуровневый LLM‑пайплайн находится в `BACKEND.CONVERT.graph_service`
  (извлечение текста, вызов LLM, построение graph JSON и сохранение в файл).
- Текущий модуль `BACKEND.SEVICES.graph_service` работает как тонкий
  оркестратор поверх БД и CONVERT‑сервиса и не содержит LLM‑логики.

Ответственность `SEVICES.graph_service`:

- Найти уже сгенерированный граф по исходному `file_id`:
  - через `Operation` с `status="completed"`, `file_id=...` и `Format.type="graph"`;
  - прочитать JSON из `File.path` и вернуть как `GraphJson`.
- Создать новую операцию генерации графа по `file_id` и дождаться результата:
  - выбрать формат `graph` через `Format`;
  - создать `Operation` через `ConvertManager.create_file_operation`;
  - вызвать `BACKEND.CONVERT.generate_graph_for_operation(...)`, который
    выполняет LLM‑пайплайн и создаёт файл результата;
  - затем снова использовать поиск, чтобы вернуть итоговый graph JSON.

Публичные функции (фактическая реализация):

- `async get_graph_for_file(session, *, source_file_id: int) -> Optional[dict]`
  - Возвращает ранее сохранённый граф для файла или `None`, если его нет.

- `async generate_graph_for_file(session, *, source_file_id: int, user_id: Optional[int], storage_dir: str) -> dict`
  - Создаёт операцию, запускает генерацию графа через CONVERT и возвращает
    готовый graph JSON (кидает исключение при фатальной ошибке).

Вызывается из FastAPI (роуты `/graph/{file_id}`) или воркером/внешними задачами.

---

### 2.3. `webparser_service.py`

Задача: связать `WebParser` с FastAPI и БД.

Ответственность:

- Создавать операции типа `website` через `ConvertManager.create_website_operation`.
- Запускать WebParser (внутренний модуль или отдельный процесс) для скачивания
  сайта и получения HTML/файла.
- После успешного парсинга создавать `File` (HTML/PDF) и обновлять операцию.
- Предоставлять API для:
  - получения статуса `website`‑операции;
  - истории конвертаций сайтов;
  - быстрого превью сайта (title/description/screenshot).

Публичные функции (идея):

- `async enqueue_website_job(operation_id: int) -> None`
- `async get_website_status(operation_id: int) -> dict`
- `async build_website_preview(url: str) -> dict`

Вызывается из `/upload/website`, `/convert/website`, `/websites/*` роутов.

---

### 2.4. `logging_config.py`

Задача: единая точка настройки логирования для всего BACKEND.

Фактическая реализация сейчас находится в модуле
`BACKEND/CONVERT/logging_config.py` (исторически относилась к сервисному слою).

Ответственность:

- Настроить root‑логгер и формат:
  - время, уровень, модуль, функция, строка, сообщение;
  - писать в stdout (для удобства docker/uvicorn).
- Определить базовые логгеры:
  - `vkmax.fastapi` — всё, что связано с FastAPI (роуты, middleware);
  - `vkmax.db` — менеджеры БД, Alembic;
  - `vkmax.convert` — конвертеры файлов и граф‑сервисы;
  - `vkmax.llm` — LLM_SERVICE;
  - `vkmax.webparser` — WebParser.
- Вызывать `setup_logging()` **до** создания FastAPI‑приложения
  (см. `FAST_API/fast_api.py`).

Важное требование: при любой необработанной ошибке должен логироваться
stacktrace, чтобы сразу видеть, **какая функция/строка упала**.

---

## 3. Связь сервисов с FastAPI

1. `FAST_API/fast_api.py`:
   - Импортирует `setup_logging()` из `BACKEND.CONVERT.logging_config` и
     вызывает его до создания `app`.
   - В exception‑handlers использует `logger.exception(...)` для логирования
     stacktrace.
   - (Опционально) добавляет middleware с `request_id` и пишет его в каждый лог.

2. Роуты:

   - `ROUTES/convert.py`:
     - вместо прямого использования `ConvertManager` (или в дополнение к нему)
       вызывает функции `conversion_service` и `graph_service` для запуска
       конвертации/генерации графа.
     - все ошибки должны проходить через сервис, который обновляет статус
       операции и логирует подробности.

   - `ROUTES/files.py`, `ROUTES/download.py`:
     - могут продолжать работать напрямую с `FilesManager`/`DownloadManager`,
       но должны использовать логгер `vkmax.fastapi.files` и писать ключевые
       события (upload, delete, download).

   - `ROUTES/system.py`, `ROUTES/user.py`, `ROUTES/format.py`:
     - логировать вход/выход и ошибки через модульный логгер.

3. Воркер/фоновые задачи:

   - Конвертация и LLM‑операции должны выполняться **вне** основной ручки, чтобы
     не блокировать запрос:
     - через `BackgroundTasks` FastAPI;
     - или через отдельный воркер (Celery/RQ/собственный loop), который дергает
       сервисные функции по `operation_id`.
   - Во всех случаях логирование должно содержать:
     - `operation_id`, `file_id`, тип операции, целевой формат.

---

## 4. Требования к логированию

- Каждый сервисный метод обязан логировать:
  - старт: входные идентификаторы (operation_id, file_id, user_id, url);
  - успешное завершение: итоговый статус, `result_file_id` и ключевые метрики
    (например, количество страниц, длина текста);
  - ошибку: `logger.exception(...)` с понятным сообщением и контекстом.

- Логи должны позволять по одному `operation_id` проследить весь путь:
  FastAPI → сервис → БД → конвертеры → LLM → обратно в БД.