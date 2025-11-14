# Руководство к файлу
# Назначение: сборка PDF-книги из сохранённого минимального HTML-контента, группировка по доменам/поддоменам и путям.
# Этап: базовая реализация на ReportLab (быстро и без внешних бинарников). Обновляйте комментарий при изменениях.

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import orjson
import tldextract
from bs4 import BeautifulSoup  # type: ignore
from html import escape as html_escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    PageBreak,
    Preformatted,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from webparser.utils.url import url_to_content_path


@dataclass
class PdfBookConfig:
    page_size: tuple = A4
    left_margin_mm: float = 18
    right_margin_mm: float = 18
    top_margin_mm: float = 18
    bottom_margin_mm: float = 18


class PdfBookBuilder:
    """Собирает PDF-книгу из graph.json и каталога контента."""

    def __init__(self, cfg: Optional[PdfBookConfig] = None) -> None:
        self.cfg = cfg or PdfBookConfig()
        self._setup_fonts()
        self.styles = self._prepare_styles()

    def _setup_fonts(self) -> None:
        """Регистрирует Unicode-шрифты, если доступны, и выбирает имена для стилей."""
        # Значения по умолчанию (ограниченная латиница)
        self._font_regular = "Helvetica"
        self._font_bold = "Helvetica-Bold"
        self._font_mono = "Courier"

        # Часто доступные пути на Linux
        candidates = {
            "DejaVuSans": [
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "/usr/local/share/fonts/DejaVuSans.ttf",
            ],
            "DejaVuSans-Bold": [
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                "/usr/local/share/fonts/DejaVuSans-Bold.ttf",
            ],
            "DejaVuSansMono": [
                "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
                "/usr/local/share/fonts/DejaVuSansMono.ttf",
            ],
        }

        registered = {}
        for name, paths in candidates.items():
            for p in paths:
                fp = Path(p)
                if fp.exists():
                    try:
                        pdfmetrics.registerFont(TTFont(name, str(fp)))
                        registered[name] = True
                        break
                    except Exception:
                        continue

        if registered.get("DejaVuSans"):
            self._font_regular = "DejaVuSans"
        if registered.get("DejaVuSans-Bold"):
            self._font_bold = "DejaVuSans-Bold"
        if registered.get("DejaVuSansMono"):
            self._font_mono = "DejaVuSansMono"

    def _prepare_styles(self) -> Dict[str, ParagraphStyle]:
        ss = getSampleStyleSheet()
        styles: Dict[str, ParagraphStyle] = {}
        styles["title"] = ParagraphStyle(
            "title",
            parent=ss["Heading1"],
            fontSize=18,
            fontName=self._font_bold,
            spaceAfter=6,
        )
        styles["h1"] = ParagraphStyle("h1", parent=ss["Heading2"], fontSize=16, spaceBefore=10, spaceAfter=4, fontName=self._font_bold)
        styles["h2"] = ParagraphStyle("h2", parent=ss["Heading3"], fontSize=14, spaceBefore=10, spaceAfter=4, fontName=self._font_bold)
        styles["h3"] = ParagraphStyle("h3", parent=ss["Heading4"], fontSize=12, spaceBefore=8, spaceAfter=3, fontName=self._font_bold)
        styles["p"] = ParagraphStyle("p", parent=ss["BodyText"], fontSize=10, leading=14, spaceAfter=4, fontName=self._font_regular)
        styles["blockquote"] = ParagraphStyle(
            "blockquote",
            parent=styles["p"],
            leftIndent=12,
            textColor=colors.gray,
        )
        styles["bullet"] = ParagraphStyle(
            "bullet",
            parent=styles["p"],
            leftIndent=12,
            bulletIndent=0,
        )
        styles["pre"] = ParagraphStyle(
            "pre",
            parent=styles["p"],
            fontName=self._font_mono,
            leading=12,
            backColor=colors.whitesmoke,
            leftIndent=6,
        )
        return styles

    @staticmethod
    def _fqdn_and_segments(url: str) -> Tuple[str, List[str]]:
        p = tldextract.extract(url)
        apex = p.top_domain_under_public_suffix or p.registered_domain or p.fqdn
        subs = p.subdomain.split(".") if p.subdomain else []
        fqdn = apex if not subs else f"{p.subdomain}.{apex}"
        path = url.split("//", 1)[-1].split("/", 1)[1] if "/" in url.split("//", 1)[-1] else ""
        segments = [seg for seg in path.split("/") if seg]
        return fqdn, segments

    @staticmethod
    def _load_nodes(graph_json: Path) -> List[str]:
        data = orjson.loads(graph_json.read_bytes())
        nodes = data.get("nodes", [])
        # иногда edges могут содержать узлы, отсутствующие в nodes — синхронизируем
        edges = data.get("edges", [])
        extra = []
        for s, d in edges:
            if s not in nodes:
                extra.append(s)
            if d not in nodes:
                extra.append(d)
        nodes = list(dict.fromkeys(nodes + extra))
        return nodes

    @staticmethod
    def _read_minimal_html(url: str, content_dir: Path) -> Optional[str]:
        p = url_to_content_path(url, content_dir)
        return p.read_text(encoding="utf-8") if p.exists() else None

    def _html_to_flowables(self, minimal_html: str) -> List:
        # Используем минимальный набор тегов, который мы сами и генерируем
        soup = BeautifulSoup(minimal_html, "html.parser")
        article = soup.find("article") or soup.body or soup
        flows: List = []
        for el in article.children:
            if getattr(el, "name", None) is None:
                continue
            name = el.name.lower()
            raw_txt = el.get_text(" ").strip()
            # Экранируем спецсимволы, чтобы ReportLab не пытался интерпретировать
            # случайные подстроки как разметку (<a style=...> и т.п.).
            txt = html_escape(raw_txt)
            if not txt:
                continue
            if name in ("h1",):
                flows.append(Paragraph(html_escape(txt), self.styles["h1"]))
            elif name in ("h2",):
                flows.append(Paragraph(html_escape(txt), self.styles["h2"]))
            elif name in ("h3", "h4", "h5", "h6"):
                flows.append(Paragraph(html_escape(txt), self.styles["h3"]))
            elif name in ("p"):
                flows.append(Paragraph(html_escape(txt), self.styles["p"]))
            elif name in ("blockquote",):
                flows.append(Paragraph(html_escape(txt), self.styles["blockquote"]))
            elif name in ("pre", "code"):
                flows.append(Preformatted(html_escape(txt), self.styles["pre"]))
            elif name in ("ul", "ol"):
                for li in el.find_all("li", recursive=False):
                    flows.append(Paragraph(li.get_text(" ").strip(), self.styles["bullet"], bulletText="• "))
            else:
                flows.append(Paragraph(txt, self.styles["p"]))
        return flows

    def build(self, out_pdf: Path, graph_json: Path, content_dir: Path, site_url: Optional[str] = None) -> None:
        # Загружаем список URL и фильтруем по сайту (если задан)
        urls = self._load_nodes(graph_json)
        if site_url:
            site_fqdn, _ = self._fqdn_and_segments(site_url)
            filtered: List[str] = []
            for u in urls:
                fqdn, _ = self._fqdn_and_segments(u)
                if fqdn.endswith(site_fqdn):
                    filtered.append(u)
            urls = filtered

        # Группировка: {fqdn: {first: {second: [urls]}}}
        by_fqdn: Dict[str, Dict[str, Dict[str, List[str]]]] = {}
        for u in urls:
            fqdn, segs = self._fqdn_and_segments(u)
            first = segs[0] if segs else "_root"
            second = segs[1] if len(segs) > 1 else "_"
            by_fqdn.setdefault(fqdn, {}).setdefault(first, {}).setdefault(second, []).append(u)

        # Документ
        doc = SimpleDocTemplate(
            str(out_pdf),
            pagesize=self.cfg.page_size,
            leftMargin=self.cfg.left_margin_mm * mm,
            rightMargin=self.cfg.right_margin_mm * mm,
            topMargin=self.cfg.top_margin_mm * mm,
            bottomMargin=self.cfg.bottom_margin_mm * mm,
            title="WebParser Book",
        )

        story: List = []

        # Заголовок книги: если задан site_url, использум его FQDN
        if site_url:
            site_fqdn, _ = self._fqdn_and_segments(site_url)
            book_title = f"Книга сайта {site_fqdn}"
        else:
            book_title = "Книга ссылок и контента"

        # Крышка
        story.append(Paragraph(book_title, self.styles["title"]))
        story.append(Spacer(1, 6))

        # Оглавление (простое): перечислим FQDN
        story.append(Paragraph("Оглавление", self.styles["h1"]))

        # Подсчёт количества страниц по каждому fqdn
        fqdn_counts: Dict[str, int] = {}
        for fqdn, first_map in by_fqdn.items():
            total = 0
            for second_map in first_map.values():
                for urls_list in second_map.values():
                    total += len(urls_list)
            fqdn_counts[fqdn] = total

        for fqdn in sorted(by_fqdn.keys()):
            cnt = fqdn_counts.get(fqdn, 0)
            story.append(Paragraph(f"• {fqdn} — {cnt} страниц", self.styles["p"]))
        story.append(PageBreak())

        # Основные главы
        for fqdn in sorted(by_fqdn.keys()):
            story.append(Paragraph(fqdn, self.styles["h1"]))
            story.append(Spacer(1, 4))
            first_map = by_fqdn[fqdn]
            for first in sorted(first_map.keys()):
                if first != "_root":
                    story.append(Paragraph(f"/{first}", self.styles["h2"]))
                second_map = first_map[first]
                for second in sorted(second_map.keys()):
                    if second != "_":
                        story.append(Paragraph(f"/{first}/{second}", self.styles["h3"]))
                    for u in sorted(second_map[second]):
                        html = self._read_minimal_html(u, content_dir)
                        if not html:
                            continue
                        # заголовок страницы
                        story.append(Paragraph(u, self.styles["p"]))
                        story.extend(self._html_to_flowables(html))
                        story.append(Spacer(1, 6))
            story.append(PageBreak())

        # Нумерация страниц
        def _add_page_number(canvas, document):  # type: ignore[override]
            page_num = canvas.getPageNumber()
            txt = f"Стр. {page_num}"
            canvas.setFont(self._font_regular, 8)
            canvas.drawRightString(
                document.pagesize[0] - 15 * mm,
                10 * mm,
                txt,
            )

        doc.build(story, onFirstPage=_add_page_number, onLaterPages=_add_page_number)
