# Руководство к файлу (CONVERT/webparser_service.py)
# Назначение:
# - Сервис интеграции WebParser с БД VKMax (website-операции).
# - Для формата site_bundle выполняет обход сайта через WebParser, собирает
#   JSON-bundle и сохраняет его в File.content, обновляя Operation.
# - Дополнительно строит GraphJson-представление (подграфы) из site_bundle
#   для динамической визуализации и поиска по сайту.

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional, List, Set
from pathlib import Path
import tempfile

import orjson
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from BACKEND.DATABASE.CACHE_MANAGER import ConvertManager, FilesManager
from BACKEND.DATABASE.models import Format, File as FileModel
from BACKEND.WebParser.webparser.core.config import CrawlConfig
from BACKEND.WebParser.webparser.orchestrator.crawler import CrawlerOrchestrator
from BACKEND.WebParser.webparser.graph.exporters import Exporter
from BACKEND.WebParser.webparser.export.site_bundle import build_site_bundle


logger = logging.getLogger("vkmax.webparser")


async def _crawl_site_bundle(url: str) -> bytes:
    logger.info("[webparser_service._crawl_site_bundle] Start crawl url=%s", url)
    with tempfile.TemporaryDirectory(prefix="vkmax_webparser_") as tmpdir:
        tmp_path = Path(tmpdir)
        content_dir = tmp_path / "content"
        graph_json = tmp_path / "graph.json"
        content_dir.mkdir(parents=True, exist_ok=True)

        cfg = CrawlConfig(
            seeds=[url],
            max_depth=2,
            max_pages=2000,
            same_domain_only=True,
            concurrency=10,
            per_host_rps=2.0,
            save_content=True,
            content_dir=str(content_dir),
            content_text_only=True,
        )

        orch = CrawlerOrchestrator(cfg)
        graph = await orch.run()

        Exporter.write_graph_json(graph_json, list(graph.nodes()), graph.edges())

        bundle_bytes = build_site_bundle(
            graph_json=graph_json,
            content_dir=content_dir,
            site_url=url,
            root_url=url,
        )
        return bundle_bytes


def _build_graphjson_from_site_bundle(bundle: Dict[str, Any], query: Optional[str] = None) -> Dict[str, Any]:
    """Построить GraphJson-представление сайта из site_bundle.

    bundle ожидается в формате build_site_bundle: {site_url, crawled_at, pages[], edges[]}.
    Если передан query, строится подграф по найденным страницам + их соседям.
    """

    pages: List[Dict[str, Any]] = list(bundle.get("pages") or [])
    edges_raw: List[List[int]] = list(bundle.get("edges") or [])

    # Фильтрация страниц по запросу (по title и text, case-insensitive)
    if query:
        q = query.lower().strip()
        matched_ids: Set[int] = set()
        for p in pages:
            pid = int(p.get("id")) if p.get("id") is not None else None
            if pid is None:
                continue
            title = str(p.get("title") or "").lower()
            text = str(p.get("text") or "").lower()
            if q in title or q in text:
                matched_ids.add(pid)

        # Добавляем 1-hop соседей по рёбрам как контекст
        neighbor_ids: Set[int] = set()
        for s_id, d_id in edges_raw:
            if s_id in matched_ids or d_id in matched_ids:
                neighbor_ids.add(s_id)
                neighbor_ids.add(d_id)

        keep_ids: Set[int] = matched_ids | neighbor_ids
    else:
        keep_ids = {int(p.get("id")) for p in pages if p.get("id") is not None}

    # Узлы графа
    nodes = []
    keep_ids_str: Set[str] = set()
    for p in pages:
        pid_raw = p.get("id")
        if pid_raw is None:
            continue
        pid = int(pid_raw)
        if pid not in keep_ids:
            continue
        node_id = str(pid)
        keep_ids_str.add(node_id)
        label = p.get("title") or p.get("url") or f"Page {pid}"
        # В data кладём весь объект страницы, чтобы фронт мог использовать текст/мета
        nodes.append(
            {
                "id": node_id,
                "label": str(label),
                "type": "page",
                "data": p,
            }
        )

    # Рёбра только между выбранными страницами
    edges = []
    for s_id, d_id in edges_raw:
        s = str(s_id)
        d = str(d_id)
        if s in keep_ids_str and d in keep_ids_str:
            edges.append(
                {
                    "id": f"{s}->{d}",
                    "source": s,
                    "target": d,
                    "label": "link",
                    "type": "link",
                    "data": {
                        "source_id": s_id,
                        "target_id": d_id,
                    },
                }
            )

    meta: Dict[str, Any] = dict(bundle.get("meta") or {})
    meta.setdefault("site_url", bundle.get("site_url"))
    meta.setdefault("crawled_at", bundle.get("crawled_at"))
    if query:
        meta["query"] = query

    return {
        "nodes": nodes,
        "edges": edges,
        "meta": meta,
    }


