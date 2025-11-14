# Руководство к файлу
# Назначение: кэш robots.txt по хосту, TTL, хранение парсера.
# Этап: базовая реализация. Обновляйте комментарий при изменениях.

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class RobotsEntry:
    parser: object
    expires_at: float


class RobotsCache:
    def __init__(self, ttl_sec: int) -> None:
        self._store: Dict[str, RobotsEntry] = {}
        self._ttl = ttl_sec

    def get(self, host: str) -> Optional[object]:
        e = self._store.get(host)
        if not e:
            return None
        if e.expires_at < time.time():
            self._store.pop(host, None)
            return None
        return e.parser

    def put(self, host: str, parser: object) -> None:
        self._store[host] = RobotsEntry(parser=parser, expires_at=time.time() + self._ttl)
