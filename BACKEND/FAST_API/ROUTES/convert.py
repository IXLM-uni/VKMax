# Руководство к файлу (ROUTES/convert.py)
# Назначение:
# - Операции конвертации файлов/сайтов и их статусы поверх БД (SQLAlchemy async).
# - Очередь/воркер не реализованы: создаём операции в статусе queued.

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..schemas import (
    ConvertRequest,
    ConvertWebsiteRequest,
    BatchConvertRequest,
    OperationResponse,
    OperationStatusResponse,
    WebsiteStatusResponse,
    WebsitePreviewRequest,
    WebsitePreviewResponse,
)
from ...DATABASE.session import get_db_session
from ...DATABASE.CACHE_MANAGER import ConvertManager
from ...DATABASE.models import Format, File as FileModel


router = APIRouter(tags=["convert"])


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _resolve_format_id(session: AsyncSession, fmt: Optional[str]) -> Optional[int]:
    if not fmt:
        return None
    key = str(fmt).lower().lstrip('.')
    res = await session.execute(select(Format).where(Format.file_extension.in_([key, f'.{key}'])))
    f = res.scalars().first()
    return int(getattr(f, 'id')) if f is not None else None


@router.post("/convert", response_model=OperationResponse)
async def convert(payload: ConvertRequest, session: AsyncSession = Depends(get_db_session)):
    if not payload.source_file_id and not payload.url:
        raise HTTPException(400, "Either source_file_id or url is required")
    if payload.source_file_id and payload.url:
        raise HTTPException(400, "Provide only one of source_file_id or url")

    cm = ConvertManager(session)
    target_fmt_id = await _resolve_format_id(session, payload.target_format)

    if payload.source_file_id:
        try:
            fid = int(payload.source_file_id)
        except Exception:
            raise HTTPException(400, "Bad source_file_id")
        op = await cm.create_file_operation(user_id=int(payload.user_id) if payload.user_id else None, source_file_id=fid, target_format_id=target_fmt_id)
    else:
        op = await cm.create_website_operation(user_id=int(payload.user_id) if payload.user_id else None, target_format_id=target_fmt_id)

    return OperationResponse(operation_id=str(getattr(op, 'id')), status='queued', estimated_time=5.0, queue_position=None)


@router.post("/convert/website", response_model=OperationResponse)
async def convert_website(payload: ConvertWebsiteRequest, session: AsyncSession = Depends(get_db_session)):
    cm = ConvertManager(session)
    target_fmt_id = await _resolve_format_id(session, payload.target_format)
    op = await cm.create_website_operation(user_id=int(payload.user_id) if payload.user_id else None, target_format_id=target_fmt_id)
    return OperationResponse(operation_id=str(getattr(op, 'id')), status='queued', estimated_time=5.0, queue_position=None)


@router.post("/batch-convert")
async def batch_convert(payload: BatchConvertRequest, session: AsyncSession = Depends(get_db_session)):
    items: List[Dict[str, Any]] = []
    for it in payload.operations:
        entry: Dict[str, Any] = {}
        if it.source_file_id:
            try:
                entry["source_file_id"] = int(it.source_file_id)
            except Exception:
                raise HTTPException(400, "Bad source_file_id in batch")
            entry["type"] = "file"
        elif it.url:
            entry["type"] = "website"
        else:
            raise HTTPException(400, "Operation requires source_file_id or url")
        entry["target_ext"] = it.target_format
        items.append(entry)
    cm = ConvertManager(session)
    ids = await cm.batch_create(user_id=int(payload.user_id) if payload.user_id else None, items=items)
    return {"batch_id": None, "operations": [{"operation_id": str(i), "status": "queued", "estimated_time": 5.0} for i in ids]}


@router.get("/operations/{operation_id}", response_model=OperationStatusResponse)
async def get_operation(operation_id: str, session: AsyncSession = Depends(get_db_session)):
    try:
        oid = int(operation_id)
    except Exception:
        raise HTTPException(400, "Bad operation id")
    cm = ConvertManager(session)
    op = await cm.get_operation(oid)
    if op is None:
        raise HTTPException(404, "Operation not found")
    return OperationStatusResponse(
        operation_id=str(op.get("operation_id")),
        user_id=str(op.get("user_id")) if op.get("user_id") is not None else None,
        file_id=str(op.get("file_id")) if op.get("file_id") is not None else None,
        url="",
        old_format=str(op.get("old_format_id")) if op.get("old_format_id") is not None else None,
        new_format=str(op.get("new_format_id")) if op.get("new_format_id") is not None else None,
        datetime=str(op.get("datetime")),
        status=str(op.get("status")),
        progress=0,
    )


@router.get("/operations")
async def list_operations(user_id: Optional[str] = Query(None), status: Optional[str] = Query(None), type: Optional[str] = Query(None), session: AsyncSession = Depends(get_db_session)):
    uid = None
    if user_id is not None:
        try:
            uid = int(user_id)
        except Exception:
            raise HTTPException(400, "Bad user id")
    cm = ConvertManager(session)
    rows = await cm.list_operations(user_id=uid, status=status, type_hint=type)
    # добавить url="" для совместимости схемы
    out = []
    for r in rows:
        item = dict(r)
        item["operation_id"] = str(item.get("operation_id"))
        item["file_id"] = str(item.get("file_id")) if item.get("file_id") is not None else None
        item["url"] = ""
        out.append(item)
    return out


# --------------------------- Website specific ---------------------------

@router.get("/websites/{operation_id}/status", response_model=WebsiteStatusResponse)
async def website_status(operation_id: str, session: AsyncSession = Depends(get_db_session)):
    try:
        oid = int(operation_id)
    except Exception:
        raise HTTPException(400, "Bad operation id")
    cm = ConvertManager(session)
    op = await cm.get_operation(oid)
    if op is None:
        raise HTTPException(404, "Website operation not found")
    return WebsiteStatusResponse(
        operation_id=str(op.get("operation_id")),
        url="",
        status=str(op.get("status")),
        progress=0,
        result_file_id=str(op.get("result_file_id")) if op.get("result_file_id") is not None else None,
    )


@router.post("/websites/preview", response_model=WebsitePreviewResponse)
async def website_preview(payload: WebsitePreviewRequest):
    # MVP-заглушка: прелоадер по URL
    title = payload.url
    return WebsitePreviewResponse(title=title, description=None, screenshot_url=None, page_count=None)


@router.get("/websites/history")
async def website_history(user_id: Optional[str] = Query(None), session: AsyncSession = Depends(get_db_session)):
    uid = None
    if user_id is not None:
        try:
            uid = int(user_id)
        except Exception:
            raise HTTPException(400, "Bad user id")
    cm = ConvertManager(session)
    rows = await cm.list_operations(user_id=uid, type_hint='website')
    # Возвращаем url="" для совместимости
    return [
        {
            "operation_id": str(r.get("operation_id")),
            "url": "",
            "format": None,
            "datetime": r.get("datetime"),
            "status": r.get("status"),
        }
        for r in rows
    ]
