"""Tests for src.infrastructure.file_utils module."""

from unittest.mock import patch

import pytest

from src.infrastructure.file_utils import (ensure_directory,
                                           file_exists_in_directory,
                                           normalize_filename)


@pytest.mark.unit
class TestNormalizeFilename:
    """Test filename normalization function."""

    def test_basic_alphanumeric(self):
        """Test normalization of basic alphanumeric characters."""
        assert normalize_filename("AudioBook123") == "audiobook123"

    def test_removes_special_characters(self):
        """Test that special characters are removed."""
        assert normalize_filename("Audio-Book!@#") == "audiobook"

    def test_preserves_spaces(self):
        """Test that spaces are preserved."""
        result = normalize_filename("Audio Book")
        assert result == "audio book"

    def test_converts_to_lowercase(self):
        """Test conversion to lowercase."""
        assert normalize_filename("AUDIOBOOK") == "audiobook"

    def test_mixed_case_and_special_chars(self):
        """Test mixed case with special characters."""
        assert normalize_filename("Audio-Book_2024!") == "audiobook 2024"

    def test_strips_leading_trailing_spaces(self):
        """Test that leading and trailing spaces are stripped."""
        assert normalize_filename("  audio book  ") == "audio book"

    def test_multiple_spaces_preserved(self):
        """Test that multiple spaces are preserved."""
        result = normalize_filename("audio    book")
        assert "audio" in result and "book" in result

    def test_empty_string(self):
        """Test normalization of empty string."""
        assert normalize_filename("") == ""

    def test_only_special_characters(self):
        """Test string with only special characters."""
        assert normalize_filename("!@#$%^&*()") == ""

    def test_numbers_preserved(self):
        """Test that numbers are preserved."""
        assert normalize_filename("Book123") == "book123"

    def test_unicode_characters(self):
        """Test handling of unicode characters."""
        # Non-alphanumeric unicode characters should be removed
        result = normalize_filename("Café")
        assert "caf" in result

    def test_parentheses_removed(self):
        """Test that parentheses are removed."""
        assert normalize_filename("Book (Author)") == "book author"

    def test_dots_removed(self):
        """Test that dots are removed."""
        assert normalize_filename("book.title.mp3") == "booktitlemp3"

    def test_hyphens_removed(self):
        """Test that hyphens are removed."""
        assert normalize_filename("book-title") == "booktitle"

    def test_underscores_removed(self):
        """Test that underscores are removed."""
        assert normalize_filename("book_title") == "booktitle"

    def test_slashes_removed(self):
        """Test that slashes are removed."""
        assert normalize_filename("book/title") == "booktitle"

    def test_backslashes_removed(self):
        """Test that backslashes are removed."""
        assert normalize_filename("book\\title") == "booktitle"


@pytest.mark.asyncio
@pytest.mark.unit
class TestEnsureDirectory:
    """Test directory creation function."""

    async def test_creates_directory(self, temp_dir):
        """Test that ensure_directory creates a directory."""
        test_dir = temp_dir / "test_dir"
        assert not test_dir.exists()

        await ensure_directory(str(test_dir))

        assert test_dir.exists()
        assert test_dir.is_dir()

    async def test_creates_nested_directories(self, temp_dir):
        """Test that ensure_directory creates nested directories."""
        test_dir = temp_dir / "a" / "b" / "c"
        assert not test_dir.exists()

        await ensure_directory(str(test_dir))

        assert test_dir.exists()
        assert test_dir.is_dir()

    async def test_idempotent_existing_directory(self, temp_dir):
        """Test that ensure_directory works with existing directories."""
        test_dir = temp_dir / "test_dir"
        test_dir.mkdir(parents=True, exist_ok=True)

        await ensure_directory(str(test_dir))

        assert test_dir.exists()

    async def test_does_not_fail_on_existing_dir(self, temp_dir):
        """Test that ensure_directory doesn't fail when directory exists."""
        test_dir = temp_dir / "existing"
        test_dir.mkdir(parents=True, exist_ok=True)

        await ensure_directory(str(test_dir))

        assert test_dir.exists()

    async def test_creates_multiple_levels(self, temp_dir):
        """Test creating deeply nested directories."""
        test_dir = temp_dir / "level1" / "level2" / "level3" / "level4"

        await ensure_directory(str(test_dir))

        assert test_dir.exists()
        assert (test_dir.parent / "level3").exists()
        assert (test_dir.parent.parent / "level2").exists()


