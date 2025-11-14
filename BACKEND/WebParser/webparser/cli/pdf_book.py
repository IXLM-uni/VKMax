# Руководство к файлу
# Назначение: CLI для сборки PDF-книги из graph.json и каталога контента.
# Этап: базовая реализация. Обновляйте комментарий при изменениях.

from __future__ import annotations

import argparse
from pathlib import Path

from webparser.export.pdf_book import PdfBookBuilder


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Сборка PDF-книги из контента")
    p.add_argument("--graph-json", type=Path, required=True)
    p.add_argument("--content-dir", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--site-url", type=str, default=None, help="Опционально: ограничить сборку конкретным сайтом (fqdn)")
    return p.parse_args()


def main() -> None:
    ns = parse_args()
    builder = PdfBookBuilder()
    builder.build(out_pdf=ns.out, graph_json=ns.graph_json, content_dir=ns.content_dir, site_url=ns.site_url)


if __name__ == "__main__":
    main()
