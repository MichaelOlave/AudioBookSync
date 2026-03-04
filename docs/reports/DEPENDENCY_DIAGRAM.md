# AudioBookSync - Complete Dependency Diagram

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         ENTRY POINT                             │
│                        main.py (ASGI)                           │
└──────────────────────────┬──────────────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
        ▼                  ▼                  ▼
   ┌─────────┐       ┌──────────┐      ┌──────────────┐
   │Middleware│      │  Routers │      │ WebSockets   │
   │           │      │           │      │              │
   │error_hdlr│      │ (11 total) │      │  manager.py  │
   │logging   │      │           │      │  events.py   │
   └─────────┘      └──────────┘      └──────────────┘
```

---

## Detailed Layer-by-Layer Diagram

```
╔════════════════════════════════════════════════════════════════════╗
║                    API ROUTERS LAYER                               ║
║                    (11 Endpoints)                                  ║
║                                                                    ║
║  auth.py ──┐                                                       ║
║            │                                                       ║
║  audible_auth.py ──┐                                               ║
║                    │                                               ║
║  books.py ─────┐   │                                               ║
║                │   │                                               ║
║  downloads.py ─┤   │                                               ║
║                │   │                                               ║
║  decryptions.py ┤  │                                               ║
║                │   │                                               ║
║  files.py ──┐  │   │                                               ║
║             │  │   │                                               ║
║  library.py ─┤  │   │                                               ║
║             │  │   │                                               ║
║  sync.py ────┤  │   │                                               ║
║             │  │   │                                               ║
║  settings.py ─┤  │   │                                               ║
║             │  │   │                                               ║
║  websocket.py  │  │   │                                               ║
║             │  │   │                                               ║
║  errors.py ─┴──┤   │                                               ║
║                │   │                                               ║
╚────────────────┼───┼──────────────────────────────────────────────╝
                 │   │
        ┌────────┘   │    All routers import from these layers:
        │            │
        ▼            ▼    • Security (auth dependencies)
    ┌─────────────────────┐ • Database (specific db_* modules)
    │  SECURITY LAYER     │ • Services (for async tasks)
    │                     │ • Middleware (error handling)
    │ auth.py         ◄───┼─────────────────────────────────────┐
    │   ├─ JWTs            │                                      │
    │   ├─ Tokens          │ ┌────────────────────────────────┐   │
    │   └─ Decode/Encode   │ │ SERVICES LAYER                │   │
    │                     │ │                                │   │
    │ password.py      ◄──┼─┤ background_service.py          │   │
    │   ├─ Hash            │ │  ├─ Download operations       │   │
    │   └─ Verify          │ │  ├─ Decrypt operations        │   │
    │                     │ │  ├─ Sync operations           │   │
    └─────────────────────┘ │  └─ Broadcasting via WebSocket │   │
                            │                                │   │
                            │ sync_service.py             ◄──┼───┼─┐
                            │  ├─ Sync orchestration        │   │ │
                            │  └─ WebSocket events          │   │ │
                            └────────────────────────────────┘   │ │
                                       ▲                         │ │
                                       │                         │ │
    ┌──────────────────────────────────┘                         │ │
    │                                                             │ │
    │  ┌───────────────────────────────────────────────────────┐ │ │
    │  │         OPERATIONS LAYER                              │ │ │
    │  │   (Business Logic & Workflows)                        │ │ │
    │  │                                                       │ │ │
    │  │ library_sync.py ◄──────────┐                          │ │ │
    │  │  ├─ Main sync orchestration  │                        │ │ │
    │  │  ├─ Book processing         │                        │ │ │
    │  │  └─ Metadata sync           │                        │ │ │
    │  │                              │                        │ │ │
    │  │ db_manager.py               │                        │ │ │
    │  │  ├─ Transaction management   │                        │ │ │
    │  │  └─ Database coordination    │                        │ │ │
    │  │                              │                        │ │ │
    │  │ downloader.py ◄──────────┐   │                        │ │ │
    │  │  ├─ Download operations      │                        │ │ │
    │  │  ├─ File management          │                        │ │ │
    │  │  └─ Chunk handling           │                        │ │ │
    │  │                              │                        │ │ │
    │  │ decryptor.py ◄──────────────┘                        │ │ │
    │  │  ├─ DRM decryption                                   │ │ │
    │  │  ├─ Audio processing                                 │ │ │
    │  │  └─ File conversion                                  │ │ │
    │  │                                                       │ │ │
    │  └───────────────────────────────────────────────────────┘ │ │
    │                         ▲                                   │ │
    │                         │                                   │ │
    │  ┌──────────────────────┼──────────────────────────────┐   │ │
    │  │                      │                              │   │ │
    │  │  DATABASE LAYER      │                              │   │ │
    │  │  (CRUD Operations)   │                              │   │ │
    │  │                      │                              │   │ │
    │  │  ┌─────────────────────────────────────────────┐   │   │ │
    │  │  │ Core Database Files                         │   │   │ │
    │  │  │                                             │   │   │ │
    │  │  │ db_users.py ◄──────────────────────────┐   │   │   │ │
    │  │  │  ├─ User CRUD                          │   │   │   │ │
    │  │  │  ├─ Auth credentials                   │   │   │   │ │
    │  │  │  └─ User settings                      │   │   │   │ │
    │  │  │                                        │   │   │   │ │
    │  │  │ db_books.py ◄──────────────────────┐   │   │   │   │ │
    │  │  │  ├─ Book metadata                    │   │   │   │   │ │
    │  │  │  ├─ Book details                     │   │   │   │   │ │
    │  │  │  └─ Book search/filter               │   │   │   │   │ │
    │  │  │                                      │   │   │   │   │ │
    │  │  │ db_downloads.py ◄───────────────┐   │   │   │   │   │ │
    │  │  │  ├─ Download tracking                │   │   │   │   │ │
    │  │  │  ├─ Download status                  │   │   │   │   │ │
    │  │  │  └─ Download history                 │   │   │   │   │ │
    │  │  │                                      │   │   │   │   │ │
    │  │  │ db_decryptions.py ◄──────────┐       │   │   │   │   │ │
    │  │  │  ├─ Decryption status              │   │   │   │   │ │
    │  │  │  ├─ Decryption tracking            │   │   │   │   │ │
    │  │  │  └─ Decryption history             │   │   │   │   │ │
    │  │  │                                    │   │   │   │   │ │
    │  │  │ db_sync.py ◄──────────────┐       │   │   │   │   │ │
    │  │  │  ├─ Sync history                   │   │   │   │   │ │
    │  │  │  ├─ Sync status                    │   │   │   │   │ │
    │  │  │  └─ Last sync tracking             │   │   │   │   │ │
    │  │  │                                    │   │   │   │   │ │
    │  │  │ db_errors.py                      │   │   │   │   │ │
    │  │  │  ├─ Error logging                  │   │   │   │   │ │
    │  │  │  ├─ Error tracking                 │   │   │   │   │ │
    │  │  │  └─ Error analytics                │   │   │   │   │ │
    │  │  └─────────────────────────────────────────────────────┘ │
    │  │                                        │   │   │   │   │ │
    │  │  ┌─────────────────────────────────────┼───┼───┼───┼───┘ │
    │  │  │ Metadata Database Files             │   │   │   │     │
    │  │  │ (Used by db_books)                  │   │   │   │     │
    │  │  │                                     │   │   │   │     │
    │  │  │ db_book_metadata.py (JSON storage)  │   │   │   │     │
    │  │  │ db_book_contributors.py             │   │   │   │     │
    │  │  │ db_media_info.py (audio details)    │   │   │   │     │
    │  │  │ db_reading_progress.py              │   │   │   │     │
    │  │  │ db_book_availability.py             │   │   │   │     │
    │  │  │ db_companion_materials.py           │   │   │   │     │
    │  │  │ db_contributors.py                  │   │   │   │     │
    │  │  └─────────────────────────────────────────────────────┘ │
    │  │                                                           │
    │  │  ┌───────────────────────────────────────────────────────┘
    │  │  │  database.py (aggregator)
    │  │  │  ├─ Exports all db_* operations as singletons
    │  │  │  └─ Provides single import point
    │  │  │
    │  │  db_pool.py (Connection Pooling)
    │  │  ├─ PostgreSQL connection management
    │  │  ├─ Connection pooling (10-20 connections)
    │  │  └─ Used by ALL db_* files
    │  │
    │  └──────────────────────────────────────────────────────────────┘
    │
    └─────────────────────────────────────────────────────────────────┐
                                                                      │
    ┌─────────────────────────────────────────────────────────────────┘
    │
    │  ┌──────────────────────────────────────────────────────────────┐
    │  │ INFRASTRUCTURE LAYER                                         │
    │  │ (Utilities & External Clients)                              │
    │  │                                                              │
    │  │ file_utils.py                                               │
    │  │  ├─ File operations (ensure_directory, normalize_filename) │
    │  │  ├─ File existence checks                                   │
    │  │  ├─ Directory traversal                                     │
    │  │  └─ Used by: downloader, decryptor                         │
    │  │                                                              │
    │  │ audible_client.py (Available but not currently used)        │
    │  │  ├─ Audible API wrapper                                     │
    │  │  ├─ Async login capabilities                                │
    │  │  └─ Can be integrated when needed                           │
    │  └──────────────────────────────────────────────────────────────┘
    │
    └──────┐
           │
    ┌──────▼──────────────────────────────────────────────────────────┐
    │ CORE LAYER (Configuration & Setup)                             │
    │                                                                  │
    │ config.py (CENTRAL CONFIGURATION)                              │
    │  ├─ Environment variables                                       │
    │  ├─ Database URL                                               │
    │  ├─ File paths                                                 │
    │  ├─ JWT secrets                                                │
    │  └─ Used by: ALL layers (db_pool, auth, operations, etc.)     │
    │                                                                  │
    │ logging_config.py                                              │
    │  ├─ Loguru configuration                                       │
    │  ├─ Log formatting & rotation                                  │
    │  └─ Used by: main.py                                           │
    └──────────────────────────────────────────────────────────────────┘
