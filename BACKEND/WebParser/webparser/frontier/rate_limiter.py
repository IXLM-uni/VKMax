# Руководство к файлу
# Назначение: глобальные и пер-хостовые лимиты (Semaphore + aiolimiter).
# Этап: базовая реализация. Обновляйте комментарий при изменениях.

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncIterator, Dict

from aiolimiter import AsyncLimiter

from webparser.utils.url import get_host


class RateLimiter:
    """Глобальная семафора и per-host limiter."""

    def __init__(self, concurrency: int, per_host_rps: float) -> None:
        self._sem = asyncio.Semaphore(concurrency)
        self._host_limiters: Dict[str, AsyncLimiter] = {}
        self._per_host_rps = max(0.1, per_host_rps)

    def _get_host_limiter(self, host: str) -> AsyncLimiter:
        if host not in self._host_limiters:
            # rps -> 1 request per (1/rps) seconds
            self._host_limiters[host] = AsyncLimiter(max_rate=self._per_host_rps, time_period=1)
        return self._host_limiters[host]

    @asynccontextmanager
    async def slot(self, url: str) -> AsyncIterator[None]:
        host = get_host(url)
        limiter = self._get_host_limiter(host)
        await self._sem.acquire()
        async with limiter:
            try:
                yield None
            finally:
                self._sem.release()
