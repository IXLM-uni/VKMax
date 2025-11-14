# Руководство к файлу
# Назначение: очередь фронтира (BFS/DFS) на asyncio.Queue, хранение глубины.
# Этап: базовая реализация. Обновляйте комментарий при изменениях.

import asyncio
from typing import Optional

from webparser.core.types import UrlTask


class Frontier:
    """Очередь URL-задач (BFS по умолчанию)."""

    def __init__(self) -> None:
        self._q: asyncio.Queue[UrlTask] = asyncio.Queue()

    def size(self) -> int:
        return self._q.qsize()

    def empty(self) -> bool:
        return self._q.empty()

    async def enqueue(self, task: UrlTask) -> None:
        await self._q.put(task)

    async def dequeue(self) -> UrlTask:
        return await self._q.get()

    def task_done(self) -> None:
        self._q.task_done()