```

---

## Complete File Dependency Graph

```
┌─────────────────────────────────────────────────────────────────────┐
│ MAIN ENTRY POINT                                                    │
│ main.py                                                             │
└────────────┬────────────────────────────────────────────────────────┘
             │
        ┌────┼────────────────────┬─────────────┬─────────────┐
        │    │                    │             │             │
        ▼    ▼                    ▼             ▼             ▼
    ┌────────────┐    ┌──────────────────┐  ┌─────────┐  ┌─────────┐
    │ Middleware │    │   11 Routers     │  │Schemas  │  │Database │
    │            │    │                  │  │         │  │         │
    │error_hdlr  │    │ ┌──────────────┐ │  └─────────┘  └─────────┘
    │logging     │    │ │ auth.py      │ │
    └────────────┘    │ ├──────────────┤ │      ┌──────────────┐
                      │ │ audible_auth │ │      │ WebSockets   │
     ▲                │ ├──────────────┤ │      │              │
     │                │ │ books.py     │ │  ┌───┤ manager.py   │
     │                │ ├──────────────┤ │  │   │ events.py    │
     └────────────────┼─┤ downloads.py │ │──┘   └──────────────┘
                      │ ├──────────────┤ │
                      │ │ decryptions  │ │
                      │ ├──────────────┤ │
                      │ │ files.py     │ │
                      │ ├──────────────┤ │
                      │ │ library.py   │ │
                      │ ├──────────────┤ │
                      │ │ sync.py      │ │
                      │ ├──────────────┤ │
                      │ │ settings.py  │ │
                      │ ├──────────────┤ │
                      │ │ websocket.py │ │
                      │ ├──────────────┤ │
                      │ │ errors.py    │ │
                      │ └──────────────┘ │
                      └──────────────────┘
                             │
        ┌────────────────────┼────────────────────┬─────────────┐
        │                    │                    │             │
        ▼                    ▼                    ▼             ▼
    ┌─────────────┐   ┌───────────────┐  ┌──────────────┐  ┌──────┐
    │  SECURITY   │   │   SERVICES    │  │  OPERATIONS  │  │ CORE │
    │             │   │               │  │              │  │      │
    │auth.py ◄────┼───┼─┐             │  │┌────────────┐│  │Config│
    │password.py  │   │ │             │  ││lib_sync.py││  │      │
    └─────────────┘   │ │background ◄─┼──┤│ • Sync    ││  └──┬───┘
                      │ │service.py   │  ││ • Books   ││     │
         ▲            │ │             │  ││ • Metadata││     │
         │            │ │• Downloads  │  │└────────────┘│     │
         │            │ │• Decrypts   │  │             │     │
         │            │ │• Broadcasts │  │┌────────────┐│     │
         │            │ │• Error log  │  ││downloader ││     │
         │            │ │             │  ││ • DL ops   ││     │
         │            │ │sync_service │  ││ • Chunks   ││     │
         │            │ │             │  │└────────────┘│     │
         │            │ │• Sync orch  │  │             │     │
         │            │ │• WebSocket  │  │┌────────────┐│     │
         │            │ │  events     │  ││decryptor   ││     │
         │            │ │             │  ││ • DRM      ││     │
         │            │ └─────────────┘  ││ • Convert  ││     │
         │            │                   │└────────────┘│     │
         └────────────┼───────────────────┼──────┬───────┘     │
                      │                   │      │             │
                      │      ┌────────────┘      │             │
                      │      │                   │             │
                      ▼      ▼                   ▼             ▼
                   ┌──────────────────────────────────────┬────────┐
                   │      DATABASE LAYER                  │        │
                   │                                      │        │
                   │ ┌─────────────────────────────────┐ │        │
                   │ │ CORE DB FILES                   │ │        │
                   │ │                                 │ │        │
                   │ │ db_pool.py (Connection Mgmt) ◄──┼─┤        │
                   │ │ • Pooling (10-20 connections) │ │ │        │
                   │ │ • PostgreSQL driver           │ │ │        │
                   │ │ • Used by ALL db_* files      │ │ │        │
                   │ │                                 │ │        │
                   │ │ db_users.py ◄──────────────────┼─┤        │
                   │ │ • User CRUD                    │ │        │
                   │ │ • Auth credentials             │ │        │
                   │ │ • User settings                │ │        │
                   │ │                                 │ │        │
                   │ │ db_books.py ◄────────────────────┼─┤        │
                   │ │ • Book metadata                │ │        │
                   │ │ • Book details                 │ │        │
                   │ │ • Book search/filter           │ │        │
                   │ │                                 │ │        │
                   │ │ db_downloads.py ◄──────────────┼─┤        │
                   │ │ • Download tracking            │ │        │
                   │ │ • Download status              │ │        │
                   │ │ • Download history             │ │        │
                   │ │                                 │ │        │
                   │ │ db_decryptions.py ◄────────────┼─┤        │
                   │ │ • Decryption status            │ │        │
                   │ │ • Decryption tracking          │ │        │
                   │ │                                 │ │        │
                   │ │ db_sync.py ◄────────────────────┼─┤        │
                   │ │ • Sync history                 │ │        │
                   │ │ • Sync status                  │ │        │
                   │ │                                 │ │        │
                   │ │ db_errors.py ◄──────────────────┼─┤        │
                   │ │ • Error logging                │ │        │
                   │ │ • Error tracking               │ │        │
                   │ └─────────────────────────────────┘ │        │
                   │                                      │        │
                   │ ┌─────────────────────────────────┐ │        │
                   │ │ METADATA DB FILES               │ │        │
                   │ │ (Used by db_books)              │ │        │
                   │ │                                 │ │        │
                   │ │ db_book_metadata.py             │ │        │
                   │ │ db_book_contributors.py         │ │        │
                   │ │ db_media_info.py                │ │        │
                   │ │ db_reading_progress.py          │ │        │
                   │ │ db_book_availability.py         │ │        │
                   │ │ db_companion_materials.py       │ │        │
                   │ │ db_contributors.py              │ │        │
                   │ │                                 │ │        │
                   │ │ database.py (Aggregator)        │ │        │
                   │ │ • Exports all singletons        │ │        │
                   │ │ • Single import point           │ │        │
                   │ └─────────────────────────────────┘ │        │
                   └──────────────────────────────────────┴────────┘
                                    ▲
                                    │
                      ┌─────────────┼─────────────┐
                      │             │             │
                      ▼             ▼             ▼
                   ┌─────────┐ ┌───────────┐ ┌──────────┐
                   │file_util│ │ audible   │ │ config   │
                   │         │ │ client.py │ │ (CENTRAL)│
                   └─────────┘ └───────────┘ └──────────┘
