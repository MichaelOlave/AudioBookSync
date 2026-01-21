"""Unit tests for status_service_factory.

Tests verify that the factory correctly generates service functions with proper
signatures and behavior patterns.
"""

import inspect


from src.database.models.decryption import DecryptionStatus
from src.database.models.download import DownloadStatus
from src.database.services.status_service_factory import (
    StatusServiceConfig,
    StatusServiceFactory,
)

# ============================================================================
# CONFIGURATION TESTS
# ============================================================================


def test_download_config_creation():
    """Test creating a DownloadStatus service config."""
    config = StatusServiceConfig(
        model_class=DownloadStatus,
        model_name="download",
        id_column="download_id",
        started_at_column="download_started_at",
        completed_at_column="download_completed_at",
        active_status="downloading",
    )

    assert config.model_class == DownloadStatus
    assert config.model_name == "download"
    assert config.id_column == "download_id"
    assert config.started_at_column == "download_started_at"
    assert config.completed_at_column == "download_completed_at"
    assert config.active_status == "downloading"
    assert config.pending_status == "pending"
    assert config.completed_status == "completed"
    assert config.failed_status == "failed"


def test_decryption_config_creation():
    """Test creating a DecryptionStatus service config."""
    config = StatusServiceConfig(
        model_class=DecryptionStatus,
        model_name="decryption",
        id_column="decryption_id",
        started_at_column="decryption_started_at",
        completed_at_column="decryption_completed_at",
        active_status="decrypting",
    )

    assert config.model_class == DecryptionStatus
    assert config.model_name == "decryption"
    assert config.active_status == "decrypting"


# ============================================================================
# FACTORY INITIALIZATION TESTS
# ============================================================================


def test_factory_initialization():
    """Test factory initializes correctly with config."""
    config = StatusServiceConfig(
        model_class=DownloadStatus,
        model_name="download",
        id_column="download_id",
        started_at_column="download_started_at",
        completed_at_column="download_completed_at",
        active_status="downloading",
    )

    factory = StatusServiceFactory(config)

    assert factory.config == config
    assert factory.model == DownloadStatus
    assert factory.model_name == "download"
    assert factory.id_column == "download_id"


# ============================================================================
# FUNCTION GENERATION TESTS
# ============================================================================


def test_factory_generates_all_functions():
    """Test that factory generates all 14 required functions."""
    config = StatusServiceConfig(
        model_class=DownloadStatus,
        model_name="download",
        id_column="download_id",
        started_at_column="download_started_at",
        completed_at_column="download_completed_at",
        active_status="downloading",
    )

    factory = StatusServiceFactory(config)
    functions = factory.generate_service_functions()

    expected_functions = {
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
    }

    assert set(functions.keys()) == expected_functions


def test_generated_functions_are_callable():
    """Test that all generated functions are callable."""
    config = StatusServiceConfig(
        model_class=DownloadStatus,
        model_name="download",
        id_column="download_id",
        started_at_column="download_started_at",
        completed_at_column="download_completed_at",
        active_status="downloading",
    )

    factory = StatusServiceFactory(config)
    functions = factory.generate_service_functions()

    for func_name, func in functions.items():
        assert callable(func), f"{func_name} is not callable"


def test_generated_functions_are_async():
    """Test that all generated functions are async."""
    config = StatusServiceConfig(
        model_class=DownloadStatus,
        model_name="download",
        id_column="download_id",
        started_at_column="download_started_at",
        completed_at_column="download_completed_at",
        active_status="downloading",
    )

    factory = StatusServiceFactory(config)
    functions = factory.generate_service_functions()

    for func_name, func in functions.items():
        assert inspect.iscoroutinefunction(func), f"{func_name} is not async"


# ============================================================================
# FUNCTION SIGNATURE TESTS
# ============================================================================


def test_create_function_signature():
    """Test that create function has expected signature."""
    config = StatusServiceConfig(
        model_class=DownloadStatus,
        model_name="download",
        id_column="download_id",
        started_at_column="download_started_at",
        completed_at_column="download_completed_at",
        active_status="downloading",
    )

    factory = StatusServiceFactory(config)
    functions = factory.generate_service_functions()
    create_func = functions["create_download_status"]

    sig = inspect.signature(create_func)
    params = list(sig.parameters.keys())

    # Should have at least: db, asin, status, and **kwargs
    assert "db" in params
    assert "asin" in params
    assert "status" in params


def test_get_by_id_function_signature():
    """Test that get_by_id function has expected signature."""
    config = StatusServiceConfig(
        model_class=DownloadStatus,
        model_name="download",
        id_column="download_id",
        started_at_column="download_started_at",
        completed_at_column="download_completed_at",
        active_status="downloading",
    )

    factory = StatusServiceFactory(config)
    functions = factory.generate_service_functions()
    get_func = functions["get_download_by_id"]

    sig = inspect.signature(get_func)
    params = list(sig.parameters.keys())

    assert "db" in params
    assert "entity_id" in params


def test_update_function_signature():
    """Test that update function has expected signature."""
    config = StatusServiceConfig(
        model_class=DownloadStatus,
        model_name="download",
        id_column="download_id",
        started_at_column="download_started_at",
        completed_at_column="download_completed_at",
        active_status="downloading",
    )

    factory = StatusServiceFactory(config)
    functions = factory.generate_service_functions()
    update_func = functions["update_download_status"]

    sig = inspect.signature(update_func)
    params = list(sig.parameters.keys())

    assert "db" in params
    assert "entity_id" in params
    assert "status" in params


