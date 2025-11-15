# Руководство к файлу (BACKEND/Dockerfile)
# Назначение:
# - Сборка контейнера VKMax backend (FastAPI + SEVICES) на базе Ubuntu.
# - Устанавливает Python, зависимости проекта, Playwright и wkhtmltopdf.
# - Точка входа: uvicorn BACKEND.FAST_API.fast_api:app.

FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Базовые зависимости: Python, pip, Postgres client libs, wkhtmltopdf
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    curl \
    wget \
    ca-certificates \
    libpq-dev \
    wkhtmltopdf \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Устанавливаем Python-зависимости из requirements.txt
COPY BACKEND/requirements.txt ./BACKEND/requirements.txt
RUN python3 -m pip install --no-cache-dir --upgrade pip \
 && python3 -m pip install --no-cache-dir -r BACKEND/requirements.txt \
 && python3 -m pip install --no-cache-dir playwright \
 && python3 -m playwright install --with-deps chromium

# Копируем исходники backend
COPY BACKEND /app/BACKEND

# Чтобы можно было импортировать BACKEND как пакет и локальный WebParser как `webparser`
ENV PYTHONPATH=/app:/app/BACKEND/WebParser

EXPOSE 8000

CMD ["uvicorn", "BACKEND.FAST_API.fast_api:app", "--host", "0.0.0.0", "--port", "8000"]
