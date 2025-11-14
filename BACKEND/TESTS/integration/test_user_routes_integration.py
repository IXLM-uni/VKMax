# Руководство к файлу (TESTS/integration/test_user_routes_integration.py)
# Назначение:
# - Интеграционные тесты для роутера пользователей `/users`.
# - Проверяют базовый CRUD и связанные списки файлов/операций.

from __future__ import annotations

import uuid

import pytest


@pytest.mark.asyncio
async def test_user_crud_and_related_lists(http_client):
    """Полный цикл: create -> get -> lists -> delete -> 404."""

    # Создаём пользователя
    payload = {
        "max_id": f"test-max-{uuid.uuid4()}",
        "name": "Test User",
        "metadata": {"role": "tester"},
    }
    resp_create = await http_client.post("/users", json=payload)
    assert resp_create.status_code == 200

    user = resp_create.json()
    user_id = user["id"]

    assert user["max_id"] == payload["max_id"]
    assert user["name"] == payload["name"]
    assert isinstance(user["created_at"], str)

    # Читаем пользователя по id
    resp_get = await http_client.get(f"/users/{user_id}")
    assert resp_get.status_code == 200
    user_got = resp_get.json()
    assert user_got["id"] == user_id
    assert user_got["max_id"] == payload["max_id"]

    # Список файлов пользователя (пока пустой)
    resp_files = await http_client.get(f"/users/{user_id}/files")
    assert resp_files.status_code == 200
    files = resp_files.json()
    assert isinstance(files, list)
    assert files == []

    # Список операций пользователя (пока пустой)
    resp_ops = await http_client.get(f"/users/{user_id}/operations")
    assert resp_ops.status_code == 200
    ops = resp_ops.json()
    assert isinstance(ops, list)
    assert ops == []

    # Удаляем пользователя
    resp_delete = await http_client.delete(f"/users/{user_id}")
    assert resp_delete.status_code == 200
    assert resp_delete.json().get("ok") is True

    # Повторный GET должен вернуть 404
    resp_get_404 = await http_client.get(f"/users/{user_id}")
    assert resp_get_404.status_code == 404
