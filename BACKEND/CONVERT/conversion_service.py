# Руководство к файлу (CONVERT/conversion_service.py)
# Назначение:
# - Сервис оркестрации файловых конверсий поверх низкоуровневых конвертеров
#   (CONVERT/converters.py) и БД (AsyncSession, ConvertManager, FilesManager).
# - Не знает о FastAPI напрямую: принимает сессию БД и параметры как аргументы.
# Важно:
# - Предполагается вызов из фонового воркера или BackgroundTasks по operation_id.

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .converters import (
    ConversionError,
    ConversionResult,
    convert_docx_to_docx,
    convert_docx_to_pdf,
    convert_pdf_to_docx,
    convert_pdf_to_pdf,
)
from .webparser_service import generate_site_pdf_from_bundle
from BACKEND.DATABASE.CACHE_MANAGER import ConvertManager, FilesManager
from BACKEND.DATABASE.models import File as FileModel, Format, Operation


logger = logging.getLogger("vkmax.convert")


def _ensure_dir(path: str) -> None:
    """Гарантирует существование директории для указанного пути файла."""

    try:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    except Exception:
        # Логируем, но не падаем: сама операция конвертации потом упадёт, если
        # путь реально недоступен.
        logger.warning("[conversion_service._ensure_dir] Failed to create dir for %s", path)


async def _resolve_format_ext(session: AsyncSession, format_id: Optional[int]) -> Optional[str]:
    """Возвращает расширение формата по его id (без точки)."""

    if format_id is None:
        return None
    res = await session.execute(select(Format).where(Format.id == int(format_id)))
    f = res.scalars().first()
    if not f:
        return None
    ext = getattr(f, "file_extension") or ""
    return ext.lstrip(".") if isinstance(ext, str) else None


