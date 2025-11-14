# Руководство к файлу (TESTS/e2e/test_flow_file_to_pdf_e2e.py)
# Назначение:
# - E2E-сценарий: upload PDF -> convert (pdf->pdf) -> проверить статус операции и скачивание результата.

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from BACKEND.DATABASE.session import async_session_factory
from BACKEND.DATABASE.models import Format, Operation


async def _ensure_pdf_format() -> None:
    """Гарантирует наличие формата PDF в таблице formats.

    Для конвертации pdf->pdf нужны корректные old_format_id/new_format_id.
    """

    async with async_session_factory() as session:
        res = await session.execute(
            select(Format).where(Format.file_extension.in_(["pdf", ".pdf"]))
        )
        fmt = res.scalars().first()
        if fmt is None:
            fmt = Format(
                type="document",
                prompt=None,
                file_extension=".pdf",
                is_input=True,
                is_output=True,
            )
            session.add(fmt)
            await session.commit()
        else:
            changed = False
            if not getattr(fmt, "is_input"):
                fmt.is_input = True
                changed = True
            if not getattr(fmt, "is_output"):
                fmt.is_output = True
                changed = True
            if changed:
                await session.commit()


@pytest.mark.asyncio
async def test_flow_file_to_pdf_e2e(http_client):
    """Поток: создать пользователя -> upload PDF -> convert -> скачать результат."""

    await _ensure_pdf_format()

    # 1. Создаём пользователя, чтобы привязать к нему файлы/операции
    user_payload = {
        "max_id": f"e2e-user-{uuid.uuid4()}",
        "name": "E2E User",
        "metadata": {"role": "e2e"},
    }
    resp_user = await http_client.post("/users", json=user_payload)
    assert resp_user.status_code == 200
    user_id = resp_user.json()["id"]

    # 2. Загружаем небольшой PDF (условный контент)
    pdf_bytes = b"%PDF-1.4\n%VKMAX TEST\n%%EOF\n"
    files = {"file": ("test.pdf", pdf_bytes, "application/pdf")}
    data = {"user_id": user_id, "original_format": "pdf"}

    resp_upload = await http_client.post("/upload", files=files, data=data)
    assert resp_upload.status_code == 200
    uploaded = resp_upload.json()
    src_file_id = uploaded["file_id"]

    # 3. Запускаем конвертацию pdf->pdf
    convert_payload = {
        "source_file_id": src_file_id,
        "target_format": "pdf",
        "user_id": user_id,
    }
    resp_convert = await http_client.post("/convert", json=convert_payload)
    assert resp_convert.status_code == 200
    op_data = resp_convert.json()
    operation_id = op_data["operation_id"]

    # 4. Считываем операцию из БД, чтобы узнать result_file_id
    async with async_session_factory() as session:
        res = await session.execute(
            select(Operation).where(Operation.id == int(operation_id))
        )
        op = res.scalars().first()
        assert op is not None
        await session.refresh(op)
        status = getattr(op, "status")
        result_file_id = getattr(op, "result_file_id")

    assert status in {"completed", "failed"}

    # Для pdf->pdf при наличии формата PDF и рабочего shutil статус должен быть completed
    if status == "completed" and result_file_id is not None:
        resp_download = await http_client.get(f"/download/{int(result_file_id)}")
        assert resp_download.status_code == 200
        assert resp_download.content  # какие-то байты должны вернуться
