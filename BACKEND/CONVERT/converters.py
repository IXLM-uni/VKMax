# Руководство к файлу (CONVERT/converters.py)
# Назначение:
# - Набор чистых Python-конвертеров для VKMax (DOCX/PDF и извлечение текста).
# - Не знает о FastAPI/БД/LLM, работает только с путями к файлам и форматами.
# Важно:
# - Все функции должны быть максимально лёгковесными по памяти.
# - В LLM-пайплайнах извлекается не более 10 000 слов текста.

from __future__ import annotations

import logging
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Set


logger = logging.getLogger(__name__)


SUPPORTED_INPUT_FORMATS: Set[str] = {"docx", "pdf"}
SUPPORTED_OUTPUT_FORMATS: Set[str] = {"docx", "pdf"}


class ConversionError(Exception):
    """Общая ошибка конвертации."""


@dataclass
class ConversionResult:
    """Результат файловой конвертации.

    - input_path / output_path — абсолютные пути к файлам.
    - input_format / output_format — нормализованные расширения: docx/pdf.
    - meta — любые дополнительные данные (количество страниц, время и т.п.).
    """

    input_path: str
    output_path: str
    input_format: str
    output_format: str
    meta: Dict[str, Any] | None = None


# ---------------------------------------------------------------------------
# Вспомогательные функции
# ---------------------------------------------------------------------------


def _normalize_fmt(value: str) -> str:
    v = value.lower().strip()
    if v.startswith("."):
        v = v[1:]
    return v


def _ensure_parent_dir(path: Path) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass


def _limit_words(text: str, max_words: int) -> str:
    if max_words <= 0:
        return ""
    words = text.split()
    if len(words) <= max_words:
        return " ".join(words)
    return " ".join(words[:max_words])


# ---------------------------------------------------------------------------
# Простые файловые конвертации (копирование/смена формата)
# ---------------------------------------------------------------------------


def convert_docx_to_docx(input_path: str, output_path: Optional[str] = None) -> ConversionResult:
    """Базовый DOCX→DOCX: копирование или минимальная нормализация.

    Для MVP выполняется только копирование файла в новое место.
    """

    src = Path(input_path).resolve()
    if not src.exists():
        raise ConversionError(f"DOCX not found: {src}")

    if output_path is None:
        output_path = str(src.with_name(src.stem + "-copy.docx"))
    dst = Path(output_path).resolve()
    _ensure_parent_dir(dst)

    shutil.copyfile(src, dst)

    return ConversionResult(
        input_path=str(src),
        output_path=str(dst),
        input_format="docx",
        output_format="docx",
        meta={},
    )


def convert_pdf_to_pdf(input_path: str, output_path: Optional[str] = None) -> ConversionResult:
    """Базовый PDF→PDF: копирование без изменений содержимого.

    Полезно для нормализации пути/имени файла.
    """

    src = Path(input_path).resolve()
    if not src.exists():
        raise ConversionError(f"PDF not found: {src}")

    if output_path is None:
        output_path = str(src.with_name(src.stem + "-copy.pdf"))
    dst = Path(output_path).resolve()
    _ensure_parent_dir(dst)

    shutil.copyfile(src, dst)

    return ConversionResult(
        input_path=str(src),
        output_path=str(dst),
        input_format="pdf",
        output_format="pdf",
        meta={},
    )


def convert_docx_to_pdf(input_path: str, output_path: Optional[str] = None) -> ConversionResult:
    """DOCX→PDF через DOCX→HTML→PDF (если доступны зависимости).

    Использует:
      - mammoth для получения HTML из DOCX;
      - pdfkit + wkhtmltopdf для конвертации HTML в PDF.

    Если нужные библиотеки отсутствуют, кидает ConversionError.
    """

    src = Path(input_path).resolve()
    if not src.exists():
        raise ConversionError(f"DOCX not found: {src}")

    try:
        import mammoth  # type: ignore
    except Exception as exc:  # pragma: no cover - зависимость может отсутствовать
        raise ConversionError("mammoth is required for DOCX→HTML conversion") from exc

    try:
        import pdfkit  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise ConversionError("pdfkit is required for HTML→PDF conversion") from exc

    if output_path is None:
        output_path = str(src.with_suffix(".pdf"))
    dst = Path(output_path).resolve()
    _ensure_parent_dir(dst)

    # DOCX → HTML (в памяти)
    with src.open("rb") as f:
        html_result = mammoth.convert_to_html(f)
    html_body = html_result.value  # type: ignore[assignment]

    # Оборачиваем в полноценный HTML-документ с charset UTF-8,
    # чтобы pdfkit/wkhtmltopdf корректно обрабатывали кириллицу.
    html = (
        "<!DOCTYPE html>\n"
        "<html><head><meta charset=\"utf-8\"></head><body>"
        f"{html_body}"
        "</body></html>"
    )

    # HTML → PDF
    try:
        pdfkit.from_string(html, str(dst), options={"encoding": "UTF-8"})
    except Exception as exc:  # pragma: no cover
        raise ConversionError(f"Failed to render PDF via pdfkit: {exc}") from exc

    return ConversionResult(
        input_path=str(src),
        output_path=str(dst),
        input_format="docx",
        output_format="pdf",
        meta={"html_length": len(html)},
    )


