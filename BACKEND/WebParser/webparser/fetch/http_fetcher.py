# Руководство к файлу
# Назначение: быстрый HTTP-загрузчик на aiohttp.ClientSession (keep-alive, редиректы).
# Этап: базовая реализация на aiohttp. Обновляйте комментарий при изменениях.

from __future__ import annotations

from typing import Optional
import logging

import aiohttp

from webparser.core.types import FetchResult


class HttpFetcher:
    """Быстрый HTTP-загрузчик на базе aiohttp.ClientSession."""

    def __init__(self, user_agent: str, timeout_ms: int, max_redirects: int = 5) -> None:
        self._user_agent = user_agent
        self._timeout_sec = timeout_ms / 1000.0
        self._max_redirects = max_redirects
        self._session: Optional[aiohttp.ClientSession] = None
        self._log = logging.getLogger(__name__)

    async def start(self) -> None:
        if self._session is not None:
            return
        timeout = aiohttp.ClientTimeout(total=self._timeout_sec)
        headers = {
            "User-Agent": self._user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.8",
            "Cache-Control": "no-cache",
        }
        self._session = aiohttp.ClientSession(timeout=timeout, headers=headers, raise_for_status=False)

    async def stop(self) -> None:
        if self._session is not None:
            await self._session.close()
            self._session = None

    async def fetch(self, url: str) -> FetchResult:
        assert self._session is not None, "HttpFetcher.start() must be called first"
        try:
            async with self._session.get(
                url,
                allow_redirects=True,
                max_redirects=self._max_redirects,
                ssl=False,
            ) as resp:
                final_url = str(resp.url)
                status = resp.status
                ctype = resp.headers.get("Content-Type") or resp.headers.get("content-type")
                try:
                    text = await resp.text()
                except Exception:
                    text = None
                return FetchResult(url=url, final_url=final_url, status=status, content_type=ctype, text=text)
        except Exception as e:
            # При таймауте/сетевой ошибке логируем и возвращаем пустой результат со status=0,
            # чтобы оркестратор мог продолжить обход.
            self._log.warning("http-fetch-failed url=%s err=%r", url, e)
            return FetchResult(url=url, final_url=None, status=0, content_type=None, text=None)
