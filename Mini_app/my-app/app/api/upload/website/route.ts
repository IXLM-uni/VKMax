import { type NextRequest, NextResponse } from "next/server"

export async function POST(request: NextRequest) {
  const body = await request.json()
  const { user_id, url, name, format } = body

  if (!url || !user_id) {
    return NextResponse.json({ error: "URL и user_id обязательны" }, { status: 400 })
  }

  // Mock response для загрузки сайта
  const response = {
    file_id: `site_${Date.now()}`,
    operation_id: `op_${Date.now()}`,
    status: "processing",
    estimated_time: 15,
    url,
    name: name || new URL(url).hostname,
    format: format || "site",
    created_at: new Date().toISOString(),
  }

  return NextResponse.json(response, { status: 201 })
}
