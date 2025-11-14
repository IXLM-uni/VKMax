# Руководство к файлу (DATABASE/CACHE_MANAGER/files.py)
# Назначение:
# - Менеджер файлов VKMax: загрузка, чтение, обновление, удаление, список.
# - Поддержка хранения в БД (content) и/или на диске (path), совместимо с SQLite.

from __future__ import annotations

import base64
import os
from pathlib import Path
from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .base_class import BaseManager
from ..models import File


class FilesManager(BaseManager):
    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def create_file(
        self,
        *,
        user_id: Optional[int],
        format_id: Optional[int],
        filename: Optional[str],
        mime_type: Optional[str],
        content_bytes: bytes | None = None,
        path: Optional[str] = None,
    ) -> File:
        size = None
        if content_bytes is not None:
            size = len(content_bytes)
        elif path:
            try:
                size = os.path.getsize(path)
            except Exception:
                size = None

        obj = await self.create(
            File,
            {
                "user_id": user_id,
                "format_id": format_id,
                "filename": filename,
                "mime_type": mime_type,
                "content": content_bytes,
                "path": path,
                "file_size": size,
                "status": None,
            },
        )
        return obj

    async def get_file(self, file_id: int) -> Optional[File]:
        return await self.get_by_id(File, file_id)

    async def patch_content(self, file_id: int, content_b64: Optional[str] = None, new_format_id: Optional[int] = None) -> bool:
        data: Dict[str, Any] = {}
        if content_b64 is not None:
            try:
                raw = base64.b64decode(content_b64)
            except Exception:
                raise ValueError("Bad base64 content")
            data.update({"content": raw, "file_size": len(raw)})
        if new_format_id is not None:
            data["format_id"] = int(new_format_id)
        if not data:
            return True
        affected = await self.update_by_id(File, file_id, data)
        return affected > 0

    async def delete_file(self, file_id: int, remove_disk: bool = True) -> bool:
        rec = await self.get_by_id(File, file_id)
        if rec is None:
            return False
        if remove_disk:
            p = getattr(rec, "path", None)
            if p and os.path.exists(p):
                try:
                    os.remove(p)
                except Exception:
                    pass
        affected = await self.delete_by_id(File, file_id)
        return affected > 0

    async def list_files_page(self, *, user_id: Optional[int] = None, page: int = 1, limit: int = 20) -> Dict[str, Any]:
        where = []
        if user_id is not None:
            where.append(File.user_id == user_id)
        result = await self.paginate(File, where=where, order_by=File.created_at.desc(), page=page, limit=limit)
        # Нормализация под API
        items = [
            {
                "id": int(getattr(f, "id")),
                "user_id": int(getattr(f, "user_id")) if getattr(f, "user_id") is not None else None,
                "filename": getattr(f, "filename"),
                "format": int(getattr(f, "format_id")) if getattr(f, "format_id") is not None else None,
                "size": int(getattr(f, "file_size") or 0),
                "path": getattr(f, "path") or "",
                "created_at": getattr(f, "created_at").isoformat() if getattr(f, "created_at") else "",
            }
            for f in result["items"]
        ]
        return {"files": items, "total": result["total"], "page": result["page"], "pages": result["pages"]}

