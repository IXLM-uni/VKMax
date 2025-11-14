# Руководство к файлу
# Назначение: паттерны включения/исключения URL, трекинг-параметры и т.д.
# Этап: базовая реализация. Обновляйте комментарий при изменениях.

from typing import Set, List


TRACKING_PARAMS: Set[str] = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "fbclid",
    "gclid",
    "roistat_visit",
    "yclid",
    "ysclid",
    "transaction_id",
    "ybaip",
}


BLOCK_EXTENSIONS: Set[str] = {
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


# Параметры по префиксу (удаляются все ключи, начинающиеся с указанных префиксов)
TRACKING_PREFIXES: Set[str] = {
    "utm_",
    "roistat_",
}


# Шаблоны для возможного будущего использования (пока пустые)
INCLUDE_PATTERNS: List[str] = []
EXCLUDE_PATTERNS: List[str] = []
