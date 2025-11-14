export type FileStatus = "uploading" | "uploaded" | "converting" | "converted" | "error"

export interface ConvertFile {
  id: string
  name: string
  size: number
  originalFormat: string
  targetFormat?: string
  status: FileStatus
  uploadDate: Date
  downloadUrl?: string
  mermaidSchema?: string
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
