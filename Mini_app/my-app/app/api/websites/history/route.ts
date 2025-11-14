import { type NextRequest, NextResponse } from "next/server"

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url)
  const userId = searchParams.get("user_id")

  if (!userId) {
    return NextResponse.json({ error: "user_id обязателен" }, { status: 400 })
  }

  // Mock история конвертаций сайтов
  const history = [
    {
      operation_id: "op_web_001",
      url: "https://example.com",
      format: "pdf",
      datetime: new Date(Date.now() - 86400000).toISOString(),
      status: "completed",
      result_file_id: "file_001",
    },
    {
      operation_id: "op_web_002",
      url: "https://docs.example.com",
      format: "docx",
      datetime: new Date(Date.now() - 172800000).toISOString(),
      status: "completed",
      result_file_id: "file_002",
    },
    {
      operation_id: "op_web_003",
      url: "https://blog.example.com",
      format: "txt",
      datetime: new Date(Date.now() - 259200000).toISOString(),
      status: "failed",
      error_message: "Превышено время ожидания",
    },
  ]

  return NextResponse.json(history)
}
