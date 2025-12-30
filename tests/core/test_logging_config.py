"""Tests for src.core.logging_config module."""

import sys
from unittest.mock import patch

import pytest

from src.core.logging_config import configure_logging


@pytest.mark.unit
class TestConfigureLogging:
    """Test logging configuration."""

    def test_configure_logging_default_level(self):
        """Test configure_logging with default INFO level."""
        with patch("src.core.logging_config.logger.remove") as mock_remove, patch(
            "src.core.logging_config.logger.add"
        ) as mock_add:
            configure_logging()

            mock_remove.assert_called_once()
            assert mock_add.call_count == 2

    def test_configure_logging_custom_level(self):
        """Test configure_logging with custom log level."""
        with patch("src.core.logging_config.logger.remove") as mock_remove, patch(
            "src.core.logging_config.logger.add"
        ) as mock_add:
            configure_logging(log_level="DEBUG")

            mock_remove.assert_called_once()
            assert mock_add.call_count == 2

    def test_configure_logging_removes_default_handler(self):
        """Test that configure_logging removes default logger."""
        with patch("src.core.logging_config.logger.remove") as mock_remove:
            configure_logging()
            mock_remove.assert_called_once()

    def test_configure_logging_adds_stderr_handler(self):
        """Test that configure_logging adds stderr handler."""
        with patch("src.core.logging_config.logger.remove"), patch(
            "src.core.logging_config.logger.add"
        ) as mock_add:
            configure_logging()

            calls = mock_add.call_args_list
            assert calls[0][0][0] == sys.stderr

    def test_configure_logging_adds_file_handler(self):
        """Test that configure_logging adds file handler."""
        with patch("src.core.logging_config.logger.remove"), patch(
            "src.core.logging_config.logger.add"
        ) as mock_add:
            configure_logging()

            calls = mock_add.call_args_list
            assert "logs/" in calls[1][0][0]

    def test_configure_logging_stderr_format(self):
        """Test stderr handler has correct format."""
        with patch("src.core.logging_config.logger.remove"), patch(
            "src.core.logging_config.logger.add"
        ) as mock_add:
            configure_logging()

            stderr_call = mock_add.call_args_list[0]
            format_str = stderr_call[1]["format"]
            assert "{time:YYYY-MM-DD HH:mm:ss}" in format_str
            assert "{level}" in format_str
            assert "{message}" in format_str

    def test_configure_logging_file_format(self):
        """Test file handler has correct format."""
        with patch("src.core.logging_config.logger.remove"), patch(
            "src.core.logging_config.logger.add"
        ) as mock_add:
            configure_logging()

            file_call = mock_add.call_args_list[1]
            format_str = file_call[1]["format"]
            assert "{time:YYYY-MM-DD HH:mm:ss}" in format_str
            assert "{level: <8}" in format_str
            assert "{message}" in format_str

    def test_configure_logging_file_rotation(self):
        """Test file handler has rotation configuration."""
        with patch("src.core.logging_config.logger.remove"), patch(
            "src.core.logging_config.logger.add"
        ) as mock_add:
            configure_logging()

            file_call = mock_add.call_args_list[1]
            assert file_call[1]["rotation"] == "500 MB"

    def test_configure_logging_info_level(self):
        """Test configure_logging with INFO level."""
        with patch("src.core.logging_config.logger.remove"), patch(
            "src.core.logging_config.logger.add"
        ) as mock_add:
            configure_logging(log_level="INFO")

            for call_args in mock_add.call_args_list:
                assert call_args[1]["level"] == "INFO"

    def test_configure_logging_debug_level(self):
        """Test configure_logging with DEBUG level."""
        with patch("src.core.logging_config.logger.remove"), patch(
            "src.core.logging_config.logger.add"
        ) as mock_add:
            configure_logging(log_level="DEBUG")

            for call_args in mock_add.call_args_list:
                assert call_args[1]["level"] == "DEBUG"

    def test_configure_logging_warning_level(self):
        """Test configure_logging with WARNING level."""
        with patch("src.core.logging_config.logger.remove"), patch(
            "src.core.logging_config.logger.add"
        ) as mock_add:
            configure_logging(log_level="WARNING")

            for call_args in mock_add.call_args_list:
                assert call_args[1]["level"] == "WARNING"

    def test_configure_logging_error_level(self):
        """Test configure_logging with ERROR level."""
        with patch("src.core.logging_config.logger.remove"), patch(
            "src.core.logging_config.logger.add"
        ) as mock_add:
            configure_logging(log_level="ERROR")

            for call_args in mock_add.call_args_list:
                assert call_args[1]["level"] == "ERROR"

    def test_configure_logging_critical_level(self):
        """Test configure_logging with CRITICAL level."""
        with patch("src.core.logging_config.logger.remove"), patch(
            "src.core.logging_config.logger.add"
        ) as mock_add:
            configure_logging(log_level="CRITICAL")

            for call_args in mock_add.call_args_list:
                assert call_args[1]["level"] == "CRITICAL"

    def test_configure_logging_handlers_count(self):
        """Test that configure_logging adds exactly 2 handlers."""
        with patch("src.core.logging_config.logger.remove"), patch(
            "src.core.logging_config.logger.add"
        ) as mock_add:
            configure_logging()

            assert mock_add.call_count == 2

    def test_configure_logging_file_path_contains_logs(self):
        """Test that file handler path contains logs directory."""
        with patch("src.core.logging_config.logger.remove"), patch(
            "src.core.logging_config.logger.add"
        ) as mock_add:
            configure_logging()

            file_call = mock_add.call_args_list[1]
            file_path = file_call[0][0]
            assert "logs" in file_path

    def test_configure_logging_file_path_has_time_format(self):
        """Test that file handler path includes time format."""
        with patch("src.core.logging_config.logger.remove"), patch(
            "src.core.logging_config.logger.add"
        ) as mock_add:
            configure_logging()

            file_call = mock_add.call_args_list[1]
            file_path = file_call[0][0]
            assert "{time}" in file_path


@pytest.mark.unit
class TestConfigureLoggingIntegration:
    """Integration tests for logging configuration."""

    def test_configure_logging_idempotent(self):
        """Test that configure_logging can be called multiple times."""
        with patch("src.core.logging_config.logger.remove") as mock_remove, patch(
            "src.core.logging_config.logger.add"
        ):
            configure_logging()
            configure_logging()
            assert mock_remove.call_count == 2

    def test_configure_logging_with_different_levels(self):
        """Test configure_logging with different levels in sequence."""
        levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

        with patch("src.core.logging_config.logger.remove"), patch(
            "src.core.logging_config.logger.add"
        ) as mock_add:
            for level in levels:
                mock_add.reset_mock()
                configure_logging(log_level=level)

                for call_args in mock_add.call_args_list:
                    assert call_args[1]["level"] == level
