# Руководство к файлу
# Назначение: параметры запуска краулера (seeds, глубина, лимиты, фильтры) и сборки PDF.
# Этап: расширенная реализация. Включает настройки сохранения контента и опциональной сборки PDF после обхода.
# Обновляйте комментарий при изменениях.

from dataclasses import dataclass, field
from typing import List, Set, Optional


@dataclass
class CrawlConfig:
    """Конфигурация парсера и построения графа ссылок."""

    # Входные данные
    seeds: List[str]

    # Ограничения обхода
    max_depth: int = 2
    max_pages: int = 10000
    same_domain_only: bool = True

    # Конкурентность и лимиты
    concurrency: int = 10
    per_host_rps: float = 2.0

    # Сетевые настройки
    user_agent: str = (
        "WebParser/0.1 (+https://example.com; contact: bot@example.com)"
    )
    request_timeout_ms: int = 15000
    max_redirects: int = 5

    # Фильтры URL
    allowed_schemes: Set[str] = field(default_factory=lambda: {"http", "https"})
    block_extensions: Set[str] = field(
        default_factory=lambda: {
            "jpg",
            "jpeg",
            "png",
            "gif",
            "webp",
            "svg",
            "mp4",
            "mp3",
            "avi",
            "mov",
            "mkv",
            "pdf",
            "zip",
            "rar",
            "7z",
            "gz",
            "bz2",
            "exe",
            "dmg",
            "iso",
        }
    )
    tracking_params: Set[str] = field(
        default_factory=lambda: {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "fbclid", "gclid"}
    )
    tracking_prefixes: Set[str] = field(
        default_factory=lambda: {"utm_", "roistat_"}
    )

    # Каноникализация пути
    strip_trailing_slash: bool = True

    # robots.txt
    robots_ttl_sec: int = 600

    # Сохранение контента
    save_content: bool = False
    content_dir: str = "content"
    content_text_only: bool = False

    # Сборка PDF после обхода
    build_pdf: bool = False
    pdf_out: str = "book.pdf"
    pdf_site_url: Optional[str] = None
