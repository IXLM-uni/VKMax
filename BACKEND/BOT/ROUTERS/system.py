"""Руководство к файлу (BACKEND/BOT/ROUTERS/system.py)
Назначение:
- Системный роутер бота VKMax (ping/health, служебные команды).
- Логически отражает FAST_API/ROUTES/system.py, но в чат‑интерфейсе.
"""

from __future__ import annotations

import aiomax

from ..SERVICES.vkmax_api import client as vkmax_client


router = aiomax.Router()


@router.on_command("ping")
async def cmd_ping(ctx: aiomax.CommandContext):
    """Простой ping‑хендлер для проверки, что бот жив."""

    await ctx.reply("pong")


@router.on_command("stats")
async def cmd_stats(ctx: aiomax.CommandContext):
    """Показывает агрегированную статистику VKMax из /stats FastAPI."""

    data = await vkmax_client.get_stats()
    text = (
        "Статистика VKMax:\n"
        f"- Пользователей: {data.get('total_users', 0)}\n"
        f"- Файлов: {data.get('total_files', 0)}\n"
        f"- Операций: {data.get('total_operations', 0)}\n"
        f"- Конвертаций за сегодня: {data.get('conversions_today', 0)}\n"
        f"- Website‑конвертаций: {data.get('website_conversions', 0)}"
    )
    await ctx.reply(text)


@router.on_message("Мои операции")
async def msg_operations(message: aiomax.Message):
    """Обработчик кнопки «Мои операции» из главного меню.

    Пока что выводит заглушку о том, что история операций доступна в мини‑приложении.
    """

    await message.reply(
        "История операций в боте пока в разработке. "
        "Используйте мини‑приложение VKMax для просмотра операций."
    )