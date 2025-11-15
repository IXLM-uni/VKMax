# Руководство к файлу (FAST_API/fast_api.py)
# Назначение:
# - Точка входа приложения FastAPI для VKMax.
# - Подключение всех роутеров и базовая инфраструктура (CORS, логирование, ошибки).
# Важно:
# - Конфиг и in-memory store берутся из FAST_API/config.py.
# - Централизованное логирование настраивается через CONVERT/logging_config.setup_logging().
# - Ручка /health реализована в ROUTES/system.py, здесь не дублируется.

from __future__ import annotations

import json
import logging
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from dotenv import load_dotenv

from .config import settings
from BACKEND.CONVERT.logging_config import setup_logging

# Загружаем переменные окружения из BACKEND/.env до инициализации сервисов
_BASE_DIR = Path(__file__).resolve().parent.parent
_DOTENV_PATH = _BASE_DIR / ".env"
if _DOTENV_PATH.exists():  # безопасно для продакшена: в Docker можно не класть .env
    load_dotenv(dotenv_path=_DOTENV_PATH)

# Инициализируем централизованное логирование до создания FastAPI-приложения
setup_logging()

logger = logging.getLogger("vkmax.fastapi")
logger.setLevel(logging.DEBUG)

app = FastAPI(title=settings.app_name, version=settings.version)

# CORS
allow_origins = [o.strip() for o in (settings.cors_origins or "").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.debug(f"Request: {request.method} {request.url}")
    ctype = request.headers.get("content-type", "")
    if ctype.startswith("application/json"):
        try:
            body = await request.json()
            logger.debug(f"Request body: {json.dumps(body, ensure_ascii=False)[:1000]}")
        except Exception:
            pass
    elif "multipart/form-data" in ctype or "application/octet-stream" in ctype:
        logger.debug("Request body: <multipart/binary skipped>")

    response = await call_next(request)
    return response

# Exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    logger.error(f"Validation error: {exc.errors()} for request: {request.url}")
    return JSONResponse(status_code=422, content={"detail": exc.errors()})

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc):
    logger.error(f"HTTP error: {exc.detail} for request: {request.url}, status: {exc.status_code}")
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

# Routers
from .ROUTES import user as user_router  # noqa: E402
from .ROUTES import system as system_router  # noqa: E402
from .ROUTES import format as format_router  # noqa: E402
from .ROUTES import files as files_router  # noqa: E402
from .ROUTES import download as download_router  # noqa: E402
from .ROUTES import convert as convert_router  # noqa: E402
from .ROUTES import auth as auth_router  # noqa: E402
from .ROUTES import graph as graph_router  # noqa: E402

app.include_router(user_router.router)
app.include_router(system_router.router)
app.include_router(format_router.router)
app.include_router(files_router.router)
app.include_router(download_router.router)
app.include_router(convert_router.router)
app.include_router(auth_router.router)
app.include_router(graph_router.router)

@app.get("/")
async def root():
    return {"message": settings.app_name, "version": settings.version, "docs": "/docs"}
