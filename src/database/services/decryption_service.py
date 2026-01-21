"""Decryption status database service layer using SQLAlchemy ORM."""

from src.database.models.decryption import DecryptionStatus
from src.database.services.status_service_factory import (
    StatusServiceConfig,
    StatusServiceFactory,
)

# Configure decryption status service
_config = StatusServiceConfig(
    model_class=DecryptionStatus,
    model_name="decryption",
    id_column="decryption_id",
    started_at_column="decryption_started_at",
    completed_at_column="decryption_completed_at",
    active_status="decrypting",
)

# Generate service functions
_factory = StatusServiceFactory(_config)
_functions = _factory.generate_service_functions()

# Export as module-level functions for backward compatibility
create_decryption_status = _functions["create_decryption_status"]
get_decryption_by_id = _functions["get_decryption_by_id"]
get_decryptions_by_asin = _functions["get_decryptions_by_asin"]
get_latest_decryption = _functions["get_latest_decryption"]
update_decryption_status = _functions["update_decryption_status"]
start_decryption = _functions["start_decryption"]
complete_decryption = _functions["complete_decryption"]
fail_decryption = _functions["fail_decryption"]
get_pending_decryptions = _functions["get_pending_decryptions"]
get_failed_decryptions = _functions["get_failed_decryptions"]
delete_decryption = _functions["delete_decryption"]
get_decryptions_by_user = _functions["get_decryptions_by_user"]
count_decryptions_by_user = _functions["count_decryptions_by_user"]
get_decryption_by_id_for_user = _functions["get_decryption_by_id_for_user"]

__all__ = [
    "create_decryption_status",
    "get_decryption_by_id",
    "get_decryptions_by_asin",
    "get_latest_decryption",
    "update_decryption_status",
    "start_decryption",
    "complete_decryption",
    "fail_decryption",
    "get_pending_decryptions",
    "get_failed_decryptions",
    "delete_decryption",
    "get_decryptions_by_user",
    "count_decryptions_by_user",
    "get_decryption_by_id_for_user",
]
