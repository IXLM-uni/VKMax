<!-- Руководство к файлу (VKMax/README.md)
Назначение:
- Дать единое, всеобъемлющее описание проекта VKMax (backend, бот, мини‑приложение, WebParser, LLM‑слой).
- Объяснить архитектуру каталогов BACKEND и Mini_app/my-app.
- Показать, как запустить проект локально и через Docker, как пользоваться API и тестами.
-->

# VKMax — конвертер документов с JSON‑графами и WebParser

VKMax — это сервис для конвертации документов (PDF/DOCX → PDF/DOCX/JSON‑GRAPH) и сайтов, с поддержкой:

- **файловых конвертаций** (DOCX↔PDF, нормализация DOCX, переупаковка PDF);
- **генерации доменных JSON‑графов** по содержимому документов через LLM (DeepSeek через OpenRouter);
- **конвертации сайтов** с помощью отдельного WebParser;
- **мини‑приложения (Next.js)** для работы пользователем с файлами, графами и историями операций;
- **бота MAX** (каталог `BACKEND/BOT`), который даёт чат‑интерфейс и умеет открывать мини‑аппу.

Backend написан на **FastAPI**, хранение данных — через **SQLAlchemy async** (первый этап — SQLite, целевая БД — Postgres). Все тяжёлые операции (конвертация, LLM, парсинг сайтов) вынесены в сервисный слой и отдельные модули.

---

## 1. Обзор структуры репозитория

Ключевые каталоги:

- `BACKEND/` — серверная часть VKMax:
  - `FAST_API/` — HTTP‑слой, роуты и схемы;
  - `DATABASE/` — модели БД, сессии, CACHE_MANAGER;
  - `SEVICES/` — сервисный слой (оркестрация конвертаций, графов и WebParser);
  - `CONVERT/` — низкоуровневые конвертеры DOCX/PDF и извлечение текста;
  - `LLM_SERVICE/` — клиент LLM (DeepSeek через OpenRouter) и оркестратор DocumentGenerator;
  - `WebParser/` — встроенный быстрый парсер сайтов (обёртка вокруг отдельного проекта WebParser);
  - `BOT/` — бот MAX поверх VKMax API;
  - `TESTS/` — unit/integration/e2e‑тесты backend.

- `Mini_app/my-app/` — фронтенд‑мини‑приложение (Next.js):
  - UI для загрузки файлов, конвертации, просмотра графов и истории операций;
  - документация по API фронта: `API_DOCUMENTATION.md`.

- `docker-compose.yml` — docker‑стек (Postgres, backend API, бот, frontend).

Дополнительно в корне могут лежать вспомогательные файлы (скрипты, README для под‑проектов и т.п.).

---

## 2. Архитектура backend

### 2.1. FAST_API — HTTP‑слой

Каталог `BACKEND/FAST_API` отвечает за HTTP‑API VKMax:

- конфигурация приложения (`config.py`); 
- инициализация FastAPI‑приложения (`fast_api.py`, `run_app.py`);
- роуты в `ROUTES/`:
  - `user.py` — пользователи и связанные списки файлов/операций;
  - `files.py` — загрузка, список, удаление файлов; `POST /upload`, `POST /upload/website`;
  - `convert.py` — создание операций конвертации файлов и сайтов, статусы `/operations`, `/websites/*`;
  - `download.py` — скачивание/preview файлов по `file_id`;
  - `format.py` — список форматов и матрица поддерживаемых конвертаций;
  - `system.py` — `/health`, `/stats`, `/webhook/conversion-complete`;
  - `graph.py` — получение/генерация JSON‑графов по файлам (`GET/POST /graph/{file_id}`).

FastAPI‑слой **минимален по логике** и работает через сервисы (`SEVICES`) и CACHE_MANAGER (`DATABASE`).

Ключевые свойства конфигурации (`config.Settings`):

- `base_dir` — базовая директория проекта;
- `storage_dir`, `tmp_dir`, `logs_dir` — каталоги для файлов, временных файлов и логов;
- `max_upload_mb` — лимит размера загружаемого файла (по умолчанию 40 МБ);
- `cors_origins` — разрешённые Origin для фронта;
- параметры подключения к БД и LLM (через .env).

### 2.2. DATABASE — модели и менеджеры

Каталог `BACKEND/DATABASE` содержит всё, что связано с постоянным хранением данных:

- `models.py` — ORM‑модели:
  - `User` — пользователи VKMax;
  - `File` — файлы с путями на диске, форматами, размерами;
  - `Operation` — операции конвертации (file/website), статусы, связи;
  - `Format` — справочник форматов (`pdf`, `docx`, `html`, `graph`, `url`).
