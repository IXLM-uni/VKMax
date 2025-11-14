# Руководство к файлу (ROUTES/files.py)
# Назначение:
# - Управление файлами поверх БД: загрузка, получение, обновление, удаление, список.
# - Эндпоинты: POST /upload, POST /upload/website, GET/PATCH/DELETE /files/{id}, GET /files
# - Хранение контента на диске (storage_dir) с лимитом 40 МБ.

from __future__ import annotations

import base64
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
import logging

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, Query, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..schemas import FileUploadWebsiteRequest, FileUploadResponse, FilesPage
from BACKEND.DATABASE.session import get_db_session
from BACKEND.DATABASE.CACHE_MANAGER import FilesManager, ConvertManager
from BACKEND.DATABASE.models import Format, File as FileModel
from BACKEND.CONVERT import enqueue_website_job


logger = logging.getLogger("vkmax.fastapi.files")

router = APIRouter(tags=["files"])


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_join(*parts: str) -> str:
    return str(Path(*parts).resolve())


async def _save_upload_stream(upload: UploadFile, dst_path: str, max_bytes: int) -> int:
    size = 0
    with open(dst_path, "wb") as out:
        while True:
            chunk = await upload.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            if size > max_bytes:
                try:
                    out.close()
                finally:
                    try:
                        os.remove(dst_path)
                    except Exception:
                        pass
                raise HTTPException(413, "File too large (limit 40MB)")
            out.write(chunk)
    return size


async def _resolve_format_id(session: AsyncSession, value: Optional[str], fallback_filename: Optional[str]) -> Optional[int]:
    key = (value or (fallback_filename.split(".")[-1] if fallback_filename and "." in fallback_filename else None) or "").lower().lstrip(".")
    if not key:
        return None
    res = await session.execute(select(Format).where(Format.file_extension.in_([key, f".{key}"])) )
    f = res.scalars().first()
    return int(getattr(f, "id")) if f is not None else None


@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    user_id: Optional[str] = Form(None),
    original_format: Optional[str] = Form(None),
    session: AsyncSession = Depends(get_db_session),
):
    max_bytes = int(settings.max_upload_mb) * 1024 * 1024
    filename = file.filename or "upload"
    dst = _safe_join(settings.storage_dir, f"{filename}")
    size = await _save_upload_stream(file, dst, max_bytes)

    fmt_id = await _resolve_format_id(session, original_format, filename)
    mgr = FilesManager(session)
    obj = await mgr.create_file(
        user_id=int(user_id) if user_id is not None else None,
        format_id=fmt_id,
        filename=filename,
        mime_type=getattr(file, "content_type", None),
        content_bytes=None,
        path=dst,
    )
    # Переименуем файл с префиксом id, чтобы избежать коллизий
    try:
        file_id_str = str(getattr(obj, "id"))
        new_dst = _safe_join(settings.storage_dir, f"{file_id_str}__{filename}")
        if dst != new_dst:
            try:
                os.replace(dst, new_dst)
            except Exception:
                os.rename(dst, new_dst)
            await mgr.update_by_id(FileModel, int(getattr(obj, "id")), {"path": new_dst, "file_size": size})
            dst = new_dst
    except Exception:
        pass
    created_at = getattr(obj, "created_at")
    return FileUploadResponse(
        file_id=str(getattr(obj, "id")),
        filename=filename,
        size=size,
        upload_date=(created_at.isoformat() if created_at else _now_iso()),
    ).model_dump()


@router.post("/upload/website")
async def upload_website(payload: FileUploadWebsiteRequest, session: AsyncSession = Depends(get_db_session)):
    # Создаём website-операцию (без хранения URL в БД)
    target_fmt_id = await _resolve_format_id(session, payload.format, None)
    cm = ConvertManager(session)
    logger.info("[/upload/website] create website operation user_id=%s format=%s url=%s", payload.user_id, payload.format, payload.url)
    op = await cm.create_website_operation(user_id=int(payload.user_id) if payload.user_id else None, target_format_id=target_fmt_id)
    try:
        await enqueue_website_job(session, operation_id=int(getattr(op, "id")))
    except Exception as exc:  # noqa: WPS430
        logger.exception("[/upload/website] Failed to enqueue website operation_id=%s: %s", getattr(op, "id"), exc)
    return {
        "file_id": None,
        "operation_id": int(getattr(op, "id")),
        "status": "queued",
        "estimated_time": 5.0,
    }


