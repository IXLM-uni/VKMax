export type FileStatus = "uploading" | "uploaded" | "converting" | "converted" | "error"

export interface GraphNode {
  id: string
  label: string
  type?: string
  data?: Record<string, unknown>
}

export interface GraphEdge {
  id: string
  source: string
  target: string
  label?: string
  type?: string
}

export interface GraphMeta {
  source_title?: string
  generated_at?: string
  [key: string]: unknown
}

export interface GraphJson {
  nodes: GraphNode[]
  edges: GraphEdge[]
  meta?: GraphMeta
}

export interface ConvertFile {
  id: string
  name: string
  size: number
  originalFormat: string
  targetFormat?: string
  status: FileStatus
  uploadDate: Date
  downloadUrl?: string
  graphJson?: GraphJson
  generateGraph?: boolean // Added field to track if graph should be generated
  url?: string // URL веб-сайта, если это конвертация сайта
  isWebsite?: boolean // Флаг, указывающий на то, что это веб-сайт
}

export interface ConversionOperation {
  id: string
  fileId: string
  oldFormat: string
  newFormat: string
  status: "pending" | "processing" | "completed" | "failed"
  progress: number
  createdAt: Date
}

export type ConverterStep = "upload" | "select-format" | "download"

export const SUPPORTED_FORMATS = ["pdf", "docx", "doc", "jpg", "png", "xlsx", "csv", "txt", "site"] as const
export type SupportedFormat = (typeof SUPPORTED_FORMATS)[number]
