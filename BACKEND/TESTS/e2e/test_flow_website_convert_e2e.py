# Руководство к файлу (TESTS/e2e/test_flow_website_convert_e2e.py)
# Назначение:
# - E2E-сценарий: website-конвертация через /convert/website + проверка статуса и истории.

from __future__ import annotations

import uuid

import pytest


@pytest.mark.asyncio
async def test_flow_website_convert_status_history_e2e(http_client):
    """Полный поток: /users -> /convert/website -> /websites/{id}/status -> /websites/history."""

    # 1. Пользователь
    user_payload = {
        "max_id": f"website-flow-user-{uuid.uuid4()}",
        "name": "Website Flow User",
        "metadata": {"role": "website-flow"},
    }
    resp_user = await http_client.post("/users", json=user_payload)
    assert resp_user.status_code == 200
    user_id = resp_user.json()["id"]

    # 2. Создаём website-операцию
    payload = {
        "url": "https://example.com",
        "target_format": "html",
        "user_id": user_id,
    }
    resp_conv = await http_client.post("/convert/website", json=payload)
    assert resp_conv.status_code == 200
    op_data = resp_conv.json()
    operation_id = op_data["operation_id"]
    assert op_data["status"] == "queued"

    # 3. Статус website-операции
    resp_status = await http_client.get(f"/websites/{operation_id}/status")
    assert resp_status.status_code == 200
    st = resp_status.json()
    assert st["operation_id"] == operation_id
    assert st["status"] == "queued"

    # 4. История website-операций для пользователя
    resp_history = await http_client.get(f"/websites/history?user_id={user_id}")
    assert resp_history.status_code == 200
    history = resp_history.json()
    ids = {item["operation_id"] for item in history}
    assert operation_id in ids
