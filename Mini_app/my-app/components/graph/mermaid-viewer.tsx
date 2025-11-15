// Руководство к файлу (components/graph/mermaid-viewer.tsx)
// Назначение: Viewer JSON-графа с использованием @xyflow/react (React Flow/XYFlow) с базовым редактированием.
"use client"

import { useCallback, useEffect, useState } from "react"
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  addEdge,
  getIncomers,
  getOutgoers,
  getConnectedEdges,
  type Node,
  type Edge,
  type Connection,
} from "@xyflow/react"
import "@xyflow/react/dist/style.css"
import { Button } from "@/components/ui/button"
import { Loader2 } from "lucide-react"
import type { GraphJson } from "@/lib/types"

interface GraphViewerProps {
  graph: GraphJson | null
  fileId: string
  onGenerate: () => void
}

export function GraphViewer({ graph, fileId, onGenerate }: GraphViewerProps) {
  const [isLoading, setIsLoading] = useState(false)
  const [nodes, setNodes, onNodesChange] = useNodesState([])
  const [edges, setEdges, onEdgesChange] = useEdgesState([])

  useEffect(() => {
    if (!graph) {
      setNodes([])
      setEdges([])
      return
    }

    const initialNodes: Node[] = graph.nodes.map((n, index) => ({
      id: n.id,
      data: { label: n.label, ...(n.data || {}) },
      position: {
        x: (index % 5) * 220,
        y: Math.floor(index / 5) * 140,
      },
      type: n.type || "default",
    }))

    const initialEdges: Edge[] = graph.edges.map((e) => ({
      id: e.id,
      source: e.source,
      target: e.target,
      label: e.label,
      type: e.type || "default",
    }))

    setNodes(initialNodes)
    setEdges(initialEdges)
  }, [graph, fileId, setNodes, setEdges])

  const onConnect = useCallback(
    (connection: Connection) => {
      setEdges((eds: Edge[]) => addEdge(connection, eds))
    },
    [setEdges],
  )

  const onNodesDelete = useCallback(
    (deleted: Node[]) => {
      setEdges((eds: Edge[]) =>
        deleted.reduce((acc: Edge[], node: Node) => {
          const incomers = getIncomers(node, nodes, acc)
          const outgoers = getOutgoers(node, nodes, acc)
          const connectedEdges = getConnectedEdges([node], acc)

          const remainingEdges = acc.filter((edge: Edge) => !connectedEdges.includes(edge))

          const createdEdges = incomers.flatMap(({ id: source }: Node) =>
            outgoers.map(({ id: target }: Node) => ({
              id: `${source}->${target}`,
              source,
              target,
            })),
          )

          return [...remainingEdges, ...createdEdges]
        }, eds),
      )
    },
    [nodes, setEdges],
  )

  const handleGenerate = async () => {
    setIsLoading(true)
    await onGenerate()
    setIsLoading(false)
  }

  if (!graph) {
    return (
      <div className="w-full h-full flex items-center justify-center p-8">
        <div className="text-center space-y-4">
          <div className="w-16 h-16 mx-auto bg-muted rounded-full flex items-center justify-center">
            <svg
              className="w-8 h-8 text-muted-foreground"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              xmlns="http://www.w3.org/2000/svg"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
              />
            </svg>
          </div>
          <div className="space-y-2">
            <h3 className="text-lg font-semibold">No Graph Available</h3>
            <p className="text-sm text-muted-foreground max-w-md">
              Generate a JSON graph to visualize the structure and relationships in this file using React Flow.
            </p>
          </div>
          <Button
            onClick={handleGenerate}
            disabled={isLoading}
            className="bg-[#0077FF] hover:bg-[#0077FF]/90 text-white"
          >
            {isLoading && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
            Generate Graph
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div className="w-full h-full flex items-center justify-center p-4 md:p-8 overflow-hidden">
      <div className="w-full h-full max-w-5xl max-h-[80vh] border rounded-lg bg-background">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onNodesDelete={onNodesDelete}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          fitView
        >
          <Background />
          <MiniMap />
          <Controls />
        </ReactFlow>
      </div>
    </div>
  )
}
