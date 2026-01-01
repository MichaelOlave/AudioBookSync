# AudioBookSync API Documentation

## Overview

AudioBookSync provides a secure, multi-user REST API for managing audiobook libraries from Audible. The API supports user authentication, library management, sync operations, real-time WebSocket updates, and audiobook file streaming with Range request support.

**Base URL**: `http://localhost:8000/api/v1`
**Version**: 1.0.0
**Documentation**: Available at `/docs` (Swagger UI) and `/redoc` (ReDoc)

---

## Table of Contents

1. [Authentication](#authentication)
2. [API Endpoints](#api-endpoints)
   - [Auth](#auth)
   - [Library](#library)
   - [Books](#books)
   - [Sync](#sync)
   - [Files](#files)
3. [WebSocket](#websocket)
4. [Error Handling](#error-handling)
5. [Rate Limiting](#rate-limiting)
6. [Examples](#examples)
7. [Deployment](#deployment)

---

## Authentication

### OAuth2 Password Flow

AudioBookSync uses **OAuth2 with JWT tokens** for authentication. All endpoints except `/auth/register` and `/auth/login` require authentication.

### Token Types

- **Access Token**: Short-lived token (default: 30 minutes) for API requests
- **Refresh Token**: Long-lived token (default: 7 days) for obtaining new access tokens

### Using Tokens

Include the access token in the `Authorization` header:

```bash
curl -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  https://localhost:8000/api/v1/library/
```

Or with Python requests:

```python
headers = {"Authorization": f"Bearer {access_token}"}
response = requests.get("http://localhost:8000/api/v1/library/", headers=headers)
```

### Token Refresh

When your access token expires, use the refresh token to get a new one:

```bash
curl -X POST http://localhost:8000/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "YOUR_REFRESH_TOKEN"}'
```

---

## API Endpoints

### Auth

#### Register User

Create a new user account.

**Endpoint**: `POST /auth/register`

**Request**:
```json
{
  "username": "john_doe",
  "email": "john@example.com",
  "password": "SecurePassword123!"
}
```

**Response** (201 Created):
```json
{
  "user_id": "uuid-123",
  "username": "john_doe",
  "email": "john@example.com",
  "created_at": "2025-12-20T20:00:00Z"
}
```

**Error Codes**:
- `409 Conflict`: Username or email already exists
- `422 Unprocessable Entity`: Invalid input (email format, password too short)

---

#### Login

Authenticate and receive tokens.

**Endpoint**: `POST /auth/login`

**Request**:
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=john_doe&password=SecurePassword123!"
```

**Response** (200 OK):
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer"
}
```

**Error Codes**:
- `401 Unauthorized`: Invalid username or password
- `403 Forbidden`: User account is inactive

---

#### Refresh Token

Get a new access token using a refresh token.

**Endpoint**: `POST /auth/refresh`

**Request**:
```json
{
  "refresh_token": "YOUR_REFRESH_TOKEN"
}
```

**Response** (200 OK):
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer"
}
```

**Error Codes**:
- `401 Unauthorized`: Invalid or expired refresh token
- `403 Forbidden`: User account is inactive

---

### Library

#### Get Library

Retrieve user's audiobook library with pagination.

**Endpoint**: `GET /library?page=1&page_size=50`

**Headers**:
```
Authorization: Bearer ACCESS_TOKEN
```

**Response** (200 OK):
```json
{
  "items": [
    {
      "asin": "B084L6Z6M3",
      "title": "Becoming",
      "author": "Michelle Obama",
      "narrator": "Michelle Obama",
      "rating": 4.8,
      "runtime_min": 1440,
      "user_id": "user-uuid",
      "purchase_date": "2023-01-15",
      "is_downloaded": true,
      "is_decrypted": true,
      "download_path": "/audiobooks/downloaded/B084L6Z6M3.m4b",
      "decrypted_path": "/audiobooks/decrypted/B084L6Z6M3.m4a",
      "created_at": "2023-01-15T10:30:00Z",
      "updated_at": "2023-01-15T10:30:00Z"
    }
  ],
  "total": 125,
  "page": 1,
  "page_size": 50,
  "pages": 3
}
```

**Query Parameters**:
- `page` (int, default: 1): Page number
- `page_size` (int, default: 50, max: 100): Items per page

---

#### Get Book Details

Get detailed information about a specific book.

**Endpoint**: `GET /library/{asin}`

**Example**:
```bash
curl -H "Authorization: Bearer ACCESS_TOKEN" \
  http://localhost:8000/api/v1/library/B084L6Z6M3
```

**Response** (200 OK):
```json
{
  "asin": "B084L6Z6M3",
  "title": "Becoming",
  "author": "Michelle Obama",
  "narrator": "Michelle Obama",
  "series_name": null,
  "description": "An intimate, powerful, and inspiring memoir...",
  "rating": 4.8,
  "runtime_min": 1440,
  "user_id": "user-uuid",
  "purchase_date": "2023-01-15",
  "is_downloaded": true,
  "is_decrypted": true,
  "download_path": "/audiobooks/downloaded/B084L6Z6M3.m4b",
  "decrypted_path": "/audiobooks/decrypted/B084L6Z6M3.m4a",
  "created_at": "2023-01-15T10:30:00Z",
  "updated_at": "2023-01-15T10:30:00Z"
}
```

**Error Codes**:
- `403 Forbidden`: Not authorized to access this book
- `404 Not Found`: Book not found

---

### Books

#### Add Book

Add a new book to user's library.

**Endpoint**: `POST /books/`

**Request**:
```json
{
  "asin": "B084L6Z6M3",
  "title": "Becoming",
  "author": "Michelle Obama",
  "narrator": "Michelle Obama",
  "runtime_min": 1440,
  "rating": 4.8
}
```

**Response** (201 Created):
```json
{
  "asin": "B084L6Z6M3",
  "title": "Becoming",
  "user_id": "user-uuid",
  ...
}
```

**Error Codes**:
- `400 Bad Request`: Invalid book data
- `422 Unprocessable Entity`: Validation error

---

#### Delete Book

Remove a book from library.

**Endpoint**: `DELETE /books/{asin}`

**Example**:
```bash
curl -X DELETE -H "Authorization: Bearer ACCESS_TOKEN" \
  http://localhost:8000/api/v1/books/B084L6Z6M3
```

**Response** (200 OK):
```json
{
  "message": "Book 'B084L6Z6M3' deleted successfully",
  "success": true
}
```

**Error Codes**:
- `403 Forbidden`: Not authorized to delete this book
- `404 Not Found`: Book not found

---

### Sync

#### Trigger Sync

Start a background library sync operation.

**Endpoint**: `POST /sync/`

**Request**:
```json
{
  "sync_type": "full"
}
```

**Sync Types**:
- `full`: Fetch all books from Audible library
- `incremental`: Fetch only new/updated books
- `manual`: Manual sync request

**Response** (202 Accepted):
```json
{
  "sync_id": "sync-uuid-123",
  "status": "in_progress",
  "message": "Sync initiated successfully, running in background",
  "sync_started_at": "2025-12-20T20:00:00Z"
}
```

**Note**: The sync runs asynchronously. Use WebSocket or polling to track progress.

---

#### Get Sync History

Retrieve user's sync operation history.

**Endpoint**: `GET /sync/history?page=1&page_size=10`

**Response** (200 OK):
```json
{
  "items": [
    {
      "sync_id": "sync-uuid-123",
      "user_id": "user-uuid",
      "sync_type": "full",
      "status": "completed",
      "sync_started_at": "2025-12-20T20:00:00Z",
      "sync_completed_at": "2025-12-20T20:15:30Z",
      "duration_seconds": 930.0,
      "books_found": 125,
      "books_added": 3,
      "books_downloaded": 2,
      "books_decrypted": 2,
      "errors_count": 0,
      "notes": "Sync completed successfully",
      "created_at": "2025-12-20T20:00:00Z",
      "updated_at": "2025-12-20T20:15:30Z"
    }
  ],
  "total": 5,
  "page": 1,
  "page_size": 10,
  "pages": 1
}
```

---

#### Get Sync Status

Get detailed status of a specific sync operation.

**Endpoint**: `GET /sync/{sync_id}`

**Example**:
```bash
curl -H "Authorization: Bearer ACCESS_TOKEN" \
  http://localhost:8000/api/v1/sync/sync-uuid-123
```

**Response** (200 OK):
```json
{
  "sync_id": "sync-uuid-123",
  "user_id": "user-uuid",
  "sync_type": "full",
  "status": "in_progress",
  "sync_started_at": "2025-12-20T20:00:00Z",
  "sync_completed_at": null,
  "duration_seconds": null,
  "books_found": 0,
  "books_added": 0,
  "books_downloaded": 0,
  "books_decrypted": 0,
  "errors_count": 0,
  "notes": null
}
```

**Sync Statuses**:
- `in_progress`: Sync is currently running
- `completed`: Sync finished successfully
- `partial`: Sync finished with some errors
- `failed`: Sync failed

---

### Files

#### Stream Audiobook

Stream a decrypted audiobook file with Range request support.

**Endpoint**: `GET /files/audiobook/{asin}`

**Example** (Full file):
```bash
curl -H "Authorization: Bearer ACCESS_TOKEN" \
  http://localhost:8000/api/v1/files/audiobook/B084L6Z6M3 \
  -o audiobook.m4a
```

**Example** (With Range header for seeking):
```bash
curl -H "Authorization: Bearer ACCESS_TOKEN" \
  -H "Range: bytes=0-1023" \
  http://localhost:8000/api/v1/files/audiobook/B084L6Z6M3 \
  -o audiobook.m4a
```

**Response Headers**:
- `Content-Type`: audio/mp4
- `Content-Length`: File size in bytes
- `Accept-Ranges`: bytes
- `Content-Range` (206 only): bytes START-END/TOTAL

**Status Codes**:
- `200 OK`: Full file stream
- `206 Partial Content`: Range request (with Content-Range header)

**Supports**:
- HTTP Range requests (HTTP 206 Partial Content)
- Audio player seeking
- Streaming from any byte offset
- Multiple concurrent connections

**Error Codes**:
- `403 Forbidden`: Not authorized to access this book
- `404 Not Found`: Book or decrypted file not found

---

## WebSocket

### Real-time Updates

Connect to receive real-time sync progress and status updates.

**Endpoint**: `WS /ws/updates?token=ACCESS_TOKEN`

**Authentication**: JWT access token required via query parameter

**JavaScript Example**:
```javascript
const token = "YOUR_ACCESS_TOKEN";
const ws = new WebSocket(`ws://localhost:8000/api/v1/ws/updates?token=${token}`);

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  console.log("Event:", message.type);
  console.log("Data:", message.data);
};

ws.onopen = () => {
  // Send heartbeat to keep connection alive
  ws.send(JSON.stringify({ type: "heartbeat" }));
};

ws.onerror = (error) => {
  console.error("WebSocket error:", error);
};
```

**Python Example**:
```python
import websocket
import json

token = "YOUR_ACCESS_TOKEN"
ws_url = f"ws://localhost:8000/api/v1/ws/updates?token={token}"

ws = websocket.WebSocketApp(
    ws_url,
    on_message=on_message,
    on_error=on_error,
    on_close=on_close
)

def on_message(ws, message):
    event = json.loads(message)
    print(f"Event: {event['type']}")
    print(f"Data: {event['data']}")

ws.run_forever()
```

### Event Types

#### sync.started
Sent when a sync operation begins.

```json
{
  "type": "sync.started",
  "data": {
    "sync_id": "sync-uuid-123",
    "sync_type": "full",
    "timestamp": 1703107200.5
  }
}
```

#### sync.progress
Sent periodically during sync operation.

```json
{
  "type": "sync.progress",
  "data": {
    "sync_id": "sync-uuid-123",
    "current_book": "B084L6Z6M3",
    "books_processed": 10,
    "books_total": 125,
    "progress_percent": 8.0,
    "status": "in_progress",
    "timestamp": 1703107220.5
  }
}
```

#### sync.completed
Sent when sync operation finishes successfully.

```json
{
  "type": "sync.completed",
  "data": {
    "sync_id": "sync-uuid-123",
    "status": "completed",
    "books_found": 125,
    "books_added": 3,
    "books_downloaded": 2,
    "books_decrypted": 2,
    "errors_count": 0,
    "duration_seconds": 930.0,
    "timestamp": 1703107230.5
  }
}
```

#### sync.failed
Sent when sync operation fails.

```json
{
  "type": "sync.failed",
  "data": {
    "sync_id": "sync-uuid-123",
    "error": "Connection timeout",
    "error_code": "CONNECTION_TIMEOUT",
    "timestamp": 1703107230.5
  }
}
```

#### download.progress
Sent during file downloads.

```json
{
  "type": "download.progress",
  "data": {
    "asin": "B084L6Z6M3",
    "filename": "B084L6Z6M3.m4b",
    "bytes_downloaded": 102400,
    "total_bytes": 1024000,
    "progress_percent": 10.0,
    "speed_kbps": 512.5,
    "timestamp": 1703107220.5
  }
}
```

---

## Error Handling

### Error Response Format

All errors follow a consistent JSON structure:

```json
{
  "error": "ErrorType",
  "message": "Human-readable error message",
  "status_code": 400,
  "details": {
    "field": "error description"
  }
}
```

### Common HTTP Status Codes

| Status | Meaning | Example |
|--------|---------|---------|
| 200 | OK | Successful request |
| 201 | Created | Resource created successfully |
| 202 | Accepted | Request accepted (async operation) |
| 206 | Partial Content | Range request successful |
| 400 | Bad Request | Invalid request body |
| 401 | Unauthorized | Missing/invalid token |
| 403 | Forbidden | Not authorized to access resource |
| 404 | Not Found | Resource not found |
| 409 | Conflict | Resource already exists (e.g., duplicate username) |
| 422 | Unprocessable Entity | Validation error |
| 500 | Internal Server Error | Server error |

### Error Examples

**Missing Token**:
```json
{
  "error": "AuthenticationError",
  "message": "Not authenticated",
  "status_code": 403
}
```

**Duplicate Username**:
```json
{
  "error": "ConflictError",
  "message": "Username 'john_doe' is already taken",
  "status_code": 409
}
```

**Book Not Found**:
```json
{
  "error": "ResourceNotFoundError",
  "message": "Book 'NOTEXIST' not found",
  "status_code": 404
}
```

---

## Rate Limiting

API requests are rate-limited to prevent abuse:

- **General endpoints**: 60 requests per minute
- **Login endpoint**: 5 requests per minute

Rate limit headers in response:
```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1703107260
```

When rate limit exceeded: `429 Too Many Requests`

---

## Examples

### Complete Authentication Flow

```bash
#!/bin/bash

API_URL="http://localhost:8000/api/v1"

# 1. Register new user
echo "Registering user..."
REGISTER_RESPONSE=$(curl -s -X POST $API_URL/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john_doe",
    "email": "john@example.com",
    "password": "SecurePassword123!"
  }')

echo "Register Response: $REGISTER_RESPONSE"

# 2. Login
echo "Logging in..."
LOGIN_RESPONSE=$(curl -s -X POST $API_URL/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=john_doe&password=SecurePassword123!")

echo "Login Response: $LOGIN_RESPONSE"

# Extract tokens (requires jq)
ACCESS_TOKEN=$(echo $LOGIN_RESPONSE | jq -r '.access_token')
REFRESH_TOKEN=$(echo $LOGIN_RESPONSE | jq -r '.refresh_token')

echo "Access Token: $ACCESS_TOKEN"
echo "Refresh Token: $REFRESH_TOKEN"

# 3. Get library
echo "Fetching library..."
curl -s -H "Authorization: Bearer $ACCESS_TOKEN" \
  $API_URL/library/ | jq .

# 4. Refresh token
echo "Refreshing token..."
curl -s -X POST $API_URL/auth/refresh \
  -H "Content-Type: application/json" \
  -d "{\"refresh_token\": \"$REFRESH_TOKEN\"}" | jq .
```

### Python Client Example

```python
import requests
from datetime import datetime, timedelta

class AudioBookSyncClient:
    def __init__(self, base_url, username, password):
        self.base_url = base_url
        self.username = username
        self.password = password
        self.access_token = None
        self.refresh_token = None
        self.token_expires_at = None

    def login(self):
        """Authenticate and get tokens."""
        response = requests.post(
            f"{self.base_url}/auth/login",
            data={"username": self.username, "password": self.password}
        )
        response.raise_for_status()
        data = response.json()
        self.access_token = data["access_token"]
        self.refresh_token = data["refresh_token"]
        self.token_expires_at = datetime.now() + timedelta(minutes=30)

    def _get_headers(self):
        """Get request headers with auth token."""
        return {"Authorization": f"Bearer {self.access_token}"}

    def get_library(self, page=1, page_size=50):
        """Get user's library."""
        response = requests.get(
            f"{self.base_url}/library/",
            headers=self._get_headers(),
            params={"page": page, "page_size": page_size}
        )
        response.raise_for_status()
        return response.json()

    def get_book(self, asin):
        """Get book details."""
        response = requests.get(
            f"{self.base_url}/library/{asin}",
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()

    def trigger_sync(self, sync_type="full"):
        """Start a sync operation."""
        response = requests.post(
            f"{self.base_url}/sync/",
            headers=self._get_headers(),
            json={"sync_type": sync_type}
        )
        response.raise_for_status()
        return response.json()

    def get_sync_status(self, sync_id):
        """Get sync operation status."""
        response = requests.get(
            f"{self.base_url}/sync/{sync_id}",
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()

    def stream_audiobook(self, asin, output_file):
        """Download audiobook file."""
        response = requests.get(
            f"{self.base_url}/files/audiobook/{asin}",
            headers=self._get_headers(),
            stream=True
        )
        response.raise_for_status()
        with open(output_file, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

# Usage
client = AudioBookSyncClient(
    "http://localhost:8000/api/v1",
    "john_doe",
    "SecurePassword123!"
)

client.login()
library = client.get_library()
print(f"Found {library['total']} books")

sync_response = client.trigger_sync()
print(f"Started sync: {sync_response['sync_id']}")
```

---

## Deployment

### Running the API

**Development**:
```bash
# Activate virtual environment
source .venv/bin/activate

# Run with auto-reload
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

**Production**:
```bash
# Using Gunicorn with Uvicorn workers
gunicorn src.api.main:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --access-logfile - \
    --error-logfile -
```

### Environment Variables

```bash
# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4
LOG_LEVEL=INFO

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/audiobooksync

# Security (IMPORTANT: Use strong secret in production)
SECRET_KEY=generate-with-openssl-rand-hex-32
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# CORS
CORS_ORIGINS=http://localhost:3000,https://example.com

# File Serving
MAX_FILE_SIZE=5368709120
CHUNK_SIZE=1048576

# Rate Limiting
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_LOGIN_PER_MINUTE=5
```

### Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["gunicorn", "src.api.main:app", \
     "--workers", "4", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--bind", "0.0.0.0:8000"]
```

---

## Support

For issues, feature requests, or questions:
- Check the [GitHub Issues](https://github.com/MichaelOlave/AudioBookSync/issues)
- Review test examples in `tests/api/`
- Check API documentation at `/docs` endpoint

---

## License

This API is part of the AudioBookSync project. See LICENSE for details.
