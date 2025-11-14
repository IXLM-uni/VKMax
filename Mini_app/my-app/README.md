# File Converter Application

A mobile-first file converter application with graph visualization capabilities built with Next.js 16, React 19, TypeScript, Zustand, and React Flow.

## Features

### 1. File Converter (Page 1)
Three-step conversion process:
- **Upload Step**: Drag & drop or click to upload files
- **Format Selection Step**: Select output format for each file
- **Download Step**: Download converted files and ask LLM questions

### 2. Graph Visualization (Page 2)
- Sidebar with file management (click menu icon to open)
- Interactive JSON graph visualization of file structure using React Flow
- Generate graph button for files without visualization
- LLM chat for questions about file formats

## Tech Stack

- **Framework**: Next.js 16 (App Router)
- **UI**: React 19, Tailwind CSS v4, shadcn/ui
- **State Management**: Zustand with persistence
- **Graph Visualization**: JSON Graph + React Flow
- **Icons**: Lucide React

## Brand Colors

- `#FF3985` - Strong Pink (accents)
- `#0077FF` - Strong Blue (primary actions)
- `#76E7F8` - Strong Turquoise (secondary accents)

## Project Structure

```
app/
├── converter/          # File converter page
│   └── page.tsx
├── graph/              # Graph visualization page
│   └── page.tsx
├── layout.tsx          # Root layout with navigation
└── globals.css         # Global styles with brand colors

components/
├── converter/          # Converter components
│   ├── upload-step.tsx
│   ├── format-select-step.tsx
│   └── download-step.tsx
├── graph/              # Graph visualization components
│   ├── file-sidebar.tsx
│   ├── react-flow-viewer.tsx
│   └── llm-chat.tsx
├── navigation/         # Navigation components
│   ├── top-nav.tsx
│   └── bottom-nav.tsx
├── file-icon.tsx       # File type icons
└── format-badge.tsx    # Format display badge

lib/
├── store.ts            # Zustand state management
├── types.ts            # TypeScript types
└── api.ts              # API client functions
```

## Getting Started

```bash
# Install dependencies
npm install

# Run development server
npm run dev

# Build for production
npm run build

# Start production server
npm start
```

Open [http://localhost:3000](http://localhost:3000) to view the application.

## API Integration

The application is ready to integrate with your backend API. Update the `NEXT_PUBLIC_API_URL` environment variable to point to your API endpoint.

API endpoints used:
- `POST /upload` - Upload files
- `POST /convert` - Convert files
- `GET /operations/{id}` - Check conversion status
- `GET /download/{id}` - Download converted file
- `GET /users/{id}/files` - Get user files

See `lib/api.ts` for full API client implementation.

## Mobile-First Design

- Bottom navigation for mobile devices
- Top navigation for desktop
- Responsive layout with Tailwind breakpoints
- Touch-optimized interactions
- Sidebar drawer for graph page

## State Management

Files are persisted in localStorage using Zustand middleware. The state includes:
- File list with metadata
- Current converter step
- Selected files
- Conversion status

## Notes

- Maximum file size: 1GB (configurable)
- Files auto-delete after 8 hours for privacy
- LLM chat is simulation-ready (connect your LLM API)
- JSON graphs generated on-demand and rendered via React Flow
