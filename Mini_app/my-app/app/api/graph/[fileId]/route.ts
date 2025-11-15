// Руководство к файлу (app/api/graph/[fileId]/route.ts)
// Назначение: Next.js API-роут, который проксирует запросы граф-визуализации к FastAPI.
// - GET /api/graph/{fileId}: проксирует запрос к FAST_API /graph/{file_id},
//   который возвращает уже сгенерированный JSON-граф (или null, если его нет).
// - POST /api/graph/{fileId}: проксирует запрос к FAST_API /graph/{file_id},
//   который запускает генерацию графа и сразу возвращает готовый graph JSON.
import { type NextRequest, NextResponse } from "next/server"
// Базовый URL FastAPI (совпадает с lib/api.ts). Если не задан, считаем, что backend доступен на /api.
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api"

// ----------------------------- GET: читать готовый граф -----------------------------

export async function GET(_request: NextRequest, { params }: { params: Promise<{ fileId: string }> }) {
  const { fileId } = await params

  try {
    const res = await fetch(`${API_BASE}/graph/${fileId}`)
    if (!res.ok) {
      return NextResponse.json({ file_id: fileId, graph: null, generated_at: null }, { status: 200 })
    }

    const data = await res.json()
    const graph = (data as any)?.graph ?? null
    const meta = (graph as any)?.meta ?? {}

    return NextResponse.json({
      file_id: fileId,
      graph,
      generated_at: meta.generated_at ?? new Date().toISOString(),
    })
  } catch (error) {
    console.error("[/api/graph/[fileId]] GET error", error)
    return NextResponse.json({ file_id: fileId, graph: null, generated_at: null }, { status: 200 })
  }
}

// ----------------------------- POST: сгенерировать граф -----------------------------

export async function POST(_request: NextRequest, { params }: { params: Promise<{ fileId: string }> }) {
  const { fileId } = await params

  try {
    const res = await fetch(`${API_BASE}/graph/${fileId}`, {
      method: "POST",
    })
    if (!res.ok) {
      const text = await res.text().catch(() => "")
      console.error("[/api/graph/[fileId]] POST /graph failed", res.status, text)
      return NextResponse.json({ file_id: fileId, graph: null, generated_at: null }, { status: 500 })
    }

    const data = await res.json()
    const graph = (data as any)?.graph ?? null
    const meta = (graph as any)?.meta ?? {}

    return NextResponse.json({
      file_id: fileId,
      graph,
      generated_at: meta.generated_at ?? new Date().toISOString(),
    })
  } catch (error) {
    console.error("[/api/graph/[fileId]] POST error", error)
    return NextResponse.json({ file_id: fileId, graph: null, generated_at: null }, { status: 500 })
  }
}

