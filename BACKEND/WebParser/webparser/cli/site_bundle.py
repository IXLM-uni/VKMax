# Руководство к файлу
# Назначение: CLI для сборки JSON-пакета site_bundle из graph.json и каталога контента.
#   Формат: {site_url, crawled_at, pages[], edges[]} для поиска и графовой визуализации.
# Этап: базовая реализация. Обновляйте комментарий при изменениях.

from __future__ import annotations

import argparse
from pathlib import Path

from webparser.export.site_bundle import build_site_bundle


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Сборка JSON-пакета сайта из graph.json и контента")
    p.add_argument("--graph-json", type=Path, required=True)
    p.add_argument("--content-dir", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--site-url", type=str, default=None, help="Опционально: ограничить сборку конкретным сайтом (fqdn/URL)")
    p.add_argument("--root-url", type=str, default=None, help="Опциональный корневой URL для расчёта глубины")
    return p.parse_args()


def main() -> None:
    ns = parse_args()
    data = build_site_bundle(
        graph_json=ns.graph_json,
        content_dir=ns.content_dir,
        site_url=ns.site_url,
        root_url=ns.root_url,
    )
    ns.out.parent.mkdir(parents=True, exist_ok=True)
    ns.out.write_bytes(data)


if __name__ == "__main__":
    main()
