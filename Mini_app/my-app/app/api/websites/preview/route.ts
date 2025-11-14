import { type NextRequest, NextResponse } from "next/server"

export async function POST(request: NextRequest) {
  const body = await request.json()
  const { url } = body

  if (!url) {
    return NextResponse.json({ error: "URL обязателен" }, { status: 400 })
  }

  // Mock предпросмотр сайта
  const response = {
    url,
    title: "Пример страницы",
    description: "Это описание страницы для предпросмотра",
    screenshot_url: "/placeholder.svg?height=400&width=600",
    page_count: 1,
    estimated_size: 2500000,
    domain: new URL(url).hostname,
    status: "ready",
  }

  return NextResponse.json(response)
}
