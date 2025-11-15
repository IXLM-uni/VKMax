"""Руководство к файлу (BACKEND/BOT/SERVICES/max_api.py)
Назначение:
- Заготовка клиента к platform-api.max.ru (MAX Bot API) для бота VKMax.
- Содержит интерфейс, который можно реализовать через aiohttp/httpx при необходимости.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass
class MaxApiConfig:
    """Настройки доступа к MAX Bot API."""

    token: str
    base_url: str = "https://platform-api.max.ru"


class MaxApiClient:
    """Минимальный интерфейс клиента к MAX Bot API.

    Реальная HTTP‑логика намеренно не реализована, чтобы не тянуть лишние зависимости.
    Методы следует реализовать по мере необходимости (через aiohttp/httpx).
    """

    def __init__(self, config: MaxApiConfig) -> None:
        self._config = config

    async def get_me(self) -> Mapping[str, Any]:  # pragma: no cover - заглушка
        """Вернуть информацию о боте (GET /me).

        На хакатоне достаточно реализовать это позже, при реальной интеграции.
        """

        raise NotImplementedError("MaxApiClient.get_me ещё не реализован")