import { type NextRequest, NextResponse } from "next/server"

export async function POST(request: NextRequest) {
  const body = await request.json()
  const { operations, user_id } = body

  if (!operations || !Array.isArray(operations) || operations.length === 0) {
    return NextResponse.json({ error: "Операции должны быть массивом" }, { status: 400 })
  }

  const batchId = `batch_${Date.now()}`

  const operationResults = operations.map((op, index) => ({
    operation_id: `op_${Date.now()}_${index}`,
    status: "queued",
    queue_position: index + 1,
    source: op.source_file_id || op.url,
    target_format: op.target_format,
    type: op.url ? "website" : "file",
  }))

  const response = {
    batch_id: batchId,
    operations: operationResults,
    total: operations.length,
    user_id,
    created_at: new Date().toISOString(),
  }

  return NextResponse.json(response, { status: 201 })
}
