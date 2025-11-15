// Руководство к файлу (components/converter/format-select-step.tsx)
// Назначение: Второй шаг конвертера VKMax в Mini_app — выбор целевых форматов и запуск конвертации.
// Важно: Для файлов конвертация выполняется через backend (/convert) и статус операции читается из /operations/{id}.
"use client"

import { useState } from "react"
import { Plus, X, ChevronDown, Download, Network } from "lucide-react"
import { useRouter } from "next/navigation"
import { Button } from "@/components/ui/button"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Checkbox } from "@/components/ui/checkbox"
import { useFileStore } from "@/lib/store"
import { FileIcon } from "@/components/file-icon"
import { type ConvertFile } from "@/lib/types"
import { convertFile, convertWebsite, getOperationStatus, getWebsiteStatus, downloadFile } from "@/lib/api"

export function FormatSelectStep() {
  const router = useRouter()
  const { files, updateFile, removeFile, setCurrentStep, conversionType } = useFileStore()
  const [selectedFormats, setSelectedFormats] = useState<Record<string, string>>({})
  const getAvailableFormats = (file: ConvertFile) => {
    const isWebsite = Boolean(file.isWebsite)

    if (isWebsite) {
      // Для сайта: PDF + GRAPH
      return ["pdf", "graph"]
    }

    const ext = (file.originalFormat || "").toLowerCase().replace(/^\.+/, "")

    if (ext === "doc" || ext === "docx") {
      // Для DOC/DOCX: PDF + GRAPH
      return ["pdf", "graph"]
    }

    if (ext === "pdf") {
      // Для PDF: DOCX + GRAPH
      return ["docx", "graph"]
    }

    // На всякий случай: всегда разрешаем хотя бы GRAPH
    return ["graph"]
  }

  const handleDownload = async (
    fileId: string,
    resultFileId?: string,
    name?: string,
    targetFormat?: string,
    originalFormat?: string,
  ) => {
    const id = resultFileId || fileId
    try {
      const blob = await downloadFile(id)
      const url = URL.createObjectURL(blob)
      const a = document.createElement("a")
      a.href = url
      const ext = (targetFormat || originalFormat || "").replace(/^\.+/, "")
      const baseName = (name || "file").replace(/\.[^.]+$/, "")
      if (ext) {
        a.download = `${baseName}.${ext}`
      } else {
        a.download = name || "file"
      }
      document.body.appendChild(a)
      a.click()
      a.remove()
      URL.revokeObjectURL(url)
    } catch (error) {
      console.error("Не удалось скачать файл", id, error)
    }
  }

  const handleFormatChange = (fileId: string, format: string) => {
    setSelectedFormats((prev) => ({ ...prev, [fileId]: format }))
    updateFile(fileId, { targetFormat: format })
  }

  const handleConvert = async () => {
    const tasks = files
      .filter((file) => selectedFormats[file.id])
      .map(async (file) => {
        const targetFormat = selectedFormats[file.id]
        if (!targetFormat) return

        // помечаем файл как конвертирующийся
        updateFile(file.id, { status: "converting" })

        try {
          let isCompleted = false
          let resultFileId: string | undefined

          if (file.isWebsite && file.url) {
            // Двухшаговый поток для сайтов:
            // 1) convert/website -> site_bundle
            const siteBundleOp = await convertWebsite(file.url, "site_bundle")
            const siteBundleStatus = await getWebsiteStatus(siteBundleOp.id)

            const siteBundleFileId = (siteBundleStatus as any).result_file_id as string | undefined

            if (!siteBundleFileId) {
              throw new Error("Не удалось получить site_bundle для сайта")
            }

            // 2) обычный convert site_bundle -> целевой формат (pdf/docx/..)
            const op = await convertFile(siteBundleFileId, targetFormat)
            const st = await getOperationStatus(op.id)

            isCompleted = st.status === "completed"
            resultFileId = st.resultFileId ?? undefined
          } else {
            // Для файлов: file.id уже равен backend file_id (см. uploadFile в lib/api.ts)
            const operation = await convertFile(file.id, targetFormat)
            const status = await getOperationStatus(operation.id)
            isCompleted = status.status === "completed"
            resultFileId = status.resultFileId ?? undefined
          }

          const baseName = file.name.replace(/\.[^.]+$/, "")
          const finalName =
            isCompleted && targetFormat ? `${baseName}.${targetFormat}` : file.name

          updateFile(file.id, {
            status: isCompleted ? "converted" : "error",
            targetFormat,
            resultFileId,
            name: finalName,
          })
        } catch (error) {
          console.error("Ошибка конвертации файла", file.id, error)
          updateFile(file.id, { status: "error" })
        }
      })

    await Promise.all(tasks)
  }

  const handleAddMore = () => {
    setCurrentStep("upload")
  }

  return (
    <div className="flex flex-col min-h-screen px-4 py-6 max-w-4xl mx-auto">
      <div className="space-y-6">
        <div className="text-center space-y-2">
          <h1 className="text-3xl md:text-4xl font-bold">
            {conversionType === "website" ? "Конвертер Сайтов" : "Конвертер Файлов"}
          </h1>
          <p className="text-muted-foreground">
            {conversionType === "website"
              ? "Выберите выходной формат для сайта"
              : "Выберите выходной формат для ваших файлов"}
          </p>
        </div>

        <Button
          variant="outline"
          className="w-full justify-start gap-2 border-2 border-dashed h-auto py-3 bg-transparent"
          onClick={handleAddMore}
        >
          <Plus className="w-5 h-5 text-[#0077FF]" />
          <span>{conversionType === "website" ? "Добавить еще сайты" : "Добавить еще файлы"}</span>
          <ChevronDown className="w-4 h-4 ml-auto" />
        </Button>

        <div className="space-y-3">
          {files.map((file) => {
            const isConverting = file.status === "converting"
            const isConverted = file.status === "converted"

            return (
              <div key={file.id} className="flex flex-col gap-3 p-4 border rounded-lg bg-card">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-start gap-3 flex-1 min-w-0">
                    <FileIcon format={file.originalFormat} className="w-5 h-5 mt-0.5 flex-shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="font-medium truncate">{file.name}</p>
                      {!file.isWebsite && (
                        <p className="text-sm text-muted-foreground">{(file.size / (1024 * 1024)).toFixed(2)} MB</p>
                      )}
                      {file.isWebsite && <p className="text-sm text-muted-foreground">Веб-сайт</p>}
                    </div>
                  </div>
                  <Button variant="ghost" size="icon" onClick={() => removeFile(file.id)} className="flex-shrink-0">
                    <X className="w-4 h-4" />
                  </Button>
                </div>

                <div className="flex items-center gap-2">
                  <span className="text-sm text-muted-foreground">Выходной формат:</span>
                  <Select value={selectedFormats[file.id]} onValueChange={(value) => handleFormatChange(file.id, value)}>
                    <SelectTrigger className="w-32 border-[#0077FF]">
                      <SelectValue placeholder="Формат" />
                    </SelectTrigger>
                    <SelectContent>
                      {getAvailableFormats(file).map((format) => (
                        <SelectItem key={format} value={format}>
                          {format.toUpperCase()}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="pt-2 space-y-2">
                  <Button
                    className="w-full"
                    disabled={!isConverted}
                    onClick={() =>
                      isConverted &&
                      handleDownload(
                        file.id,
                        file.resultFileId,
                        file.name,
                        file.targetFormat,
                        file.originalFormat,
                      )
                    }
                  >
                    {isConverting && "Processing..."}
                    {!isConverting && isConverted && (
                      <>
                        <Download className="w-4 h-4 mr-2" />
                        Download
                      </>
                    )}
                    {!isConverting && !isConverted && "Download"}
                  </Button>

                  {isConverted && file.targetFormat === "graph" && (
                    <Button
                      variant="outline"
                      size="sm"
                      className="w-full bg-transparent border-[#76E7F8] text-[#76E7F8] hover:bg-[#76E7F8]/10"
                      onClick={() => {
                        router.push(`/graph?fileId=${file.id}`)
                      }}
                    >
                      <Network className="w-4 h-4 mr-2" />
                      View Graph Visualization
                    </Button>
                  )}
                </div>
              </div>
            )
          })}
        </div>

        <div className="sticky bottom-0 bg-background pt-4 border-t mt-6">
          <div className="flex items-center justify-between mb-4">
            <p className="text-sm text-muted-foreground">
              Добавлено {files.length}{" "}
              {files.length === 1
                ? conversionType === "website"
                  ? "сайт"
                  : "файл"
                : conversionType === "website"
                  ? "сайтов"
                  : "файлов"}
            </p>
          </div>
          <Button
            onClick={handleConvert}
            disabled={!files.some((f) => selectedFormats[f.id])}
            className="w-full bg-[#0077FF] hover:bg-[#0077FF]/90 text-white py-6 text-lg"
          >
            Конвертировать
          </Button>
        </div>
      </div>
    </div>
  )
}
