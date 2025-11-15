# Руководство к файлу (TESTS/unit/test_document_generator_unit.py)
# Назначение:
# - Unit-тесты для BACKEND.LLM_SERVICE.document_generator.DocumentGenerator.
# - Проверяют успешный сценарий, ретраи при ошибке и падение после max_attempts.

from __future__ import annotations

from typing import Any, Dict, List

import pytest

from BACKEND.LLM_SERVICE.document_generator import DocumentGenerator


pytestmark = pytest.mark.asyncio


class DummyLlmService:
    def __init__(self, fail_first: bool = False) -> None:
        self.fail_first = fail_first
        self.prompts: List[str] = []

    async def generate(self, prompt: str) -> str:
        self.prompts.append(prompt)
        if self.fail_first and len(self.prompts) == 1:
            raise RuntimeError("llm failure on first attempt")
        return f"RAW:{prompt}"


class DummyCleanerService:
    def __init__(self) -> None:
        self.calls: List[Dict[str, str]] = []

    async def clean(self, text: str, doc_type: str) -> str:
        self.calls.append({"text": text, "doc_type": doc_type})
        return f"CLEAN:{doc_type}:{text}"


class DummyValidatorService:
    def __init__(self, always_raise: bool = False) -> None:
        self.always_raise = always_raise
        self.calls: List[Dict[str, Any]] = []

    async def validate(self, data: Any, doc_type: str, prompt_id: str, rules: Any | None = None) -> Any:
        self.calls.append({"data": data, "doc_type": doc_type, "prompt_id": prompt_id})
        if self.always_raise:
            raise RuntimeError("validation failure")
        return {"validated": data, "doc_type": doc_type, "prompt_id": prompt_id}


def _make_generator(*, max_attempts: int = 3, llm: DummyLlmService | None = None,
                    cleaner: DummyCleanerService | None = None,
                    validator: DummyValidatorService | None = None) -> DocumentGenerator:
    llm_service = llm or DummyLlmService()
    cleaner_service = cleaner or DummyCleanerService()
    validator_service = validator or DummyValidatorService()

    registry = {
        "test_task": {
            "prompt_template": "Hello, {name}!",
            "doc_type": "plain",
        }
    }

    return DocumentGenerator(
        llm_service=llm_service,
        cleaner_service=cleaner_service,
        validator_service=validator_service,
        registry=registry,
        max_attempts=max_attempts,
    )


async def test_worker_work_success_single_attempt() -> None:
    """Успешный сценарий: без ошибок, одна попытка."""

    llm = DummyLlmService()
    cleaner = DummyCleanerService()
    validator = DummyValidatorService()
    gen = _make_generator(llm=llm, cleaner=cleaner, validator=validator)

    result = await gen.worker_work("test_task", name="VKMax")

    # LLM и cleaner вызваны один раз
    assert len(llm.prompts) == 1
    assert len(cleaner.calls) == 1
    assert result["validated"].startswith("CLEAN:plain:RAW:Hello, VKMax!")


async def test_worker_work_retries_when_llm_fails_once() -> None:
    """При ошибке LLM на первой попытке происходит retry и вторая попытка успешна."""

    llm = DummyLlmService(fail_first=True)
    cleaner = DummyCleanerService()
    validator = DummyValidatorService()
    gen = _make_generator(llm=llm, cleaner=cleaner, validator=validator, max_attempts=2)

    result = await gen.worker_work("test_task", name="VKMax")

    # Должно быть две попытки LLM
    assert len(llm.prompts) == 2
    assert result["validated"].startswith("CLEAN:plain:RAW:Hello, VKMax!")


async def test_worker_work_raises_after_max_attempts_exhausted() -> None:
    """Если все попытки завершаются ошибкой, worker_work выбрасывает исключение."""

    llm = DummyLlmService()
    cleaner = DummyCleanerService()
    validator = DummyValidatorService(always_raise=True)
    gen = _make_generator(llm=llm, cleaner=cleaner, validator=validator, max_attempts=2)

    with pytest.raises(RuntimeError):
        await gen.worker_work("test_task", name="VKMax")

    # Валидация должна была вызываться на каждой попытке
    assert len(validator.calls) == 2
