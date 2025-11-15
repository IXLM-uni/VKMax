"""Руководство к файлу (BACKEND/BOT/run_bot.py)
Назначение:
- Точка входа для запуска бота VKMax на платформе MAX.
- Создаёт экземпляр aiomax.Bot, подключает роутеры и настраивает логирование.
- Вызывается командой `python -m BACKEND.BOT.run_bot` или аналогом.
"""

from __future__ import annotations

import sys

import aiomax

from .confg import config
from .logging_config import logger, setup_logging
from .ROUTERS import auth, convert, download, files, format as format_router, system, user


def create_bot() -> aiomax.Bot:
    """Создаёт и настраивает экземпляр бота aiomax.Bot.

    Ожидает, что токен бота передан через VKMAX_BOT_TOKEN в окружении.
    """

    if not config.bot_token:
        raise RuntimeError("Переменная окружения VKMAX_BOT_TOKEN не задана")

    bot = aiomax.Bot(
        config.bot_token,
        default_format="markdown",
    )

    # Подключаем роутеры как зеркала HTTP‑слоя FAST_API.
    bot.add_router(user.router)
    bot.add_router(files.router)
    bot.add_router(convert.router)
    bot.add_router(download.router)
    bot.add_router(format_router.router)
    bot.add_router(system.router)
    bot.add_router(auth.router)

    return bot


def main() -> None:
    """Точка входа: настраивает логирование и запускает long polling бота."""

    setup_logging(debug=config.debug)

    try:
        bot = create_bot()
    except RuntimeError as exc:  # нет токена бота
        logger.error("Не удалось запустить бота: %s", exc)
        sys.exit(1)

    logger.info("Запуск VKMax Bot (debug=%s)", config.debug)
    bot.run()


if __name__ == "__main__":
    main()