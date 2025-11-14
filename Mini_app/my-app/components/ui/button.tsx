// Руководство к файлу:
// - Этот файл содержит базовый UI-компонент Button.
// - Используйте `Button` для всех кликабельных действий (отправка форм, триггеры действий и т.п.).
// - Пропсы совместимы с обычной кнопкой HTML (`button`), дополнительно можно передавать `className` для кастомизации.

"use client"

import * as React from "react"

import { Slot } from "@radix-ui/react-slot"

import { cn } from "@/lib/utils"

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  asChild?: boolean
  // Можно расширить пропсы (variant, size и т.п.) при развитии дизайн-системы.
}

function Button({ className, type = "button", asChild = false, ...props }: ButtonProps) {
  const Comp = asChild ? Slot : "button"
  return (
    <Comp
      {...(!asChild && { type })}
      data-slot="button"
      className={cn(
        // Базовый стиль округлой кнопки
        "inline-flex items-center justify-center whitespace-nowrap rounded-full text-sm font-medium ring-offset-background",
        "bg-primary text-primary-foreground shadow-sm",
        // Размер по умолчанию
        "h-9 px-4",
        // Состояния
        "transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
        "disabled:pointer-events-none disabled:opacity-50",
        className,
      )}
      {...props}
    />
  )
}

export { Button }