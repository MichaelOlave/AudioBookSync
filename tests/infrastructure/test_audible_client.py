"""Tests for src.infrastructure.audible_client module."""

import concurrent.futures
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.infrastructure.audible_client import AsyncAudibleClient, authenticate, sync_get_library


@pytest.mark.unit
class TestSyncGetLibrary:
    """Test synchronous library retrieval function."""

    def test_get_library_calls_client_method(self):
        """Test that sync_get_library calls client.get method."""
        mock_client = MagicMock()
        mock_client.get = MagicMock(return_value={"items": []})

        sync_get_library(
            mock_client,
            num_results=100,
            response_groups="product_desc",
            sort_by="-PurchaseDate",
        )

        mock_client.get.assert_called_once_with(
            "1.0/library",
            num_results=100,
            response_groups="product_desc",
            sort_by="-PurchaseDate",
        )

    def test_get_library_returns_result(self):
        """Test that sync_get_library returns library data."""
        expected_data = {"items": [{"asin": "B001ABC123"}]}
        mock_client = MagicMock()
        mock_client.get = MagicMock(return_value=expected_data)

        result = sync_get_library(
            mock_client,
            num_results=100,
            response_groups="product_desc",
            sort_by="-PurchaseDate",
        )

        assert result == expected_data

    def test_get_library_with_different_params(self):
        """Test sync_get_library with different parameters."""
        mock_client = MagicMock()
        mock_client.get = MagicMock(return_value={"items": []})

        sync_get_library(
            mock_client,
            num_results=50,
            response_groups="custom_groups",
            sort_by="-DateAdded",
        )

        mock_client.get.assert_called_once_with(
            "1.0/library",
            num_results=50,
            response_groups="custom_groups",
            sort_by="-DateAdded",
        )


@pytest.mark.asyncio
@pytest.mark.unit
class TestAsyncAudibleClient:
    """Test AsyncAudibleClient context manager."""

    async def test_init_creates_executor(self):
        """Test that __init__ creates a ThreadPoolExecutor."""
        auth = MagicMock()
        client = AsyncAudibleClient(auth)

        assert client.executor is not None
        assert isinstance(client.executor, concurrent.futures.ThreadPoolExecutor)
        client.executor.shutdown()

    async def test_init_stores_auth(self):
        """Test that __init__ stores authentication."""
        auth = MagicMock()
        client = AsyncAudibleClient(auth)

        assert client.auth is auth
        client.executor.shutdown()

    async def test_aenter_creates_client(self):
        """Test that __aenter__ creates Audible client."""
        auth = MagicMock()
        mock_audible_client = MagicMock()

        with patch("src.infrastructure.audible_client.audible.Client"):
            with patch("asyncio.get_event_loop") as mock_loop:
                mock_loop.return_value.run_in_executor = AsyncMock(return_value=mock_audible_client)

                client = AsyncAudibleClient(auth)
                result = await client.__aenter__()

                assert result is client
                mock_loop.return_value.run_in_executor.assert_called_once()
                client.executor.shutdown()

    async def test_aexit_shuts_down_executor(self):
        """Test that __aexit__ shuts down executor."""
        auth = MagicMock()
        client = AsyncAudibleClient(auth)
        client.client = MagicMock()

        await client.__aexit__(None, None, None)

        # Verify executor was shutdown (it's async, so we just verify the method was called)

    async def test_aexit_returns_false(self):
        """Test that __aexit__ returns False for exception propagation."""
        auth = MagicMock()
        client = AsyncAudibleClient(auth)
        client.client = MagicMock()

        result = await client.__aexit__(None, None, None)

        assert result is False

    async def test_context_manager_usage(self):
        """Test using AsyncAudibleClient as context manager."""
        auth = MagicMock()
        mock_audible_client = MagicMock()

        with patch("src.infrastructure.audible_client.audible.Client"):
            with patch("asyncio.get_event_loop") as mock_loop:
                mock_loop.return_value.run_in_executor = AsyncMock(return_value=mock_audible_client)

                async with AsyncAudibleClient(auth) as client:
                    assert client.client == mock_audible_client

    async def test_get_library_calls_executor(self):
        """Test that get_library uses executor."""
        auth = MagicMock()
        mock_audible_client = MagicMock()
        expected_library = {"items": []}

        with patch("src.infrastructure.audible_client.audible.Client"):
            with patch("asyncio.get_event_loop") as mock_loop:
                mock_loop.return_value.run_in_executor = AsyncMock(
                    side_effect=[mock_audible_client, expected_library]
                )

                client = AsyncAudibleClient(auth)
                await client.__aenter__()

                with patch("src.infrastructure.audible_client.sync_get_library") as mock_sync:
                    mock_sync.return_value = expected_library
                    result = await client.get_library()

                    # Verify run_in_executor was called for get_library
                    assert mock_loop.return_value.run_in_executor.call_count >= 2
                    assert result == expected_library
                    client.executor.shutdown()

    async def test_get_library_returns_library_data(self):
        """Test that get_library returns library data."""
        auth = MagicMock()
        expected_data = {"items": [{"asin": "B001ABC123"}]}

        with patch("src.infrastructure.audible_client.audible.Client"):
            with patch("asyncio.get_event_loop") as mock_loop:
                mock_loop.return_value.run_in_executor = AsyncMock(
                    side_effect=[MagicMock(), expected_data]
                )

                client = AsyncAudibleClient(auth)
                await client.__aenter__()

                with patch("src.infrastructure.audible_client.sync_get_library") as mock_sync:
                    mock_sync.return_value = expected_data
                    result = await client.get_library()

                    assert result == expected_data
                    client.executor.shutdown()


