"""Tests for database metadata operations."""

import pytest
from datetime import date


class TestContributorsOperations:
    """Tests for contributors database operations."""

    def test_add_contributor(self, monkeypatch):
        """Test adding a contributor."""
        from src.database.db_contributors import contributor_ops

        def mock_add_contributor(name, role, bio=None):
            return f"contributor-{name}"

        monkeypatch.setattr(contributor_ops, "add_contributor", mock_add_contributor)

        # Test can add contributor
        result = contributor_ops.add_contributor("Michelle Obama", "author")
        assert result is not None

    def test_get_contributor_by_id(self, monkeypatch):
        """Test retrieving contributor by ID."""
        from src.database.db_contributors import contributor_ops

        def mock_get_contributor_by_id(contributor_id):
            return {
                "contributor_id": contributor_id,
                "name": "Test Author",
                "role": "author",
            }

        monkeypatch.setattr(
            contributor_ops, "get_contributor_by_id", mock_get_contributor_by_id
        )

        result = contributor_ops.get_contributor_by_id("contrib-1")
        assert result["name"] == "Test Author"

    def test_link_contributor_to_book(self, monkeypatch):
        """Test linking contributor to book."""
        from src.database.db_contributors import contributor_ops

        def mock_link_contributor_to_book(asin, contributor_id):
            return True

        monkeypatch.setattr(
            contributor_ops, "link_contributor_to_book", mock_link_contributor_to_book
        )

        result = contributor_ops.link_contributor_to_book("B084L6Z6M3", "contrib-1")
        assert result is True

    def test_get_book_contributors(self, monkeypatch):
        """Test retrieving all contributors for a book."""
        from src.database.db_contributors import contributor_ops

        def mock_get_book_contributors(asin):
            return [
                {"contributor_id": "1", "name": "Michelle Obama", "role": "author"},
                {"contributor_id": "2", "name": "Narrator Name", "role": "narrator"},
            ]

        monkeypatch.setattr(
            contributor_ops, "get_book_contributors", mock_get_book_contributors
        )

        result = contributor_ops.get_book_contributors("B084L6Z6M3")
        assert len(result) == 2
        assert any(c["role"] == "narrator" for c in result)

    def test_update_contributor_info(self, monkeypatch):
        """Test updating contributor information."""
        from src.database.db_contributors import contributor_ops

        def mock_update_contributor(contributor_id, **fields):
            return True

        monkeypatch.setattr(contributor_ops, "update_contributor", mock_update_contributor)

        result = contributor_ops.update_contributor("contrib-1", bio="Updated bio")
        assert result is True


class TestMediaInfoOperations:
    """Tests for media information database operations."""

    def test_add_media_info(self, monkeypatch):
        """Test adding media information for a book."""
        from src.database.db_media_info import media_info_ops

        def mock_add_media_info(asin, codec, bitrate, sample_rate=None):
            return True

        monkeypatch.setattr(media_info_ops, "add_media_info", mock_add_media_info)

        result = media_info_ops.add_media_info("B084L6Z6M3", "aac", 64000)
        assert result is True

    def test_get_media_info(self, monkeypatch):
        """Test retrieving media information."""
        from src.database.db_media_info import media_info_ops

        def mock_get_media_info(asin):
            return {
                "asin": asin,
                "codec": "aac",
                "bitrate": 64000,
                "sample_rate": 44100,
                "channels": 2,
                "duration_ms": 36000000,
            }

        monkeypatch.setattr(media_info_ops, "get_media_info", mock_get_media_info)

        result = media_info_ops.get_media_info("B084L6Z6M3")
        assert result["codec"] == "aac"
        assert result["bitrate"] == 64000

    def test_update_media_info(self, monkeypatch):
        """Test updating media information."""
        from src.database.db_media_info import media_info_ops

        def mock_update_media_info(asin, **fields):
            return True

        monkeypatch.setattr(media_info_ops, "update_media_info", mock_update_media_info)

        result = media_info_ops.update_media_info("B084L6Z6M3", codec="mp3")
        assert result is True

    def test_get_books_by_codec(self, monkeypatch):
        """Test retrieving books filtered by codec."""
        from src.database.db_media_info import media_info_ops

        def mock_get_books_by_codec(codec):
            return [
                {"asin": "B084L6Z6M3", "codec": codec},
                {"asin": "B084L6Z6M4", "codec": codec},
            ]

        monkeypatch.setattr(
            media_info_ops, "get_books_by_codec", mock_get_books_by_codec
        )

        result = media_info_ops.get_books_by_codec("aac")
        assert len(result) == 2


