# Руководство к файлу (ROUTES/download.py)
# Назначение:
# - Эндпоинты скачивания файлов поверх БД: /download/{file_id}, /download/{file_id}/preview
# - Потоковая отдача через FileResponse, корректные заголовки.

from __future__ import annotations

import os
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ...DATABASE.session import get_db_session
from ...DATABASE.CACHE_MANAGER import DownloadManager


router = APIRouter(tags=["download"])

@router.get("/download/{file_id}")
async def download_file(file_id: str, session: AsyncSession = Depends(get_db_session)):
    try:
        fid = int(file_id)
    except Exception:
        raise HTTPException(400, "Bad file id")
    mgr = DownloadManager(session)
    try:
        meta = await mgr.get_file_meta(fid)
    except FileNotFoundError:
        raise HTTPException(404, "File not found")
    return FileResponse(meta["path"], media_type="application/octet-stream", filename=meta.get("filename") or f"file-{file_id}")


@router.get("/download/{file_id}/preview")
async def preview_file(file_id: str, session: AsyncSession = Depends(get_db_session)):
    try:
        fid = int(file_id)
    except Exception:
        raise HTTPException(400, "Bad file id")
    mgr = DownloadManager(session)
    try:
        meta = await mgr.get_file_meta(fid)
    except FileNotFoundError:
        raise HTTPException(404, "File not found")
    return FileResponse(meta["path"], media_type=meta.get("mime") or "application/octet-stream")
