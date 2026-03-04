# AudioBookSync Frontend Implementation Guide

Complete guide for integrating AudioBookSync API endpoints into any frontend application.

---

## Table of Contents

1. [API Overview](#api-overview)
2. [Authentication](#authentication)
3. [Core Implementation](#core-implementation)
4. [Complete Endpoint Reference](#complete-endpoint-reference)
5. [Real-Time Updates with WebSockets](#real-time-updates-with-websockets)
6. [Error Handling](#error-handling)
7. [Best Practices](#best-practices)
8. [Framework-Specific Examples](#framework-specific-examples)

---

## API Overview

### Base URL
```
http://localhost:8000/api/v1
```

### Available Documentation
- **Interactive Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **OpenAPI JSON**: `http://localhost:8000/openapi.json`

### API Version
- **Current**: v1
- **Versioning Strategy**: Major version in path (`/api/v1/`)

### Key Features
- REST API with proper HTTP verbs
- JWT-based authentication
- Pagination for list endpoints
- Background task support (202 Accepted responses)
- Real-time updates via WebSocket
- Streaming audio with Range request support

---

## Authentication

### Overview

The API uses JWT (JSON Web Tokens) for stateless authentication. Tokens are obtained via login and can be refreshed for extended sessions.

- **Algorithm**: HS256
- **Access Token Duration**: 30 minutes
- **Refresh Token Duration**: 7 days

### Token Flow

```
1. User enters credentials
   ↓
2. Send POST /auth/login with username & password
   ↓
3. Receive access_token & refresh_token
   ↓
4. Store tokens securely (localStorage/sessionStorage for web, secure storage for mobile)
   ↓
5. Include access_token in Authorization header for all subsequent requests
   ↓
6. When access_token expires (30 min), use refresh_token to get new access_token
   ↓
7. When refresh_token expires (7 days), user must login again
```

### 1. Register User

**Endpoint**: `POST /auth/register`

**Request**:
```json
{
  "username": "john_doe",
  "email": "john@example.com",
  "password": "secure_password_123"
}
```

**Response** (201 Created):
```json
{
  "user_id": "uuid-here",
  "username": "john_doe",
  "email": "john@example.com",
  "created_at": "2025-01-20T10:30:00Z",
  "updated_at": "2025-01-20T10:30:00Z"
}
```

**Error Responses**:
- **409 Conflict**: Username or email already exists
- **422 Unprocessable Entity**: Invalid email format, password too short, etc.

### 2. Login

**Endpoint**: `POST /auth/login`

**Request** (Form Data):
```
username: john_doe
password: secure_password_123
```

Or as JSON:
```json
{
  "username": "john_doe",
  "password": "secure_password_123"
}
```

**Response** (200 OK):
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer"
}
```

**Error Responses**:
- **401 Unauthorized**: Invalid username or password

### 3. Refresh Token

**Endpoint**: `POST /auth/refresh`

**Request**:
```json
{
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

**Response** (200 OK):
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer"
}
```

**Error Responses**:
- **401 Unauthorized**: Invalid or expired refresh token

### Using Tokens in Requests

All authenticated endpoints require the `Authorization` header:

```
Authorization: Bearer {access_token}
```

**Example with cURL**:
```bash
curl -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..." \
  http://localhost:8000/api/v1/library/
```

---

## Core Implementation

### Setting Up API Client

Create a reusable API client that handles token management, requests, and error handling.

#### Core Features

Your API client should handle:
1. **Token Management**: Store, refresh, and validate tokens
2. **Request Handling**: Automatic authorization headers
3. **Error Handling**: Parse and handle API errors
4. **Retry Logic**: Automatically retry failed requests
5. **Request/Response Logging**: Debug API issues

#### Base API Client Interface

```javascript
class APIClient {
  constructor(baseURL = 'http://localhost:8000/api/v1') {
    this.baseURL = baseURL;
    this.accessToken = null;
    this.refreshToken = null;
    this.accessTokenExpiry = null;
  }

  // ============ Authentication Methods ============

  async register(username, email, password) {
    // POST /auth/register
  }

  async login(username, password) {
    // POST /auth/login
    // Store tokens from response
  }

  async refreshAccessToken() {
    // POST /auth/refresh
    // Use stored refresh token
  }

  // ============ Library Methods ============

  async getLibrary(page = 1, pageSize = 50) {
    // GET /library/?page=1&page_size=50
  }

  async getBook(asin) {
    // GET /library/{asin}
  }

  async fetchFromAudible(numResults = 50, page = 0) {
    // GET /audible/fetch?num_results=50&page=0
  }

  // ============ Book Management Methods ============

  async addBook(bookData) {
    // POST /books/
  }

  async deleteBook(asin) {
    // DELETE /books/{asin}
  }

  // ============ Sync Operations ============

  async startSync(syncType = 'full') {
    // POST /sync/
  }

  async getSyncHistory(page = 1, pageSize = 10) {
    // GET /sync/history
  }

  async getSyncStatus(syncId) {
    // GET /sync/{syncId}
  }

  // ============ Download Operations ============

  async startDownload(asin, title) {
    // POST /downloads/
  }

  async getDownloads(status = null, page = 1, pageSize = 50) {
    // GET /downloads/?status={status}&page=1&page_size=50
  }

  async getDownloadStatus(downloadId) {
    // GET /downloads/{downloadId}
  }

  // ============ Decryption Operations ============

  async startDecryption(asin, title) {
    // POST /decryptions/
  }

  async getDecryptions(status = null, page = 1, pageSize = 50) {
    // GET /decryptions/?status={status}&page=1&page_size=50
  }

  async getDecryptionStatus(decryptionId) {
    // GET /decryptions/{decryptionId}
  }

  // ============ File Streaming ============

  async streamAudiobook(asin, options = {}) {
    // GET /files/audiobook/{asin}
    // Supports Range requests for seeking
  }

  // ============ Settings ============

  async getAudibleCredentialsStatus() {
    // GET /settings/audible-credentials
  }

  async clearAudibleCredentials() {
    // DELETE /settings/audible-credentials
  }

  // ============ Audible OAuth ============

  async startAudibleAuth(countryCode = 'us') {
    // POST /audible/auth/start
  }

  async completeAudibleAuth(redirectUrl) {
    // POST /audible/auth/complete
  }

  // ============ Health Check ============

  async checkHealth() {
    // GET /health
  }

  // ============ Internal Methods ============

  async _request(method, endpoint, options = {}) {
    // Handles all HTTP requests with token management
  }

  async _ensureValidToken() {
    // Refresh token if about to expire
  }
}
```

---

## Complete Endpoint Reference

### 1. Authentication Endpoints

#### Register User
```
POST /auth/register
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| username | string | Yes | Unique, alphanumeric, 3-50 chars |
| email | string | Yes | Valid email, unique |
| password | string | Yes | Min 8 characters |

**Implementation Example**:
```javascript
async register(username, email, password) {
  return this._request('POST', '/auth/register', {
    body: JSON.stringify({ username, email, password })
  });
}
```

---

#### Login
```
POST /auth/login
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| username | string | Yes | Registered username |
| password | string | Yes | Account password |

**Implementation Example**:
```javascript
async login(username, password) {
  const response = await this._request('POST', '/auth/login', {
    body: JSON.stringify({ username, password })
  });

  if (response.access_token) {
    this.accessToken = response.access_token;
    this.refreshToken = response.refresh_token;
    // Store in secure storage
    this._storeTokens(response);
  }

  return response;
}
```

---

#### Refresh Token
```
POST /auth/refresh
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| refresh_token | string | Yes | Valid refresh token |

**Implementation Example**:
```javascript
async refreshAccessToken() {
  if (!this.refreshToken) {
    throw new Error('No refresh token available');
  }

  const response = await this._request('POST', '/auth/refresh', {
    body: JSON.stringify({ refresh_token: this.refreshToken }),
    skipAuth: true  // Don't add Authorization header
  });

  this.accessToken = response.access_token;
  this.refreshToken = response.refresh_token;
  this._storeTokens(response);

  return response;
}
```

---

### 2. Library Endpoints

#### Get User's Library
```
GET /library/?page=1&page_size=50
```

**Query Parameters**:
| Field | Type | Default | Max | Notes |
|-------|------|---------|-----|-------|
| page | integer | 1 | N/A | Page number, starts at 1 |
| page_size | integer | 50 | 100 | Items per page |

**Response** (200 OK):
```json
{
  "items": [
    {
      "asin": "B123ABC456",
      "title": "The Hobbit",
      "author": "J.R.R. Tolkien",
      "narrator": "Rob Inglis",
      "series_name": "Middle-earth",
      "description": "A fantasy adventure...",
      "rating": 4.8,
      "runtime_min": 660,
      "purchase_date": "2024-01-15T00:00:00Z",
      "is_downloaded": true,
      "is_decrypted": true,
      "download_path": "/downloads/B123ABC456.aax",
      "decrypted_path": "/decrypted/B123ABC456.m4b"
    }
  ],
  "total": 42,
  "page": 1,
  "page_size": 50,
  "pages": 1
}
```

**Implementation Example**:
```javascript
async getLibrary(page = 1, pageSize = 50) {
  return this._request('GET', '/library/', {
    query: { page, page_size: pageSize }
  });
}
```

---

#### Get Book Details
```
GET /library/{asin}
```

**Path Parameters**:
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| asin | string | Yes | 10-char Amazon ID |

**Response** (200 OK):
```json
{
  "asin": "B123ABC456",
  "title": "The Hobbit",
  "author": "J.R.R. Tolkien",
  "narrator": "Rob Inglis",
  "series_name": "Middle-earth",
  "description": "A fantasy adventure...",
  "rating": 4.8,
  "runtime_min": 660,
  "purchase_date": "2024-01-15T00:00:00Z",
  "is_downloaded": true,
  "is_decrypted": true,
  "download_path": "/downloads/B123ABC456.aax",
  "decrypted_path": "/decrypted/B123ABC456.m4b"
}
```

**Error Responses**:
- **404 Not Found**: Book not found in user's library
- **403 Forbidden**: User doesn't own this book

**Implementation Example**:
```javascript
async getBook(asin) {
  return this._request('GET', `/library/${asin}`);
}
```

---

#### Fetch Library from Audible
```
GET /audible/fetch?num_results=50&page=0
```

**Query Parameters**:
| Field | Type | Default | Max | Notes |
|-------|------|---------|-----|-------|
| num_results | integer | 50 | 1000 | Results per page from Audible |
| page | integer | 0 | N/A | Audible page number, starts at 0 |

**Response** (200 OK):
```json
{
  "items": [
    {
      "asin": "B123ABC456",
      "title": "The Hobbit",
      "author": "J.R.R. Tolkien",
      "narrator": "Rob Inglis",
      "series_name": "Middle-earth",
      "description": "A fantasy adventure...",
      "rating": 4.8,
      "runtime_min": 660
    }
  ],
  "total": 156,
  "page": 0,
  "num_results": 50,
  "user_id": "uuid-here"
}
```

**Error Responses**:
- **403 Forbidden**: User hasn't configured Audible credentials

**Implementation Example**:
```javascript
async fetchFromAudible(numResults = 50, page = 0) {
  return this._request('GET', '/library/audible/fetch', {
    query: { num_results: numResults, page }
  });
}
```

---

### 3. Book Management Endpoints

#### Add Book
```
POST /books/
```

**Request Body**:
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| asin | string | Yes | 10-char Amazon ID |
| title | string | Yes | Book title |
| author | string | Yes | Author name |
| narrator | string | Yes | Narrator name |
| runtime_min | integer | Yes | Runtime in minutes |
| series_name | string | No | Series name |
| description | string | No | Book description |
| rating | float | No | 0-5 rating |

**Response** (201 Created):
```json
{
  "asin": "B123ABC456",
  "title": "The Hobbit",
  "author": "J.R.R. Tolkien",
  "narrator": "Rob Inglis",
  "series_name": "Middle-earth",
  "description": "A fantasy adventure...",
  "rating": 4.8,
  "runtime_min": 660,
  "purchase_date": "2025-01-20T10:30:00Z",
  "is_downloaded": false,
  "is_decrypted": false
}
```

**Error Responses**:
- **400 Bad Request**: Missing required fields
- **422 Unprocessable Entity**: Invalid data format
- **409 Conflict**: Book already in library

**Implementation Example**:
```javascript
async addBook(bookData) {
  return this._request('POST', '/books/', {
    body: JSON.stringify(bookData)
  });
}
```

---

#### Delete Book
```
DELETE /books/{asin}
```

**Path Parameters**:
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| asin | string | Yes | 10-char Amazon ID |

**Response** (200 OK):
```json
{
  "success": true,
  "message": "Book deleted successfully"
}
```

**Error Responses**:
- **404 Not Found**: Book not found
- **403 Forbidden**: User doesn't own this book

**Implementation Example**:
```javascript
async deleteBook(asin) {
  return this._request('DELETE', `/books/${asin}`);
}
```

---

### 4. Sync Operations

#### Start Sync
```
POST /sync/
```

**Request Body**:
| Field | Type | Required | Options | Notes |
|-------|------|----------|---------|-------|
| sync_type | string | Yes | "full", "incremental", "manual" | Type of sync |

**Response** (202 Accepted):
```json
{
  "sync_id": "uuid-here",
  "status": "in_progress",
  "message": "Sync operation started",
  "sync_started_at": "2025-01-20T10:30:00Z"
}
```

**Implementation Example**:
```javascript
async startSync(syncType = 'full') {
  return this._request('POST', '/sync/', {
    body: JSON.stringify({ sync_type: syncType })
  });
}
```

**Note**: Sync runs in background. Use WebSocket or polling to monitor progress.

---

#### Get Sync History
```
GET /sync/history?page=1&page_size=10
```

**Query Parameters**:
| Field | Type | Default | Max | Notes |
|-------|------|---------|-----|-------|
| page | integer | 1 | N/A | Page number |
| page_size | integer | 10 | 50 | Items per page |

**Response** (200 OK):
```json
{
  "items": [
    {
      "sync_id": "uuid-here",
      "status": "completed",
      "sync_type": "full",
      "books_found": 45,
      "books_added": 3,
      "books_downloaded": 1,
      "books_decrypted": 1,
      "errors_count": 0,
      "duration_seconds": 125,
      "started_at": "2025-01-20T10:30:00Z",
      "completed_at": "2025-01-20T10:32:05Z"
    }
  ],
  "total": 12,
  "page": 1,
  "page_size": 10,
  "pages": 2
}
```

**Implementation Example**:
```javascript
async getSyncHistory(page = 1, pageSize = 10) {
  return this._request('GET', '/sync/history', {
    query: { page, page_size: pageSize }
  });
}
```

---

#### Get Sync Status
```
GET /sync/{sync_id}
```

**Path Parameters**:
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| sync_id | string | Yes | UUID from sync start response |

**Response** (200 OK):
```json
{
  "sync_id": "uuid-here",
  "status": "in_progress",
  "sync_type": "full",
  "books_found": 45,
  "books_added": 3,
  "books_downloaded": 1,
  "books_decrypted": 1,
  "errors_count": 0,
  "duration_seconds": 45,
  "started_at": "2025-01-20T10:30:00Z",
  "completed_at": null
}
```

**Status Values**: `pending`, `in_progress`, `completed`, `failed`

**Implementation Example**:
```javascript
async getSyncStatus(syncId) {
  return this._request('GET', `/sync/${syncId}`);
}
```

---

### 5. Download Operations

#### Start Download
```
POST /downloads/
```

**Request Body**:
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| asin | string | Yes | 10-char Amazon ID |
| title | string | Yes | Book title (for display) |

**Response** (202 Accepted):
```json
{
  "download_id": "uuid-here",
  "status": "in_progress",
  "message": "Download started"
}
```

**Implementation Example**:
```javascript
async startDownload(asin, title) {
  return this._request('POST', '/downloads/', {
    body: JSON.stringify({ asin, title })
  });
}
```

---

#### Get Downloads
```
GET /downloads/?status=in_progress&page=1&page_size=50
```

**Query Parameters**:
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| status | string | No | Filter: "pending", "in_progress", "completed", "failed" |
| page | integer | No | Page number (default 1) |
| page_size | integer | No | Items per page (default 50, max 100) |

**Response** (200 OK):
```json
{
  "items": [
    {
      "download_id": "uuid-here",
      "asin": "B123ABC456",
      "title": "The Hobbit",
      "status": "in_progress",
      "progress_percent": 45,
      "downloaded_bytes": 524288,
      "total_bytes": 1048576,
      "error_message": null
    }
  ],
  "total": 3,
  "page": 1,
  "page_size": 50,
  "pages": 1
}
```

**Implementation Example**:
```javascript
async getDownloads(status = null, page = 1, pageSize = 50) {
  const query = { page, page_size: pageSize };
  if (status) query.status = status;

  return this._request('GET', '/downloads/', { query });
}
```

---

#### Get Download Status
```
GET /downloads/{download_id}
```

**Path Parameters**:
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| download_id | string | Yes | UUID from start response |

**Response** (200 OK):
```json
{
  "download_id": "uuid-here",
  "asin": "B123ABC456",
  "title": "The Hobbit",
  "status": "completed",
  "progress_percent": 100,
  "downloaded_bytes": 1048576,
  "total_bytes": 1048576,
  "error_message": null,
  "completed_at": "2025-01-20T10:45:00Z"
}
```

**Implementation Example**:
```javascript
async getDownloadStatus(downloadId) {
  return this._request('GET', `/downloads/${downloadId}`);
}
```

---

### 6. Decryption Operations

#### Start Decryption
```
POST /decryptions/
```

**Request Body**:
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| asin | string | Yes | Must be downloaded first |
| title | string | Yes | Book title (for display) |

**Response** (202 Accepted):
```json
{
  "decryption_id": "uuid-here",
  "status": "in_progress",
  "message": "Decryption started"
}
```

**Implementation Example**:
```javascript
async startDecryption(asin, title) {
  return this._request('POST', '/decryptions/', {
    body: JSON.stringify({ asin, title })
  });
}
```

---

#### Get Decryptions
```
GET /decryptions/?status=completed&page=1&page_size=50
```

**Query Parameters**: Same as Downloads

**Response** (200 OK):
```json
{
  "items": [
    {
      "decryption_id": "uuid-here",
      "asin": "B123ABC456",
      "title": "The Hobbit",
      "status": "completed",
      "progress_percent": 100,
      "error_message": null,
      "completed_at": "2025-01-20T10:50:00Z"
    }
  ],
  "total": 2,
  "page": 1,
  "page_size": 50,
  "pages": 1
}
```

**Implementation Example**:
```javascript
async getDecryptions(status = null, page = 1, pageSize = 50) {
  const query = { page, page_size: pageSize };
  if (status) query.status = status;

  return this._request('GET', '/decryptions/', { query });
}
```

---

#### Get Decryption Status
```
GET /decryptions/{decryption_id}
```

**Response** (200 OK):
```json
{
  "decryption_id": "uuid-here",
  "asin": "B123ABC456",
  "title": "The Hobbit",
  "status": "completed",
  "progress_percent": 100,
  "error_message": null
}
```

**Implementation Example**:
```javascript
async getDecryptionStatus(decryptionId) {
  return this._request('GET', `/decryptions/${decryptionId}`);
}
```

---

### 7. File Streaming

#### Stream Audiobook
```
GET /files/audiobook/{asin}
```

**Path Parameters**:
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| asin | string | Yes | Must be decrypted |

**Query Parameters**:
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| download | boolean | No | If true, returns download instead of stream |

**Headers** (Optional):
```
Range: bytes=0-1048575
```

**Response** (200 OK or 206 Partial Content):
```
Content-Type: audio/mp4
Content-Length: 1048576
Accept-Ranges: bytes
```

**Streaming Features**:
- Supports HTTP Range requests for seeking
- Returns 206 Partial Content when Range header provided
- Useful for audio players that need to skip ahead

**Implementation Example** (Basic):
```javascript
async streamAudiobook(asin, options = {}) {
  const query = {};
  if (options.download) query.download = true;

  return this._request('GET', `/files/audiobook/${asin}`, {
    query,
    responseType: 'blob'  // Get audio blob
  });
}
```

**Implementation Example** (With Range Support):
```javascript
async streamAudiobookWithRange(asin, startByte, endByte) {
  const headers = {
    'Range': `bytes=${startByte}-${endByte}`
  };

  return this._request('GET', `/files/audiobook/${asin}`, {
    headers,
    responseType: 'blob'
  });
}
```

---

### 8. Settings Endpoints

#### Get Audible Credentials Status
```
GET /settings/audible-credentials
```

**Response** (200 OK):
```json
{
  "auth_configured": true,
  "audible_email": "user@example.com",
  "device_name": "iPhone",
  "has_activation_bytes": true
}
```

**Note**: Actual tokens are never returned for security

**Implementation Example**:
```javascript
async getAudibleCredentialsStatus() {
  return this._request('GET', '/settings/audible-credentials');
}
```

---

#### Clear Audible Credentials
```
DELETE /settings/audible-credentials
```

**Response** (200 OK):
```json
{
  "success": true,
  "message": "Audible credentials cleared"
}
```

**Implementation Example**:
```javascript
async clearAudibleCredentials() {
  return this._request('DELETE', '/settings/audible-credentials');
}
```

---

### 9. Audible Authentication (OAuth)

#### Start Audible Auth
```
POST /audible/auth/start
```

**Request Body**:
| Field | Type | Required | Options | Notes |
|-------|------|----------|---------|-------|
| country_code | string | Yes | "us", "de", "uk", etc. | Audible region |

**Response** (200 OK):
```json
{
  "login_url": "https://www.audible.com/auth/start?state=..."
}
```

**Implementation Example**:
```javascript
async startAudibleAuth(countryCode = 'us') {
  const response = await this._request('POST', '/audible/auth/start', {
    body: JSON.stringify({ country_code: countryCode })
  });

  // Open in browser
  window.location.href = response.login_url;

  return response;
}
```

---

#### Complete Audible Auth
```
POST /audible/auth/complete
```

**Request Body**:
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| redirect_url | string | Yes | Full URL from Audible redirect |

**Response** (200 OK):
```json
{
  "success": true,
  "message": "Audible credentials saved successfully",
  "auth_file_path": "/path/to/auth.json"
}
```

**Implementation Example**:
```javascript
async completeAudibleAuth(redirectUrl) {
  return this._request('POST', '/audible/auth/complete', {
    body: JSON.stringify({ redirect_url: redirectUrl })
  });
}
```

---

### 10. Health Check

#### Check API Health
```
GET /health
```

**Response** (200 OK):
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "api_status": "running",
  "minio_status": "connected"
}
```

**Implementation Example**:
```javascript
async checkHealth() {
  return this._request('GET', '/health', {
    skipAuth: true
  });
}
```

---

## Real-Time Updates with WebSockets

### WebSocket Connection

Connect to receive real-time updates about background operations.

**Endpoint**: `WS /updates`

**Authentication**: Include JWT token as query parameter

**Connection String**:
```
ws://localhost:8000/api/v1/ws/updates?token=ACCESS_TOKEN
```

### Connection Lifecycle

```javascript
const token = localStorage.getItem('accessToken');
const ws = new WebSocket(`ws://localhost:8000/api/v1/ws/updates?token=${token}`);

// Handle connection
ws.onopen = (event) => {
  console.log('WebSocket connected');
};

// Handle incoming messages
ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  console.log('Received:', message);
};

// Handle errors
ws.onerror = (error) => {
  console.error('WebSocket error:', error);
};

// Handle disconnection
ws.onclose = (event) => {
  console.log('WebSocket disconnected');
};
```

### Message Types

#### Sync Events

**sync.started**:
```json
{
  "type": "sync.started",
  "sync_id": "uuid-here",
  "sync_type": "full",
  "timestamp": "2025-01-20T10:30:00Z"
}
```

**sync.progress**:
```json
{
  "type": "sync.progress",
  "sync_id": "uuid-here",
  "books_found": 45,
  "books_added": 3,
  "books_downloaded": 1,
  "books_decrypted": 0,
  "errors_count": 0,
  "timestamp": "2025-01-20T10:30:30Z"
}
```

**sync.completed**:
```json
{
  "type": "sync.completed",
  "sync_id": "uuid-here",
  "books_found": 45,
  "books_added": 3,
  "books_downloaded": 1,
  "books_decrypted": 1,
  "errors_count": 0,
  "duration_seconds": 125,
  "timestamp": "2025-01-20T10:32:05Z"
}
```

**sync.failed**:
```json
{
  "type": "sync.failed",
  "sync_id": "uuid-here",
  "error": "Failed to fetch from Audible",
  "timestamp": "2025-01-20T10:31:00Z"
}
```

#### Download Events

**download.progress**:
```json
{
  "type": "download.progress",
  "download_id": "uuid-here",
  "asin": "B123ABC456",
  "progress_percent": 45,
  "downloaded_bytes": 524288,
  "total_bytes": 1048576,
  "timestamp": "2025-01-20T10:30:30Z"
}
```

#### Heartbeat

**ping/pong**: Server sends periodic heartbeats; respond with pong

```json
{ "type": "ping" }
```

Response:
```json
{ "type": "pong" }
```

### WebSocket Client Implementation

```javascript
class WebSocketClient {
  constructor(token, baseURL = 'ws://localhost:8000') {
    this.token = token;
    this.baseURL = baseURL;
    this.ws = null;
    this.handlers = {};
    this.isConnecting = false;
  }

  connect() {
    if (this.isConnecting || this.ws?.readyState === WebSocket.OPEN) {
      return;
    }

    this.isConnecting = true;
    const wsUrl = `${this.baseURL}/api/v1/ws/updates?token=${this.token}`;

    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      console.log('WebSocket connected');
      this.isConnecting = false;
      this._emit('connected');
    };

    this.ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        this._handleMessage(message);
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error);
      }
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      this._emit('error', error);
    };

    this.ws.onclose = () => {
      console.log('WebSocket disconnected');
      this.isConnecting = false;
      this._emit('disconnected');
      // Attempt reconnection
      setTimeout(() => this.connect(), 5000);
    };
  }

  _handleMessage(message) {
    const { type } = message;

    // Handle ping
    if (type === 'ping') {
      this.send({ type: 'pong' });
      return;
    }

    this._emit(type, message);
    this._emit('message', message);
  }

  on(event, callback) {
    if (!this.handlers[event]) {
      this.handlers[event] = [];
    }
    this.handlers[event].push(callback);
  }

  off(event, callback) {
    if (this.handlers[event]) {
      this.handlers[event] = this.handlers[event].filter(cb => cb !== callback);
    }
  }

  _emit(event, data) {
    if (this.handlers[event]) {
      this.handlers[event].forEach(callback => callback(data));
    }
  }

  send(message) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    }
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
}

