import { type NextRequest, NextResponse } from "next/server"

export async function POST(request: NextRequest) {
  const body = await request.json()
  const { source_file_id, target_format, user_id, is_website } = body

  const operationId = `op_${Date.now()}`

  const estimatedTime = is_website ? 15 : 5 // Конвертация сайтов занимает больше времени

  // Mock conversion response
  const response = {
    operation_id: operationId,
    status: "queued",
    estimated_time: estimatedTime,
    queue_position: 1,
    source_file_id,
    target_format,
    user_id,
    is_website: is_website || false,
    created_at: new Date().toISOString(),
  }

  return NextResponse.json(response, { status: 201 })
}
