# Руководство к файлу (ROUTES/user.py)
# Назначение:
# - Эндпоинты управления пользователями VKMax поверх БД (SQLAlchemy async).
# - Реализует: POST /users, GET /users/{id}, DELETE /users/{id},
#             GET /users/{id}/files, GET /users/{id}/operations.

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..schemas import UserCreateRequest, UserResponse
from BACKEND.DATABASE.session import get_db_session
from BACKEND.DATABASE.CACHE_MANAGER import UserManager


router = APIRouter(prefix="/users", tags=["users"])


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@router.post("", response_model=UserResponse)
async def create_user(payload: UserCreateRequest, session: AsyncSession = Depends(get_db_session)):
    mgr = UserManager(session)
    obj = await mgr.create_user(max_id=payload.max_id, name=payload.name, metadata=payload.metadata or {})
    return {
        "id": str(getattr(obj, "id")),
        "max_id": getattr(obj, "max_id"),
        "name": getattr(obj, "name"),
        "metadata": getattr(obj, "extra_metadata") or {},
        "created_at": getattr(obj, "created_at").isoformat() if getattr(obj, "created_at") else _now_iso(),
    }


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: str, session: AsyncSession = Depends(get_db_session)):
    try:
        uid = int(user_id)
    except Exception:
        raise HTTPException(400, "Bad user id")
    mgr = UserManager(session)
    obj = await mgr.get_user(uid)
    if obj is None:
        raise HTTPException(404, "User not found")
    return {
        "id": str(getattr(obj, "id")),
        "max_id": getattr(obj, "max_id"),
        "name": getattr(obj, "name"),
        "metadata": getattr(obj, "extra_metadata") or {},
        "created_at": getattr(obj, "created_at").isoformat() if getattr(obj, "created_at") else _now_iso(),
    }


@router.delete("/{user_id}")
async def delete_user(user_id: str, session: AsyncSession = Depends(get_db_session)):
    try:
        uid = int(user_id)
    except Exception:
        raise HTTPException(400, "Bad user id")
    mgr = UserManager(session)
    ok = await mgr.delete_user(uid)
    if not ok:
        raise HTTPException(404, "User not found")
    return {"ok": True}


@router.get("/{user_id}/files")
async def list_user_files(user_id: str, session: AsyncSession = Depends(get_db_session)):
    try:
        uid = int(user_id)
    except Exception:
        raise HTTPException(400, "Bad user id")
    mgr = UserManager(session)
    return await mgr.list_user_files(uid)


@router.get("/{user_id}/operations")
async def list_user_operations(user_id: str, session: AsyncSession = Depends(get_db_session)):
    try:
        uid = int(user_id)
    except Exception:
        raise HTTPException(400, "Bad user id")
    mgr = UserManager(session)
    return await mgr.list_user_operations(uid)
