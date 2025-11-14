// Руководство к файлу (components/ui/graph_ui/Resizer.tsx)
// Назначение: Пример кастомных узлов с NodeResizer для изменения размеров узла.
"use client"

import {
  ReactFlow,
  Background,
  Controls,
  NodeResizer,
  type Node,
} from "@xyflow/react"
import "@xyflow/react/dist/style.css"

type ResizableData = {
  label: string
}

const defaultNodes: Node<ResizableData>[] = [
  {
    id: "1",
    type: "resizable",
    position: { x: 0, y: 50 },
    data: { label: "Drag the corners to resize" },
    style: {
      width: 200,
      height: 100,
      border: "1px solid var(--border)",
      borderRadius: 8,
      padding: 8,
      background: "var(--card)",
      fontSize: 12,
    },
  },
]

function ResizableNode({ data, selected }: { data: ResizableData; selected: boolean }) {
  return (
    <div className="w-full h-full relative">
      <NodeResizer
        color="#0077FF"
        isVisible={selected}
        minWidth={120}
        minHeight={60}
      />
      <div className="w-full h-full flex items-center justify-center text-xs text-foreground">
        {data.label}
      </div>
    </div>
  )
}

const nodeTypes = {
  resizable: ResizableNode,
}

export function ResizerExample() {
  return (
    <ReactFlow
      defaultNodes={defaultNodes}
      defaultEdges={[]}
      nodeTypes={nodeTypes}
      fitView
      minZoom={0.4}
      maxZoom={2}
    >
      <Background />
      <Controls />
    </ReactFlow>
  )
}