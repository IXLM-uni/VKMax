# Руководство к файлу
# Назначение: утилиты для MIME-типов и фильтрации контента.
# Этап: базовая реализация. Обновляйте комментарий при изменениях.

from typing import Optional, Tuple


def parse_content_type(header: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    """Парсит заголовок Content-Type. Возвращает (mime, charset)."""
    if not header:
        return None, None
    parts = [p.strip() for p in header.split(";")]
    mime = parts[0].lower() if parts else None
    charset = None
    for p in parts[1:]:
        if p.lower().startswith("charset="):
            charset = p.split("=", 1)[1].strip().strip('"').lower()
            break
    return mime, charset


def is_html(content_type: Optional[str]) -> bool:
    mime, _ = parse_content_type(content_type)
    return bool(mime and (mime == "text/html" or mime.startswith("text/html")))