def _build_pdf_from_site_bundle(bundle: Dict[str, Any], out_pdf: Path) -> None:
    """Собрать PDF-книгу сайта из site_bundle.

    Использует только поля title/url/text из pages без HTML. Структура:
    - Заголовок: site_url (или generic подпись).
    - Каждая страница bundle.pages -> раздел: подзаголовок = title или url,
      затем plain-text содержимое.
    """

    site_url = str(bundle.get("site_url") or "")
    pages: List[Dict[str, Any]] = list(bundle.get("pages") or [])

    # Подготовка шрифтов: если доступны DejaVuSans/DejaVuSans-Bold, используем их
    # для корректного отображения UTF-8 (кириллица и др.). Иначе остаёмся на
    # стандартных Helvetica.
    font_regular = "Helvetica"
    font_bold = "Helvetica-Bold"

    candidates = {
        "DejaVuSans": [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/local/share/fonts/DejaVuSans.ttf",
        ],
        "DejaVuSans-Bold": [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/local/share/fonts/DejaVuSans-Bold.ttf",
        ],
    }

    registered: Dict[str, bool] = {}
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
        font_regular = "DejaVuSans"
    if registered.get("DejaVuSans-Bold"):
        font_bold = "DejaVuSans-Bold"

    # Готовим стили (минимальный набор, чтобы не дублировать PdfBookBuilder полностью)
    ss = getSampleStyleSheet()
    style_title: ParagraphStyle = ParagraphStyle(
        "site_title",
        parent=ss["Heading1"],
        fontSize=18,
        spaceAfter=6,
        fontName=font_bold,
    )
    style_h1: ParagraphStyle = ParagraphStyle(
        "page_title",
        parent=ss["Heading2"],
        fontSize=14,
        spaceBefore=10,
        spaceAfter=2,
        fontName=font_bold,
    )
    style_url: ParagraphStyle = ParagraphStyle(
        "page_url",
        parent=ss["BodyText"],
        fontSize=8,
        leading=10,
        spaceAfter=4,
        fontName=font_regular,
    )
    style_p: ParagraphStyle = ParagraphStyle(
        "page_text",
        parent=ss["BodyText"],
        fontSize=10,
        leading=14,
        spaceAfter=4,
        fontName=font_regular,
    )

    doc = SimpleDocTemplate(
        str(out_pdf),
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title=(site_url or "Site Bundle Book"),
    )

    story: List = []

    # Титульная страница
    title_text = site_url or "Книга сайта"
    story.append(Paragraph(title_text, style_title))
    story.append(Spacer(1, 12))

    # Страницы сайта в порядке id
    pages_sorted = sorted(pages, key=lambda p: int(p.get("id") or 0))
    for idx, page in enumerate(pages_sorted):
        if idx > 0:
            story.append(PageBreak())
        raw_title = page.get("title") or page.get("url") or f"Page {page.get('id')}"
        page_url = page.get("url") or ""
        text = str(page.get("text") or "").strip()

        story.append(Paragraph(str(raw_title), style_h1))
        if page_url:
            story.append(Paragraph(str(page_url), style_url))
        story.append(Spacer(1, 6))

        if text:
            # Простейшая разбивка на абзацы по пустым строкам
            paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
            for para in paragraphs:
                story.append(Paragraph(para, style_p))
        else:
            story.append(Paragraph("(нет текста)", style_p))

    doc.build(story)


