ПРИМЕРЫ РЕАЛИЗАЦИИ



# Руководство к файлу (Nea/fast_api/fast_api.py)
# Назначение:
# - Точка входа FastAPI для среды Nea (локальная/прод).
# - Явно используем ОТНОСИТЕЛЬНЫЕ импорты из .routes, чтобы загружались модули из пакета Nea.
# Важно:
# - Конфиг и .env читаются из Nea/.env через Nea/fast_api/config.py (единый .env).
# - Для локального запуска: uvicorn Nea.fast_api.fast_api:app --reload
# - Дублируем /health по пути /api/health для совместимости с прокси (reverse SSH/Nginx),
#   когда внешний роутинг ожидает, что все ручки висят под /api/*.

import json
from fastapi import FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles
import os
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging

logger = logging.getLogger("uvicorn.error")
logger.setLevel(logging.DEBUG)

app = FastAPI(title="Nea Telegram Mini App API (Test)")

from .routes import users as users_router
from .routes import projects as projects_router
from .routes import likes as likes_router
from .routes import chats as chats_router
from .routes import chat_groups as chat_groups_router
from .routes import meetings
from .routes import notifications as notifications_router
from .routes import teams as teams_router
from .routes import knowledge as knowledge_router
from .routes import friends as friends_router
from .routes import checklists as checklists_router
from .routes import test_auth as test_router
from .routes import auth as auth_router
from .routes import billing as billing_router
from .routes import telegram as telegram_router
from .routes import debug as debug_router
from .routes import internal_asr as internal_asr_router
from .routes import project_tasks as project_tasks_router

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://nea-subdomen.ru.tuna.am",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files (uploads) — mount AFTER app is created
STATIC_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "uploads"))
try:
    os.makedirs(STATIC_ROOT, exist_ok=True)
except Exception:
    pass
app.mount("/static", StaticFiles(directory=STATIC_ROOT), name="static")

# Additional static mount for images stored under Nea/images
IMAGES_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "images"))
try:
    os.makedirs(IMAGES_ROOT, exist_ok=True)
except Exception:
    pass
app.mount("/images", StaticFiles(directory=IMAGES_ROOT), name="images")

@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.debug(f"Request: {request.method} {request.url}")
    ctype = request.headers.get("content-type", "")
    if ctype.startswith("application/json"):
        try:
            body = await request.json()
            logger.debug(f"Request body: {json.dumps(body, indent=2)}")
        except json.JSONDecodeError:
            # Not valid JSON, skip logging body
            pass
        except Exception as e:
            # Do not spam errors for non-JSON or malformed payloads
            logger.debug(f"Skip body log, cannot parse JSON: {e}")
    else:
        # Skip logging raw body for multipart/form-data or binary uploads to avoid decode errors
        if "multipart/form-data" in ctype or "application/octet-stream" in ctype:
            logger.debug("Request body: <multipart or binary; skipped>")

    response = await call_next(request)

    # Clone response body for logging
    response_body = b""
    async for chunk in response.body_iterator:
        response_body += chunk

    logger.debug(f"Response status: {response.status_code}")
    # Log response body only if it's likely text/JSON
    rctype = response.headers.get("content-type", "")
    if rctype.startswith("application/json") or rctype.startswith("text/"):
        try:
            logger.debug(f"Response body: {response_body.decode(errors='replace')}")
        except Exception:
            logger.debug("Response body: <non-text content; skipped>")
    else:
        logger.debug("Response body: <non-text content; skipped>")

    # Rebuild the response with the consumed body
    return Response(
        content=response_body,
        status_code=response.status_code,
        headers=dict(response.headers),
        media_type=response.media_type,
    )

# Include routers
app.include_router(users_router.router)
app.include_router(projects_router.router)
app.include_router(chats_router.router)
app.include_router(chat_groups_router.router)
app.include_router(likes_router.router)
app.include_router(meetings.router)
app.include_router(notifications_router.router)
app.include_router(teams_router.router)
app.include_router(test_router.router)
app.include_router(knowledge_router.router)
app.include_router(friends_router.router)
app.include_router(checklists_router.router)
app.include_router(auth_router.router)
app.include_router(billing_router.router)
app.include_router(telegram_router.router)
app.include_router(debug_router.router)
app.include_router(internal_asr_router.router)
app.include_router(project_tasks_router.router)

