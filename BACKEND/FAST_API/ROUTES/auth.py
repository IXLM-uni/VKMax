# Руководство к файлу (ROUTES/auth.py)
# Назначение:
# - Эндпоинт авторизации мини‑приложения MAX через WebAppData.
# - Делегирует всю бизнес‑логику в сервис BACKEND.SEVICES.max_auth_service.

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..schemas import MaxWebAppAuthRequest, MaxWebAppAuthResponse
from BACKEND.DATABASE.session import get_db_session
from BACKEND.SEVICES import max_auth_service


router = APIRouter(tags=["auth"])


@router.post("/auth/max/webapp", response_model=MaxWebAppAuthResponse)
async def auth_max_webapp(
    payload: MaxWebAppAuthRequest,
    session: AsyncSession = Depends(get_db_session),
):
    """Авторизация мини‑приложения MAX по WebAppData.

    1. Валидирует подпись init_data в сервисе max_auth_service.
    2. Получает/создаёт пользователя VKMax в БД.
    3. Возвращает внутренний user_id и данные пользователя MAX.
    """

    # Авторизация полностью делегирована сервису max_auth_service.
    # Если init_data валидна и принадлежит MAX, сервис вернёт конкретного
    # пользователя. Если нет — вернёт общего shared‑пользователя.
    result = await max_auth_service.auth_with_fallback(payload.init_data, session)

    return MaxWebAppAuthResponse(user_id=str(result.user_id), max_user=result.max_user)
