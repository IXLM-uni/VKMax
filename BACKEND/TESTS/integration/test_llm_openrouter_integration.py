# Руководство к файлу (TESTS/integration/test_llm_openrouter_integration.py)
# Назначение:
# - Интеграционный тест для реального вызова LlmService через OpenRouter/DeepSeek.
# - Использует настройки из BACKEND/.env (VKMAX_LLM_PROVIDER, VKMAX_OPENROUTER_API_KEY, VKMAX_LLM_MODEL_NAME).

from __future__ import annotations

import os

import pytest

from BACKEND.LLM_SERVICE.llm_service import LlmService


pytestmark = pytest.mark.asyncio


@pytest.mark.skipif(
    os.getenv("VKMAX_LLM_PROVIDER", "deepseek").lower() == "mock"
    or not (
        os.getenv("VKMAX_OPENROUTER_API_KEY")
        or os.getenv("OPENROUTER_API_KEY")
        or os.getenv("VKMAX_DEEPSEEK_API_KEY")
        or os.getenv("DEEPSEEK_API_KEY")
    ),
    reason="Real LLM tests require configured OpenRouter/DeepSeek key and non-mock provider",
)
async def test_llm_service_generate_real_deepseek():
    """Проверяем, что LlmService реально ходит в OpenRouter/DeepSeek и возвращает непустой текст.

    Тест намеренно не привязан к точному содержимому ответа, только к факту успешного
    вызова и разумной длине текста, чтобы не падать от небольших изменений модели.
    """

    service = LlmService()
    prompt = "Коротко ответь на русском словом 'OK'."

    text = await service.generate(prompt)

    assert isinstance(text, str)
    assert text.strip() != ""
    # Ответ не должен быть гигантским — ожидаем короткую строку
    assert len(text) < 1000
