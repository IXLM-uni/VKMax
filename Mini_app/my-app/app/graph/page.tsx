"use client"

import { useState, useEffect } from "react"
import { Menu, MessageCircle } from "lucide-react"
import { useSearchParams } from "next/navigation"
import { Button } from "@/components/ui/button"
import { FileSidebar } from "@/components/graph/file-sidebar"
import { MermaidViewer } from "@/components/graph/mermaid-viewer"
import { LLMChat } from "@/components/graph/llm-chat"
import { useFileStore } from "@/lib/store"

export default function GraphPage() {
  const searchParams = useSearchParams()
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [chatOpen, setChatOpen] = useState(false)
  const [selectedFileId, setSelectedFileId] = useState<string | null>(null)
  const [mermaidChart, setMermaidChart] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const { files } = useFileStore()

  useEffect(() => {
    const fileIdFromUrl = searchParams.get("fileId")
    if (fileIdFromUrl) {
      setSelectedFileId(fileIdFromUrl)
    }
  }, [searchParams])

  useEffect(() => {
    const fetchMermaidChart = async () => {
      if (!selectedFileId) {
        setMermaidChart(null)
        return
      }

      setIsLoading(true)
      try {
        const response = await fetch(`/api/graph/${selectedFileId}`)
        const data = await response.json()
        setMermaidChart(data.mermaid_chart || null)
      } catch (error) {
        console.error("[v0] Error fetching mermaid chart:", error)
        setMermaidChart(null)
      } finally {
        setIsLoading(false)
      }
    }

    fetchMermaidChart()
  }, [selectedFileId])

  const handleGenerateSchema = async () => {
    if (!selectedFileId) return

    setIsLoading(true)
    try {
      const response = await fetch(`/api/graph/${selectedFileId}`, {
        method: "POST",
      })
      const data = await response.json()
      setMermaidChart(data.mermaid_chart)
    } catch (error) {
      console.error("[v0] Error generating mermaid chart:", error)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <main className="relative h-screen flex flex-col bg-background">
      {/* Header */}
      <header className="flex items-center justify-between p-4 border-b">
        <Button variant="ghost" size="icon" onClick={() => setSidebarOpen(true)}>
          <Menu className="w-5 h-5" />
        </Button>
        <h1 className="font-semibold">Graph Visualization</h1>
        <Button
          variant="ghost"
          size="icon"
          onClick={() => setChatOpen(!chatOpen)}
          className={chatOpen ? "bg-[#0077FF]/10 text-[#0077FF]" : ""}
        >
          <MessageCircle className="w-5 h-5" />
        </Button>
      </header>

      {/* Main Content */}
      <div className="flex-1 overflow-hidden">
        {!selectedFileId ? (
          <div className="h-full flex flex-col items-center justify-center p-8 text-center">
            <div className="max-w-md space-y-4">
              <div className="w-16 h-16 rounded-full bg-[#76E7F8]/20 flex items-center justify-center mx-auto">
                <Menu className="w-8 h-8 text-[#76E7F8]" />
              </div>
              <h2 className="text-2xl font-bold">No File Selected</h2>
              <p className="text-muted-foreground">
                Click the menu icon to open the sidebar and select a file to visualize its structure.
              </p>
            </div>
          </div>
        ) : (
          <MermaidViewer chart={mermaidChart} fileId={selectedFileId} onGenerate={handleGenerateSchema} />
        )}
      </div>

      {/* Sidebar */}
      <FileSidebar
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        selectedFileId={selectedFileId}
        onSelectFile={setSelectedFileId}
      />

      {/* Chat */}
      <LLMChat isOpen={chatOpen} onClose={() => setChatOpen(false)} />
    </main>
  )
}
