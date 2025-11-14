# Руководство к файлу (DATABASE/CACHE_MANAGER/base_class.py)
# Назначение:
# - Базовый класс менеджера данных для VKMax на SQLAlchemy (async).
# - Общие утилиты: безопасная пагинация, простые CRUD-хелперы.
# Важно:
# - Redis не используется (MVP). Кэш добавим позднее.

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple, Type, TypeVar

from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute

from ..models import Base


TModel = TypeVar("TModel", bound=Base)


class BaseManager:
    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    def _clamp_page_limit(page: int | None, limit: int | None, max_limit: int = 100) -> Tuple[int, int]:
        p = 1 if not page or page < 1 else int(page)
        l = 20 if not limit or limit < 1 else int(limit)
        l = min(max_limit, l)
        return p, l

    async def get_by_id(self, model: Type[TModel], obj_id: Any) -> Optional[TModel]:
        q = select(model).where(getattr(model, "id") == obj_id).limit(1)
        res = await self.session.execute(q)
        return res.scalar_one_or_none()

    async def create(self, model: Type[TModel], data: Dict[str, Any]) -> TModel:
        # Для SQLite BigInteger PRIMARY KEY не даёт автоинкремента, поэтому
        # при отсутствии явного id вычисляем его вручную как max(id)+1.
        bind = getattr(self.session, "bind", None)
        dialect_name = getattr(getattr(bind, "dialect", None), "name", None)
        if "id" not in data and hasattr(model, "id") and dialect_name == "sqlite":
            max_id_res = await self.session.execute(select(func.max(getattr(model, "id"))))
            max_id = max_id_res.scalar() or 0
            data["id"] = int(max_id) + 1

        obj = model(**data)  # type: ignore[arg-type]
        self.session.add(obj)
        await self.session.flush()
        return obj

    async def update_by_id(self, model: Type[TModel], obj_id: Any, data: Dict[str, Any]) -> int:
        q = (
            update(model)
            .where(getattr(model, "id") == obj_id)
            .values(**data)
        )
        res = await self.session.execute(q)
        return int(res.rowcount or 0)

    async def delete_by_id(self, model: Type[TModel], obj_id: Any) -> int:
        q = delete(model).where(getattr(model, "id") == obj_id)
        res = await self.session.execute(q)
        return int(res.rowcount or 0)

    async def paginate(self, model: Type[TModel], where: List[Any] | None = None, order_by: InstrumentedAttribute | None = None, page: int = 1, limit: int = 20) -> Dict[str, Any]:
        page, limit = self._clamp_page_limit(page, limit)
        conds = where or []
        # total
        count_q = select(func.count()).select_from(model).where(*conds)
        total = (await self.session.execute(count_q)).scalar_one() or 0
        # items
        q = select(model).where(*conds)
        if order_by is not None:
            q = q.order_by(order_by)
        q = q.offset((page - 1) * limit).limit(limit)
        res = await self.session.execute(q)
        items = list(res.scalars().all())
        pages = (total + limit - 1) // limit if limit else 1
        return {"items": items, "total": int(total), "page": page, "pages": int(pages)}

