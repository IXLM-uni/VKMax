import { NextResponse } from "next/server"

const mockFormats = [
  {
    format_id: "1",
    type: "pdf",
    extension: ".pdf",
    mime_type: "application/pdf",
    is_input: true,
    is_output: true,
  },
  {
    format_id: "2",
    type: "docx",
    extension: ".docx",
    mime_type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    is_input: true,
    is_output: true,
  },
  {
    format_id: "3",
    type: "csv",
    extension: ".csv",
    mime_type: "text/csv",
    is_input: true,
    is_output: true,
  },
  {
    format_id: "4",
    type: "xlsx",
    extension: ".xlsx",
    mime_type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    is_input: true,
    is_output: true,
  },
]

export async function GET() {
  return NextResponse.json(mockFormats)
}
