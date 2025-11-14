import { type NextRequest, NextResponse } from "next/server"

export async function GET(request: NextRequest, { params }: { params: Promise<{ fileId: string }> }) {
  const { fileId } = await params

  // Mock file download
  const mockFileContent = Buffer.from("Mock file content for " + fileId)

  return new NextResponse(mockFileContent, {
    headers: {
      "Content-Type": "application/octet-stream",
      "Content-Disposition": `attachment; filename="converted_file_${fileId}.pdf"`,
    },
  })
}
