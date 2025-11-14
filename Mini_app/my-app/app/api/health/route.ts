import { NextResponse } from "next/server"

export async function GET() {
  const health = {
    status: "ok",
    timestamp: new Date().toISOString(),
    version: "1.0.0",
    uptime: process.uptime(),
    services: {
      database: "ok",
      storage: "ok",
      converter: "ok",
      website_parser: "ok",
    },
  }

  return NextResponse.json(health)
}