- `session.py` — асинхронный `engine`, `async_session_factory`, dependency `get_db_session`.
- `alembic.py` — вспомогательные функции `create_tables()` и `seed_formats()` для начальной схемы БД.
- `CACHE_MANAGER/` — менеджеры поверх моделей:
  - `user.py`, `files.py`, `convert.py`, `download.py`, `format.py`, `system.py`.

FastAPI‑роуты всегда работают через `AsyncSession = Depends(get_db_session)` и менеджеры, без сырых SQL.

### 2.3. SEVICES — сервисный слой

Каталог `BACKEND/SEVICES` (опечатка имени сохранена намеренно) — прослойка между HTTP‑слоем и низкоуровневыми модулями:

- `conversion_service.py` — оркестрация файловых конвертаций:
  - создаёт/обновляет `Operation` через `ConvertManager`;
  - вызывает функции из `CONVERT/converters.py` (`convert_docx_to_pdf`, `convert_pdf_to_docx`, `convert_docx_to_docx`, `convert_pdf_to_pdf`);
  - создаёт результат `File` через `FilesManager` и проставляет `result_file_id`;
  - логирует шаги и ошибки, выставляет статус `failed` при падениях.

- `graph_service.py` — высокоуровневая работа с JSON‑графами:
  - ищет уже сгенерированный граф по `source_file_id`;
  - при необходимости создаёт новую `Operation` типа `graph`, вызывает `BACKEND.CONVERT.generate_graph_for_operation` и возвращает готовый graph JSON.

- `webparser_service.py` — связка с WebParser:
  - создаёт `website`‑операции;
  - запускает WebParser для скачивания сайта и сохранения результата как `File`;
  - предоставляет API для статусов/истории/превью сайтов.

Отдельно используется `logging_config` (фактическая реализация в `BACKEND/CONVERT/logging_config.py`) — единая настройка логирования (`vkmax.fastapi`, `vkmax.db`, `vkmax.convert`, `vkmax.llm`, `vkmax.webparser`).

### 2.4. CONVERT — низкоуровневые конвертеры

Каталог `BACKEND/CONVERT` содержит чистые функции конвертации и извлечения текста. Основные принципы (см. `BACKEND/CONVERT/INSTRUCTIONS.MD`):

- Вход: `DOCX`, `PDF`.
- Выход: `DOCX`, `PDF`, `GRAPH` (JSON‑граф).
- Внутреннее представление — условный `InternalDoc`:
  - `plain_text` (до **10 000 слов** для LLM);
  - `meta` (язык, размер, страницы);
  - опциональный `html` — только там, где реально нужен для PDF.

Стандартные пайплайны:

- **DOCX → PDF**: DOCX → HTML (mammoth) → PDF (pdfkit/wkhtmltopdf).
- **DOCX → JSON‑GRAPH**: DOCX → `plain_text` → обрезка до 10k слов → LLM (`graph_from_document`) → outline → Python‑функция строит итоговый граф (`nodes`/`edges`/`meta`).
- **PDF → DOCX**: через `pdf2docx`.
- **PDF → JSON‑GRAPH**: PDF → `plain_text` (через PyMuPDF или PDF→DOCX→text) → LLM → граф.

Требования:

- потоковая/страничная обработка крупных файлов;
- строгий контракт ввода/вывода (входной путь + формат → выходной путь + формат или контролируемое исключение);
- отсутствие зависимости от FastAPI и CACHE_MANAGER;
- изоляция LLM: сами конвертеры работают только с файлами и текстом.

### 2.5. LLM_SERVICE — работа с LLM

Каталог `BACKEND/LLM_SERVICE` (структура описана отдельно) включает:

- `LlmService` — клиент DeepSeek через OpenRouter;
- `DocumentGenerator` — оркестратор задач типа `graph_from_document`;
- `CleanerService`, `ValidatorService` — очистка и валидация структур JSON/HTML/Mermaid/plain.

LLM_SERVICE принимает `plain_text` и метаданные от конвертеров и возвращает строковый JSON‑outline, который затем преобразуется в итоговый граф.

### 2.6. WebParser — конвертация сайтов

Каталог `BACKEND/WebParser` содержит встроенную часть WebParser (см. отдельный проект `/home/alexander/Projects/WebParser` и `BACKEND/WebParser/INSTRUCTIONS.md`):

- вход: список seed‑URL;
- выход: граф ссылок (nodes, edges), экспорт в `edges.csv` и `graph.json`;
- стек: Playwright APIRequestContext, Selectolax, aiolimiter, tldextract, orjson;
- архитектура: core/utils/robots/fetch/parse/frontier/graph/orchestrator/cli;
- асинхронность и лимиты по хостам.