# Health

@app.get("/health")
async def health():
    return {"status": "ok"}

# Совместимость с прокси: /api/health → тот же ответ, что и /health
@app.get("/api/health")
async def health_api():
    return {"status": "ok"}

# Exception handlers

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    logger.error(f"Validation error: {exc.errors()} for request: {request.url}")
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()},
    )

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc):
    logger.error(f"HTTP error: {exc.detail} for request: {request.url}, status: {exc.status_code}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )

# Root – ссылка на документацию

@app.get("/")
async def root():
    """Короткая справка с линками на docs/redoc"""
    return {
        "message": "Nea API is running",
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/health",
    }


SCHEMAS.PY

"""
Руководство к файлу (schemas.py)

Назначение:
- Централизованные Pydantic-схемы запросов/ответов для FastAPI.
- Используются роутами в каталоге fast_api/routes/* и кэш-слоем.

Изменения в этой ревизии:
- Добавлена схема LikeRoleRequest для эндпоинта лайка проекта с выбором роли.
 - ProjectBrief расширен полями для мультикомандного формата сохранения команды:
   teams_count (1-4), team_size (1-4) и team_roles_by_team (список списков ролей по командам).
 - Добавлена схема SocialLinks и поля social_links в UserResponse и UserUpdateRequest
  для поддержки соцсетей (telegram, vk, linkedin) в профиле пользователя.
- Новое: для Базы знаний добавлено поле starred_by_me в KnowledgeResourceResponse —
  индикатор, поставил ли текущий пользователь звезду ресурсу.
 - Добавлено поле about_me в UserResponse/UserUpdateRequest (краткий блок "О себе").
 - Добавлено поле career_path (JSON) в UserResponse/UserUpdateRequest для инлайнового редактирования образования и опыта.
 - Добавлена поддержка слоя команд: во все релевантные схемы добавлено поле teamId (camelCase) с алиасом team_id для маппинга SQLAlchemy.
 - Добавлены поля для серии встреч проекта при создании: frequency_week (частота в неделю) и slots_weekly
   (список слотов { weekday: 0..6, time: "HH:MM" }).
 - Расширён ProjectBrief (онбординг ментора): duration_weeks, frequency_week (alias frequencyWeek),
   slots_weekly (alias slotsWeekly) для корректного создания проектов через submit-projects.

Правила разработки:
- Все публичные схемы должны иметь понятные алиасы под фронтенд (snake/camel при необходимости).
- Новые схемы группируйте по доменам (Projects, Likes, Chats и т.д.).
"""

from typing import List, Optional, Union, Literal
import uuid
from pydantic import BaseModel, field_validator, Field, ConfigDict, model_validator
from datetime import date, datetime

class UserResponse(BaseModel):
    id: int | str
    telegram_id: Optional[int] = None
    username: Optional[str] = None
    name: Optional[str] = None
    avatar: Optional[str] = None
    role: str
    skills: List[str] | None = Field(default_factory=list)
    description: Optional[str] = Field(None, alias="description_text")
    about_me: Optional[str] = None
    career_path: Optional[dict] = None
    cv: Optional[str] = None
    has_description: Optional[bool] = None
    total_tokens_used: Optional[int] = None
    onboarding_completed: Optional[bool] = Field(None, alias="onboardingCompleted")
    # Onboarding form fields
    university_name: Optional[str] = None
    graduation_year: Optional[int] = None
    experience_years: Optional[int] = None
    desired_roles: Optional[List[str]] = None
    yandex_form_completed: Optional[bool] = None
    # Social links block
    social_links: Optional["SocialLinks"] = None

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


RUN_APP.PY

# run_app.py
import asyncio
from Nea.fast_api.fast_api import app
import uvicorn

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8001, log_level="debug")


CONFIG.PY

