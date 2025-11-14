"use client"

import { useFileStore } from "@/lib/store"
import { UploadStep } from "@/components/converter/upload-step"
import { FormatSelectStep } from "@/components/converter/format-select-step"
import { DownloadStep } from "@/components/converter/download-step"

export default function ConverterPage() {
  const { currentStep } = useFileStore()

  return (
    <main className="min-h-screen">
      {currentStep === "upload" && <UploadStep />}
      {currentStep === "select-format" && <FormatSelectStep />}
      {currentStep === "download" && <DownloadStep />}
    </main>
  )
}
