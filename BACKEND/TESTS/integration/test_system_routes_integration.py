# Руководство к файлу (TESTS/integration/test_system_routes_integration.py)
# Назначение:
# - Интеграционные тесты для системных ручек `/stats` и `/webhook/conversion-complete`.

from __future__ import annotations

import pytest
from sqlalchemy import select

from BACKEND.DATABASE.session import async_session_factory
from BACKEND.DATABASE.models import Operation
from BACKEND.DATABASE.CACHE_MANAGER import ConvertManager


@pytest.mark.asyncio
async def test_stats_without_token(http_client, monkeypatch):
    """/stats без VKMAX_ADMIN_TOKEN должен быть доступен и возвращать метрики."""

    monkeypatch.delenv("VKMAX_ADMIN_TOKEN", raising=False)

    resp = await http_client.get("/stats")
    assert resp.status_code == 200
    data = resp.json()
    for key in [
        "total_users",
        "total_files",
        "total_operations",
        "conversions_today",
        "website_conversions",
    ]:
        assert key in data
        assert isinstance(data[key], int)


@pytest.mark.asyncio
async def test_stats_with_token_authz(http_client, monkeypatch):
    """/stats с VKMAX_ADMIN_TOKEN требует корректного Bearer-токена."""

    monkeypatch.setenv("VKMAX_ADMIN_TOKEN", "secret-token")

    # Без токена – 401
    resp_unauth = await http_client.get("/stats")
    assert resp_unauth.status_code == 401

    # С правильным токеном – 200
    resp_auth = await http_client.get(
        "/stats",
        headers={"Authorization": "Bearer secret-token"},
    )
    assert resp_auth.status_code == 200


@pytest.mark.asyncio
async def test_webhook_conversion_complete_updates_status(http_client):
    """/webhook/conversion-complete должен обновлять статус операции в БД."""

    # Создаём черновую операцию напрямую через ConvertManager
    async with async_session_factory() as session:
        cm = ConvertManager(session)
        op = await cm.create(
            Operation,
            {
                "user_id": None,
                "file_id": None,
                "result_file_id": None,
                "old_format_id": None,
                "new_format_id": None,
                "status": "queued",
                "error_message": None,
            },
        )
        await session.commit()
        operation_id = int(getattr(op, "id"))

    payload = {
        "operation_id": str(operation_id),
        "status": "completed",
        "converted_file_id": None,
        "error_message": None,
        "type": None,
    }

    resp = await http_client.post("/webhook/conversion-complete", json=payload)
    assert resp.status_code == 200
    assert resp.json().get("ok") is True

    # Проверяем, что статус операции изменился
    async with async_session_factory() as session:
        res = await session.execute(select(Operation).where(Operation.id == operation_id))
        op = res.scalars().first()
        assert op is not None
        assert getattr(op, "status") == "completed"