# Nea/fast_api/config.py
 # Руководство к файлу (config.py)
 #
 # Назначение:
 # - Централизованная загрузка настроек FastAPI через Pydantic Settings.
 # - Единый источник переменных окружения — только файл Nea/.env.
 #
 # Изменения в этой ревизии:
 # - Полностью удалено использование Nea/fast_api/.env и корневого ../.env.
 # - Параметр model_config.env_file указывает только на Nea/.env.
 # - Переменные окружения процесса не переопределяются значениями из .env (override=False).
 # - Добавлены информативные DEBUG-prinты о наличии Nea/.env и ключевых переменных.
 #
 # Правила эксплуатации:
 # - Храните все конфигурационные значения в файле Nea/.env.
 # - Если ранее существовал Nea/fast_api/.env — удалите его, чтобы избежать путаницы.
 # - Для локальной отладки проверьте значения TELEGRAM_BOT_TOKEN, TELEGRAM_BOT_USERNAME и др.
 #
import os


import logging
from pathlib import Path
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, AliasChoices


# Абсолютные пути
CONFIG_FILE_DIR = Path(__file__).resolve().parent               # Nea/fast_api
NEA_DIR = CONFIG_FILE_DIR.parent                                 # Nea/

# Единственный .env-источник
NEA_ENV_FILE_PATH = NEA_DIR / ".env"                            # Nea/.env

# Явно подгружаем .env-файл без перезаписи уже существующих переменных окружения
try:
    if NEA_ENV_FILE_PATH.exists():
        load_dotenv(NEA_ENV_FILE_PATH, override=False)
except Exception as _e:
    logging.warning(
        f"Не удалось загрузить .env: {NEA_ENV_FILE_PATH}: {_e}"
    )


ЛЮБОЙ_РОУТЕР.PY

# Nea/fast_api/routes/billing.py
from __future__ import annotations
import time
import json
from typing import Literal

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from Nea.database.session import get_db_session
from Nea.database.cache_manager import CacheManager
from Nea.database.redis_client import redis_client
from Nea.database import models
from Nea.fast_api.dependencies.auth import get_current_user
from Nea.config import settings as core_settings

router = APIRouter(prefix="/api/billing", tags=["billing"])


CREDIT_PACKS = {
    10: 1000,   # credits -> RUB
    20: 2000,
    50: 5000,
    100: 10000,
}


class CreateInvoiceRequest(BaseModel):
    credits: Literal[10, 20, 50, 100]


@router.get("/me")
async def get_my_billing(current_user = Depends(get_current_user), db = Depends(get_db_session)):
    """Возвращает баланс в кредитах и список доступных пакетов."""
    cache = CacheManager(db, redis_client)

    # Ensure wallet exists
    wallet = await cache.crud.get_one_or_none(
        model=models.Wallet,
        where_conditions=[models.Wallet.user_id == current_user.id],
    )
    if wallet is None:
        wallet = await cache.crud.create(models.Wallet, {"user_id": int(current_user.id), "balance_credits": 0})

    packs = [
        {"credits": c, "priceRub": r, "label": f"{c} кредитов", "amountKopeks": r * 100}
        for c, r in CREDIT_PACKS.items()
    ]
    pricing_help = (
        "Каждая неделя работы с ментором = 10 кредитов. "
        "Проект на 2 недели = 20 кредитов."
    )
    return {
        "balance": int(getattr(wallet, "balance_credits", 0) or 0),
        "packs": packs,
        "pricingHelp": pricing_help,
    }


