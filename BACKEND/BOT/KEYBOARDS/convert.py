"""Руководство к файлу (BACKEND/BOT/KEYBOARDS/convert.py)
Назначение:
- Содержит inline‑клавиатуры, связанные с конвертацией файлов.
- Используется в роутере BOT.ROUTERS.convert.
"""

from __future__ import annotations

from typing import Iterable

from aiomax import buttons


def formats_keyboard(formats: Iterable[str] | None = None) -> buttons.KeyboardBuilder:
    """Клавиатура выбора целевого формата конвертации.

    Параметры:
    - formats: коллекция названий форматов ("pdf", "docx", "graph" и т.п.).
      Если None, используются несколько форматов по умолчанию.
    """

    if formats is None:
        formats = ["pdf", "docx", "graph"]

    kb = buttons.KeyboardBuilder()

    for fmt in formats:
        kb.add(
            buttons.CallbackButton(
                text=fmt.upper(),
                payload=f"convert:{fmt}",
            )
        )

    return kb