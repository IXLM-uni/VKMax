"""Руководство к файлу (BACKEND/BOT/ROUTERS/convert.py)
Назначение:
- Роутер бота VKMax для сценариев конвертации файлов и сайтов.
- Зеркалит HTTP‑роуты FAST_API/ROUTES/convert.py, но в виде команд и кнопок.
"""

from __future__ import annotations

import aiomax

from ..KEYBOARDS import formats_keyboard
from ..SERVICES.vkmax_api import client as vkmax_client


router = aiomax.Router()


@router.on_command("convert")
async def cmd_convert(ctx: aiomax.CommandContext):
    """Начало сценария конвертации: подгружаем форматы из VKMax API."""

    fmts = await vkmax_client.list_formats()
    # Берём только форматы, которые помечены как output
    choices = [
        (f.get("extension") or "").lstrip(".")
        for f in fmts
        if f.get("is_output")
    ] or ["pdf", "docx", "graph"]

    text = (
        "Выбери целевой формат конвертации.\n\n"
        "Можешь также использовать команду /convert_file <file_id> <format>."
    )
    kb = formats_keyboard(choices)
    await ctx.reply(text, keyboard=kb)


@router.on_command("convert_file")
async def cmd_convert_file(ctx: aiomax.CommandContext):
    """Создать операцию конвертации через /convert FastAPI.

    Синтаксис: /convert_file <file_id> <format>
    """

    if len(ctx.args) < 2:
        await ctx.reply("Использование: /convert_file <file_id> <format>")
        return

    file_id, target_format = ctx.args[0], ctx.args[1]
    payload_user_id = str(ctx.sender.user_id)

    try:
        data = await vkmax_client.create_convert_operation(
            source_file_id=file_id,
            url=None,
            target_format=target_format,
            user_id=payload_user_id,
        )
    except Exception as exc:  # noqa: WPS430
        await ctx.reply(f"Не удалось создать операцию конвертации: {exc}")
        return

    op_id = data.get("operation_id") or "?"
    status = data.get("status") or "queued"
    await ctx.reply(f"Операция конвертации создана. ID={op_id}, статус={status}.")


@router.on_command("docx_to_pdf")
async def cmd_docx_to_pdf(ctx: aiomax.CommandContext):
    """Упростённая команда конвертации DOCX → PDF через /convert.

    Синтаксис: /docx_to_pdf <file_id>
    """

    if not ctx.args:
        await ctx.reply("Использование: /docx_to_pdf <file_id>")
        return

    file_id = ctx.args[0]
    payload_user_id = str(ctx.sender.user_id)

    try:
        data = await vkmax_client.create_convert_operation(
            source_file_id=file_id,
            url=None,
            target_format="pdf",
            user_id=payload_user_id,
        )
    except Exception as exc:  # noqa: WPS430
        await ctx.reply(f"Не удалось создать операцию DOCX → PDF: {exc}")
        return

    op_id = data.get("operation_id") or "?"
    status = data.get("status") or "queued"
    await ctx.reply(f"Операция DOCX → PDF создана. ID={op_id}, статус={status}.")


@router.on_command("site_to_pdf")
async def cmd_site_to_pdf(ctx: aiomax.CommandContext):
    """Команда конвертации сайта в PDF через /convert (website flow).

    Синтаксис: /site_to_pdf <url>
    """

    if not ctx.args:
        await ctx.reply("Использование: /site_to_pdf <url>")
        return

    url = ctx.args[0]
    payload_user_id = str(ctx.sender.user_id)

    try:
        data = await vkmax_client.create_convert_operation(
            source_file_id=None,
            url=url,
            target_format="pdf",
            user_id=payload_user_id,
        )
    except Exception as exc:  # noqa: WPS430
        await ctx.reply(f"Не удалось создать операцию сайт → PDF: {exc}")
        return

    op_id = data.get("operation_id") or "?"
    status = data.get("status") or "queued"
    await ctx.reply(f"Операция сайт → PDF создана. ID={op_id}, статус={status}.")


@router.on_message("DOCX → PDF")
async def msg_docx_to_pdf(message: aiomax.Message):
    """Обработчик кнопки «DOCX → PDF» из главного меню.

    Показывает, как запустить конвертацию по ID файла.
    """

    text = (
        "Конвертация DOCX → PDF.\n\n"
        "1. Найди ID файла в списке /files (или кнопке «Мои файлы»).\n"
        "2. Введи команду: /docx_to_pdf <file_id>\n"
        "   пример: /docx_to_pdf 123\n"
    )
    await message.reply(text)


@router.on_message("Сайт → PDF")
async def msg_site_to_pdf(message: aiomax.Message):
    """Обработчик кнопки «Сайт → PDF» из главного меню.

    Показывает, как запустить конвертацию сайта в PDF.
    """

    text = (
        "Конвертация сайта → PDF.\n\n"
        "Отправь команду: /site_to_pdf <url>\n"
        "пример: /site_to_pdf https://example.com\n"
    )
    await message.reply(text)