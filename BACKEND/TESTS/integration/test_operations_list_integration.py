# Руководство к файлу (TESTS/integration/test_operations_list_integration.py)
# Назначение:
# - Интеграционные тесты для списка операций `/operations`.
# - Проверяют фильтрацию по user_id и type, а также обработку некорректного user_id.

from __future__ import annotations

import uuid

import pytest


pytestmark = pytest.mark.asyncio


async def _create_user(http_client) -> str:
    payload = {
        "max_id": f"ops-user-{uuid.uuid4()}",
        "name": "Ops User",
        "metadata": {"role": "ops"},
    }
    resp = await http_client.post("/users", json=payload)
    assert resp.status_code == 200
    return resp.json()["id"]


async def _create_file_operation(http_client, user_id: str, target_format: str = "pdf") -> str:
    # Небольшой PDF как источник
    pdf_bytes = b"%PDF-1.4\n%OPS TEST\n%%EOF\n"
    files = {"file": ("ops.pdf", pdf_bytes, "application/pdf")}
    data = {"user_id": user_id, "original_format": "pdf"}

    resp_upload = await http_client.post("/upload", files=files, data=data)
    assert resp_upload.status_code == 200
    file_id = resp_upload.json()["file_id"]

    conv_payload = {
        "source_file_id": file_id,
        "target_format": target_format,
        "user_id": user_id,
    }
    resp_convert = await http_client.post("/convert", json=conv_payload)
    assert resp_convert.status_code == 200
    return resp_convert.json()["operation_id"]


async def _create_website_operation(http_client, user_id: str) -> str:
    payload = {
        "url": "https://example.com",
        "target_format": "html",
        "user_id": user_id,
    }
    resp = await http_client.post("/convert/website", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "queued"
    return data["operation_id"]


async def test_operations_list_filter_by_user_and_type(http_client):
    """/operations должен фильтровать по user_id и type=website."""

    user_id = await _create_user(http_client)

    file_op_id = await _create_file_operation(http_client, user_id=user_id, target_format="pdf")
    website_op_id = await _create_website_operation(http_client, user_id=user_id)

    # Все операции пользователя
    resp_all = await http_client.get(f"/operations?user_id={user_id}")
    assert resp_all.status_code == 200
    ops = resp_all.json()
    ids = {op["operation_id"] for op in ops}
    assert file_op_id in ids
    assert website_op_id in ids

    # Только website-операции
    resp_web = await http_client.get(f"/operations?user_id={user_id}&type=website")
    assert resp_web.status_code == 200
    web_ops = resp_web.json()
    assert web_ops, "Ожидаем хотя бы одну website-операцию"
    for op in web_ops:
        assert op["operation_id"] in ids


async def test_operations_list_bad_user_id_returns_400(http_client):
    """Некорректный user_id в query должен приводить к 400, а не 500."""

    resp = await http_client.get("/operations?user_id=not-an-int")
    assert resp.status_code == 400
