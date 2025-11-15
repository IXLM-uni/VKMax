// Руководство к файлу (lib/api.ts)
// Назначение: Клиент VKMax FAST_API для Mini_app. Содержит функции для загрузки файлов,
// конвертации, работы с сайтами и получения статусов/справочников.
// Важно:
// - Базовый URL берётся из NEXT_PUBLIC_API_URL (иначе "/api" для dev/mocks).
// - userId в вызовах upload может быть опциональным (файлы без владельца),
//   а в convert всегда передаётся строка (в т.ч. пустая) для совместимости со схемами.
import type { ConvertFile, ConversionOperation } from "./types"

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api"

export async function uploadFile(file: File, userId?: string): Promise<ConvertFile> {
  const formData = new FormData()
  formData.append("file", file)
  if (userId) {
    formData.append("user_id", userId)
  }
  formData.append("original_format", file.name.split(".").pop() || "")

  const response = await fetch(`${API_BASE}/upload`, {
    method: "POST",
    body: formData,
  })

  if (!response.ok) {
    throw new Error("Не удалось загрузить файл")
  }

  const data = await response.json()
  return {
    id: data.file_id,
    name: data.filename,
    size: data.size,
    originalFormat: file.name.split(".").pop() || "",
    status: "uploaded",
    uploadDate: new Date(data.upload_date),
  }
}

export async function uploadWebsite(
  url: string,
  userId?: string,
  name?: string,
  format?: string,
): Promise<{ fileId: string; operationId: string; status: string }> {
  const payload: any = {
    url,
    name: name || new URL(url).hostname,
  }
  if (userId) {
    payload.user_id = userId
  }
  if (format) {
    payload.format = format
  }

  const response = await fetch(`${API_BASE}/upload/website`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  })

  if (!response.ok) {
    throw new Error("Не удалось загрузить сайт")
  }

  const data = await response.json()
  return {
    fileId: data.file_id ?? null,
    operationId: String(data.operation_id),
    status: data.status,
  }
}

export async function convertFile(
  fileId: string,
  targetFormat: string,
  userId: string = "",
  isWebsite = false,
): Promise<ConversionOperation> {
  const response = await fetch(`${API_BASE}/convert`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      source_file_id: fileId,
      target_format: targetFormat,
      user_id: userId || "",
    }),
  })

  if (!response.ok) {
    throw new Error("Не удалось выполнить конвертацию")
  }

  const data = await response.json()

  return {
    id: String(data.operation_id),
    fileId: null,
    userId,
    oldFormat: null,
    newFormat: targetFormat,
    status: (data.status ?? "queued") as ConversionOperation["status"],
    progress: 0,
    createdAt: new Date(),
  }
}

export async function convertWebsite(
  url: string,
  targetFormat: string,
  userId: string = "",
): Promise<ConversionOperation> {
  const response = await fetch(`${API_BASE}/convert/website`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      url,
      target_format: targetFormat,
      user_id: userId || "",
    }),
  })

  if (!response.ok) {
    throw new Error("Не удалось конвертировать сайт")
  }

  const data = await response.json()

  return {
    id: String(data.operation_id),
    fileId: null,
    userId,
    oldFormat: null,
    newFormat: targetFormat,
    status: (data.status ?? "queued") as ConversionOperation["status"],
    progress: 0,
    createdAt: new Date(),
  }
}

export async function batchConvert(
  operations: Array<{ source_file_id?: string; url?: string; target_format: string }>,
  userId: string = "",
): Promise<{ batch_id: string; operations: any[] }> {
  const response = await fetch(`${API_BASE}/batch-convert`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      operations,
      user_id: userId || "",
    }),
  })

  if (!response.ok) {
    throw new Error("Не удалось выполнить пакетную конвертацию")
  }

  return response.json()
}

export async function getOperationStatus(operationId: string): Promise<ConversionOperation> {
  const response = await fetch(`${API_BASE}/operations/${operationId}`)
  if (!response.ok) {
    throw new Error("Не удалось получить статус операции")
  }

  const data = await response.json()

  return {
    id: String(data.operation_id),
    fileId: data.file_id ?? null,
    userId: data.user_id ?? null,
    oldFormat: data.old_format ?? null,
    newFormat: data.new_format ?? null,
    status: (data.status ?? "queued") as ConversionOperation["status"],
    progress: typeof data.progress === "number" ? data.progress : 0,
    createdAt: data.datetime ? new Date(data.datetime) : undefined,
    resultFileId: data.result_file_id ?? null,
  }
}

export async function getWebsiteStatus(operationId: string): Promise<any> {
  const response = await fetch(`${API_BASE}/websites/${operationId}/status`)
  if (!response.ok) {
    throw new Error("Не удалось получить статус конвертации сайта")
  }
  return response.json()
}

export async function previewWebsite(url: string): Promise<any> {
  const response = await fetch(`${API_BASE}/websites/preview`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
  })
  if (!response.ok) {
    throw new Error("Не удалось получить предпросмотр сайта")
  }
  return response.json()
}

export async function getWebsiteHistory(userId: string): Promise<any[]> {
  const response = await fetch(`${API_BASE}/websites/history?user_id=${userId}`)
  if (!response.ok) {
    throw new Error("Не удалось получить историю конвертаций")
  }
  return response.json()
}

export async function downloadFile(fileId: string): Promise<Blob> {
  const response = await fetch(`${API_BASE}/download/${fileId}`)
  if (!response.ok) {
    throw new Error("Не удалось скачать файл")
  }
  return response.blob()
}

export async function getUserFiles(userId: string): Promise<ConvertFile[]> {
  const response = await fetch(`${API_BASE}/users/${userId}/files`)
  if (!response.ok) {
    throw new Error("Не удалось получить файлы пользователя")
  }
  const data = (await response.json()) as any[]

  return data.map((file: any): ConvertFile => {
    const id = String(file.id ?? file.file_id)
    const createdAt = file.created_at ?? file.upload_date ?? new Date().toISOString()

    return {
      id,
      name: file.filename ?? file.name ?? "file",
      size: typeof file.size === "number" ? file.size : 0,
      originalFormat: file.format ?? "",
      status: "uploaded",
      uploadDate: new Date(createdAt),
      downloadUrl: `${API_BASE}/download/${id}`,
    }
  })
}

export async function getSupportedConversions(): Promise<Record<string, string[]>> {
  const response = await fetch(`${API_BASE}/supported-conversions`)
  if (!response.ok) {
    throw new Error("Не удалось получить список поддерживаемых конвертаций")
  }
  return response.json()
}
