"""Руководство к пакету (BACKEND/BOT/SERVICES)
Назначение:
- Содержит вспомогательные сервисы для бота VKMax:
  - vkmax_api — клиент к HTTP‑слою VKMax (FAST_API);
  - max_api — обёртка над platform-api.max.ru (при необходимости);
  - state — FSM‑состояния;
  - mapping — вспомогательные функции маппинга пользователей.
"""

from . import max_api, mapping, state, vkmax_api

__all__ = [
    "max_api",
    "mapping",
    "state",
    "vkmax_api",
]

