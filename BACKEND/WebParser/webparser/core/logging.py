# Руководство к файлу
# Назначение: настройка логирования проекта (уровень, формат, вывод в файл/STDOUT).
# Этап: базовая реализация. Обновляйте комментарий при изменениях.

from __future__ import annotations

import logging
import sys
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


class JsonFormatter(logging.Formatter):
    """Простой JSON-форматтер без внешних зависимостей."""

    def format(self, record: logging.LogRecord) -> str:
        # минимальный JSON руками, чтобы избежать зависимостей
        ts = datetime.utcfromtimestamp(record.created).isoformat() + "Z"
        msg = record.getMessage().replace("\n", " ")
        # экранирование простое
        msg = msg.replace("\\", "\\\\").replace('"', '\\"')
        name = record.name
        level = record.levelname
        return f'{{"ts":"{ts}","level":"{level}","logger":"{name}","msg":"{msg}"}}'


@dataclass
class LogConfig:
    level: str = "INFO"
    to_file: Optional[str] = None
    json: bool = False


def configure_logging(level: str = "INFO", *, to_file: Optional[str] = None, json: bool = False) -> None:
    handlers: list[logging.Handler] = []
    if to_file:
        h = logging.FileHandler(to_file, encoding="utf-8")
    else:
        h = logging.StreamHandler(sys.stdout)
    if json:
        fmt = JsonFormatter()
    else:
        fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    h.setFormatter(fmt)
    handlers.append(h)

    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    for hh in handlers:
        root.addHandler(hh)

    # снизим шум от внешних библиотек
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("playwright").setLevel(logging.WARNING)
