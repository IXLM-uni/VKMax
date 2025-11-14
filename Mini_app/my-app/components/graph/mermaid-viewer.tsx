"use client"

import { useEffect, useRef, useState } from "react"
import mermaid from "mermaid"
import { Button } from "@/components/ui/button"
import { Loader2 } from "lucide-react"

interface MermaidViewerProps {
  chart: string | null
  fileId: string
  onGenerate: () => void
}

export function MermaidViewer({ chart, fileId, onGenerate }: MermaidViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    mermaid.initialize({
      startOnLoad: true,
      theme: "default",
      securityLevel: "loose",
    })
  }, [])

  useEffect(() => {
    const renderChart = async () => {
      if (containerRef.current && chart) {
        try {
          setError(null)
          containerRef.current.innerHTML = ""
          const { svg } = await mermaid.render(`mermaid-${fileId}`, chart)
          containerRef.current.innerHTML = svg
        } catch (err) {
          console.error("[v0] Mermaid render error:", err)
          setError("Failed to render chart")
        }
      }
    }
    renderChart()
  }, [chart, fileId])

  const handleGenerate = async () => {
    setIsLoading(true)
    await onGenerate()
    setIsLoading(false)
  }

  if (!chart) {
    return (
      <div className="w-full h-full flex items-center justify-center p-8">
        <div className="text-center space-y-4">
          <div className="w-16 h-16 mx-auto bg-muted rounded-full flex items-center justify-center">
            <svg
              className="w-8 h-8 text-muted-foreground"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              xmlns="http://www.w3.org/2000/svg"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
              />
            </svg>
          </div>
          <div className="space-y-2">
            <h3 className="text-lg font-semibold">No Graph Available</h3>
            <p className="text-sm text-muted-foreground max-w-md">
              Generate a Mermaid diagram to visualize the structure and relationships in this file.
            </p>
          </div>
          <Button
            onClick={handleGenerate}
            disabled={isLoading}
            className="bg-[#0077FF] hover:bg-[#0077FF]/90 text-white"
          >
            {isLoading && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
            Generate Graph
          </Button>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="w-full h-full flex items-center justify-center p-8">
        <div className="text-center space-y-2">
          <p className="text-sm text-destructive">{error}</p>
          <Button onClick={handleGenerate} variant="outline" size="sm">
            Retry
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div className="w-full h-full flex items-center justify-center p-4 md:p-8 overflow-auto">
      <div ref={containerRef} className="w-full max-w-4xl" />
    </div>
  )
}
