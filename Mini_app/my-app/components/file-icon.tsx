import { FileText, FileImage, FileSpreadsheet, Globe } from "lucide-react"

interface FileIconProps {
  format: string
  className?: string
}

export function FileIcon({ format, className = "w-5 h-5" }: FileIconProps) {
  const lowerFormat = format.toLowerCase()

  if (lowerFormat === "site") {
    return <Globe className={className} />
  }

  if (["pdf", "doc", "docx", "txt"].includes(lowerFormat)) {
    return <FileText className={className} />
  }

  if (["jpg", "jpeg", "png", "gif"].includes(lowerFormat)) {
    return <FileImage className={className} />
  }

  if (["xlsx", "xls", "csv"].includes(lowerFormat)) {
    return <FileSpreadsheet className={className} />
  }

  return <FileText className={className} />
}
