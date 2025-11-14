# Руководство к файлу (TESTS/e2e/test_flow_file_to_graph_e2e.py)
# Назначение:
# - E2E-сценарий: upload PDF -> convert (graph) с заглушкой графогенератора -> download graph JSON.

from __future__ import annotations

import json
import uuid
from pathlib import Path

import pytest
from sqlalchemy import select

from BACKEND.DATABASE.session import async_session_factory
from BACKEND.DATABASE.models import Operation, File, Format
from BACKEND.DATABASE.CACHE_MANAGER import ConvertManager, FilesManager
from BACKEND.FAST_API.ROUTES import convert as convert_module


@pytest.mark.asyncio
async def test_flow_file_to_graph_e2e(http_client, monkeypatch):
    """Полный поток: /users -> /upload -> /convert (graph) -> /operations -> /download."""

    # Гарантируем mock-режим LLM (на всякий случай)
    monkeypatch.setenv("VKMAX_LLM_PROVIDER", "mock")

    async def fake_generate_graph_for_operation(session, *, operation_id: int, storage_dir: str) -> None:
        """Заглушка граф-сервиса для E2E: пишет простой JSON и обновляет операцию."""

        cm = ConvertManager(session)
        fm = FilesManager(session)

        res = await session.execute(select(Operation).where(Operation.id == int(operation_id)))
        op = res.scalars().first()
        if op is None:
            return

        # Находим graph-формат по type
        res_fmt = await session.execute(select(Format).where(Format.type == "graph"))
        graph_fmt = res_fmt.scalars().first()
        graph_fmt_id = int(getattr(graph_fmt, "id")) if graph_fmt is not None else None

        graph_path = Path(storage_dir) / f"flow-{operation_id}.graph.json"
        graph_path.parent.mkdir(parents=True, exist_ok=True)
        graph_data = {
            "nodes": [
                {"id": "n1", "label": "Root", "type": "root", "data": {}},
            ],
            "edges": [],
            "meta": {"source_title": "flow-test", "generated_at": "2025-01-01T00:00:00Z"},
        }
        graph_path.write_text(json.dumps(graph_data), encoding="utf-8")

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

    # Подменяем generate_graph_for_operation в роутере convert
    monkeypatch.setattr(convert_module, "generate_graph_for_operation", fake_generate_graph_for_operation)

    # 1. Пользователь
    user_payload = {
        "max_id": f"graph-flow-user-{uuid.uuid4()}",
        "name": "Graph Flow User",
        "metadata": {"role": "graph-flow"},
    }
    resp_user = await http_client.post("/users", json=user_payload)
    assert resp_user.status_code == 200
    user_id = resp_user.json()["id"]

    # 2. Загрузка PDF-файла
    pdf_bytes = b"%PDF-1.4\n%VKMAX GRAPH FLOW TEST\n%%EOF\n"
    files = {"file": ("graph-flow.pdf", pdf_bytes, "application/pdf")}
    data = {"user_id": user_id, "original_format": "pdf"}

    resp_upload = await http_client.post("/upload", files=files, data=data)
    assert resp_upload.status_code == 200
    src_file_id = resp_upload.json()["file_id"]

    # 3. Конвертация в graph
    convert_payload = {
        "source_file_id": src_file_id,
        "target_format": "graph",
        "user_id": user_id,
    }
    resp_convert = await http_client.post("/convert", json=convert_payload)
    assert resp_convert.status_code == 200
    op_data = resp_convert.json()
    operation_id = op_data["operation_id"]

    # 4. Проверяем статус операции
    resp_op = await http_client.get(f"/operations/{operation_id}")
    assert resp_op.status_code == 200
    op_json = resp_op.json()
    assert op_json["operation_id"] == operation_id
    assert op_json["status"] == "completed"

    # Находим result_file_id в БД
    async with async_session_factory() as session:
        res = await session.execute(select(Operation).where(Operation.id == int(operation_id)))
        op = res.scalars().first()
        assert op is not None
        result_file_id = getattr(op, "result_file_id")
        assert result_file_id is not None

    # 5. Скачиваем graph JSON
    resp_download = await http_client.get(f"/download/{int(result_file_id)}")
    assert resp_download.status_code == 200
    data = json.loads(resp_download.content.decode("utf-8"))
    assert data["nodes"]
    assert data["meta"]["source_title"] == "flow-test"
