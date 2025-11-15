"""Руководство к файлу (BACKEND/BOT/SERVICES/state.py)
Назначение:
- Содержит перечисления FSM‑состояний для сложных сценариев бота VKMax.
- Используется совместно с aiomax.fsm.FSMCursor в роутерах.
"""

from __future__ import annotations

from enum import Enum, auto


class ConvertState(Enum):
    """Состояния сценария конвертации документа."""

    CHOOSING_FILE = auto()
    CHOOSING_FORMAT = auto()
    CONFIRMING = auto()


class WebsiteConvertState(Enum):
    """Состояния сценария конвертации сайта (website)."""

    ENTERING_URL = auto()
    QUEUED = auto()
    WAITING_RESULT = auto()