import { type NextRequest, NextResponse } from "next/server"

// Mock data
const mockUsers = new Map([
  [
    "1",
    {
      id: "1",
      max_id: "user_001",
      name: "John Doe",
      metadata: { role: "user", plan: "free" },
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    },
  ],
])

export async function POST(request: NextRequest) {
  const body = await request.json()
  const newUser = {
    id: String(mockUsers.size + 1),
    max_id: body.max_id,
    name: body.name,
    metadata: body.metadata || {},
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  }
  mockUsers.set(newUser.id, newUser)
  return NextResponse.json(newUser, { status: 201 })
}
