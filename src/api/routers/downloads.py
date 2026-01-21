"""Download management endpoints."""

from fastapi import APIRouter

from ...database.services import download_service
from ..schemas.download import (
    DownloadCreate,
    DownloadResponse,
    DownloadList,
)
from ..services.background_service import BackgroundTaskService
from ..middleware.error_handler import ResourceNotFoundError
from .router_factory import StatusRouterFactory, RouterConfig

# Configure router for download operations
config = RouterConfig(
    operation_name="download",
    operation_name_plural="downloads",
    service_module=download_service,
    create_schema=DownloadCreate,
    response_schema=DownloadResponse,
    list_schema=DownloadList,
    id_field="download_id",
    status_values="pending, downloading, completed, failed, cancelled",
    background_task_func=BackgroundTaskService.execute_download_operation,
    creation_failure_error=ResourceNotFoundError,
    operation_verb="download",
    trigger_summary="Trigger book download",
    list_summary="List user's downloads",
    get_status_summary="Get download status",
)

# Create router using factory
factory = StatusRouterFactory(config)
router: APIRouter = factory.create_router()
