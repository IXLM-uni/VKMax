# Руководство к файлу (CONVERT/graph_service.py)
# Назначение:
# - Сервис генерации доменного JSON-графа по документу (DOCX/PDF) через LLM.
# - Работает поверх БД (AsyncSession, ConvertManager, FilesManager) и
#   LLM_SERVICE (LlmService, CleanerService, ValidatorService, DocumentGenerator).
# - Реализует двухшаговый пайплайн: LLM сначала возвращает упрощённый JSON-outline
#   (entities/relations/meta), а затем Python-функция преобразует его в итоговый
#   graph JSON (nodes/edges/meta).
# Важно:
# - Не зависит от FastAPI напрямую, принимает сессию и параметры как аргументы.

from __future__ import annotations

import logging
import json
import os
from pathlib import Path
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .converters import ConversionError, extract_plain_text
from BACKEND.DATABASE.CACHE_MANAGER import ConvertManager, FilesManager
from BACKEND.DATABASE.models import File as FileModel, Format, Operation
from BACKEND.LLM_SERVICE.cleaner import CleanerService
from BACKEND.LLM_SERVICE.document_generator import DocumentGenerator
from BACKEND.LLM_SERVICE.llm_service import LlmService
from BACKEND.LLM_SERVICE.validator import ValidatorService


logger = logging.getLogger("vkmax.convert")


GRAPH_TASK_ID = "graph_from_document"


async def _resolve_format_ext(session: AsyncSession, format_id: Optional[int]) -> Optional[str]:
    if format_id is None:
        return None
    res = await session.execute(select(Format).where(Format.id == int(format_id)))
    f = res.scalars().first()
    if not f:
        return None
    ext = getattr(f, "file_extension") or ""
    return ext.lstrip(".") if isinstance(ext, str) else None


def _build_document_generator() -> DocumentGenerator:
    """Создаёт DocumentGenerator с реестром задач для JSON-графа.

    LLM возвращает доменный JSON-граф (узлы/связи/метаданные) в строгом
    JSON-формате, без markdown-ограждений и лишнего текста. Этот JSON далее
    может быть преобразован во что угодно (React Flow, Mermaid и т.п.) без
    изменения LLM-промпта.
    """

    llm = LlmService()
    cleaner = CleanerService()
    validator = ValidatorService()

    registry = {
        GRAPH_TASK_ID: {
            "doc_type": "json",
            "prompt_template": (
                "Ты — помощник, который строит структурированные графы по тексту документа.\n"
                "Тебе передан текст документа (первые 10 000 слов).\n"
                "Нужно: сначала выделить сущности и связи между ними и вернуть ОДИН JSON-объект\n"
                "простого вида, который потом будет автоматически преобразован в граф.\n"
                "\n"
                "СТРУКТУРА JSON-ОТВЕТА:\n"
                "- top-level ключи: \"entities\", \"relations\", \"meta\".\n"
                "- \"entities\" — список объектов с полями: \"id\", \"name\", \"type\".\n"
                "- \"relations\" — список объектов с полями: \"id\", \"source\", \"target\", \"type\", \"description\".\n"
                "- \"meta\" — объект с метаданными (например, \"source_title\", \"generated_at\").\n"
                "\n"
                "ВАЖНО:\n"
                "- НЕ возвращай поля \"nodes\" и \"edges\" — их построит сервер по твоему JSON.\n"
                "- Верни ОДИН корректный JSON-объект без комментариев и текста до/после.\n"
                "\n"
                "ПРИМЕР 1 (короткий текст):\n"
                "Текст:\n"
                "\"Иван купил ноутбук в магазине Техника+ в Москве.\"\n"
                "Ожидаемый JSON (словами):\n"
                "entities: e1=Иван (person), e2=ноутбук (product), e3=Техника+ (store), e4=Москва (city)\n"
                "relations: r1=(e1 -> e2, type=purchase), r2=(e1 -> e3, type=buys_from), r3=(e3 -> e4, type=located_in)\n"
                "meta: source_title=\"пример 1\", generated_at=\"2025-01-01T00:00:00Z\"\n"
                "\n"
                "ПРИМЕР 2 (инвойс):\n"
                "Текст:\n"
                "\"ООО Ромашка выставило счёт №123 клиенту Иванову И.И. за услуги консалтинга. Сумма 100 000 руб. Срок оплаты до 10.10.2025.\"\n"
                "Ожидаемый JSON (словами):\n"
                "entities: e1=ООО Ромашка (company), e2=счёт №123 (invoice), e3=Иванов И.И. (client), e4=услуги консалтинга (service)\n"
                "relations: r1=(e1 -> e2, type=issues), r2=(e2 -> e3, type=billed_to), r3=(e2 -> e4, type=covers_service)\n"
                "meta: source_title=\"инвойс\", generated_at=\"2025-01-02T00:00:00Z\"\n"
                "\n"
                "Теперь обработай реальный текст документа ниже и верни JSON описанного формата.\n"
                "\n"
                "Текст документа:\n"
                "{document_text}\n"
            ),
        },
    }

    return DocumentGenerator(llm, cleaner, validator, registry=registry)