```

---

## Dependency Flow Summary

### **Tier 1: Entry Point**
- `main.py` - Starts the application

### **Tier 2: HTTP/WebSocket Handlers**
- 11 routers (auth, books, downloads, etc.)
- WebSocket manager
- All depend on Tier 3

### **Tier 3: Application Logic**
- Security layer (JWT, password hashing)
- Services (background tasks, sync orchestration)
- All depend on Tier 4

### **Tier 4: Business Operations**
- Library sync, downloader, decryptor
- Database manager
- All depend on Tier 5

### **Tier 5: Data Access**
- Database operations (CRUD on all entities)
- Connection pooling
- All depend on Tier 6

### **Tier 6: Configuration & Utilities**
- Core config (environment variables)
- File utilities
- Infrastructure (Audible client)
- Logging configuration

### **Key Architectural Properties**
✓ **No Circular Dependencies** - Clean unidirectional flow
✓ **Layered Architecture** - Clear separation of concerns
✓ **Single Responsibility** - Each module has one purpose
✓ **Testability** - Easy to mock dependencies
✓ **Scalability** - Can extend each layer independently
✓ **Maintainability** - Changes localized to one layer

---

## Critical Dependencies

### Files Used by Most Other Files
1. **config.py** - Used by ~12 files (core configuration)
2. **db_pool.py** - Used by all database files (connection management)
3. **auth.py** - Used by all routers (security/JWT)
4. **db_users.py** - Used by 6 files (user data)
5. **db_books.py** - Used by 4 files (book data)

### Most Connected Files
1. **background_service.py** - Imports from 6 different modules
2. **library_sync.py** - Imports from 5 different modules
3. **main.py** - Imports from 11 routers + middleware + config

### Safest Files to Modify (No dependents)
- Metadata db files (db_book_metadata, db_contributors, etc.)
- audible_client.py (not currently used)
- Individual helper utilities