@pytest.mark.unit
class TestAuthenticate:
    """Test authentication function."""

    def test_authenticate_with_valid_auth_file(self):
        """Test authenticate with valid auth file."""
        mock_auth = MagicMock()

        with patch("src.infrastructure.audible_client.audible.Authenticator") as mock_auth_class:
            mock_auth_class.from_file = MagicMock(return_value=mock_auth)
            with patch(
                "src.infrastructure.audible_client.Config.AUTH_FILE",
                "/path/to/auth.json",
            ):
                client = authenticate()

                assert isinstance(client, AsyncAudibleClient)
                assert client.auth == mock_auth
                client.executor.shutdown()

    def test_authenticate_calls_from_file(self):
        """Test that authenticate calls Authenticator.from_file."""
        mock_auth = MagicMock()

        with patch("src.infrastructure.audible_client.audible.Authenticator") as mock_auth_class:
            mock_auth_class.from_file = MagicMock(return_value=mock_auth)
            with patch(
                "src.infrastructure.audible_client.Config.AUTH_FILE",
                "/path/to/auth.json",
            ):
                authenticate()

                mock_auth_class.from_file.assert_called_once_with("/path/to/auth.json")

    def test_authenticate_file_not_found(self):
        """Test authenticate when auth file not found."""
        with patch("src.infrastructure.audible_client.audible.Authenticator") as mock_auth_class:
            mock_auth_class.from_file = MagicMock(side_effect=FileNotFoundError("Not found"))
            with patch(
                "src.infrastructure.audible_client.Config.AUTH_FILE",
                "/missing/auth.json",
            ):
                with patch("src.infrastructure.audible_client.logger.error"):
                    with pytest.raises(FileNotFoundError):
                        authenticate()

    def test_authenticate_logs_file_not_found_error(self):
        """Test that authenticate logs FileNotFoundError."""
        with patch("src.infrastructure.audible_client.audible.Authenticator") as mock_auth_class:
            mock_auth_class.from_file = MagicMock(side_effect=FileNotFoundError("Not found"))
            with patch(
                "src.infrastructure.audible_client.Config.AUTH_FILE",
                "/missing/auth.json",
            ):
                with patch("src.infrastructure.audible_client.logger.error") as mock_logger:
                    with pytest.raises(FileNotFoundError):
                        authenticate()

                    mock_logger.assert_called()

    def test_authenticate_general_exception(self):
        """Test authenticate with general exception."""
        with patch("src.infrastructure.audible_client.audible.Authenticator") as mock_auth_class:
            mock_auth_class.from_file = MagicMock(side_effect=Exception("Auth failed"))
            with patch(
                "src.infrastructure.audible_client.Config.AUTH_FILE",
                "/path/to/auth.json",
            ):
                with patch("src.infrastructure.audible_client.logger.error"):
                    with pytest.raises(Exception):
                        authenticate()

    def test_authenticate_logs_general_error(self):
        """Test that authenticate logs general exceptions."""
        with patch("src.infrastructure.audible_client.audible.Authenticator") as mock_auth_class:
            mock_auth_class.from_file = MagicMock(side_effect=Exception("Auth failed"))
            with patch(
                "src.infrastructure.audible_client.Config.AUTH_FILE",
                "/path/to/auth.json",
            ):
                with patch("src.infrastructure.audible_client.logger.error") as mock_logger:
                    with pytest.raises(Exception):
                        authenticate()

                    mock_logger.assert_called()

    def test_authenticate_returns_async_client(self):
        """Test that authenticate returns AsyncAudibleClient instance."""
        mock_auth = MagicMock()

        with patch("src.infrastructure.audible_client.audible.Authenticator") as mock_auth_class:
            mock_auth_class.from_file = MagicMock(return_value=mock_auth)
            with patch(
                "src.infrastructure.audible_client.Config.AUTH_FILE",
                "/path/to/auth.json",
            ):
                result = authenticate()

                assert isinstance(result, AsyncAudibleClient)
                result.executor.shutdown()


@pytest.mark.asyncio
@pytest.mark.unit
class TestAsyncAudibleClientIntegration:
    """Integration tests for AsyncAudibleClient."""

    async def test_full_context_manager_lifecycle(self):
        """Test complete context manager lifecycle."""
        auth = MagicMock()
        mock_audible_client = MagicMock()
        library_data = {"items": [{"asin": "B001"}]}

        with patch("src.infrastructure.audible_client.audible.Client"):
            with patch("asyncio.get_event_loop") as mock_loop:
                mock_loop.return_value.run_in_executor = AsyncMock(
                    side_effect=[mock_audible_client, library_data]
                )

                async with AsyncAudibleClient(auth) as client:
                    with patch("src.infrastructure.audible_client.sync_get_library") as mock_sync:
                        mock_sync.return_value = library_data
                        library = await client.get_library()

                        assert library == library_data

    async def test_executor_cleanup_on_exception(self):
        """Test that executor is cleaned up even on exception."""
        auth = MagicMock()
        mock_audible_client = MagicMock()

        with patch("src.infrastructure.audible_client.audible.Client"):
            with patch("asyncio.get_event_loop") as mock_loop:
                mock_loop.return_value.run_in_executor = AsyncMock(return_value=mock_audible_client)

                try:
                    async with AsyncAudibleClient(auth):
                        raise ValueError("Test error")
                except ValueError:
                    pass