def _outline_to_graph(data: dict) -> dict:
    """Преобразует упрощённый JSON-outline (entities/relations/meta) в graph JSON.

    Ожидается структура:
      {
        "entities": [ {"id": ..., "name": ..., "type": ...}, ... ],
        "relations": [ {"id": ..., "source": ..., "target": ..., "type": ..., "description": ...}, ... ],
        "meta": { ... }
      }
    """

    entities = data.get("entities") or []
    relations = data.get("relations") or []
    meta = data.get("meta") or {}

    nodes = []
    id_map = {}

    for idx, ent in enumerate(entities, start=1):
        raw_id = ent.get("id")
        name = ent.get("name") or ent.get("title") or f"Entity {idx}"
        ent_type = ent.get("type") or "entity"

        node_id = str(raw_id or f"e{idx}")
        # Маппим как по id, так и по имени (в нижнем регистре), чтобы связи могли
        # ссылаться и так, и так.
        id_map[str(raw_id).lower()] = node_id if raw_id is not None else node_id
        id_map[str(name).lower()] = node_id

        nodes.append(
            {
                "id": node_id,
                "label": str(name),
                "type": str(ent_type),
                "data": ent,
            }
        )

    edges = []
    for idx, rel in enumerate(relations, start=1):
        src_raw = rel.get("source") or rel.get("from")
        tgt_raw = rel.get("target") or rel.get("to")
        src_key = str(src_raw or "").lower()
        tgt_key = str(tgt_raw or "").lower()
        src_id = id_map.get(src_key, str(src_raw or ""))
        tgt_id = id_map.get(tgt_key, str(tgt_raw or ""))

        edge_id = str(rel.get("id") or f"r{idx}")
        edge_type = rel.get("type") or "relation"
        label = rel.get("label") or edge_type

        edges.append(
            {
                "id": edge_id,
                "source": src_id,
                "target": tgt_id,
                "label": str(label),
                "type": str(edge_type),
                "data": rel,
            }
        )

    if "source_title" not in meta:
        meta["source_title"] = str(meta.get("title") or "document")

    return {
        "nodes": nodes,
        "edges": edges,
        "meta": meta,
    }


