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
      content: "base64_encoded_content",
      created_at: new Date().toISOString(),
      status: "uploaded",
    },
  ],
])

export async function GET(request: NextRequest, { params }: { params: Promise<{ fileId: string }> }) {
  const { fileId } = await params
  const file = mockFiles.get(fileId)
  if (!file) {
    return NextResponse.json({ error: "File not found" }, { status: 404 })
  }
  return NextResponse.json(file)
}

export async function PATCH(request: NextRequest, { params }: { params: Promise<{ fileId: string }> }) {
  const { fileId } = await params
  const body = await request.json()
  const file = mockFiles.get(fileId)
  if (!file) {
    return NextResponse.json({ error: "File not found" }, { status: 404 })
  }
  const updatedFile = { ...file, ...body }
  mockFiles.set(fileId, updatedFile)
  return NextResponse.json(updatedFile)
}

export async function DELETE(request: NextRequest, { params }: { params: Promise<{ fileId: string }> }) {
  const { fileId } = await params
  mockFiles.delete(fileId)
  return NextResponse.json({ success: true })
}
