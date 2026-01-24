"""Request/response logging middleware for FastAPI."""

import time
from typing import Awaitable, Callable

from fastapi import Request
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that logs HTTP requests and responses.

    Logs include:
    - Request method and path
    - Response status code
    - Processing duration
    - Request size
    - Response size
    - Client IP address
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Process request and log details."""

        # Skip logging for health checks to reduce log noise
        if request.url.path == "/api/v1/health":
            response = await call_next(request)
            return response

        # Record start time
        start_time = time.time()

        # Get client IP
        client_host = request.client.host if request.client else "unknown"

        # Get request size (approximate)
        request_size = (
            len(await request.body()) if request.method in ["POST", "PUT", "PATCH"] else 0
        )

        # Log reques
        logger.info(
            f"→ {request.method} {request.url.path}",
            extra={
                "method": request.method,
                "path": request.url.path,
                "query": dict(request.query_params),
                "client_ip": client_host,
                "request_size": request_size,
            },
        )

        # Process reques
        try:
            response = await call_next(request)
        except Exception as e:
            logger.error(
                f"✗ {request.method} {request.url.path} - Exception",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "client_ip": client_host,
                    "error": str(e),
                },
            )
            raise

        # Calculate duration
        duration = time.time() - start_time

        # Log response
        status_emoji = (
            "✓"
            if 200 <= response.status_code < 300
            else "⚠" if 300 <= response.status_code < 400 else "✗"
        )

        logger.info(
            (
                f"{status_emoji} {request.method} {request.url.path} "
                f"[{response.status_code}] {duration:.3f}s"
            ),
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_seconds": duration,
                "client_ip": client_host,
                "response_size": response.headers.get("content-length", "unknown"),
            },
        )

        return response