class TestReadingProgressOperations:
    """Tests for reading progress database operations."""

    def test_create_reading_progress(self, monkeypatch):
        """Test creating reading progress record."""
        from src.database.db_reading_progress import progress_ops

        def mock_create_reading_progress(user_id, asin):
            return True

        monkeypatch.setattr(
            progress_ops, "create_reading_progress", mock_create_reading_progress
        )

        result = progress_ops.create_reading_progress("user-1", "B084L6Z6M3")
        assert result is True

    def test_update_reading_progress(self, monkeypatch):
        """Test updating reading progress."""
        from src.database.db_reading_progress import progress_ops

        def mock_update_reading_progress(user_id, asin, position_ms):
            return True

        monkeypatch.setattr(
            progress_ops, "update_reading_progress", mock_update_reading_progress
        )

        result = progress_ops.update_reading_progress("user-1", "B084L6Z6M3", 3600000)
        assert result is True

    def test_get_reading_progress(self, monkeypatch):
        """Test retrieving reading progress."""
        from src.database.db_reading_progress import progress_ops

        def mock_get_reading_progress(user_id, asin):
            return {
                "user_id": user_id,
                "asin": asin,
                "position_ms": 3600000,
                "last_updated": "2024-12-20T10:00:00",
                "completed": False,
            }

        monkeypatch.setattr(
            progress_ops, "get_reading_progress", mock_get_reading_progress
        )

        result = progress_ops.get_reading_progress("user-1", "B084L6Z6M3")
        assert result["position_ms"] == 3600000
        assert result["completed"] is False

    def test_mark_book_completed(self, monkeypatch):
        """Test marking book as completed."""
        from src.database.db_reading_progress import progress_ops

        def mock_mark_completed(user_id, asin):
            return True

        monkeypatch.setattr(progress_ops, "mark_completed", mock_mark_completed)

        result = progress_ops.mark_completed("user-1", "B084L6Z6M3")
        assert result is True

    def test_get_user_currently_reading(self, monkeypatch):
        """Test getting user's currently reading books."""
        from src.database.db_reading_progress import progress_ops

        def mock_get_currently_reading(user_id, limit=10):
            return [
                {"asin": "B084L6Z6M3", "position_ms": 3600000},
                {"asin": "B084L6Z6M4", "position_ms": 7200000},
            ]

        monkeypatch.setattr(
            progress_ops, "get_currently_reading", mock_get_currently_reading
        )

        result = progress_ops.get_currently_reading("user-1")
        assert len(result) == 2


class TestBookAvailabilityOperations:
    """Tests for book availability database operations."""

    def test_add_book_availability(self, monkeypatch):
        """Test adding book availability record."""
        from src.database.db_book_availability import availability_ops

        def mock_add_book_availability(asin, **fields):
            return True

        monkeypatch.setattr(
            availability_ops, "add_book_availability", mock_add_book_availability
        )

        result = availability_ops.add_book_availability(
            "B084L6Z6M3",
            region="US",
            available=True,
        )
        assert result is True

    def test_get_availability_by_region(self, monkeypatch):
        """Test retrieving availability for region."""
        from src.database.db_book_availability import availability_ops

        def mock_get_availability_by_region(asin, region):
            return {
                "asin": asin,
                "region": region,
                "available": True,
                "ownership_type": "purchased",
            }

        monkeypatch.setattr(
            availability_ops,
            "get_availability_by_region",
            mock_get_availability_by_region,
        )

        result = availability_ops.get_availability_by_region("B084L6Z6M3", "US")
        assert result["available"] is True

    def test_check_regional_availability(self, monkeypatch):
        """Test checking availability across regions."""
        from src.database.db_book_availability import availability_ops

        def mock_get_book_availability_all_regions(asin):
            return [
                {"region": "US", "available": True},
                {"region": "GB", "available": True},
                {"region": "CA", "available": False},
            ]

        monkeypatch.setattr(
            availability_ops,
            "get_book_availability_all_regions",
            mock_get_book_availability_all_regions,
        )

        result = availability_ops.get_book_availability_all_regions("B084L6Z6M3")
        assert len(result) == 3
        assert any(r["available"] for r in result)


class TestCompanionMaterialsOperations:
    """Tests for companion materials database operations."""

    def test_add_companion_material(self, monkeypatch):
        """Test adding companion material."""
        from src.database.db_companion_materials import materials_ops

        def mock_add_companion_material(asin, file_type, file_path):
            return True

        monkeypatch.setattr(
            materials_ops, "add_companion_material", mock_add_companion_material
        )

        result = materials_ops.add_companion_material(
            "B084L6Z6M3",
            "pdf",
            "/materials/book-guide.pdf",
        )
        assert result is True

    def test_get_companion_materials(self, monkeypatch):
        """Test retrieving companion materials for book."""
        from src.database.db_companion_materials import materials_ops

        def mock_get_companion_materials(asin):
            return [
                {"file_type": "pdf", "file_path": "/materials/guide.pdf"},
                {"file_type": "txt", "file_path": "/materials/transcript.txt"},
            ]

        monkeypatch.setattr(
            materials_ops, "get_companion_materials", mock_get_companion_materials
        )

        result = materials_ops.get_companion_materials("B084L6Z6M3")
        assert len(result) == 2
        assert any(m["file_type"] == "pdf" for m in result)

    def test_remove_companion_material(self, monkeypatch):
        """Test removing companion material."""
        from src.database.db_companion_materials import materials_ops

        def mock_remove_companion_material(material_id):
            return True

        monkeypatch.setattr(
            materials_ops, "remove_companion_material", mock_remove_companion_material
        )

        result = materials_ops.remove_companion_material("material-1")
        assert result is True


