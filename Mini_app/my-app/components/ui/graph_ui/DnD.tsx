// Руководство к файлу (components/ui/graph_ui/DnD.tsx)
// Назначение: Пример drag-and-drop палитры узлов на @xyflow/react.
"use client"

import { useRef, useCallback, useState } from "react"
import {
  ReactFlow,
  ReactFlowProvider,
  addEdge,
  useNodesState,
  useEdgesState,
  Controls,
  useReactFlow,
  Background,
  type Node,
  type Edge,
  type OnConnect,
} from "@xyflow/react"
import "@xyflow/react/dist/style.css"

const initialNodes: Node[] = [
  {
    id: "1",
    type: "input",
    data: { label: "Input node" },
    position: { x: 250, y: 5 },
  },
]

let idCounter = 2
const getId = () => `dnd_${idCounter++}`

type DnDType = "input" | "default" | "output"

function DnDInner() {
  const wrapperRef = useRef<HTMLDivElement | null>(null)
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes as any)
  const [edges, setEdges, onEdgesChange] = useEdgesState([] as any)
  const { screenToFlowPosition } = useReactFlow()
  const [dragType, setDragType] = useState<DnDType | null>(null)

  const onConnect: OnConnect = useCallback(
    (params: any) => setEdges((eds: any[]) => addEdge(params, eds)),
    [setEdges],
  )

  const onDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault()
    event.dataTransfer.dropEffect = "move"
  }, [])

  const onDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault()

      if (!dragType) return

      const position = screenToFlowPosition({ x: event.clientX, y: event.clientY })
      const newNode: Node = {
        id: getId(),
        type: dragType,
        position,
        data: { label: `${dragType} node` },
      }

      setNodes((nds: any[]) => nds.concat(newNode))
    },
    [dragType, screenToFlowPosition, setNodes],
  )

  const onDragStart = (event: React.DragEvent<HTMLDivElement>, type: DnDType) => {
    setDragType(type)
    event.dataTransfer.setData("application/reactflow", type)
    event.dataTransfer.effectAllowed = "move"
  }

  return (
    <div className="flex w-full h-full">
      <div className="flex-1 h-full" ref={wrapperRef}>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          onDrop={onDrop}
          onDragOver={onDragOver}
          fitView
        >
          <Controls />
          <Background />
        </ReactFlow>
      </div>

      <div className="w-40 border-l bg-card p-2 text-xs space-y-2">
        <div className="font-semibold mb-1">Palette</div>
        <div
          className="p-2 border rounded cursor-move bg-background"
          draggable
          onDragStart={(e) => onDragStart(e, "input")}
        >
          Input node
        </div>
        <div
          className="p-2 border rounded cursor-move bg-background"
          draggable
          onDragStart={(e) => onDragStart(e, "default")}
        >
          Default node
        </div>
        <div
          className="p-2 border rounded cursor-move bg-background"
          draggable
          onDragStart={(e) => onDragStart(e, "output")}
        >
          Output node
        </div>
      </div>
    </div>
  )
}

export function DnDExample() {
  return (
    <ReactFlowProvider>
      <DnDInner />
    </ReactFlowProvider>
  )
}