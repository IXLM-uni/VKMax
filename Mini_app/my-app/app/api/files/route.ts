import { type NextRequest, NextResponse } from "next/server"

const mockFiles = new Map([
  [
    "1",
    {
      id: "1",
      user_id: "1",
      format_id: "1",
      filename: "sample-document.pdf",
      file_size: 1048576,
      mime_type: "application/pdf",
      path: "/files/sample-document.pdf",
      created_at: new Date().toISOString(),
      status: "uploaded",
    },
  ],
  [
    "2",
    {
      id: "2",
      user_id: "1",
      format_id: "2",
      filename: "financial-report.docx",
      file_size: 524288,
      mime_type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      path: "/files/financial-report.docx",
      created_at: new Date(Date.now() - 86400000).toISOString(),
      status: "uploaded",
    },
  ],
  [
    "3",
    {
      id: "3",
      user_id: "1",
      format_id: "3",
      filename: "data-export.csv",
      file_size: 262144,
      mime_type: "text/csv",
      path: "/files/data-export.csv",
      created_at: new Date(Date.now() - 172800000).toISOString(),
      status: "uploaded",
    },
  ],
])

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams
  const userId = searchParams.get("user_id")
  const page = Number.parseInt(searchParams.get("page") || "1")
  const limit = Number.parseInt(searchParams.get("limit") || "10")

  let files = Array.from(mockFiles.values())
  if (userId) {
    files = files.filter((f) => f.user_id === userId)
  }

  const total = files.length
  const start = (page - 1) * limit
  const end = start + limit
  const paginatedFiles = files.slice(start, end)

  return NextResponse.json({
    files: paginatedFiles,
    total,
    page,
    pages: Math.ceil(total / limit),
  })
}
