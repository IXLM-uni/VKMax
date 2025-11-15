# Руководство к файлу (TESTS/e2e/test_flow_invalid_inputs_e2e.py)
# Назначение:
# - E2E-негативные сценарии для upload/convert.
# - Проверяют, что API корректно обрабатывает некорректные форматы, слишком большие файлы
#   и неверные параметры конвертации, возвращая 4xx, а не 500.

from __future__ import annotations

import io

import pytest


pytestmark = pytest.mark.asyncio


async def test_upload_unsupported_extension(http_client):
    """upload с неподдерживаемым расширением должен вернуть 200/4xx, но не 500.

    Текущая реализация пробует резолвить формат по расширению, но отсутствие формата
    не должно ломать API: файл может быть сохранён без format_id или с ошибкой уровня 4xx.
    Здесь мы фиксируем лишь то, что сервер не падает с 500.
    """

    file_content = b"dummy content"
    files = {"file": ("unsupported.xyz", io.BytesIO(file_content), "application/octet-stream")}
    data = {"original_format": "xyz"}

    resp = await http_client.post("/upload", files=files, data=data)
    assert resp.status_code < 500


async def test_upload_too_large_file_hits_413(http_client):
    """upload файла больше лимита должен отдавать 413 (File too large)."""

    # Лимит 40 МБ, соберём чуть больше (41 МБ). Используем BytesIO, чтобы не писать на диск.
    big_size = 41 * 1024 * 1024
    big_content = b"0" * big_size

    files = {"file": ("big.bin", io.BytesIO(big_content), "application/octet-stream")}
    data = {"original_format": "bin"}

    resp = await http_client.post("/upload", files=files, data=data)
    assert resp.status_code == 413


async def test_convert_with_bad_source_file_id_returns_400_or_404(http_client):
    """POST /convert с некорректным source_file_id должен вернуть 400/404, но не 500."""

    payload = {
        "source_file_id": "not-an-int",
        "target_format": "pdf",
        "user_id": "1",
    }
    resp = await http_client.post("/convert", json=payload)
    assert resp.status_code in {400, 404}


async def test_convert_with_unsupported_target_format_returns_4xx(http_client):
    """POST /convert с неподдерживаемым target_format должен возвращать 4xx.

    На текущем этапе поведение может быть разным (400/422), главное — не 500.
    Тест фиксирует этот контракт.
    """

    # Для корректного file_id сначала загрузим маленький файл
    file_content = b"dummy"
    files = {"file": ("test.txt", io.BytesIO(file_content), "text/plain")}
    data = {"original_format": "txt"}

    resp_upload = await http_client.post("/upload", files=files, data=data)
    assert resp_upload.status_code < 500
    file_id = resp_upload.json()["file_id"]

    bad_payload = {
        "source_file_id": file_id,
        "target_format": "unknown-format",
        "user_id": "1",
    }
    resp = await http_client.post("/convert", json=bad_payload)
    assert 400 <= resp.status_code < 500
