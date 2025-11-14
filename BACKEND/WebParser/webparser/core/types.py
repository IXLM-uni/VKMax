# Руководство к файлу
# Назначение: общие типы/DTO (узел/ребро/задача очереди и т.п.).
# Этап: базовая реализация DTO. Обновляйте комментарий при изменениях.

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class UrlTask:
    """Задача для фронтира: URL с глубиной и родителем."""

    url: str
    depth: int
    parent: Optional[str] = None


@dataclass
class FetchResult:
    """Результат загрузки URL."""

    url: str
    final_url: str
    status: int
    content_type: Optional[str]
    text: Optional[str]
