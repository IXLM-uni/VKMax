"""Руководство к файлу (BACKEND/BOT/confg.py)
Назначение:
- Хранит и инициализирует настройки бота VKMax для платформы MAX.
- Считывает токен бота и URL FastAPI из переменных окружения VKMAX_*.
- Используется в run_bot.py и сервисах BOT.SERVICES.*.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class BotConfig:
    """Простая обёртка над настройками бота VKMax.

    Поля:
    - bot_token: токен бота MAX (обязателен для запуска).
    - fastapi_base_url: базовый URL HTTP‑API VKMax (FAST_API).
    - debug: флаг детализированного логирования.
    """

    bot_token: str
    fastapi_base_url: str
    debug: bool = False


def load_config() -> BotConfig:
    """Считывает настройки бота из переменных окружения VKMAX_*.

    Переменные окружения:
    - VKMAX_BOT_TOKEN — токен бота MAX.
    - VKMAX_FASTAPI_BASE_URL — базовый URL FastAPI (по умолчанию http://localhost:8000).
    - VKMAX_BOT_DEBUG — включает debug‑режим ("1", "true", "yes").
    """

    bot_token = os.getenv("VKMAX_BOT_TOKEN", "")
    fastapi_base_url = os.getenv(
        "VKMAX_FASTAPI_BASE_URL",
        "http://localhost:8000",
    )
    debug = os.getenv("VKMAX_BOT_DEBUG", "false").lower() in {"1", "true", "yes"}

    return BotConfig(
        bot_token=bot_token,
        fastapi_base_url=fastapi_base_url,
        debug=debug,
    )


# Глобальный экземпляр конфигурации, который можно импортировать из других модулей.
config = load_config()