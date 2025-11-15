"""Руководство к файлу (BACKEND/BOT/ROUTERS/files.py)
Назначение:
- Роутер бота VKMax для сценариев, связанных с файлами.
- В будущем будет вызывать VKMax FAST_API (/files, /upload и т.п.).
"""

from __future__ import annotations

import aiomax

from ..SERVICES.vkmax_api import client as vkmax_client


router = aiomax.Router()


@router.on_command("files")
async def cmd_files(ctx: aiomax.CommandContext):
    """Показывает страницу файлов из /files VKMax API (MVP)."""

    # Пока что не используем real user_id VKMax, а просто берём первую страницу.
    data = await vkmax_client.list_files(page=1, limit=5)
    files = data.get("files", [])

    if not files:
        await ctx.reply("Файлов пока нет. Загрузите документ через мини‑приложение VKMax.")
        return

    lines: list[str] = ["Последние файлы:"]
    for f in files:
        lines.append(
            f"- #{f.get('id')} — {f.get('filename')} ({f.get('format') or 'unknown'}, {f.get('size', 0)} байт)"
        )

    await ctx.reply("\n".join(lines))


@router.on_message("Мои файлы")
async def msg_my_files(message: aiomax.Message):
    """Обработчик кнопки «Мои файлы» из главного меню.

    Повторяет логику /files, но работает по тексту сообщения.
    """

    data = await vkmax_client.list_files(page=1, limit=5)
    files = data.get("files", [])

    if not files:
        await message.reply("Файлов пока нет. Загрузите документ через мини‑приложение VKMax.")
        return

    lines: list[str] = ["Последние файлы:"]
    for f in files:
        lines.append(
            f"- #{f.get('id')} — {f.get('filename')} ({f.get('format') or 'unknown'}, {f.get('size', 0)} байт)"
        )

    await message.reply("\n".join(lines))