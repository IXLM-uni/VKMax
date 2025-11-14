# Руководство к файлу (TESTS/integration/test_download_routes_integration.py)
# Назначение:
# - Интеграционные тесты для роутера скачивания `/download`.
# - Проверяют preview с корректным MIME и поведение при отсутствии файла на диске.

from __future__ import annotations

import os
from io import BytesIO

import pytest


@pytest.mark.asyncio
async def test_download_preview_ok_and_404(http_client):
    """Поток: upload -> preview OK -> удалить файл -> preview 404."""

    # 1. Создаём пользователя
    user_payload = {
        "max_id": "download-user",
        "name": "Download User",
        "metadata": {"role": "download"},
    }
    resp_user = await http_client.post("/users", json=user_payload)
    assert resp_user.status_code == 200
    user_id = resp_user.json()["id"]

    # 2. Загружаем PDF-файл
    pdf_bytes = b"%PDF-1.4\n%VKMAX DOWNLOAD TEST\n%%EOF\n"
    files = {"file": ("download.pdf", BytesIO(pdf_bytes), "application/pdf")}
    data = {"user_id": user_id, "original_format": "pdf"}

    resp_upload = await http_client.post("/upload", files=files, data=data)
    assert resp_upload.status_code == 200
    uploaded = resp_upload.json()
    file_id = uploaded["file_id"]

    # 3. Preview должен отдать application/pdf
    resp_preview = await http_client.get(f"/download/{file_id}/preview")
    assert resp_preview.status_code == 200
    ctype = resp_preview.headers.get("content-type", "")
    assert "application/pdf" in ctype or "application/octet-stream" in ctype

    # 4. Удаляем файл с диска, но оставляем запись в БД
    resp_meta = await http_client.get(f"/files/{file_id}")
    assert resp_meta.status_code == 200
    meta = resp_meta.json()
    path = meta.get("path")
    if path and os.path.exists(path):
        os.remove(path)

    # 5. Повторный preview должен вернуть 404
    resp_preview_404 = await http_client.get(f"/download/{file_id}/preview")
    assert resp_preview_404.status_code == 404
