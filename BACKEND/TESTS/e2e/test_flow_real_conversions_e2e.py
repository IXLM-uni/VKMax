# Руководство к файлу (TESTS/e2e/test_flow_real_conversions_e2e.py)
# Назначение:
# - E2E-тесты РЕАЛЬНЫХ цепочек конвертаций (без заглушек):
#   * DOCX -> PDF (через mammoth + pdfkit + wkhtmltopdf)
#   * PDF  -> DOCX (через pdf2docx)
#   * DOCX -> Graph JSON (через extract_plain_text + LlmService/OpenRouter + graph_service)
#   * PDF  -> Graph JSON (то же для PDF)
# - Тесты помечены skipif, если окружение не готово (нет зависимостей или LLM-ключа).

from __future__ import annotations

import importlib
import json
import os
import shutil
import uuid
from pathlib import Path

import pytest
from sqlalchemy import select

from BACKEND.DATABASE.session import async_session_factory
from BACKEND.DATABASE.models import Operation, File as FileModel


ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets" / "files"


# -------------------- ДЕТЕКТОРЫ ЗАВИСИМОСТЕЙ --------------------


def _has_mammoth_pdfkit() -> bool:
    try:
        importlib.import_module("mammoth")
        importlib.import_module("pdfkit")
    except ImportError:
        return False

    return shutil.which("wkhtmltopdf") is not None


def _has_pdf2docx() -> bool:
    try:
        importlib.import_module("pdf2docx")
        return True
    except ImportError:
        return False


def _has_pdf_text_deps() -> bool:
    """Нужен PyMuPDF (fitz) для extract_text_from_pdf."""

    try:
        importlib.import_module("fitz")
        return True
    except ImportError:
        return False


def _has_docx_text_deps() -> bool:
    """python-docx или связка mammoth+bs4 для extract_text_from_docx."""

    try:
        importlib.import_module("docx")
        return True
    except ImportError:
        try:
            importlib.import_module("mammoth")
            importlib.import_module("bs4")
            return True
        except ImportError:
            return False


def _has_llm_openrouter() -> bool:
    provider = (os.getenv("VKMAX_LLM_PROVIDER", "deepseek") or "deepseek").lower()
    if provider != "deepseek":
        return False

    key = (
        os.getenv("VKMAX_OPENROUTER_API_KEY")
        or os.getenv("OPENROUTER_API_KEY")
        or os.getenv("VKMAX_DEEPSEEK_API_KEY")
        or os.getenv("DEEPSEEK_API_KEY")
    )
    return bool(key)


# -------------------- DOCX -> PDF --------------------