@router.get("/files/{file_id}")
async def get_file(file_id: str, session: AsyncSession = Depends(get_db_session)):
    try:
        fid = int(file_id)
    except Exception:
        raise HTTPException(400, "Bad file id")
    mgr = FilesManager(session)
    obj = await mgr.get_file(fid)
    if obj is None:
        raise HTTPException(404, "File not found")
    # Контент не возвращаем
    # Разрешаем строковый формат из расширения, если доступен
    fmt_ext = None
    try:
        fmt_id = getattr(obj, "format_id")
        if fmt_id is not None:
            res = await session.execute(select(Format).where(Format.id == int(fmt_id)))
            f = res.scalars().first()
            if f is not None:
                ext = getattr(f, "file_extension") or ""
                fmt_ext = ext.lstrip(".") if isinstance(ext, str) else None
    except Exception:
        fmt_ext = None
    return {
        "file_id": str(getattr(obj, "id")),
        "user_id": int(getattr(obj, "user_id")) if getattr(obj, "user_id") is not None else None,
        "format": fmt_ext or None,
        "content": None,
        "path": getattr(obj, "path"),
        "created_at": getattr(obj, "created_at").isoformat() if getattr(obj, "created_at") else _now_iso(),
    }


@router.patch("/files/{file_id}")
async def patch_file(file_id: str, payload: dict, session: AsyncSession = Depends(get_db_session)):
    try:
        fid = int(file_id)
    except Exception:
        raise HTTPException(400, "Bad file id")
    content_b64 = payload.get("content")
    new_format = payload.get("format")
    if content_b64 is not None:
        # проверим лимит
        try:
            data = base64.b64decode(content_b64)
        except Exception:
            raise HTTPException(400, "Bad base64 content")
        max_bytes = int(settings.max_upload_mb) * 1024 * 1024
        if len(data) > max_bytes:
            raise HTTPException(413, "File too large (limit 40MB)")
    new_format_id = None
    if new_format:
        new_format_id = await _resolve_format_id(session, str(new_format), None)
    mgr = FilesManager(session)
    ok = await mgr.patch_content(fid, content_b64=content_b64, new_format_id=new_format_id)
    if not ok:
        raise HTTPException(404, "File not found")
    return {"ok": True}


@router.delete("/files/{file_id}")
async def delete_file(file_id: str, session: AsyncSession = Depends(get_db_session)):
    try:
        fid = int(file_id)
    except Exception:
        raise HTTPException(400, "Bad file id")
    mgr = FilesManager(session)
    ok = await mgr.delete_file(fid, remove_disk=True)
    if not ok:
        raise HTTPException(404, "File not found")
    return {"ok": True}


@router.get("/files", response_model=FilesPage)
async def list_files(user_id: Optional[str] = Query(None), page: int = 1, limit: int = 20, session: AsyncSession = Depends(get_db_session)):
    mgr = FilesManager(session)
    uid = None
    if user_id is not None:
        try:
            uid = int(user_id)
        except Exception:
            raise HTTPException(400, "Bad user id")
    result = await mgr.list_files_page(user_id=uid, page=page, limit=limit)
    # адаптация формата в строковое расширение
    out_files = []
    for f in result["files"]:
        fmt_str = None
        try:
            if f.get("format") is not None:
                res = await session.execute(select(Format).where(Format.id == int(f["format"])) )
                fm = res.scalars().first()
                if fm is not None:
                    ext = getattr(fm, "file_extension") or ""
                    fmt_str = ext.lstrip(".") if isinstance(ext, str) else None
        except Exception:
            fmt_str = None
        out_files.append({
            "id": str(f.get("id")),
            "user_id": (str(f.get("user_id")) if f.get("user_id") is not None else None),
            "filename": f.get("filename"),
            "format": fmt_str or "",
            "size": f.get("size", 0),
            "path": f.get("path", ""),
            "created_at": f.get("created_at", ""),
        })
    return FilesPage(files=out_files, total=result["total"], page=result["page"], pages=result["pages"]).model_dump()
