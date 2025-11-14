# Руководство к файлу (LLM_SERVICE/cleaner.py)
# Назначение:
# - Сервис очистки и нормализации текста, возвращаемого LLM.
# - Поддерживает doc_type: json, json_reasons, graph_json, html, plain.

from __future__ import annotations

from typing import Dict


class CleanerService:
    """Сервис для приведения текста к нужному формату.

    Поддерживает разные *doc_type*:
    - ``json`` / ``json_reasons`` / ``graph_json`` — вырезает markdown-ограждения и берёт первую JSON-структуру.
    - ``html`` — удаляет ```html ограждения.
    - иначе — тривиальная очистка (`plain`).
    """

    _DISPATCH_MAP: Dict[str, str] = {
        "json": "_clean_json",
        "json_reasons": "_clean_json",
        "graph_json": "_clean_json",
        "html": "_clean_html",
        "mermaid": "_clean_mermaid",
    }

    async def clean(self, text: str, doc_type: str) -> str:
        """Асинхронный диспетчер очистки."""

        method_name = self._DISPATCH_MAP.get(doc_type.lower(), "_clean_plain")
        cleaner_fn = getattr(self, method_name)
        return cleaner_fn(text)

    # ------------------------------------------------------------------
    # Приватные реализации
    # ------------------------------------------------------------------

    def _clean_json(self, text: str) -> str:
        """Удаляет markdown-ограждения и берёт первую JSON-структуру."""

        import re
        from typing import Optional

        cleaned = re.sub(r"```(?:json)?", "", text, flags=re.IGNORECASE).strip()

        start_obj = cleaned.find("{")
        start_arr = cleaned.find("[")
        if start_obj == -1 and start_arr == -1:
            return cleaned

        start_idx = (
            start_obj
            if start_obj != -1 and (start_obj < start_arr or start_arr == -1)
            else start_arr
        )

        stack: list[str] = []
        end_idx: Optional[int] = None
        for i, ch in enumerate(cleaned[start_idx:], start=start_idx):
            if ch in "[{":
                stack.append(ch)
            elif ch in "]}":
                if not stack:
                    break
                stack.pop()
                if not stack:
                    end_idx = i + 1
                    break

        return cleaned[start_idx:end_idx] if end_idx else cleaned[start_idx:]

    def _clean_html(self, text: str) -> str:
        import re

        cleaned = re.sub(r"```(?:html)?", "", text, flags=re.IGNORECASE).strip()
        return cleaned

    def _clean_mermaid(self, text: str) -> str:
        """Удаляет ```mermaid или ``` и возвращает тело mermaid-графа."""

        import re

        cleaned = re.sub(r"```(?:mermaid)?", "", text, flags=re.IGNORECASE).strip()
        cleaned = cleaned.replace("```", "").strip()
        return cleaned

    def _clean_plain(self, text: str) -> str:
        return text.strip()