def convert_pdf_to_docx(input_path: str, output_path: Optional[str] = None) -> ConversionResult:
    """PDF→DOCX через pdf2docx.

    Если библиотека pdf2docx недоступна, кидает ConversionError.
    """

    src = Path(input_path).resolve()
    if not src.exists():
        raise ConversionError(f"PDF not found: {src}")

    try:
        from pdf2docx import Converter  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise ConversionError("pdf2docx is required for PDF→DOCX conversion") from exc

    if output_path is None:
        output_path = str(src.with_suffix(".docx"))
    dst = Path(output_path).resolve()
    _ensure_parent_dir(dst)

    try:
        cv = Converter(str(src))
        cv.convert(str(dst))
        cv.close()
    except Exception as exc:  # pragma: no cover
        raise ConversionError(f"Failed to convert PDF to DOCX: {exc}") from exc

    return ConversionResult(
        input_path=str(src),
        output_path=str(dst),
        input_format="pdf",
        output_format="docx",
        meta={},
    )


# ---------------------------------------------------------------------------
# Извлечение текста для LLM (до 10 000 слов)
# ---------------------------------------------------------------------------


def extract_text_from_docx(input_path: str, max_words: int = 10_000) -> str:
    """Извлекает plain-text из DOCX и обрезает до max_words слов.

    Предпочитает python-docx; если он недоступен, пытается использовать mammoth
    и вытащить текст из HTML.
    """

    src = Path(input_path).resolve()
    if not src.exists():
        raise ConversionError(f"DOCX not found: {src}")

    text: str | None = None

    # Вариант 1: python-docx
    try:
        import docx  # type: ignore

        doc = docx.Document(str(src))
        paragraphs: Iterable[str] = (p.text for p in doc.paragraphs)
        text = "\n".join(p for p in paragraphs if p)
    except Exception:
        text = None

    # Вариант 2: mammoth → HTML → plain
    if not text:
        try:
            import mammoth  # type: ignore
            from bs4 import BeautifulSoup  # type: ignore

            with src.open("rb") as f:
                html_result = mammoth.convert_to_html(f)
            html = html_result.value  # type: ignore[assignment]
            soup = BeautifulSoup(html, "html.parser")
            text = soup.get_text(" ")
        except Exception as exc:
            raise ConversionError(f"Failed to extract text from DOCX: {exc}") from exc

    return _limit_words(text, max_words)


def extract_text_from_pdf(input_path: str, max_words: int = 10_000) -> str:
    """Извлекает plain-text из PDF постранично и обрезает до max_words слов.

    Использует PyMuPDF (fitz). Если библиотека недоступна — ConversionError.
    """

    src = Path(input_path).resolve()
    if not src.exists():
        raise ConversionError(f"PDF not found: {src}")

    try:
        import fitz  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise ConversionError("PyMuPDF (fitz) is required for PDF text extraction") from exc

    parts: list[str] = []
    words_count = 0
    try:
        doc = fitz.open(str(src))
    except Exception as exc:  # pragma: no cover
        raise ConversionError(f"Failed to open PDF: {exc}") from exc

    try:
        for page in doc:
            if words_count >= max_words:
                break
            try:
                page_text = page.get_text("text") or ""
            except Exception:
                continue
            if not page_text:
                continue
            page_words = page_text.split()
            if not page_words:
                continue
            remaining = max_words - words_count
            if len(page_words) > remaining:
                page_words = page_words[:remaining]
            parts.append(" ".join(page_words))
            words_count += len(page_words)
    finally:
        try:
            doc.close()
        except Exception:
            pass

    if not parts:
        return ""
    return " ".join(parts)


def extract_plain_text(input_path: str, input_format: str, max_words: int = 10_000) -> str:
    """Унифицированный вход для извлечения текста из DOCX/PDF.

    *input_format* — расширение или логическое имя ("docx"/"pdf").
    """

    fmt = _normalize_fmt(input_format)
    if fmt == "docx":
        return extract_text_from_docx(input_path, max_words=max_words)
    if fmt == "pdf":
        return extract_text_from_pdf(input_path, max_words=max_words)
    raise ConversionError(f"Unsupported input format for text extraction: {input_format}")
