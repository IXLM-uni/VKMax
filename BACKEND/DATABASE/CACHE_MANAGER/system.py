 # Руководство к файлу (DATABASE/CACHE_MANAGER/system.py)
 # Назначение:
 # - Системный менеджер: агрегирует статистику по БД (users, files, operations)
 #   и отдельный счётчик website-конверсий.
 # - Совместим с SQLite и Postgres.

 from __future__ import annotations

 from typing import Dict

 from sqlalchemy import select, func
 from sqlalchemy.ext.asyncio import AsyncSession

 from .base_class import BaseManager
 from ..models import User, File, Operation, Format


 class SystemManager(BaseManager):
     def __init__(self, session: AsyncSession):
         super().__init__(session)

     async def stats(self) -> Dict[str, int]:
         # totals
         total_users = (await self.session.execute(select(func.count()).select_from(User))).scalar_one() or 0
         total_files = (await self.session.execute(select(func.count()).select_from(File))).scalar_one() or 0
         total_operations = (await self.session.execute(select(func.count()).select_from(Operation))).scalar_one() or 0

         # website conversions: операции без file_id и с old_format == website (.url)
         website_fmt = (await self.session.execute(
             select(Format.id).where(Format.file_extension.in_(["url", ".url"]))
         )).scalar_one_or_none()

         website_conversions = 0
         if website_fmt is not None:
             website_conversions = (
                 await self.session.execute(
                     select(func.count()).select_from(Operation).where(
                         Operation.file_id.is_(None),
                         Operation.old_format_id == int(website_fmt),
                     )
                 )
             ).scalar_one() or 0

         # Для MVP conversions_today = total_operations (упрощение)
         conversions_today = int(total_operations)

         return {
             "total_users": int(total_users),
             "total_files": int(total_files),
             "total_operations": int(total_operations),
             "conversions_today": int(conversions_today),
             "website_conversions": int(website_conversions),
         }

