# Руководство к файлу (TESTS/e2e/test_flow_assets_files_e2e.py)
# Назначение:
# - E2E-сценарии, использующие реальные файлы из BACKEND/TESTS/assets/files.
# - Проверяют, что API выдерживает реальные документы (DOCX/PDF) и корректно
#   обрабатывает успех/ошибки конвертации.

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from sqlalchemy import select

from BACKEND.DATABASE.session import async_session_factory
from BACKEND.DATABASE.models import Operation


ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets" / "files"


@pytest.mark.asyncio
async def test_flow_invoice_docx_to_pdf_asset_e2e(http_client):
    """Поток: upload DOCX (invoice.docx) -> convert(docx->pdf).

    Тест не требует, чтобы конвертация обязательно завершилась success: при
    отсутствии зависимостей (mammoth, pdfkit) статус может быть `failed`.
    Главное — что пайплайн операций и маршруты работают на реальном файле.
    """

    docx_path = ASSETS_DIR / "invoice.docx"
    assert docx_path.exists(), "invoice.docx должен лежать в TESTS/assets/files"

    # 1. Пользователь
    user_payload = {
        "max_id": f"assets-docx-user-{uuid.uuid4()}",
        "name": "Assets DOCX User",
        "metadata": {"role": "assets-docx"},
    }
    resp_user = await http_client.post("/users", json=user_payload)
    assert resp_user.status_code == 200
    user_id = resp_user.json()["id"]

    # 2. Upload DOCX
    with docx_path.open("rb") as f:
        files = {
            "file": (
                "invoice.docx",
                f,
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        }
        data = {"user_id": user_id, "original_format": "docx"}
        resp_upload = await http_client.post("/upload", files=files, data=data)

    assert resp_upload.status_code == 200
    src_file_id = resp_upload.json()["file_id"]

    # 3. convert(docx -> pdf)
    convert_payload = {
        "source_file_id": src_file_id,
        "target_format": "pdf",
        "user_id": user_id,
    }
    resp_convert = await http_client.post("/convert", json=convert_payload)
    assert resp_convert.status_code == 200
    op_data = resp_convert.json()
    operation_id = op_data["operation_id"]

    # 4. Проверяем статус операции в БД
    async with async_session_factory() as session:
        res = await session.execute(select(Operation).where(Operation.id == int(operation_id)))
        op = res.scalars().first()
        assert op is not None
        await session.refresh(op)
        status = getattr(op, "status")
        result_file_id = getattr(op, "result_file_id")

    # При отсутствии зависимостей возможен статус failed, это допустимо
    assert status in {"completed", "failed"}

    # Если всё-таки completed — проверяем скачивание результата
    if status == "completed" and result_file_id is not None:
        resp_download = await http_client.get(f"/download/{int(result_file_id)}")
        assert resp_download.status_code == 200
        assert resp_download.content


@pytest.mark.asyncio
async def test_flow_small_pdf_to_pdf_asset_e2e(http_client):
    """Поток: upload PDF (small.pdf) -> convert(pdf->pdf).

    Использует реальный PDF-файл из assets. По аналогии с тестом для DOCX,
    статус операции может быть `completed` или `failed`.
    """

    pdf_path = ASSETS_DIR / "small.pdf"
    assert pdf_path.exists(), "small.pdf должен лежать в TESTS/assets/files"

    # 1. Пользователь
    user_payload = {
        "max_id": f"assets-pdf-user-{uuid.uuid4()}",
        "name": "Assets PDF User",
        "metadata": {"role": "assets-pdf"},
    }
    resp_user = await http_client.post("/users", json=user_payload)
    assert resp_user.status_code == 200
    user_id = resp_user.json()["id"]

    # 2. Upload PDF
    with pdf_path.open("rb") as f:
        files = {"file": ("small.pdf", f, "application/pdf")}
        data = {"user_id": user_id, "original_format": "pdf"}
        resp_upload = await http_client.post("/upload", files=files, data=data)

    assert resp_upload.status_code == 200
    src_file_id = resp_upload.json()["file_id"]

    # 3. convert(pdf -> pdf)
    convert_payload = {
        "source_file_id": src_file_id,
        "target_format": "pdf",
        "user_id": user_id,
    }
    resp_convert = await http_client.post("/convert", json=convert_payload)
    assert resp_convert.status_code == 200
    op_data = resp_convert.json()
    operation_id = op_data["operation_id"]

    # 4. Проверяем статус операции в БД
    async with async_session_factory() as session:
        res = await session.execute(select(Operation).where(Operation.id == int(operation_id)))
        op = res.scalars().first()
        assert op is not None
        await session.refresh(op)
        status = getattr(op, "status")
        result_file_id = getattr(op, "result_file_id")

    assert status in {"completed", "failed"}

    if status == "completed" and result_file_id is not None:
        resp_download = await http_client.get(f"/download/{int(result_file_id)}")
        assert resp_download.status_code == 200
        assert resp_download.content
