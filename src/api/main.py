"""FastAPI application for AudioBookSync.

This module initializes the FastAPI application with middleware,
exception handlers, routers, and lifespan management.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from ..core.config import Config
from ..core.logging_config import configure_logging, shutdown_logging
from ..database.engine import engine as db_engine
from .middleware.error_handler import add_exception_handlers
from .middleware.logging import LoggingMiddleware
from .routers import (
    audible_auth,
    auth,
    books,
    decryptions,
    downloads,
    errors,
    files,
    library,
    settings,
    sync,
    tasks,
    users,
    websocket,
)
from .schemas.common import HealthResponse

# ============================================================================
# LIFESPAN MANAGEMENT
# ============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifecycle (startup and shutdown).

    This context manager handles:
    - Startup: Configure logging, ensure directories exist
    - Shutdown: Close database connections
    """
    # ========== STARTUP ==========
    try:
        # Configure logging with loguru
        configure_logging(log_level=Config.LOG_LEVEL)
        logger.info("Logging configured successfully")

        logger.info("=" * 80)
        logger.info("AudioBookSync API Starting Up")
        logger.info("=" * 80)
        logger.info(f"Environment: {Config.LOG_LEVEL}")
        logger.info(
            "Database: "
            f"{Config.DATABASE_URL.split('@')[1] if '@' in Config.DATABASE_URL else 'configured'}"
        )
        logger.info(f"CORS Origins: {Config.CORS_ORIGINS}")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"Startup failed: {e}", exc_info=True)
        raise

    yield  # Application runs here

    # ========== SHUTDOWN ==========
    try:
        logger.info("AudioBookSync API Shutting Down")
        shutdown_logging()
        await db_engine.dispose()
        logger.info("Database connections closed")
    except Exception as e:
        logger.error(f"Shutdown error: {e}", exc_info=True)


# ============================================================================
# APPLICATION FACTORY
# ============================================================================


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Returns:
        FastAPI: Configured FastAPI instance

    Features:
        - Full async/await support
        - JWT authentication ready
        - Comprehensive error handling
        - Request/response logging
        - CORS configuration
        - WebSocket support
        - OpenAPI documentation
    """

    # Create FastAPI instance with metadata
    app = FastAPI(
        title="AudioBookSync API",
        description=(
            "Multi-user audiobook library management system with Audible sync, "
            "downloads, and decryption"
        ),
        version="1.0.0",
        docs_url="/docs",  # Swagger UI
        redoc_url="/redoc",  # ReDoc
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # ========== MIDDLEWARE ==========

    # CORS Middleware - Handle cross-origin requests
    app.add_middleware(
        CORSMiddleware,
        allow_origins=Config.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["Content-Range", "Content-Length"],
    )

    # Custom logging middleware - Log all requests and responses
    app.add_middleware(LoggingMiddleware)

    # ========== EXCEPTION HANDLERS ==========
    # Register all custom exception handlers
    add_exception_handlers(app)

    # ========== ROUTERS ==========
    # Register all API routers with version prefix

    app.include_router(
        auth.router,
        prefix="/api/v1/auth",
        tags=["Authentication"],
    )

    app.include_router(
        audible_auth.router,
        prefix="/api/v1",
        tags=["Authentication"],
    )

    app.include_router(
        users.router,
        prefix="/api/v1/users",
        tags=["Users"],
    )

    app.include_router(
        library.router,
        prefix="/api/v1/library",
        tags=["Library"],
    )

    app.include_router(
        books.router,
        prefix="/api/v1/books",
        tags=["Books"],
    )

    app.include_router(
        sync.router,
        prefix="/api/v1/sync",
        tags=["Sync"],
    )

    app.include_router(
        downloads.router,
        prefix="/api/v1/downloads",
        tags=["Downloads"],
    )

    app.include_router(
        decryptions.router,
        prefix="/api/v1/decryptions",
        tags=["Decryptions"],
    )

    app.include_router(
        errors.router,
        prefix="/api/v1/errors",
        tags=["Errors"],
    )

    app.include_router(
        files.router,
        prefix="/api/v1/files",
        tags=["Files"],
    )

    app.include_router(
        websocket.router,
        prefix="/api/v1/ws",
        tags=["WebSocket"],
    )

    app.include_router(
        tasks.router,
        prefix="/api/v1/tasks",
        tags=["Tasks"],
    )

    app.include_router(
        settings.router,
        prefix="/api/v1/settings",
        tags=["Settings"],
    )

    # ========== HEALTH CHECK ENDPOINT ==========

    @app.get(
        "/api/v1/health",
        response_model=HealthResponse,
        tags=["Health"],
        summary="Health Check",
        description="Check if the API and MinIO storage are running and healthy",
    )
    async def health_check() -> HealthResponse:
        """
        Health check endpoint with MinIO connectivity status.

        MinIO is required for all operations in native mode, so connectivity
        is mandatory for the service to be considered healthy.

        Returns:
            HealthResponse: Service health status with MinIO connectivity

        Example:
            GET /api/v1/health
            Response: {
                "status": "healthy",
                "service": "AudioBookSync",
                "version": "1.0.0",
                "minio": "connected"
            }

        MinIO Status:
            - "connected": MinIO service is accessible and responding
            - "disconnected: <error>": MinIO service is not accessible
        """
        # Check MinIO connectivity (required for native MinIO mode)
        overall_status = "healthy"
        minio_status = "connected"

        try:
            # Import MinIOClient here to avoid circular imports
            from ..infrastructure.minio_client import MinIOClient

            minio_client = MinIOClient()
            # Try to check bucket existence as a connectivity test
            # This is a lightweight operation that verifies MinIO is accessible
            minio_client.bucket_exists("test-health-check")
            logger.debug("MinIO health check: connected")
        except Exception as e:
            minio_status = f"disconnected: {str(e)}"
            overall_status = "unhealthy"  # MinIO is critical infrastructure
            logger.error(f"MinIO health check failed: {e}")

        return HealthResponse(
            status=overall_status,
            service="AudioBookSync",
            version="1.0.0",
            minio=minio_status,
        )

    # ========== DOCUMENTATION ==========

    logger.info("FastAPI application created successfully")
    logger.info("Documentation available at:")
    logger.info(f"  - Swagger UI: http://localhost:{Config.API_PORT}/docs")
    logger.info(f"  - ReDoc: http://localhost:{Config.API_PORT}/redoc")
    logger.info(f"  - OpenAPI JSON: http://localhost:{Config.API_PORT}/openapi.json")

    return app


# ============================================================================
# APPLICATION INSTANCE
# ============================================================================

app = create_app()


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    logger.info(f"Starting AudioBookSync API on {Config.API_HOST}:{Config.API_PORT}")

    uvicorn.run(
        "src.api.main:app",
        host=Config.API_HOST,
        port=Config.API_PORT,
        reload=True,  # Auto-reload on code changes (development)
        log_level=Config.LOG_LEVEL.lower(),
    )
