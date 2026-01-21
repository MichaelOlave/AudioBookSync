"""Tests for src.core.config module."""

import os
from unittest.mock import patch

import pytest

from src.core.config import Config


@pytest.mark.unit
class TestConfigDefaults:
    """Test Config class with default values."""

    def test_default_auth_file(self):
        """Test default AUTH_FILE value."""
        with patch.dict(os.environ, {}, clear=False):
            # Need to reload Config to reset class variables
            import importlib

            import src.core.config

            importlib.reload(src.core.config)
            from src.core.config import Config as ConfigReloaded

            assert ConfigReloaded.AUTH_FILE == "Michael.json"

    def test_default_activation_bytes(self):
        """Test default ACTIVATION_BYTES value."""
        with patch.dict(os.environ, {}, clear=False):
            import importlib

            import src.core.config

            importlib.reload(src.core.config)
            from src.core.config import Config as ConfigReloaded

            assert ConfigReloaded.ACTIVATION_BYTES == "c3f80507"

    def test_default_download_dir(self):
        """Test default DOWNLOAD_DIR value."""
        with patch.dict(os.environ, {}, clear=False):
            import importlib

            import src.core.config

            importlib.reload(src.core.config)
            from src.core.config import Config as ConfigReloaded

            assert ConfigReloaded.DOWNLOAD_DIR == "audiobooks/downloaded"

    def test_default_decrypted_dir(self):
        """Test default DECRYPTED_DIR value."""
        with patch.dict(os.environ, {}, clear=False):
            import importlib

            import src.core.config

            importlib.reload(src.core.config)
            from src.core.config import Config as ConfigReloaded

            assert ConfigReloaded.DECRYPTED_DIR == "audiobooks/decrypted"

    def test_default_log_dir(self):
        """Test default LOG_DIR value."""
        with patch.dict(os.environ, {}, clear=False):
            import importlib

            import src.core.config

            importlib.reload(src.core.config)
            from src.core.config import Config as ConfigReloaded

            assert ConfigReloaded.LOG_DIR == "logs"

    def test_default_num_results(self):
        """Test default AUDIBLE_NUM_RESULTS value."""
        with patch.dict(os.environ, {}, clear=False):
            import importlib

            import src.core.config

            importlib.reload(src.core.config)
            from src.core.config import Config as ConfigReloaded

            assert ConfigReloaded.AUDIBLE_NUM_RESULTS == 2
            assert isinstance(ConfigReloaded.AUDIBLE_NUM_RESULTS, int)


@pytest.mark.unit
class TestConfigEnvironmentVariables:
    """Test Config class with environment variable overrides."""

    def test_auth_file_from_env(self, monkeypatch):
        """Test AUTH_FILE can be set from environment variable."""
        monkeypatch.setenv("AUTH_FILE", "/custom/path/auth.json")
        import importlib

        import src.core.config

        importlib.reload(src.core.config)
        from src.core.config import Config as ConfigReloaded

        assert ConfigReloaded.AUTH_FILE == "/custom/path/auth.json"

    def test_activation_bytes_from_env(self, monkeypatch):
        """Test ACTIVATION_BYTES can be set from environment variable."""
        monkeypatch.setenv("ACTIVATION_BYTES", "abcdef1234567890")
        import importlib

        import src.core.config

        importlib.reload(src.core.config)
        from src.core.config import Config as ConfigReloaded

        assert ConfigReloaded.ACTIVATION_BYTES == "abcdef1234567890"

    def test_download_dir_from_env(self, monkeypatch):
        """Test DOWNLOAD_DIR can be set from environment variable."""
        monkeypatch.setenv("DOWNLOAD_DIR", "/custom/downloads")
        import importlib

        import src.core.config

        importlib.reload(src.core.config)
        from src.core.config import Config as ConfigReloaded

        assert ConfigReloaded.DOWNLOAD_DIR == "/custom/downloads"

    def test_num_results_from_env(self, monkeypatch):
        """Test AUDIBLE_NUM_RESULTS can be set from environment variable."""
        monkeypatch.setenv("AUDIBLE_NUM_RESULTS", "50")
        import importlib

        import src.core.config

        importlib.reload(src.core.config)
        from src.core.config import Config as ConfigReloaded

        assert ConfigReloaded.AUDIBLE_NUM_RESULTS == 50
        assert isinstance(ConfigReloaded.AUDIBLE_NUM_RESULTS, int)


