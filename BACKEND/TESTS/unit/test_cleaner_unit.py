# Руководство к файлу (TESTS/unit/test_cleaner_unit.py)
# Назначение:
# - Unit-тесты для LLM_SERVICE/CleanerService: проверка очистки json/html/mermaid/plain.

from __future__ import annotations

import pytest

from BACKEND.LLM_SERVICE.cleaner import CleanerService


@pytest.mark.asyncio
async def test_clean_json_strips_fences_and_returns_first_object():
    cleaner = CleanerService()

    raw = """Some intro
```json
{"a": 1, "b": 2}
```
Trailing text
"""
    cleaned = await cleaner.clean(raw, doc_type="json")

    # Должны получить ровно JSON-объект без markdown-ограждений и мусора.
    assert cleaned.strip().startswith("{")
    assert cleaned.strip().endswith("}")
    assert "\"a\"" in cleaned
    assert "\"b\"" in cleaned


@pytest.mark.asyncio
async def test_clean_json_array_with_noise():
    cleaner = CleanerService()

    raw = """noise
```json
[{"id": 1}, {"id": 2}]
```
extra
"""
    cleaned = await cleaner.clean(raw, doc_type="graph_json")

    # Ожидаем, что вернётся именно массив с фигурными скобками внутри.
    assert cleaned.strip().startswith("[")
    assert cleaned.strip().endswith("]")
    assert "\"id\"" in cleaned


@pytest.mark.asyncio
async def test_clean_html_removes_html_fences():
    cleaner = CleanerService()

    raw = """```html
<div>OK</div>
```
"""
    cleaned = await cleaner.clean(raw, doc_type="html")
    assert cleaned == "<div>OK</div>"


@pytest.mark.asyncio
async def test_clean_mermaid_removes_mermaid_fences():
    cleaner = CleanerService()

    raw = """```mermaid
graph TD;
A-->B;
```
"""
    cleaned = await cleaner.clean(raw, doc_type="mermaid")

    # Должен остаться только код графа без ```.
    assert "```" not in cleaned
    assert cleaned.startswith("graph TD;")
    assert "A-->B;" in cleaned


@pytest.mark.asyncio
async def test_clean_plain_fallback_strips_whitespace():
    cleaner = CleanerService()

    raw = "  plain text with spaces  \n"
    cleaned = await cleaner.clean(raw, doc_type="plain")
    assert cleaned == "plain text with spaces"
