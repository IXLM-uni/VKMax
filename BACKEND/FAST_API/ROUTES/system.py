# Руководство к файлу (ROUTES/system.py)
# Назначение:
# - Системные эндпоинты VKMax: /health, /stats, /webhook/conversion-complete поверх БД.
# - /stats агрегирует метрики из БД, /webhook обновляет статус операции в БД.

from __future__ import annotations

import os
from datetime import datetime, timezone
from fastapi import APIRouter, Header, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..schemas import HealthResponse, StatsResponse, WebhookConversionComplete
from BACKEND.DATABASE.session import get_db_session
from BACKEND.DATABASE.CACHE_MANAGER import SystemManager, ConvertManager


router = APIRouter(tags=["system"])


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@router.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(status="ok", timestamp=_now_iso(), version=settings.version)


@router.get("/stats", response_model=StatsResponse)
async def stats(authorization: str | None = Header(None), session: AsyncSession = Depends(get_db_session)):
    required = os.getenv("VKMAX_ADMIN_TOKEN", "")
    if required:
        token = (authorization or "").replace("Bearer ", "").strip()
        if token != required:
            raise HTTPException(401, "Unauthorized")
    mgr = SystemManager(session)
    s = await mgr.stats()
    return StatsResponse(
        total_users=s["total_users"],
        total_files=s["total_files"],
        total_operations=s["total_operations"],
        conversions_today=s["conversions_today"],
        website_conversions=s["website_conversions"],
    )


@router.post("/webhook/conversion-complete")
async def webhook_conversion_complete(payload: WebhookConversionComplete, session: AsyncSession = Depends(get_db_session)):
    try:
        oid = int(payload.operation_id)
    except Exception:
        raise HTTPException(400, "Bad operation id")
    cm = ConvertManager(session)
    rid = int(payload.converted_file_id) if payload.converted_file_id is not None else None
    ok = await cm.update_status(oid, status=payload.status, error_message=payload.error_message, result_file_id=rid)
    if not ok:
        raise HTTPException(404, "Operation not found")
    return {"ok": True}