@router.post("/create-invoice")
async def create_invoice(payload: CreateInvoiceRequest, current_user = Depends(get_current_user), db = Depends(get_db_session)):
    """Создаёт инвойс через Telegram createInvoiceLink и возвращает ссылку.

    Фронтенд в Telegram WebApp вызывает tg.openInvoice(link).
    """
    credits = int(payload.credits)
    if credits not in CREDIT_PACKS:
        raise HTTPException(400, "Неверный пакет кредитов")

    price_rub = CREDIT_PACKS[credits]
    amount_kopeks = price_rub * 100

    bot_token = core_settings.bot_token
    provider_token = core_settings.u_kassa_token
    if not bot_token:
        raise HTTPException(500, "BOT_TOKEN не задан")
    if not provider_token:
        raise HTTPException(500, "U_KASSA_TOKEN не задан")

    # Безопасный payload — используем JSON с нашими полями
    invoice_payload = {
        "type": "credits_topup",
        "uid": int(current_user.id),
        "credits": credits,
        "ts": int(time.time()),
    }

    api_url = f"https://api.telegram.org/bot{bot_token}/createInvoiceLink"
    body = {
        "title": f"Покупка {credits} кредитов",
        "description": f"Пополнение баланса на {credits} кредитов",
        "payload": json.dumps(invoice_payload, ensure_ascii=False),
        "provider_token": provider_token,
        "currency": "RUB",
        "prices": [
            {"label": "К оплате", "amount": amount_kopeks}
        ],
        # Необязательные поля:
        # "photo_url": "",
        # "start_parameter": "topup",
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.post(api_url, json=body)
        try:
            data = r.json()
        except Exception:
            raise HTTPException(502, f"Telegram API error: {r.text[:200]}")

        if not data.get("ok"):
            raise HTTPException(502, f"Telegram API error: {data}")
        link = data.get("result")
        if not isinstance(link, str):
            raise HTTPException(502, f"Bad response from Telegram: {data}")

    # Создадим транзакцию в pending (для истории)
    cache = CacheManager(db, redis_client)
    await cache.crud.create(
        model=models.BillingTransaction,
        data={
            "user_id": int(current_user.id),
            "type": "credit",
            "credits": credits,
            "amount_rub": price_rub,
            "currency": "RUB",
            "status": "pending",
            "payload": json.dumps(invoice_payload, ensure_ascii=False),
        },
    )

    return {"link": link}


# Nea/fast_api/routes/auth.py
# Руководство к файлу (routes/auth.py)
#
# Назначение:
# - Эндпоинты аутентификации для Web и Telegram Mini App.
# - TMA (Telegram Mini App) вход через заголовок Authorization: tma <base64url(initData)>.
# - Cookie-based сессии (HttpOnly) для фронта.
#
# Важно:
# - Используются модули из пакета Nea (НЕ Nea_test).
# - Настройки читаются из единственного файла Nea/.env через Nea/fast_api/config.py.
# - JWT создаются в ..dependencies.jwt_utils, куки настраиваются из ..config.settings.
#
from __future__ import annotations
import base64
import hashlib
import hmac
import json
import time
from typing import Dict, Any, Tuple
import urllib.parse

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, EmailStr

from ..config import settings
from Nea.database.session import get_db_session
from Nea.database.cache_manager import CacheManager
from Nea.database.redis_client import redis_client
from Nea.database import models
from ..dependencies.jwt_utils import create_jwt, decode_jwt
from ..dependencies.passwords import hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _parse_init_data(raw: str) -> Tuple[Dict[str, str], str]:
    """Парсит initData в словарь строк и возвращает (данные_без_hash, hash)."""
    parts = raw.split("&") if raw else []
    data_map: Dict[str, str] = {}
    hash_value = ""
    for p in parts:
        if not p:
            continue
        if "=" not in p:
            # пропускаем странные сегменты
            continue
        k, v = p.split("=", 1)
        # значения идут url-encoded, но Telegram сравнивает именно сырой data_check_string
        # поэтому здесь храним как есть (дефолт)
        if k == "hash":
            hash_value = v
        else:
            data_map[k] = v
    return data_map, hash_value


def _build_data_check_string(data_map: Dict[str, str]) -> str:
    # Ключи по алфавиту, формат "key=value" построчно
    items = [f"{k}={data_map[k]}" for k in sorted(data_map.keys())]
    return "\n".join(items)


def _hex_hmac_sha256(key: bytes, msg: bytes) -> str:
    return hmac.new(key, msg, hashlib.sha256).hexdigest()


def _verify_tma_signature(raw_init_data: str, provided_hash: str) -> bool:
    """Проверяем подпись initData. Поддерживаем 2 стратегии:
    1) Login Widget: secret_key = SHA256(bot_token), signature = HMAC_SHA256(data_check_string, secret_key)
    2) WebApp: secret_key = HMAC_SHA256("WebAppData", bot_token), signature = HMAC_SHA256(data_check_string, secret_key)
    """
    token = settings.TELEGRAM_BOT_TOKEN or ""
    if not token:
        return False
    data_map, _ = _parse_init_data(raw_init_data)
    # Встречаются реализации, где data_check_string строят из URL‑декодированных значений.
    # Чтобы быть совместимыми, проверяем ОБА варианта.
    dcs_raw = _build_data_check_string(data_map).encode()
    # Сборка decoded-версии (значения URL‑декодированы)
    try:
        decoded_map = {k: urllib.parse.unquote(v) for k, v in data_map.items()}
        dcs_dec = _build_data_check_string(decoded_map).encode()
    except Exception:
        dcs_dec = None

    # Ветка 1: Login Widget
    secret1 = hashlib.sha256(token.encode()).digest()
    sig1_raw = _hex_hmac_sha256(secret1, dcs_raw)
    sig1_dec = _hex_hmac_sha256(secret1, dcs_dec) if dcs_dec is not None else ""

    # Ветка 2: WebApp
    secret2 = hmac.new("WebAppData".encode(), token.encode(), hashlib.sha256).digest()
    sig2_raw = _hex_hmac_sha256(secret2, dcs_raw)
    sig2_dec = _hex_hmac_sha256(secret2, dcs_dec) if dcs_dec is not None else ""
    return (
        hmac.compare_digest(sig1_raw, provided_hash)
        or hmac.compare_digest(sig2_raw, provided_hash)
        or (sig1_dec and hmac.compare_digest(sig1_dec, provided_hash))
        or (sig2_dec and hmac.compare_digest(sig2_dec, provided_hash))
    )


def _set_access_cookie(response: Response, token: str, max_age_sec: int) -> None:
    cookie_parts = [
        f"{settings.SESSION_COOKIE_NAME}={token}",
        "HttpOnly",
        f"Path={settings.SESSION_COOKIE_PATH}",
        f"SameSite={settings.SESSION_COOKIE_SAMESITE.capitalize()}",
    ]
    if settings.SESSION_COOKIE_SECURE:
        cookie_parts.append("Secure")
    cookie_parts.append(f"Max-Age={max_age_sec}")
    response.headers.append("Set-Cookie", "; ".join(cookie_parts))


# --------------------------- Web: email/password ---------------------------

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: str | None = None
    username: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


@router.post("/register")
async def register(payload: RegisterRequest, response: Response, db = Depends(get_db_session)):
    """Регистрация веб‑пользователя по email/password (prod)."""
    cache = CacheManager(db, redis_client)
    # Проверка уникальности email
    existing = await cache.crud.get_one_or_none(
        model=models.User,
        where_conditions=[models.User.email == payload.email],
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="Email already registered")

    pwd_hash = hash_password(payload.password)
    created = await cache.crud.create(
        model=models.User,
        data={
            "email": payload.email,
            "password_hash": pwd_hash,
            "name": payload.name,
            "username": payload.username,
            "role": "mentee",
        },
    )

    user_id = int(getattr(created, "id"))
    token_version = int(getattr(created, "token_version", 0) or 0)

    now_ts = int(time.time())
    access_exp = now_ts + settings.JWT_EXPIRES_MIN * 60
    refresh_exp = now_ts + settings.JWT_REFRESH_EXPIRES_MIN * 60

    access = create_jwt({
        "sub": user_id,
        "ver": token_version,
        "iat": now_ts,
        "exp": access_exp,
    })
    refresh = create_jwt({
        "sub": user_id,
        "ver": token_version,
        "iat": now_ts,
        "exp": refresh_exp,
    })

    _set_access_cookie(response, access, settings.JWT_EXPIRES_MIN * 60)
    _set_refresh_cookie(response, refresh, settings.JWT_REFRESH_EXPIRES_MIN * 60)
    return {"ok": True, "user_id": user_id}


@router.post("/login")
async def login(payload: LoginRequest, response: Response, db = Depends(get_db_session)):
    """Логин веб‑пользователя: проверка email/password, выдача access+refresh."""
    cache = CacheManager(db, redis_client)
    user = await cache.crud.get_one_or_none(
        model=models.User,
        where_conditions=[models.User.email == payload.email],
    )
    if user is None or not user.password_hash or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Обновляем отметку входа (тип datetime)
    try:
        import datetime as _dt
        await cache.crud.update(
            model=models.User,
            where_conditions=[models.User.id == user.id],
            data={"last_login_at": _dt.datetime.utcnow()},
        )
    except Exception:
        pass

    user_id = int(getattr(user, "id"))
    token_version = int(getattr(user, "token_version", 0) or 0)

    now_ts = int(time.time())
    access_exp = now_ts + settings.JWT_EXPIRES_MIN * 60
    refresh_exp = now_ts + settings.JWT_REFRESH_EXPIRES_MIN * 60

    access = create_jwt({
        "sub": user_id,
        "ver": token_version,
        "iat": now_ts,
        "exp": access_exp,
    })
    refresh = create_jwt({
        "sub": user_id,
        "ver": token_version,
        "iat": now_ts,
        "exp": refresh_exp,
    })

    _set_access_cookie(response, access, settings.JWT_EXPIRES_MIN * 60)
    _set_refresh_cookie(response, refresh, settings.JWT_REFRESH_EXPIRES_MIN * 60)
    return {"ok": True, "user_id": user_id}


def _set_refresh_cookie(response: Response, token: str, max_age_sec: int) -> None:
    cookie_parts = [
        f"{settings.REFRESH_COOKIE_NAME}={token}",
        "HttpOnly",
        f"Path={settings.REFRESH_COOKIE_PATH}",
        f"SameSite={settings.REFRESH_COOKIE_SAMESITE.capitalize()}",
    ]
    if settings.REFRESH_COOKIE_SECURE:
        cookie_parts.append("Secure")
    cookie_parts.append(f"Max-Age={max_age_sec}")
    response.headers.append("Set-Cookie", "; ".join(cookie_parts))


def _clear_access_cookie(response: Response) -> None:
    cookie_parts = [
        f"{settings.SESSION_COOKIE_NAME}=", "HttpOnly",
        f"Path={settings.SESSION_COOKIE_PATH}",
        f"SameSite={settings.SESSION_COOKIE_SAMESITE.capitalize()}",
        "Max-Age=0",
    ]
    if settings.SESSION_COOKIE_SECURE:
        cookie_parts.append("Secure")
    response.headers.append("Set-Cookie", "; ".join(cookie_parts))


def _clear_refresh_cookie(response: Response) -> None:
    cookie_parts = [
        f"{settings.REFRESH_COOKIE_NAME}=", "HttpOnly",
        f"Path={settings.REFRESH_COOKIE_PATH}",
        f"SameSite={settings.REFRESH_COOKIE_SAMESITE.capitalize()}",
        "Max-Age=0",
    ]
    if settings.REFRESH_COOKIE_SECURE:
        cookie_parts.append("Secure")
    response.headers.append("Set-Cookie", "; ".join(cookie_parts))


@router.post("/telegram")
async def auth_telegram(request: Request, response: Response, db = Depends(get_db_session)):
    """Принимает Telegram initData через Authorization: tma <base64url(initData)>
    Валидирует подпись и свежесть, делает upsert пользователя и выдаёт JWT в HttpOnly cookie.
    """
    auth = request.headers.get("authorization") or request.headers.get("Authorization") or ""
    if not auth.startswith("tma "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing TMA authorization header")

    payload = auth[4:].strip()
    # Поддерживаем оба формата: base64url(initData) и raw initData (query string)
    # Сначала пытаемся декодировать как base64url; если не получилось — считаем, что это raw
    try:
        raw_init_data = base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)).decode()
    except Exception:
        raw_init_data = payload

    data_map, provided_hash = _parse_init_data(raw_init_data)
    if not provided_hash:
        raise HTTPException(status_code=401, detail="No hash in initData")

    if not _verify_tma_signature(raw_init_data, provided_hash):
        raise HTTPException(status_code=401, detail="Invalid initData signature")

    # Проверка свежести
    try:
        auth_date = int(data_map.get("auth_date", "0"))
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid auth_date")
    now = int(time.time())
    if auth_date <= 0 or now - auth_date > settings.AUTH_INITDATA_MAX_AGE:
        raise HTTPException(status_code=401, detail="initData is too old")

    # Извлекаем user
    raw_user = data_map.get("user")
    if not raw_user:
        raise HTTPException(status_code=401, detail="No user in initData")
    try:
        # user приходит как URL-encoded JSON — корректно декодируем и парсим
        decoded = urllib.parse.unquote(raw_user)
        user_obj = json.loads(decoded)
    except Exception:
        raise HTTPException(status_code=400, detail="Bad user payload")

    # Нормализуем поля
    tg_id = int(user_obj.get("id"))
    username = user_obj.get("username")
    first_name = user_obj.get("first_name") or ""
    last_name = user_obj.get("last_name") or ""
    name = (first_name + " " + last_name).strip() or username or f"tg_{tg_id}"
    language = user_obj.get("language_code")
    photo_url = user_obj.get("photo_url")

    cache = CacheManager(db, redis_client)

    # Ищем пользователя по telegram_id
    existing = await cache.crud.get_one_or_none(
        model=models.User,
        where_conditions=[models.User.telegram_id == tg_id],
    )

    if existing is None:
        # Создаём с минимальным набором
        created = await cache.crud.create(
            model=models.User,
            data={
                "telegram_id": tg_id,
                "username": username,
                "name": name,
                "avatar": photo_url,
                # Дефолтная роль: mentee (можно скорректировать бизнес-логикой)
                "role": "mentee",
            },
        )
        user_id = getattr(created, "id")
        token_version = getattr(created, "token_version", 0) or 0
    else:
        # Обновляем актуальные поля (без агрессивного перетирания)
        await cache.crud.update(
            model=models.User,
            where_conditions=[models.User.id == existing.id],
            data={
                "username": username if username is not None else existing.username,
                "name": name if name else existing.name,
                "avatar": photo_url if photo_url else existing.avatar,
            },
        )
        user_id = getattr(existing, "id")
        token_version = getattr(existing, "token_version", 0) or 0

    # Выпускаем JWT
    now_ts = int(time.time())
    access_exp = now_ts + settings.JWT_EXPIRES_MIN * 60
    access = create_jwt({
        "sub": int(user_id),
        "ver": int(token_version),
        "tid": tg_id,
        "iat": now_ts,
        "exp": access_exp,
    })
    # Telegram Mini App поток — только access cookie (без refresh)
    _set_access_cookie(response, access, settings.JWT_EXPIRES_MIN * 60)
    return {"ok": True, "user_id": user_id}


