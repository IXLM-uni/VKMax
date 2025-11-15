# Руководство к файлу (DATABASE/CACHE_MANAGER/user.py)
# Назначение:
# - Менеджер пользователей: создание/чтение/удаление и выборки по файлам/операциям.
# - Работает поверх SQLAlchemy AsyncSession.

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .base_class import BaseManager
from ..models import User, File, Operation


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class UserManager(BaseManager):
    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def create_user(self, max_id: str, name: str, metadata: Optional[Dict[str, Any]] = None) -> User:
        obj = await self.create(User, {"max_id": max_id, "name": name, "extra_metadata": metadata or {}})
        return obj

    async def get_user(self, user_id: int) -> Optional[User]:
        return await self.get_by_id(User, user_id)

    async def get_user_by_max_id(self, max_id: str) -> Optional[User]:
        """Найти пользователя по внешнему идентификатору MAX (поле User.max_id)."""

        q = select(User).where(User.max_id == max_id)
        res = await self.session.execute(q)
        return res.scalars().first()

    async def delete_user(self, user_id: int) -> bool:
        affected = await self.delete_by_id(User, user_id)
        return affected > 0

    async def list_user_files(self, user_id: int) -> List[Dict[str, Any]]:
        q = select(File).where(File.user_id == user_id).order_by(File.created_at.desc())
        res = await self.session.execute(q)
        rows = res.scalars().all()
        return [
            {
                "file_id": int(getattr(r, "id")),
                "filename": getattr(r, "filename"),
                "format": int(getattr(r, "format_id")) if getattr(r, "format_id") is not None else None,
                "upload_date": getattr(r, "created_at").isoformat() if getattr(r, "created_at") else _now_iso(),
            }
            for r in rows
        ]

    async def list_user_operations(self, user_id: int) -> List[Dict[str, Any]]:
        q = select(Operation).where(Operation.user_id == user_id).order_by(Operation.datetime.desc())
        res = await self.session.execute(q)
        rows = res.scalars().all()
        items: List[Dict[str, Any]] = []
        for op in rows:
            items.append(
                {
                    "operation_id": int(getattr(op, "id")),
                    "file_id": int(getattr(op, "file_id")) if getattr(op, "file_id") is not None else None,
                    "old_format": int(getattr(op, "old_format_id")) if getattr(op, "old_format_id") is not None else None,
                    "new_format": int(getattr(op, "new_format_id")) if getattr(op, "new_format_id") is not None else None,
                    "datetime": getattr(op, "datetime").isoformat() if getattr(op, "datetime") else _now_iso(),
                    "status": getattr(op, "status"),
                }
            )
        return items

