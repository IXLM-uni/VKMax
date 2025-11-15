"""Руководство к файлу (BACKEND/BOT/KEYBOARDS/common.py)
Назначение:
- Содержит общие inline‑клавиатуры для чат‑бота VKMax (главное меню, запуск мини‑аппы).
- Используется в роутерах BOT.ROUTERS.*.
"""

from __future__ import annotations

from aiomax import buttons


def main_menu_keyboard() -> buttons.KeyboardBuilder:
    """Клавиатура главного меню бота.

    Кнопки по умолчанию:
    - «Мои файлы» — переход к списку файлов VKMax.
    - «Мои операции» — переход к истории конвертаций.
    - «Форматы» — просмотр поддерживаемых форматов.
    """

    kb = buttons.KeyboardBuilder()
    kb.add(
        buttons.MessageButton("Мои файлы"),
        buttons.MessageButton("Мои операции"),
    )
    kb.row(
        buttons.MessageButton("Форматы"),
    )
    kb.row(
        buttons.MessageButton("DOCX → PDF"),
        buttons.MessageButton("Сайт → PDF"),
    )
    return kb


def open_app_keyboard(bot: str | int) -> buttons.KeyboardBuilder:
    """Клавиатура с кнопкой открытия мини‑приложения VKMax.

    Параметры:
    - bot: ID или username бота, у которого подключено мини‑приложение.
      Обычно это текущий бот; значение задаётся в роутере.
    """

    kb = buttons.KeyboardBuilder()
    kb.add(
        buttons.WebAppButton(
            text="Открыть мини‑приложение VKMax",
            bot=bot,
        )
    )
    return kb