Через сервис `webparser_service` WebParser интегрируется с БД и HTTP‑роутами (`/upload/website`, `/convert/website`, `/websites/*`).

### 2.7. BOT — чат‑бот MAX

Каталог `BACKEND/BOT` описан в `BACKEND/BOT/INSTRUCTIONS.MD` и содержит слой чат‑бота MAX поверх VKMax‑API.

Основное:

- `config.py` — `BotConfig` c переменными окружения:
  - `VKMAX_BOT_TOKEN` — токен бота MAX;
  - `VKMAX_FASTAPI_BASE_URL` — базовый URL FastAPI VKMax;
  - `VKMAX_BOT_DEBUG` — детальное логирование;
  - при необходимости `VKMAX_ADMIN_TOKEN` для защищённых ручек.
- `logging_config.py` — настройка логгера `vkmax.bot`.
- `run_bot.py` — точка входа бота (`python -m BACKEND.BOT.run_bot`).
- `KEYBOARDS/` — билдеры клавиатур, включая кнопку открытия мини‑аппы (WebAppButton).
- `ROUTERS/` — роутеры команд:
  - приветствие, `/start`, главное меню;
  - `/ping`, `/stats` (через `VkmaxApiClient.get_stats`);
  - `/files`, `/formats`, `/convert`, заглушка `/download`;
  - `/app` — команда для открытия мини‑приложения VKMax.
- `SERVICES/` — HTTP‑клиенты к VKMax FastAPI и (опционально) platform‑api.max.ru.

Бот **не содержит бизнес‑логики конвертации**, а только вызывает HTTP‑слой VKMax.

### 2.8. TESTS — архитектура тестов

Каталог `BACKEND/TESTS` документирован в `BACKEND/TESTS/INSTRUCTIONS.MD`.

Уровни тестов:

- unit — чистые функции (конвертеры, LLM_SERVICE, cleaner/validator);
- integration — FastAPI + тестовая БД + сервисный слой;
- e2e/flow — полный путь `upload → convert → download/graph/website`.

`conftest.py` предоставляет общий event loop, инициализацию тестовой БД и HTTP‑клиент для FastAPI‑приложения.

---

## 3. Фронтенд: Mini_app/my-app

Каталог `Mini_app/my-app` — это Next.js‑мини‑приложение для работы с VKMax:

- загрузка файлов и сайтов;
- выбор форматов конвертации;
- просмотр истории операций и статусов;
- просмотр доменных JSON‑графов (с отображением через React Flow/диаграммы);
- интеграция с MAX WebApp (открытие мини‑аппы из бота).

API‑контракт подробно описан в `Mini_app/my-app/API_DOCUMENTATION.md` (на английском), включая:

- `/users` — создание/получение/удаление пользователей;
- `/upload`, `/files` — управление файлами;
- `/convert`, `/operations` — создание и статус конвертаций;
- `/download/{fileId}` — скачивание файлов;
- `/formats` — список форматов;
- `/graph/{fileId}` — получение/генерация JSON‑графа;
- `/llm` — примеры интеграции с LLM;
- коды ответов и примеры mock‑данных.

Фронт обращается к backend по базовому URL, задаваемому переменной окружения `NEXT_PUBLIC_API_URL` (см. `docker-compose.yml`).

---

## 4. Поддерживаемые форматы и конвертация

Текущие основные форматы v1:

- **Вход:** `PDF`, `DOCX`, `URL` (для сайтов);
- **Выход:** `PDF`, `DOCX`, `GRAPH` (JSON‑граф), HTML/другие технические форматы внутри.

Ограничения и принципы:

- лимит размера загружаемого файла — **40 МБ** (на уровне FastAPI);
- для LLM используется только первые **10 000 слов** текста документа;
- тяжелые операции (PDF→DOCX, сайты) максимально потоковые и экономные по памяти;
- LLM‑конверсия (графы) вынесена в отдельный слой `LLM_SERVICE`.

Матрица поддерживаемых конвертаций и список форматов доступны через `/formats` и `/supported-conversions` (см. `FAST_API/ROUTES/format.py`).

---

## 5. Запуск проекта

### 5.1. Подготовка окружения (локально)

