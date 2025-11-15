"""Руководство к файлу (BACKEND/BOT/ROUTERS/user.py)
Назначение:
- Роутер aiomax для обработки пользовательских команд (/start и др.).
- Показывает главное меню и базовую информацию о VKMax.
"""

from __future__ import annotations

import aiomax

from ..KEYBOARDS import main_menu_keyboard


router = aiomax.Router()


@router.on_bot_start()
async def on_bot_start(payload: aiomax.BotStartPayload):
    """Хендлер нажатия кнопки «Начать» в ЛС с ботом."""

    text = (
        "Привет! Я бот VKMax.\n\n"
        "Я умею работать с твоим мини‑приложением VKMax: \n"
        "- загружать файлы,\n"
        "- запускать конвертацию,\n"
        "- показывать историю операций."
    )
    await payload.send(text, keyboard=main_menu_keyboard())


@router.on_command("start")
async def cmd_start(ctx: aiomax.CommandContext):
    """Команда /start — повторно показывает приветствие и главное меню."""

    text = (
        "VKMax бот готов к работе.\n\n"
        "Используй кнопки ниже, чтобы перейти к файлам или операциям."
    )
    await ctx.reply(text, keyboard=main_menu_keyboard())