# Руководство к файлу (CONVERT/__init__.py)
# Назначение:
# - Объявляет пакет VKMax.BACKEND.CONVERT и экспортирует основные сущности
#   конвертеров и сервисов (конвертация, графы, WebParser, логирование).

from __future__ import annotations

from .converters import (
    ConversionError,
    ConversionResult,
    SUPPORTED_INPUT_FORMATS,
    SUPPORTED_OUTPUT_FORMATS,
    convert_docx_to_pdf,
    convert_pdf_to_docx,
    convert_docx_to_docx,
    convert_pdf_to_pdf,
    extract_text_from_docx,
    extract_text_from_pdf,
    extract_plain_text,
)
from .conversion_service import run_file_conversion
from .graph_service import generate_graph_for_operation
from .webparser_service import (
    enqueue_website_job,
    get_website_status,
    build_website_preview,
    search_site_graph,
    generate_site_pdf_from_bundle,
)
from .logging_config import setup_logging

__all__ = [
    "ConversionError",
    "ConversionResult",
    "SUPPORTED_INPUT_FORMATS",
    "SUPPORTED_OUTPUT_FORMATS",
    "convert_docx_to_pdf",
    "convert_pdf_to_docx",
    "convert_docx_to_docx",
    "convert_pdf_to_pdf",
    "extract_text_from_docx",
    "extract_text_from_pdf",
    "extract_plain_text",
    "run_file_conversion",
    "generate_graph_for_operation",
    "enqueue_website_job",
    "get_website_status",
    "build_website_preview",
    "search_site_graph",
    "generate_site_pdf_from_bundle",
    "setup_logging",
]
