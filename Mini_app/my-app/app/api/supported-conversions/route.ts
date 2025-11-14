import { NextResponse } from "next/server"

export async function GET() {
  const conversions = {
    from_pdf: ["docx", "txt", "jpg", "png"],
    from_docx: ["pdf", "txt"],
    from_jpg: ["pdf", "png"],
    from_png: ["pdf", "jpg"],
    from_csv: ["xlsx", "txt"],
    from_xlsx: ["csv", "pdf"],
    from_txt: ["pdf", "docx"],
    from_website: ["pdf", "docx", "txt"],
    from_site: ["pdf", "docx", "txt"],
  }

  return NextResponse.json(conversions)
}
