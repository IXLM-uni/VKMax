"""Руководство к файлу (BACKEND/BOT/SERVICES/mapping.py)
Назначение:
- Содержит функции маппинга пользователей MAX на сущности VKMax (БД, User).
- В этой заготовке реализованы только интерфейсы (без обращения к БД).
"""

from __future__ import annotations

from typing import Optional


def get_internal_user_id(max_user_id: int) -> Optional[int]:  # pragma: no cover - заглушка
    """Вернуть внутренний ID пользователя VKMax по MAX user_id.

    В реальной реализации здесь будет запрос в БД через DATABASE/UserManager.
    Сейчас функция оставлена как заглушка, чтобы не тянуть зависимости на БД.
    """

    return None