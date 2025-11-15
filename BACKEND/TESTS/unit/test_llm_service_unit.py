# Руководство к файлу (TESTS/unit/test_llm_service_unit.py)
# Назначение:
# - Unit-тесты для BACKEND.LLM_SERVICE.llm_service.LlmService.
# - Проверяют mock-провайдер и поведение при некорректной конфигурации окружения.

from __future__ import annotations

import os

import pytest

from BACKEND.LLM_SERVICE.llm_service import LlmService


pytestmark = pytest.mark.asyncio


_LLM_KEYS = (
    "VKMAX_OPENROUTER_API_KEY",
    "OPENROUTER_API_KEY",
    "VKMAX_DEEPSEEK_API_KEY",
    "DEEPSEEK_API_KEY",
)


async def test_llm_service_generate_mock_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    """Провайдер mock: generate возвращает предсказуемую строку без сети."""

    monkeypatch.setenv("VKMAX_LLM_PROVIDER", "mock")
    for key in _LLM_KEYS:
        monkeypatch.delenv(key, raising=False)

    service = LlmService()

    prompt = "Привет, VKMax!"
    text = await service.generate(prompt)

    assert isinstance(text, str)
    assert text.startswith("MOCK_LLM_OUTPUT:")
    # В mock-ответе должен присутствовать обрезанный prompt
    assert "Привет, VKMax" in text


async def test_llm_service_falls_back_to_deepseek_on_unknown_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    """Неизвестный провайдер в env приводит к fallback на deepseek."""

    monkeypatch.setenv("VKMAX_LLM_PROVIDER", "some-unknown-provider")

    service = LlmService()

    assert service.provider == "deepseek"


async def test_llm_service_deepseek_without_api_key_raises_on_init(monkeypatch: pytest.MonkeyPatch) -> None:
    """При deepseek без ключа конструктор LlmService должен сразу падать.

    Это позволяет быстро выявлять битую конфигурацию окружения до сетевого запроса.
    """

    monkeypatch.setenv("VKMAX_LLM_PROVIDER", "deepseek")
    for key in _LLM_KEYS:
        monkeypatch.delenv(key, raising=False)

    with pytest.raises(RuntimeError):
        LlmService(api_key=None)
