import { type NextRequest, NextResponse } from "next/server"

export async function GET(request: NextRequest, { params }: { params: Promise<{ operationId: string }> }) {
  const { operationId } = await params

  // Mock данные для статуса конвертации сайта
  const mockStatuses = ["processing", "completed", "failed"]
  const randomStatus = mockStatuses[Math.floor(Math.random() * mockStatuses.length)]

  const response = {
    operation_id: operationId,
    url: "https://example.com",
    status: randomStatus,
    progress: randomStatus === "processing" ? 65 : randomStatus === "completed" ? 100 : 0,
    result_file_id: randomStatus === "completed" ? `file_${Date.now()}` : null,
    error_message: randomStatus === "failed" ? "Не удалось загрузить сайт" : null,
    created_at: new Date(Date.now() - 300000).toISOString(),
    updated_at: new Date().toISOString(),
  }

  return NextResponse.json(response)
}