// Usage
const wsClient = new WebSocketClient(accessToken);

wsClient.on('sync.progress', (message) => {
  console.log(`Sync progress: ${message.books_added} added`);
});

wsClient.on('sync.completed', (message) => {
  console.log('Sync completed!');
});

wsClient.on('download.progress', (message) => {
  console.log(`Downloaded: ${message.progress_percent}%`);
});

wsClient.connect();
```

---

## Error Handling

### Standard Error Response Format

All errors follow this format:

```json
{
  "error": "Error type",
  "message": "Human-readable message",
  "status_code": 400,
  "details": {
    "field": "Additional context"
  }
}
```

### Common Error Codes

| Status | Error | Meaning | Solution |
|--------|-------|---------|----------|
| 400 | Bad Request | Invalid request format or parameters | Check request body and parameters |
| 401 | Unauthorized | Missing or invalid token | Login again, refresh token, check token expiry |
| 403 | Forbidden | Insufficient permissions | User doesn't own resource or inactive |
| 404 | Not Found | Resource doesn't exist | Check ID/ASIN, verify resource exists |
| 409 | Conflict | Resource already exists | Check for duplicates (username, email, book) |
| 422 | Unprocessable Entity | Validation failed | Check field types and formats |
| 500 | Internal Server Error | Server error | Check server logs, retry later |

### Error Handling Implementation

```javascript
async _request(method, endpoint, options = {}) {
  try {
    // Ensure valid token
    if (!options.skipAuth) {
      await this._ensureValidToken();
    }

    const headers = {
      'Content-Type': 'application/json',
      ...options.headers
    };

    if (!options.skipAuth && this.accessToken) {
      headers['Authorization'] = `Bearer ${this.accessToken}`;
    }

    const url = `${this.baseURL}${endpoint}`;
    const response = await fetch(url, {
      method,
      headers,
      body: options.body
    });

    // Handle different status codes
    if (response.status === 401) {
      // Token expired, try refresh
      await this.refreshAccessToken();
      // Retry request with new token
      return this._request(method, endpoint, options);
    }

    if (!response.ok) {
      const error = await response.json();
      throw new APIError(
        error.message || 'Unknown error',
        response.status,
        error.details
      );
    }

    return await response.json();

  } catch (error) {
    console.error(`Request failed: ${method} ${endpoint}`, error);
    throw error;
  }
}

