# Руководство к файлу
# Назначение: построение дерева по доменам/поддоменам из edges.csv (ASCII дерево).
# Этап: базовая реализация. Обновляйте комментарий при изменениях.

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import tldextract


@dataclass
class Node:
    name: str
    count: int = 0
    children: Dict[str, "Node"] = field(default_factory=dict)
    urls: List[str] = field(default_factory=list)

    def add_child(self, child: "Node") -> None:
        self.children[child.name] = child


def domain_from_url(url: str) -> Tuple[str, List[str]]:
    ext = tldextract.extract(url)
    apex = ext.top_domain_under_public_suffix or ext.registered_domain or ext.fqdn  # e.g., eduson.academy
    subs = ext.subdomain.split(".") if ext.subdomain else []  # e.g., ["a","b"] for a.b
    return apex, subs


def fqdn_from_parts(apex: str, subs: List[str]) -> str:
    if not subs:
        return apex
    return f"{'.'.join(subs)}.{apex}"


def load_unique_urls(edges_csv: Path) -> List[str]:
    urls: set[str] = set()
    with edges_csv.open("r", encoding="utf-8") as f:
        r = csv.reader(f)
        header = next(r, None)
        for row in r:
            if not row:
                continue
            if len(row) >= 1 and row[0]:
                urls.add(row[0].strip())
            if len(row) >= 2 and row[1]:
                urls.add(row[1].strip())
    return list(urls)

def fqdn_and_segments(url: str) -> Tuple[str, str, List[str]]:
    ext = tldextract.extract(url)
    apex = ext.top_domain_under_public_suffix or ext.registered_domain or ext.fqdn
    fqdn = apex if not ext.subdomain else f"{ext.subdomain}.{apex}"
    rest = url.split("//", 1)[-1]
    path = rest.split("/", 1)[1] if "/" in rest else ""
    segs = [s for s in path.split("/") if s]
    return apex, fqdn, segs


def build_toc(urls: Iterable[str], levels: int) -> Dict[str, Node]:
    roots: Dict[str, Node] = {}
    for u in urls:
        apex, fqdn, segs = fqdn_and_segments(u)
        root = roots.setdefault(apex, Node(name=apex))
        # узел fqdn под apex (создаём только если есть поддомен или хотим явный уровень)
        fqnode = root.children.setdefault(fqdn, Node(name=fqdn)) if fqdn != apex else root
        current = fqnode
        # группировка по сегментам пути до levels
        for i in range(min(levels, len(segs))):
            group_name = "/" + "/".join(segs[: i + 1])
            current = current.children.setdefault(group_name, Node(name=group_name))
        # листовой список URL
        current.urls.append(u)

    # агрегируем counts снизу вверх
    def aggregate(n: Node) -> int:
        total = len(n.urls)
        for ch in n.children.values():
            total += aggregate(ch)
        n.count = total
        return total

    for apex, n in roots.items():
        aggregate(n)
    return roots


def render_tree(root: Node, indent: str = "", is_last: bool = True, *, include_urls: bool, max_urls: int) -> List[str]:
    connector = "└─ " if is_last else "├─ "
    lines = [f"{indent}{connector}{root.name} ({root.count})"]
    child_items = list(sorted(root.children.values(), key=lambda n: n.name))
    for idx, ch in enumerate(child_items):
        last = idx == len(child_items) - 1
        next_indent = indent + ("   " if is_last else "│  ")
        lines.extend(render_tree(ch, next_indent, last, include_urls=include_urls, max_urls=max_urls))
    if include_urls and root.urls:
        # ограничим количество URL в группе
        shown = root.urls[:max_urls] if max_urls > 0 else root.urls
        for i, u in enumerate(shown):
            last = i == len(shown) - 1 and not child_items
            url_connector = "└─ " if last else "├─ "
            url_indent = indent + ("   " if is_last else "│  ")
            lines.append(f"{url_indent}{url_connector}{u}")
    return lines


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Дерево по доменам/поддоменам из edges.csv")
    p.add_argument("--edges-csv", type=Path, required=True)
    p.add_argument("--out", type=Path, default=Path("domain_tree.txt"))
    p.add_argument("--min-count", type=int, default=1, help="Скрыть узлы с суммарным счётчиком < min-count")
    p.add_argument("--levels", type=int, default=2, help="Глубина группировки по сегментам пути")
    p.add_argument("--max-urls-per-group", type=int, default=10, help="Максимум ссылок, отображаемых в группе")
    p.add_argument("--include-urls", action=argparse.BooleanOptionalAction, default=True, help="Показывать URL-листья")
    return p.parse_args()


def prune_by_count(n: Node, min_count: int) -> bool:
    # Возвращает True, если узел следует сохранить
    # Сначала фильтруем детей
    for k in list(n.children.keys()):
        if not prune_by_count(n.children[k], min_count):
            del n.children[k]
    return n.count >= min_count or bool(n.children)


def main() -> None:
    ns = parse_args()
    urls = load_unique_urls(ns.edges_csv)
    roots = build_toc(urls, levels=ns.levels)

    lines: List[str] = []
    for apex in sorted(roots.keys()):
        root = roots[apex]
        prune_by_count(root, ns.min_count)
        # корневую строку без стартового отступа
        lines.append(f"{root.name} ({root.count})")
        for idx, ch in enumerate(sorted(root.children.values(), key=lambda n: n.name)):
            lines.extend(render_tree(ch, "", idx == len(root.children) - 1, include_urls=ns.include_urls, max_urls=ns.max_urls_per_group))
        lines.append("")

    ns.out.parent.mkdir(parents=True, exist_ok=True)
    ns.out.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