1. Создать и активировать виртуальное окружение Python (пример для Linux/macOS):

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. Настроить переменные окружения в `BACKEND/.env` или аналогичном файле:

   Минимальный набор (пример, значения адаптировать под окружение):

   ```bash
   # БД (SQLite или Postgres)
   VKMAX_DATABASE_URL="sqlite+aiosqlite:///./vkmax.db"  # или Postgres URL

   # Директории хранения
   VKMAX_STORAGE_DIR="./storage"
   VKMAX_TMP_DIR="./storage/tmp"
   VKMAX_LOGS_DIR="./storage/logs"

   # Лимиты
   VKMAX_MAX_UPLOAD_MB=40

   # LLM / OpenRouter
   VKMAX_OPENROUTER_API_KEY="<your_openrouter_key>"
   VKMAX_LLM_PROVIDER="deepseek"

   # CORS для фронта
   VKMAX_CORS_ORIGINS="[\"http://localhost:3000\"]"

   # Токены бота MAX
   VKMAX_BOT_TOKEN="<max_bot_token>"
   VKMAX_FASTAPI_BASE_URL="http://localhost:8000"
   ```

3. При первом запуске создать таблицы и заполнить справочник форматов (см. `DATABASE/alembic.py`) — при использовании тестового/вспомогательного скрипта или отдельной команды (детали зависят от ваших сценариев запуска).

### 5.2. Запуск backend (FastAPI) локально

Из корня проекта:

```bash
uvicorn BACKEND.FAST_API.run_app:app --reload --port 8000
```

После этого HTTP‑API будет доступен по `http://localhost:8000`.

### 5.3. Запуск бота MAX локально

При условии, что `VKMAX_BOT_TOKEN` и `VKMAX_FASTAPI_BASE_URL` заданы:

```bash
python -m BACKEND.BOT.run_bot
```

Бот подключится к серверам MAX, начнёт long polling и сможет вызывать HTTP‑API VKMax.

### 5.4. Запуск фронтенда локально

Перейти в каталог `Mini_app/my-app` и выполнить команды (пример):

```bash
cd Mini_app/my-app
npm install
npm run dev
```

Перед запуском убедиться, что `NEXT_PUBLIC_API_URL` указывает на работающий backend, например:

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 5.5. Запуск через Docker Compose

В корне репозитория есть `docker-compose.yml`, который поднимает:

- **db** — контейнер Postgres (`vkmax_db`), внешний порт `25432`;
- **api** — backend VKMax (`vkmax_api`), порт `8157` → `8000` внутри контейнера;
- **bot** — бот MAX, использующий тот же образ, что `api`;
- **frontend** — Next.js‑приложение (`vkmax_frontend`), порт `3000`.

Шаги:

1. Подготовить файл `BACKEND/.env.compose` с переменными окружения для контейнеров (БД, LLM, токены бота, пути к storage/logs и т.п.).
2. Запустить стек:

   ```bash
   docker compose up --build
   ```

После успешного старта:

- backend‑API доступен по `http://localhost:8157`;
- фронт — по `http://localhost:3000`;
- бот подключается к MAX и использует `VKMAX_FASTAPI_BASE_URL` внутри контейнера (как правило, `http://api:8000`).

---

## 6. Тестирование

Запуск тестов backend (из корня репозитория):

```bash
python -m pytest BACKEND/TESTS -q
```

При запуске интеграционных и e2e‑тестов используется тестовая БД и FastAPI‑приложение в памяти (через `httpx.AsyncClient` и ASGITransport). `conftest.py` автоматически создаёт таблицы и заполняет базовый набор форматов.

Рекомендуется постепенно покрывать:

- unit‑тестами — конвертеры, LLM_SERVICE (в mock‑режиме), cleaner/validator;
- integration‑тестами — основные роуты (`/upload`, `/convert`, `/download`, `/graph`, `/websites/*`);
- e2e‑тестами — полные сценарии `file → pdf`, `file → graph`, `website → pdf/graph`.

---

## 7. Дальнейшее развитие

Планы и направления развития системы VKMax:

- переход на полноценные миграции Alembic для `DATABASE`;
- расширение набора форматов (например, `pptx`, `xlsx`, дополнительные графовые форматы);
- оптимизация WebParser и добавление fallback‑браузера с блокировкой ресурсоёмких ресурсов;
- расширение сценариев бота (FSM‑диалоги, интеграция с MAX WebApp‑авторизацией);
- улучшение UX мини‑приложения (глубокие ссылки из бота, больше визуализации графов);
- доработка мониторинга и метрик (`/stats`, логи, request_id, дашборды).

За деталями по конкретным модулям обращайтесь к локальным инструкциям:

- `BACKEND/FAST_API/INSTRUCTIONS.MD`
- `BACKEND/DATABASE/INSTRUCTIONS.MD`
- `BACKEND/SEVICES/INSTRUCTIONS.MD`
- `BACKEND/CONVERT/INSTRUCTIONS.MD`
- `BACKEND/TESTS/INSTRUCTIONS.MD`
- `BACKEND/BOT/INSTRUCTIONS.MD`
- `BACKEND/WebParser/INSTRUCTIONS.md`
- `Mini_app/my-app/API_DOCUMENTATION.md`

