import { type NextRequest, NextResponse } from "next/server"

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

export async function GET(request: NextRequest, { params }: { params: Promise<{ userId: string }> }) {
  const { userId } = await params
  const user = mockUsers.get(userId)
  if (!user) {
    return NextResponse.json({ error: "User not found" }, { status: 404 })
  }
  return NextResponse.json(user)
}

export async function DELETE(request: NextRequest, { params }: { params: Promise<{ userId: string }> }) {
  const { userId } = await params
  mockUsers.delete(userId)
  return NextResponse.json({ success: true })
}