class APIError extends Error {
  constructor(message, statusCode, details = {}) {
    super(message);
    this.name = 'APIError';
    this.statusCode = statusCode;
    this.details = details;
  }
}

// Usage
try {
  await apiClient.getLibrary();
} catch (error) {
  if (error instanceof APIError) {
    if (error.statusCode === 401) {
      // Handle authentication error
      redirectToLogin();
    } else if (error.statusCode === 404) {
      // Handle not found
      showNotification('Resource not found');
    } else {
      // Handle other errors
      showNotification(error.message);
    }
  }
}
```

---

## Best Practices

### 1. Token Management

**Store tokens securely**:
```javascript
// Web
localStorage.setItem('accessToken', response.access_token);
sessionStorage.setItem('refreshToken', response.refresh_token);

// Mobile
// Use secure storage (iOS Keychain, Android Secure Enclave)
```

**Automatically refresh tokens**:
```javascript
async _ensureValidToken() {
  const expiryTime = localStorage.getItem('tokenExpiry');
  const now = Date.now();

  // Refresh if within 5 minutes of expiry
  if (expiryTime && now > expiryTime - 5 * 60 * 1000) {
    await this.refreshAccessToken();
  }
}
```

**Clear tokens on logout**:
```javascript
logout() {
  localStorage.removeItem('accessToken');
  localStorage.removeItem('refreshToken');
  this.accessToken = null;
  this.refreshToken = null;
}
```

### 2. Request Optimization

**Use pagination for lists**:
```javascript
// Good: Load first page, then load more on demand
const page1 = await apiClient.getLibrary(1, 50);

