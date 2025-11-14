# Руководство к файлу (TESTS/e2e/test_flow_root_health_e2e.py)
# Назначение:
# - Базовый e2e-флоу: проверка, что корень API и /health отвечают корректно.

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_flow_root_and_health(http_client):
    # Проверяем корневую ручку
    resp_root = await http_client.get("/")
    assert resp_root.status_code == 200
    data_root = resp_root.json()
    assert "message" in data_root
    assert "version" in data_root

    # Проверяем /health
    resp_health = await http_client.get("/health")
    assert resp_health.status_code == 200
    data_health = resp_health.json()
    assert data_health["status"] == "ok"