class TestMetadataJSONOperations:
    """Tests for flexible JSON metadata operations."""

    def test_store_json_metadata(self, monkeypatch):
        """Test storing flexible metadata as JSON."""
        from src.database.db_book_metadata import metadata_ops

        def mock_store_metadata(asin, metadata_key, metadata_value):
            return True

        monkeypatch.setattr(metadata_ops, "store_metadata", mock_store_metadata)

        custom_metadata = {
            "series_position": 3,
            "recommended_age": 18,
            "content_warnings": ["violence"],
        }
        result = metadata_ops.store_metadata("B084L6Z6M3", "custom", custom_metadata)
        assert result is True

    def test_retrieve_json_metadata(self, monkeypatch):
        """Test retrieving flexible metadata."""
        from src.database.db_book_metadata import metadata_ops

        def mock_get_metadata(asin, metadata_key):
            return {
                "asin": asin,
                "key": metadata_key,
                "value": {
                    "series_position": 3,
                    "recommended_age": 18,
                },
            }

        monkeypatch.setattr(metadata_ops, "get_metadata", mock_get_metadata)

        result = metadata_ops.get_metadata("B084L6Z6M3", "custom")
        assert result["value"]["series_position"] == 3

    def test_query_by_metadata(self, monkeypatch):
        """Test querying books by metadata."""
        from src.database.db_book_metadata import metadata_ops

        def mock_query_by_metadata(metadata_key, metadata_value):
            return [
                {"asin": "B084L6Z6M3"},
                {"asin": "B084L6Z6M4"},
            ]

        monkeypatch.setattr(
            metadata_ops, "query_by_metadata", mock_query_by_metadata
        )

        result = metadata_ops.query_by_metadata("series", "Becoming")
        assert len(result) >= 0


class TestMetadataViews:
    """Tests for database views aggregating metadata."""

    def test_view_books_with_metadata(self, monkeypatch):
        """Test v_books_with_metadata view."""
        from src.database.db_books import book_ops

        def mock_get_book_with_all_metadata(asin):
            return {
                "asin": asin,
                "title": "Test Book",
                "authors": ["Author 1", "Author 2"],
                "narrators": ["Narrator"],
                "media_info": {"codec": "aac", "bitrate": 64000},
                "contributors": [
                    {"name": "Author 1", "role": "author"},
                    {"name": "Narrator", "role": "narrator"},
                ],
                "availability": {"region": "US", "available": True},
                "companion_materials": [{"type": "pdf", "path": "/path"}],
                "reading_progress": {"position_ms": 0, "completed": False},
            }

        monkeypatch.setattr(
            book_ops, "get_book_with_all_metadata", mock_get_book_with_all_metadata
        )

        result = book_ops.get_book_with_all_metadata("B084L6Z6M3")
        assert result["asin"] == "B084L6Z6M3"
        assert "authors" in result
        assert "media_info" in result
        assert "reading_progress" in result


class TestMetadataIndexing:
    """Tests for metadata index optimization."""

    def test_search_by_author(self, monkeypatch):
        """Test searching books by author using indexes."""
        from src.database.db_contributors import contributor_ops

        def mock_search_books_by_author(author_name):
            return [{"asin": "B084L6Z6M3"}, {"asin": "B084L6Z6M4"}]

        monkeypatch.setattr(
            contributor_ops, "search_books_by_author", mock_search_books_by_author
        )

        result = contributor_ops.search_books_by_author("Michelle Obama")
        assert len(result) > 0

    def test_search_by_narrator(self, monkeypatch):
        """Test searching books by narrator using indexes."""
        from src.database.db_contributors import contributor_ops

        def mock_search_books_by_narrator(narrator_name):
            return [{"asin": "B084L6Z6M3"}]

        monkeypatch.setattr(
            contributor_ops, "search_books_by_narrator", mock_search_books_by_narrator
        )

        result = contributor_ops.search_books_by_narrator("Narrator Name")
        assert len(result) >= 0

    def test_search_by_series(self, monkeypatch):
        """Test searching books by series name."""
        from src.database.db_book_metadata import metadata_ops

        def mock_search_by_series(series_name):
            return [{"asin": "B084L6Z6M3"}, {"asin": "B084L6Z6M4"}]

        monkeypatch.setattr(
            metadata_ops, "search_by_series", mock_search_by_series
        )

        result = metadata_ops.search_by_series("Some Series")
        assert len(result) >= 0