// Avoid: Fetching all items at once
for (let page = 1; page <= 100; page++) {
  await apiClient.getLibrary(page, 50);
}
```

**Cache frequently accessed data**:
```javascript
class CachedAPIClient {
  constructor(apiClient) {
    this.apiClient = apiClient;
    this.cache = new Map();
  }

  async getBook(asin) {
    const cacheKey = `book:${asin}`;

    if (this.cache.has(cacheKey)) {
      return this.cache.get(cacheKey);
    }

    const book = await this.apiClient.getBook(asin);
    this.cache.set(cacheKey, book);

    return book;
  }

  invalidateCache() {
    this.cache.clear();
  }
}
```

### 3. WebSocket Best Practices

**Maintain persistent connection**:
```javascript
// Auto-reconnect with exponential backoff
let reconnectDelay = 1000;
const MAX_DELAY = 30000;

ws.onclose = () => {
  setTimeout(() => {
    wsClient.connect();
    reconnectDelay = Math.min(reconnectDelay * 2, MAX_DELAY);
  }, reconnectDelay);
};
```

**Handle connection interruptions**:
```javascript
// Use both polling and WebSocket for reliability
const pollInterval = setInterval(async () => {
  if (wsClient.ws?.readyState !== WebSocket.OPEN) {
    // Fallback to polling if WebSocket not connected
    const status = await apiClient.getSyncStatus(syncId);
    updateUI(status);
  }
}, 5000);

