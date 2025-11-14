# WebParser — быстрый асинхронный парсер ссылок

## Идея
- Вход: список seed-URL.
- Выход: граф ссылок (nodes, edges), экспорт в edges.csv и graph.json.
- Первая версия: фокус на скорости, HTML-only, построение графа без лишней логики.

## Стек
- Playwright (APIRequestContext) — быстрый HTTP, HTTP/2, keep-alive.
- Selectolax — быстрый парсер HTML.
- aiolimiter — лимиты по хостам.
- tldextract — анализ домена/сабдомена.
- orjson — быстрый экспорт.
- Опционально: bloom-filter2 (экономия памяти), networkx (экспорт графа).

## Архитектура
- core, utils, robots, fetch, parse, frontier, graph, orchestrator, cli.
- Асинхронность: asyncio + Semaphore (глобальная конкуренция) + per-host RateLimiter.
- Очередь: asyncio.Queue (BFS/DFS), дедуп: set/BloomFilter.

## Установка
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
python -m playwright install --with-deps chromium
```

## Быстрый старт (скелет)
```bash
python -m webparser.cli.main --seeds https://example.com --max-depth 2 --concurrency 10
```

## Экспорт
- edges.csv (src,dst)
- graph.json (nodes,edges)

## Политика
- Уважать robots.txt и лимиты.
- Фильтровать не-HTML, трекинговые query, неподдерживаемые схемы.

## Планы
- Добавить fallback headless-браузера с блокировкой ресурсов.
- Бенчмарки и тесты производительности.
