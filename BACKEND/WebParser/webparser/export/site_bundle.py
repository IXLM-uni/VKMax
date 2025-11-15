# Руководство к файлу
# Назначение: сборка JSON-пакета сайта (site_bundle) из graph.json и каталога контента.
#   Формат: {site_url, crawled_at, pages[], edges[]} для поиска и графовой визуализации.
# Этап: базовая реализация. Обновляйте комментарий при изменениях.

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import orjson
import tldextract
from bs4 import BeautifulSoup  # type: ignore

from webparser.utils.url import url_to_content_path, normalize_url


@dataclass
class PageRecord:
    """Структура одного узла/страницы в site_bundle."""

    id: int
    url: str
    title: str
    text: str
    content_path: str
    depth: Optional[int]
    fqdn: str
    path: str
    cluster: str
    status: Optional[int] = None


def _fqdn_path_cluster(url: str) -> Tuple[str, str, str]:
    """Вернуть (fqdn, path, cluster) для URL.

    - fqdn: полное доменное имя (sub.domain.tld)
    - path: путь начиная с '/'
    - cluster: грубый кластер по первому сегменту пути ("/", "/media", "/course" и т.п.)
    """

    ext = tldextract.extract(url)
    apex = ext.top_domain_under_public_suffix or ext.registered_domain or ext.fqdn
    subs = ext.subdomain.split(".") if ext.subdomain else []
    fqdn = apex if not subs else f"{ext.subdomain}.{apex}"

    # выделяем путь после хоста
    rest = url.split("//", 1)[-1]
    path_part = rest.split("/", 1)[1] if "/" in rest else ""
    path = "/" + path_part if path_part else "/"
    segs = [s for s in path_part.split("/") if s]
    cluster = "/" if not segs else f"/{segs[0]}"
    return fqdn, path, cluster


def _compute_depths(nodes: Iterable[str], edges: Iterable[Tuple[str, str]], root_url: Optional[str]) -> Dict[str, int]:
    """Посчитать глубину узлов от root_url по графу.

    Если root_url=None или он не найден среди nodes — возвращает пустой словарь.
    """

    from collections import deque

    node_set = set(nodes)
    if not root_url:
        return {}

    norm_root = normalize_url(root_url)
    if not norm_root or norm_root not in node_set:
        return {}

    adj: Dict[str, List[str]] = {u: [] for u in node_set}
    for s, d in edges:
        if s in node_set and d in node_set:
            adj[s].append(d)

    depths: Dict[str, int] = {norm_root: 0}
    q: deque[Tuple[str, int]] = deque([(norm_root, 0)])
    while q:
        u, d = q.popleft()
        for v in adj.get(u, []):
            if v not in depths:
                depths[v] = d + 1
                q.append((v, d + 1))
    return depths


def build_site_bundle(
    graph_json: Path,
    content_dir: Path,
    *,
    site_url: Optional[str] = None,
    root_url: Optional[str] = None,
) -> bytes:
    """Собрать JSON-пакет сайта из graph.json и каталога контента.

    - graph_json: файл формата {"nodes": [...], "edges": [[src, dst], ...]}
    - content_dir: базовая директория с минимальными HTML-файлами
    - site_url: если задан, фильтруем только по этому сайту (fqdn совпадает)
    - root_url: корневой URL для расчёта глубины (по умолчанию = site_url)

    Возвращает сериализованный JSON (UTF-8) с полями:
    - site_url, crawled_at
    - pages: список PageRecord
    - edges: список [src_id, dst_id]
    """

    data = orjson.loads(graph_json.read_bytes())
    all_nodes: List[str] = list(data.get("nodes", []))
    raw_edges: List[Tuple[str, str]] = [tuple(e) for e in data.get("edges", [])]

    # Фильтрация по сайту (если задан)
    if site_url:
        site_fqdn, _, _ = _fqdn_path_cluster(site_url)
        nodes = [u for u in all_nodes if _fqdn_path_cluster(u)[0].endswith(site_fqdn)]
    else:
        nodes = all_nodes

    node_set = set(nodes)

    # Глубины от корневого URL
    if root_url is None:
        root_url = site_url
    depths = _compute_depths(nodes, raw_edges, root_url)

    # Собираем страницы
    pages: List[PageRecord] = []
    url_to_id: Dict[str, int] = {}

    for u in nodes:
        # Путь к минимальному HTML. Если файла нет — страницу пропускаем.
        cpath = url_to_content_path(u, content_dir)
        if not cpath.exists():
            continue
        try:
            html = cpath.read_text(encoding="utf-8")
        except Exception:
            continue

        soup = BeautifulSoup(html, "html.parser")
        article = soup.find("article") or soup.body or soup
        text = article.get_text(" ", strip=True) if article else ""
        title_tag = soup.find("title")
        title = title_tag.get_text(strip=True) if title_tag else ""

        # Пустые страницы (без текста и заголовка) пропускаем
        if not text and not title:
            continue

        fqdn, path, cluster = _fqdn_path_cluster(u)
        pid = len(pages)
        url_to_id[u] = pid

        rel_path: str
        try:
            rel_path = str(cpath.relative_to(content_dir))
        except ValueError:
            rel_path = str(cpath)

        pages.append(
            PageRecord(
                id=pid,
                url=u,
                title=title,
                text=text,
                content_path=rel_path,
                depth=depths.get(u),
                fqdn=fqdn,
                path=path,
                cluster=cluster,
                status=None,
            )
        )

    # Рёбра только между страницами, которые есть в pages
    page_urls = set(url_to_id.keys())
    edges_out: List[Tuple[int, int]] = []
    for s, d in raw_edges:
        if s in page_urls and d in page_urls:
            edges_out.append((url_to_id[s], url_to_id[d]))

    # Метаданные
    crawled_at = datetime.fromtimestamp(graph_json.stat().st_mtime, tz=timezone.utc).isoformat()

    bundle = {
        "site_url": site_url,
        "crawled_at": crawled_at,
        "pages": [
            {
                "id": p.id,
                "url": p.url,
                "status": p.status,
                "title": p.title,
                "text": p.text,
                "content_path": p.content_path,
                "depth": p.depth,
                "fqdn": p.fqdn,
                "path": p.path,
                "cluster": p.cluster,
            }
            for p in pages
        ],
        "edges": [[s, d] for (s, d) in edges_out],
    }

    return orjson.dumps(bundle)
