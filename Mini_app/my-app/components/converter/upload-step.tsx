// Руководство к файлу (components/converter/upload-step.tsx)
// Назначение: Первый шаг конвертера VKMax в Mini_app: загрузка файлов или ввод URL сайта.
// Важно: Для файлов сразу вызывается backend (/upload) через lib/api.uploadFile,
//        сайты пока только добавляются в стор и конвертируются на следующем шаге.
"use client"

import type React from "react"

import { useCallback, useState } from "react"
import { Upload, Globe } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { useFileStore } from "@/lib/store"
import { cn } from "@/lib/utils"
import { uploadFile } from "@/lib/api"

export function UploadStep() {
  const [isDragging, setIsDragging] = useState(false)
  const [websiteUrl, setWebsiteUrl] = useState("")
  const { addFile, setCurrentStep, conversionType } = useFileStore()

  const handleFiles = useCallback(
    async (files: FileList | null) => {
      if (!files) return

      const uploads = Array.from(files).map(async (file) => {
        try {
          const uploaded = await uploadFile(file)
          addFile(uploaded)
        } catch (error) {
          // TODO: можно показать уведомление пользователю, пока логируем в консоль
          console.error("Не удалось загрузить файл", error)
        }
      })

      await Promise.all(uploads)

      setCurrentStep("select-format")
    },
    [addFile, setCurrentStep],
  )

  const handleWebsiteSubmit = useCallback(() => {
    if (!websiteUrl) return

    const newFile = {
      id: crypto.randomUUID(),
      name: websiteUrl,
      size: 0,
      originalFormat: "site",
      status: "uploaded" as const,
      uploadDate: new Date(),
      url: websiteUrl,
      isWebsite: true,
    }
    addFile(newFile)
    setCurrentStep("select-format")
  }, [websiteUrl, addFile, setCurrentStep])

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      setIsDragging(false)
      handleFiles(e.dataTransfer.files)
    },
    [handleFiles],
  )

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }, [])

  const handleDragLeave = useCallback(() => {
    setIsDragging(false)
  }, [])

  if (conversionType === "website") {
    return (
      <div className="flex flex-col items-center justify-center min-h-[70vh] px-4">
        <div className="w-full max-w-2xl text-center space-y-6">
          <h1 className="text-4xl md:text-5xl font-bold text-balance">Конвертер Сайтов</h1>
          <p className="text-lg md:text-xl text-muted-foreground text-pretty">
            Введите URL веб-сайта для конвертации в PDF или текстовый файл
          </p>

          <div className="relative w-full border-2 border-dashed rounded-lg p-12 transition-colors border-border">
            <div className="flex flex-col items-center gap-6">
              <div className="w-16 h-16 rounded-full bg-[#FF3985] flex items-center justify-center">
                <Globe className="w-8 h-8 text-white" />
              </div>

              <div className="w-full max-w-md space-y-4">
                <Input
                  type="url"
                  placeholder="https://example.com"
                  value={websiteUrl}
                  onChange={(e) => setWebsiteUrl(e.target.value)}
                  className="text-center text-lg py-6"
                />
                <Button
                  size="lg"
                  className="bg-[#FF3985] hover:bg-[#FF3985]/90 text-white px-8 py-6 text-lg w-full"
                  onClick={handleWebsiteSubmit}
                  disabled={!websiteUrl}
                >
                  Продолжить
                </Button>
              </div>
            </div>
          </div>

          <div className="space-y-2 text-sm text-muted-foreground">
            <p>
              Максимальный размер 1GB.{" "}
              <a href="#" className="text-[#FF3985] hover:underline">
                Регистрация
              </a>{" "}
              для большего
            </p>
            <p>
              Продолжая, вы соглашаетесь с{" "}
              <a href="#" className="text-[#FF3985] hover:underline">
                Условиями использования
              </a>
              .
            </p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col items-center justify-center min-h-[70vh] px-4">
      <div className="w-full max-w-2xl text-center space-y-6">
        <h1 className="text-4xl md:text-5xl font-bold text-balance">Конвертер Файлов</h1>
        <p className="text-lg md:text-xl text-muted-foreground text-pretty">
          Легко конвертируйте файлы из одного формата в другой онлайн
        </p>

        <div
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          className={cn(
            "relative w-full border-2 border-dashed rounded-lg p-12 transition-colors",
            isDragging ? "border-[#0077FF] bg-[#0077FF]/5" : "border-border",
          )}
        >
          <input
            type="file"
            multiple
            onChange={(e) => handleFiles(e.target.files)}
            className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
            id="file-upload"
          />
          <div className="flex flex-col items-center gap-4">
            <div className="w-16 h-16 rounded-full bg-[#0077FF] flex items-center justify-center">
              <Upload className="w-8 h-8 text-white" />
            </div>
            <label htmlFor="file-upload" className="cursor-pointer">
              <Button size="lg" className="bg-[#0077FF] hover:bg-[#0077FF]/90 text-white px-8 py-6 text-lg" asChild>
                <span>Выбрать Файлы</span>
              </Button>
            </label>
          </div>
        </div>

        <div className="space-y-2 text-sm text-muted-foreground">
          <p>
            Максимальный размер файла 1GB.{" "}
            <a href="#" className="text-[#0077FF] hover:underline">
              Регистрация
            </a>{" "}
            для большего
          </p>
          <p>
            Продолжая, вы соглашаетесь с{" "}
            <a href="#" className="text-[#0077FF] hover:underline">
              Условиями использования
            </a>
            .
          </p>
        </div>
      </div>
    </div>
  )
}
