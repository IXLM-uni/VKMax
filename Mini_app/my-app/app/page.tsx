"use client"

import { useRouter } from "next/navigation"
import { Upload, Globe } from "lucide-react"
import { Button } from "@/components/ui/button"
import { useFileStore } from "@/lib/store"

export default function HomePage() {
  const router = useRouter()
  const { setConversionType } = useFileStore()

  const handleFileConversion = () => {
    setConversionType("file")
    router.push("/converter")
  }

  const handleWebsiteConversion = () => {
    setConversionType("website")
    router.push("/converter")
  }

  return (
    <main className="min-h-screen flex items-center justify-center px-4">
      <div className="w-full max-w-2xl text-center space-y-8">
        <div className="space-y-4">
          <h1 className="text-4xl md:text-5xl font-bold text-balance">Конвертер Файлов</h1>
          <p className="text-lg md:text-xl text-muted-foreground text-pretty">
            Легко конвертируйте файлы из одного формата в другой онлайн
          </p>
        </div>

        <div className="space-y-4">
          <Button
            onClick={handleFileConversion}
            size="lg"
            className="w-full bg-[#0077FF] hover:bg-[#0077FF]/90 text-white py-8 text-lg gap-3"
          >
            <Upload className="w-6 h-6" />
            Выбрать Файлы
          </Button>

          <Button
            onClick={handleWebsiteConversion}
            size="lg"
            className="w-full bg-[#FF3985] hover:bg-[#FF3985]/90 text-white py-8 text-lg gap-3"
          >
            <Globe className="w-6 h-6" />
            Сайт в PDF
          </Button>
        </div>

        <div className="space-y-2 text-sm text-muted-foreground">
          <p>
            Максимальный размер файла 1GB.{" "}
            <a href="#" className="text-[#0077FF] hover:underline">
              Регистрация
            </a>{" "}
            для большего
          </p>
          <p>
            Продолжая, вы соглашаетесь с{" "}
            <a href="#" className="text-[#0077FF] hover:underline">
              Условиями использования
            </a>
            .
          </p>
        </div>
      </div>
    </main>
  )
}
