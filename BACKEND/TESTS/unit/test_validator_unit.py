# Руководство к файлу (TESTS/unit/test_validator_unit.py)
# Назначение:
# - Unit-тесты для LLM_SERVICE/ValidatorService: регистрация схем и асинхронная валидация.

from __future__ import annotations

import pytest
from pydantic import BaseModel, ValidationError

from BACKEND.LLM_SERVICE.validator import ValidatorService


class SimpleSchema(BaseModel):
    value: int


@pytest.mark.asyncio
async def test_validator_register_and_validate_dict():
    service = ValidatorService()
    service.register_schema("json", "prompt-1", SimpleSchema)

    result = await service.validate({"value": 10}, doc_type="json", prompt_id="prompt-1")

    assert isinstance(result, SimpleSchema)
    assert result.value == 10


@pytest.mark.asyncio
async def test_validator_parses_json_string_before_validation():
    service = ValidatorService()
    service.register_schema("json", "prompt-2", SimpleSchema)

    # Передаём строку JSON – сервис должен распарсить её сам.
    payload = "{\"value\": 42}"
    result = await service.validate(payload, doc_type="json", prompt_id="prompt-2")

    assert isinstance(result, SimpleSchema)
    assert result.value == 42


@pytest.mark.asyncio
async def test_validator_raises_validation_error_on_bad_data():
    service = ValidatorService()
    service.register_schema("json", "prompt-3", SimpleSchema)

    # value должен быть int, передаём строку.
    with pytest.raises(ValidationError):
        await service.validate({"value": "not-int"}, doc_type="json", prompt_id="prompt-3")


@pytest.mark.asyncio
async def test_validator_raises_value_error_if_schema_not_registered():
    service = ValidatorService()

    with pytest.raises(ValueError):
        await service.validate({"value": 1}, doc_type="json", prompt_id="missing")