def test_start_function_signature():
    """Test that start function has expected signature."""
    config = StatusServiceConfig(
        model_class=DownloadStatus,
        model_name="download",
        id_column="download_id",
        started_at_column="download_started_at",
        completed_at_column="download_completed_at",
        active_status="downloading",
    )

    factory = StatusServiceFactory(config)
    functions = factory.generate_service_functions()
    start_func = functions["start_download"]

    sig = inspect.signature(start_func)
    params = list(sig.parameters.keys())

    assert "db" in params
    assert "entity_id" in params


def test_complete_function_signature():
    """Test that complete function has expected signature."""
    config = StatusServiceConfig(
        model_class=DownloadStatus,
        model_name="download",
        id_column="download_id",
        started_at_column="download_started_at",
        completed_at_column="download_completed_at",
        active_status="downloading",
    )

    factory = StatusServiceFactory(config)
    functions = factory.generate_service_functions()
    complete_func = functions["complete_download"]

    sig = inspect.signature(complete_func)
    params = list(sig.parameters.keys())

    assert "db" in params
    assert "entity_id" in params


def test_fail_function_signature():
    """Test that fail function has expected signature."""
    config = StatusServiceConfig(
        model_class=DownloadStatus,
        model_name="download",
        id_column="download_id",
        started_at_column="download_started_at",
        completed_at_column="download_completed_at",
        active_status="downloading",
    )

    factory = StatusServiceFactory(config)
    functions = factory.generate_service_functions()
    fail_func = functions["fail_download"]

    sig = inspect.signature(fail_func)
    params = list(sig.parameters.keys())

    assert "db" in params
    assert "entity_id" in params
    assert "error_message" in params


def test_get_by_user_function_signature():
    """Test that get_by_user function has expected signature."""
    config = StatusServiceConfig(
        model_class=DownloadStatus,
        model_name="download",
        id_column="download_id",
        started_at_column="download_started_at",
        completed_at_column="download_completed_at",
        active_status="downloading",
    )

    factory = StatusServiceFactory(config)
    functions = factory.generate_service_functions()
    get_user_func = functions["get_downloads_by_user"]

    sig = inspect.signature(get_user_func)
    params = list(sig.parameters.keys())

    assert "db" in params
    assert "user_id" in params
    assert "status" in params
    assert "limit" in params
    assert "offset" in params


def test_count_by_user_function_signature():
    """Test that count_by_user function has expected signature."""
    config = StatusServiceConfig(
        model_class=DownloadStatus,
        model_name="download",
        id_column="download_id",
        started_at_column="download_started_at",
        completed_at_column="download_completed_at",
        active_status="downloading",
    )

    factory = StatusServiceFactory(config)
    functions = factory.generate_service_functions()
    count_func = functions["count_downloads_by_user"]

    sig = inspect.signature(count_func)
    params = list(sig.parameters.keys())

    assert "db" in params
    assert "user_id" in params
    assert "status" in params


def test_delete_function_signature():
    """Test that delete function has expected signature."""
    config = StatusServiceConfig(
        model_class=DownloadStatus,
        model_name="download",
        id_column="download_id",
        started_at_column="download_started_at",
        completed_at_column="download_completed_at",
        active_status="downloading",
    )

    factory = StatusServiceFactory(config)
    functions = factory.generate_service_functions()
    delete_func = functions["delete_download"]

    sig = inspect.signature(delete_func)
    params = list(sig.parameters.keys())

    assert "db" in params
    assert "entity_id" in params


# ============================================================================
# DECRYPTION SERVICE FACTORY TESTS
# ============================================================================


def test_decryption_factory_generates_all_functions():
    """Test that decryption factory generates all functions with correct names."""
    config = StatusServiceConfig(
        model_class=DecryptionStatus,
        model_name="decryption",
        id_column="decryption_id",
        started_at_column="decryption_started_at",
        completed_at_column="decryption_completed_at",
        active_status="decrypting",
    )

    factory = StatusServiceFactory(config)
    functions = factory.generate_service_functions()

    expected_functions = {
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
    }

    assert set(functions.keys()) == expected_functions


# ============================================================================
# BACKWARD COMPATIBILITY TESTS
# ============================================================================


def test_download_service_module_exports():
    """Test that download_service module exports all required functions."""
    from src.database.services import download_service

    required_functions = [
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

    for func_name in required_functions:
        assert hasattr(download_service, func_name), f"download_service missing {func_name}"
        func = getattr(download_service, func_name)
        assert callable(func), f"{func_name} is not callable"
        assert inspect.iscoroutinefunction(func), f"{func_name} is not async"


def test_decryption_service_module_exports():
    """Test that decryption_service module exports all required functions."""
    from src.database.services import decryption_service

    required_functions = [
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

    for func_name in required_functions:
        assert hasattr(decryption_service, func_name), f"decryption_service missing {func_name}"
        func = getattr(decryption_service, func_name)
        assert callable(func), f"{func_name} is not callable"
        assert inspect.iscoroutinefunction(func), f"{func_name} is not async"


def test_download_service_all_export():
    """Test that download_service has proper __all__ export."""
    from src.database.services import download_service

    assert hasattr(download_service, "__all__")
    assert len(download_service.__all__) == 14


def test_decryption_service_all_export():
    """Test that decryption_service has proper __all__ export."""
    from src.database.services import decryption_service

    assert hasattr(decryption_service, "__all__")
    assert len(decryption_service.__all__) == 14
