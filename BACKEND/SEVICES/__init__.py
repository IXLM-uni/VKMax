# Руководство к файлу (SEVICES/__init__.py)
# Назначение:
# - Объявляет пакет VKMax.BACKEND.SEVICES.
# - Экспортирует основные сервисы и функцию настройки логирования,
#   импортируемую из BACKEND.CONVERT.logging_config.

from __future__ import annotations

from BACKEND.CONVERT.logging_config import setup_logging
from . import max_auth_service
from . import graph_service

__all__ = [
    "setup_logging",
    "max_auth_service",
    "graph_service",
]
