// Руководство к файлу (components/ui/graph_ui/ContextMenu.tsx)
// Назначение: Пример контекстного меню для узлов графа на @xyflow/react.
// Правый клик по узлу открывает меню с действиями delete / copy id / focus.
"use client"

import { useCallback, useRef, useState } from "react"
import {
  ReactFlow,
  Background,
  useNodesState,
  useEdgesState,
  addEdge,
  type Node,
  type Edge,
  type NodeMouseHandler,
  type OnConnect,
} from "@xyflow/react"
import "@xyflow/react/dist/style.css"

type MenuState = {
  id: string
  top?: number
  left?: number
  right?: number
  bottom?: number
} | null

const initialNodes: Node[] = [
  {
    id: "1",
    data: { label: "Right-click me" },
    position: { x: 0, y: 0 },
  },
  {
    id: "2",
    data: { label: "Or me" },
    position: { x: 200, y: 0 },
  },
]

const initialEdges: Edge[] = [
  { id: "e1-2", source: "1", target: "2" },
]

export function GraphContextMenuExample() {
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes)
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges)
  const [menu, setMenu] = useState<MenuState>(null)
  const wrapperRef = useRef<HTMLDivElement | null>(null)

  const onConnect: OnConnect = useCallback(
    (params: any) => setEdges((eds: any[]) => addEdge(params, eds)),
    [setEdges],
  )

  const onNodeContextMenu: NodeMouseHandler = useCallback(
    (event: any, node: any) => {
      event.preventDefault()

      const pane = wrapperRef.current?.getBoundingClientRect()
      if (!pane) return

      const { clientX, clientY } = event
      const next: MenuState = {
        id: node.id,
        top: clientY < pane.height - 160 ? clientY : undefined,
        left: clientX < pane.width - 160 ? clientX : undefined,
        right: clientX >= pane.width - 160 ? pane.width - clientX : undefined,
        bottom: clientY >= pane.height - 160 ? pane.height - clientY : undefined,
      }
      setMenu(next)
    },
    [],
  )

  const onPaneClick = useCallback(() => setMenu(null), [])

  const handleDelete = useCallback(() => {
    if (!menu) return
    setNodes((nds: any[]) => nds.filter((n: any) => n.id !== menu.id))
    setEdges((eds: any[]) => eds.filter((e: any) => e.source !== menu.id && e.target !== menu.id))
    setMenu(null)
  }, [menu, setNodes, setEdges])

  const handleCopyId = useCallback(async () => {
    if (!menu) return
    try {
      await navigator.clipboard.writeText(menu.id)
    } catch (e: any) {
      console.error("Failed to copy node id", e)
    }
    setMenu(null)
  }, [menu])

  const handleFocus = useCallback(() => {
    // Для простоты – только закрываем меню, фокус реализуется через fitView в основном viewer.
    setMenu(null)
  }, [])

  return (
    <div ref={wrapperRef} className="relative w-full h-full">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onPaneClick={onPaneClick}
        onNodeContextMenu={onNodeContextMenu}
        fitView
      >
        <Background />
      </ReactFlow>

      {menu && (
        <div
          className="absolute z-50 w-40 rounded border bg-card shadow-md text-xs"
          style={{
            top: menu.top,
            left: menu.left,
            right: menu.right,
            bottom: menu.bottom,
          }}
        >
          <button
            className="w-full text-left px-3 py-2 hover:bg-accent"
            onClick={handleDelete}
          >
            Delete node
          </button>
          <button
            className="w-full text-left px-3 py-2 hover:bg-accent"
            onClick={handleCopyId}
          >
            Copy node ID
          </button>
          <button
            className="w-full text-left px-3 py-2 hover:bg-accent"
            onClick={handleFocus}
          >
            Focus node
          </button>
        </div>
      )}
    </div>
  )
}