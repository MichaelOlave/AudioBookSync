"""Decryption management endpoints."""

from contextvars import ContextVar

from fastapi import APIRouter
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from ...database.models.user import User
from ...database.services import decryption_service, download_service
from ..middleware.error_handler import InternalServerError, ResourceNotFoundError
from ..schemas.decryption import (
    DecryptCreate,
    DecryptList,
    DecryptResponse,
)
from ..services.background_service import BackgroundTaskService
from .router_factory import RouterConfig, StatusRouterFactory

# Context variable for storing validation data
_validation_context: ContextVar[dict] = ContextVar("validation_context", default={})


async def validate_download_exists(
    create_data: DecryptCreate, db: AsyncSession, current_user: User
) -> None:
    """Validate that download exists and is completed before decryption.

    Args:
        create_data: Decryption creation data
        db: Database session
        current_user: Current user

    Raises:
        ResourceNotFoundError: If download not found
        InternalServerError: If download not completed
    """
    logger.info(f"Validating download exists for {create_data.asin}")

    # Verify download exists and is completed
    download = await download_service.get_latest_download(db, create_data.asin)
    if not download:
        logger.warning(f"Download not found for {create_data.asin}")
        raise ResourceNotFoundError("Book must be downloaded before decryption")

    if download.status != "completed":
        logger.warning(f"Download not completed for {create_data.asin}: {download.status}")
        raise InternalServerError(
            f"Download must be completed before decryption (current status: {download.status})"
        )

    # Store download in context for param builder
    _validation_context.set({"download": download})


def build_decryption_params(create_data: DecryptCreate) -> dict:
    """Build extra parameters for decryption creation from validation context.

    Args:
        create_data: Decryption creation data

    Returns:
        Dict with download_id parameter
    """
    context = _validation_context.get()
    return {"download_id": context["download"].download_id}


# Configure router for decryption operations
config = RouterConfig(
    operation_name="decryption",
    operation_name_plural="decryptions",
    service_module=decryption_service,
    create_schema=DecryptCreate,
    response_schema=DecryptResponse,
    list_schema=DecryptList,
    id_field="decryption_id",
    status_values="pending, decrypting, completed, failed, cancelled",
    background_task_func=BackgroundTaskService.execute_decrypt_operation,
    creation_failure_error=InternalServerError,
    operation_verb="decrypt",
    trigger_summary="Trigger book decryption",
    list_summary="List user's decryptions",
    get_status_summary="Get decryption status",
    # Add validators
    pre_create_validator=validate_download_exists,
    create_status_params_builder=build_decryption_params,
)

# Create router using factory
factory = StatusRouterFactory(config)
router: APIRouter = factory.create_router()
