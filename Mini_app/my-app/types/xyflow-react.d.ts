// Руководство к файлу (types/xyflow-react.d.ts)
// Назначение: TypeScript-shim для модуля @xyflow/react в окружении React 19/Next 16.
// Библиотека реально установлена в node_modules, этот файл лишь подсказывает TS набор экспортов.

declare module "@xyflow/react" {
  // Базовые компоненты
  export const ReactFlow: any
  export const ReactFlowProvider: any
  export const Background: any
  export const Controls: any
  export const MiniMap: any
  export const Panel: any
  export const NodeToolbar: any
  export const NodeResizer: any

  // Хуки и утилиты
  export const useNodesState: any
  export const useEdgesState: any
  export const useReactFlow: any
  export const addEdge: any
  export const getIncomers: any
  export const getOutgoers: any
  export const getConnectedEdges: any

  // Типы (объявляем как any, чтобы не блокировать сборку)
  export type Position = any
  export type Node<T = any> = any
  export type Edge<T = any> = any
  export type Connection = any
  export type NodeMouseHandler = any
  export type OnConnect = any
}

