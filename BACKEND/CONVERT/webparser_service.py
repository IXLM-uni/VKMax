# Руководство к файлу (CONVERT/webparser_service.py)
# Назначение:
# - Сервис интеграции WebParser с БД VKMax (website-операции).
# - Пока реализован как лёгкий каркас с логированием и заглушками; реальное
#   скачивание/парсинг сайта может быть добавлено позднее.

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from BACKEND.DATABASE.CACHE_MANAGER import ConvertManager


logger = logging.getLogger("vkmax.webparser")


async def enqueue_website_job(session: AsyncSession, *, operation_id: int) -> None:
    """Заглушка постановки website-операции в очередь.

    В текущем MVP фактической очереди нет: операции создаются в статусе queued,
    а дальнейшая обработка сайта должна быть реализована отдельным воркером.
    Функция оставлена для совместимости и логирования.
    """

    cm = ConvertManager(session)
    logger.info("[webparser_service.enqueue_website_job] Received website op=%s", operation_id)
    try:
        op = await cm.get_operation(operation_id)
    except Exception as exc:  # noqa: WPS430
        logger.exception("[webparser_service.enqueue_website_job] Failed to load operation %s: %s", operation_id, exc)
        return

    if op is None:
        logger.error("[webparser_service.enqueue_website_job] Operation %s not found", operation_id)
        return

    logger.info("[webparser_service.enqueue_website_job] Website operation is queued: %s", op)


async def get_website_status(session: AsyncSession, *, operation_id: int) -> Optional[Dict[str, Any]]:
    """Возвращает статус website-операции, обёртка над ConvertManager.get_operation."""

    cm = ConvertManager(session)
    logger.debug("[webparser_service.get_website_status] Get status for op=%s", operation_id)
    try:
        return await cm.get_operation(operation_id)
    except Exception as exc:  # noqa: WPS430
        logger.exception("[webparser_service.get_website_status] Failed to get operation %s: %s", operation_id, exc)
        return None


async def build_website_preview(url: str) -> Dict[str, Any]:
    """MVP-превью сайта.

    Сейчас возвращает простую структуру с title=url. Позже сюда можно добавить
    реальный HTTP-запрос, парсинг title/description/og-тегов и т.п.
    """

    logger.info("[webparser_service.build_website_preview] Build preview for url=%s", url)
    return {
        "title": url,
        "description": None,
        "screenshot_url": None,
        "page_count": None,
    }


__all__ = [
    "enqueue_website_job",
    "get_website_status",
    "build_website_preview",
]

