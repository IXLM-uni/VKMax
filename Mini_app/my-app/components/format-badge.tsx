import { cn } from "@/lib/utils"

interface FormatBadgeProps {
  format: string
  className?: string
}

export function FormatBadge({ format, className }: FormatBadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center px-2 py-1 rounded text-xs font-medium uppercase",
        "bg-muted text-muted-foreground",
        className,
      )}
    >
      {format}
    </span>
  )
}
