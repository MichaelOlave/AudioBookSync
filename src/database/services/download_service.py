"""Download status database service layer using SQLAlchemy ORM."""

from src.database.models.download import DownloadStatus
from src.database.services.status_service_factory import StatusServiceConfig, StatusServiceFactory

# Configure download status service
_config = StatusServiceConfig(
    model_class=DownloadStatus,
    model_name="download",
    id_column="download_id",
    started_at_column="download_started_at",
    completed_at_column="download_completed_at",
    active_status="downloading",
)

# Generate service functions
_factory = StatusServiceFactory(_config)
_functions = _factory.generate_service_functions()

# Export as module-level functions for backward compatibility
create_download_status = _functions["create_download_status"]
get_download_by_id = _functions["get_download_by_id"]
get_downloads_by_asin = _functions["get_downloads_by_asin"]
get_latest_download = _functions["get_latest_download"]
update_download_status = _functions["update_download_status"]
start_download = _functions["start_download"]
complete_download = _functions["complete_download"]
fail_download = _functions["fail_download"]
get_pending_downloads = _functions["get_pending_downloads"]
get_failed_downloads = _functions["get_failed_downloads"]
delete_download = _functions["delete_download"]
get_downloads_by_user = _functions["get_downloads_by_user"]
count_downloads_by_user = _functions["count_downloads_by_user"]
get_download_by_id_for_user = _functions["get_download_by_id_for_user"]

__all__ = [
    "create_download_status",
    "get_download_by_id",
    "get_downloads_by_asin",
    "get_latest_download",
    "update_download_status",
    "start_download",
    "complete_download",
    "fail_download",
    "get_pending_downloads",
    "get_failed_downloads",
    "delete_download",
    "get_downloads_by_user",
    "count_downloads_by_user",
    "get_download_by_id_for_user",
]
