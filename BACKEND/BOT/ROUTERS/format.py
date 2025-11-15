"""Руководство к файлу (BACKEND/BOT/ROUTERS/format.py)
Назначение:
- Роутер бота VKMax для работы со справочником форматов.
- Зеркалит HTTP‑роуты FAST_API/ROUTES/format.py в чат‑команды.
"""

from __future__ import annotations

import aiomax

from ..SERVICES.vkmax_api import client as vkmax_client


router = aiomax.Router()


@router.on_command("formats")
async def cmd_formats(ctx: aiomax.CommandContext):
    """Выводит реальный список форматов и матрицу конвертаций из VKMax API."""

    fmts = await vkmax_client.list_formats()
    matrix = await vkmax_client.list_supported_conversions()

    lines: list[str] = ["Поддерживаемые форматы:"]
    for f in fmts:
        ext = f.get("extension") or ""
        lines.append(
            f"- {ext} (type={f.get('type')}, input={bool(f.get('is_input'))}, output={bool(f.get('is_output'))})"
        )

    lines.append("\nМатрица конвертаций:")
    for key, value in matrix.items():
        lines.append(f"- {key} → {', '.join(value)}")

    await ctx.reply("\n".join(lines))


@router.on_message("Форматы")
async def msg_formats(message: aiomax.Message):
    """Обработчик кнопки «Форматы» из главного меню.

    Повторяет логику /formats, но работает по тексту сообщения.
    """

    fmts = await vkmax_client.list_formats()
    matrix = await vkmax_client.list_supported_conversions()

    lines: list[str] = ["Поддерживаемые форматы:"]
    for f in fmts:
        ext = f.get("extension") or ""
        lines.append(
            f"- {ext} (type={f.get('type')}, input={bool(f.get('is_input'))}, output={bool(f.get('is_output'))})"
        )

    lines.append("\nМатрица конвертаций:")
    for key, value in matrix.items():
        lines.append(f"- {key} → {', '.join(value)}")

    await message.reply("\n".join(lines))