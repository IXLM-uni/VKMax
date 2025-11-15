"""Руководство к файлу (BACKEND/BOT/logging_config.py)
Назначение:
- Конфигурирует стандартное логирование для бота VKMax.
- Используется из run_bot.py перед запуском aiomax.Bot.
"""

from __future__ import annotations

import logging


def setup_logging(debug: bool = False) -> None:
    """Инициализирует базовое логирование.

    Параметры:
    - debug: если True, уровень логирования DEBUG, иначе INFO.
    """

    level = logging.DEBUG if debug else logging.INFO

    # Если логирование уже настроено, не переопределяем формат хендлеров.
    if logging.getLogger().handlers:
        logging.getLogger().setLevel(level)
        return

    logging.basicConfig(
        level=level,
        format="[%(asctime)s] [%(levelname)s] %(name)s: %(message)s",
    )


logger = logging.getLogger("vkmax.bot")