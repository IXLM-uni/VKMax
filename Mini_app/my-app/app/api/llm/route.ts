import { type NextRequest, NextResponse } from "next/server"

export async function POST(request: NextRequest) {
  const body = await request.json()
  const { question, context } = body

  // Mock LLM response
  const mockResponses: Record<string, string> = {
    "what is pdf":
      "PDF (Portable Document Format) is a file format developed by Adobe for presenting documents consistently across platforms.",
    "what is docx":
      "DOCX is a Microsoft Word document format introduced in Word 2007, based on XML and ZIP compression.",
    "what is csv":
      "CSV (Comma-Separated Values) is a simple text file format used to store tabular data, where each line represents a row.",
    default:
      "That's an interesting question! Based on the file conversion context, I can help you understand different file formats and their characteristics.",
  }

  const answer = mockResponses[question.toLowerCase()] || mockResponses.default

  return NextResponse.json({
    answer,
    timestamp: new Date().toISOString(),
  })
}
