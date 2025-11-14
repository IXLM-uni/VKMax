# Руководство к файлу (LLM_SERVICE/llm_service.py)
# Назначение:
# - Низкоуровневый клиент для общения с LLM-провайдером DeepSeek через OpenRouter.
# - Предоставляет метод LlmService.generate(prompt) → str без пост-обработки.

from __future__ import annotations

import logging
import os
from typing import Optional

import httpx


logger = logging.getLogger(__name__)


class LlmService:
    """Простой исполнитель для общения с LLM (DeepSeek через OpenRouter / mock).

    Провайдер выбирается через переменную окружения ``VKMAX_LLM_PROVIDER``.
    Поддерживаются значения:
    - ``deepseek`` (по умолчанию) — HTTP-вызов к https://openrouter.ai/api/v1/chat/completions
    - ``mock`` — возвращает тестовую строку без сетевого вызова.

    Дополнительные настройки читаются из окружения:
    - VKMAX_OPENROUTER_API_KEY или OPENROUTER_API_KEY (рекомендуется)
    - VKMAX_DEEPSEEK_API_KEY или DEEPSEEK_API_KEY (поддержка старых настроек)
    - VKMAX_LLM_MODEL_NAME или VKMAX_OPENROUTER_MODEL_NAME или OPENROUTER_MODEL_NAME
      (по умолчанию ``deepseek/deepseek-chat``)
    - VKMAX_LLM_TEMPERATURE (float, по умолчанию 0.2)
    - VKMAX_OPENROUTER_BASE_URL или OPENROUTER_BASE_URL
      (по умолчанию ``https://openrouter.ai/api/v1``)
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        temperature: Optional[float] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ) -> None:
        provider = (os.getenv("VKMAX_LLM_PROVIDER", "deepseek") or "deepseek").lower()
        if provider not in {"deepseek", "mock"}:
            provider = "deepseek"
        self.provider: str = provider

        # Базовые настройки
        env_model = (
            os.getenv("VKMAX_LLM_MODEL_NAME")
            or os.getenv("VKMAX_OPENROUTER_MODEL_NAME")
            or os.getenv("OPENROUTER_MODEL_NAME")
            or os.getenv("VKMAX_DEEPSEEK_MODEL_NAME")
            or os.getenv("DEEPSEEK_MODEL_NAME")
        )
        self.model_name: str = model_name or env_model or "deepseek/deepseek-chat"

        env_temp = os.getenv("VKMAX_LLM_TEMPERATURE") or "0.2"
        try:
            self.temperature: float = float(temperature) if temperature is not None else float(env_temp)
        except Exception:
            self.temperature = 0.2

        self.base_url: str = (
            base_url
            or os.getenv("VKMAX_OPENROUTER_BASE_URL")
            or os.getenv("OPENROUTER_BASE_URL")
            or os.getenv("DEEPSEEK_BASE_URL")
            or "https://openrouter.ai/api/v1"
        )
        self.api_key: Optional[str] = (
            api_key
            or os.getenv("VKMAX_OPENROUTER_API_KEY")
            or os.getenv("OPENROUTER_API_KEY")
            or os.getenv("VKMAX_DEEPSEEK_API_KEY")
            or os.getenv("DEEPSEEK_API_KEY")
        )

        if self.provider == "deepseek" and not self.api_key:
            raise RuntimeError(
                "OpenRouter/DeepSeek API key is not configured "
                "(VKMAX_OPENROUTER_API_KEY / OPENROUTER_API_KEY / VKMAX_DEEPSEEK_API_KEY / DEEPSEEK_API_KEY)"
            )

        logger.info("[LlmService] Initialized provider=%s model=%s", self.provider, self.model_name)

    # ------------------------------------------------------------------
    # Публичный метод
    # ------------------------------------------------------------------

    async def generate(self, prompt: str) -> str:
        """Асинхронно отправляет *prompt* в LLM и возвращает ответ без пост-обработки."""

        if self.provider == "mock":
            # Простой режим для локальной отладки без внешнего API
            preview = (prompt[:80] + "…") if len(prompt) > 80 else prompt
            logger.debug("[LlmService.generate] MOCK provider, prompt preview: %s", preview)
            return f"MOCK_LLM_OUTPUT: {preview}"

        if self.provider == "deepseek":
            return await self._generate_deepseek(prompt)

        raise RuntimeError(f"Unsupported LLM provider: {self.provider}")

    # ------------------------------------------------------------------
    # Внутренняя реализация DeepSeek через OpenRouter
    # ------------------------------------------------------------------

    async def _generate_deepseek(self, prompt: str) -> str:
        assert self.api_key, "OpenRouter API key must be configured"

        url = f"{self.base_url.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            # Рекомендуемые заголовки OpenRouter (необязательные, но полезные)
            "HTTP-Referer": os.getenv("OPENROUTER_REFERRER", ""),
            "X-Title": os.getenv("OPENROUTER_TITLE", "VKMax"),
        }
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "user", "content": prompt},
            ],
            "temperature": self.temperature,
        }

        try:
            logger.debug(
                "[LlmService._generate_deepseek] POST %s model=%s len(prompt)=%s",
                url,
                self.model_name,
                len(prompt),
            )
        except Exception:
            pass

        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                resp = await client.post(url, headers=headers, json=payload)
            except Exception as exc:  # pragma: no cover – сетевые сбои
                logger.error("OpenRouter HTTP error (DeepSeek model): %s", exc, exc_info=True)
                raise

        if resp.status_code != 200:
            logger.error("OpenRouter API error (DeepSeek model): status=%s body=%s", resp.status_code, resp.text)
            resp.raise_for_status()

        data = resp.json()
        try:
            choices = data["choices"]
            if not choices:
                raise RuntimeError("OpenRouter/DeepSeek response has no choices")
            message = choices[0]["message"]
            text = message.get("content")
        except Exception as exc:
            logger.error("OpenRouter/DeepSeek response parsing error: %s | raw=%s", exc, data, exc_info=True)
            raise RuntimeError("OpenRouter/DeepSeek response parsing failed") from exc

        if not isinstance(text, str) or not text.strip():
            raise RuntimeError("OpenRouter/DeepSeek returned empty content")

        return text.strip()

