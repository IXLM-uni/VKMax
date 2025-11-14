import { type NextRequest, NextResponse } from "next/server"

type GraphNode = {
  id: string
  label: string
  type?: string
  data?: Record<string, unknown>
}

type GraphEdge = {
  id: string
  source: string
  target: string
  label?: string
  type?: string
}

type GraphJson = {
  nodes: GraphNode[]
  edges: GraphEdge[]
  meta?: {
    source_title?: string
    generated_at?: string
    [key: string]: unknown
  }
}

const mockGraphs = new Map<string, GraphJson>([
  [
    "1",
    {
      nodes: [
        { id: "A", label: "Document Processing", type: "step" },
        { id: "B", label: "Format Detection", type: "step" },
        { id: "C", label: "Valid Format?", type: "decision" },
        { id: "D", label: "Parse Content", type: "step" },
        { id: "E", label: "Error Handler", type: "step" },
      ],
      edges: [
        { id: "A-B", source: "A", target: "B", label: "" },
        { id: "B-C", source: "B", target: "C", label: "" },
        { id: "C-D", source: "C", target: "D", label: "Yes" },
        { id: "C-E", source: "C", target: "E", label: "No" },
      ],
      meta: {
        source_title: "Sample document pipeline",
        generated_at: new Date().toISOString(),
      },
    },
  ],
])

export async function GET(request: NextRequest, { params }: { params: Promise<{ fileId: string }> }) {
  const { fileId } = await params
  const graph = mockGraphs.get(fileId)

  if (!graph) {
    return NextResponse.json({ file_id: fileId, graph: null, generated_at: null }, { status: 200 })
  }

  return NextResponse.json({
    file_id: fileId,
    graph,
    generated_at: graph.meta?.generated_at ?? new Date().toISOString(),
  })
}

export async function POST(request: NextRequest, { params }: { params: Promise<{ fileId: string }> }) {
  const { fileId } = await params

  // Mock generating a new JSON graph
  const newGraph: GraphJson = {
    nodes: [
      { id: "A", label: "File Upload", type: "step" },
      { id: "B", label: "Processing", type: "step" },
      { id: "C", label: "Conversion", type: "step" },
      { id: "D", label: "Download", type: "step" },
    ],
    edges: [
      { id: "A-B", source: "A", target: "B" },
      { id: "B-C", source: "B", target: "C" },
      { id: "C-D", source: "C", target: "D" },
    ],
    meta: {
      source_title: `Generated graph for file ${fileId}`,
      generated_at: new Date().toISOString(),
    },
  }

  mockGraphs.set(fileId, newGraph)

  return NextResponse.json({
    file_id: fileId,
    graph: newGraph,
    generated_at: newGraph.meta?.generated_at,
  })
}
