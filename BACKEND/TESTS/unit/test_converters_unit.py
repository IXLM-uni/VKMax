# Руководство к файлу (TESTS/unit/test_converters_unit.py)
# Назначение:
# - Unit-тесты чистых функций из CONVERT/converters.py без реальных файлов и внешних зависимостей.

from __future__ import annotations

import pytest

from BACKEND.CONVERT.converters import (
    _normalize_fmt,
    _limit_words,
    extract_plain_text,
    ConversionError,
)


def test_normalize_fmt_strips_dot_and_lowercases():
    assert _normalize_fmt(".PDF") == "pdf"
    assert _normalize_fmt(" Docx ") == "docx"


def test_limit_words_truncates_long_text():
    text = "one two three four five"
    assert _limit_words(text, max_words=3) == "one two three"
    assert _limit_words(text, max_words=10) == text


def test_extract_plain_text_unsupported_format_raises():
    # Для неподдерживаемого формата функция сразу кидает ConversionError,
    # не пытаясь читать файл с диска.
    with pytest.raises(ConversionError):
        extract_plain_text("dummy-path", input_format="txt")
