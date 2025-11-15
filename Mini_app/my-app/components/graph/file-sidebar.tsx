"use client"

import { X } from "lucide-react"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { useFileStore } from "@/lib/store"
import { FileIcon } from "@/components/file-icon"
import { cn } from "@/lib/utils"

interface FileSidebarProps {
  isOpen: boolean
  onClose: () => void
  selectedFileId: string | null
  onSelectFile: (fileId: string) => void
}

export function FileSidebar({ isOpen, onClose, selectedFileId, onSelectFile }: FileSidebarProps) {
  const { files } = useFileStore()

  return (
    <>
      {/* Overlay - Updated opacity to show 70% coverage */}
      {isOpen && <div className="fixed inset-0 bg-black/70 z-40" onClick={onClose} />}

      {/* Sidebar - Increased width to 70% on mobile */}
      <aside
        className={cn(
          "fixed top-0 left-0 h-full w-[70%] md:w-80 bg-card border-r z-50 transition-transform duration-300",
          isOpen ? "translate-x-0" : "-translate-x-full",
        )}
      >
        <div className="flex items-center justify-between p-4 border-b">
          <h2 className="font-semibold text-sm md:text-base">Мои файлы</h2>
          <Button variant="ghost" size="icon" onClick={onClose}>
            <X className="w-4 h-4" />
          </Button>
        </div>

        <ScrollArea className="h-[calc(100vh-64px)]">
          <div className="p-2 space-y-1">
            {files.length === 0 ? (
              <div className="p-4 text-center text-sm text-muted-foreground">
                Пока нет файлов. Загрузите файлы в конвертере, чтобы увидеть их здесь.
              </div>
            ) : (
              files.map((file) => (
                <button
                  key={file.id}
                  onClick={() => {
                    onSelectFile(file.id)
                    onClose()
                  }}
                  className={cn(
                    "w-full flex items-center gap-2 md:gap-3 p-2 md:p-3 rounded-lg transition-colors text-left",
                    selectedFileId === file.id ? "bg-[#0077FF]/10 text-[#0077FF]" : "hover:bg-muted",
                  )}
                >
                  <FileIcon
                    format={file.originalFormat}
                    className={cn(
                      "w-4 h-4 md:w-5 md:h-5 flex-shrink-0",
                      selectedFileId === file.id ? "text-[#0077FF]" : "",
                    )}
                  />
                  <div className="flex-1 min-w-0">
                    <p className="text-xs md:text-sm font-medium truncate">{file.name}</p>
                    <p className="text-[10px] md:text-xs text-muted-foreground">{file.originalFormat.toUpperCase()}</p>
                  </div>
                </button>
              ))
            )}
          </div>
        </ScrollArea>
      </aside>
    </>
  )
}
