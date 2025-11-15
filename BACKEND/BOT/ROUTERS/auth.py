"""Руководство к файлу (BACKEND/BOT/ROUTERS/auth.py)
Назначение:
- Роутер бота VKMax, ответственный за авторизацию через MAX и запуск мини‑приложения.
- Использует WebAppButton (через KEYBOARDS.open_app_keyboard).
"""

from __future__ import annotations

import aiomax

from ..KEYBOARDS import open_app_keyboard


router = aiomax.Router()


@router.on_command("app")
async def cmd_open_app(ctx: aiomax.CommandContext):
    """Показывает кнопку для запуска мини‑приложения VKMax внутри MAX."""

    # Для демо используем username текущего бота; aiomax подставит корректно.
    kb = open_app_keyboard(bot=ctx.sender.user_id)
    text = (
        "Нажми кнопку ниже, чтобы открыть мини‑приложение VKMax.\n\n"
        "В нём реализована основная логика работы с файлами и конвертацией."
    )
    await ctx.reply(text, keyboard=kb)