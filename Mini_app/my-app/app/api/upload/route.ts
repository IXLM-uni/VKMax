import { type NextRequest, NextResponse } from "next/server"

export async function POST(request: NextRequest) {
  const formData = await request.formData()
  const file = formData.get("file") as File | null
  const userId = formData.get("user_id") as string
  const originalFormat = formData.get("original_format") as string
  const url = formData.get("url") as string | null
  const isWebsite = formData.get("is_website") === "true"

  if (!file && !url) {
    return NextResponse.json({ error: "No file or URL provided" }, { status: 400 })
  }

  // Mock upload response
  const mockFile = {
    file_id: `file_${Date.now()}`,
    filename: isWebsite && url ? url : file?.name || "unknown",
    size: file?.size || 0,
    upload_date: new Date().toISOString(),
    user_id: userId,
    original_format: isWebsite ? "site" : originalFormat,
    status: "uploaded",
    url: url || undefined,
    is_website: isWebsite,
  }

  return NextResponse.json(mockFile, { status: 201 })
}