// Stop polling when WebSocket reconnects
wsClient.on('connected', () => {
  clearInterval(pollInterval);
});
```

### 4. Background Operations

**Poll or monitor via WebSocket**:
```javascript
async startAndMonitorSync(syncType = 'full') {
  // Start sync
  const { sync_id } = await apiClient.startSync(syncType);

  // Option 1: WebSocket monitoring (preferred)
  wsClient.on('sync.completed', (message) => {
    if (message.sync_id === sync_id) {
      handleSyncComplete(message);
    }
  });

  // Option 2: Polling fallback
  const pollInterval = setInterval(async () => {
    const status = await apiClient.getSyncStatus(sync_id);
    if (status.status === 'completed' || status.status === 'failed') {
      clearInterval(pollInterval);
      handleSyncComplete(status);
    }
  }, 2000);
}
```

**Handle long-running operations**:
```javascript
// Display progress to user
const handleOperationProgress = (message) => {
  const percent = Math.round(
    (message.progress_percent || 0)
  );

  updateProgressBar(percent);

  // Show details
  if (message.books_downloaded !== undefined) {
    updateStats({
      added: message.books_added,
      downloaded: message.books_downloaded,
      decrypted: message.books_decrypted,
      errors: message.errors_count
    });
  }
};
```

### 5. User Experience

**Indicate operation status**:
```javascript
// Show user what's happening
const statuses = {
  'pending': 'Queued...',
  'in_progress': 'Processing...',
  'completed': 'Done!',
  'failed': 'Failed'
};

