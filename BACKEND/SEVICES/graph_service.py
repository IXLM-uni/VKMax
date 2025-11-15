"""Руководство к файлу (BACKEND/SEVICES/graph_service.py)
Назначение:
- Высокоуровневый сервис работы с JSON-графами по файлам VKMax.
- Умеет находить уже сгенерированный граф по исходному file_id и запускать
  генерацию нового графа через BACKEND.CONVERT.graph_service.
- Не зависит от FastAPI, принимает AsyncSession и параметры как аргументы.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from BACKEND.DATABASE.CACHE_MANAGER import ConvertManager
from BACKEND.DATABASE.models import File as FileModel, Format, Operation
from BACKEND.CONVERT import generate_graph_for_operation


logger = logging.getLogger("vkmax.services.graph")


async def _get_graph_format_id(session: AsyncSession) -> Optional[int]:
    """Найти ID формата graph в таблице formats (type="graph")."""

    res = await session.execute(select(Format).where(Format.type == "graph"))
    fmt = res.scalars().first()
    return int(getattr(fmt, "id")) if fmt is not None else None


async def get_graph_for_file(session: AsyncSession, *, source_file_id: int) -> Optional[Dict[str, Any]]:
    """Вернуть последний сгенерированный JSON-граф для исходного файла.

    Логика:
    - находим последнюю Operation со статусом completed, у которой:
      - Operation.file_id == source_file_id;
      - Operation.new_format_id указывает на формат типа "graph";
      - Operation.result_file_id не NULL;
    - читаем связанный File и возвращаем graph JSON из его path (если это JSON).
    """

    # Ищем операции + файл результата + формат
    q = (
        select(Operation, FileModel, Format)
        .join(FileModel, Operation.result_file_id == FileModel.id)
        .join(Format, Operation.new_format_id == Format.id)
        .where(
            Operation.file_id == source_file_id,
            Operation.status == "completed",
            Format.type == "graph",
        )
        .order_by(Operation.datetime.desc())
    )

    res = await session.execute(q)
    row = res.first()
    if row is None:
        return None

    op, file_obj, _fmt = row
    path = getattr(file_obj, "path", None)
    if not path:
        logger.error(
            "[graph_service.get_graph_for_file] result_file_id=%s has no path",
            getattr(file_obj, "id", None),
        )
        return None

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as exc:  # noqa: WPS430
        logger.exception(
            "[graph_service.get_graph_for_file] Failed to read JSON from %s: %s",
            path,
            exc,
        )
        return None

    logger.info(
        "[graph_service.get_graph_for_file] Loaded graph for file_id=%s from op_id=%s result_file_id=%s",
        source_file_id,
        getattr(op, "id", None),
        getattr(file_obj, "id", None),
    )

    # Ожидаем, что data уже имеет структуру GraphJson (nodes/edges/meta).
    return data


async def generate_graph_for_file(
    session: AsyncSession,
    *,
    source_file_id: int,
    user_id: Optional[int],
    storage_dir: str,
) -> Dict[str, Any]:
    """Создать операцию и сгенерировать JSON-граф для исходного файла.

    Шаги:
    1. Находим формат graph в таблице formats.
    2. Через ConvertManager.create_file_operation создаём Operation
       c new_format_id=graph_format_id.
    3. Вызываем generate_graph_for_operation из BACKEND.CONVERT, который:
       - извлекает текст;
       - вызывает LLM;
       - сохраняет graph JSON как новый File с format.type="graph";
       - помечает Operation.status и result_file_id.
    4. Через get_graph_for_file возвращаем итоговый graph JSON.
    """

    graph_format_id = await _get_graph_format_id(session)
    if graph_format_id is None:
        raise RuntimeError("Graph format not configured in DB (Format.type='graph')")

    cm = ConvertManager(session)
    op = await cm.create_file_operation(
        user_id=user_id,
        source_file_id=source_file_id,
        target_format_id=graph_format_id,
    )

    op_id = int(getattr(op, "id"))
    logger.info(
        "[graph_service.generate_graph_for_file] Start generation for file_id=%s operation_id=%s",
        source_file_id,
        op_id,
    )

    await generate_graph_for_operation(
        session,
        operation_id=op_id,
        storage_dir=storage_dir,
    )

    graph = await get_graph_for_file(session, source_file_id=source_file_id)
    if graph is None:
        raise RuntimeError("Graph generation failed: result JSON not found")

    logger.info(
        "[graph_service.generate_graph_for_file] Completed generation for file_id=%s operation_id=%s",
        source_file_id,
        op_id,
    )

    return graph
