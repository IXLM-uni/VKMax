import { type NextRequest, NextResponse } from "next/server"

const mockOperations = new Map([
  [
    "op_1",
    {
      operation_id: "op_1",
      user_id: "1",
      file_id: "1",
      old_format: "pdf",
      new_format: "docx",
      datetime: new Date().toISOString(),
      status: "completed",
      progress: 100,
      result_file_id: "result_1",
    },
  ],
])

export async function GET(request: NextRequest, { params }: { params: Promise<{ operationId: string }> }) {
  const { operationId } = await params
  const operation = mockOperations.get(operationId)
  if (!operation) {
    return NextResponse.json({ error: "Operation not found" }, { status: 404 })
  }
  return NextResponse.json(operation)
}
