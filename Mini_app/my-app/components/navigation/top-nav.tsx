"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { FileText, GitBranch } from "lucide-react"
import { cn } from "@/lib/utils"

export function TopNav() {
  const pathname = usePathname()

  const links = [
    {
      href: "/converter",
      label: "Converter",
      icon: FileText,
    },
    {
      href: "/graph",
      label: "Graph Visualization",
      icon: GitBranch,
    },
  ]

  return (
    <nav className="hidden md:block border-b bg-card">
      <div className="container mx-auto px-4">
        <div className="flex items-center gap-6 h-14">
          <Link href="/converter" className="font-bold text-lg">
            FileConverter
          </Link>
          <div className="flex gap-1 ml-auto">
            {links.map((link) => {
              const Icon = link.icon
              const isActive = pathname === link.href
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  className={cn(
                    "flex items-center gap-2 px-4 py-2 rounded-md transition-colors",
                    isActive
                      ? "bg-[#0077FF]/10 text-[#0077FF]"
                      : "text-muted-foreground hover:text-foreground hover:bg-muted",
                  )}
                >
                  <Icon className="w-4 h-4" />
                  <span className="font-medium">{link.label}</span>
                </Link>
              )
            })}
          </div>
        </div>
      </div>
    </nav>
  )
}
