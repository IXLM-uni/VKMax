"use client"

import { useState } from "react"
import { Plus, X, ChevronDown } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Checkbox } from "@/components/ui/checkbox"
import { useFileStore } from "@/lib/store"
import { FileIcon } from "@/components/file-icon"
import { SUPPORTED_FORMATS } from "@/lib/types"

export function FormatSelectStep() {
  const { files, updateFile, removeFile, setCurrentStep, conversionType } = useFileStore()
  const [selectedFormats, setSelectedFormats] = useState<Record<string, string>>({})
  const [generateGraphs, setGenerateGraphs] = useState<Record<string, boolean>>({})

  const getAvailableFormats = (isWebsite: boolean) => {
    if (isWebsite) {
      return ["pdf", "txt", "docx"] // Для сайтов доступны только эти форматы
    }
    return SUPPORTED_FORMATS.filter((f) => f !== "site") // Для файлов все форматы кроме site
  }

  const handleFormatChange = (fileId: string, format: string) => {
    setSelectedFormats((prev) => ({ ...prev, [fileId]: format }))
    updateFile(fileId, { targetFormat: format })
  }

  const handleGraphToggle = (fileId: string, checked: boolean) => {
    setGenerateGraphs((prev) => ({ ...prev, [fileId]: checked }))
    updateFile(fileId, { generateGraph: checked })
  }

  const handleConvert = () => {
    // Имитация конвертации
    files.forEach((file) => {
      updateFile(file.id, { status: "converting" })
      setTimeout(() => {
        updateFile(file.id, { status: "converted" })
      }, 2000)
    })
    setCurrentStep("download")
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
          {files.map((file) => (
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
                    {getAvailableFormats(file.isWebsite || false).map((format) => (
                      <SelectItem key={format} value={format}>
                        {format.toUpperCase()}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="flex items-center space-x-2 pt-2 border-t">
                <Checkbox
                  id={`graph-${file.id}`}
                  checked={generateGraphs[file.id] || false}
                  onCheckedChange={(checked) => handleGraphToggle(file.id, checked as boolean)}
                />
                <label
                  htmlFor={`graph-${file.id}`}
                  className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 cursor-pointer"
                >
                  Сгенерировать граф-визуализацию (JSON + React Flow)
                </label>
              </div>
            </div>
          ))}
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
