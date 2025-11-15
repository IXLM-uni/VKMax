"""Руководство к файлу (BACKEND/SEVICES/max_auth_service.py)
Назначение:
- Валидация WebAppData от MAX (мини‑приложения) по алгоритму из документации.
- Получение/создание пользователя VKMax (DATABASE.User) по данным MAX через UserManager.
- Не зависит от FastAPI, работает только с AsyncSession и менеджерами БД.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from dataclasses import dataclass
from typing import Any, Dict, Tuple
from urllib.parse import parse_qsl

from sqlalchemy.ext.asyncio import AsyncSession

from BACKEND.DATABASE.CACHE_MANAGER.user import UserManager


class InvalidInitDataError(Exception):
    """Исключение для некорректных или подделанных WebAppData."""


@dataclass
class MaxAuthResult:
    """Результат валидации WebAppData и маппинга пользователя.

    Поля:
    - user_id: внутренний ID пользователя VKMax (users.id).
    - max_user: словарь с данными пользователя MAX из WebAppData.
    """

    user_id: int
    max_user: Dict[str, Any]


def _get_bot_token() -> str:
    """Считать токен бота из окружения.

    Используются переменные:
    - VKMAX_BOT_TOKEN
    - MAX_BOT_TOKEN (fallback)
    """

    token = os.getenv("VKMAX_BOT_TOKEN") or os.getenv("MAX_BOT_TOKEN") or ""
    if not token:
        raise RuntimeError("Токен бота MAX не задан (ожидается VKMAX_BOT_TOKEN или MAX_BOT_TOKEN)")
    return token


def _parse_init_data(init_data: str) -> Tuple[Dict[str, str], str]:
    """Разобрать строку initData на словарь параметров и hash.

    Возвращает (params_without_hash, hash_hex).
    """

    params: Dict[str, str] = {}
    received_hash: str | None = None

    # parse_qsl сам делает URL‑декодирование
    for key, value in parse_qsl(init_data, keep_blank_values=True):
        if key == "hash":
            received_hash = value
        else:
            params[key] = value

    if received_hash is None:
        raise InvalidInitDataError("В initData отсутствует параметр hash")

    return params, received_hash


def _compute_hash(params: Dict[str, str], bot_token: str) -> str:
    """Вычислить ожидаемый hash по алгоритму из документации MAX.

    1. Сортируем пары key=value (без hash) по ключу.
    2. Формируем data_check_string через '\n'.
    3. Строим secret_key = HMAC_SHA256("WebAppData", BotToken).
    4. Строим конечный hash = HMAC_SHA256(secret_key, data_check_string).
    """

    items = [f"{k}={v}" for k, v in sorted(params.items())]
    data_check_string = "\n".join(items)

    secret_key = hmac.new(
        key="WebAppData".encode("utf-8"),
        msg=bot_token.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()

    return hmac.new(
        key=secret_key,
        msg=data_check_string.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()


async def validate_and_get_user(init_data: str, session: AsyncSession) -> MaxAuthResult:
    """Провалидировать WebAppData и вернуть/создать пользователя VKMax.

    При неуспехе бросает InvalidInitDataError.
    """

    params, received_hash = _parse_init_data(init_data)
    bot_token = _get_bot_token()
    expected_hash = _compute_hash(params, bot_token)

    # Защищённое сравнение строк
    if not hmac.compare_digest(received_hash, expected_hash):
        raise InvalidInitDataError("Подпись initData не прошла проверку")

    user_raw = params.get("user")
    if not user_raw:
        raise InvalidInitDataError("В initData отсутствует параметр user")

    try:
        max_user: Dict[str, Any] = json.loads(user_raw)
    except json.JSONDecodeError as exc:  # noqa: WPS430
        raise InvalidInitDataError("Параметр user не является корректным JSON") from exc

    max_id = str(max_user.get("id") or "").strip()
    if not max_id:
        raise InvalidInitDataError("В user нет поля id")

    # Собираем человекочитаемое имя
    name_parts = []
    first_name = max_user.get("first_name")
    last_name = max_user.get("last_name")
    username = max_user.get("username")
    if first_name:
        name_parts.append(str(first_name))
    if last_name:
        name_parts.append(str(last_name))
    if not name_parts and username:
        name_parts.append(str(username))
    name = " ".join(name_parts) or f"MAX user {max_id}"

    mgr = UserManager(session)
    existing = await mgr.get_user_by_max_id(max_id)
    if existing is None:
        user_obj = await mgr.create_user(max_id=max_id, name=name, metadata={"max_user": max_user})
    else:
        user_obj = existing

    return MaxAuthResult(user_id=int(getattr(user_obj, "id")), max_user=max_user)


async def _get_or_create_shared_user(session: AsyncSession) -> MaxAuthResult:
    """Вернуть или создать общего (shared) пользователя VKMax.

    Используется как fallback, если WebAppData отсутствует или не проходит
    криптографическую проверку. Все неавторизованные пользователи будут
    работать под этим единым учётным записем.
    """

    shared_max_id = "shared"
    mgr = UserManager(session)
    existing = await mgr.get_user_by_max_id(shared_max_id)
    if existing is None:
        meta: Dict[str, Any] = {"kind": "shared"}
        user_obj = await mgr.create_user(max_id=shared_max_id, name="Shared VKMax User", metadata=meta)
    else:
        user_obj = existing

    max_user = {
        "id": shared_max_id,
        "first_name": "Shared",
        "last_name": "User",
        "username": None,
        "is_shared": True,
    }

    return MaxAuthResult(user_id=int(getattr(user_obj, "id")), max_user=max_user)


async def auth_with_fallback(init_data: str | None, session: AsyncSession) -> MaxAuthResult:
    """Авторизация с fallback на общего пользователя.

    Поведение:
    - если init_data пустая или None — сразу возвращаем shared‑пользователя;
    - если init_data есть, пробуем validate_and_get_user;
    - при InvalidInitDataError (не MAX или подделано) используем shared‑пользователя.
    """

    if not init_data:
        return await _get_or_create_shared_user(session)

    try:
        return await validate_and_get_user(init_data, session)
    except InvalidInitDataError:
        return await _get_or_create_shared_user(session)
