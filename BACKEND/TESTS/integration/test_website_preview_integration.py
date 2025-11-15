# Руководство к файлу (TESTS/integration/test_website_preview_integration.py)
# Назначение:
# - Интеграционные тесты для роутера превью сайтов `/websites/preview`.
# - Проверяют базовый успешный сценарий и поведение при некорректном URL.

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_website_preview_ok(http_client):
  """POST /websites/preview с валидным URL должен возвращать title=url и 200."""

  payload = {"url": "https://example.com"}

  resp = await http_client.post("/websites/preview", json=payload)
  assert resp.status_code == 200

  data = resp.json()
  # Текущая реализация build_website_preview возвращает title = url
  assert data["title"] == payload["url"]
  # Остальные поля могут быть None, главное — корректный JSON-ответ
  assert "description" in data
  assert "screenshot_url" in data
  assert "page_count" in data


@pytest.mark.asyncio
async def test_website_preview_invalid_url(http_client):
  """Некорректный URL всё ещё должен обрабатываться предсказуемо.

  MVP-реализация build_website_preview фактически не валидирует URL и просто
  возвращает title=url. Этот тест фиксирует текущее поведение, чтобы при
  ужесточении валидации было видно изменение контракта.
  """

  payload = {"url": "not-a-real-url"}

  resp = await http_client.post("/websites/preview", json=payload)
  assert resp.status_code == 200

  data = resp.json()
  assert data["title"] == payload["url"]
