"use client"

import { useState } from "react"
import { Send, X, Loader2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { ScrollArea } from "@/components/ui/scroll-area"
import { cn } from "@/lib/utils"

interface Message {
  id: string
  role: "user" | "assistant"
  content: string
}

interface LLMChatProps {
  isOpen: boolean
  onClose: () => void
}

export function LLMChat({ isOpen, onClose }: LLMChatProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState("")
  const [isLoading, setIsLoading] = useState(false)

  const handleSend = async () => {
    if (!input.trim() || isLoading) return

    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: "user",
      content: input,
    }

    setMessages((prev) => [...prev, userMessage])
    const questionText = input
    setInput("")
    setIsLoading(true)

    try {
      const response = await fetch("/api/llm", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          question: questionText,
          context: null,
        }),
      })

      const data = await response.json()

      const aiMessage: Message = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: data.answer,
      }
      setMessages((prev) => [...prev, aiMessage])
    } catch (error) {
      console.error("[v0] Error calling LLM API:", error)
      const errorMessage: Message = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: "Sorry, I encountered an error. Please try again.",
      }
      setMessages((prev) => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed bottom-4 right-4 w-80 md:w-96 h-[500px] bg-card border rounded-lg shadow-lg z-50 flex flex-col">
      <div className="flex items-center justify-between p-4 border-b">
        <h3 className="font-semibold">Ask AI</h3>
        <Button variant="ghost" size="icon" onClick={onClose}>
          <X className="w-4 h-4" />
        </Button>
      </div>

      {/* Инпут сверху контейнера */}
      <div className="p-4 border-b">
        <form
          onSubmit={(e) => {
            e.preventDefault()
            handleSend()
          }}
          className="flex gap-2"
        >
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask a question..."
            className="flex-1"
            disabled={isLoading}
          />
          <Button type="submit" size="icon" className="bg-[#0077FF] hover:bg-[#0077FF]/90" disabled={isLoading}>
            {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
          </Button>
        </form>
      </div>

      {/* Сообщения ниже инпута */}
      <ScrollArea className="flex-1 p-4">
        <div className="space-y-4">
          {messages.length === 0 ? (
            <div className="text-center text-sm text-muted-foreground py-8">
              Ask me anything about file formats, conversions, or general questions.
              <div className="mt-4 space-y-2">
                <p className="text-xs">Try asking:</p>
                <ul className="text-xs space-y-1">
                  <li>• What is PDF?</li>
                  <li>• What is DOCX?</li>
                  <li>• What is CSV?</li>
                </ul>
              </div>
            </div>
          ) : (
            messages.map((message) => (
              <div key={message.id} className={cn("flex", message.role === "user" ? "justify-end" : "justify-start")}>
                <div
                  className={cn(
                    "max-w-[80%] rounded-lg p-3 text-sm",
                    message.role === "user" ? "bg-[#0077FF] text-white" : "bg-muted",
                  )}
                >
                  {message.content}
                </div>
              </div>
            ))
          )}
          {isLoading && (
            <div className="flex justify-start">
              <div className="max-w-[80%] rounded-lg p-3 text-sm bg-muted flex items-center gap-2">
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Thinking...</span>
              </div>
            </div>
          )}
        </div>
      </ScrollArea>
    </div>
  )
}
