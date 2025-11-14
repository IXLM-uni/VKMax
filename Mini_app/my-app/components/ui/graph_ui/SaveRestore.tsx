// Руководство к файлу (components/ui/graph_ui/SaveRestore.tsx)
// Назначение: Пример сохранения и восстановления графа с использованием localStorage.
"use client"

import { useCallback, useState } from "react"
import {
  Background,
  ReactFlow,
  ReactFlowProvider,
  useNodesState,
  useEdgesState,
  addEdge,
  useReactFlow,
  Panel,
  type Node,
  type Edge,
  type OnConnect,
} from "@xyflow/react"
import "@xyflow/react/dist/style.css"

const FLOW_KEY = "vkmax-graph-flow"

const initialNodes: Node[] = [
  { id: "1", data: { label: "Node 1" }, position: { x: 0, y: -50 } },
  { id: "2", data: { label: "Node 2" }, position: { x: 0, y: 50 } },
]

const initialEdges: Edge[] = [{ id: "e1-2", source: "1", target: "2" }]

function SaveRestoreInner() {
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes as any)
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges as any)
  const [rfInstance, setRfInstance] = useState<any>(null)
  const { setViewport } = useReactFlow()

  const onConnect: OnConnect = useCallback(
    (params: any) => setEdges((eds: any[]) => addEdge(params, eds)),
    [setEdges],
  )

  const onSave = useCallback(() => {
    if (!rfInstance) return
    const flow = rfInstance.toObject()
    try {
      localStorage.setItem(FLOW_KEY, JSON.stringify(flow))
    } catch (e: any) {
      console.error("Failed to save flow", e)
    }
  }, [rfInstance])

  const onRestore = useCallback(() => {
    const raw = localStorage.getItem(FLOW_KEY)
    if (!raw) return
    try {
      const flow = JSON.parse(raw)
      const { x = 0, y = 0, zoom = 1 } = flow.viewport || {}
      setNodes(flow.nodes || [])
      setEdges(flow.edges || [])
      setViewport({ x, y, zoom })
    } catch (e: any) {
      console.error("Failed to restore flow", e)
    }
  }, [setNodes, setEdges, setViewport])

  const onAdd = useCallback(() => {
    const id = `node_${Date.now()}`
    const newNode: Node = {
      id,
      data: { label: "Added node" },
      position: { x: (Math.random() - 0.5) * 400, y: (Math.random() - 0.5) * 400 },
    }
    setNodes((nds: any[]) => nds.concat(newNode))
  }, [setNodes])

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      onNodesChange={onNodesChange}
      onEdgesChange={onEdgesChange}
      onConnect={onConnect}
      onInit={setRfInstance}
      fitView
      fitViewOptions={{ padding: 0.5 }}
    >
      <Background />
      <Panel position="top-right" className="space-x-2 bg-card/80 px-3 py-2 rounded text-xs">
        <button className="px-2 py-1 border rounded" onClick={onSave}>
          save
        </button>
        <button className="px-2 py-1 border rounded" onClick={onRestore}>
          restore
        </button>
        <button className="px-2 py-1 border rounded" onClick={onAdd}>
          add node
        </button>
      </Panel>
    </ReactFlow>
  )
}

export function SaveRestoreExample() {
  return (
    <ReactFlowProvider>
      <SaveRestoreInner />
    </ReactFlowProvider>
  )
}