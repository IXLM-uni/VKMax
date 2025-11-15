// Руководство к файлу:
// - Этот файл содержит базовый UI-компонент Button.
// - Используйте `Button` для всех кликабельных действий (отправка форм, триггеры действий и т.п.).
// - Пропсы совместимы с обычной кнопкой HTML (`button`), дополнительно поддерживаются `variant` и `size`,
//   а также можно передавать `className` для кастомизации внешнего вида.

"use client"

import * as React from "react"

import { Slot } from "@radix-ui/react-slot"

import { cn } from "@/lib/utils"

type ButtonVariant = "default" | "ghost" | "outline"
type ButtonSize = "default" | "icon" | "lg" | "sm"

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  asChild?: boolean
  variant?: ButtonVariant
  size?: ButtonSize
}

function Button({
  className,
  type = "button",
  asChild = false,
  variant = "default",
  size = "default",
  ...props
}: ButtonProps) {
  const Comp = asChild ? Slot : "button"
  return (
    <Comp
      {...(!asChild && { type })}
      data-slot="button"
      className={cn(
        // Базовый стиль округлой кнопки
        "inline-flex items-center justify-center whitespace-nowrap rounded-full text-sm font-medium ring-offset-background",
        // Варианты оформления
        variant === "ghost"
          ? "bg-transparent hover:bg-muted text-foreground"
          : variant === "outline"
            ? "bg-transparent border border-border text-foreground"
            : "bg-primary text-primary-foreground shadow-sm",
        // Размеры
        size === "icon" ? "h-9 w-9" : size === "lg" ? "h-11 px-6" : size === "sm" ? "h-8 px-3" : "h-9 px-4",
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