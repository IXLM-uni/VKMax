# Руководство к файлу
# Назначение: извлечение основного текстового контента из HTML и построение минимальной HTML-разметки.
# Этап: расширенная реализация. Поддерживает режим text_only (только h1–h6 и p без списков/цитат/кода).
# Обновляйте комментарий при изменениях.

from __future__ import annotations

from html import escape
from typing import List, Optional

from selectolax.parser import HTMLParser, Node


REMOVABLE_TAGS = {
    "script",
    "style",
    "noscript",
    "template",
    "svg",
    "canvas",
    "iframe",
    "object",
    "embed",
    "form",
    "figure",
    "video",
    "audio",
    "header",
    "footer",
    "nav",
    "aside",
}


REMOVABLE_KEYWORDS = (
    "cookie",
    "consent",
    "banner",
    "advert",
    "ad-",
    "promo",
    "subscribe",
    "subscription",
    "modal",
    "popup",
    "share",
    "social",
    "breadcrumbs",
    "breadcrumb",
    "sidebar",
    "menu",
    "header",
    "footer",
    "signin",
    "login",
    "comments",
)


class ContentExtractor:
    """Извлечение минимальной HTML-разметки из страницы."""

    @staticmethod
    def _prune(tree: HTMLParser) -> Node:
        """Удалить обслуживающие блоки и вернуть узел-контейнер с контентом."""
        body = tree.body
        if body is None:
            return tree.root

        # Удаляем нежелательные теги целиком
        for tag in REMOVABLE_TAGS:
            for n in body.css(tag):
                n.decompose()

        # Удаляем по классам/ID эвристически
        for n in list(body.css("*[class], *[id], *[role]")):
            cls = (n.attributes.get("class") or "").lower()
            nid = (n.attributes.get("id") or "").lower()
            role = (n.attributes.get("role") or "").lower()
            hay = f"{cls} {nid} {role}"
            if any(k in hay for k in REMOVABLE_KEYWORDS):
                n.decompose()

        # Выбираем основной контейнер: article > main > body
        main_node = body.css_first("article") or body.css_first("main") or body
        return main_node

    @staticmethod
    def _text(n: Optional[Node]) -> str:
        if not n:
            return ""
        # selectolax: text(separator) доступен в новых версиях
        try:
            return (n.text(separator=" ") or "").strip()
        except TypeError:
            return (n.text() or "").strip()

    @staticmethod
    def _collect_lists(parent: Node) -> List[str]:
        out: List[str] = []
        for lst in parent.css("ul, ol"):
            items = [escape((li.text(separator=" ") or "").strip()) for li in lst.css("li")]
            if not items:
                continue
            tag = "ol" if lst.tag == "ol" else "ul"
            out.append(f"<{tag}>")
            for it in items:
                out.append(f"  <li>{it}</li>")
            out.append(f"</{tag}>")
        return out

    @staticmethod
    def _collect_blocks(container: Node, *, text_only: bool = False) -> List[str]:
        res: List[str] = []

        # Заголовки
        for htag in ["h1", "h2", "h3", "h4", "h5", "h6"]:
            for h in container.css(htag):
                txt = escape(ContentExtractor._text(h))
                if txt:
                    res.append(f"<{htag}>{txt}</{htag}>")

        # Параграфы
        for p in container.css("p"):
            txt = escape(ContentExtractor._text(p))
            if txt:
                res.append(f"<p>{txt}</p>")

        # Списки (если не text_only)
        if not text_only:
            res.extend(ContentExtractor._collect_lists(container))

        # Блоки кода (если не text_only)
        if not text_only:
            for pre in container.css("pre"):
                code_txt = escape(ContentExtractor._text(pre))
                if code_txt:
                    res.append(f"<pre><code>{code_txt}</code></pre>")

        # Цитаты (если не text_only)
        if not text_only:
            for bq in container.css("blockquote"):
                q = escape(ContentExtractor._text(bq))
                if q:
                    res.append(f"<blockquote>{q}</blockquote>")

        # Если вообще ничего не нашли — вернём плейнтекст body в <p>
        if not res:
            bt = escape(ContentExtractor._text(container))
            if bt:
                res.append(f"<p>{bt}</p>")

        return res

    @staticmethod
    def extract_minimal_html(html: str, *, title: Optional[str] = None, text_only: bool = False) -> str:
        """Собрать минимальную HTML-разметку из текста страницы."""
        tree = HTMLParser(html)
        container = ContentExtractor._prune(tree)
        blocks = ContentExtractor._collect_blocks(container, text_only=text_only)
        title = title or escape(tree.css_first("title").text() if tree.css_first("title") else "")
        # Минимальный документ
        body = "\n".join(blocks)
        return (
            "<html><head><meta charset=\"utf-8\">"
            + (f"<title>{title}</title>" if title else "")
            + "</head><body><article>"
            + body
            + "</article></body></html>"
        )
