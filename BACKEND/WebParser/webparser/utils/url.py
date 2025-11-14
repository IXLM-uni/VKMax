# Руководство к файлу
# Назначение: нормализация/каноникализация URL, фильтры схем и расширений.
# Этап: базовая реализация. Обновляйте комментарий при изменениях.

from __future__ import annotations

from typing import Optional, Iterable, Set, Tuple
from urllib.parse import urljoin, urlparse, urlunparse, parse_qsl, urlencode
from pathlib import Path
import hashlib
import re

import tldextract


def _remove_fragment(url: str) -> str:
    p = urlparse(url)
    return urlunparse(p._replace(fragment=""))


def _normalize_netloc(scheme: str, netloc: str) -> str:
    host, port = _split_host_port(netloc)
    host = host.lower()
    # удалить порт по умолчанию
    if (scheme == "http" and port == "80") or (scheme == "https" and port == "443"):
        return host
    return f"{host}:{port}" if port else host


def _split_host_port(netloc: str) -> Tuple[str, Optional[str]]:
    if ":" in netloc:
        host, port = netloc.rsplit(":", 1)
        return host, port
    return netloc, None


def _clean_query(url: str, tracking_params: Iterable[str], tracking_prefixes: Iterable[str]) -> str:
    p = urlparse(url)
    q = parse_qsl(p.query, keep_blank_values=False)
    tracking = {k.lower() for k in tracking_params}
    prefixes = tuple(s.lower() for s in tracking_prefixes)
    def _drop(k: str) -> bool:
        kl = k.lower()
        if kl in tracking:
            return True
        return any(kl.startswith(pref) for pref in prefixes)
    q = [(k, v) for (k, v) in q if not _drop(k)]
    # сортируем для каноничности
    q.sort(key=lambda kv: (kv[0], kv[1]))
    query = urlencode(q, doseq=True)
    return urlunparse(p._replace(query=query))


def _has_blocked_extension(path: str, block_extensions: Set[str]) -> bool:
    if "." not in path:
        return False
    ext = path.rsplit(".", 1)[-1].lower()
    return ext in block_extensions


def normalize_url(
    url: str,
    *,
    base: Optional[str] = None,
    allowed_schemes: Set[str] = frozenset({"http", "https"}),
    tracking_params: Iterable[str] = (),
    tracking_prefixes: Iterable[str] = (),
    block_extensions: Set[str] = frozenset(),
    strip_trailing_slash: bool = True,
) -> Optional[str]:
    """Канонизирует URL. Возвращает None, если схема не разрешена или расширение блокируется."""
    if base:
        url = urljoin(base, url)
    # убрать фрагмент
    url = _remove_fragment(url)
    p = urlparse(url)
    if not p.scheme or p.scheme.lower() not in allowed_schemes:
        return None
    if _has_blocked_extension(p.path, block_extensions):
        return None
    netloc = _normalize_netloc(p.scheme.lower(), p.netloc)
    # обработка пути: трейлинг-слэш
    path = p.path or "/"
    if strip_trailing_slash and path.endswith("/") and path != "/":
        path = path[:-1]
    normalized = urlunparse(p._replace(scheme=p.scheme.lower(), netloc=netloc, path=path))
    # очистить трекинг параметры и отсортировать
    normalized = _clean_query(normalized, tracking_params, tracking_prefixes)
    return normalized


def same_registrable_domain(url1: str, url2: str) -> bool:
    d1 = tldextract.extract(url1)
    d2 = tldextract.extract(url2)
    return (d1.registered_domain or d1.fqdn) == (d2.registered_domain or d2.fqdn)


def get_host(url: str) -> str:
    return urlparse(url).hostname or ""


_SAFE_RE = re.compile(r"[^a-zA-Z0-9_-]+")


def _safe_part(s: str) -> str:
    s = s.strip().lower()
    s = _SAFE_RE.sub("-", s)
    s = s.strip("-")
    return s or "_"


def url_to_content_path(url: str, base_dir: Path) -> Path:
    """Построить путь для сохранения контента URL как .html.

    Структура: base_dir/host/<path_segments>/file.html
    - Путь нормализуется, пустой/"/" -> index.html
    - Если последний сегмент без расширения, добавляем .html
    - Для устойчивости к коллизиям добавляется короткий хэш.
    """
    p = urlparse(url)
    host = p.hostname or "unknown-host"
    host_safe = _safe_part(host)
    path = p.path or "/"
    segments = [seg for seg in path.split("/") if seg]
    safe_segments = [_safe_part(seg) for seg in segments]
    # имя файла
    if not safe_segments:
        filename = "index"
        dirs: list[str] = []
    else:
        filename = safe_segments[-1]
        dirs = safe_segments[:-1]

    # Расширение .html, если отсутствует
    if "." not in filename:
        filename += ".html"
    # короткий хэш по полному URL, чтобы избежать коллизий
    short = hashlib.sha1(url.encode("utf-8")).hexdigest()[:8]
    if filename.endswith(".html"):
        filename = filename[:-5] + f"__{short}.html"
    else:
        filename = filename + f"__{short}"

    full = base_dir / host_safe
    for d in dirs:
        full = full / d
    return full / filename
