"""Руководство к пакету (BACKEND/BOT/KEYBOARDS)
Назначение:
- Содержит билдеры inline‑клавиатур для чат‑бота VKMax.
- Общие клавиатуры лежат в common.py, сценарные (конвертация и т.п.) — в convert.py.
"""

from .common import main_menu_keyboard, open_app_keyboard
from .convert import formats_keyboard

__all__ = [
    "main_menu_keyboard",
    "open_app_keyboard",
    "formats_keyboard",
]