@pytest.mark.asyncio
@pytest.mark.skipif(not _has_mammoth_pdfkit(), reason="mammoth/pdfkit не установлены")
async def test_real_docx_to_pdf_e2e(http_client):
    """DOCX -> PDF через /upload + /convert.

    Используем реальный invoice.docx из TESTS/assets/files и ожидаем, что
    операция завершится со статусом completed, а выходной файл будет валидным
    PDF (начинается с сигнатуры %PDF-).
    """

    docx_path = ASSETS_DIR / "invoice.docx"
    assert docx_path.exists(), "invoice.docx должен лежать в TESTS/assets/files"

    # 1. Пользователь
    user_payload = {
        "max_id": f"real-docx-pdf-user-{uuid.uuid4()}",
        "name": "Real DOCX->PDF User",
        "metadata": {"role": "real-docx-pdf"},
    }
    resp_user = await http_client.post("/users", json=user_payload)
    assert resp_user.status_code == 200
    user_id = resp_user.json()["id"]

    # 2. Upload DOCX
    with docx_path.open("rb") as f:
        files = {
            "file": (
                "invoice.docx",
                f,
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        }
        data = {"user_id": user_id, "original_format": "docx"}
        resp_upload = await http_client.post("/upload", files=files, data=data)

    assert resp_upload.status_code == 200
    src_file_id = resp_upload.json()["file_id"]

    # 3. convert(docx -> pdf)
    convert_payload = {
        "source_file_id": src_file_id,
        "target_format": "pdf",
        "user_id": user_id,
    }
    resp_convert = await http_client.post("/convert", json=convert_payload)
    assert resp_convert.status_code == 200
    op_id = int(resp_convert.json()["operation_id"])

    # 4. Проверяем операцию и файл результата в БД
    async with async_session_factory() as session:
        res = await session.execute(select(Operation).where(Operation.id == op_id))
        op = res.scalars().first()
        assert op is not None
        await session.refresh(op)
        assert getattr(op, "status") == "completed"
        result_file_id = getattr(op, "result_file_id")
        assert result_file_id is not None

        res_f = await session.execute(select(FileModel).where(FileModel.id == int(result_file_id)))
        fobj = res_f.scalars().first()
        assert fobj is not None
        pdf_path = Path(getattr(fobj, "path"))
        assert pdf_path.exists()

        content = pdf_path.read_bytes()
        assert content.startswith(b"%PDF-"), "Выходной файл должен быть валидным PDF"


# -------------------- PDF -> DOCX --------------------


@pytest.mark.asyncio
@pytest.mark.skipif(not _has_pdf2docx(), reason="pdf2docx не установлен")
async def test_real_pdf_to_docx_e2e(http_client):
    """PDF -> DOCX через /upload + /convert.

    Берём small.pdf из assets и конвертируем в DOCX. Проверяем, что статус
    completed и полученный файл существует и имеет расширение .docx.
    """

    pdf_path = ASSETS_DIR / "small.pdf"
    assert pdf_path.exists(), "small.pdf должен лежать в TESTS/assets/files"

    user_payload = {
        "max_id": f"real-pdf-docx-user-{uuid.uuid4()}",
        "name": "Real PDF->DOCX User",
        "metadata": {"role": "real-pdf-docx"},
    }
    resp_user = await http_client.post("/users", json=user_payload)
    assert resp_user.status_code == 200
    user_id = resp_user.json()["id"]

    with pdf_path.open("rb") as f:
        files = {"file": ("small.pdf", f, "application/pdf")}
        data = {"user_id": user_id, "original_format": "pdf"}
        resp_upload = await http_client.post("/upload", files=files, data=data)

    assert resp_upload.status_code == 200
    src_file_id = resp_upload.json()["file_id"]

    convert_payload = {
        "source_file_id": src_file_id,
        "target_format": "docx",
        "user_id": user_id,
    }
    resp_convert = await http_client.post("/convert", json=convert_payload)
    assert resp_convert.status_code == 200
    op_id = int(resp_convert.json()["operation_id"])

    async with async_session_factory() as session:
        res = await session.execute(select(Operation).where(Operation.id == op_id))
        op = res.scalars().first()
        assert op is not None
        await session.refresh(op)
        assert getattr(op, "status") == "completed"
        result_file_id = getattr(op, "result_file_id")
        assert result_file_id is not None

        res_f = await session.execute(select(FileModel).where(FileModel.id == int(result_file_id)))
        fobj = res_f.scalars().first()
        assert fobj is not None
        docx_path = Path(getattr(fobj, "path"))
        assert docx_path.exists()
        assert docx_path.suffix.lower() == ".docx"
        assert docx_path.stat().st_size > 0


# -------------------- DOCX -> Graph (LLM) --------------------


@pytest.mark.asyncio
@pytest.mark.skipif(not (_has_docx_text_deps() and _has_llm_openrouter()), reason="нет зависимостей для DOCX-текста или LLM")
async def test_real_docx_to_graph_llm_e2e(http_client):
    """DOCX -> Graph JSON через реальный LLM.

    Берём invoice.docx, /convert(target_format="graph") и проверяем, что в
    storage создаётся .graph.json c валидным JSON и массивом nodes.
    """

    docx_path = ASSETS_DIR / "invoice.docx"
    assert docx_path.exists(), "invoice.docx должен лежать в TESTS/assets/files"

    user_payload = {
        "max_id": f"real-docx-graph-user-{uuid.uuid4()}",
        "name": "Real DOCX->Graph User",
        "metadata": {"role": "real-docx-graph"},
    }
    resp_user = await http_client.post("/users", json=user_payload)
    assert resp_user.status_code == 200
    user_id = resp_user.json()["id"]

    with docx_path.open("rb") as f:
        files = {
            "file": (
                "invoice.docx",
                f,
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        }
        data = {"user_id": user_id, "original_format": "docx"}
        resp_upload = await http_client.post("/upload", files=files, data=data)

    assert resp_upload.status_code == 200
    src_file_id = resp_upload.json()["file_id"]

    convert_payload = {
        "source_file_id": src_file_id,
        "target_format": "graph",
        "user_id": user_id,
    }
    resp_convert = await http_client.post("/convert", json=convert_payload)
    assert resp_convert.status_code == 200
    op_id = int(resp_convert.json()["operation_id"])

    async with async_session_factory() as session:
        res = await session.execute(select(Operation).where(Operation.id == op_id))
        op = res.scalars().first()
        assert op is not None
        await session.refresh(op)
        assert getattr(op, "status") == "completed"
        result_file_id = getattr(op, "result_file_id")
        assert result_file_id is not None

        res_f = await session.execute(select(FileModel).where(FileModel.id == int(result_file_id)))
        fobj = res_f.scalars().first()
        assert fobj is not None
        graph_path = Path(getattr(fobj, "path"))
        assert graph_path.exists()

        data = json.loads(graph_path.read_text(encoding="utf-8"))
        assert isinstance(data, dict)
        assert "nodes" in data and isinstance(data["nodes"], list)
        assert "edges" in data
        assert "meta" in data and isinstance(data["meta"], dict)


# -------------------- PDF -> Graph (LLM) --------------------


@pytest.mark.asyncio
@pytest.mark.skipif(not (_has_pdf_text_deps() and _has_llm_openrouter()), reason="нет зависимостей для PDF-текста или LLM")
async def test_real_pdf_to_graph_llm_e2e(http_client):
    """PDF -> Graph JSON через реальный LLM.

    Берём small.pdf, /convert(target_format="graph") и проверяем, что
    сохраняется .graph.json с валидным JSON-форматом.
    """

    pdf_path = ASSETS_DIR / "small.pdf"
    assert pdf_path.exists(), "small.pdf должен лежать в TESTS/assets/files"

    user_payload = {
        "max_id": f"real-pdf-graph-user-{uuid.uuid4()}",
        "name": "Real PDF->Graph User",
        "metadata": {"role": "real-pdf-graph"},
    }
    resp_user = await http_client.post("/users", json=user_payload)
    assert resp_user.status_code == 200
    user_id = resp_user.json()["id"]

    with pdf_path.open("rb") as f:
        files = {"file": ("small.pdf", f, "application/pdf")}
        data = {"user_id": user_id, "original_format": "pdf"}
        resp_upload = await http_client.post("/upload", files=files, data=data)

    assert resp_upload.status_code == 200
    src_file_id = resp_upload.json()["file_id"]

    convert_payload = {
        "source_file_id": src_file_id,
        "target_format": "graph",
        "user_id": user_id,
    }
    resp_convert = await http_client.post("/convert", json=convert_payload)
    assert resp_convert.status_code == 200
    op_id = int(resp_convert.json()["operation_id"])

    async with async_session_factory() as session:
        res = await session.execute(select(Operation).where(Operation.id == op_id))
        op = res.scalars().first()
        assert op is not None
        await session.refresh(op)
        assert getattr(op, "status") == "completed"
        result_file_id = getattr(op, "result_file_id")
        assert result_file_id is not None

        res_f = await session.execute(select(FileModel).where(FileModel.id == int(result_file_id)))
        fobj = res_f.scalars().first()
        assert fobj is not None
        graph_path = Path(getattr(fobj, "path"))
        assert graph_path.exists()

        data = json.loads(graph_path.read_text(encoding="utf-8"))
        assert isinstance(data, dict)
        assert "nodes" in data and isinstance(data["nodes"], list)
        assert "edges" in data
        assert "meta" in data and isinstance(data["meta"], dict)
