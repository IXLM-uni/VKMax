# Руководство к файлу
# Назначение: загрузка/кэш robots.txt, проверка allow/deny для URL.
# Этап: базовая реализация. Обновляйте комментарий при изменениях.

from __future__ import annotations

from urllib.parse import urlparse
import urllib.robotparser as urp

from webparser.fetch.http_fetcher import HttpFetcher
from webparser.robots.cache import RobotsCache


class RobotsPolicy:
    """Проверка доступа по robots.txt с кэшем."""

    def __init__(self, user_agent: str, cache: RobotsCache) -> None:
        self._ua = user_agent
        self._cache = cache

    async def is_allowed(self, fetcher: HttpFetcher, url: str) -> bool:
        p = urlparse(url)
        host = p.hostname or ""
        parser = self._cache.get(host)
        if parser is None:
            robots_url = f"{p.scheme}://{host}/robots.txt"
            try:
                res = await fetcher.fetch(robots_url)
                parser = urp.RobotFileParser()
                if res.status == 200 and res.text:
                    parser.parse(res.text.splitlines())
                else:
                    # отсутствует robots — считаем allow by default
                    parser.parse([])
                self._cache.put(host, parser)
            except Exception:
                # в случае ошибки — позволяем, чтобы не блокировать обход
                return True
        return parser.can_fetch(self._ua, url)
