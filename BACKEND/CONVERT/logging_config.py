# Руководство к файлу (CONVERT/logging_config.py)
# Назначение:
# - Централизованная настройка логирования для бэкенда VKMax (в первую очередь
#   для конвертации и LLM-пайплайнов).
# - Определяет формат логов и базовые именованные логгеры `vkmax.*`.
# Важно:
# - Модуль не зависит от FastAPI, его можно вызывать как из веб-приложения,
#   так и из фоновых воркеров.

from __future__ import annotations

import logging
import sys
from typing import Iterable


def _configure_handler(formatter: logging.Formatter) -> logging.Handler:
    """Создаёт stdout-обработчик с заданным форматтером.

    Выделено в отдельную функцию, чтобы не дублировать логику при переинициализации.
    """

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    return handler


def setup_logging(level: int = logging.INFO, extra_loggers: Iterable[str] | None = None) -> None:
    """Настраивает базовое логирование для VKMax.

    Формат сообщения:
      [2025-01-01 10:00:00] [INFO] [module:function:line] message

    Переиспользуется как в FastAPI-приложении, так и в сторонних воркерах.
    Повторный вызов функции безопасен: обработчики root-логгера будут очищены
    и заново инициализированы.
    """

    # Базовый форматтер
    formatter = logging.Formatter(
        fmt="[%(asctime)s] [%(levelname)s] [%(name)s:%(funcName)s:%(lineno)d] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    root = logging.getLogger()
    root.setLevel(level)

    # Удаляем старые обработчики, чтобы избежать дублирования
    for h in list(root.handlers):
        root.removeHandler(h)

    root.addHandler(_configure_handler(formatter))

    # Базовые доменные логгеры VKMax
    for name in [
        "vkmax.convert",
        "vkmax.llm",
        "vkmax.webparser",
        "vkmax.db",
        "vkmax.fastapi",
        "vkmax.fastapi.files",
        "vkmax.fastapi.convert",
        "vkmax.fastapi.download",
        "vkmax.fastapi.system",
        "vkmax.fastapi.user",
        "vkmax.fastapi.format",
    ]:
        lg = logging.getLogger(name)
        lg.setLevel(level)
        lg.propagate = True  # отдаём в root, который пишет в stdout

    # Пользовательские дополнительные логгеры
    if extra_loggers:
        for name in extra_loggers:
            lg = logging.getLogger(name)
            lg.setLevel(level)
            lg.propagate = True


__all__ = ["setup_logging"]

