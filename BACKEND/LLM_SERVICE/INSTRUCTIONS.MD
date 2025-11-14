# Руководство к каталогу BACKEND/LLM_SERVICE

## 1. Назначение

Каталог `BACKEND/LLM_SERVICE` содержит **LLM‑слой VKMax**:

- низкоуровневый клиент `LlmService` для общения с DeepSeek через OpenRouter;
- фасад `LLMRouter` для унификации формата сообщений и возможных tool‑calls;
- сервисы пост‑обработки ответа модели: `CleanerService`, `ValidatorService`;
- высокоуровневый оркестратор `DocumentGenerator` для задач вроде генерации графа.

Основная идея: FastAPI/сервисы передают сюда уже подготовленный `plain_text`
и параметры задачи, LLM‑слой делает всё остальное (генерация, очистка, валидация).

## 2. Структура модулей

- `llm_service.py`
  - Класс `LlmService`.
  - Поддерживаемые провайдеры через `VKMAX_LLM_PROVIDER`:
    - `deepseek` — реальный вызов через OpenRouter (`/api/v1/chat/completions`);
    - `mock` — режим без сети, возвращает тестовую строку.
  - Параметры берутся из окружения либо передаются в конструктор:
    - модель: `VKMAX_LLM_MODEL_NAME` / `VKMAX_OPENROUTER_MODEL_NAME` / `OPENROUTER_MODEL_NAME`
      (по умолчанию `deepseek/deepseek-chat`);
    - ключи: `VKMAX_OPENROUTER_API_KEY` / `OPENROUTER_API_KEY` / `VKMAX_DEEPSEEK_API_KEY` / `DEEPSEEK_API_KEY`;
    - база URL: `VKMAX_OPENROUTER_BASE_URL` / `OPENROUTER_BASE_URL`
      (по умолчанию `https://openrouter.ai/api/v1`);
    - температура: `VKMAX_LLM_TEMPERATURE` (по умолчанию `0.2`).

- `router.py`
  - Класс `LLMRouter` и вспомогательные `ToolSpec`, `ToolCall`, `ProviderResponse`.
  - Конкатенирует список сообщений в один текстовый промпт и делегирует вызов в `LlmService`.
  - Зарезервирован под будущую поддержку инструментов/tool‑calls.

- `cleaner.py`
  - Класс `CleanerService`.
  - Приводит сырой текст из LLM к необходимому формату:
    - `json` / `json_reasons` / `graph_json` — вырезает markdown‑ограждения ``` и
      возвращает первую целостную JSON‑структуру (`{}` или `[]`);
    - `html` — убирает ```html‑ограждения;
    - `mermaid` — убирает ```mermaid/``` и возвращает тело графа;
    - прочие типы — тривиальный `strip()`.

- `validator.py`
  - Класс `ValidatorService`.
  - Реестр Pydantic‑схем по ключу `(doc_type, prompt_id)`.
  - Метод `validate(data, doc_type, prompt_id, rules=None)`:
    - при строковом `data` пробует сделать `json.loads`, иначе оставляет как есть;
    - использует `schema.model_validate()` (Pydantic v2) или `parse_obj` для валидации;
    - логирует ошибки и пробрасывает `ValidationError`.

- `document_generator.py`
  - Класс `DocumentGenerator` — высокоуровневый оркестратор задач LLM.
  - Принимает на вход `llm_service`, `cleaner_service`, `validator_service` и `registry`.
  - `registry[task_id]` описывает задачу: `prompt_template`, `doc_type`, доп. параметры.
  - Ключевые методы:
    - `_attempt_once(prompt, doc_type, prompt_id)` — один проход LLM → cleaner → validator;
    - `worker_work(task_id, **prompt_vars)` — несколько попыток, логирование, история ошибок;
    - `create_document(task_id, **prompt_vars)` — удобная обёртка над `worker_work`.

## 3. Конфигурация и .env

Минимальный пример `.env` для реального DeepSeek через OpenRouter
(**никогда не коммить реальные ключи в Git**):

```bash
VKMAX_LLM_PROVIDER=deepseek
VKMAX_OPENROUTER_API_KEY="sk-or-..."
VKMAX_LLM_MODEL_NAME="deepseek/deepseek-chat"
```

В тестах файл `BACKEND/TESTS/conftest.py` загружает `BACKEND/.env` через `python-dotenv`
до импорта FastAPI‑приложения, поэтому `LlmService` видит эти переменные и может
ходить в реальный OpenRouter/DeepSeek.

Для отключения настоящих вызовов достаточно выставить:

```bash
VKMAX_LLM_PROVIDER=mock
```

В этом режиме `LlmService.generate()` возвращает тестовую строку и вообще не
обращается к сети.

## 4. Типичный сценарий использования

1. Сервис/роут собирает `plain_text` документа и параметры.
2. В `DocumentGenerator.registry` заранее зарегистрирована задача, например
   `"graph_from_document"` c `doc_type="graph_json"` и промптом.
3. Код вызывает `await document_generator.worker_work("graph_from_document", text=...)`.
4. Внутри происходит:
   - генерация промпта по шаблону;
   - вызов `LlmService.generate()` (DeepSeek/OpenRouter или mock);
   - очистка через `CleanerService`;
   - валидация через `ValidatorService` в строгую Pydantic‑схему;
   - повторные попытки при ошибках (до `max_attempts`).

Результат — Pydantic‑модель или сырая строка (в зависимости от схемы).

## 5. Тестирование LLM‑слоя

Тесты лежат в `BACKEND/TESTS`:

- Unit‑тесты:
  - `unit/test_cleaner_unit.py` — сценарии очистки JSON/HTML/Mermaid/plain.
  - `unit/test_validator_unit.py` — регистрация схем, разбор JSON‑строк, ошибки валидации.

- Интеграционные тесты:
  - `integration/test_llm_openrouter_integration.py` — реальный вызов DeepSeek через
    OpenRouter, если настроен ключ и провайдер не `mock`.
    - Тест помечен `@pytest.mark.asyncio` и имеет `skipif` для случая
      отсутствия ключей/использования `mock`.

Рекомендуется:

- держать основную массу тестов в `mock`‑режиме (быстро и без внешних зависимостей);
- использовать отдельные интеграционные тесты для проверки связи с реальным LLM.