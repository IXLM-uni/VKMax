# Руководство к файлу (TESTS/conftest.py)
# Назначение:
# - Общие фикстуры для pytest-тестов backend VKMax.
# - Создаёт event loop и HTTP-клиент для FastAPI-приложения.

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover - dotenv опционален
    load_dotenv = None  # type: ignore[assignment]


# Загружаем BACKEND/.env, чтобы в тестах были доступны VKMAX_* переменные
if load_dotenv is not None:
    project_root = Path(__file__).resolve().parent.parent
    env_path = project_root / ".env"
    if env_path.exists():
        load_dotenv(env_path)  # type: ignore[arg-type]

from BACKEND.FAST_API.fast_api import app
from BACKEND.DATABASE.alembic import create_tables, seed_formats


@pytest.fixture(scope="session")
def event_loop():
    """Создаёт общий event loop для асинхронных тестов."""

    loop = asyncio.new_event_loop()
    try:
        yield loop
    finally:
        loop.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def init_db():
    """Инициализирует тестовую БД: создаёт таблицы и базовые форматы."""

    await create_tables()
    await seed_formats()


@pytest_asyncio.fixture
async def http_client():
    """HTTP-клиент для тестирования FastAPI-приложения без реального сервера."""

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
