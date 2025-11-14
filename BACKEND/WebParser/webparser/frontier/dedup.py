# Руководство к файлу
# Назначение: дедупликация посещённых URL (set/BloomFilter).
# Этап: базовая реализация на set, опционально BloomFilter. Обновляйте комментарий при изменениях.

from __future__ import annotations

from typing import Optional


class Deduplicator:
    """Дедупликатор URL по нормализованной строке."""

    def __init__(self, use_bloom: bool = False, capacity: int = 1_000_000, error_rate: float = 0.001) -> None:
        self._visited = set()
        self._bloom = None
        if use_bloom:
            try:
                from bloom_filter2 import BloomFilter  # type: ignore

                self._bloom = BloomFilter(max_elements=capacity, error_rate=error_rate)
            except Exception:
                self._bloom = None

    def seen(self, url: str) -> bool:
        if self._bloom is not None:
            return url in self._bloom
        return url in self._visited

    def add(self, url: str) -> None:
        if self._bloom is not None:
            self._bloom.add(url)
        self._visited.add(url)

    def size(self) -> int:
        return len(self._visited)
