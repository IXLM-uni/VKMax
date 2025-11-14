ВОТ ПРИМЕР ИЗ ДРУГОГО ПРОЕКТА РЕАЛИЗАЦИИ LLM_SERVICE ТОЛЬКО НАМ  НУЖНО ИСПОЛЬЗОВАТЬ DEEPSEEK ПРОВАЙДЕРА. 

class LlmService:
    """Простой исполнитель для общения с LLM (Gemini/xAI Grok).

    Он умеет отправить промпт и вернуть сырой текст, выбирая провайдера
    на основании настроек (settings.llm_provider).
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> None:
        provider = (settings.llm_provider or "gemini").lower()
        self.provider: str = provider
        if provider == "gemini":
            self.model_name: str = model_name or settings.gemini_model_name
        else:
            # xAI/Grok
            self.model_name: str = model_name or settings.xai_model_name
        self.temperature: float = temperature or settings.llm_temperature

        try:
            if provider == "gemini":
                # Инициализация клиента Gemini
                self.model = genai.GenerativeModel(self.model_name)
                self.router = None
            elif provider == "xai":
                # Инициализация роутера для xAI/Grok
                self.model = None  # type: ignore[assignment]
                self.router = LLMRouter(
                    provider="xai",
                    model_name=self.model_name,
                    temperature=self.temperature,
                    xai_api_key=settings.xai_api_key,
                    xai_base_url=str(settings.xai_base_url),
                    xai_tool_choice=settings.xai_tool_choice,
                )
            else:
                raise ValueError(f"Unsupported LLM provider: {provider}")
        except Exception as exc:  # pragma: no cover – критическая инициализация
            logger.critical(
                "Не удалось инициализировать LlmService '%s' (provider=%s): %s",
                self.model_name,
                provider,
                exc,
                exc_info=True,
            )
            raise RuntimeError("LLM initialization failed") from exc

    async def generate(self, prompt: str) -> str:  # noqa: D401 – простая сигнатура
        """Асинхронно отправляет *prompt* в LLM и возвращает ответ без пост-обработки."""

        # Лог: длина и превью промпта перед отправкой в модель
        try:
            logger.debug(
                "[LlmService.generate] Sending prompt to '%s' via %s (len=%s):\n%s",
                self.model_name,
                self.provider,
                len(prompt),
                prompt,
            )
        except Exception:
            pass

        if self.provider == "gemini":
            # Нативный вызов Gemini SDK
            try:
                response = await self.model.generate_content_async(  # type: ignore[attr-defined]
                    [
                        {
                            "role": "user",
                            "parts": [
                                {"text": prompt},
                            ],
                        }
                    ],
                    generation_config={
                        "temperature": self.temperature,
                    },
                )
            except Exception as exc:
                logger.error("Gemini error (LlmService.generate): %s", exc, exc_info=True)
                raise

            if not response.candidates:
                raise RuntimeError("LLM не вернула кандидатов ответа")

            candidate = response.candidates[0]
            part0 = (
                candidate.content.parts[0]
                if candidate.content and candidate.content.parts
                else None
            )

            if part0 is None or getattr(part0, "text", None) is None:
                raise RuntimeError("LLM ответ без текстовой части")

            return part0.text  # type: ignore[return-value]

        # Провайдер xAI/Grok через LLMRouter
        try:
            messages = [{"role": "user", "parts": [{"text": prompt}]}]
            router_resp = await self.router.send(messages, tools=None, tool_specs=None, temperature=self.temperature)  # type: ignore[arg-type]
        except Exception as exc:
            logger.error("xAI/Grok error (LlmService.generate): %s", exc, exc_info=True)
            raise

        if router_resp.blocked:
            raise RuntimeError(f"LLM response blocked: {router_resp.block_reason}")
        if not router_resp.text:
            raise RuntimeError("LLM не вернула текстовый ответ")
        return router_resp.text


class CleanerService:
    """Сервис для приведения текста к нужному формату.

    Поддерживает разные *doc_type*: ``json``, ``html`` и т.д.
    """

    # Карта типов документа → приватный метод чистки
    _DISPATCH_MAP: Dict[str, str] = {
        "json": "_clean_json",
        "html": "_clean_html",
        "json_reasons": "_clean_json",
    }

    async def clean(self, text: str, doc_type: str) -> str:  # noqa: D401
        """Асинхронный диспетчер чистки.

        Если *doc_type* не зарегистрирован, используется тривиальная `_clean_plain`.
        """

        method_name = self._DISPATCH_MAP.get(doc_type.lower(), "_clean_plain")
        cleaner_fn = getattr(self, method_name)
        return cleaner_fn(text)

    # ------------------------------------------------------------------
    # Приватные реализации чистки
    # ------------------------------------------------------------------

    def _clean_json(self, text: str) -> str:
        """Удаляет markdown-ограждения и берёт первую JSON-структуру."""

        import re

        # Удаляем ```json или просто ```
        cleaned = re.sub(r"```(?:json)?", "", text, flags=re.IGNORECASE).strip()

        # Ищем первое вхождение { или [
        start_obj = cleaned.find("{")
        start_arr = cleaned.find("[")
        if start_obj == -1 and start_arr == -1:
            return cleaned  # JSON-структура не найдена

        start_idx = (
            start_obj
            if start_obj != -1 and (start_obj < start_arr or start_arr == -1)
            else start_arr
        )

        # Пробуем найти совпадающую закрывающую скобку простым стеком
        stack: list[str] = []
        end_idx: Optional[int] = None
        for i, ch in enumerate(cleaned[start_idx:], start=start_idx):
            if ch in "[{":
                stack.append(ch)
            elif ch in "}]":
                if not stack:
                    break
                stack.pop()
                if not stack:
                    end_idx = i + 1
                    break

        return cleaned[start_idx:end_idx] if end_idx else cleaned[start_idx:]

    def _clean_html(self, text: str) -> str:
        import re

        cleaned = re.sub(r"```(?:html)?", "", text, flags=re.IGNORECASE).strip()
        return cleaned

    def _clean_plain(self, text: str) -> str:
        return text.strip()


class ValidatorService:
    """Проверяет данные на соответствие Pydantic-схемам."""

    def __init__(self, schema_map: Optional[Dict[Tuple[str, str], type[BaseModel]]] = None) -> None:
        # Ключ – (doc_type, prompt_id)
        self._schema_map: Dict[Tuple[str, str], type[BaseModel]] = schema_map or {}

    # --------------------------------------------------------------
    # API
    # --------------------------------------------------------------

    def register_schema(self, doc_type: str, prompt_id: str, schema_cls: type[BaseModel]) -> None:
        """Регистрирует новую схему проверки."""

        self._schema_map[(doc_type, prompt_id)] = schema_cls

    async def validate(self, data: str, doc_type: str, prompt_id: str, rules: Any | None = None) -> BaseModel:  # noqa: D401
        """Асинхронно валидирует *data* согласно Pydantic-схеме.

        Возвращает валидированный объект или кидает ``ValidationError`` / ``ValueError``.
        """

        schema_cls = self._schema_map.get((doc_type, prompt_id))
        if not schema_cls:
            raise ValueError(f"Схема для ({doc_type!r}, {prompt_id!r}) не зарегистрирована")

        # Если передан json-стринг – разбираем
        obj: Any = data
        if isinstance(data, str):
            import json

            try:
                obj = json.loads(data)
            except json.JSONDecodeError:
                # Оставляем как есть – схема сама может ожидать str
                pass

        try:
            # Pydantic V2: используем model_validate вместо устаревшего parse_obj
            validate_fn = getattr(schema_cls, "model_validate", None)
            if callable(validate_fn):
                return validate_fn(obj)  # type: ignore[return-value]
            # Fallback на parse_obj для совместимости с V1
            return schema_cls.parse_obj(obj)  # type: ignore[return-value]
        except ValidationError as exc:
            logger.error("Validation failed for (%s, %s): %s", doc_type, prompt_id, exc)
            raise


class DocumentGenerator:
    """Высокоуровневый оркестратор создания документов.

    Он координирует генерацию, чистку и валидацию с повторными попытками.
    """

    def __init__(
        self,
        llm_service: LlmService,
        cleaner_service: CleanerService,
        validator_service: ValidatorService,
        *,
        registry: Optional[Dict[str, Any]] = None,
        max_attempts: int = 3,
    ) -> None:
        self.llm = llm_service
        self.cleaner = cleaner_service
        self.validator = validator_service
        self.max_attempts = max_attempts
        self.registry: Dict[str, Any] = registry or {}

    # ------------------------------------------------------------------
    # Внутренний одношаговый запуск (без повторов)
    # ------------------------------------------------------------------

    async def _attempt_once(self, prompt: str, doc_type: str, prompt_id: str) -> BaseModel:
        raw_output = await self.llm.generate(prompt)
        cleaned_output = await self.cleaner.clean(raw_output, doc_type)
        validated = await self.validator.validate(cleaned_output, doc_type, prompt_id)
        return validated

    # ------------------------------------------------------------------
    # Публичное API с поддержкой повторов (tenacity)
    # ------------------------------------------------------------------

    async def create_document(self, task_id: str, **prompt_vars) -> Union[BaseModel, str]:
        return await self.worker_work(task_id, **prompt_vars)

    # ------------------------------------------------------------------
    # Новый метод worker_work – логика та же, но выделена по просьбе разработчика
    # ------------------------------------------------------------------

    async def worker_work(self, task_id: str, **prompt_vars) -> Union[BaseModel, str]:
        """Выполняет задачу воркера, повторяя попытку до max_attempts.

        На каждой итерации формирует промпт, добавляя историю предыдущих ошибок
        (few-shot negative feedback) с помощью `_format_error_history`.
        """

        if task_id not in self.registry:
            raise ValueError(f"Задача с ID '{task_id}' не найдена в реестре.")

        task_config = self.registry[task_id]
        prompt_template: str = task_config["prompt_template"]
        doc_type: str = task_config["doc_type"]

        base_prompt = prompt_template.format(**prompt_vars)

        # --- PROMPT LOGGING (careful) ---
        try:
            vars_list = sorted(list(prompt_vars.keys())) if isinstance(prompt_vars, dict) else []
            logger.info(
                "[worker_work] Prepared prompt for task='%s' (doc_type=%s), vars=%s",
                task_id,
                doc_type,
                vars_list,
            )
            logger.debug(
                "[worker_work] BASE PROMPT (len=%s):\n%s",
                len(base_prompt),
                base_prompt,
            )
        except Exception:
            # Логирование не должно ломать поток
            pass

        error_history: List[str] = []

        for attempt in range(1, self.max_attempts + 1):
            logger.info("[worker_work] Попытка %s/%s для '%s'", attempt, self.max_attempts, task_id)

            current_prompt = f"{self._format_error_history(error_history)}{base_prompt}"

            # Логируем текущий промпт полностью
            try:
                logger.debug(
                    "[worker_work] CURRENT PROMPT (len=%s):\n%s",
                    len(current_prompt),
                    current_prompt,
                )
            except Exception:
                pass

            try:
                iter_t0 = perf_counter()

                gen_t0 = perf_counter()
                raw_output = await self.llm.generate(current_prompt)
                gen_dt = perf_counter() - gen_t0

                clean_t0 = perf_counter()
                cleaned_output = await self.cleaner.clean(raw_output, doc_type)
                clean_dt = perf_counter() - clean_t0

                val_t0 = perf_counter()
                validated = await self.validator.validate(cleaned_output, doc_type, task_id)
                val_dt = perf_counter() - val_t0

                iter_dt = perf_counter() - iter_t0
                logger.info(
                    "[worker_work] ✅ Успех на попытке %s для '%s' | timings: generate=%.3fs, clean=%.3fs, validate=%.3fs, iter_total=%.3fs",
                    attempt,
                    task_id,
                    gen_dt,
                    clean_dt,
                    val_dt,
                    iter_dt,
                )
                return validated
            except Exception as exc:  # noqa: WPS430 – логируем и ретраим
                logger.warning(
                    "[worker_work] Попытка %s для '%s' не удалась: %s",
                    attempt,
                    task_id,
                    exc,
                )
                error_history.append(str(exc))

                if attempt == self.max_attempts:
                    logger.error("[worker_work] Достигнут лимит попыток для '%s'", task_id)
                    raise

        # Этот return практически недостижим – либо success либо raise
        raise RuntimeError(f"worker_work: не удалось выполнить задачу '{task_id}'.")

    # ------------------------------------------------------------------
    def _format_error_history(self, errors: List[str]) -> str:  # noqa: D401
        """Формирует секцию с предыдущими ошибками для few-shot feedback."""

        if not errors:
            return ""

        joined = "\n".join(f"- Ошибка #{idx+1}: {err}" for idx, err in enumerate(errors))
        return (
            "### CONTEXT_PREVIOUS_ERRORS\n"
            "Исправь ошибки, указанные ниже, при формировании ответа.\n"
            f"{joined}\n\n---\n\n"
        )


# ------------------------------------------------------------------
# Экземпляры по умолчанию (можно переиспользовать в приложении)
# ------------------------------------------------------------------

try:
    default_llm_service = LlmService()
    default_cleaner_service = CleanerService()
    default_validator_service = ValidatorService()
    default_document_generator = DocumentGenerator(
        default_llm_service,
        default_cleaner_service,
        default_validator_service,
    )
except Exception:  # pragma: no cover – не критично для импорта модуля
    # Если при импорте произошла ошибка инициализации (например, нет API-ключа),
    # то просто логируем. Создание по умолчанию – это вспомогательная возможность.
    logger.exception("Не удалось создать экземпляры сервисов по умолчанию")


class ProfessionReasonsSchema(RootModel[Dict[str, str]]):
    pass

# ------------------------------------------------------------------
# Project draft schema for strict JSON validation (title, description, etc.)
# and default registry/prompt wiring for 'project_from_resume'
# ------------------------------------------------------------------

class ProjectDraftSchema(BaseModel):
    """Strict schema for LLM project draft JSON.

    Only the fields that must come from the LLM. All other fixed fields are
    added later before inserting into DB.
    """

    title: str = Field(..., description="3-10 words project title")
    description: str = Field(..., description="20-30 words concise description")
    problem: str = Field(..., description="1-2 sentences problem statement")
    hypothesis: str = Field(..., description="1-2 sentences hypothesis")
    company_name: str = Field(..., description="Company name for the project")

    @field_validator("title")
    def _validate_title_words(cls, v: str) -> str:  # noqa: N805
        words = [w for w in v.strip().split() if w]
        if len(words) < 3:
            raise ValueError("title must have at least 3 words")
        if len(words) > 10:
            v = " ".join(words[:10])
        return v

    @field_validator("description")
    def _validate_description_words(cls, v: str) -> str:  # noqa: N805
        words = [w for w in v.strip().split() if w]
        if len(words) < 15:
            raise ValueError("description must have at least ~15 words (target 20-30)")
        if len(words) > 40:
            v = " ".join(words[:40])
        return v

    @field_validator("problem", "hypothesis", "company_name")
    def _strip_common(cls, v: str) -> str:  # noqa: N805
        return v.strip()


# Template placeholders:
#  - {user_prompt}: additional high-level guidance from operator
#  - {resume_text}: the raw resume description text
#  - {company_name}: optional pre-filled company name (may be empty)
PROMPT_PROJECT_FROM_RESUME = (
    "Ты — генератор карточки проекта формата Nea. Верни ТОЛЬКО один валидный JSON-объект, без пояснений, без markdown.\n"
    "Требуемые ключи (lowercase): title, description, problem, hypothesis, company_name.\n"
    "Ограничения: title 3-10 слов; description 20-30 слов. problem и hypothesis — по 1-2 предложения.\n"
    "Если company_name неочевидно — аккуратно выведи наиболее вероятное из контекста.\n\n"
    "Контекст:\n{user_prompt}\n\n"
    "Текст резюме:\n{resume_text}\n\n"
    "company_name (подсказка): {company_name}\n\n"
    "Верни только JSON-объект без лишнего текста. Пример структуры (НЕ копируй тексты, только структуру):\n"
    "{{\n\"title\": \"...\", \"description\": \"...\", \"problem\": \"...\", \"hypothesis\": \"...\", \"company_name\": \"...\"}}\n"
)

try:
    if 'default_validator_service' in globals():
        default_validator_service.register_schema("json", "project_from_resume", ProjectDraftSchema)
    if 'default_document_generator' in globals():
        default_document_generator.registry["project_from_resume"] = {
            "prompt_template": PROMPT_PROJECT_FROM_RESUME,
            "doc_type": "json",
        }
except Exception:
    logger.exception("Failed to register ProjectDraftSchema or configure registry for project_from_resume")



ЕЩЕ ПРИМЕР РЕАЛИЗАЦИИ ПОЛЕЗНОГО ФУНКЦИОНАЛА

from __future__ import annotations

import logging
import asyncio
from typing import Any, Dict, List, Optional, Tuple, Union
from time import perf_counter

import google.generativeai as genai
from google.generativeai.types import Tool, FunctionDeclaration, generation_types as gen_types
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import desc
from pydantic import BaseModel, ValidationError, RootModel, Field
try:
    # Pydantic v2
    from pydantic import field_validator
except Exception:  # pragma: no cover
    # Fallback for v1 compatibility
    def field_validator(*args, **kwargs):  # type: ignore
        def wrapper(fn):
            return fn
        return wrapper
from tenacity import retry, stop_after_attempt, wait_fixed

# Импортируем настройки и промпты из config
from ..config import (
    settings,
    PROMPT_LLM1_INTERVIEWER,
    PROMPT_LLM2_GUIDANCE,
    PROMPT_LLM3_MENTOR,
    LLM4_EDITOR_PROMPT,
    PROMPT_LLM_NEYA_GENERAL,
    PROMPT_WEB_CHAT_ASSISTANT,
    PROMPT_NEYA_GENERAL_V2,
    PROMPT_PROFESSION_REASONS_GENERATOR,
)
from ..database.cache_manager import LlmDataProvider
from ..database.redis_client import redis_client
from ..database.cache_manager import CacheManager
from ..database import models  # динамические модели
from ..database.crud_new import GenericCrudService
import json

# Local LLM router facade (provider-agnostic)
from .router import LLMRouter, ProviderResponse, ToolCall, ToolSpec

logger = logging.getLogger(__name__)

# --- Объявления инструментов (FunctionDeclaration) -------------------
# LLM1 – завершение интервью и передача профиля
f_submit_user_profile = FunctionDeclaration(
    name="submit_user_profile",
    description="Как только пользовтель хочет отправить отчет, закончил отвечать, завершает разговор, интервью и передает, отправляет собранный итоговый профиль пользователя в виде единого текста.",
    parameters={
        "type": "object",
        "properties": {
            "profile_text": {
                "type": "string",
                "description": "Полный текст профиля пользователя, объединяющий все собранные разделы (Интересы, Действия, Мышление, Качества, Среда) в связный рассказ."
            }
        },
        "required": ["profile_text"],
    },
)

# LLM2 – подтверждение готовности выбора профессии
f_confirm_profession_choice = FunctionDeclaration(
    name="confirm_profession_choice",
    description="Сигнализирует, что пользователь готов увидеть опции и сделать окончательный выбор профессии.",
    parameters={
        "type": "object",
        "properties": {},
    },
)

# LLM3 – запрос смены обсуждаемой профессии
f_request_profession_change = FunctionDeclaration(
    name="request_profession_change",
    description="Вызывается, когда пользователь явно выражает желание сменить текущую обсуждаемую профессию.",
    parameters={"type": "object", "properties": {}},
)

# Новый инструмент отправки готового графа
f_submit_graph = FunctionDeclaration(
    name="submit_graph",
    description="Финальный шаг. Как только YAML-граф построен и подтверждён пользователем, вызови submit_graph и передай его в параметре graph_yaml.",
    parameters={
        "type": "object",
        "properties": {
            "graph_yaml": {
                "type": "string",
                "description": "Полный YAML граф, описывающий модели, объекты и связи."
            }
        },
        "required": ["graph_yaml"],
    },
)

# --- Новый инструмент Generic CRUD (только чтение) --------------------
f_generic_crud_get = FunctionDeclaration(
    name="generic_crud_get",
    description=(
        "Инструмент для ПОЛУЧЕНИЯ данных из базы через GenericCrudService. "
        "Поддерживает только чтение (action='get').\n\n"
        "Пример вызовов: \n"
        "1) Получить все профессии (первые 20):\n"
        "   generic_crud_get({\"model\": \"Profession\", \"action\": \"get\", \"limit\": 20})\n"
        "2) Получить курсы по профессии id=3: \n"
        "   generic_crud_get({\"model\": \"Course\", \"action\": \"get\", \"filters\": {\"profession_id\": 3}})"
    ),
    parameters={
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["get"],
                "description": "Только 'get'. Любой другой action недопустим.",
            },
            "model": {
                "type": "string",
                "description": "Имя SQLAlchemy модели (например, 'Profession', 'Course').",
            },
            "filters": {
                "type": "object",
                "description": "Карта поле -> значение для where условий (равенство).",
            },
            "limit": {
                "type": "integer",
                "description": "Ограничение количества возвращаемых записей.",
            },
        },
        "required": ["action", "model"],
    },
)

# --- Tools -------------------------------------------------------------
_TOOL_SUBMIT_PROFILE = Tool(function_declarations=[f_submit_user_profile])
_TOOL_CONFIRM_CHOICE = Tool(function_declarations=[f_confirm_profession_choice])
_TOOL_REQUEST_CHANGE = Tool(function_declarations=[f_request_profession_change])
# Новый CRUD tool
_TOOL_GENERIC_CRUD = Tool(function_declarations=[f_generic_crud_get])
# Новый инструмент отправки готового графа
_TOOL_SUBMIT_GRAPH = Tool(function_declarations=[f_submit_graph])

# --- Provider-agnostic ToolSpec equivalents ----------------------------
TOOLSPEC_SUBMIT_PROFILE = ToolSpec(
    name="submit_user_profile",
    description=(
        "Как только пользовтель хочет отправить отчет, закончил отвечать, завершает разговор, "
        "интервью и передает, отправляет собранный итоговый профиль пользователя в виде единого текста."
    ),
    parameters={
        "type": "object",
        "properties": {
            "profile_text": {
                "type": "string",
                "description": (
                    "Полный текст профиля пользователя, объединяющий все собранные разделы "
                    "(Интересы, Действия, Мышление, Качества, Среда) в связный рассказ."
                ),
            }
        },
        "required": ["profile_text"],
    },
)

TOOLSPEC_CONFIRM_CHOICE = ToolSpec(
    name="confirm_profession_choice",
    description="Сигнализирует, что пользователь готов увидеть опции и сделать окончательный выбор профессии.",
    parameters={
        "type": "object",
        "properties": {},
    },
)

TOOLSPEC_REQUEST_CHANGE = ToolSpec(
    name="request_profession_change",
    description="Вызывается, когда пользователь явно выражает желание сменить текущую обсуждаемую профессию.",
    parameters={"type": "object", "properties": {}},
)

TOOLSPEC_SUBMIT_GRAPH = ToolSpec(
    name="submit_graph",
    description=(
        "Финальный шаг. Как только YAML-граф построен и подтверждён пользователем, вызови submit_graph "
        "и передай его в параметре graph_yaml."
    ),
    parameters={
        "type": "object",
        "properties": {
            "graph_yaml": {
                "type": "string",
                "description": "Полный YAML граф, описывающий модели, объекты и связи.",
            }
        },
        "required": ["graph_yaml"],
    },
)

TOOLSPEC_GENERIC_CRUD_GET = ToolSpec(
    name="generic_crud_get",
    description=(
        "Инструмент для ПОЛУЧЕНИЯ данных из базы через GenericCrudService. Поддерживает только чтение (action='get')."
    ),
    parameters={
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["get"],
                "description": "Только 'get'. Любой другой action недопустим.",
            },
            "model": {
                "type": "string",
                "description": "Имя SQLAlchemy модели (например, 'Profession', 'Course').",
            },
            "filters": {
                "type": "object",
                "description": "Карта поле -> значение для where условий (равенство).",
                "additionalProperties": True,
            },
            "limit": {
                "type": "integer",
                "description": "Ограничение количества возвращаемых записей.",
            },
        },
        "required": ["action", "model"],
    },
)

# --- Сопоставление LLM-состояний, промптов, переменных и инструментов ---
STATE_CONFIGS: Dict[str, Dict[str, Any]] = {
    # Веб-чат ассистент (только контекст текущего чата + полная инфа из users)
    "WEB_CHAT_ASSISTANT": {
        "prompt_template": PROMPT_WEB_CHAT_ASSISTANT,
        "variables": ["chat_history", "user_fullinfo", "user_basic_info"],
        "tools": [],
        "tool_specs": [],
    },
    # Общий нейтральный режим без привязки к профессии
    "NEYA_GENERAL_V2": {
        "prompt_template": PROMPT_NEYA_GENERAL_V2,
        "variables": ["chat_history", "user_fullinfo"],
        "tools": [],
        "tool_specs": [],
    },
    # Общий режим NEa – простой ассистент без инструментов
    "LLM_NEYA_GENERAL": {
        "prompt_template": PROMPT_LLM_NEYA_GENERAL,
        "variables": ["chat_history", "user_basic_info"],
        "tools": [],
        "tool_specs": [],
    },
    # Интервью (LLM-1)
    "LLM1_INTERVIEW": {
        "prompt_template": PROMPT_LLM1_INTERVIEWER,
        # Добавили user_info для передачи сведений из profile_data
        "variables": ["chat_history", "user_info", "professions_rag"],
        # Both legacy Gemini tools and provider-agnostic specs
        "tools": [_TOOL_SUBMIT_PROFILE],
        "tool_specs": [TOOLSPEC_SUBMIT_PROFILE],
    },
    # Выбор профессии (LLM-2)
    "LLM2_CHOOSE": {
        "prompt_template": PROMPT_LLM2_GUIDANCE,
        # Переименовали переменные под реальные плейсхолдеры из PROMPT_LLM2_GUIDANCE
        "variables": ["chat_history", "user_profile", "professions_summary", "user_info"],
        "tools": [_TOOL_CONFIRM_CHOICE],
        "tool_specs": [TOOLSPEC_CONFIRM_CHOICE],
    },
    # Обсуждение профессии (LLM-3)
    "LLM3_MENTOR": {
        "prompt_template": PROMPT_LLM3_MENTOR,
        "variables": ["chat_history", "user_profile", "knowledge_base", "all_professions_list", "profession_name", "user_info"],
        "tools": [_TOOL_REQUEST_CHANGE],
        "tool_specs": [TOOLSPEC_REQUEST_CHANGE],
    },
    # Новый режим строителя графа
    "GRAPH_BUILDER": {
        "prompt_template": "{chat_history}",
        "variables": ["chat_history"],
        "tools": [_TOOL_GENERIC_CRUD, _TOOL_SUBMIT_GRAPH],
        "tool_specs": [TOOLSPEC_GENERIC_CRUD_GET, TOOLSPEC_SUBMIT_GRAPH],
    },
    # Редактирование профиля (LLM-4)
    "LLM4_EDIT_PROFILE": {
        "prompt_template": LLM4_EDITOR_PROMPT,
        "variables": ["chat_history", "user_profile", "user_info"],
        "tools": [_TOOL_SUBMIT_PROFILE],
        "tool_specs": [TOOLSPEC_SUBMIT_PROFILE],
    },
}

# --- Основной класс сервиса -------------------------------------------
class LlmServiceSimple:
    """Упрощённый сервис взаимодействия с LLM.

    Алгоритм:
    1. По `llm_state` выбираем промпт и список переменных из STATE_CONFIGS.
    2. Для каждой переменной пытаемся получить значение из Redis-кэша.
       При промахе вызываем одноимённый метод `_fetch_<variable>()` (пока заглушка).
    3. Формируем системный промпт, добавляем историю и текущее сообщение пользователя.
    4. Вызываем Gemini, возвращаем либо текст, либо вызов инструмента.
    """

    def __init__(self, model_name: Optional[str] = None):
        # Выбор провайдера и модели из настроек
        provider = (settings.llm_provider or "gemini").lower()
        if provider == "gemini":
            self.model_name = model_name or settings.gemini_model_name
        else:
            self.model_name = model_name or settings.xai_model_name
        self.temperature = settings.llm_temperature

        # self.cache = CacheManager()

        # Провайдер данных, который берёт из БД и сразу актуализирует Redis
        # self.data_provider = LlmDataProvider(self.cache)

        # Кеш описаний инструментов для каждого состояния (предпочитаем tool_specs)
        self._state_tool_descriptions: Dict[str, str] = {}
        for state, cfg in STATE_CONFIGS.items():
            specs = cfg.get("tool_specs")
            if specs:
                self._state_tool_descriptions[state] = self._generate_tools_description(specs)
            else:
                self._state_tool_descriptions[state] = self._generate_tools_description(cfg.get("tools", []))

        # Сопоставление "имя переменной" -> (crud_func_name, требуются_telegram_id)
        # Карта "имя переменной" -> имя метода-источника данных.
        # Переименовали ключи под актуальные плейсхолдеры из промптов.
        self._crud_map: Dict[str, str] = {
            "user_profile": "get_user_profile_description",  # было user_profile_description
            "professions_summary": "get_professions_summary", # было top_professions_data
            "user_info": "get_user_info",  # новая переменная из profile_data
            "user_basic_info": "get_user_basic_info",  # данные из таблицы users
            "user_fullinfo": "get_user_fullinfo",  # развернутая информация из таблицы users
            "knowledge_base": "get_profession_knowledge_base_stub",
            "all_professions_list": "get_all_professions_list",
            "profession_name": "get_profession_name",
            # добавляйте остальные по мере необходимости
        }

        # --- Классификация переменных для формирования Redis-ключей ---
        self._global_vars: set[str] = {
            "all_professions_list",
            "knowledge_base",
        }
        # Если переменную нет в _global_vars → считаем её user-scoped.

        # Initialize provider router (Gemini/xAI native function calling)
        try:
            provider = (settings.llm_provider or "gemini").lower()
            if provider == "gemini":
                self.router = LLMRouter(
                    provider="gemini",
                    model_name=self.model_name,
                    temperature=self.temperature,
                )
            elif provider == "xai":
                self.router = LLMRouter(
                    provider="xai",
                    model_name=self.model_name,
                    temperature=self.temperature,
                    xai_api_key=settings.xai_api_key,
                    xai_base_url=str(settings.xai_base_url),
                    xai_tool_choice=settings.xai_tool_choice,
                )
            else:
                raise ValueError(f"Unsupported LLM provider: {provider}")
        except Exception as e:
            logger.critical("LLMRouter init failed: %s", e, exc_info=True)
            raise

    # ------------------------------------------------------------------
    # Получение переменной: redis → fetch → сохранение в redis
    async def _get_var(
        self,
        db: AsyncSession,
        telegram_id: int,
        name: str,
        cache_manager: CacheManager,
        current_llm_context: Optional[Dict[str, Any]] = None,
        all_fetched_vars: Optional[Dict[str, Any]] = None,
    ) -> Any:
        # --- Формируем ключ Redis с учётом типа переменной и chat_id ---
        chat_id: Optional[int] = None
        if current_llm_context and isinstance(current_llm_context, dict):
            chat_id = current_llm_context.get("chat_id")

        # Специальный случай: история чата.
        # Читаем напрямую из per-chat ключа через _fetch_chat_history,
        # чтобы не создавать и не инвалидировать дублирующий llm:* кэш.
        if name == "chat_history":
            return await self._fetch_chat_history(db, telegram_id, current_llm_context, all_fetched_vars)

        # Специальный случай: полная информация о пользователе.
        # Новая схема ключа: user:{user_id}:fullinfo (независимо от telegram_id)
        if name == "user_fullinfo":
            user_id: Optional[int] = None
            if current_llm_context and isinstance(current_llm_context, dict):
                user_id = current_llm_context.get("user_id")

            primary_key: Optional[str] = None
            if user_id is not None:
                primary_key = f"user:{user_id}:fullinfo"

            # 1) Пытаемся получить по новому ключу user:{user_id}:fullinfo
            if primary_key:
                try:
                    cached_full = await cache_manager.get_data(primary_key)
                    if cached_full is not None:
                        return cached_full
                except Exception as e:
                    logger.warning(f"Redis error get {primary_key}: {e}")

            # 2) Фоллбэк на старый ключ (для совместимости): llm:{telegram_id}:user_fullinfo
            old_key = f"llm:{telegram_id}:user_fullinfo"
            try:
                cached_old = await cache_manager.get_data(old_key)
                if cached_old is not None:
                    # При наличии user_id — миграционно продублируем в новый ключ
                    if primary_key:
                        try:
                            await cache_manager.set_data(
                                primary_key, cached_old, expire=settings.redis_cache_llm_data_ttl_seconds
                            )
                        except Exception as e:
                            logger.warning(f"Redis error set {primary_key}: {e}")
                    return cached_old
            except Exception as e:
                logger.warning(f"Redis error get {old_key}: {e}")

            # 3) Промах — получаем из БД и сохраняем в новый ключ
            try:
                value = await self._fetch_user_fullinfo(db, telegram_id, current_llm_context, all_fetched_vars)
            except Exception as e:
                logger.error(f"Fetcher error for user_fullinfo: {e}")
                value = {}

            if primary_key:
                try:
                    await cache_manager.set_data(
                        primary_key, value, expire=settings.redis_cache_llm_data_ttl_seconds
                    )
                except Exception as e:
                    logger.warning(f"Redis error set {primary_key}: {e}")
            return value

        if name in self._global_vars:
            redis_key = f"llm:global:{name}"
        else:
            redis_key = f"llm:{telegram_id}:{name}"

        try:
            cached = await cache_manager.get_data(redis_key)
            if cached is not None:
                return cached
        except Exception as e:
            logger.warning(f"Redis error get {redis_key}: {e}")

        value: Any = None

        # 1) Специализированный _fetch_<var>
        fetcher = getattr(self, f"_fetch_{name}", None)
        if callable(fetcher):
            try:
                value = await fetcher(db, telegram_id, current_llm_context, all_fetched_vars)
            except Exception as e:
                logger.error(f"Fetcher error for {name}: {e}")
                value = ""
        # 2) DataProvider
        else: # Используем DataProvider для всех остальных переменных
            # Создаем локальный CacheManager и DataProvider для получения данных из БД
            local_data_provider_cache = CacheManager(db, redis_client)
            local_data_provider = LlmDataProvider(local_data_provider_cache)
            try:
                value = await local_data_provider.fetch(
                    name,
                    db,
                    telegram_id,
                    current_llm_context=current_llm_context or {},
                )
            except Exception as e:
                logger.error(f"DataProvider fetch error for {name}: {e}")
                value = ""

        # Если провайдер уже сохранил данные, можно пропустить, но дополнительный set не повредит
        try:
            await cache_manager.set_data(
                redis_key, value, expire=settings.redis_cache_llm_data_ttl_seconds
            )
        except Exception as e:
            logger.warning(f"Redis error set {redis_key}: {e}")
        return value

    # ------------------------------------------------------------------
    # Заглушки для переменных
    async def _fetch_chat_history(self, db: AsyncSession, telegram_id: int, current_llm_context: Optional[Dict[str, Any]] = None, all_fetched_vars: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Возвращает историю чата в формате, пригодном для Gemini API.

        Если в current_llm_context передан chat_id, используем историю именно этого чата
        (chat:{chat_id}:chat_history). При промахе – гидрируем из Postgres (таблица ChatMessage)
        и записываем в Redis как готовые Gemini-сообщения.
        """
        chat_id: Optional[int] = None
        if current_llm_context and isinstance(current_llm_context, dict):
            chat_id = current_llm_context.get("chat_id")
            llm_state_ctx = current_llm_context.get("llm_state")
        else:
            llm_state_ctx = None

        # По умолчанию большая история; без специальных ограничений для WEB_CHAT_ASSISTANT
        WORD_LIMIT = 40000
        MAX_MESSAGES = 999999

        if chat_id is not None:
            # 1) Пробуем Redis-историю для конкретного чата
            redis_msgs = await redis_client.lrange_chat_history_for_chat(chat_id, limit=settings.chat_history_limit)
            if redis_msgs:
                return redis_msgs

            # 2) Промах – читаем из Postgres сообщения чата и трансформируем
            local_cache = CacheManager(db, redis_client)
            try:
                from Nea.database.models import ChatMessage as DBChatMessage  # локальный импорт, чтобы избежать циклов
                db_msgs = await local_cache.get_many(
                    model=DBChatMessage,  # type: ignore
                    where_conditions=[DBChatMessage.chat_id == chat_id],  # type: ignore
                    # Берём последние N сообщений (desc), затем развернём для хронологического порядка
                    order_by=[desc(DBChatMessage.created_at)],
                    limit=settings.chat_history_limit,
                )
            except Exception as e:
                logger.error(f"DB fetch chat history failed for chat_id={chat_id}: {e}")
                db_msgs = []

            gemini_messages: List[Dict[str, Any]] = []
            total_words = 0
            appended = 0
            # Разворачиваем, чтобы получить хронологический порядок (от старых к новым)
            for m in reversed(db_msgs):
                text = getattr(m, "content", "") or ""
                role_raw = getattr(m, "role", "user") or "user"
                role = "user" if role_raw == "user" else "model"
                words = len(text.split())
                if total_words + words > WORD_LIMIT:
                    break
                gemini_messages.append({"role": role, "parts": [{"text": text}]})
                total_words += words
                appended += 1
                if appended >= MAX_MESSAGES:
                    break

            # 3) Сохраним в Redis-историю для чата
            try:
                for item in gemini_messages:
                    await redis_client.push_chat_message_for_chat(telegram_id, chat_id, item)
            except Exception:
                pass

            return gemini_messages

        # --- Поведение по умолчанию (user-scoped) ---
        # 1) Пытаемся получить из Redis «горячий» хвост
        redis_msgs = await redis_client.lrange_chat_history(
            telegram_id, limit=settings.chat_history_limit
        )
        if redis_msgs:
            return redis_msgs

        # 2) Промах – (историческое поведение): заглушка
        history_models = await redis_client.get_chat_history(telegram_id, limit=settings.chat_history_limit)

        gemini_messages_rev: List[Dict[str, Any]] = []
        total_words = 0
        appended = 0

        for msg in reversed(history_models):
            text = msg.message_text or ""
            words = len(text.split())
            if total_words + words > WORD_LIMIT:
                break
            role = "user" if msg.sender.lower() == "user" else "model"
            gemini_messages_rev.append({"role": role, "parts": [{"text": text}]})
            total_words += words
            appended += 1
            if appended >= MAX_MESSAGES:
                break

        gemini_messages_rev.reverse()

        try:
            for m in gemini_messages_rev:
                await redis_client.push_chat_message(telegram_id, m)
        except Exception:
            pass

        return gemini_messages_rev

    # Другие _fetch_ методы удалены — для всех прочих переменных используется
    # CRUD-fallback или возвращается пустое значение.

    async def _fetch_user_fullinfo(
        self,
        db: AsyncSession,
        telegram_id: int,
        current_llm_context: Optional[Dict[str, Any]] = None,
        all_fetched_vars: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Возвращает полную запись пользователя (все поля таблицы users) по user_id.

        Ожидает, что user_id передан в current_llm_context.
        """
        user_id: Optional[int] = None
        if current_llm_context and isinstance(current_llm_context, dict):
            user_id = current_llm_context.get("user_id")

        if user_id is None:
            logger.warning("_fetch_user_fullinfo called without user_id in context")
            return {}

        local_cache = CacheManager(db, redis_client)
        try:
            from Nea.database.models import User as DBUser  # локальный импорт, чтобы избежать циклов
            user_obj = await local_cache.get_one_or_none(
                model=DBUser,  # type: ignore
                where_conditions=[DBUser.id == user_id],  # type: ignore
            )
        except Exception as e:
            logger.error(f"DB fetch user failed for user_id={user_id}: {e}")
            user_obj = None

        if not user_obj:
            return {}

        # Преобразуем объект пользователя в примитивный словарь
        result: Dict[str, Any] = {}
        try:
            for k, v in vars(user_obj).items():
                if k.startswith("_"):
                    continue
                try:
                    if hasattr(v, "isoformat"):
                        result[k] = v.isoformat()
                    else:
                        result[k] = v
                except Exception:
                    # Непримитивные поля приводим к строке
                    result[k] = str(v)
        except Exception as e:
            logger.warning(f"Failed to serialize user object for user_id={user_id}: {e}")
        return result