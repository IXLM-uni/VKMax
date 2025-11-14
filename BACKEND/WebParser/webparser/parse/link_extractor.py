# Руководство к файлу
# Назначение: извлечение ссылок из HTML (a[href]), быстрый парсер Selectolax.
# Этап: базовая реализация. Обновляйте комментарий при изменениях.

from __future__ import annotations

from typing import List
from selectolax.parser import HTMLParser


class LinkExtractor:
    """Извлечение href из тегов <a>."""

    @staticmethod
    def extract_hrefs(html: str) -> List[str]:
        tree = HTMLParser(html)
        hrefs: List[str] = []
        for node in tree.css("a"):
            href = node.attributes.get("href")
            if href:
                hrefs.append(href.strip())
        return hrefs
