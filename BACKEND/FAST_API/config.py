# Руководство к файлу (FAST_API/config.py)
# Назначение:
# - Централизованные настройки FastAPI для VKMax и параметры хранилища.
# - Временное in-memory хранилище (до подключения SQLite/Postgres).
# Важно:
# - Директории storage/tmp/logs создаются автоматически.
# - Лимит загрузки файлов по умолчанию 40 МБ.
# - Все значения можно переопределить через переменные окружения.

from __future__ import annotations

import os
import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, Optional
from uuid import uuid4

try:
    from pydantic_settings import BaseSettings
    from pydantic import Field
except Exception:  # минимально работаем без pydantic_settings
    BaseSettings = object  # type: ignore
    def Field(default=None, **kwargs):  # type: ignore
        return default


class Settings(BaseSettings):
    """Базовые настройки VKMax FastAPI."""

    app_name: str = Field("VKMax API", description="Название приложения")
    version: str = Field("0.1.0", description="Версия API")

    # Путь к базовой папке проекта (по умолчанию – рядом с этим модулем)
    base_dir: str = Field(default=str(Path(__file__).resolve().parent.parent), description="Базовая директория")

    # Каталоги для хранения
    storage_dir: str = Field(default=str(Path(__file__).resolve().parent.parent / "storage"), description="Файлы")
    tmp_dir: str = Field(default=str(Path(__file__).resolve().parent.parent / "tmp"), description="TMP файлы")
    logs_dir: str = Field(default=str(Path(__file__).resolve().parent.parent / "logs"), description="Логи")

    # Ограничения
    max_upload_mb: int = Field(default=40, description="Максимальный размер файла в МБ")

    # CORS
    cors_origins: str = Field(default="http://localhost:3000,http://127.0.0.1:3000", description="Разрешённые Origin")

    # Провайдер LLM (для будущей интеграции)
    llm_provider: str = Field(default="gemini")

    class Config:
        env_prefix = "VKMAX_"


def _ensure_dirs(*paths: str) -> None:
    for p in paths:
        try:
            Path(p).mkdir(parents=True, exist_ok=True)
        except Exception:
            pass


settings = Settings()  # type: ignore[call-arg]
_ensure_dirs(settings.storage_dir, settings.tmp_dir, settings.logs_dir)


# --------------------------- In-Memory Store ---------------------------

@dataclass
class InMemoryStore:
    """Простейшее in-memory хранилище до подключения БД.

    Структуры:
      - users: {user_id: {...}}
      - files: {file_id: {...}}
      - operations: {operation_id: {...}}
      - formats: список поддерживаемых форматов
    """

    users: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    files: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    operations: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    formats: Dict[str, Any] = field(default_factory=dict)

    def next_id(self) -> str:
        return str(uuid4())

    def sha256_file(self, path: str) -> str:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()


store = InMemoryStore()

# Базовая матрица поддерживаемых конверсий v1
SUPPORTED_CONVERSIONS = {
    "from_pdf": ["html"],
    "from_docx": ["html"],
    "from_website": ["html"],
    "from_html": ["graph"],
}

# Справочник форматов (минимум)
store.formats = {
    "pdf": {"type": "document", "extension": ".pdf", "mime_type": "application/pdf", "is_input": True, "is_output": False},
    "docx": {"type": "document", "extension": ".docx", "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "is_input": True, "is_output": False},
    "html": {"type": "document", "extension": ".html", "mime_type": "text/html", "is_input": True, "is_output": True},
    "graph": {"type": "graph", "extension": ".json", "mime_type": "application/json", "is_input": False, "is_output": True},
}
