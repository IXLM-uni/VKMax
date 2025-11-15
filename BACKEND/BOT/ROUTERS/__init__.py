"""Руководство к пакету (BACKEND/BOT/ROUTERS)
Назначение:
- Содержит aiomax.Router‑модули по функциональным областям (user, files, convert и т.п.).
- Логически зеркалит структуру FAST_API/ROUTES.
"""

from . import auth, convert, download, files, format, system, user

__all__ = [
    "auth",
    "convert",
    "download",
    "files",
    "format",
    "system",
    "user",
]

