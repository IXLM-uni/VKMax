import { create } from "zustand"
import { persist } from "zustand/middleware"
import type { ConvertFile, ConverterStep } from "./types"

interface FileStore {
  files: ConvertFile[]
  currentStep: ConverterStep
  selectedFiles: string[]
  conversionType: "file" | "website"
  addFile: (file: ConvertFile) => void
  updateFile: (id: string, updates: Partial<ConvertFile>) => void
  removeFile: (id: string) => void
  setCurrentStep: (step: ConverterStep) => void
  selectFile: (id: string) => void
  deselectFile: (id: string) => void
  clearSelection: () => void
  setConversionType: (type: "file" | "website") => void
  reset: () => void
}

export const useFileStore = create<FileStore>()(
  persist(
    (set) => ({
      files: [],
      currentStep: "upload",
      selectedFiles: [],
      conversionType: "file", // Добавлено начальное значение
      addFile: (file) =>
        set((state) => ({
          files: [...state.files, file],
        })),
      updateFile: (id, updates) =>
        set((state) => ({
          files: state.files.map((f) => (f.id === id ? { ...f, ...updates } : f)),
        })),
      removeFile: (id) =>
        set((state) => ({
          files: state.files.filter((f) => f.id !== id),
          selectedFiles: state.selectedFiles.filter((fid) => fid !== id),
        })),
      setCurrentStep: (step) => set({ currentStep: step }),
      selectFile: (id) =>
        set((state) => ({
          selectedFiles: [...state.selectedFiles, id],
        })),
      deselectFile: (id) =>
        set((state) => ({
          selectedFiles: state.selectedFiles.filter((fid) => fid !== id),
        })),
      clearSelection: () => set({ selectedFiles: [] }),
      setConversionType: (type) => set({ conversionType: type }), // Добавлена функция установки типа
      reset: () => set({ files: [], currentStep: "upload", selectedFiles: [], conversionType: "file" }),
    }),
    {
      name: "file-converter-storage",
    },
  ),
)
