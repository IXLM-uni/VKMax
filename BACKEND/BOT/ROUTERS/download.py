"""Руководство к файлу (BACKEND/BOT/ROUTERS/download.py)
Назначение:
- Роутер бота VKMax для сценариев скачивания/получения результата конвертации.
- Логически связан с FAST_API/ROUTES/download.py.
"""

from __future__ import annotations

import aiomax


router = aiomax.Router()


@router.on_command("download")
async def cmd_download(ctx: aiomax.CommandContext):
    """Заглушка для сценария скачивания результатов конвертации."""

    text = (
        "Здесь позже будет скачивание результата по id операции или файла.\n\n"
        "Пока что воспользуйся мини‑аппой VKMax для скачивания."
    )
    await ctx.reply(text)