"""Руководство к файлу (BACKEND/BOT/SERVICES/vkmax_api.py)
Назначение:
- HTTP‑клиент к FAST_API‑слою VKMax для использования из чат‑бота.
- Реализует запросы к /stats, /formats, /supported-conversions, /files и др.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional

import httpx

from ..confg import config


@dataclass
class VkmaxApiConfig:
    """Настройки клиента к VKMax FAST_API."""

    base_url: str
    admin_token: Optional[str] = None
    timeout: float = 10.0


class VkmaxApiClient:
    """Async‑клиент к VKMax FAST_API.

    Все методы делают HTTP‑запросы к FastAPI, развёрнутому в BACKEND/FAST_API.
    """

    def __init__(self, cfg: VkmaxApiConfig | None = None) -> None:
        admin_token = os.getenv("VKMAX_ADMIN_TOKEN", "") or None
        self._cfg = cfg or VkmaxApiConfig(
            base_url=config.fastapi_base_url,
            admin_token=admin_token,
        )

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        use_admin: bool = False,
    ) -> Any:
        """Выполнить HTTP‑запрос к VKMax FAST_API и вернуть JSON‑ответ.

        Если use_admin=True и задан VKMAX_ADMIN_TOKEN, добавляет заголовок
        Authorization: Bearer <token> (нужно для /stats).
        """

        headers: Dict[str, str] = {}
        if use_admin and self._cfg.admin_token:
            headers["Authorization"] = f"Bearer {self._cfg.admin_token}"

        async with httpx.AsyncClient(base_url=self._cfg.base_url, timeout=self._cfg.timeout) as client:
            resp = await client.request(method, path, params=params, json=json, headers=headers)
        resp.raise_for_status()
        return resp.json()

    async def get_stats(self) -> Mapping[str, Any]:
        """Вернуть агрегированную статистику сервиса (/stats)."""

        return await self._request("GET", "/stats", use_admin=True)

    async def list_formats(self) -> list[Dict[str, Any]]:
        """Вернуть список форматов из /formats."""

        data = await self._request("GET", "/formats")
        assert isinstance(data, list)
        return data  # список словарей FormatItem

    async def list_supported_conversions(self) -> Mapping[str, Any]:
        """Вернуть матрицу поддерживаемых конверсий из /supported-conversions."""

        data = await self._request("GET", "/supported-conversions")
        assert isinstance(data, dict)
        return data

    async def list_files(
        self,
        *,
        user_id: Optional[str] = None,
        page: int = 1,
        limit: int = 5,
    ) -> Mapping[str, Any]:
        """Вернуть страницу файлов из /files.

        user_id пока не используется (MVP показывает общую страницу файлов).
        """

        params: Dict[str, Any] = {"page": page, "limit": limit}
        # При появлении маппинга MAX user → VKMax user здесь можно будет
        # подставлять реальный user_id VKMax.
        if user_id is not None:
            params["user_id"] = user_id

        data = await self._request("GET", "/files", params=params)
        assert isinstance(data, dict)
        return data

    async def create_convert_operation(
        self,
        *,
        source_file_id: Optional[str],
        url: Optional[str],
        target_format: str,
        user_id: str,
    ) -> Mapping[str, Any]:
        """Создать операцию конвертации через POST /convert.

        Параметры соответствуют схеме ConvertRequest в FAST_API/schemas.py.
        """

        payload: Dict[str, Any] = {
            "source_file_id": source_file_id,
            "url": url,
            "target_format": target_format,
            "user_id": user_id,
        }
        data = await self._request("POST", "/convert", json=payload)
        assert isinstance(data, dict)
        return data


# Глобальный экземпляр клиента по умолчанию.
client = VkmaxApiClient()