async def generate_graph_for_operation(
    session: AsyncSession,
    *,
    operation_id: int,
    storage_dir: str,
) -> None:
    """Генерирует JSON-граф для операции *operation_id*.

    Ожидается, что Operation.new_format_id указывает на формат graph/json, а
    Operation.file_id — на исходный DOCX/PDF.
    """

    cm = ConvertManager(session)
    fm = FilesManager(session)

    try:
        op = await cm.get_by_id(Operation, operation_id)  # type: ignore[arg-type]
    except Exception as exc:  # noqa: WPS430
        logger.exception("[graph_service.generate_graph_for_operation] Failed to load operation %s: %s", operation_id, exc)
        return

    if op is None:
        logger.error("[graph_service.generate_graph_for_operation] Operation %s not found", operation_id)
        return

    file_id = getattr(op, "file_id", None)
    new_format_id = getattr(op, "new_format_id", None)

    if file_id is None or new_format_id is None:
        msg = "operation missing file_id or new_format_id"
        logger.error("[graph_service.generate_graph_for_operation] %s", msg)
        await cm.update_status(operation_id, status="failed", error_message=msg)
        return

    logger.info(
        "[graph_service.generate_graph_for_operation] Start operation_id=%s file_id=%s new_format_id=%s",
        operation_id,
        file_id,
        new_format_id,
    )

    src: Optional[FileModel] = await fm.get_file(int(file_id))
    if src is None:
        msg = f"source file {file_id} not found"
        logger.error("[graph_service.generate_graph_for_operation] %s", msg)
        await cm.update_status(operation_id, status="failed", error_message=msg)
        return

    src_path = getattr(src, "path")
    if not src_path or not os.path.exists(src_path):
        msg = f"source file path missing or not exists: {src_path}"
        logger.error("[graph_service.generate_graph_for_operation] %s", msg)
        await cm.update_status(operation_id, status="failed", error_message=msg)
        return

    old_fmt_id = getattr(op, "old_format_id", None)
    src_ext = await _resolve_format_ext(session, old_fmt_id)
    if not src_ext:
        msg = f"cannot resolve source format for graph generation: old_format_id={old_fmt_id}"
        logger.error("[graph_service.generate_graph_for_operation] %s", msg)
        await cm.update_status(operation_id, status="failed", error_message=msg)
        return

    try:
        # 1. Извлекаем текст до 10 000 слов
        text = extract_plain_text(src_path, input_format=src_ext, max_words=10_000)
        logger.info(
            "[graph_service.generate_graph_for_operation] Extracted text for op=%s len(text)~=%s",
            operation_id,
            len(text),
        )

        # 2. Готовим LLM-оркестратор
        doc_gen = _build_document_generator()

        # 3. Запрашиваем упрощённый JSON-outline (entities/relations/meta)
        raw_output = await doc_gen.create_document(GRAPH_TASK_ID, document_text=text)
        if not isinstance(raw_output, str) or not raw_output.strip():
            raise RuntimeError("LLM returned empty graph outline")

        raw_output = raw_output.strip()
        try:
            outline_data = json.loads(raw_output)
        except Exception as exc:  # noqa: WPS430
            raise RuntimeError(f"LLM returned non-JSON outline: {exc}") from exc

        graph_data = _outline_to_graph(outline_data)
        graph_json = json.dumps(graph_data, ensure_ascii=False, indent=2)

        # 4. Сохраняем как файл (JSON с nodes/edges/meta)
        base_name = os.path.splitext(getattr(src, "filename") or os.path.basename(src_path))[0]
        dst_filename = f"{base_name}.graph.json"
        dst_path = os.path.join(storage_dir, dst_filename)
        Path(dst_path).parent.mkdir(parents=True, exist_ok=True)
        with open(dst_path, "w", encoding="utf-8") as f:
            f.write(graph_json)

        # 5. Создаём запись файла результата
        new_file = await fm.create_file(
            user_id=getattr(op, "user_id", None),
            format_id=int(new_format_id),
            filename=dst_filename,
            mime_type="application/json",
            content_bytes=None,
            path=dst_path,
        )

        await cm.update_status(
            operation_id,
            status="completed",
            error_message=None,
            result_file_id=int(getattr(new_file, "id")),
        )

        logger.info(
            "[graph_service.generate_graph_for_operation] Operation %s completed, result_file_id=%s",
            operation_id,
            int(getattr(new_file, "id")),
        )

    except ConversionError as exc:
        msg = f"text extraction failed: {exc}"
        logger.error("[graph_service.generate_graph_for_operation] %s", msg)
        await cm.update_status(operation_id, status="failed", error_message=msg)
    except Exception as exc:  # noqa: WPS430
        logger.exception("[graph_service.generate_graph_for_operation] Unexpected error for op=%s: %s", operation_id, exc)
        await cm.update_status(operation_id, status="failed", error_message=str(exc))


__all__ = ["generate_graph_for_operation"]

