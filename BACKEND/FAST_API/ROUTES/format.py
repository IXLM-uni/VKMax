# Руководство к файлу (ROUTES/format.py)
# Назначение:
# - Эндпоинты форматов и матрицы конвертаций поверх БД (SQLAlchemy async).
# - Реализует: GET /formats, /formats/input, /formats/output, /supported-conversions

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..schemas import FormatItem
from BACKEND.DATABASE.session import get_db_session
from BACKEND.DATABASE.CACHE_MANAGER import FormatManager


router = APIRouter(tags=["formats"])


@router.get("/formats")
async def list_formats(session: AsyncSession = Depends(get_db_session)):
    mgr = FormatManager(session)
    items = await mgr.list_all()
    # адаптация: привести format_id к str
    return [FormatItem(**{**i, "format_id": str(i.get("format_id"))}).model_dump() for i in items]


@router.get("/formats/input")
async def list_input_formats(session: AsyncSession = Depends(get_db_session)):
    mgr = FormatManager(session)
    items = await mgr.list_input()
    return [{**i, "format_id": str(i.get("format_id"))} for i in items]


@router.get("/formats/output")
async def list_output_formats(input_format: str = Query(..., alias="input_format"), session: AsyncSession = Depends(get_db_session)):
    key = (input_format or "").lower()
    if key in ("url",):
        input_format = "website"
    mgr = FormatManager(session)
    items = await mgr.list_output_for_input(input_format)
    if not items:
        raise HTTPException(404, "Unsupported input format")
    return [{**i, "format_id": str(i.get("format_id"))} for i in items]


@router.get("/supported-conversions")
async def supported_conversions(session: AsyncSession = Depends(get_db_session)):
    mgr = FormatManager(session)
    return await mgr.supported_matrix()
