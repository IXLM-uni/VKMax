# Руководство к файлу (FAST_API/schemas.py)
# Назначение:
# - Централизованные Pydantic-схемы запросов/ответов FastAPI для VKMax.
# - Минимально достаточные поля под MVP (in-memory), совместимы с будущей БД.

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field


# --------------------------- Users ---------------------------

class UserCreateRequest(BaseModel):
    max_id: str
    name: str
    metadata: Optional[Dict[str, Any]] = None


class UserResponse(BaseModel):
    id: str
    max_id: str
    name: str
    metadata: Optional[Dict[str, Any]] = None
    created_at: str


# --------------------------- Files ---------------------------

class FileRecord(BaseModel):
    file_id: str = Field(..., alias="id")
    user_id: Optional[str] = None
    filename: str
    format: str
    size: int
    path: str
    created_at: str

    model_config = {"populate_by_name": True}


class FileUploadWebsiteRequest(BaseModel):
    user_id: str
    url: str
    name: Optional[str] = None
    format: str = "html"


class FileUploadResponse(BaseModel):
    file_id: str
    filename: str
    size: int
    upload_date: str


class FilesPage(BaseModel):
    files: List[FileRecord]
    total: int
    page: int
    pages: int


class FilePatchRequest(BaseModel):
    content: Optional[str] = None  # base64
    format: Optional[str] = None


# --------------------------- Operations ---------------------------

class ConvertRequest(BaseModel):
    source_file_id: Optional[str] = None
    url: Optional[str] = None
    target_format: str
    user_id: str


class ConvertWebsiteRequest(BaseModel):
    url: str
    target_format: str
    user_id: str


class BatchOperation(BaseModel):
    source_file_id: Optional[str] = None
    url: Optional[str] = None
    target_format: str


class BatchConvertRequest(BaseModel):
    operations: List[BatchOperation]
    user_id: str


class OperationResponse(BaseModel):
    operation_id: str
    status: str
    estimated_time: Optional[float] = None
    queue_position: Optional[int] = None


class OperationStatusResponse(BaseModel):
    operation_id: str
    user_id: Optional[str] = None
    file_id: Optional[str] = None
    url: Optional[str] = None
    old_format: Optional[str] = None
    new_format: Optional[str] = None
    datetime: str
    status: str
    progress: int = 0


class BatchConvertResponse(BaseModel):
    batch_id: str
    operations: List[OperationResponse]


# --------------------------- Websites ---------------------------

class WebsiteStatusResponse(BaseModel):
    operation_id: str
    url: str
    status: str
    progress: int = 0
    result_file_id: Optional[str] = None


class WebsitePreviewRequest(BaseModel):
    url: str


class WebsitePreviewResponse(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    screenshot_url: Optional[str] = None
    page_count: Optional[int] = None


class WebsiteHistoryItem(BaseModel):
    operation_id: str
    url: str
    format: str
    datetime: str
    status: str


# --------------------------- Formats ---------------------------

class FormatItem(BaseModel):
    format_id: str
    type: str
    extension: str
    mime_type: Optional[str] = None
    is_input: bool = False
    is_output: bool = False


# --------------------------- System ---------------------------

class HealthResponse(BaseModel):
    status: str = "ok"
    timestamp: str
    version: str


class StatsResponse(BaseModel):
    total_users: int
    total_files: int
    total_operations: int
    conversions_today: int
    website_conversions: int


class WebhookConversionComplete(BaseModel):
    operation_id: str
    status: str
    converted_file_id: Optional[str] = None
    error_message: Optional[str] = None
    type: Optional[str] = None