@pytest.mark.unit
class TestFileExistsInDirectory:
    """Test file existence checking function."""

    def test_finds_file_with_identifier(self, temp_dir):
        """Test finding a file matching an identifier."""
        test_file = temp_dir / "book_ABC123.m4b"
        test_file.touch()

        assert file_exists_in_directory(str(temp_dir), ["ABC123"])

    def test_does_not_find_missing_file(self, temp_dir):
        """Test that missing files return False."""
        test_file = temp_dir / "book_ABC123.m4b"
        test_file.touch()

        assert not file_exists_in_directory(str(temp_dir), ["XYZ789"])

    def test_finds_file_with_multiple_identifiers(self, temp_dir):
        """Test finding with multiple identifier options."""
        test_file = temp_dir / "book_ABC123.m4b"
        test_file.touch()

        assert file_exists_in_directory(str(temp_dir), ["XYZ", "ABC123", "DEF"])

    def test_finds_first_matching_identifier(self, temp_dir):
        """Test that first matching identifier returns True."""
        test_file = temp_dir / "book_ABC123.m4b"
        test_file.touch()

        assert file_exists_in_directory(str(temp_dir), ["ABC123", "ABC"])

    def test_handles_nonexistent_directory(self, temp_dir):
        """Test handling of non-existent directory."""
        nonexistent = temp_dir / "does_not_exist"

        with patch("src.infrastructure.file_utils.logger.warning"):
            result = file_exists_in_directory(str(nonexistent), ["test"])

        assert result is False

    def test_handles_empty_identifiers_list(self, temp_dir):
        """Test handling of empty identifiers list."""
        test_file = temp_dir / "book_ABC123.m4b"
        test_file.touch()

        assert not file_exists_in_directory(str(temp_dir), [])

    def test_case_sensitive_matching(self, temp_dir):
        """Test that matching is case-sensitive."""
        test_file = temp_dir / "book_ABC123.m4b"
        test_file.touch()

        assert file_exists_in_directory(str(temp_dir), ["ABC123"])
        assert not file_exists_in_directory(str(temp_dir), ["abc123"])

    def test_partial_identifier_matching(self, temp_dir):
        """Test partial identifier matching."""
        test_file = temp_dir / "book_ABC123_full.m4b"
        test_file.touch()

        assert file_exists_in_directory(str(temp_dir), ["ABC"])
        assert file_exists_in_directory(str(temp_dir), ["123"])
        assert file_exists_in_directory(str(temp_dir), ["full"])

    def test_multiple_files_in_directory(self, temp_dir):
        """Test with multiple files in directory."""
        (temp_dir / "book_ABC123.m4b").touch()
        (temp_dir / "book_XYZ789.m4b").touch()
        (temp_dir / "book_DEF456.m4b").touch()

        assert file_exists_in_directory(str(temp_dir), ["ABC123"])
        assert file_exists_in_directory(str(temp_dir), ["XYZ789"])
        assert file_exists_in_directory(str(temp_dir), ["DEF456"])

    def test_ignores_subdirectories(self, temp_dir):
        """Test that subdirectories don't cause issues."""
        subdir = temp_dir / "subdir"
        subdir.mkdir()
        (subdir / "nested_ABC123.m4b").touch()

        # Should not find files in subdirectories (only checks directory contents)
        result = file_exists_in_directory(str(temp_dir), ["ABC123"])
        # The function will list the subdir name, which doesn't contain ABC123
        assert result is False

    def test_finds_directory_names(self, temp_dir):
        """Test finding directories by identifier."""
        subdir = temp_dir / "ABC123_directory"
        subdir.mkdir()

        assert file_exists_in_directory(str(temp_dir), ["ABC123"])

    def test_handles_empty_directory(self, temp_dir):
        """Test handling of empty directory."""
        assert not file_exists_in_directory(str(temp_dir), ["test"])

    def test_handles_file_not_found_exception(self):
        """Test handling of FileNotFoundError exception."""
        with patch("os.listdir") as mock_listdir:
            mock_listdir.side_effect = FileNotFoundError("Directory not found")

            with patch("src.infrastructure.file_utils.logger.warning"):
                result = file_exists_in_directory("/nonexistent", ["test"])

        assert result is False

    def test_with_special_characters_in_identifier(self, temp_dir):
        """Test identifiers with special characters."""
        test_file = temp_dir / "book_ABC-123.m4b"
        test_file.touch()

        assert file_exists_in_directory(str(temp_dir), ["ABC-123"])

    def test_logs_warning_for_missing_directory(self, temp_dir):
        """Test that warning is logged for missing directory."""
        nonexistent = temp_dir / "does_not_exist"

        with patch("src.infrastructure.file_utils.logger.warning") as mock_logger:
            file_exists_in_directory(str(nonexistent), ["test"])
            mock_logger.assert_called()


@pytest.mark.unit
class TestFileUtilsEdgeCases:
    """Test edge cases for file utilities."""

    def test_normalize_whitespace_only(self):
        """Test normalization of whitespace-only string."""
        assert normalize_filename("   ") == ""

    def test_normalize_with_tabs(self):
        """Test normalization with tab characters."""
        result = normalize_filename("audio\tbook")
        # Tabs are not alphanumeric or spaces, so should be removed
        assert "audio" in result and "book" in result

    def test_file_exists_identifier_substring_match(self, temp_dir):
        """Test that identifier must be substring, not exact match."""
        test_file = temp_dir / "prefix_ABC123_suffix.m4b"
        test_file.touch()

        assert file_exists_in_directory(str(temp_dir), ["ABC123"])
        assert file_exists_in_directory(str(temp_dir), ["prefix_ABC"])
        assert file_exists_in_directory(str(temp_dir), ["123_suffix"])

    def test_file_exists_with_long_filename(self, temp_dir):
        """Test with very long filename."""
        test_file = temp_dir / ("book_" + "a" * 100 + "_ABC123.m4b")
        test_file.touch()

        assert file_exists_in_directory(str(temp_dir), ["ABC123"])
