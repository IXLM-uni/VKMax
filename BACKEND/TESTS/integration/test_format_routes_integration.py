# Руководство к файлу (TESTS/integration/test_format_routes_integration.py)
# Назначение:
# - Интеграционные тесты для роутера форматов `/formats` и `/supported-conversions`.
# - Проверяют наличие базовых форматов и матрицу конвертаций html->graph.

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_formats_and_output_html_to_graph(http_client):
    """Проверка /formats, /formats/input, /formats/output и /supported-conversions."""

    # /formats
    resp_all = await http_client.get("/formats")
    assert resp_all.status_code == 200
    items = resp_all.json()
    assert isinstance(items, list)

    exts = {i.get("extension") for i in items}
    # seed_formats создаёт хотя бы pdf, docx, url, html, json(graph)
    assert ".pdf" in exts
    assert ".docx" in exts
    assert ".html" in exts
    assert ".json" in exts

    # /formats/input
    resp_input = await http_client.get("/formats/input")
    assert resp_input.status_code == 200
    inputs = resp_input.json()
    assert any(i.get("extension") in (".pdf", "pdf") for i in inputs)
    assert any(i.get("extension") in (".docx", "docx") for i in inputs)

    # /formats/output?input_format=html
    resp_output = await http_client.get("/formats/output", params={"input_format": "html"})
    assert resp_output.status_code == 200
    outs = resp_output.json()
    # Для html должен быть хотя бы один graph-формат (через SUPPORTED_CONVERSIONS)
    assert any(o.get("extension") == ".graph" for o in outs)

    # /supported-conversions
    resp_matrix = await http_client.get("/supported-conversions")
    assert resp_matrix.status_code == 200
    matrix = resp_matrix.json()
    assert set(matrix.keys()) >= {"pdf", "docx", "website", "html"}
