 # Руководство к файлу (DATABASE/session.py)
 # Назначение:
 # - Асинхронная настройка SQLAlchemy: движок, фабрика сессий, зависимость get_db_session.
 # - По умолчанию SQLite (aiosqlite), далее возможен переход на Postgres без изменения интерфейса.
 # Важно:
 # - URL БД берётся из переменной окружения DB_URL, иначе используется локальный sqlite.

from __future__ import annotations

import os
from typing import AsyncGenerator
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

DEFAULT_SQLITE_PATH = Path(__file__).resolve().parent / "vkmax.sqlite3"
DEFAULT_DB_URL = f"sqlite+aiosqlite:///{DEFAULT_SQLITE_PATH}"

DB_URL = os.getenv("DB_URL", DEFAULT_DB_URL)

engine = create_async_engine(DB_URL, echo=False, future=True)

async_session_factory = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency function that yields an async DB session.
    Коммит/роллбек управляется здесь для простоты использования в FastAPI.
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

