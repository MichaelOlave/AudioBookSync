"""Unit tests for SQLAlchemy setup and models.

These tests verify that all models, services, and infrastructure are properly set up.
No database required.

Run with:
    pytest tests/test_sqlalchemy_setup.py -v
"""

from src.database.engine import engine, get_db_session
from src.database.models import (
    Base,
    Book,
    BookAvailability,
    BookContributor,
    BookGenre,
    BookMetadataJson,
    CompanionMaterial,
    Contributor,
    DecryptionStatus,
    DownloadStatus,
    ErrorLog,
    Genre,
    MediaInfo,
    ReadingProgress,
    SyncHistory,
    User,
)
from src.database.services import (
    book_service,
    decryption_service,
    download_service,
    error_service,
    metadata_service,
    sync_service,
    user_service,
)

# ============================================================================
# MODEL TESTS
# ============================================================================


class TestModels:
    """Test SQLAlchemy model definitions."""

    def test_user_model_exists(self):
        """Test User model is defined."""
        assert User is not None
        assert User.__tablename__ == "users"

    def test_book_model_exists(self):
        """Test Book model is defined."""
        assert Book is not None
        assert Book.__tablename__ == "books"

    def test_download_status_model_exists(self):
        """Test DownloadStatus model is defined."""
        assert DownloadStatus is not None
        assert DownloadStatus.__tablename__ == "download_status"

    def test_decryption_status_model_exists(self):
        """Test DecryptionStatus model is defined."""
        assert DecryptionStatus is not None
        assert DecryptionStatus.__tablename__ == "decryption_status"

    def test_sync_history_model_exists(self):
        """Test SyncHistory model is defined."""
        assert SyncHistory is not None
        assert SyncHistory.__tablename__ == "sync_history"

    def test_error_log_model_exists(self):
        """Test ErrorLog model is defined."""
        assert ErrorLog is not None
        assert ErrorLog.__tablename__ == "error_log"

    def test_genre_model_exists(self):
        """Test Genre model is defined."""
        assert Genre is not None
        assert Genre.__tablename__ == "genres"

    def test_book_genre_model_exists(self):
        """Test BookGenre model is defined."""
        assert BookGenre is not None
        assert BookGenre.__tablename__ == "book_genres"

    def test_contributor_model_exists(self):
        """Test Contributor model is defined."""
        assert Contributor is not None
        assert Contributor.__tablename__ == "contributors"

    def test_book_contributor_model_exists(self):
        """Test BookContributor model is defined."""
        assert BookContributor is not None
        assert BookContributor.__tablename__ == "book_contributors"

    def test_media_info_model_exists(self):
        """Test MediaInfo model is defined."""
        assert MediaInfo is not None
        assert MediaInfo.__tablename__ == "media_info"

    def test_reading_progress_model_exists(self):
        """Test ReadingProgress model is defined."""
        assert ReadingProgress is not None
        assert ReadingProgress.__tablename__ == "reading_progress"

    def test_book_availability_model_exists(self):
        """Test BookAvailability model is defined."""
        assert BookAvailability is not None
        assert BookAvailability.__tablename__ == "book_availability"

    def test_companion_material_model_exists(self):
        """Test CompanionMaterial model is defined."""
        assert CompanionMaterial is not None
        assert CompanionMaterial.__tablename__ == "companion_materials"

    def test_book_metadata_json_model_exists(self):
        """Test BookMetadataJson model is defined."""
        assert BookMetadataJson is not None
        assert BookMetadataJson.__tablename__ == "book_metadata_json"

    def test_all_models_have_tablename(self):
        """Test all models have __tablename__ defined."""
        models = [
            User,
            Book,
            DownloadStatus,
            DecryptionStatus,
            SyncHistory,
            ErrorLog,
            Genre,
            BookGenre,
            Contributor,
            BookContributor,
            MediaInfo,
            ReadingProgress,
            BookAvailability,
            CompanionMaterial,
            BookMetadataJson,
        ]
        for model in models:
            # Check model has tablename
            assert hasattr(model, "__tablename__")
            assert isinstance(model.__tablename__, str)


# ============================================================================
# SERVICE TESTS
# ============================================================================


