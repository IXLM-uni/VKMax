# Руководство к файлу
# Назначение: CLI для обхода сайта и единовременной сборки JSON-пакета (site_bundle).
#   На выходе только один JSON-файл: {site_url, crawled_at, pages[], edges[]}.
# Этап: базовая реализация. Обновляйте комментарий при изменениях.

from __future__ import annotations

import argparse
import asyncio
import tempfile
from pathlib import Path

from webparser.core.config import CrawlConfig
from webparser.core.logging import configure_logging
from webparser.graph.exporters import Exporter
from webparser.orchestrator.crawler import CrawlerOrchestrator
from webparser.export.site_bundle import build_site_bundle


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Обход сайта и сборка одного JSON-bundle (без PDF/CSV)",
    )
    p.add_argument("--seed", type=str, required=True, help="Seed-URL сайта (например, https://dev.max.ru/docs)")
    p.add_argument("--out", type=Path, required=True, help="Путь к JSON-файлу bundle")
    p.add_argument("--max-depth", type=int, default=2)
    p.add_argument("--max-pages", type=int, default=2000)
    p.add_argument("--concurrency", type=int, default=10)
    p.add_argument("--per-host-rps", type=float, default=2.0)
    p.add_argument("--same-domain-only", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument(
        "--content-text-only",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Извлекать только текст (h1–h6, p) без списков/кода/цитат",
    )
    p.add_argument("--log-level", type=str, default="INFO")
    return p.parse_args()


async def main_async(ns: argparse.Namespace) -> None:
    configure_logging(level=ns.log_level, to_file=None, json=False)

    seed = ns.seed

    # Временный каталог для graph.json и минимального HTML (технический слой)
    with tempfile.TemporaryDirectory(prefix="crawl_bundle_") as tmpdir:
        tmp_path = Path(tmpdir)
        content_dir = tmp_path / "content"
        content_dir.mkdir(parents=True, exist_ok=True)
        graph_json = tmp_path / "graph.json"

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
        )

        orch = CrawlerOrchestrator(cfg)
        graph = await orch.run()

        # Граф сохраняем только во временный файл для дальнейшей сборки JSON
        Exporter.write_graph_json(graph_json, list(graph.nodes()), graph.edges())

        bundle_bytes = build_site_bundle(
            graph_json=graph_json,
            content_dir=content_dir,
            site_url=seed,
            root_url=seed,
        )

    # Пишем только JSON bundle во внешний файл
    ns.out.parent.mkdir(parents=True, exist_ok=True)
    ns.out.write_bytes(bundle_bytes)
    print(f"[crawl_bundle] JSON bundle для {seed} сохранён в {ns.out}")


def main() -> None:
    ns = parse_args()
    asyncio.run(main_async(ns))


if __name__ == "__main__":
    main()