async def run_file_conversion(
    session: AsyncSession,
    *,
    operation_id: int,
    storage_dir: str,
) -> None:
    """Выполняет файловую конвертацию для операции *operation_id*.

    Алгоритм:
      1. Загружает Operation и исходный File из БД.
      2. По old_format_id/new_format_id определяет тип конвертации.
      3. Вызывает соответствующий конвертер из converters.py.
      4. Создаёт новый File с результатом и обновляет Operation.result_file_id.
      5. В случае ошибки пишет статус failed и error_message.
    """

    cm = ConvertManager(session)
    fm = FilesManager(session)

    try:
        op = await cm.get_by_id(Operation, operation_id)  # type: ignore[arg-type]
    except Exception as exc:  # noqa: WPS430
        logger.exception("[conversion_service.run_file_conversion] Failed to load operation %s: %s", operation_id, exc)
        return

    if op is None:
        logger.error("[conversion_service.run_file_conversion] Operation %s not found", operation_id)
        return

    file_id = getattr(op, "file_id", None)
    new_format_id = getattr(op, "new_format_id", None)

    if file_id is None or new_format_id is None:
        logger.error(
            "[conversion_service.run_file_conversion] Operation %s has no file_id or new_format_id (file_id=%s, new_format_id=%s)",
            operation_id,
            file_id,
            new_format_id,
        )
        await cm.update_status(operation_id, status="failed", error_message="operation missing file_id or new_format_id")
        return

    logger.info(
        "[conversion_service.run_file_conversion] Start operation_id=%s file_id=%s new_format_id=%s",
        operation_id,
        file_id,
        new_format_id,
    )

    src: Optional[FileModel] = await fm.get_file(int(file_id))
    if src is None:
        msg = f"source file {file_id} not found"
        logger.error("[conversion_service.run_file_conversion] %s", msg)
        await cm.update_status(operation_id, status="failed", error_message=msg)
        return

    # Проверяем тип исходного формата: для site_bundle используем специальный поток
    src_format_id = getattr(src, "format_id", None)
    src_fmt: Optional[Format] = None
    if src_format_id is not None:
        try:
            res = await session.execute(select(Format).where(Format.id == int(src_format_id)))
            src_fmt = res.scalars().first()
        except Exception as exc:  # noqa: WPS430
            logger.exception(
                "[conversion_service.run_file_conversion] Failed to load src format id=%s for file_id=%s: %s",
                src_format_id,
                file_id,
                exc,
            )

    src_type = getattr(src_fmt, "type", None) if src_fmt is not None else None
    if src_type == "site_bundle":
        # Для site_bundle обходим файловые конвертеры и строим PDF напрямую из JSON-пакета сайта.
        logger.info(
            "[conversion_service.run_file_conversion] Detected site_bundle source file_id=%s, running generate_site_pdf_from_bundle",
            file_id,
        )
        try:
            new_file_id = await generate_site_pdf_from_bundle(session, file_id=int(file_id), storage_dir=storage_dir)
        except Exception as exc:  # noqa: WPS430
            logger.exception(
                "[conversion_service.run_file_conversion] generate_site_pdf_from_bundle failed for file_id=%s: %s",
                file_id,
                exc,
            )
            await cm.update_status(operation_id, status="failed", error_message=str(exc))
            return

        if not new_file_id:
            msg = "generate_site_pdf_from_bundle returned no result file id"
            logger.error("[conversion_service.run_file_conversion] %s", msg)
            await cm.update_status(operation_id, status="failed", error_message=msg)
            return

        await cm.update_status(
            operation_id,
            status="completed",
            error_message=None,
            result_file_id=int(new_file_id),
        )
        logger.info(
            "[conversion_service.run_file_conversion] site_bundle operation %s completed, result_file_id=%s",
            operation_id,
            int(new_file_id),
        )
        return

    src_path = getattr(src, "path")
    if not src_path or not os.path.exists(src_path):
        msg = f"source file path missing or not exists: {src_path}"
        logger.error("[conversion_service.run_file_conversion] %s", msg)
        await cm.update_status(operation_id, status="failed", error_message=msg)
        return

    old_fmt_id = getattr(op, "old_format_id", None)
    src_ext = await _resolve_format_ext(session, old_fmt_id)
    dst_ext = await _resolve_format_ext(session, new_format_id)

    if not src_ext or not dst_ext:
        msg = f"cannot resolve formats: src_ext={src_ext}, dst_ext={dst_ext}"
        logger.error("[conversion_service.run_file_conversion] %s", msg)
        await cm.update_status(operation_id, status="failed", error_message=msg)
        return

    # Готовим путь для выходного файла
    src_name = getattr(src, "filename") or os.path.basename(src_path)
    base_name = os.path.splitext(src_name)[0]
    dst_filename = f"{base_name}." + dst_ext
    dst_path = os.path.join(storage_dir, dst_filename)
    _ensure_dir(dst_path)

    try:
        result: ConversionResult
        if src_ext == "docx" and dst_ext == "docx":
            result = convert_docx_to_docx(src_path, dst_path)
        elif src_ext == "docx" and dst_ext == "pdf":
            result = convert_docx_to_pdf(src_path, dst_path)
        elif src_ext == "pdf" and dst_ext == "pdf":
            result = convert_pdf_to_pdf(src_path, dst_path)
        elif src_ext == "pdf" and dst_ext == "docx":
            result = convert_pdf_to_docx(src_path, dst_path)
        else:
            raise ConversionError(f"Unsupported conversion: {src_ext} -> {dst_ext}")

        logger.info(
            "[conversion_service.run_file_conversion] Conversion success op=%s %s->%s input=%s output=%s",
            operation_id,
            src_ext,
            dst_ext,
            result.input_path,
            result.output_path,
        )

        # Создаём запись файла результата
        new_file = await fm.create_file(
            user_id=getattr(op, "user_id", None),
            format_id=int(new_format_id),
            filename=os.path.basename(result.output_path),
            mime_type=None,
            content_bytes=None,
            path=result.output_path,
        )

        await cm.update_status(
            operation_id,
            status="completed",
            error_message=None,
            result_file_id=int(getattr(new_file, "id")),
        )

        logger.info(
            "[conversion_service.run_file_conversion] Operation %s completed, result_file_id=%s",
            operation_id,
            int(getattr(new_file, "id")),
        )

    except ConversionError as exc:
        msg = f"conversion failed: {exc}"
        logger.error("[conversion_service.run_file_conversion] %s", msg)
        await cm.update_status(operation_id, status="failed", error_message=msg)
    except Exception as exc:  # noqa: WPS430
        logger.exception("[conversion_service.run_file_conversion] Unexpected error for op=%s: %s", operation_id, exc)
        await cm.update_status(operation_id, status="failed", error_message=str(exc))


__all__ = ["run_file_conversion"]

