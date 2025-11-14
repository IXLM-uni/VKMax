# Руководство к файлу
# Назначение: удобный CLI-обёртка для обхода одного сайта с авто-созданием структуры папок
#   sites/<fqdn>/<timestamp>/ (edges.csv, graph.json, content/, <fqdn>.pdf).
# Этап: базовая реализация. Обновляйте комментарий при изменениях.

from __future__ import annotations

import argparse
import asyncio
from datetime import datetime
from pathlib import Path

import tldextract

from webparser.core.config import CrawlConfig
from webparser.core.logging import configure_logging
from webparser.graph.exporters import Exporter
from webparser.orchestrator.crawler import CrawlerOrchestrator
from webparser.export.pdf_book import PdfBookBuilder


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Обход одного сайта с автосозданием папки и сборкой PDF-книги",
    )
    p.add_argument("--seed", type=str, required=True, help="Seed-URL сайта (например, https://minobrnauki.gov.ru/)")
    p.add_argument("--max-depth", type=int, default=2)
    p.add_argument("--max-pages", type=int, default=2000)
    p.add_argument("--concurrency", type=int, default=10)
    p.add_argument("--per-host-rps", type=float, default=2.0)
    p.add_argument("--same-domain-only", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--base-dir", type=Path, default=Path("sites"), help="Базовая директория для результатов")
    p.add_argument(
        "--content-text-only",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Извлекать только текст (h1–h6, p) без списков/кода/цитат",
    )
    p.add_argument("--log-level", type=str, default="INFO")
    return p.parse_args()


def _fqdn_from_seed(seed: str) -> str:
    ext = tldextract.extract(seed)
    apex = ext.top_domain_under_public_suffix or ext.registered_domain or ext.fqdn
    fqdn = apex if not ext.subdomain else f"{ext.subdomain}.{apex}"
    return fqdn


async def main_async(ns: argparse.Namespace) -> None:
    configure_logging(level=ns.log_level, to_file=None, json=False)

    seed = ns.seed
    fqdn = _fqdn_from_seed(seed)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")

    run_dir = ns.base_dir / fqdn / ts
    content_dir = run_dir / "content"
    edges_csv = run_dir / "edges.csv"
    graph_json = run_dir / "graph.json"
    pdf_out = run_dir / f"{fqdn}.pdf"

    run_dir.mkdir(parents=True, exist_ok=True)
    content_dir.mkdir(parents=True, exist_ok=True)

    cfg = CrawlConfig(
        seeds=[seed],
        max_depth=ns.max_depth,
        max_pages=ns.max_pages,
        same_domain_only=ns.same_domain_only,
        concurrency=ns.concurrency,
        per_host_rps=ns.per_host_rps,
        save_content=True,
        content_dir=str(content_dir),
        content_text_only=ns.content_text_only,
        build_pdf=True,
        pdf_out=str(pdf_out),
        pdf_site_url=seed,
    )

    orch = CrawlerOrchestrator(cfg)
    graph = await orch.run()

    Exporter.write_edges_csv(edges_csv, graph.edges())
    Exporter.write_graph_json(graph_json, list(graph.nodes()), graph.edges())

    # Сборка PDF-книги для этого сайта
    builder = PdfBookBuilder()
    builder.build(out_pdf=pdf_out, graph_json=graph_json, content_dir=content_dir, site_url=seed)

    # Выводим пользователю путь к результатам (через обычный print)
    print(f"[site_crawl] Результаты для {seed} сохранены в {run_dir}")


def main() -> None:
    ns = parse_args()
    asyncio.run(main_async(ns))


if __name__ == "__main__":
    main()