async def search_site_graph(
    session: AsyncSession,
    *,
    file_id: int,
    query: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Построить GraphJson-подграф по site_bundle-файлу *file_id*.

    Ожидается, что File.format указывает на формат type="site_bundle", а content
    содержит сериализованный JSON-пакет в формате build_site_bundle.
    """

    fm = FilesManager(session)
    obj = await fm.get_file(file_id)
    if obj is None:
        logger.error("[webparser_service.search_site_graph] file_id=%s not found", file_id)
        return None

    fmt_id = getattr(obj, "format_id", None)
    if fmt_id is None:
        logger.error("[webparser_service.search_site_graph] file_id=%s has no format_id", file_id)
        return None

    try:
        res = await session.execute(select(Format).where(Format.id == int(fmt_id)))
        fmt = res.scalars().first()
    except Exception as exc:  # noqa: WPS430
        logger.exception(
            "[webparser_service.search_site_graph] Failed to load format id=%s for file_id=%s: %s",
            fmt_id,
            file_id,
            exc,
        )
        return None

    if fmt is None or getattr(fmt, "type", None) != "site_bundle":
        logger.error(
            "[webparser_service.search_site_graph] file_id=%s has unsupported format type=%s (expected site_bundle)",
            file_id,
            getattr(fmt, "type", None) if fmt is not None else None,
        )
        return None

    content = getattr(obj, "content", None)
    if not content:
        logger.error("[webparser_service.search_site_graph] file_id=%s has empty content", file_id)
        return None

    try:
        bundle = orjson.loads(bytes(content))
    except Exception as exc:  # noqa: WPS430
        logger.exception(
            "[webparser_service.search_site_graph] Failed to parse site_bundle JSON for file_id=%s: %s",
            file_id,
            exc,
        )
        return None

    graph = _build_graphjson_from_site_bundle(bundle, query=query)
    return graph


async def generate_site_pdf_from_bundle(
    session: AsyncSession,
    *,
    file_id: int,
    storage_dir: str,
) -> Optional[int]:
    """Сгенерировать PDF-книгу сайта по сохранённому site_bundle-файлу *file_id*.

    - Читает File из БД (ожидается format.type == "site_bundle" и content с JSON).
    - Строит PDF по схеме: заголовок = site_url, разделы = страницы.
    - Сохраняет PDF в storage_dir и создаёт новую запись File формата pdf.
    - Возвращает id созданного файла или None при ошибке.
    """

    fm = FilesManager(session)
    obj: Optional[FileModel] = await fm.get_file(file_id)
    if obj is None:
        logger.error("[webparser_service.generate_site_pdf_from_bundle] file_id=%s not found", file_id)
        return None

    fmt_id = getattr(obj, "format_id", None)
    if fmt_id is None:
        logger.error("[webparser_service.generate_site_pdf_from_bundle] file_id=%s has no format_id", file_id)
        return None

    try:
        res = await session.execute(select(Format).where(Format.id == int(fmt_id)))
        fmt = res.scalars().first()
    except Exception as exc:  # noqa: WPS430
        logger.exception(
            "[webparser_service.generate_site_pdf_from_bundle] Failed to load format id=%s for file_id=%s: %s",
            fmt_id,
            file_id,
            exc,
        )
        return None

    if fmt is None or getattr(fmt, "type", None) != "site_bundle":
        logger.error(
            "[webparser_service.generate_site_pdf_from_bundle] file_id=%s has unsupported format type=%s (expected site_bundle)",
            file_id,
            getattr(fmt, "type", None) if fmt is not None else None,
        )
        return None

    content = getattr(obj, "content", None)
    if not content:
        logger.error("[webparser_service.generate_site_pdf_from_bundle] file_id=%s has empty content", file_id)
        return None

    try:
        bundle = orjson.loads(bytes(content))
    except Exception as exc:  # noqa: WPS430
        logger.exception(
            "[webparser_service.generate_site_pdf_from_bundle] Failed to parse site_bundle JSON for file_id=%s: %s",
            file_id,
            exc,
        )
        return None

    # Определяем формат PDF (по расширению .pdf)
    try:
        res_pdf = await session.execute(
            select(Format).where(Format.file_extension.in_(["pdf", ".pdf"]))
        )
        pdf_fmt = res_pdf.scalars().first()
    except Exception as exc:  # noqa: WPS430
        logger.exception(
            "[webparser_service.generate_site_pdf_from_bundle] Failed to resolve PDF format for file_id=%s: %s",
            file_id,
            exc,
        )
        return None

    if pdf_fmt is None:
        logger.error("[webparser_service.generate_site_pdf_from_bundle] PDF format not found in formats table")
        return None

    filename = f"site-{file_id}.pdf"
    out_path = os.path.join(storage_dir, filename)
    try:
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        _build_pdf_from_site_bundle(bundle, Path(out_path))
    except Exception as exc:  # noqa: WPS430
        logger.exception(
            "[webparser_service.generate_site_pdf_from_bundle] Failed to build PDF for file_id=%s: %s",
            file_id,
            exc,
        )
        return None

    new_file = await fm.create_file(
        user_id=getattr(obj, "user_id", None),
        format_id=int(getattr(pdf_fmt, "id")),
        filename=filename,
        mime_type="application/pdf",
        content_bytes=None,
        path=out_path,
    )

    return int(getattr(new_file, "id")) if new_file is not None else None


async def enqueue_website_job(session: AsyncSession, *, operation_id: int, url: Optional[str] = None) -> None:
    """Заглушка постановки website-операции в очередь.

    В текущем MVP фактической очереди нет: операции создаются в статусе queued,
    а дальнейшая обработка сайта должна быть реализована отдельным воркером.
    Функция оставлена для совместимости и логирования.
    """

    cm = ConvertManager(session)
    logger.info("[webparser_service.enqueue_website_job] Received website op=%s url=%s", operation_id, url)
    try:
        op = await cm.get_operation(operation_id)
    except Exception as exc:  # noqa: WPS430
        logger.exception("[webparser_service.enqueue_website_job] Failed to load operation %s: %s", operation_id, exc)
        return

    if op is None:
        logger.error("[webparser_service.enqueue_website_job] Operation %s not found", operation_id)
        return

    new_format_id = op.get("new_format_id")
    if not new_format_id:
        logger.info(
            "[webparser_service.enqueue_website_job] Operation %s has no new_format_id, leaving status as is",
            operation_id,
        )
        return

    try:
        res = await session.execute(select(Format).where(Format.id == int(new_format_id)))
        fmt = res.scalars().first()
    except Exception as exc:  # noqa: WPS430
        logger.exception(
            "[webparser_service.enqueue_website_job] Failed to load format id=%s for op=%s: %s",
            new_format_id,
            operation_id,
            exc,
        )
        return

    if fmt is None:
        logger.error(
            "[webparser_service.enqueue_website_job] Format id=%s for op=%s not found",
            new_format_id,
            operation_id,
        )
        return

    fmt_type = getattr(fmt, "type", None)
    if fmt_type != "site_bundle":
        logger.info(
            "[webparser_service.enqueue_website_job] Skip non-site_bundle website op=%s format_type=%s",
            operation_id,
            fmt_type,
        )
        return

    if not url:
        logger.error(
            "[webparser_service.enqueue_website_job] site_bundle operation %s has no url, cannot proceed",
            operation_id,
        )
        await cm.update_status(
            operation_id,
            status="failed",
            error_message="url is required for site_bundle website operation",
        )
        return

    logger.info(
        "[webparser_service.enqueue_website_job] Start site_bundle crawl for op=%s url=%s",
        operation_id,
        url,
    )

    try:
        await cm.update_status(operation_id, status="processing")
        bundle_bytes = await _crawl_site_bundle(url)
        fm = FilesManager(session)
        filename = f"site-{operation_id}.site_bundle.json"
        new_file = await fm.create_file(
            user_id=op.get("user_id"),
            format_id=int(new_format_id),
            filename=filename,
            mime_type="application/json",
            content_bytes=bundle_bytes,
            path=None,
        )
        await cm.update_status(
            operation_id,
            status="completed",
            error_message=None,
            result_file_id=int(getattr(new_file, "id")),
        )
        logger.info(
            "[webparser_service.enqueue_website_job] Completed site_bundle op=%s result_file_id=%s",
            operation_id,
            int(getattr(new_file, "id")),
        )
    except Exception as exc:  # noqa: WPS430
        logger.exception(
            "[webparser_service.enqueue_website_job] Failed to process site_bundle op=%s: %s",
            operation_id,
            exc,
        )
        await cm.update_status(
            operation_id,
            status="failed",
            error_message=str(exc),
        )


async def get_website_status(session: AsyncSession, *, operation_id: int) -> Optional[Dict[str, Any]]:
    """Возвращает статус website-операции, обёртка над ConvertManager.get_operation."""

    cm = ConvertManager(session)
    logger.debug("[webparser_service.get_website_status] Get status for op=%s", operation_id)
    try:
        return await cm.get_operation(operation_id)
    except Exception as exc:  # noqa: WPS430
        logger.exception("[webparser_service.get_website_status] Failed to get operation %s: %s", operation_id, exc)
        return None


async def build_website_preview(url: str) -> Dict[str, Any]:
    """MVP-превью сайта.

    Сейчас возвращает простую структуру с title=url. Позже сюда можно добавить
    реальный HTTP-запрос, парсинг title/description/og-тегов и т.п.
    """

    logger.info("[webparser_service.build_website_preview] Build preview for url=%s", url)
    return {
        "title": url,
        "description": None,
        "screenshot_url": None,
        "page_count": None,
    }


__all__ = [
    "enqueue_website_job",
    "get_website_status",
    "build_website_preview",
    "search_site_graph",
    "generate_site_pdf_from_bundle",
]