@pytest.mark.unit
class TestConfigEnsureDirectories:
    """Test ensure_directories method."""

    def test_ensure_directories_creates_missing_dirs(self, temp_dir):
        """Test that ensure_directories creates missing directories."""
        download_dir = temp_dir / "downloads"
        decrypted_dir = temp_dir / "decrypted"
        log_dir = temp_dir / "logs"

        assert not download_dir.exists()
        assert not decrypted_dir.exists()
        assert not log_dir.exists()

        with (
            patch.object(Config, "DOWNLOAD_DIR", str(download_dir)),
            patch.object(Config, "DECRYPTED_DIR", str(decrypted_dir)),
            patch.object(Config, "LOG_DIR", str(log_dir)),
        ):
            Config.ensure_directories()

        assert download_dir.exists()
        assert decrypted_dir.exists()
        assert log_dir.exists()

    def test_ensure_directories_with_existing_dirs(self, temp_dir):
        """Test that ensure_directories works with existing directories."""
        download_dir = temp_dir / "downloads"
        decrypted_dir = temp_dir / "decrypted"
        log_dir = temp_dir / "logs"

        download_dir.mkdir(parents=True, exist_ok=True)
        decrypted_dir.mkdir(parents=True, exist_ok=True)
        log_dir.mkdir(parents=True, exist_ok=True)

        with (
            patch.object(Config, "DOWNLOAD_DIR", str(download_dir)),
            patch.object(Config, "DECRYPTED_DIR", str(decrypted_dir)),
            patch.object(Config, "LOG_DIR", str(log_dir)),
        ):
            Config.ensure_directories()

        assert download_dir.exists()
        assert decrypted_dir.exists()
        assert log_dir.exists()

    def test_ensure_directories_creates_nested_dirs(self, temp_dir):
        """Test that ensure_directories creates nested directories."""
        nested_dir = temp_dir / "a" / "b" / "c"

        assert not nested_dir.exists()

        with (
            patch.object(Config, "DOWNLOAD_DIR", str(nested_dir)),
            patch.object(Config, "DECRYPTED_DIR", str(temp_dir / "d")),
            patch.object(Config, "LOG_DIR", str(temp_dir / "e")),
        ):
            Config.ensure_directories()

        assert nested_dir.exists()

    def test_ensure_directories_idempotent(self, temp_dir):
        """Test that ensure_directories can be called multiple times safely."""
        download_dir = temp_dir / "downloads"

        with (
            patch.object(Config, "DOWNLOAD_DIR", str(download_dir)),
            patch.object(Config, "DECRYPTED_DIR", str(temp_dir / "d")),
            patch.object(Config, "LOG_DIR", str(temp_dir / "e")),
        ):
            Config.ensure_directories()
            assert download_dir.exists()
            Config.ensure_directories()
            assert download_dir.exists()


@pytest.mark.unit
class TestConfigAudibleAPI:
    """Test Audible API configuration."""

    def test_default_response_groups(self):
        """Test default AUDIBLE_RESPONSE_GROUPS value."""
        with patch.dict(os.environ, {}, clear=False):
            import importlib

            import src.core.config

            importlib.reload(src.core.config)
            from src.core.config import Config as ConfigReloaded

            assert ConfigReloaded.AUDIBLE_RESPONSE_GROUPS == "product_desc, product_attrs"

    def test_default_sort_by(self):
        """Test default AUDIBLE_SORT_BY value."""
        with patch.dict(os.environ, {}, clear=False):
            import importlib

            import src.core.config

            importlib.reload(src.core.config)
            from src.core.config import Config as ConfigReloaded

            assert ConfigReloaded.AUDIBLE_SORT_BY == "-PurchaseDate"

    def test_response_groups_from_env(self, monkeypatch):
        """Test AUDIBLE_RESPONSE_GROUPS from environment variable."""
        monkeypatch.setenv("AUDIBLE_RESPONSE_GROUPS", "custom_group")
        import importlib

        import src.core.config

        importlib.reload(src.core.config)
        from src.core.config import Config as ConfigReloaded

        assert ConfigReloaded.AUDIBLE_RESPONSE_GROUPS == "custom_group"

    def test_sort_by_from_env(self, monkeypatch):
        """Test AUDIBLE_SORT_BY from environment variable."""
        monkeypatch.setenv("AUDIBLE_SORT_BY", "-DateAdded")
        import importlib

        import src.core.config

        importlib.reload(src.core.config)
        from src.core.config import Config as ConfigReloaded

        assert ConfigReloaded.AUDIBLE_SORT_BY == "-DateAdded"