class TestServices:
    """Test service modules are properly defined."""

    def test_user_service_module_exists(self):
        """Test user_service module exists."""
        assert user_service is not None

    def test_user_service_functions(self):
        """Test user_service has required functions."""
        required_functions = [
            "create_user",
            "get_user_by_id",
            "get_user_by_username",
            "get_user_by_email",
            "update_user_password",
            "update_user_last_sync",
            "update_user_audible_auth",
            "update_user_activation_bytes",
            "get_active_users",
            "deactivate_user",
            "delete_user",
        ]
        for func_name in required_functions:
            assert hasattr(user_service, func_name), f"Missing function: {func_name}"
            assert callable(getattr(user_service, func_name))

    def test_book_service_functions(self):
        """Test book_service has required functions."""
        required_functions = [
            "add_book",
            "get_book_by_asin",
            "get_books_by_user",
            "get_downloaded_books",
            "get_decrypted_books",
            "update_book_download_status",
            "update_book_decryption_status",
            "delete_book",
            "search_books",
            "get_books_by_series",
        ]
        for func_name in required_functions:
            assert hasattr(book_service, func_name), f"Missing function: {func_name}"
            assert callable(getattr(book_service, func_name))

    def test_download_service_functions(self):
        """Test download_service has required functions."""
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
        ]
        for func_name in required_functions:
            assert hasattr(download_service, func_name), f"Missing function: {func_name}"
            assert callable(getattr(download_service, func_name))

    def test_decryption_service_functions(self):
        """Test decryption_service has required functions."""
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
        ]
        for func_name in required_functions:
            assert hasattr(decryption_service, func_name), f"Missing function: {func_name}"
            assert callable(getattr(decryption_service, func_name))

    def test_sync_service_functions(self):
        """Test sync_service has required functions."""
        required_functions = [
            "create_sync_history",
            "get_sync_by_id",
            "get_syncs_by_user",
            "get_latest_sync",
            "update_sync_status",
            "complete_sync",
            "fail_sync",
            "get_incomplete_syncs",
            "get_failed_syncs",
            "get_sync_statistics",
            "delete_sync",
        ]
        for func_name in required_functions:
            assert hasattr(sync_service, func_name), f"Missing function: {func_name}"
            assert callable(getattr(sync_service, func_name))

    def test_error_service_functions(self):
        """Test error_service has required functions."""
        required_functions = [
            "log_error",
            "get_error_by_id",
            "get_errors_by_user",
            "get_errors_by_asin",
            "get_errors_by_type",
            "get_errors_by_severity",
            "get_unresolved_errors",
            "resolve_error",
            "get_critical_errors",
            "get_recent_errors",
            "get_error_summary",
            "delete_error",
            "clean_old_resolved_errors",
        ]
        for func_name in required_functions:
            assert hasattr(error_service, func_name), f"Missing function: {func_name}"
            assert callable(getattr(error_service, func_name))

    def test_metadata_service_functions(self):
        """Test metadata_service has required functions."""
        required_functions = [
            "create_contributor",
            "get_contributor_by_id",
            "get_contributor_by_name",
            "add_book_contributor",
            "create_media_info",
            "get_media_info",
            "create_reading_progress",
            "get_reading_progress",
            "update_reading_progress",
            "create_book_availability",
            "get_book_availability",
            "create_companion_material",
            "get_companion_materials",
            "get_chapters_by_asin",
            "replace_chapters",
            "create_book_metadata",
            "get_book_metadata",
            "update_book_metadata",
        ]
        for func_name in required_functions:
            assert hasattr(metadata_service, func_name), f"Missing function: {func_name}"
            assert callable(getattr(metadata_service, func_name))


# ============================================================================
# INFRASTRUCTURE TESTS
# ============================================================================


class TestInfrastructure:
    """Test database infrastructure."""

    def test_engine_exists(self):
        """Test async engine is created."""
        assert engine is not None

    def test_get_db_session_is_callable(self):
        """Test get_db_session is a callable dependency."""
        assert callable(get_db_session)

    def test_base_metadata_exists(self):
        """Test Base has metadata."""
        assert Base is not None
        assert hasattr(Base, "metadata")


# ============================================================================
# INTEGRATION TESTS (no DB required)
# ============================================================================


class TestServiceIntegration:
    """Test that services work together."""

    def test_all_services_importable(self):
        """Test all services can be imported."""
        services = [
            user_service,
            book_service,
            download_service,
            decryption_service,
            sync_service,
            error_service,
            metadata_service,
        ]

        for service in services:
            assert service is not None

    def test_user_service_functions_are_async(self):
        """Test user_service functions are async."""
        import inspect

        functions = [
            "create_user",
            "get_user_by_id",
            "get_user_by_username",
        ]

        for func_name in functions:
            func = getattr(user_service, func_name)
            assert inspect.iscoroutinefunction(func), f"{func_name} is not async"

    def test_book_service_functions_are_async(self):
        """Test book_service functions are async."""
        import inspect

        functions = [
            "add_book",
            "get_book_by_asin",
            "get_books_by_user",
        ]

        for func_name in functions:
            func = getattr(book_service, func_name)
            assert inspect.iscoroutinefunction(func), f"{func_name} is not async"


# Run tests with: pytest tests/test_sqlalchemy_setup.py -v
