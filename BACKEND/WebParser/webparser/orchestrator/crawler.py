# Руководство к файлу
# Назначение: оркестратор: планирование задач, лимиты, robots, построение графа, сохранение контента.
# Этап: расширенная реализация. Поддерживает сохранение минимального HTML в режиме text_only.
# Обновляйте комментарий при изменениях.
# Важно: конкурентность 10 задач; по завершении слота — добор из очереди.

from __future__ import annotations

import asyncio
import logging
from typing import List, Set
from pathlib import Path

from webparser.core.config import CrawlConfig
from webparser.core.types import UrlTask
from webparser.fetch.http_fetcher import HttpFetcher
from webparser.frontier.dedup import Deduplicator
from webparser.frontier.queue import Frontier
from webparser.frontier.rate_limiter import RateLimiter
from webparser.graph.store import GraphStore
from webparser.parse.link_extractor import LinkExtractor
from webparser.parse.content_extractor import ContentExtractor
from webparser.robots.cache import RobotsCache
from webparser.robots.policy import RobotsPolicy
from webparser.utils.mime import is_html
from webparser.utils.url import normalize_url, same_registrable_domain, url_to_content_path


class CrawlerOrchestrator:
    """Оркестратор обхода и построения графа ссылок."""

    def __init__(self, cfg: CrawlConfig) -> None:
        self.cfg = cfg
        self.log = logging.getLogger(__name__)
        self.frontier = Frontier()
        self.dedup = Deduplicator(use_bloom=False)
        self.graph = GraphStore()
        self.limiter = RateLimiter(cfg.concurrency, cfg.per_host_rps)
        self.fetcher = HttpFetcher(cfg.user_agent, cfg.request_timeout_ms, cfg.max_redirects)
        self.robots = RobotsPolicy(cfg.user_agent, RobotsCache(cfg.robots_ttl_sec))
        # список базовых доменов для ограничения same_domain_only
        self.allowed_domains: Set[str] = set()
        # счётчик обработанных страниц и событие остановки
        self._processed = 0
        self._stop_event = asyncio.Event()
        self._cnt_lock = asyncio.Lock()

    async def _init_allowed_domains(self) -> None:
        if not self.cfg.same_domain_only:
            return
        for seed in self.cfg.seeds:
            for other in self.cfg.seeds:
                if same_registrable_domain(seed, other):
                    # добавляем домен одного уровня
                    # same_registrable_domain сравнивает корректно
                    self.allowed_domains.add(seed)
        # упрощение: будем проверять по отношению к каждому seed

    def _is_allowed_domain(self, url: str) -> bool:
        if not self.cfg.same_domain_only:
            return True
        for seed in self.cfg.seeds:
            if same_registrable_domain(seed, url):
                return True
        return False

    async def _worker(self, worker_id: int) -> None:
        while True:
            if self._stop_event.is_set():
                return
            try:
                task = await asyncio.wait_for(self.frontier.dequeue(), timeout=1.0)
            except asyncio.TimeoutError:
                return

            self.log.debug(f"worker={worker_id} dequeue url={task.url} depth={task.depth}")
            if self.dedup.seen(task.url):
                self.log.debug(f"worker={worker_id} skip-dup url={task.url}")
                self.frontier.task_done()
                continue

            # robots
            allowed = await self.robots.is_allowed(self.fetcher, task.url)
            if not allowed:
                self.log.debug(f"worker={worker_id} robots-deny url={task.url}")
                self.frontier.task_done()
                continue

            # лимиты
            async with self.limiter.slot(task.url):
                res = await self.fetcher.fetch(task.url)

            # дедуп по финальному url (с нормализацией)
            final_raw = res.final_url or task.url
            self.log.info(f"worker={worker_id} fetched status={res.status} url={task.url} final={final_raw}")
            final = normalize_url(
                final_raw,
                allowed_schemes=self.cfg.allowed_schemes,
                tracking_params=self.cfg.tracking_params,
                tracking_prefixes=self.cfg.tracking_prefixes,
                block_extensions=self.cfg.block_extensions,
                strip_trailing_slash=self.cfg.strip_trailing_slash,
            )
            if not final:
                self.frontier.task_done()
                continue
            if self.dedup.seen(final):
                self.frontier.task_done()
                continue
            self.dedup.add(final)

            # добавляем ребро, если есть родитель
            if task.parent:
                self.graph.add_edge(task.parent, final)

            # проверяем контент
            if res.status < 400 and is_html(res.content_type or "") and res.text:
                # извлечение и сохранение минимальной HTML-разметки
                if self.cfg.save_content:
                    try:
                        minimal = ContentExtractor.extract_minimal_html(res.text, text_only=self.cfg.content_text_only)
                        out_path = url_to_content_path(final, Path(self.cfg.content_dir))
                        out_path.parent.mkdir(parents=True, exist_ok=True)
                        out_path.write_text(minimal, encoding="utf-8")
                    except Exception as e:
                        self.log.debug(f"content-save-failed url={final} err={e}")
                hrefs = LinkExtractor.extract_hrefs(res.text)
                children: List[str] = []
                for href in hrefs:
                    norm = normalize_url(
                        href,
                        base=final,
                        allowed_schemes=self.cfg.allowed_schemes,
                        tracking_params=self.cfg.tracking_params,
                        tracking_prefixes=self.cfg.tracking_prefixes,
                        block_extensions=self.cfg.block_extensions,
                        strip_trailing_slash=self.cfg.strip_trailing_slash,
                    )
                    if not norm:
                        continue
                    if self.cfg.same_domain_only and not self._is_allowed_domain(norm):
                        continue
                    children.append(norm)

                # энкью детей
                if task.depth + 1 <= self.cfg.max_depth:
                    self.log.debug(f"worker={worker_id} enqueue-children count={len(children)} from={final} depth={task.depth+1}")
                    for c in children:
                        if not self.dedup.seen(c):
                            await self.frontier.enqueue(UrlTask(url=c, depth=task.depth + 1, parent=final))

            self.frontier.task_done()

            # инкремент processed, закрываем когда достигли лимита
            async with self._cnt_lock:
                self._processed += 1
                # Простое информирование о прогрессе: каждые 50 страниц
                if self._processed == 1 or self._processed % 50 == 0:
                    self.log.info("progress: processed=%d queue=%d", self._processed, self.frontier.size())
                if self._processed >= self.cfg.max_pages:
                    self.log.info("stop: reached max_pages=%d", self.cfg.max_pages)
                    self._stop_event.set()
                    return

    async def run(self) -> GraphStore:
        # старт компонентов
        await self._init_allowed_domains()
        await self.fetcher.start()

        # начальные задачи (нормализованные seeds)
        for s in self.cfg.seeds:
            norm = normalize_url(
                s,
                allowed_schemes=self.cfg.allowed_schemes,
                tracking_params=self.cfg.tracking_params,
                tracking_prefixes=self.cfg.tracking_prefixes,
                block_extensions=self.cfg.block_extensions,
                strip_trailing_slash=self.cfg.strip_trailing_slash,
            )
            if not norm:
                continue
            await self.frontier.enqueue(UrlTask(url=norm, depth=0, parent=None))

        # запускаем пул воркеров
        workers = [asyncio.create_task(self._worker(i)) for i in range(self.cfg.concurrency)]

        # ожидание завершения очереди или пока не достигнем лимита
        await asyncio.gather(*workers)

        await self.fetcher.stop()
        return self.graph
