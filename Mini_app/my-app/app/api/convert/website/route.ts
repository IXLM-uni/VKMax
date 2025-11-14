import { type NextRequest, NextResponse } from "next/server"

export async function POST(request: NextRequest) {
  const body = await request.json()
  const { url, target_format, user_id } = body

  if (!url || !target_format || !user_id) {
    return NextResponse.json({ error: "URL, target_format и user_id обязательны" }, { status: 400 })
  }

  const operationId = `op_web_${Date.now()}`

  const response = {
    operation_id: operationId,
    status: "processing",
    estimated_time: 20,
    url,
    target_format,
    user_id,
    type: "website",
    created_at: new Date().toISOString(),
  }

  return NextResponse.json(response, { status: 201 })
}
