# Руководство к файлу
# Назначение: простая визуализация графа (graph.json) через networkx + matplotlib.
# Этап: базовая реализация. Обновляйте комментарий при изменениях.

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable, Tuple

import orjson
import networkx as nx
import matplotlib.pyplot as plt


def load_graph_json(path: Path) -> Tuple[list[str], list[Tuple[str, str]]]:
    data = orjson.loads(path.read_bytes())
    nodes = data.get("nodes", [])
    edges = data.get("edges", [])
    # приведение к кортежам
    edges_t: list[Tuple[str, str]] = []
    for e in edges:
        if isinstance(e, (list, tuple)) and len(e) == 2:
            edges_t.append((e[0], e[1]))
    return nodes, edges_t


def build_nx_graph(nodes: Iterable[str], edges: Iterable[Tuple[str, str]]) -> nx.DiGraph:
    g = nx.DiGraph()
    g.add_nodes_from(nodes)
    g.add_edges_from(edges)
    return g


def draw_graph(g: nx.DiGraph, out: Path, layout: str = "spring", max_nodes: int | None = 1000, figsize: tuple[int, int] = (12, 8)) -> None:
    # если граф слишком большой — взять подграф по top-degree
    if max_nodes is not None and g.number_of_nodes() > max_nodes:
        degrees = sorted(g.degree, key=lambda kv: kv[1], reverse=True)
        top_nodes = {n for n, _ in degrees[:max_nodes]}
        g = g.subgraph(top_nodes).copy()

    plt.figure(figsize=figsize)

    if layout == "kamada":
        pos = nx.kamada_kawai_layout(g)
    elif layout == "circular":
        pos = nx.circular_layout(g)
    else:
        pos = nx.spring_layout(g, k=None, seed=42)

    nx.draw_networkx_nodes(g, pos, node_size=50, node_color="#1f77b4", alpha=0.8)
    nx.draw_networkx_edges(g, pos, arrows=False, width=0.5, alpha=0.4)

    # Подписывать только топ-узлы по степени, чтобы не захламлять
    try:
        degrees = sorted(g.degree, key=lambda kv: kv[1], reverse=True)
        labels = {n: n for n, _ in degrees[:50]}
        nx.draw_networkx_labels(g, pos, labels=labels, font_size=6)
    except Exception:
        pass

    plt.axis("off")
    out.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(out, dpi=200)
    plt.close()


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Визуализация графа ссылок из graph.json")
    p.add_argument("--graph-json", type=Path, required=True)
    p.add_argument("--out", type=Path, default=Path("graph.png"))
    p.add_argument("--layout", type=str, default="spring", choices=["spring", "kamada", "circular"])
    p.add_argument("--max-nodes", type=int, default=1000)
    return p.parse_args()


def main() -> None:
    ns = parse_args()
    nodes, edges = load_graph_json(ns.graph_json)
    g = build_nx_graph(nodes, edges)
    draw_graph(g, ns.out, layout=ns.layout, max_nodes=ns.max_nodes)


if __name__ == "__main__":
    main()
