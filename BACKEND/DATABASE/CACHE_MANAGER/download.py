# Руководство к файлу (DATABASE/CACHE_MANAGER/download.py)
# Назначение:
# - Менеджер скачивания/предпросмотра: возвращает метаданные файла для отдачи через FastAPI.
# - Проверяет наличие пути и подбирает mime/type по format_id, если отсутствует.

from __future__ import annotations

import os
from typing import Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from .base_class import BaseManager
from ..models import File, Format


class DownloadManager(BaseManager):
    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def get_file_meta(self, file_id: int) -> Dict[str, Optional[str]]:
        rec = await self.get_by_id(File, file_id)
        if rec is None:
            raise FileNotFoundError("file not found")
        path = getattr(rec, "path")
        if not path or not os.path.exists(path):
            raise FileNotFoundError("file content missing")
        filename = getattr(rec, "filename") or f"file-{file_id}"
        mime = getattr(rec, "mime_type")
        if not mime:
            # попытка определить mime по format_id
            fmt = None
            try:
                fmt_id = getattr(rec, "format_id")
                if fmt_id is not None:
                    fmt = await self.get_by_id(Format, int(fmt_id))
            except Exception:
                fmt = None
            ext = (getattr(fmt, "file_extension") or "").lstrip(".") if fmt else None
            if ext == "html":
                mime = "text/html"
            elif ext == "pdf":
                mime = "application/pdf"
            else:
                mime = "application/octet-stream"
        return {"path": path, "filename": filename, "mime": mime}

