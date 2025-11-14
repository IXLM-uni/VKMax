# Руководство к файлу (LLM_SERVICE/router.py)
# Назначение:
# - Провайдер-независимый фасад LLMRouter поверх LlmService.
# - Для MVP VKMax не использует tool-calls, но структура оставлена для будущего расширения.

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .llm_service import LlmService


logger = logging.getLogger(__name__)


@dataclass
class ToolSpec:
    """Описание инструмента (зарезервировано под будущее использование).

    В текущем MVP инструменты не задействованы, но структура оставлена
    для совместимости с более сложными сценариями.
    """

    name: str
    description: str
    parameters: Dict[str, Any]


@dataclass
class ToolCall:
    """Результат вызова инструмента (MVP: не используется)."""

    name: str
    arguments: Dict[str, Any]


@dataclass
class ProviderResponse:
    """Унифицированный ответ от LLM-провайдера."""

    text: str
    blocked: bool = False
    block_reason: Optional[str] = None
    tool_calls: Optional[List[ToolCall]] = None


class LLMRouter:
    """Простая обёртка над LlmService.

    Цель – абстрагировать логику формирования промпта от конкретного
    провайдера. Для VKMax достаточно собрать текст из messages и
    передать его в LlmService.generate.
    """

    def __init__(
        self,
        provider: str = "deepseek",
        *,
        llm_service: Optional[LlmService] = None,
        model_name: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> None:
        self.provider = provider
        self.llm = llm_service or LlmService(model_name=model_name, temperature=temperature)

    async def send(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Any]] = None,  # noqa: ARG002 – зарезервировано
        tool_specs: Optional[List[ToolSpec]] = None,  # noqa: ARG002
        temperature: Optional[float] = None,
    ) -> ProviderResponse:
        """Унифицированный интерфейс обращения к LLM.

        *messages* – список сообщений чата в формате, близком к OpenAI/DeepSeek:
        [{"role": "user", "content": "..."}, ...].

        В MVP:
        - все messages конкатенируются в один текстовый промпт;
        - tools/tool_specs игнорируются;
        - возвращается только текст без tool-calls.
        """

        # Собираем промпт из сообщений
        parts: List[str] = []
        for m in messages:
            role = m.get("role", "user")
            content = m.get("content")
            if content is None and "parts" in m:
                try:
                    # Совместимость с форматом вида {"parts": [{"text": "..."}]}
                    first = m["parts"][0]
                    content = first.get("text")
                except Exception:
                    content = None
            if not isinstance(content, str):
                continue
            parts.append(f"{role}: {content}")

        prompt = "\n\n".join(parts)
        if temperature is not None:
            # Локальная настройка температуры не меняет глобальное состояние –
            # просто создаём временный экземпляр клиента.
            client = LlmService(model_name=self.llm.model_name, temperature=temperature)
        else:
            client = self.llm

        logger.debug("[LLMRouter.send] provider=%s len(prompt)=%s", self.provider, len(prompt))
        text = await client.generate(prompt)
        return ProviderResponse(text=text, blocked=False, block_reason=None, tool_calls=None)

