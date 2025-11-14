# Руководство к файлу (LLM_SERVICE/document_generator.py)
# Назначение:
# - Высокоуровневый оркестратор LLM-задач (DocumentGenerator) для VKMax.
# - Координирует генерацию, чистку и валидацию с поддержкой повторных попыток.

from __future__ import annotations

import logging
from time import perf_counter
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from .llm_service import LlmService
from .cleaner import CleanerService
from .validator import ValidatorService


logger = logging.getLogger(__name__)


class DocumentGenerator:
    """Высокоуровневый оркестратор создания документов/ответов LLM.

    Использует три сервиса:
        - LlmService – фактический клиент LLM (DeepSeek/mock);
        - CleanerService – нормализует сырой текст (json/html/graph_json/plain);
        - ValidatorService – опционально валидирует результат по Pydantic-схеме.

    Реестр задач (registry) управляется снаружи. Для каждой задачи задаётся:
        - prompt_template: str
        - doc_type: str ("json", "html", "graph_json", "plain")
        - (опционально) любые дополнительные поля, которые могут пригодиться позже.
    """

    def __init__(
        self,
        llm_service: LlmService,
        cleaner_service: CleanerService,
        validator_service: ValidatorService,
        *,
        registry: Optional[Dict[str, Dict[str, Any]]] = None,
        max_attempts: int = 3,
    ) -> None:
        self.llm = llm_service
        self.cleaner = cleaner_service
        self.validator = validator_service
        self.max_attempts = max_attempts
        self.registry: Dict[str, Dict[str, Any]] = registry or {}

    # ------------------------------------------------------------------
    # Публичный API
    # ------------------------------------------------------------------

    async def create_document(self, task_id: str, **prompt_vars: Any) -> Any:
        """Совместимый алиас поверх worker_work."""

        return await self.worker_work(task_id, **prompt_vars)

    async def worker_work(self, task_id: str, **prompt_vars: Any) -> Any:
        """Выполняет задачу с поддержкой повторных попыток.

        На каждой попытке:
          1. Формирует промпт (base_prompt + история ошибок),
          2. Вызывает LlmService.generate,
          3. Прогоняет ответ через CleanerService,
          4. Пытается валидировать результат через ValidatorService.

        Схема для валидации берётся по ключу (doc_type, task_id).
        """

        if task_id not in self.registry:
            raise ValueError(f"Задача с ID '{task_id}' не найдена в реестре.")

        task_config = self.registry[task_id]
        prompt_template: str = task_config["prompt_template"]
        doc_type: str = task_config.get("doc_type", "plain")

        base_prompt = prompt_template.format(**prompt_vars)

        # Логирование базового промпта (без критичности)
        try:
            vars_list = sorted(list(prompt_vars.keys())) if isinstance(prompt_vars, dict) else []
            logger.info(
                "[DocumentGenerator.worker_work] Prepared prompt for task='%s' (doc_type=%s), vars=%s",
                task_id,
                doc_type,
                vars_list,
            )
            logger.debug(
                "[DocumentGenerator.worker_work] BASE PROMPT (len=%s):\n%s",
                len(base_prompt),
                base_prompt,
            )
        except Exception:
            pass

        error_history: List[str] = []

        for attempt in range(1, self.max_attempts + 1):
            logger.info("[DocumentGenerator.worker_work] Попытка %s/%s для '%s'", attempt, self.max_attempts, task_id)

            current_prompt = f"{self._format_error_history(error_history)}{base_prompt}"

            try:
                logger.debug(
                    "[DocumentGenerator.worker_work] CURRENT PROMPT (len=%s):\n%s",
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

                # Валидация опциональна: если схемы нет, просто возвращаем строку
                val_t0 = perf_counter()
                try:
                    validated: Any = await self.validator.validate(cleaned_output, doc_type, task_id)
                except Exception:
                    # Если схемы нет или валидация не настроена, отдаём "как есть"
                    validated = cleaned_output
                val_dt = perf_counter() - val_t0

                iter_dt = perf_counter() - iter_t0
                logger.info(
                    "[DocumentGenerator.worker_work] ✅ Успех на попытке %s для '%s' | timings: generate=%.3fs, clean=%.3fs, validate=%.3fs, iter_total=%.3fs",
                    attempt,
                    task_id,
                    gen_dt,
                    clean_dt,
                    val_dt,
                    iter_dt,
                )
                return validated
            except Exception as exc:  # noqa: WPS430
                logger.warning(
                    "[DocumentGenerator.worker_work] Попытка %s для '%s' не удалась: %s",
                    attempt,
                    task_id,
                    exc,
                )
                error_history.append(str(exc))

                if attempt == self.max_attempts:
                    logger.error("[DocumentGenerator.worker_work] Достигнут лимит попыток для '%s'", task_id)
                    raise

        # Практически недостижимый path
        raise RuntimeError(f"worker_work: не удалось выполнить задачу '{task_id}'.")

    # ------------------------------------------------------------------
    # Вспомогательные функции
    # ------------------------------------------------------------------

    def _format_error_history(self, errors: List[str]) -> str:
        """Формирует секцию с предыдущими ошибками для few-shot feedback."""

        if not errors:
            return ""

        joined = "\n".join(f"- Ошибка #{idx+1}: {err}" for idx, err in enumerate(errors))
        return (
            "### CONTEXT_PREVIOUS_ERRORS\n"
            "Исправь ошибки, указанные ниже, при формировании ответа.\n"
            f"{joined}\n\n---\n\n"
        )

