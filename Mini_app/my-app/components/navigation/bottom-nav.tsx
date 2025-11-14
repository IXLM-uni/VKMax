"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { FileText, GitBranch } from "lucide-react"
import { cn } from "@/lib/utils"

export function BottomNav() {
  const pathname = usePathname()

  const links = [
    {
      href: "/converter",
      label: "Converter",
      icon: FileText,
    },
    {
      href: "/graph",
      label: "Graph",
      icon: GitBranch,
    },
  ]

  return (
    <nav className="fixed bottom-0 left-0 right-0 border-t bg-card z-30 md:hidden">
      <div className="flex items-center justify-around h-16">
        {links.map((link) => {
          const Icon = link.icon
          const isActive = pathname === link.href
          return (
            <Link
              key={link.href}
              href={link.href}
              className={cn(
                "flex flex-col items-center justify-center gap-1 flex-1 h-full transition-colors",
                isActive ? "text-[#0077FF]" : "text-muted-foreground hover:text-foreground",
              )}
            >
              <Icon className="w-5 h-5" />
              <span className="text-xs font-medium">{link.label}</span>
            </Link>
          )
        })}
      </div>
    </nav>
  )
}
