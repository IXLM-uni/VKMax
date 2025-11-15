# Руководство к файлу (ROUTES/graph.py)
# Назначение:
# - HTTP-роуты для работы с JSON-графами по файлам.
# - Делегируют всю бизнес-логику в BACKEND.SEVICES.graph_service.

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from BACKEND.DATABASE.session import get_db_session
from BACKEND.SEVICES import graph_service


router = APIRouter(tags=["graph"])


@router.get("/graph/{file_id}")
async def get_graph(file_id: str, session: AsyncSession = Depends(get_db_session)) -> Dict[str, Any]:
    """Вернуть уже сгенерированный JSON-граф для файла.

    Если граф не найден, возвращаем `{ "file_id": ..., "graph": None }`
    без ошибки, чтобы фронт мог показать кнопку генерации.
    """

    try:
        fid = int(file_id)
    except Exception:
        raise HTTPException(400, "Bad file id")

    graph: Optional[Dict[str, Any]] = await graph_service.get_graph_for_file(session, source_file_id=fid)
    return {"file_id": file_id, "graph": graph}


@router.post("/graph/{file_id}")
async def generate_graph(file_id: str, session: AsyncSession = Depends(get_db_session)) -> Dict[str, Any]:
    """Сгенерировать JSON-граф для файла и вернуть его.

    - Создаёт Operation c target_format=graph через сервисный слой.
    - Вызывает генерацию графа (LLM + сохранение в File).
    - Возвращает готовый graph JSON из файла-результата.
    """

    try:
        fid = int(file_id)
    except Exception:
        raise HTTPException(400, "Bad file id")

    # user_id сейчас можно не привязывать (MVP). При необходимости сюда
    # можно пробрасывать реальный VKMax user_id из авторизации.
    graph = await graph_service.generate_graph_for_file(
        session,
        source_file_id=fid,
        user_id=None,
        storage_dir=settings.storage_dir,
    )

    return {"file_id": file_id, "graph": graph}
