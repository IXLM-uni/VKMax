# Руководство к файлу (LLM_SERVICE/validator.py)
# Назначение:
# - Сервис валидации данных, возвращаемых LLM, по Pydantic-схемам.
# - Позволяет регистрировать схемы по ключу (doc_type, prompt_id) и вызывать validate.

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Tuple, Type

from pydantic import BaseModel, ValidationError


logger = logging.getLogger(__name__)


class ValidatorService:
    """Проверяет данные на соответствие Pydantic-схемам.

    Схемы регистрируются по паре (doc_type, prompt_id). Это позволяет
    переиспользовать сервис для разных задач LLM.
    """

    def __init__(self, schema_map: Optional[Dict[Tuple[str, str], Type[BaseModel]]] = None) -> None:
        # Ключ – (doc_type, prompt_id)
        self._schema_map: Dict[Tuple[str, str], Type[BaseModel]] = schema_map or {}

    # --------------------------------------------------------------
    # API
    # --------------------------------------------------------------

    def register_schema(self, doc_type: str, prompt_id: str, schema_cls: Type[BaseModel]) -> None:
        """Регистрирует новую схему проверки."""

        self._schema_map[(doc_type, prompt_id)] = schema_cls

    async def validate(self, data: Any, doc_type: str, prompt_id: str, rules: Any | None = None) -> BaseModel:
        """Асинхронно валидирует *data* согласно зарегистрированной Pydantic-схеме.

        *rules* зарезервирован под дополнительные правила, пока не используется.
        """

        schema_cls = self._schema_map.get((doc_type, prompt_id))
        if not schema_cls:
            raise ValueError(f"Схема для ({doc_type!r}, {prompt_id!r}) не зарегистрирована")

        # Если передан json-стринг – пробуем распарсить.
        obj: Any = data
        if isinstance(data, str):
            import json

            try:
                obj = json.loads(data)
            except json.JSONDecodeError:
                # Оставляем как есть – схема сама может ожидать str
                pass

        try:
            validate_fn = getattr(schema_cls, "model_validate", None)
            if callable(validate_fn):
                return validate_fn(obj)  # type: ignore[return-value]
            return schema_cls.parse_obj(obj)  # type: ignore[return-value]
        except ValidationError as exc:
            logger.error("Validation failed for (%s, %s): %s", doc_type, prompt_id, exc)
            raise

