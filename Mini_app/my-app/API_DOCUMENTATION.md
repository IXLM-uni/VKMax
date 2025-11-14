# File Converter API Documentation

This document provides comprehensive documentation for all API endpoints in the File Converter application.

## Base URL
All endpoints are relative to: `/api`

---

## User Management

### Create User
**POST** `/users`

Creates a new user in the system.

**Request Body:**
\`\`\`json
{
  "max_id": "string",
  "name": "string",
  "metadata": {}
}
\`\`\`

**Response:** `201 Created`
\`\`\`json
{
  "id": "string",
  "max_id": "string",
  "name": "string",
  "metadata": {},
  "created_at": "ISO8601 timestamp",
  "updated_at": "ISO8601 timestamp"
}
\`\`\`

---

### Get User
**GET** `/users/{userId}`

Retrieves user information by ID.

**Response:** `200 OK`
\`\`\`json
{
  "id": "string",
  "max_id": "string",
  "name": "string",
  "metadata": {},
  "created_at": "ISO8601 timestamp"
}
\`\`\`

---

### Delete User
**DELETE** `/users/{userId}`

Deletes a user and all associated data.

**Response:** `200 OK`
\`\`\`json
{
  "success": true
}
\`\`\`

---

## File Management

### Upload File
**POST** `/upload`

Uploads a file for conversion.

**Request:** `multipart/form-data`
- `file`: File to upload
- `user_id`: User ID
- `original_format`: Original file format

**Response:** `201 Created`
\`\`\`json
{
  "file_id": "string",
  "filename": "string",
  "size": number,
  "upload_date": "ISO8601 timestamp",
  "user_id": "string",
  "original_format": "string",
  "status": "uploaded"
}
\`\`\`

---

### Get File
**GET** `/files/{fileId}`

Retrieves file information and content.

**Response:** `200 OK`
\`\`\`json
{
  "id": "string",
  "user_id": "string",
  "format_id": "string",
  "filename": "string",
  "file_size": number,
  "mime_type": "string",
  "path": "string",
  "content": "base64_encoded_string",
  "created_at": "ISO8601 timestamp",
  "status": "string"
}
\`\`\`

---

### List Files
**GET** `/files?user_id={userId}&page={page}&limit={limit}`

Lists files with pagination.

**Query Parameters:**
- `user_id` (optional): Filter by user ID
- `page` (optional, default: 1): Page number
- `limit` (optional, default: 10): Items per page

**Response:** `200 OK`
\`\`\`json
{
  "files": [],
  "total": number,
  "page": number,
  "pages": number
}
\`\`\`

---

### Update File
**PATCH** `/files/{fileId}`

Updates file content or metadata.

**Request Body:**
\`\`\`json
{
  "content": "base64_encoded_string",
  "format": "string"
}
\`\`\`

**Response:** `200 OK`
\`\`\`json
{
  "id": "string",
  "user_id": "string",
  ...
}
\`\`\`

---

### Delete File
**DELETE** `/files/{fileId}`

Deletes a file.

**Response:** `200 OK`
\`\`\`json
{
  "success": true
}
\`\`\`

---

## Conversion Operations

### Convert File
**POST** `/convert`

Initiates a file conversion operation.

**Request Body:**
\`\`\`json
{
  "source_file_id": "string",
  "target_format": "string",
  "user_id": "string"
}
\`\`\`

**Response:** `201 Created`
\`\`\`json
{
  "operation_id": "string",
  "status": "queued",
  "estimated_time": number,
  "queue_position": number,
  "source_file_id": "string",
  "target_format": "string",
  "created_at": "ISO8601 timestamp"
}
\`\`\`

---

### Get Operation Status
**GET** `/operations/{operationId}`

Retrieves the status of a conversion operation.

**Response:** `200 OK`
\`\`\`json
{
  "operation_id": "string",
  "user_id": "string",
  "file_id": "string",
  "old_format": "string",
  "new_format": "string",
  "datetime": "ISO8601 timestamp",
  "status": "completed",
  "progress": 100,
  "result_file_id": "string"
}
\`\`\`

---

## Download

### Download File
**GET** `/download/{fileId}`

Downloads a converted file.

**Response:** `200 OK`
- Content-Type: `application/octet-stream`
- Content-Disposition: `attachment; filename="..."`

---

## Formats

### List Supported Formats
**GET** `/formats`

Lists all supported file formats.

**Response:** `200 OK`
\`\`\`json
[
  {
    "format_id": "string",
    "type": "string",
    "extension": "string",
    "mime_type": "string",
    "is_input": boolean,
    "is_output": boolean
  }
]
\`\`\`

---

## Graph Visualization

### Get Mermaid Chart
**GET** `/graph/{fileId}`

Retrieves the Mermaid diagram for a file.

**Response:** `200 OK`
\`\`\`json
{
  "file_id": "string",
  "mermaid_chart": "string | null",
  "generated_at": "ISO8601 timestamp"
}
\`\`\`

---

### Generate Mermaid Chart
**POST** `/graph/{fileId}`

Generates a new Mermaid diagram for a file.

**Response:** `200 OK`
\`\`\`json
{
  "file_id": "string",
  "mermaid_chart": "string",
  "generated_at": "ISO8601 timestamp"
}
\`\`\`

---

## LLM Integration

### Ask Question
**POST** `/llm`

Sends a question to the LLM for a response.

**Request Body:**
\`\`\`json
{
  "question": "string",
  "context": "string | null"
}
\`\`\`

**Response:** `200 OK`
\`\`\`json
{
  "answer": "string",
  "timestamp": "ISO8601 timestamp"
}
\`\`\`

---

## Status Codes

- `200 OK` - Request succeeded
- `201 Created` - Resource created successfully
- `400 Bad Request` - Invalid request parameters
- `404 Not Found` - Resource not found
- `500 Internal Server Error` - Server error

---

## Mock Data

All endpoints currently return mock data for demonstration purposes. The following mock files are available:

1. **sample-document.pdf** (ID: "1")
2. **financial-report.docx** (ID: "2")
3. **data-export.csv** (ID: "3")

Each mock file has a corresponding Mermaid diagram available through the graph API.
