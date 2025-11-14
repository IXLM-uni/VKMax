// Руководство к файлу (components/ui/graph_ui/NodeToolbar.tsx)
// Назначение: Демонстрация кастомного типа узла с NodeToolbar (cut/copy/paste/Ask LLM)
// на основе @xyflow/react. Используется как отдельный пример UI для графа.
"use client"

import { useCallback } from "react"
import {
  Background,
  ReactFlow,
  ReactFlowProvider,
  Panel,
  NodeToolbar,
  useNodesState,
} from "@xyflow/react"
import "@xyflow/react/dist/style.css"

type ToolbarPosition = "top" | "right" | "bottom" | "left"
type ToolbarAlign = "start" | "center" | "end"

type ToolbarNodeData = {
  label: string
  toolbarPosition?: ToolbarPosition
  align?: ToolbarAlign
  forceToolbarVisible?: boolean
}

const initialNodes = [
  {
    id: "1",
    position: { x: 0, y: 0 },
    type: "node-with-toolbar",
    data: { label: "Select me to show the toolbar", toolbarPosition: "top", align: "center" },
  },
]

function NodeWithToolbar({ data }: { data: ToolbarNodeData }) {
  return (
    <>
      <NodeToolbar
        isVisible={data.forceToolbarVisible || undefined}
        position={data.toolbarPosition}
        align={data.align}
      >
        <div className="flex gap-1">
          <button className="px-2 py-1 text-xs rounded border bg-background">cut</button>
          <button className="px-2 py-1 text-xs rounded border bg-background">copy</button>
          <button className="px-2 py-1 text-xs rounded border bg-background">paste</button>
          <button className="px-2 py-1 text-xs rounded border bg-background">Ask LLM</button>
        </div>
      </NodeToolbar>
      <div className="px-3 py-2 rounded border bg-card shadow-sm text-xs">{data?.label}</div>
    </>
  )
}

const nodeTypes = {
  "node-with-toolbar": NodeWithToolbar,
}

function NodeToolbarInner() {
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes as any)

  const setPosition = useCallback(
    (pos: string) =>
      setNodes((curr: any[]) =>
        curr.map((node: any) => ({
          ...node,
          data: { ...node.data, toolbarPosition: pos },
        })),
      ),
    [setNodes],
  )

  const setAlignment = useCallback(
    (align: ToolbarAlign) =>
      setNodes((curr: any[]) =>
        curr.map((node: any) => ({
          ...node,
          data: { ...node.data, align },
        })),
      ),
    [setNodes],
  )

  const setForceVisible = useCallback(
    (enabled: boolean) =>
      setNodes((curr: any[]) =>
        curr.map((node: any) => ({
          ...node,
          data: { ...node.data, forceToolbarVisible: enabled },
        })),
      ),
    [setNodes],
  )

  return (
    <ReactFlow
      nodes={nodes}
      onNodesChange={onNodesChange}
      nodeTypes={nodeTypes}
      fitView
      preventScrolling={false}
    >
      <Background />
      <Panel position="top-left" className="space-y-2 bg-card/80 p-2 rounded shadow-sm text-xs">
        <div className="space-x-1">
          <span className="font-semibold">Toolbar position:</span>
          <button onClick={() => setPosition("top")} className="px-1 border rounded">top</button>
          <button onClick={() => setPosition("right")} className="px-1 border rounded">right</button>
          <button onClick={() => setPosition("bottom")} className="px-1 border rounded">bottom</button>
          <button onClick={() => setPosition("left")} className="px-1 border rounded">left</button>
        </div>
        <div className="space-x-1">
          <span className="font-semibold">Alignment:</span>
          <button onClick={() => setAlignment("start")} className="px-1 border rounded">start</button>
          <button onClick={() => setAlignment("center")} className="px-1 border rounded">center</button>
          <button onClick={() => setAlignment("end")} className="px-1 border rounded">end</button>
        </div>
        <label className="flex items-center gap-1">
          <input type="checkbox" onChange={(e) => setForceVisible(e.target.checked)} />
          <span>Always show toolbar</span>
        </label>
      </Panel>
    </ReactFlow>
  )
}

export function NodeToolbarExample() {
  return (
    <ReactFlowProvider>
      <NodeToolbarInner />
    </ReactFlowProvider>
  )
}