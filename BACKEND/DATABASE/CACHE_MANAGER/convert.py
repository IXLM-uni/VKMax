 # Руководство к файлу (DATABASE/CACHE_MANAGER/convert.py)
 # Назначение:
 # - Менеджер операций конвертации: создание операций, обновление статуса,
 #   получение статуса и фильтрованный список. Поддержка batch.
 # Важно:
 # - В текущей схеме OPERATIONS нет поля url. Для website‑операций используем
 #   old_format_id, указывая формат "website" (см. seed форматов) и file_id=None.

 from __future__ import annotations

 from typing import Any, Dict, List, Optional
 from datetime import datetime, timezone

 from sqlalchemy import select
 from sqlalchemy.ext.asyncio import AsyncSession

 from .base_class import BaseManager
 from ..models import Operation, File, Format


 def _iso(dt: Optional[datetime]) -> str:
     if isinstance(dt, datetime):
         try:
             return dt.astimezone(timezone.utc).isoformat()
         except Exception:
             return dt.isoformat()
     return datetime.now(timezone.utc).isoformat()


 class ConvertManager(BaseManager):
     def __init__(self, session: AsyncSession):
         super().__init__(session)

     async def _get_format_id_by_ext(self, ext_key: str) -> Optional[int]:
         key = ext_key.lstrip('.')
         q = select(Format).where(Format.file_extension.in_([key, f'.{key}']))
         res = await self.session.execute(q)
         f = res.scalars().first()
         return int(getattr(f, 'id')) if f is not None else None

     async def create_file_operation(self, *, user_id: Optional[int], source_file_id: int, target_format_id: Optional[int]) -> Operation:
         # Определяем старый формат по файлу
         src = await self.get_by_id(File, source_file_id)
         old_fmt = int(getattr(src, 'format_id')) if src and getattr(src, 'format_id') is not None else None
         op = await self.create(
             Operation,
             {
                 'user_id': user_id,
                 'file_id': source_file_id,
                 'result_file_id': None,
                 'old_format_id': old_fmt,
                 'new_format_id': target_format_id,
                 'status': 'queued',
             },
         )
         return op

     async def create_website_operation(self, *, user_id: Optional[int], target_format_id: Optional[int]) -> Operation:
         # Помечаем website через old_format_id = id("website")
         website_fmt_id = await self._get_format_id_by_ext('url')
         op = await self.create(
             Operation,
             {
                 'user_id': user_id,
                 'file_id': None,
                 'result_file_id': None,
                 'old_format_id': website_fmt_id,
                 'new_format_id': target_format_id,
                 'status': 'queued',
             },
         )
         return op

     async def update_status(self, operation_id: int, *, status: str, error_message: Optional[str] = None, result_file_id: Optional[int] = None) -> bool:
         data: Dict[str, Any] = {'status': status}
         if error_message is not None:
             data['error_message'] = error_message
         if result_file_id is not None:
             data['result_file_id'] = result_file_id
         affected = await self.update_by_id(Operation, operation_id, data)
         return affected > 0

     async def get_operation(self, operation_id: int) -> Optional[Dict[str, Any]]:
         op = await self.get_by_id(Operation, operation_id)
         if op is None:
             return None
         return {
             'operation_id': int(getattr(op, 'id')),
             'user_id': int(getattr(op, 'user_id')) if getattr(op, 'user_id') is not None else None,
             'file_id': int(getattr(op, 'file_id')) if getattr(op, 'file_id') is not None else None,
             'result_file_id': int(getattr(op, 'result_file_id')) if getattr(op, 'result_file_id') is not None else None,
             'old_format_id': int(getattr(op, 'old_format_id')) if getattr(op, 'old_format_id') is not None else None,
             'new_format_id': int(getattr(op, 'new_format_id')) if getattr(op, 'new_format_id') is not None else None,
             'datetime': _iso(getattr(op, 'datetime')),
             'status': getattr(op, 'status'),
             'error_message': getattr(op, 'error_message'),
         }

     async def list_operations(self, *, user_id: Optional[int] = None, status: Optional[str] = None, type_hint: Optional[str] = None) -> List[Dict[str, Any]]:
         # type_hint: 'file' | 'website' (эвристика по old_format_id == website)
         q = select(Operation)
         if user_id is not None:
             q = q.where(Operation.user_id == user_id)
         if status is not None:
             q = q.where(Operation.status == status)
         res = await self.session.execute(q.order_by(Operation.datetime.desc()))
         rows = res.scalars().all()
         result: List[Dict[str, Any]] = []
         for op in rows:
             row = {
                 'operation_id': int(getattr(op, 'id')),
                 'file_id': int(getattr(op, 'file_id')) if getattr(op, 'file_id') is not None else None,
                 'status': getattr(op, 'status'),
                 'datetime': _iso(getattr(op, 'datetime')),
                 'type': 'file',
             }
             # определяем website по old_format, если это формат .url (см. seed)
             try:
                 if getattr(op, 'file_id') is None and getattr(op, 'old_format_id') is not None:
                     # Загрузить формат и проверить расширение
                     f = await self.get_by_id(Format, int(getattr(op, 'old_format_id')))
                     ext = (getattr(f, 'file_extension') or '').lstrip('.') if f else ''
                     if ext == 'url':
                         row['type'] = 'website'
             except Exception:
                 pass
             if type_hint and row['type'] != type_hint:
                 continue
             result.append(row)
         return result

     async def batch_create(self, *, user_id: Optional[int], items: List[Dict[str, Any]]) -> List[int]:
         """Создаёт пакет операций. item: {'source_file_id'|None,'target_format_id'|'target_ext','type':'file'|'website'}"""
         ids: List[int] = []
         for it in items:
             target_format_id = it.get('target_format_id')
             if target_format_id is None and it.get('target_ext'):
                 target_format_id = await self._get_format_id_by_ext(str(it['target_ext']))
             if it.get('type') == 'website':
                 op = await self.create_website_operation(user_id=user_id, target_format_id=target_format_id)
             else:
                 src_id = int(it.get('source_file_id'))
                 op = await self.create_file_operation(user_id=user_id, source_file_id=src_id, target_format_id=target_format_id)
             ids.append(int(getattr(op, 'id')))
         return ids

