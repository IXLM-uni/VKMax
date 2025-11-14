import { type NextRequest, NextResponse } from "next/server"

const mockMermaidCharts = new Map([
  [
    "1",
    `graph TD
    A[Document Processing] --> B[Format Detection]
    B --> C{Valid Format?}
    C -->|Yes| D[Parse Content]
    C -->|No| E[Error Handler]
    D --> F[Extract Metadata]
    F --> G[Structure Analysis]
    G --> H[Generate Output]
    H --> I[Quality Check]
    I --> J[Final Document]
    E --> K[Return Error]`,
  ],
  [
    "2",
    `graph LR
    A[Financial Report] --> B[Income Statement]
    A --> C[Balance Sheet]
    A --> D[Cash Flow]
    B --> E[Revenue Analysis]
    B --> F[Expense Breakdown]
    C --> G[Assets]
    C --> H[Liabilities]
    D --> I[Operating Activities]
    D --> J[Investing Activities]`,
  ],
  [
    "3",
    `graph TD
    A[Data Export] --> B[CSV Parser]
    B --> C[Column Detection]
    C --> D[Data Validation]
    D --> E[Type Inference]
    E --> F[Transform Data]
    F --> G[Excel Converter]
    G --> H[Format Cells]
    H --> I[Export File]`,
  ],
])

export async function GET(request: NextRequest, { params }: { params: Promise<{ fileId: string }> }) {
  const { fileId } = await params
  const mermaidChart = mockMermaidCharts.get(fileId)

  if (!mermaidChart) {
    return NextResponse.json({ mermaid_chart: null }, { status: 200 })
  }

  return NextResponse.json({
    file_id: fileId,
    mermaid_chart: mermaidChart,
    generated_at: new Date().toISOString(),
  })
}

export async function POST(request: NextRequest, { params }: { params: Promise<{ fileId: string }> }) {
  const { fileId } = await params

  // Mock generating a new mermaid chart
  const newChart = `graph TD
    A[File Upload] --> B[Processing]
    B --> C[Conversion]
    C --> D[Download]`

  mockMermaidCharts.set(fileId, newChart)

  return NextResponse.json({
    file_id: fileId,
    mermaid_chart: newChart,
    generated_at: new Date().toISOString(),
  })
}