const getStatusMessage = (status) => statuses[status] || status;
```

**Provide clear error messages**:
```javascript
const getErrorMessage = (error) => {
  const messages = {
    401: 'Your session expired. Please log in again.',
    403: "You don't have permission to access this.",
    404: 'This item was not found.',
    409: 'This already exists.',
    500: 'Server error. Please try again later.'
  };

  return messages[error.statusCode] || error.message;
};
```

---

## Framework-Specific Examples

### React Implementation

```javascript
// useAudioBookAPI.ts - Custom Hook
import { useState, useCallback, useEffect } from 'react';

export function useAudioBookAPI() {
  const [books, setBooks] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [syncStatus, setSyncStatus] = useState(null);

  const apiClient = useAPIClient();

  const fetchLibrary = useCallback(async (page = 1) => {
    setLoading(true);
    setError(null);

    try {
      const response = await apiClient.getLibrary(page, 50);
      setBooks(response.items);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [apiClient]);

  const startSync = useCallback(async (syncType = 'full') => {
    try {
      const response = await apiClient.startSync(syncType);
      setSyncStatus({
        id: response.sync_id,
        type: 'in_progress'
      });
      return response;
    } catch (err) {
      setError(err.message);
      throw err;
    }
  }, [apiClient]);

  return {
    books,
    loading,
    error,
    fetchLibrary,
    startSync,
    syncStatus
  };
}

// Component Usage
function LibraryView() {
  const { books, loading, error, fetchLibrary } = useAudioBookAPI();

  useEffect(() => {
    fetchLibrary();
  }, [fetchLibrary]);

  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error}</div>;

  return (
    <div className="library">
      {books.map(book => (
        <BookCard key={book.asin} book={book} />
      ))}
    </div>
  );
}
```

### Vue.js Implementation

```javascript
// composables/useAudioBookAPI.ts
import { ref, computed } from 'vue';

export function useAudioBookAPI() {
  const books = ref([]);
  const loading = ref(false);
  const error = ref(null);

  const apiClient = useAPIClient();

  const fetchLibrary = async (page = 1) => {
    loading.value = true;
    error.value = null;

    try {
      const response = await apiClient.getLibrary(page, 50);
      books.value = response.items;
    } catch (err) {
      error.value = err.message;
    } finally {
      loading.value = false;
    }
  };

  return {
    books: computed(() => books.value),
    loading: computed(() => loading.value),
    error: computed(() => error.value),
    fetchLibrary
  };
}

// Component Usage
<template>
  <div class="library">
    <div v-if="loading">Loading...</div>
    <div v-if="error" class="error">{{ error }}</div>
    <div v-for="book in books" :key="book.asin">
      <BookCard :book="book" />
    </div>
  </div>
</template>

<script setup>
import { onMounted } from 'vue';
import { useAudioBookAPI } from '@/composables/useAudioBookAPI';

const { books, loading, error, fetchLibrary } = useAudioBookAPI();

onMounted(() => fetchLibrary());
</script>
```

### Angular Implementation

```typescript
// services/audiobook-api.service.ts
import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class AudiobookAPIService {
  private books$ = new BehaviorSubject([]);
  private loading$ = new BehaviorSubject(false);
  private error$ = new BehaviorSubject<string | null>(null);

  books = this.books$.asObservable();
  loading = this.loading$.asObservable();
  error = this.error$.asObservable();

  constructor(private apiClient: APIClient) {}

  fetchLibrary(page: number = 1): void {
    this.loading$.next(true);
    this.error$.next(null);

    this.apiClient.getLibrary(page, 50).subscribe({
      next: (response) => {
        this.books$.next(response.items);
        this.loading$.next(false);
      },
      error: (err) => {
        this.error$.next(err.message);
        this.loading$.next(false);
      }
    });
  }
}

// Component Usage
@Component({
  selector: 'app-library',
  templateUrl: './library.component.html'
})
export class LibraryComponent {
  books$ = this.audioBookAPI.books;
  loading$ = this.audioBookAPI.loading;
  error$ = this.audioBookAPI.error;

  constructor(private audioBookAPI: AudiobookAPIService) {
    this.audioBookAPI.fetchLibrary();
  }
}
```

---

## Summary

This guide provides everything needed to implement AudioBookSync API endpoints into a frontend:

1. **Authentication**: JWT-based with token refresh
2. **Library Management**: CRUD operations for audiobook libraries
3. **Background Operations**: Sync, download, and decrypt with progress tracking
4. **Real-Time Updates**: WebSocket integration for live status
5. **File Streaming**: Range request support for audio playback
6. **Error Handling**: Standardized error responses
7. **Best Practices**: Token management, caching, optimization
8. **Framework Examples**: React, Vue, Angular implementations

Use the API client interface as a template to implement API communication in your frontend, and refer to the endpoint reference for detailed parameter and response documentation.
