# Руководство к файлу (TESTS/integration/test_convert_routes_integration.py)
# Назначение:
# - Интеграционные тесты для роутера конвертации `/convert` и связанных ручек.
# - Проверяют конвертацию файла в граф (с заглушкой LLM-пайплайна) и website-конвертацию.

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from BACKEND.DATABASE.session import async_session_factory
from BACKEND.DATABASE.models import Operation, File, Format
from BACKEND.DATABASE.CACHE_MANAGER import ConvertManager, FilesManager
from BACKEND.FAST_API.ROUTES import convert as convert_module


@pytest.mark.asyncio
async def test_convert_file_to_graph_with_stubbed_generator(http_client, monkeypatch):
    """Файл -> graph: /upload + /convert с заглушенным generate_graph_for_operation.

    Проверяем, что создаётся Operation, её статус становится `completed`,
    и в БД появляется результатный файл graph-json.
    """

    # Подготовим пользователя
    user_payload = {
        "max_id": f"convert-user-{uuid.uuid4()}",
        "name": "Convert Graph User",
        "metadata": {"role": "convert-graph"},
    }
    resp_user = await http_client.post("/users", json=user_payload)
    assert resp_user.status_code == 200
    user_id = resp_user.json()["id"]

    # Загружаем PDF-файл как источник
    pdf_bytes = b"%PDF-1.4\n%VKMAX GRAPH TEST\n%%EOF\n"
    files = {"file": ("graph-src.pdf", pdf_bytes, "application/pdf")}
    data = {"user_id": user_id, "original_format": "pdf"}

    resp_upload = await http_client.post("/upload", files=files, data=data)
    assert resp_upload.status_code == 200
    src_file_id = resp_upload.json()["file_id"]

    async def fake_generate_graph_for_operation(session, *, operation_id: int, storage_dir: str) -> None:
        """Заглушка LLM-графа: создаёт простой JSON-файл и обновляет операцию.

        Использует реальные ConvertManager/FilesManager, но не вызывает LLM.
        """

        from pathlib import Path

        # Загружаем операцию
        res = await session.execute(select(Operation).where(Operation.id == int(operation_id)))
        op = res.scalars().first()
        if op is None:
            return

        cm = ConvertManager(session)
        fm = FilesManager(session)

        # Находим формат graph по type
        res_fmt = await session.execute(select(Format).where(Format.type == "graph"))
        graph_fmt = res_fmt.scalars().first()
        graph_fmt_id = int(getattr(graph_fmt, "id")) if graph_fmt is not None else None

        graph_path = Path(storage_dir) / f"operation-{operation_id}.graph.json"
        graph_path.parent.mkdir(parents=True, exist_ok=True)
        graph_content = (
            '{"nodes": [], "edges": [], '
            '"meta": {"source_title": "test-graph", "generated_at": "2025-01-01T00:00:00Z"}}'
        )
        graph_path.write_text(graph_content, encoding="utf-8")

        new_file = await fm.create_file(
            user_id=getattr(op, "user_id", None),
            format_id=graph_fmt_id,
            filename=graph_path.name,
            mime_type="application/json",
            content_bytes=None,
            path=str(graph_path),
        )

        await cm.update_status(
            operation_id,
            status="completed",
            error_message=None,
            result_file_id=int(getattr(new_file, "id")),
        )

    # Подменяем generate_graph_for_operation в роутере
    monkeypatch.setattr(convert_module, "generate_graph_for_operation", fake_generate_graph_for_operation)

    # Запускаем /convert с target_format="graph"
    payload = {"source_file_id": src_file_id, "target_format": "graph", "user_id": user_id}
    resp_convert = await http_client.post("/convert", json=payload)
    assert resp_convert.status_code == 200
    op_data = resp_convert.json()
    operation_id = op_data["operation_id"]

    # Проверяем статус операции через /operations/{id}
    resp_op = await http_client.get(f"/operations/{operation_id}")
    assert resp_op.status_code == 200
    op_json = resp_op.json()
    assert op_json["operation_id"] == operation_id
    assert op_json["status"] == "completed"

    # Проверяем, что в БД есть result_file_id и сам файл
    async with async_session_factory() as session:
        res = await session.execute(select(Operation).where(Operation.id == int(operation_id)))
        op = res.scalars().first()
        assert op is not None
        result_file_id = getattr(op, "result_file_id")
        assert result_file_id is not None

        res_file = await session.execute(select(File).where(File.id == int(result_file_id)))
        file_obj = res_file.scalars().first()
        assert file_obj is not None
        assert getattr(file_obj, "path")


@pytest.mark.asyncio
async def test_convert_website_status_and_history(http_client):
    """Website-поток: /convert/website -> /websites/{id}/status -> /websites/history."""

    # Создаём пользователя
    user_payload = {
        "max_id": f"website-user-{uuid.uuid4()}",
        "name": "Website User",
        "metadata": {"role": "website"},
    }
    resp_user = await http_client.post("/users", json=user_payload)
    assert resp_user.status_code == 200
    user_id = resp_user.json()["id"]

    # Создаём website-операцию для dev-домена
    conv_payload = {
        "url": "https://dev.max.ru/",
        "target_format": "html",
        "user_id": user_id,
    }
    resp_conv = await http_client.post("/convert/website", json=conv_payload)
    assert resp_conv.status_code == 200
    op_data = resp_conv.json()
    operation_id = op_data["operation_id"]
    assert op_data["status"] == "queued"

    # Статус website-операции
    resp_status = await http_client.get(f"/websites/{operation_id}/status")
    assert resp_status.status_code == 200
    st = resp_status.json()
    assert st["operation_id"] == operation_id
    assert st["status"] == "queued"

    # История website-операций
    resp_history = await http_client.get(f"/websites/history?user_id={user_id}")
    assert resp_history.status_code == 200
    history = resp_history.json()
    ids = {item["operation_id"] for item in history}
    assert operation_id in ids
