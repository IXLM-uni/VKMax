# Руководство к файлу (DATABASE/CACHE_MANAGER/format.py)
# Назначение:
# - Менеджер форматов: список всех, входные/выходные, матрица поддерживаемых конверсий.
# - Для MVP использует статическую матрицу соответствий вход→выход.

from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .base_class import BaseManager
from ..models import Format


# Простая матрица: ключ по названию входного формата (extension без точки или спец-метка)
SUPPORTED_CONVERSIONS: Dict[str, List[str]] = {
    "pdf": ["html"],
    "docx": ["html"],
    "website": ["html"],
    "html": ["graph"],
}


class FormatManager(BaseManager):
    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def list_all(self) -> List[Dict[str, Any]]:
        q = select(Format).order_by(Format.id.asc())
        res = await self.session.execute(q)
        rows = res.scalars().all()
        items: List[Dict[str, Any]] = []
        for f in rows:
            # Пытаемся вывести extension из столбца file_extension
            ext = getattr(f, "file_extension") or ""
            if isinstance(ext, str) and ext.startswith("."):
                ext = ext
            elif isinstance(ext, str) and ext:
                ext = "." + ext
            else:
                ext = ""
            items.append(
                {
                    "format_id": int(getattr(f, "id")),
                    "type": getattr(f, "type"),
                    "extension": ext,
                    "mime_type": None,  # заполним позже по справочнику
                    "is_input": bool(getattr(f, "is_input")),
                    "is_output": bool(getattr(f, "is_output")),
                }
            )
        return items

    async def list_input(self) -> List[Dict[str, Any]]:
        q = select(Format).where(Format.is_input.is_(True)).order_by(Format.id.asc())
        res = await self.session.execute(q)
        rows = res.scalars().all()
        out: List[Dict[str, Any]] = []
        for f in rows:
            ext = getattr(f, "file_extension") or ""
            if isinstance(ext, str) and not ext.startswith(".") and ext:
                ext = "." + ext
            out.append({
                "format_id": int(getattr(f, "id")),
                "type": getattr(f, "type"),
                "extension": ext,
                "is_input": True,
            })
        return out

    async def list_output_for_input(self, input_format: str) -> List[Dict[str, Any]]:
        key = (input_format or "").lower().lstrip(".")
        outs = SUPPORTED_CONVERSIONS.get(key)
        if not outs:
            return []
        # поднимаем форматы по file_extension
        result: List[Dict[str, Any]] = []
        for dst in outs:
            dst_key = dst.lower().lstrip(".")
            q = select(Format).where(Format.is_output.is_(True))
            res = await self.session.execute(q)
            rows = res.scalars().all()
            found = None
            for f in rows:
                ext = (getattr(f, "file_extension") or "").lstrip(".")
                if ext == dst_key:
                    found = f
                    break
            if found is not None:
                result.append({
                    "format_id": int(getattr(found, "id")),
                    "type": getattr(found, "type"),
                    "extension": ("." + dst_key),
                    "is_output": True,
                })
            else:
                # запасной вариант — вернуть запись по ключу без id
                result.append({
                    "format_id": -1,
                    "type": "document" if dst_key != "graph" else "graph",
                    "extension": "." + dst_key,
                    "is_output": True,
                })
        return result

    async def supported_matrix(self) -> Dict[str, List[str]]:
        return SUPPORTED_CONVERSIONS

