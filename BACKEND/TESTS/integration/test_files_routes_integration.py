# Руководство к файлу (TESTS/integration/test_files_routes_integration.py)
# Назначение:
# - Интеграционные тесты для роутера файлов `/upload` и `/files`.
# - Проверяют загрузку файла, получение, список и удаление.

from __future__ import annotations

from io import BytesIO

import pytest


@pytest.mark.asyncio
async def test_files_upload_list_get_delete(http_client):
    """Поток: upload -> get -> list -> delete -> get 404."""

    # Загружаем небольшой текстовый файл
    file_content = b"hello from tests"
    files = {"file": ("test.txt", BytesIO(file_content), "text/plain")}
    data = {"original_format": "txt"}

    resp_upload = await http_client.post("/upload", files=files, data=data)
    assert resp_upload.status_code == 200

    uploaded = resp_upload.json()
    file_id = uploaded["file_id"]

    assert uploaded["filename"] == "test.txt"
    assert uploaded["size"] == len(file_content)

    # Получаем файл по id (метаданные)
    resp_get = await http_client.get(f"/files/{file_id}")
    assert resp_get.status_code == 200
    meta = resp_get.json()
    assert meta["file_id"] == file_id
    assert meta["path"]

    # Список файлов должен содержать наш файл
    resp_list = await http_client.get("/files")
    assert resp_list.status_code == 200
    page = resp_list.json()
    assert "files" in page
    ids = {f["file_id"] if "file_id" in f else f.get("id") for f in page["files"]}
    assert file_id in ids

    # Удаляем файл
    resp_delete = await http_client.delete(f"/files/{file_id}")
    assert resp_delete.status_code == 200
    assert resp_delete.json().get("ok") is True

    # Повторный GET должен вернуть 404
    resp_get_404 = await http_client.get(f"/files/{file_id}")
    assert resp_get_404.status_code == 404
