# Руководство к файлу
# Назначение: CLI: параметры запуска (seeds, глубина, concurrency), вызов оркестратора, опциональная сборка PDF.
# Этап: расширенная реализация. Поддерживает сохранение контента и сборку PDF после обхода.
# Обновляйте комментарий при изменениях.

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from webparser.core.config import CrawlConfig
from webparser.core.logging import configure_logging
from webparser.graph.exporters import Exporter
from webparser.orchestrator.crawler import CrawlerOrchestrator


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="WebParser: построение графа ссылок")
    p.add_argument("--seeds", nargs="+", required=True, help="Список seed-URL")
    p.add_argument("--max-depth", type=int, default=2)
    p.add_argument("--max-pages", type=int, default=10000)
    p.add_argument("--concurrency", type=int, default=10)
    p.add_argument("--per-host-rps", type=float, default=2.0)
    p.add_argument("--same-domain-only", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--edges-csv", type=Path, default=Path("edges.csv"))
    p.add_argument("--graph-json", type=Path, default=Path("graph.json"))
    p.add_argument("--save-content", action=argparse.BooleanOptionalAction, default=False, help="Сохранять минимальный HTML-контент страниц")
    p.add_argument("--content-dir", type=Path, default=Path("content"), help="Директория для сохранения контента")
    p.add_argument("--content-text-only", action=argparse.BooleanOptionalAction, default=False, help="Извлекать только текст (h1–h6, p) без списков/кода/цитат")
    p.add_argument("--log-level", type=str, default="INFO", help="Уровень логирования (DEBUG/INFO/WARN/ERROR)")
    p.add_argument("--log-json", action=argparse.BooleanOptionalAction, default=False, help="JSON-логирование")
    p.add_argument("--log-file", type=Path, default=None, help="Файл для логов (по умолчанию STDOUT)")

    # Параметры сборки PDF
    p.add_argument("--build-pdf", action=argparse.BooleanOptionalAction, default=False, help="Собрать PDF после обхода")
    p.add_argument("--pdf-out", type=Path, default=Path("book.pdf"), help="Путь к выходному PDF")
    p.add_argument("--pdf-site-url", type=str, default=None, help="Ограничить PDF одним сайтом (по FQDN)")
    return p.parse_args()


async def main_async(ns: argparse.Namespace) -> None:
    configure_logging(level=ns.log_level, to_file=str(ns.log_file) if ns.log_file else None, json=ns.log_json)
    # Если хотим сразу собрать PDF — нужно сохранять контент
    if ns.build_pdf and not ns.save_content:
        ns.save_content = True
    cfg = CrawlConfig(
        seeds=list(ns.seeds),
        max_depth=ns.max_depth,
        max_pages=ns.max_pages,
        same_domain_only=ns.same_domain_only,
        concurrency=ns.concurrency,
        per_host_rps=ns.per_host_rps,
        save_content=ns.save_content,
        content_dir=str(ns.content_dir),
        content_text_only=ns.content_text_only,
        build_pdf=ns.build_pdf,
        pdf_out=str(ns.pdf_out),
        pdf_site_url=ns.pdf_site_url,
    )
    orch = CrawlerOrchestrator(cfg)
    graph = await orch.run()
    Exporter.write_edges_csv(ns.edges_csv, graph.edges())
    Exporter.write_graph_json(ns.graph_json, list(graph.nodes()), graph.edges())

    # Опционально — сборка PDF после обхода
    if ns.build_pdf:
        from webparser.export.pdf_book import PdfBookBuilder  # локальный импорт, чтобы не требовать dep без флага
        builder = PdfBookBuilder()
        builder.build(out_pdf=ns.pdf_out, graph_json=ns.graph_json, content_dir=ns.content_dir, site_url=ns.pdf_site_url)


def main() -> None:
    ns = parse_args()
    asyncio.run(main_async(ns))


if __name__ == "__main__":
    main()
