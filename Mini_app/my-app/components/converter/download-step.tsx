"use client"

import { Download, X, ChevronDown, MessageCircle, Network } from "lucide-react"
import { useRouter } from "next/navigation"
import { Button } from "@/components/ui/button"
import { useFileStore } from "@/lib/store"
import { FileIcon } from "@/components/file-icon"
import { cn } from "@/lib/utils"

export function DownloadStep() {
  const router = useRouter()
  const { files, removeFile, setCurrentStep } = useFileStore()

  const handleConvertMore = () => {
    setCurrentStep("upload")
  }

  const handleViewGraph = (fileId: string) => {
    router.push(`/graph?fileId=${fileId}`)
  }

  return (
    <div className="flex flex-col min-h-screen px-4 py-6 max-w-4xl mx-auto">
      <div className="space-y-6">
        <div className="text-center space-y-2">
          <h1 className="text-3xl md:text-4xl font-bold">Conversion Results</h1>
        </div>

        <div className="space-y-3">
          {files.map((file) => {
            const isConverted = file.status === "converted"
            const isConverting = file.status === "converting"
            const hasGraph = file.generateGraph

            return (
              <div key={file.id} className="flex flex-col gap-4 p-4 border rounded-lg bg-card">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-start gap-3 flex-1 min-w-0">
                    <FileIcon
                      format={file.targetFormat || file.originalFormat}
                      className="w-5 h-5 mt-0.5 flex-shrink-0"
                    />
                    <div className="flex-1 min-w-0">
                      <p className="font-medium truncate">{file.name}</p>
                      <div className="flex items-center gap-2 mt-1">
                        <span
                          className={cn(
                            "text-xs px-2 py-1 rounded font-medium",
                            isConverted && "bg-[#76E7F8]/20 text-[#76E7F8]",
                            isConverting && "bg-yellow-500/20 text-yellow-600",
                          )}
                        >
                          {isConverting ? "Converting..." : "Done"}
                        </span>
                      </div>
                    </div>
                  </div>
                  <Button variant="ghost" size="icon" onClick={() => removeFile(file.id)}>
                    <X className="w-4 h-4" />
                  </Button>
                </div>

                <div className="flex gap-2">
                  <Button
                    disabled={!isConverted}
                    className={cn(
                      "flex-1",
                      isConverted ? "bg-[#0077FF] hover:bg-[#0077FF]/90 text-white" : "bg-muted text-muted-foreground",
                    )}
                  >
                    <Download className="w-4 h-4 mr-2" />
                    Download
                  </Button>
                  <Button variant="outline" size="icon">
                    <ChevronDown className="w-4 h-4" />
                  </Button>
                </div>

                {isConverted && (
                  <div className="space-y-2">
                    {hasGraph && (
                      <Button
                        variant="outline"
                        className="w-full bg-transparent border-[#76E7F8] text-[#76E7F8] hover:bg-[#76E7F8]/10"
                        size="sm"
                        onClick={() => handleViewGraph(file.id)}
                      >
                        <Network className="w-4 h-4 mr-2" />
                        View Graph Visualization
                      </Button>
                    )}
                    <Button variant="outline" className="w-full bg-transparent" size="sm">
                      <MessageCircle className="w-4 h-4 mr-2" />
                      Ask LLM a Question
                    </Button>
                  </div>
                )}
              </div>
            )
          })}
        </div>

        <Button onClick={handleConvertMore} variant="outline" className="w-full py-6 text-lg bg-transparent">
          Convert More
        </Button>

        <p className="text-xs text-center text-muted-foreground">
          Converted files are automatically deleted after 8 hours to protect your privacy. Please download files before
          they are deleted.
        </p>
      </div>
    </div>
  )
}