@router.post("/refresh")
async def refresh_token(request: Request, response: Response, db = Depends(get_db_session)):
    """Обновляет access по refresh (stateless, через users.token_version)."""
    refresh = request.cookies.get(settings.REFRESH_COOKIE_NAME)
    if not refresh:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No refresh token")

    try:
        data = decode_jwt(refresh)
    except HTTPException as e:
        # Прокидываем 401/440 наверх
        raise e

    try:
        user_id = int(data.get("sub"))
        ver = int(data.get("ver", 0))
    except Exception:
        raise HTTPException(status_code=401, detail="Bad refresh token payload")

    cache = CacheManager(db, redis_client)
    user = await cache.crud.get_one_or_none(
        model=models.User,
        where_conditions=[models.User.id == user_id],
    )
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    current_ver = int(getattr(user, "token_version", 0) or 0)
    if ver != current_ver:
        raise HTTPException(status_code=401, detail="Refresh invalidated")

    # Выдать новый access (и по желанию — новый refresh)
    now_ts = int(time.time())
    access_exp = now_ts + settings.JWT_EXPIRES_MIN * 60
    access = create_jwt({
        "sub": int(user_id),
        "ver": current_ver,
        "iat": now_ts,
        "exp": access_exp,
    })
    _set_access_cookie(response, access, settings.JWT_EXPIRES_MIN * 60)

    # Ротация refresh по желанию (оставим без ротации для простоты)
    return {"ok": True}


@router.post("/logout")
async def logout(request: Request, response: Response, db = Depends(get_db_session)):
    """Выход: инкремент token_version (инвалидирует все refresh), очистка cookies.
    Access мгновенно не отзовём (кроме опционального blacklist), но он короткий.
    """
    # Попробуем прочитать текущего пользователя из refresh (если есть), чтобы инкрементировать версию
    refresh = request.cookies.get(settings.REFRESH_COOKIE_NAME)
    if refresh:
        try:
            data = decode_jwt(refresh)
            user_id = int(data.get("sub"))
        except Exception:
            user_id = None
        if user_id:
            cache = CacheManager(db, redis_client)
            try:
                await cache.crud.update(
                    model=models.User,
                    where_conditions=[models.User.id == user_id],
                    data={"token_version": models.User.token_version + 1},
                )
            except Exception:
                # Не блокируем logout на ошибках обновления версии
                pass

    _clear_access_cookie(response)
    _clear_refresh_cookie(response)
    return {"ok": True}
