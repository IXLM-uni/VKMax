# Руководство к файлу
# Назначение: экспорт результатов (edges.csv, graph.json, опционально networkx).
# Этап: базовая реализация. Обновляйте комментарий при изменениях.

from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable, Tuple, Sequence

import orjson


class Exporter:
    """Экспорт рёбер и графа в файлы."""

    @staticmethod
    def write_edges_csv(path: str | Path, edges: Iterable[Tuple[str, str]]) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["src", "dst"])
            for s, d in edges:
                w.writerow([s, d])

    @staticmethod
    def write_graph_json(path: str | Path, nodes: Sequence[str], edges: Iterable[Tuple[str, str]]) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        payload = {"nodes": list(nodes), "edges": list(edges)}
        data = orjson.dumps(payload)
        p.write_bytes(data)
