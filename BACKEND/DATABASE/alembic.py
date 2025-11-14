 # Руководство к файлу (DATABASE/alembic.py)
 # Назначение:
 # - Минимальная инициализация БД VKMax: создание таблиц по моделям и начальная загрузка форматов.
 # - В dev режиме заменяет полноценный Alembic до внедрения миграций.
 # Использование:
 # - python -m VKMax.BACKEND.DATABASE.alembic  (создаст таблицы и загрузит базовые форматы)

 from __future__ import annotations

 import asyncio
 from typing import Sequence

 from sqlalchemy import select

 from .session import engine, async_session_factory
 from .models import Base, Format


 async def create_tables() -> None:
     async with engine.begin() as conn:
         # Важно: run_sync для create_all в async режиме
         await conn.run_sync(Base.metadata.create_all)


 async def seed_formats() -> None:
    async with async_session_factory() as session:
        exists = (await session.execute(select(Format.id).limit(1))).first()
        if exists:
            return
        items: Sequence[Format] = [
            Format(type="document", prompt=None, file_extension=".pdf", is_input=True, is_output=False),   # pdf
            Format(type="document", prompt=None, file_extension=".docx", is_input=True, is_output=False),  # docx
            Format(type="website",  prompt=None, file_extension=".url", is_input=True, is_output=False),   # website marker
            Format(type="document", prompt=None, file_extension=".html", is_input=True, is_output=True),   # html
            Format(type="graph",    prompt=None, file_extension=".json", is_input=False, is_output=True),  # graph
        ]
        session.add_all(items)
        await session.commit()


async def main() -> None:
    await create_tables()
    await seed_formats()


 if __name__ == "__main__":
     asyncio.run(main())

