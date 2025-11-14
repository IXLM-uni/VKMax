// Руководство к файлу (components/ui/graph_ui/DownloadImage.tsx)
// Назначение: Пример экспорта графа в изображение (PNG) c использованием toPng из html-to-image.
"use client"

import { useCallback, useRef } from "react"
import {
  ReactFlow,
  useNodesState,
  useEdgesState,
  addEdge,
  Controls,
  Background,
  type Node,
  type Edge,
  type OnConnect,
} from "@xyflow/react"
import "@xyflow/react/dist/style.css"
import { toPng } from "html-to-image"

const initialNodes: Node[] = [
  {
    id: "1",
    type: "input",
    data: { label: "Downloadable graph" },
    position: { x: 0, y: 0 },
  },
  {
    id: "2",
    data: { label: "Another node" },
    position: { x: 200, y: 100 },
  },
]

const initialEdges: Edge[] = [{ id: "e1-2", source: "1", target: "2" }]

export function DownloadImageExample() {
  const ref = useRef<HTMLDivElement | null>(null)
  const [nodes, , onNodesChange] = useNodesState(initialNodes as any)
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges as any)

  const onConnect: OnConnect = useCallback(
    (params: any) => setEdges((eds: any[]) => addEdge(params, eds)),
    [setEdges],
  )

  const handleDownload = useCallback(async () => {
    if (!ref.current) return
    try {
      const dataUrl = await toPng(ref.current)
      const link = document.createElement("a")
      link.download = "graph.png"
      link.href = dataUrl
      link.click()
    } catch (e: any) {
      console.error("Failed to download image", e)
    }
  }, [])

  return (
    <div className="w-full h-full flex flex-col gap-2">
      <div className="flex justify-end">
        <button className="px-3 py-1 text-xs border rounded" onClick={handleDownload}>
          Download image
        </button>
      </div>
      <div className="flex-1" ref={ref}>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          fitView
          className="download-image"
        >
          <Controls />
          <Background />
        </ReactFlow>
      </div>
    </div>
  )
}