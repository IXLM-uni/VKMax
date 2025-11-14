# Руководство к файлу
# Назначение: хранение графа ссылок в памяти (dict[src] -> set[dst]).
# Этап: базовая реализация. Обновляйте комментарий при изменениях.

from __future__ import annotations

from typing import Dict, Set, List


class GraphStore:
    """Памятное хранилище графа (ориентированные рёбра)."""

    def __init__(self) -> None:
        self._edges: Dict[str, Set[str]] = {}

    def add_edge(self, src: str, dst: str) -> None:
        if src not in self._edges:
            self._edges[src] = set()
        self._edges[src].add(dst)

    def nodes(self) -> Set[str]:
        s: Set[str] = set(self._edges.keys())
        for v in self._edges.values():
            s.update(v)
        return s

    def edges(self) -> List[tuple[str, str]]:
        out: List[tuple[str, str]] = []
        for src, dsts in self._edges.items():
            for dst in dsts:
                out.append((src, dst))
        return out

    def edges_count(self) -> int:
        return sum(len(v) for v in self._edges.values())
