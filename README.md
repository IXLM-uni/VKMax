API
COMPLETE API METHODS FOR DOCUMENT CONVERTER WITH WEBSITE SUPPORT
USER MANAGEMENT:─────────────────────────────────────────────────────────────────POST /usersBody: { "max_id": "string", "name": "string", "metadata": "json" }Desc: Создание пользователя
GET /users/{user_id}Response: { "id", "max_id", "name", "metadata", "created_at" }Desc: Получение данных пользователя
DELETE /users/{user_id}Desc: Удаление пользователя
GET /users/{user_id}/filesResponse: [{ "file_id", "filename", "format", "upload_date" }]Desc: Файлы пользователя
GET /users/{user_id}/operationsResponse: [{ "operation_id", "file_id/url", "old_format", "new_format", "datetime", "status" }]Desc: История операций
FILE MANAGEMENT:─────────────────────────────────────────────────────────────────POST /uploadBody: multipart/form-data (file, user_id, original_format)Response: { "file_id", "filename", "size", "upload_date" }Desc: Загрузка файла
POST /upload/websiteBody: { "user_id": "uuid", "url": "string", "name": "string", "format": "string" }Response: { "file_id", "operation_id", "status", "estimated_time" }Desc: Загрузка сайта по URL
GET /files/{file_id}Response: { "file_id", "user_id", "format", "content", "path", "created_at" }Desc: Получение файла
PATCH /files/{file_id}Body: { "content": "base64", "format": "string" }Desc: Обновление файла
DELETE /files/{file_id}Desc: Удаление файла
GET /files?user_id={user_id}&page={page}&limit={limit}Response: { "files": [], "total", "page", "pages" }Desc: Список файлов с пагинацией
CONVERSION OPERATIONS:─────────────────────────────────────────────────────────────────POST /convertBody: { "source_file_id": "uuid" | "url": "string", "target_format": "string", "user_id": "uuid" }Response: { "operation_id", "status", "estimated_time", "queue_position" }Desc: Универсальная конвертация (файл или сайт)
POST /convert/websiteBody: { "url": "string", "target_format": "string", "user_id": "uuid" }Response: { "operation_id", "status", "estimated_time" }Desc: Прямая конвертация сайта
POST /batch-convertBody: { "operations": [{ "source_file_id" | "url", "target_format" }], "user_id": "uuid" }Response: { "batch_id", "operations": [{ "operation_id", "status" }] }Desc: Пакетная конвертация
GET /operations/{operation_id}Response: { "operation_id", "user_id", "file_id/url", "old_format", "new_format", "datetime", "status", "progress" }Desc: Статус операции
GET /operations?user_id={user_id}&status={status}&type={file/website}Response: [{ "operation_id", "file_id/url", "status", "datetime", "type" }]Desc: Фильтр операций
DOWNLOAD & EXPORT:─────────────────────────────────────────────────────────────────GET /download/{file_id}Response: file binary streamHeaders: Content-Type: application/octet-stream, Content-Disposition: attachmentDesc: Скачивание файла
GET /download/{file_id}/previewResponse: file binary stream with preview headersDesc: Предпросмотр файла
WEBSITE-SPECIFIC:─────────────────────────────────────────────────────────────────GET /websites/{operation_id}/statusResponse: { "operation_id", "url", "status", "progress", "result_file_id" }Desc: Статус конвертации сайта
POST /websites/previewBody: { "url": "string" }Response: { "title", "description", "screenshot_url", "page_count" }Desc: Предпросмотр сайта
GET /websites/history?user_id={user_id}Response: [{ "operation_id", "url", "format", "datetime", "status" }]Desc: История конвертаций сайтов
FORMAT MANAGEMENT:─────────────────────────────────────────────────────────────────GET /formatsResponse: [{ "format_id", "type", "extension", "mime_type", "is_input", "is_output" }]Desc: Все форматы
GET /formats/inputResponse: [{ "format_id", "type", "extension", "is_input" }]Desc: Входные форматы
GET /formats/output?input_format={format}Response: [{ "format_id", "type", "extension", "is_output" }]Desc: Доступные выходные форматы
GET /supported-conversionsResponse: { "from_pdf": ["word", "jpg"], "from_jpg": ["pdf"], "from_csv": ["excel"], "from_website": ["pdf", "word"] }Desc: Матрица конвертаций
SYSTEM & ADMIN:─────────────────────────────────────────────────────────────────GET /healthResponse: { "status": "ok", "timestamp", "version" }Desc: Проверка здоровья
GET /statsHeaders: Authorization: Bearer {admin_token}Response: { "total_users", "total_files", "total_operations", "conversions_today", "website_conversions" }Desc: Статистика
POST /webhook/conversion-completeBody: { "operation_id", "status", "converted_file_id", "error_message", "type" }Desc: Webhook уведомлений

Database
FILES: id (PK, bigint) user_id (FK, bigint) format_id (FK, bigint) content (bytea) path (varchar) filename (varchar) file_size (bigint) mime_type (varchar) created_at (timestamp) status (varchar)

USERS: id (PK, bigint) max_id (varchar) name (varchar) metadata (jsonb) created_at (timestamp) updated_at (timestamp)stamp)
OPERATIONS: id (PK, bigint) user_id (FK, bigint) file_id (FK, bigint) result_file_id (FK, bigint) datetime (timestamp) old_format_id (FK, bigint) new_format_id (FK, bigint) status (varchar) error_message (text)
FORMATS: id (PK, bigint) type (varchar) prompt (varchar) file_extension (varchar) is_input (boolean) is_output (boolean) created_at (timestamp)
Requirements
pdfkit os sys argparse
sqlalchemy
from urllib.parse import quote
csv
asyncio
json
langchain
aiosqlite
httpx
fitz (PyMuPDF)
PyYAML   Библиотеки для конвертации # requirements.txt fitz>=0.1.0  # PyMuPDF - САМЫЙ БЫСТРЫЙ PDF pdf2docx>=0.5  # Для сложных PDF mammoth>=1.6  # DOCX -> HTML pandas>=2.0  # CSV/Excel операции (использует C-парсеры) openpyxl>=3.1  # Для Excel файлов pdfkit>=1.0  # HTML -> PDF (требует wkhtmltopdf) python-docx>=1.1  # DOCX операции html2text>=2020.1  # HTML -> текст beautifulsoup4>=4.12  # Парсинг HTML



Функциональные требования:
Пользователь должен иметь возможность: Загружать документ
Выбрать формат
Скачать файл
PDF → Word, JPG → PDF, CSV → Excel  Desktop
  Нефункциональные требования:
Минимальный UX UI
Быстрый
Персистентный

Out of scope: Поддерживать множество форматов


Сущности (БД):
Пользователи:
Операции:
Файлы:
Форматы:
