# Руководство к файлу
# Назначение: быстрый загрузчик на Playwright APIRequestContext (HTTP/2, keep-alive).
# Этап: базовая реализация. Обновляйте комментарий при изменениях.

from __future__ import annotations

from typing import Optional, Dict
import logging

from playwright.async_api import async_playwright, APIRequestContext, Playwright

from webparser.core.types import FetchResult


class HttpFetcher:
    """Быстрый загрузчик на APIRequestContext."""

    def __init__(self, user_agent: str, timeout_ms: int, max_redirects: int = 5) -> None:
        self._user_agent = user_agent
        self._timeout_ms = timeout_ms
        self._max_redirects = max_redirects
        self._pw: Optional[Playwright] = None
        self._ctx: Optional[APIRequestContext] = None
        self._log = logging.getLogger(__name__)

    async def start(self) -> None:
        if self._ctx is not None:
            return
        self._pw = await async_playwright().start()
        self._ctx = await self._pw.request.new_context(
            extra_http_headers={
                "User-Agent": self._user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.8",
                "Cache-Control": "no-cache",
            },
            timeout=self._timeout_ms,
            max_redirects=self._max_redirects,
            ignore_https_errors=True,  # позволяем ходить на сайты с кривыми сертификатами
        )

    async def stop(self) -> None:
        if self._ctx is not None:
            await self._ctx.dispose()
            self._ctx = None
        if self._pw is not None:
            await self._pw.stop()
            self._pw = None

    async def fetch(self, url: str) -> FetchResult:
        assert self._ctx is not None, "HttpFetcher.start() must be called first"
        try:
            resp = await self._ctx.get(url)
        except Exception as e:
            # При таймауте/сетевой ошибке логируем и возвращаем пустой результат со status=0,
            # чтобы оркестратор мог продолжить обход.
            self._log.warning("http-fetch-failed url=%s err=%r", url, e)
            return FetchResult(url=url, final_url=None, status=0, content_type=None, text=None)

        # финальный URL после редиректов не отдается напрямую, используем response.url
        final_url = resp.url
        status = resp.status
        ctype = resp.headers.get("content-type")
        text: Optional[str] = None
        # не читаем тело всегда, это делает оркестратор через MIME-фильтр
        # но здесь можно вернуть текст по запросу
        try:
            text = await resp.text()
        except Exception:
            text = None
        return FetchResult(url=url, final_url=final_url, status=status, content_type=ctype, text=text)
