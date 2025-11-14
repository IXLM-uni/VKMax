# Руководство к файлу (TESTS/integration/test_health_integration.py)
# Назначение:
# - Интеграционный тест FastAPI-ручки /health через реальное приложение.

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_health_endpoint(http_client):
    response = await http_client.get("/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data
